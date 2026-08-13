import hashlib
import json
import uuid
from datetime import datetime, timezone

from phitest.domain.models import Run, Stimulus, Observation, Intervention, MetricResult, EvidenceClaim, TelemetrySample
from phitest.domain.errors import NotFoundError, AdapterError
from phitest.domain.telemetry import ALLOWED_TELEMETRY_KEYS
from phitest.ports.repository import Repository
from phitest.ports.target import TargetAdapter, ControllableTarget
from phitest.protocols.registry import get_protocol
from phitest.application import audit_service
from phitest import config as cfg


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def execute_run(repo: Repository, experiment_id: str, adapter: TargetAdapter,
                random_seed: int | None = None) -> Run:
    experiment = repo.get_experiment(experiment_id)
    if experiment is None:
        raise NotFoundError(f"Experiment {experiment_id} not found.")

    protocol = get_protocol(experiment.protocol_key)
    if protocol is None:
        raise NotFoundError(f"Protocol {experiment.protocol_key} not found.")

    seed = random_seed if random_seed is not None else 42
    run = Run(
        id=str(uuid.uuid4()),
        experiment_id=experiment_id,
        started_at=_now(),
        status="running",
        random_seed=seed,
        protocol_version=protocol.version,
        target_adapter=adapter.adapter_type,
    )
    repo.save_run(run)
    audit_service.emit(repo, "run_created", "run", run.id,
                       {"experiment_id": experiment_id, "protocol": protocol.key})
    repo.update_experiment_status(experiment_id, "running")
    audit_service.emit(repo, "experiment_started", "experiment", experiment_id, {})

    exp_config = json.loads(experiment.configuration_json)
    telemetry_allowlist = frozenset(exp_config.get("telemetry_allowlist", [])) & ALLOWED_TELEMETRY_KEYS

    try:
        raw_stimuli = protocol.generate_stimuli(exp_config, seed)
        recorded_stimuli = []
        recorded_observations = []
        recorded_interventions = []

        for raw in raw_stimuli:
            content = raw["content"]
            stim = Stimulus(
                id=str(uuid.uuid4()),
                run_id=run.id,
                sequence_no=raw["sequence_no"],
                stimulus_type=raw["stimulus_type"],
                content=content,
                content_sha256=_sha256(content),
                created_at=_now(),
            )
            repo.save_stimulus(stim)
            audit_service.emit(repo, "stimulus_recorded", "stimulus", stim.id,
                               {"sequence_no": stim.sequence_no, "type": stim.stimulus_type})
            recorded_stimuli.append(stim)

            if raw["stimulus_type"] == "intervention_marker":
                if isinstance(adapter, ControllableTarget):
                    intvn_config = raw.get("intervention_config", {})
                    intvn_type = intvn_config.get("type", raw.get("content", "marker"))
                    result = adapter.apply_intervention(intvn_type, intvn_config)
                    intvn = Intervention(
                        id=str(uuid.uuid4()),
                        run_id=run.id,
                        sequence_no=raw["sequence_no"],
                        intervention_type=intvn_type,
                        configuration_json=json.dumps(result),
                        rationale=raw.get("content", ""),
                        created_at=_now(),
                    )
                    repo.save_intervention(intvn)
                    audit_service.emit(repo, "intervention_recorded", "intervention", intvn.id,
                                       {"type": intvn.intervention_type,
                                        "sequence_no": intvn.sequence_no})
                    recorded_interventions.append(intvn)
                continue

            try:
                response = adapter.send(content)
            except AdapterError as exc:
                run.status = "failed"
                run.completed_at = _now()
                run.failure_reason = str(exc)
                repo.update_run(run)
                audit_service.emit(repo, "run_failed", "run", run.id,
                                   {"reason": run.failure_reason})
                repo.update_experiment_status(experiment_id, "failed")
                return run

            obs_text = response.text
            if len(obs_text) > cfg.MAX_OBSERVATION_LENGTH:
                obs_text = obs_text[:cfg.MAX_OBSERVATION_LENGTH]

            obs_type = _infer_obs_type(raw["stimulus_type"])
            obs = Observation(
                id=str(uuid.uuid4()),
                run_id=run.id,
                stimulus_id=stim.id,
                sequence_no=raw["sequence_no"],
                observation_type=obs_type,
                content=obs_text,
                content_sha256=_sha256(obs_text),
                created_at=_now(),
            )
            repo.save_observation(obs)
            audit_service.emit(repo, "observation_recorded", "observation", obs.id,
                               {"sequence_no": obs.sequence_no, "type": obs.observation_type})
            recorded_observations.append(obs)

            # Persist allowlisted telemetry from response metadata
            if telemetry_allowlist and response.metadata:
                filtered = {
                    k: v for k, v in response.metadata.items()
                    if k in telemetry_allowlist
                }
                if filtered:
                    sample = TelemetrySample(
                        id=str(uuid.uuid4()),
                        run_id=run.id,
                        observation_id=obs.id,
                        sequence_no=raw["sequence_no"],
                        phase="stimulus",
                        schema_version="1.0",
                        values_json=json.dumps(filtered),
                        allowed_keys=json.dumps(sorted(telemetry_allowlist)),
                        sampled_at=_now(),
                    )
                    repo.save_telemetry_sample(sample)
                    audit_service.emit(
                        repo, "telemetry_recorded", "telemetry_sample", sample.id,
                        {"sequence_no": sample.sequence_no,
                         "keys": sorted(filtered.keys())},
                    )

        # Metrics consume the same allowlisted telemetry persisted as evidence.
        telemetry_by_obs_id = {
            sample.observation_id: json.loads(sample.values_json)
            for sample in repo.list_telemetry_samples(run.id)
            if sample.observation_id is not None
        }
        runtime_config = dict(exp_config)
        runtime_config["_telemetry_by_obs_id"] = telemetry_by_obs_id

        # Compute metrics — pass recorded interventions and persisted telemetry.
        metric_dicts = protocol.compute_metrics(
            recorded_stimuli, recorded_observations, recorded_interventions, runtime_config
        )
        for md in metric_dicts:
            value_json = json.dumps(md["value"])
            mr = MetricResult(
                id=str(uuid.uuid4()),
                run_id=run.id,
                metric_key=md["metric_key"],
                metric_version=md["metric_version"],
                value_json=value_json,
                definition=md["definition"],
                computed_at=_now(),
            )
            repo.save_metric_result(mr)
            audit_service.emit(repo, "metric_computed", "metric_result", mr.id,
                               {"metric_key": mr.metric_key})

        # Generate claims
        claim_dicts = protocol.generate_claims(
            recorded_stimuli, recorded_observations, metric_dicts, runtime_config
        )
        for cd in claim_dicts:
            claim = EvidenceClaim(
                id=str(uuid.uuid4()),
                run_id=run.id,
                claim_type=cd["claim_type"],
                theory_key=cd.get("theory_key"),
                statement=cd["statement"],
                evidence_json="{}",
                confidence_label=cd.get("confidence_label", "not_applicable"),
                created_at=_now(),
            )
            repo.save_evidence_claim(claim)
            audit_service.emit(repo, "claim_created", "evidence_claim", claim.id,
                               {"claim_type": claim.claim_type})

        run.status = "completed"
        run.completed_at = _now()
        repo.update_run(run)
        audit_service.emit(repo, "run_completed", "run", run.id, {})
        repo.update_experiment_status(experiment_id, "completed")

    except Exception as exc:
        run.status = "failed"
        run.completed_at = _now()
        run.failure_reason = str(exc)
        repo.update_run(run)
        audit_service.emit(repo, "run_failed", "run", run.id, {"reason": run.failure_reason})
        repo.update_experiment_status(experiment_id, "failed")

    return run


def _infer_obs_type(stimulus_type: str) -> str:
    mapping = {
        "baseline_task": "baseline_response",
        "partitioned_recall_task": "partitioned_response",
        "information_seed": "seed_acknowledgment",
        "cross_task_retrieval": "retrieval_response",
        "calibration_question": "calibration_response",
        "identity_probe": "identity_response",
        "continuity_probe": "continuity_response",
        "phenomenal_report_elicitation": "phenomenal_report_behavior",
        "paraphrase_probe": "paraphrase_response",
        "leading_prompt": "leading_response",
        "pre_perturbation_probe": "pre_perturbation_response",
        "post_perturbation_probe": "post_perturbation_response",
        "resource_progress_task": "resource_progress_response",
        "gsb_baseline_probe": "gsb_baseline_response",
        "gsb_local_task": "gsb_local_task_response",
        "gsb_invariant_probe": "gsb_invariant_response",
        "rip_baseline_probe": "rip_baseline_response",
        "rip_induction_retrieval": "rip_induction_response",
        "rip_post_probe": "rip_post_response",
    }
    return mapping.get(stimulus_type, "response")
