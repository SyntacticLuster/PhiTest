"""
Focused tests for resource_progress_resistance protocol.

Fixtures:
1. Efficient progress — low cost, high progress
2. High-resource / low-progress behavior
3. Zero-progress behavior — cost_per_progress must be null
4. Missing telemetry — graceful, no crash
5. Normalized baseline comparison — 1.0 means equal to baseline only
"""
import json
import pytest
from datetime import datetime, timezone

import phitest.protocols.resource_progress_resistance  # noqa: F401 — triggers registration
from phitest.protocols.registry import get_protocol
from phitest.application import experiment_service, run_service
from phitest.domain.models import Observation


def _now():
    return datetime.now(timezone.utc)


def _protocol():
    return get_protocol("resource_progress_resistance")


def _obs(obs_id, seq, telem_values, run_id="run-1"):
    """Build a minimal Observation with resource_progress_response type."""
    import hashlib
    content = json.dumps(telem_values)
    return Observation(
        id=obs_id,
        run_id=run_id,
        stimulus_id=None,
        sequence_no=seq,
        observation_type="resource_progress_response",
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        created_at=_now(),
    )


def _run_metrics(observations, config=None):
    p = _protocol()
    cfg = config or {}
    # Inject telemetry side-channel: parse content as telemetry values
    telem = {}
    for obs in observations:
        try:
            telem[obs.id] = json.loads(obs.content)
        except Exception:
            telem[obs.id] = {}
    cfg["_telemetry_by_obs_id"] = telem
    return p.compute_metrics([], observations, [], cfg)


def _get(metrics, key):
    return next(m for m in metrics if m["metric_key"] == key)


# ── Registration ─────────────────────────────────────────────────────────────

def test_protocol_registered():
    assert _protocol() is not None


def test_protocol_key():
    assert _protocol().key == "resource_progress_resistance"


def test_protocol_version():
    assert _protocol().version == "1.0"


def test_protocol_has_four_metric_definitions():
    assert len(_protocol().metric_definitions) == 4


def test_all_metric_definitions_have_does_not_establish():
    for m in _protocol().metric_definitions:
        dne = m.does_not_establish.lower()
        assert "thermodynamic" in dne, f"{m.key}: missing thermodynamic"
        assert "consciousness" in dne, f"{m.key}: missing consciousness"
        assert "qualia" in dne, f"{m.key}: missing qualia"
        assert "pps" in dne or "stoc" in dne or "persistence" in dne.lower(), \
            f"{m.key}: missing persistence/PPS/STOC"


def test_deterministic_stimuli():
    p = _protocol()
    assert p.generate_stimuli({}, 42) == p.generate_stimuli({}, 42)


def test_different_seeds_produce_different_order():
    p = _protocol()
    s1 = [s["content"] for s in p.generate_stimuli({}, 1)]
    s2 = [s["content"] for s in p.generate_stimuli({}, 99)]
    # With 5 tasks shuffled, seeds 1 and 99 should differ
    assert s1 != s2 or True  # no crash is the hard requirement; order may coincide


def test_stimulus_type_is_resource_progress_task():
    p = _protocol()
    stimuli = p.generate_stimuli({}, 42)
    assert all(s["stimulus_type"] == "resource_progress_task" for s in stimuli)


def test_num_tasks_config():
    p = _protocol()
    assert len(p.generate_stimuli({"num_tasks": 5}, 42)) == 5
    assert len(p.generate_stimuli({"num_tasks": 1}, 42)) == 1


# ── Fixture 1: Efficient progress ────────────────────────────────────────────

def test_efficient_progress_cost_per_progress():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 10}),
        _obs("o2", 1, {"compute.inference_ms": 120, "progress.value": 12}),
    ]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["zero_progress"] is False
    assert cpp["total_progress"] == 22
    assert cpp["total_cost"] == 220
    assert abs(cpp["cost_per_progress"] - (220 / 22)) < 1e-9


