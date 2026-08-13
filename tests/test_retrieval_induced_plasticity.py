"""Focused tests for the target-agnostic retrieval_induced_plasticity protocol."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

import phitest.protocols.retrieval_induced_plasticity  # noqa: F401
from phitest.application import experiment_service, run_service
from phitest.domain.models import Observation, TargetResponse
from phitest.protocols.registry import get_protocol


def _now():
    return datetime.now(timezone.utc)


def _protocol():
    return get_protocol("retrieval_induced_plasticity")


def _obs(obs_id, seq, obs_type):
    content = "ok"
    return Observation(
        id=obs_id,
        run_id="run-1",
        stimulus_id=None,
        sequence_no=seq,
        observation_type=obs_type,
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        created_at=_now(),
    )


ITEMS = [
    {"target_id": "A", "role": "induced", "query": "Retrieve A."},
    {"target_id": "B", "role": "related_control", "query": "Retrieve B."},
    {"target_id": "C", "role": "unrelated_control", "query": "Retrieve C."},
]


def _metrics(rows, *, config=None):
    cfg = {
        "items": ITEMS,
        "retrieval_metric_key": "retrieval.score",
        "metric_mode": "higher_is_better",
    }
    if config:
        cfg.update(config)
    observations = []
    telemetry = {}
    for i, (obs_type, target_id, value) in enumerate(rows):
        obs = _obs(f"o{i}", i, obs_type)
        observations.append(obs)
        payload = {}
        if target_id is not None:
            payload["retrieval.target_id"] = target_id
        if value is not None:
            payload[cfg["retrieval_metric_key"]] = value
        telemetry[obs.id] = payload
    cfg["_telemetry_by_obs_id"] = telemetry
    return _protocol().compute_metrics([], observations, [], cfg), observations, cfg


def _get(metrics, key):
    return next(m for m in metrics if m["metric_key"] == key)


def test_registered_versioned_and_has_five_metrics():
    p = _protocol()
    assert p is not None
    assert p.key == "retrieval_induced_plasticity"
    assert p.version == "1.0"
    assert len(p.metric_definitions) == 5


def test_epistemic_boundaries_are_explicit():
    for metric in _protocol().metric_definitions:
        text = metric.does_not_establish.lower()
        for term in ("synaptic plasticity", "causal memory mechanism", "subjective memory", "consciousness", "qualia"):
            assert term in text


def test_stimulus_generation_is_deterministic_and_balanced():
    cfg = {
        "items": ITEMS,
        "baseline_repetitions": 2,
        "induction_repetitions": 3,
        "post_repetitions": 2,
    }
    s1 = _protocol().generate_stimuli(cfg, 42)
    s2 = _protocol().generate_stimuli(cfg, 42)
    assert s1 == s2
    types = [s["stimulus_type"] for s in s1]
    assert types.count("rip_baseline_probe") == 6
    assert types.count("rip_induction_retrieval") == 3
    assert types.count("rip_post_probe") == 6
    assert [s["sequence_no"] for s in s1] == list(range(len(s1)))


def test_invalid_item_configuration_fails_visibly():
    with pytest.raises(ValueError, match="induced"):
        _protocol().generate_stimuli({
            "items": [{"target_id": "C", "role": "unrelated_control", "query": "C"}]
        }, 42)
    with pytest.raises(ValueError, match="duplicate target_id"):
        _protocol().generate_stimuli({
            "items": [
                {"target_id": "A", "role": "induced", "query": "A"},
                {"target_id": "A", "role": "unrelated_control", "query": "A"},
            ]
        }, 42)


def test_unsupported_retrieval_metric_fails_visibly():
    with pytest.raises(ValueError, match="unsupported retrieval metric key"):
        _protocol().generate_stimuli({
            "items": ITEMS,
            "retrieval_metric_key": "memory.writes",
        }, 42)


def test_higher_is_better_signed_delta():
    metrics, _, _ = _metrics([
        ("rip_baseline_response", "A", 0.5),
        ("rip_baseline_response", "C", 0.7),
        ("rip_induction_response", "A", 0.6),
        ("rip_post_response", "A", 0.9),
        ("rip_post_response", "C", 0.7),
    ], config={
        "items": [
            {"target_id": "A", "role": "induced", "query": "A"},
            {"target_id": "C", "role": "unrelated_control", "query": "C"},
        ],
    })
    delta = _get(metrics, "rip.item_plasticity_delta")["value"]["per_item"]
    assert delta["A"]["signed_improvement"] == pytest.approx(0.4)
    assert delta["C"]["signed_improvement"] == pytest.approx(0.0)


def test_lower_is_better_signed_delta():
    metrics, _, _ = _metrics([
        ("rip_baseline_response", "A", 10.0),
        ("rip_baseline_response", "C", 10.0),
        ("rip_induction_response", "A", 8.0),
        ("rip_post_response", "A", 6.0),
        ("rip_post_response", "C", 10.0),
    ], config={
        "items": [
            {"target_id": "A", "role": "induced", "query": "A"},
            {"target_id": "C", "role": "unrelated_control", "query": "C"},
        ],
        "retrieval_metric_key": "retrieval.path_cost",
        "metric_mode": "lower_is_better",
    })
    delta = _get(metrics, "rip.item_plasticity_delta")["value"]["per_item"]
    assert delta["A"]["signed_improvement"] == pytest.approx(4.0)
    assert delta["C"]["signed_improvement"] == pytest.approx(0.0)


def test_target_gain_and_related_suppression_are_separate_contrasts():
    metrics, _, _ = _metrics([
        ("rip_baseline_response", "A", 0.5),
        ("rip_baseline_response", "B", 0.8),
        ("rip_baseline_response", "C", 0.7),
        ("rip_induction_response", "A", 0.6),
        ("rip_induction_response", "A", 0.7),
        ("rip_post_response", "A", 0.9),
        ("rip_post_response", "B", 0.6),
        ("rip_post_response", "C", 0.7),
    ])
    contrast = _get(metrics, "rip.role_contrast")["value"]
    assert contrast["role_mean_signed_improvement"]["induced"] == pytest.approx(0.4)
    assert contrast["role_mean_signed_improvement"]["related_control"] == pytest.approx(-0.2)
    assert contrast["role_mean_signed_improvement"]["unrelated_control"] == pytest.approx(0.0)
    assert contrast["contrasts"]["induced_minus_unrelated"] == pytest.approx(0.4)
    assert contrast["contrasts"]["related_minus_unrelated"] == pytest.approx(-0.2)


def test_common_drift_is_removed_by_role_contrast():
    metrics, _, _ = _metrics([
        ("rip_baseline_response", "A", 0.5),
        ("rip_baseline_response", "C", 0.5),
        ("rip_induction_response", "A", 0.6),
        ("rip_post_response", "A", 0.6),
        ("rip_post_response", "C", 0.6),
    ], config={
        "items": [
            {"target_id": "A", "role": "induced", "query": "A"},
            {"target_id": "C", "role": "unrelated_control", "query": "C"},
        ],
    })
    contrast = _get(metrics, "rip.role_contrast")["value"]["contrasts"]
    assert contrast["induced_minus_unrelated"] == pytest.approx(0.0)


def test_missing_or_unknown_telemetry_is_explicit():
    metrics, observations, cfg = _metrics([
        ("rip_baseline_response", None, 0.5),
        ("rip_baseline_response", "UNKNOWN", 0.7),
        ("rip_baseline_response", "A", None),
        ("rip_post_response", "A", 0.9),
    ], config={
        "items": [
            {"target_id": "A", "role": "induced", "query": "A"},
            {"target_id": "C", "role": "unrelated_control", "query": "C"},
        ],
    })
    baseline = _get(metrics, "rip.baseline_retrieval_profile")["value"]
    assert baseline["missing_target_id_count"] == 1
    assert baseline["unknown_target_id_count"] == 1
    assert baseline["missing_metric_count"] == 1
    assert baseline["per_item"]["A"]["mean"] is None
    claims = _protocol().generate_claims([], observations, metrics, cfg)
    assert any(c["claim_type"] == "unresolved" and "lack usable pre/post" in c["statement"] for c in claims)


def test_missing_induction_is_unresolved():
    metrics, observations, cfg = _metrics([
        ("rip_baseline_response", "A", 0.5),
        ("rip_baseline_response", "C", 0.5),
        ("rip_post_response", "A", 0.6),
        ("rip_post_response", "C", 0.5),
    ], config={
        "items": [
            {"target_id": "A", "role": "induced", "query": "A"},
            {"target_id": "C", "role": "unrelated_control", "query": "C"},
        ],
    })
    claims = _protocol().generate_claims([], observations, metrics, cfg)
    assert any(c["claim_type"] == "unresolved" and "No usable selective-retrieval induction" in c["statement"] for c in claims)


def test_run_service_obs_type_mappings():
    assert run_service._infer_obs_type("rip_baseline_probe") == "rip_baseline_response"
    assert run_service._infer_obs_type("rip_induction_retrieval") == "rip_induction_response"
    assert run_service._infer_obs_type("rip_post_probe") == "rip_post_response"


class _InstrumentedAdapter:
    adapter_type = "rip_test"

    def __init__(self):
        self.calls = {"A": 0, "B": 0, "C": 0}
        self.series = {
            "A": [0.5, 0.6, 0.7, 0.9],
            "B": [0.8, 0.6],
            "C": [0.7, 0.7],
        }

    def send(self, stimulus, context=None):
        target_id = stimulus.split()[-1].rstrip(".")
        i = self.calls[target_id]
        self.calls[target_id] += 1
        return TargetResponse(
            text="ok",
            metadata={
                "retrieval.target_id": target_id,
                "retrieval.score": self.series[target_id][i],
            },
            received_at=_now(),
        )


def test_full_run_persisted_telemetry_drives_metrics(tmp_repo):
    subject = experiment_service.create_subject(tmp_repo, {
        "name": "Instrumented target",
        "subject_type": "ai",
        "adapter_type": "rip_test",
    })
    experiment = experiment_service.create_experiment(tmp_repo, {
        "subject_id": subject.id,
        "name": "RIP integration",
        "protocol_key": "retrieval_induced_plasticity",
        "configuration_json": json.dumps({
            "items": [
                {"target_id": "A", "role": "induced", "query": "Retrieve A."},
                {"target_id": "B", "role": "related_control", "query": "Retrieve B."},
                {"target_id": "C", "role": "unrelated_control", "query": "Retrieve C."},
            ],
            "baseline_repetitions": 1,
            "induction_repetitions": 2,
            "post_repetitions": 1,
            "retrieval_metric_key": "retrieval.score",
            "telemetry_allowlist": ["retrieval.target_id", "retrieval.score"],
        }),
    })
    run = run_service.execute_run(tmp_repo, experiment.id, _InstrumentedAdapter(), random_seed=42)
    assert run.status == "completed"
    assert len(tmp_repo.list_telemetry_samples(run.id)) == 8
    values = {
        row.metric_key: json.loads(row.value_json)
        for row in tmp_repo.list_metric_results(run.id)
    }
    assert values["rip.item_plasticity_delta"]["per_item"]["A"]["signed_improvement"] == pytest.approx(0.4)
    assert values["rip.role_contrast"]["contrasts"]["induced_minus_unrelated"] == pytest.approx(0.4)
    assert values["rip.role_contrast"]["contrasts"]["related_minus_unrelated"] == pytest.approx(-0.2)
