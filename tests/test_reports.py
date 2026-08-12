import json
import pytest
from phitest.application import experiment_service, run_service, report_service
from phitest.adapters.manual_target import ManualTarget

FORBIDDEN_FIELDS = [
    "qualia_detected", "qualia detected",
    "consciousness_probability", "consciousness probability",
    "consciousness score", "sentience score", "sentience gauge",
    "consciousness meter", "agi score",
    "phenomenal_experience_confirmed", "agi_score",
    "conscious = true",
]


def _run_and_report(repo, protocol_key="partition_sensitivity"):
    s = experiment_service.create_subject(repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(repo, {
        "subject_id": s.id, "name": "E", "protocol_key": protocol_key,
        "theory_keys_json": '["integration"]',
    })
    adapter = ManualTarget("response")
    run = run_service.execute_run(repo, e.id, adapter, random_seed=42)
    return report_service.generate_report(repo, run.id)


def test_report_generated(tmp_repo):
    report = _run_and_report(tmp_repo)
    assert report["run"] is not None
    assert report["epistemic_boundary"]


def test_report_has_epistemic_boundary(tmp_repo):
    report = _run_and_report(tmp_repo)
    boundary = report["epistemic_boundary"]
    assert "phenomenal consciousness" in boundary.lower()
    assert "qualia" in boundary.lower()
    assert "do not constitute" in boundary.lower()


def test_report_no_forbidden_fields(tmp_repo):
    report = _run_and_report(tmp_repo)
    report_str = json.dumps(report, default=str).lower()
    for field in FORBIDDEN_FIELDS:
        assert field not in report_str, f"Forbidden field found in report: {field}"


def test_claims_preserve_epistemic_type(tmp_repo):
    report = _run_and_report(tmp_repo)
    claims = report["claims"]
    allowed_types = {
        "observation", "operational_metric", "theory_prediction",
        "inference", "self_report", "unresolved",
    }
    for c in claims:
        assert c.claim_type in allowed_types, f"Invalid claim type: {c.claim_type}"


def test_self_reports_not_labeled_phenomenal_evidence(tmp_repo):
    report = _run_and_report(tmp_repo, "phenomenal_report_consistency")
    self_reports = report["self_reports"]
    for c in self_reports:
        assert "phenomenal experience" not in c.statement.lower() or \
               "not" in c.statement.lower() or "classified as" in c.statement.lower()


def test_no_consciousness_verdict_in_claims(tmp_repo):
    report = _run_and_report(tmp_repo)
    for c in report["claims"]:
        stmt = c.statement.lower()
        assert "conscious = true" not in stmt
        assert "qualia detected" not in stmt
        assert "consciousness probability" not in stmt


def test_report_all_six_protocols(tmp_repo):
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
            "subject_id": s.id, "name": f"E-{pk}", "protocol_key": pk,
        })
        adapter = ManualTarget("response")
        run = run_service.execute_run(repo=tmp_repo, experiment_id=e.id,
                                      adapter=adapter, random_seed=42)
        report = report_service.generate_report(tmp_repo, run.id)
        report_str = json.dumps(report, default=str).lower()
        for field in FORBIDDEN_FIELDS:
            assert field not in report_str, \
                f"Forbidden field '{field}' in report for protocol {pk}"