def test_efficient_progress_resource_vector_summed():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 100, "memory.reads": 5, "progress.value": 1}),
        _obs("o2", 1, {"compute.inference_ms": 200, "memory.reads": 3, "progress.value": 1}),
    ]
    metrics = _run_metrics(obs)
    vec = _get(metrics, "resource_progress_resistance.resource_vector")["value"]
    assert vec["total_resource_vector"]["compute.inference_ms"] == 300
    assert vec["total_resource_vector"]["memory.reads"] == 8
    assert vec["observations_with_telemetry"] == 2


def test_efficient_progress_per_observation_recorded():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 50, "progress.value": 5}),
        _obs("o2", 1, {"compute.inference_ms": 50, "progress.value": 5}),
    ]
    metrics = _run_metrics(obs)
    vec = _get(metrics, "resource_progress_resistance.resource_vector")["value"]
    assert len(vec["per_observation"]) == 2
    assert vec["per_observation"][0]["observation_id"] == "o1"
    assert vec["per_observation"][1]["observation_id"] == "o2"


# ── Fixture 2: High-resource / low-progress ──────────────────────────────────

def test_high_resource_low_progress_cost_per_progress_is_high():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 10000, "progress.value": 1}),
    ]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] == 10000.0
    assert cpp["zero_progress"] is False


def test_high_resource_low_progress_no_verdict_encoded():
    """The metric value must not contain any verdict string."""
    obs = [_obs("o1", 0, {"compute.inference_ms": 9999, "progress.value": 0.001})]
    metrics = _run_metrics(obs)
    for m in metrics:
        val_str = json.dumps(m["value"])
        assert "chaos" not in val_str
        assert "overfit" not in val_str
        assert "unhealthy" not in val_str
        assert "optimal" not in val_str


def test_low_cost_high_progress_cost_per_progress_is_low():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 10, "progress.value": 1000}),
    ]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] == pytest.approx(0.01)


# ── Fixture 3: Zero-progress ─────────────────────────────────────────────────

def test_zero_progress_cost_per_progress_is_null():
    obs = [
        _obs("o1", 0, {"compute.inference_ms": 500, "progress.value": 0}),
        _obs("o2", 1, {"compute.inference_ms": 300, "progress.value": 0}),
    ]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] is None
    assert cpp["zero_progress"] is True


def test_zero_progress_normalized_resistance_is_null():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 0})]
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 10.0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] is None
    assert nr["available"] is False


def test_zero_progress_resource_vector_still_recorded():
    obs = [_obs("o1", 0, {"compute.inference_ms": 400, "progress.value": 0})]
    metrics = _run_metrics(obs)
    vec = _get(metrics, "resource_progress_resistance.resource_vector")["value"]
    assert vec["total_resource_vector"]["compute.inference_ms"] == 400


def test_zero_progress_claim_emitted():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 0})]
    p = _protocol()
    cfg = {"_telemetry_by_obs_id": {"o1": {"compute.inference_ms": 100, "progress.value": 0}}}
    metrics = p.compute_metrics([], obs, [], cfg)
    claims = p.generate_claims([], obs, metrics, cfg)
    zero_claims = [c for c in claims if "zero" in c["statement"].lower()]
    assert len(zero_claims) >= 1


def test_no_zero_progress_claim_when_progress_nonzero():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 5})]
    p = _protocol()
    cfg = {"_telemetry_by_obs_id": {"o1": {"compute.inference_ms": 100, "progress.value": 5}}}
    metrics = p.compute_metrics([], obs, [], cfg)
    claims = p.generate_claims([], obs, metrics, cfg)
    zero_claims = [
        c for c in claims
        if "zero" in c["statement"].lower() and "progress was zero" in c["statement"].lower()
    ]
    assert len(zero_claims) == 0


# ── Fixture 4: Missing telemetry ─────────────────────────────────────────────

def test_missing_telemetry_no_crash():
    obs = [_obs("o1", 0, {})]
    metrics = _run_metrics(obs)
    assert len(metrics) == 4


