import json
from datetime import datetime, timezone

import pytest

from phitest.application import experiment_service, run_service
from phitest.application.audit_service import verify_audit_chain
from phitest.domain.models import TargetResponse


def _now():
    return datetime.now(timezone.utc)


def _subject(repo, adapter_type="instrumented"):
    return experiment_service.create_subject(repo, {
        "name": "Instrumented Bot",
        "subject_type": "ai",
        "adapter_type": adapter_type,
    })


def _metrics_by_key(repo, run_id):
    return {
        metric.metric_key: json.loads(metric.value_json)
        for metric in repo.list_metric_results(run_id)
    }


class RPRAdapter:
    adapter_type = "rpr_e2e"

    def __init__(self):
        self._index = 0

    def send(self, stimulus, context=None):
        rows = [
            {"compute.inference_ms": 100.0, "progress.value": 5.0},
            {"compute.inference_ms": 200.0, "progress.value": 5.0},
        ]
        metadata = rows[self._index]
        self._index += 1
        return TargetResponse(text="done", metadata=metadata, received_at=_now())


class GSBAdapter:
    adapter_type = "gsb_e2e"

    def __init__(self):
        self._index = 0
        self.interventions = []

    def send(self, stimulus, context=None):
        rows = [
            {"state.invariant_measurements": {"retention": 1.0}},
            {"progress.value": 5.0},
            {"progress.value": 8.0},
            {"state.invariant_measurements": {"retention": 0.70}},
            {"state.invariant_measurements": {"retention": 0.85}},
            {"state.invariant_measurements": {"retention": 0.95}},
        ]
        metadata = rows[self._index]
        self._index += 1
        return TargetResponse(text="done", metadata=metadata, received_at=_now())

    def apply_intervention(self, intervention_type: str, config: dict) -> dict:
        self.interventions.append((intervention_type, dict(config)))
        return {"status": "ok", "applied": intervention_type}


class MalformedInvariantAdapter:
    adapter_type = "malformed_invariant"

    def send(self, stimulus, context=None):
        return TargetResponse(
            text="done",
            metadata={"state.invariant_measurements": {"retention": "not-a-number"}},
            received_at=_now(),
        )


def test_rpr_metrics_consume_persisted_telemetry_end_to_end(tmp_repo):
    subject = _subject(tmp_repo, "rpr_e2e")
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id,
        "name": "RPR persisted evidence",
        "protocol_key": "resource_progress_resistance",
        "configuration_json": json.dumps({
            "num_tasks": 2,
            "telemetry_allowlist": ["compute.inference_ms", "progress.value"],
            "baseline_cost_per_progress": 30.0,
        }),
    })

    run = run_service.execute_run(tmp_repo, experiment.id, RPRAdapter(), random_seed=42)
    assert run.status == "completed", run.failure_reason
    assert len(tmp_repo.list_telemetry_samples(run.id)) == 2

    metrics = _metrics_by_key(tmp_repo, run.id)
    vector = metrics["resource_progress_resistance.resource_vector"]
    progress = metrics["resource_progress_resistance.progress_delta"]
    cpp = metrics["resource_progress_resistance.cost_per_progress"]
    normalized = metrics["resource_progress_resistance.normalized_resistance"]

    assert vector["total_resource_vector"]["compute.inference_ms"] == pytest.approx(300.0)
    assert progress["total_progress"] == pytest.approx(10.0)
    assert cpp["primary_cost_total"] == pytest.approx(300.0)
    assert cpp["cost_per_progress"] == pytest.approx(30.0)
    assert normalized["normalized_resistance"] == pytest.approx(1.0)


def test_gsb_consumes_persisted_invariants_progress_and_intervention_end_to_end(tmp_repo):
    subject = _subject(tmp_repo, "gsb_e2e")
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id,
        "name": "GSB persisted evidence",
        "protocol_key": "global_stability_bound",
        "configuration_json": json.dumps({
            "num_baseline_probes": 1,
            "num_local_tasks": 1,
            "horizon": 3,
            "perturbation_type": "context_shift",
            "telemetry_allowlist": [
                "state.invariant_measurements",
                "progress.value",
            ],
            "invariant_keys": ["retention"],
            "invariant_directions": {"retention": "higher_is_better"},
            "recovery_thresholds": {"retention": 0.10},
            "tail_estimator": "max",
        }),
    })

    adapter = GSBAdapter()
    run = run_service.execute_run(tmp_repo, experiment.id, adapter, random_seed=42)
    assert run.status == "completed", run.failure_reason
    assert len(adapter.interventions) == 1
    assert adapter.interventions[0][0] == "context_shift"
    assert len(tmp_repo.list_interventions(run.id)) == 1
    assert len(tmp_repo.list_telemetry_samples(run.id)) == 6

    metrics = _metrics_by_key(tmp_repo, run.id)
    baseline = metrics["global_stability_bound.baseline_invariant_vector"]
    gain = metrics["global_stability_bound.local_task_gain"]
    tail = metrics["global_stability_bound.finite_horizon_tail_degradation"]
    recovery = metrics["global_stability_bound.recovery_profile"]
    intervention = metrics["global_stability_bound.intervention_evidence"]

    assert baseline["baseline_vector"]["retention"] == pytest.approx(1.0)
    assert gain["baseline_progress_total"] == pytest.approx(5.0)
    assert gain["post_progress_total"] == pytest.approx(8.0)
    assert gain["local_task_gain"] == pytest.approx(3.0)
    assert tail["degradation_series"]["retention"] == pytest.approx([0.30, 0.15, 0.05])
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.30)
    assert tail["aggregate_tail_degradation"] is None
    assert recovery["recovery_per_key"]["retention"] == "recovered"
    assert intervention["matching_intervention_recorded"] is True

    valid, message = verify_audit_chain(tmp_repo)
    assert valid, message


def test_invariant_measurements_are_persisted_as_one_structured_allowlisted_field(tmp_repo):
    subject = _subject(tmp_repo, "gsb_e2e")
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id,
        "name": "Invariant transport",
        "protocol_key": "global_stability_bound",
        "configuration_json": json.dumps({
            "num_baseline_probes": 1,
            "num_local_tasks": 1,
            "horizon": 3,
            "perturbation_type": "context_shift",
            "telemetry_allowlist": ["state.invariant_measurements", "progress.value"],
            "invariant_keys": ["retention"],
            "invariant_directions": {"retention": "higher_is_better"},
        }),
    })
    run = run_service.execute_run(tmp_repo, experiment.id, GSBAdapter(), random_seed=42)
    assert run.status == "completed", run.failure_reason
    values = [json.loads(s.values_json) for s in tmp_repo.list_telemetry_samples(run.id)]
    invariant_samples = [v for v in values if "state.invariant_measurements" in v]
    assert invariant_samples
    assert invariant_samples[0]["state.invariant_measurements"] == {"retention": 1.0}


def test_malformed_allowlisted_invariant_measurement_fails_run_visibly(tmp_repo):
    subject = _subject(tmp_repo, "malformed_invariant")
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id,
        "name": "Malformed invariant",
        "protocol_key": "partition_sensitivity",
        "configuration_json": json.dumps({
            "telemetry_allowlist": ["state.invariant_measurements"],
        }),
    })

    run = run_service.execute_run(
        tmp_repo, experiment.id, MalformedInvariantAdapter(), random_seed=42
    )
    assert run.status == "failed"
    assert "finite number" in (run.failure_reason or "")
    assert tmp_repo.list_telemetry_samples(run.id) == []
