import json
import pytest
from phitest.application import experiment_service, run_service
from phitest.adapters.manual_target import ManualTarget


def _setup(repo, protocol_key="partition_sensitivity"):
    s = experiment_service.create_subject(repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(repo, {
        "subject_id": s.id, "name": "Exp",
        "protocol_key": protocol_key,
        "theory_keys_json": '["integration"]',
    })
    return s, e


def test_successful_manual_run(tmp_repo):
    s, e = _setup(tmp_repo)
    adapter = ManualTarget("Test response")
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    stimuli = tmp_repo.list_stimuli(run.id)
    assert len(stimuli) > 0
    observations = tmp_repo.list_observations(run.id)
    assert len(observations) > 0
    metrics = tmp_repo.list_metric_results(run.id)
    assert len(metrics) > 0
    claims = tmp_repo.list_evidence_claims(run.id)
    assert len(claims) > 0


def test_failed_target_preserves_partial_evidence(tmp_repo):
    from phitest.domain.errors import AdapterError

    class FailingAdapter:
        adapter_type = "failing"
        def send(self, stimulus, context=None):
            raise AdapterError("simulated failure")

    s, e = _setup(tmp_repo)
    run = run_service.execute_run(tmp_repo, e.id, FailingAdapter(), random_seed=42)
    assert run.status == "failed"
    assert run.failure_reason
    # At least the first stimulus should be recorded before failure
    stimuli = tmp_repo.list_stimuli(run.id)
    assert len(stimuli) >= 1


def test_run_status_transitions(tmp_repo):
    s, e = _setup(tmp_repo)
    adapter = ManualTarget("ok")
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=1)
    assert run.status in ("completed", "failed")
    assert run.completed_at is not None


def test_metrics_computed_on_completion(tmp_repo):
    s, e = _setup(tmp_repo)
    adapter = ManualTarget("answer")
    run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
    assert run.status == "completed"
    metrics = tmp_repo.list_metric_results(run.id)
    assert any("partition_sensitivity" in m.metric_key for m in metrics)


def test_all_six_protocols_run(tmp_repo):
    protocols = [
        "partition_sensitivity", "global_availability",
        "metacognitive_calibration", "self_model_continuity",
        "phenomenal_report_consistency", "perturbation_response",
    ]
    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    for pk in protocols:
        e = experiment_service.create_experiment(tmp_repo, {
            "subject_id": s.id, "name": f"Exp-{pk}", "protocol_key": pk,
        })
        adapter = ManualTarget("response")
        run = run_service.execute_run(tmp_repo, e.id, adapter, random_seed=42)
        assert run.status == "completed", f"Protocol {pk} run failed: {run.failure_reason}"