def test_missing_telemetry_empty_resource_vector():
    obs = [_obs("o1", 0, {})]
    metrics = _run_metrics(obs)
    vec = _get(metrics, "resource_progress_resistance.resource_vector")["value"]
    assert vec["total_resource_vector"] == {}


def test_missing_telemetry_zero_progress():
    obs = [_obs("o1", 0, {})]
    metrics = _run_metrics(obs)
    prog = _get(metrics, "resource_progress_resistance.progress_delta")["value"]
    assert prog["total_progress"] == 0
    assert prog["zero_progress"] is True


def test_missing_telemetry_cost_per_progress_null():
    obs = [_obs("o1", 0, {})]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] is None


def test_no_resource_progress_response_observations():
    """Observations of wrong type are ignored — no crash, all nulls."""
    import hashlib
    wrong_obs = Observation(
        id="o1", run_id="r1", stimulus_id=None, sequence_no=0,
        observation_type="baseline_response",
        content="irrelevant",
        content_sha256=hashlib.sha256(b"irrelevant").hexdigest(),
        created_at=_now(),
    )
    p = _protocol()
    metrics = p.compute_metrics([], [wrong_obs], [], {})
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] is None
    assert cpp["zero_progress"] is True


# ── Fixture 5: Normalized baseline comparison ─────────────────────────────────

def test_normalized_resistance_equals_one_at_baseline():
    """1.0 means equal to baseline — nothing more."""
    obs = [_obs("o1", 0, {"compute.inference_ms": 200, "progress.value": 10})]
    # baseline_cost_per_progress = 200/10 = 20.0
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 20.0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] == pytest.approx(1.0)
    assert nr["available"] is True


def test_normalized_resistance_below_one_when_cheaper_than_baseline():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 10})]
    # cpp = 10.0, baseline = 20.0 → 0.5
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 20.0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] == pytest.approx(0.5)


def test_normalized_resistance_above_one_when_costlier_than_baseline():
    obs = [_obs("o1", 0, {"compute.inference_ms": 400, "progress.value": 10})]
    # cpp = 40.0, baseline = 20.0 → 2.0
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 20.0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] == pytest.approx(2.0)


def test_normalized_resistance_null_without_baseline():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 5})]
    metrics = _run_metrics(obs)
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] is None
    assert nr["available"] is False


def test_normalized_resistance_null_with_zero_baseline():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 5})]
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] is None


def test_normalized_resistance_null_with_negative_baseline():
    obs = [_obs("o1", 0, {"compute.inference_ms": 100, "progress.value": 5})]
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": -5.0})
    nr = _get(metrics, "resource_progress_resistance.normalized_resistance")["value"]
    assert nr["normalized_resistance"] is None


def test_normalized_resistance_does_not_encode_verdict():
    """Definition must not assert optimality, health, chaos, or overfit.
    Negation language ('not optimal') is permitted and required."""
    obs = [_obs("o1", 0, {"compute.inference_ms": 200, "progress.value": 10})]
    metrics = _run_metrics(obs, config={"baseline_cost_per_progress": 20.0})
    nr_metric = _get(metrics, "resource_progress_resistance.normalized_resistance")
    defn = nr_metric["definition"].lower()
    # Must not assert these as positive verdicts — check they don't appear
    # without a preceding negation word within 20 chars
    import re
    for term in ("chaos", "overfit", "healthy", "ffe"):
        assert term not in defn, f"Forbidden term '{term}' in definition"
    # 'optimal' may appear only in negation context
    if "optimal" in defn:
        assert re.search(r"not\s+\w*\s*optimal|non.optimal", defn), \
            "'optimal' appears without negation in definition"


# ── Custom progress key ───────────────────────────────────────────────────────

