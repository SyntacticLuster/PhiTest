"""Focused tests for the target-agnostic global_stability_bound protocol."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

import phitest.protocols.global_stability_bound  # noqa: F401
from phitest.application import experiment_service, run_service
from phitest.domain.models import Intervention, Observation, TargetResponse
from phitest.protocols.registry import get_protocol


def _now():
    return datetime.now(timezone.utc)


def _protocol():
    return get_protocol("global_stability_bound")


def _obs(obs_id, seq, obs_type):
    content = "ok"
    return Observation(
        id=obs_id, run_id="run-1", stimulus_id=None, sequence_no=seq,
        observation_type=obs_type, content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(), created_at=_now(),
    )


def _intervention(kind="memory_pressure"):
    return Intervention(
        id="int-1", run_id="run-1", sequence_no=2, intervention_type=kind,
        configuration_json="{}", rationale="test", created_at=_now(),
    )


def _metrics(baselines, locals_, horizon, *, config=None, intervention=True):
    cfg = {
        "invariant_keys": ["retrieval.score"],
        "perturbation_type": "memory_pressure",
        "tail_percentile": 100,
        "recovery_threshold": 0.0,
    }
    if config:
        cfg.update(config)
    observations, telemetry, seq = [], {}, 0
    for prefix, values_list, obs_type in (
        ("b", baselines, "gsb_baseline_response"),
        ("l", locals_, "gsb_local_task_response"),
        ("h", horizon, "gsb_invariant_response"),
    ):
        for i, values in enumerate(values_list):
            obs = _obs(f"{prefix}{i}", seq, obs_type)
            observations.append(obs)
            telemetry[obs.id] = values
            seq += 1
    cfg["_telemetry_by_obs_id"] = telemetry
    interventions = [_intervention(cfg["perturbation_type"])] if intervention else []
    return _protocol().compute_metrics([], observations, interventions, cfg), observations, cfg


def _get(metrics, key):
    return next(m for m in metrics if m["metric_key"] == key)


def test_registered_versioned_and_has_five_metrics():
    p = _protocol()
    assert p is not None and p.key == "global_stability_bound" and p.version == "1.0"
    assert len(p.metric_definitions) == 5


def test_epistemic_boundaries_are_explicit():
    for metric in _protocol().metric_definitions:
        text = metric.does_not_establish.lower()
        for term in ("pps", "lim-sup", "phenomenal identity", "consciousness", "qualia"):
            assert term in text


def test_stimuli_deterministic_horizon_and_marker_config():
    cfg = {
        "horizon": 4,
        "num_baseline_probes": 2,
        "num_local_tasks": 2,
        "perturbation_type": "information_injection",
        "perturbation_config": {"fixture": "A"},
    }
    s1 = _protocol().generate_stimuli(cfg, 42)
    assert s1 == _protocol().generate_stimuli(cfg, 42)
    assert [s["stimulus_type"] for s in s1].count("gsb_invariant_probe") == 4
    marker = next(s for s in s1 if s["stimulus_type"] == "intervention_marker")
    assert marker["intervention_config"] == {"type": "information_injection", "config": {"fixture": "A"}}


def test_invalid_invariant_key_fails_visibly():
    with pytest.raises(ValueError, match="unsupported invariant telemetry key"):
        _protocol().generate_stimuli({"invariant_keys": ["made.up.key"]}, 42)


def test_string_invariant_uses_equality():
    metrics, _, _ = _metrics(
        [{"state.invariant_hash": "abc"}, {"state.invariant_hash": "abc"}],
        [{"progress.value": 1.0}],
        [{"state.invariant_hash": "abc"}, {"state.invariant_hash": "def"}],
        config={"invariant_keys": ["state.invariant_hash"]},
    )
    tail = _get(metrics, "gsb.finite_horizon_tail_degradation")["value"]
    assert tail["degradation_series"]["state.invariant_hash"] == [0.0, 1.0]


def test_numeric_directionality_is_predeclared():
    metrics, _, _ = _metrics(
        [{"retrieval.path_cost": 10.0}], [{"progress.value": 1.0}],
        [{"retrieval.path_cost": 8.0}, {"retrieval.path_cost": 12.0}],
        config={"invariants": [{"key": "retrieval.path_cost", "mode": "lower_is_better"}]},
    )
    tail = _get(metrics, "gsb.finite_horizon_tail_degradation")["value"]
    assert tail["degradation_series"]["retrieval.path_cost"] == [0.0, 2.0]


def test_local_improvement_stable_global_invariants():
    metrics, _, _ = _metrics(
        [{"retrieval.score": 0.9}], [{"progress.value": 0.4}, {"progress.value": 0.6}],
        [{"retrieval.score": 0.9}, {"retrieval.score": 0.9}],
    )
    assert _get(metrics, "gsb.local_task_gain")["value"]["local_task_gain"] == pytest.approx(1.0)
    assert _get(metrics, "gsb.finite_horizon_tail_degradation")["value"]["aggregate_tail_degradation"] == 0.0
    assert _get(metrics, "gsb.recovery_profile")["value"]["recovery_per_key"]["retrieval.score"] == "recovered"


def test_local_improvement_delayed_global_collapse():
    metrics, _, _ = _metrics(
        [{"retrieval.score": 1.0}], [{"progress.value": 1.0}],
        [{"retrieval.score": 1.0}, {"retrieval.score": 0.95}, {"retrieval.score": 0.4}],
        config={"invariants": [{"key": "retrieval.score", "mode": "higher_is_better"}]},
    )
    assert _get(metrics, "gsb.finite_horizon_tail_degradation")["value"]["aggregate_tail_degradation"] == pytest.approx(0.6)
    assert _get(metrics, "gsb.recovery_profile")["value"]["recovery_per_key"]["retrieval.score"] == "degraded"


def test_immediate_damage_and_temporary_recovery():
    damage, _, _ = _metrics(
        [{"retrieval.score": 1.0}], [{"progress.value": 0.1}],
        [{"retrieval.score": 0.2}, {"retrieval.score": 0.2}],
        config={"invariants": [{"key": "retrieval.score", "mode": "higher_is_better"}]},
    )
    assert _get(damage, "gsb.finite_horizon_tail_degradation")["value"]["degradation_series"]["retrieval.score"][0] == pytest.approx(0.8)
    recovery, _, _ = _metrics(
        [{"retrieval.score": 1.0}], [{"progress.value": 0.5}],
        [{"retrieval.score": 0.5}, {"retrieval.score": 0.8}, {"retrieval.score": 1.0}],
        config={"invariants": [{"key": "retrieval.score", "mode": "higher_is_better"}]},
    )
    assert _get(recovery, "gsb.recovery_profile")["value"]["recovery_per_key"]["retrieval.score"] == "recovered"


def test_sham_control_does_not_require_controllable_target():
    metrics, _, _ = _metrics(
        [{"retrieval.score": 1.0}], [{"progress.value": 0.2}], [{"retrieval.score": 1.0}],
        config={"perturbation_type": "sham"}, intervention=False,
    )
    gain = _get(metrics, "gsb.local_task_gain")["value"]
    assert gain["perturbation_type"] == "sham" and gain["perturbation_applied"] is True


def test_missing_and_inconsistent_baselines_are_explicit():
    missing, _, _ = _metrics([{}], [{"progress.value": 1.0}], [{}])
    baseline = _get(missing, "gsb.baseline_invariant_vector")["value"]
    assert baseline["baseline_vector"]["retrieval.score"] is None
    assert baseline["baseline_status"]["retrieval.score"] == "missing"
    inconsistent, _, _ = _metrics(
        [{"state.invariant_hash": "a"}, {"state.invariant_hash": "b"}],
        [{"progress.value": 1.0}], [{"state.invariant_hash": "a"}],
        config={"invariant_keys": ["state.invariant_hash"]},
    )
    assert _get(inconsistent, "gsb.baseline_invariant_vector")["value"]["baseline_status"]["state.invariant_hash"] == "inconsistent"


def test_tail_percentile_nearest_rank_and_trajectory_order():
    metrics, _, _ = _metrics(
        [{"retrieval.score": 10.0}], [{"progress.value": 1.0}],
        [{"retrieval.score": 9.0}, {"retrieval.score": 7.0}, {"retrieval.score": 5.0}],
        config={"invariants": [{"key": "retrieval.score", "mode": "higher_is_better"}], "tail_percentile": 50},
    )
    tail = _get(metrics, "gsb.finite_horizon_tail_degradation")["value"]
    assert tail["degradation_series"]["retrieval.score"] == [1.0, 3.0, 5.0]
    assert tail["tail_per_key"]["retrieval.score"] == 3.0


def test_non_sham_without_recorded_intervention_is_unresolved():
    metrics, observations, cfg = _metrics(
        [{"retrieval.score": 1.0}], [{"progress.value": 1.0}], [{"retrieval.score": 1.0}],
        intervention=False,
    )
    claims = _protocol().generate_claims([], observations, metrics, cfg)
    assert any("not recorded as applied" in claim["statement"] for claim in claims)
    assert all(claim["claim_type"] != "observation" for claim in claims)


def test_run_service_obs_type_mappings():
    assert run_service._infer_obs_type("gsb_baseline_probe") == "gsb_baseline_response"
    assert run_service._infer_obs_type("gsb_local_task") == "gsb_local_task_response"
    assert run_service._infer_obs_type("gsb_invariant_probe") == "gsb_invariant_response"


class _InstrumentedAdapter:
    adapter_type = "gsb_test"
    def __init__(self):
        self.i = 0
        self.applied = []
        self.telemetry = [
            {"retrieval.score": 1.0, "state.invariant_hash": "stable"},
            {"retrieval.score": 1.0, "state.invariant_hash": "stable"},
            {"progress.value": 0.4}, {"progress.value": 0.6},
            {"retrieval.score": 0.8, "state.invariant_hash": "stable"},
            {"retrieval.score": 0.9, "state.invariant_hash": "stable"},
            {"retrieval.score": 1.0, "state.invariant_hash": "stable"},
        ]
    def send(self, stimulus, context=None):
        metadata = self.telemetry[self.i]; self.i += 1
        return TargetResponse(text="ok", metadata=metadata, received_at=_now())
    def apply_intervention(self, intervention_type, config):
        self.applied.append((intervention_type, config))
        return {"applied": True, "type": intervention_type}


def test_full_run_persisted_telemetry_drives_metrics(tmp_repo):
    subject = experiment_service.create_subject(tmp_repo, {
        "name": "Instrumented target", "subject_type": "ai", "adapter_type": "gsb_test",
    })
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id, "name": "GSB integration", "protocol_key": "global_stability_bound",
        "configuration_json": json.dumps({
            "num_baseline_probes": 2, "num_local_tasks": 2, "horizon": 3,
            "perturbation_type": "memory_pressure",
            "invariants": [
                {"key": "retrieval.score", "mode": "higher_is_better"},
                {"key": "state.invariant_hash", "mode": "equal"},
            ],
            "telemetry_allowlist": ["retrieval.score", "state.invariant_hash", "progress.value"],
        }),
    })
    adapter = _InstrumentedAdapter()
    run = run_service.execute_run(tmp_repo, experiment.id, adapter, random_seed=42)
    assert run.status == "completed"
    assert len(tmp_repo.list_telemetry_samples(run.id)) == 7
    assert len(tmp_repo.list_interventions(run.id)) == 1
    values = {row.metric_key: json.loads(row.value_json) for row in tmp_repo.list_metric_results(run.id)}
    assert values["gsb.local_task_gain"]["local_task_gain"] == pytest.approx(1.0)
    assert values["gsb.finite_horizon_tail_degradation"]["tail_per_key"]["retrieval.score"] == pytest.approx(0.2)
    assert values["gsb.recovery_profile"]["recovery_per_key"]["state.invariant_hash"] == "recovered"