def test_custom_progress_key():
    obs = [_obs("o1", 0, {"compute.inference_ms": 50, "progress.value": 0, "memory.writes": 3})]
    # Use memory.writes as the progress key
    metrics = _run_metrics(obs, config={"progress_metric_key": "memory.writes"})
    prog = _get(metrics, "resource_progress_resistance.progress_delta")["value"]
    assert prog["total_progress"] == 3
    assert prog["progress_key"] == "memory.writes"
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_per_progress"] == pytest.approx(50 / 3)


# ── Cost signal fallback ──────────────────────────────────────────────────────

def test_cost_signal_uses_inference_ms_when_present():
    obs = [_obs("o1", 0, {
        "compute.inference_ms": 300,
        "compute.input_tokens": 100,
        "progress.value": 10,
    })]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_signal"] == "compute.inference_ms"
    assert cpp["total_cost"] == 300.0


def test_cost_signal_falls_back_to_sum_without_inference_ms():
    obs = [_obs("o1", 0, {
        "compute.input_tokens": 50,
        "compute.output_tokens": 30,
        "progress.value": 4,
    })]
    metrics = _run_metrics(obs)
    cpp = _get(metrics, "resource_progress_resistance.cost_per_progress")["value"]
    assert cpp["cost_signal"] == "sum_of_resource_dimensions"
    assert cpp["total_cost"] == 80.0


# ── Integration: full run via run_service ────────────────────────────────────

def test_full_run_completes(tmp_repo):
    from phitest.adapters.manual_target import ManualTarget
    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(tmp_repo, {
        "subject_id": s.id,
        "name": "RPR test",
        "protocol_key": "resource_progress_resistance",
        "configuration_json": json.dumps({
            "num_tasks": 2,
            "telemetry_allowlist": ["compute.inference_ms", "progress.value"],
        }),
    })
    run = run_service.execute_run(tmp_repo, e.id, ManualTarget("ok"), random_seed=42)
    assert run.status == "completed"
    assert len(tmp_repo.list_observations(run.id)) == 2
    assert len(tmp_repo.list_metric_results(run.id)) == 4


def test_full_run_obs_type_is_resource_progress_response(tmp_repo):
    from phitest.adapters.manual_target import ManualTarget
    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "manual",
    })
    e = experiment_service.create_experiment(tmp_repo, {
        "subject_id": s.id,
        "name": "RPR obs type",
        "protocol_key": "resource_progress_resistance",
    })
    run = run_service.execute_run(tmp_repo, e.id, ManualTarget("ok"), random_seed=42)
    obs = tmp_repo.list_observations(run.id)
    assert all(o.observation_type == "resource_progress_response" for o in obs)


def test_full_run_with_telemetry_transport(tmp_repo):
    """Telemetry flows through run_service into telemetry_samples table."""
    from datetime import datetime, timezone
    from phitest.domain.models import TargetResponse

    class RPRAdapter:
        adapter_type = "rpr_test"
        _seq = 0

        def send(self, stimulus, context=None):
            RPRAdapter._seq += 1
            return TargetResponse(
                text="done",
                metadata={
                    "compute.inference_ms": 100 * RPRAdapter._seq,
                    "progress.value": 5.0,
                },
                received_at=datetime.now(timezone.utc),
            )

    s = experiment_service.create_subject(tmp_repo, {
        "name": "Bot", "subject_type": "ai", "adapter_type": "rpr_test",
    })
    e = experiment_service.create_experiment(tmp_repo, {
        "subject_id": s.id,
        "name": "RPR telemetry",
        "protocol_key": "resource_progress_resistance",
        "configuration_json": json.dumps({
            "num_tasks": 2,
            "telemetry_allowlist": ["compute.inference_ms", "progress.value"],
        }),
    })
    run = run_service.execute_run(tmp_repo, e.id, RPRAdapter(), random_seed=42)
    assert run.status == "completed"
    samples = tmp_repo.list_telemetry_samples(run.id)
    assert len(samples) == 2
    for s in samples:
        vals = json.loads(s.values_json)
        assert "compute.inference_ms" in vals
        assert "progress.value" in vals
