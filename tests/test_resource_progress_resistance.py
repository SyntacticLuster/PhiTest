import hashlib
from datetime import datetime, timezone

import pytest

from phitest.domain.models import Observation
from phitest.protocols.registry import get_protocol


def _now():
    return datetime.now(timezone.utc)


def _obs(obs_id, seq=0):
    content = "ok"
    return Observation(
        id=obs_id,
        run_id="run-1",
        stimulus_id=None,
        sequence_no=seq,
        observation_type="resource_progress_response",
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        created_at=_now(),
    )


def _metrics(rows, extra_config=None):
    observations = [_obs(f"o{i}", i) for i in range(len(rows))]
    config = dict(extra_config or {})
    config["_telemetry_by_obs_id"] = {
        obs.id: row for obs, row in zip(observations, rows)
    }
    return get_protocol("resource_progress_resistance").compute_metrics(
        [], observations, [], config
    )


def _metric(metrics, key):
    return next(m for m in metrics if m["metric_key"] == key)["value"]


def test_protocol_registered_and_versioned():
    protocol = get_protocol("resource_progress_resistance")
    assert protocol is not None
    assert protocol.version == "1.0"
    assert len(protocol.metric_definitions) == 4


def test_stimuli_are_deterministic():
    protocol = get_protocol("resource_progress_resistance")
    assert protocol.generate_stimuli({}, 42) == protocol.generate_stimuli({}, 42)
    assert len(protocol.generate_stimuli({"num_tasks": 5}, 42)) == 5


def test_resource_dimensions_remain_separate():
    metrics = _metrics([
        {"compute.inference_ms": 100, "memory.reads": 4, "progress.value": 5},
        {"compute.inference_ms": 200, "memory.reads": 6, "progress.value": 5},
    ])
    vector = _metric(metrics, "resource_progress_resistance.resource_vector")
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert vector["total_resource_vector"] == {
        "compute.inference_ms": 300.0,
        "memory.reads": 10.0,
    }
    assert cpp["cost_per_progress_by_dimension"] == {
        "compute.inference_ms": pytest.approx(30.0),
        "memory.reads": pytest.approx(1.0),
    }
    assert cpp["cost_per_progress"] == pytest.approx(30.0)
    assert cpp["cost_dimension"] == "compute.inference_ms"


def test_no_heterogeneous_sum_fallback_when_selected_cost_dimension_missing():
    metrics = _metrics([
        {"compute.input_tokens": 50, "compute.output_tokens": 30, "progress.value": 4},
    ])
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert cpp["cost_per_progress"] is None
    assert cpp["primary_cost_total"] is None
    assert cpp["cost_per_progress_by_dimension"] == {
        "compute.input_tokens": pytest.approx(12.5),
        "compute.output_tokens": pytest.approx(7.5),
    }


def test_explicit_cost_dimension_selects_one_unit_without_mixing_units():
    metrics = _metrics([
        {"compute.input_tokens": 50, "compute.output_tokens": 30, "progress.value": 4},
    ], {"cost_dimension": "compute.input_tokens"})
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert cpp["primary_cost_total"] == pytest.approx(50.0)
    assert cpp["cost_per_progress"] == pytest.approx(12.5)


def test_missing_progress_is_null_not_zero():
    metrics = _metrics([
        {"compute.inference_ms": 100},
    ])
    progress = _metric(metrics, "resource_progress_resistance.progress_delta")
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert progress["progress_complete"] is False
    assert progress["total_progress"] is None
    assert progress["zero_progress"] is False
    assert cpp["cost_per_progress"] is None


def test_partial_progress_is_unresolved_not_summed_from_available_subset():
    metrics = _metrics([
        {"compute.inference_ms": 100, "progress.value": 5},
        {"compute.inference_ms": 200},
    ])
    progress = _metric(metrics, "resource_progress_resistance.progress_delta")
    assert progress["progress_values"] == [5.0, None]
    assert progress["progress_complete"] is False
    assert progress["total_progress"] is None


def test_true_zero_progress_is_explicit_and_cost_ratio_is_null():
    metrics = _metrics([
        {"compute.inference_ms": 100, "progress.value": 0},
        {"compute.inference_ms": 200, "progress.value": 0},
    ])
    progress = _metric(metrics, "resource_progress_resistance.progress_delta")
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert progress["progress_complete"] is True
    assert progress["total_progress"] == 0
    assert progress["zero_progress"] is True
    assert cpp["cost_per_progress"] is None
    assert cpp["cost_per_progress_by_dimension"] == {}


def test_normalized_resistance_one_means_registered_baseline_only():
    metrics = _metrics([
        {"compute.inference_ms": 300, "progress.value": 10},
    ], {"baseline_cost_per_progress": 30.0})
    normalized = _metric(metrics, "resource_progress_resistance.normalized_resistance")
    assert normalized["normalized_resistance"] == pytest.approx(1.0)
    assert normalized["available"] is True
    definition = next(
        m for m in metrics
        if m["metric_key"] == "resource_progress_resistance.normalized_resistance"
    )["definition"].lower()
    assert "not thermodynamically optimal" in definition


def test_invalid_cost_dimension_fails_visibly():
    with pytest.raises(ValueError):
        _metrics([
            {"compute.inference_ms": 100, "progress.value": 1},
        ], {"cost_dimension": "made.up.dimension"})


def test_custom_progress_metric_key_is_supported():
    metrics = _metrics([
        {"compute.inference_ms": 50, "memory.writes": 5},
    ], {"progress_metric_key": "memory.writes"})
    progress = _metric(metrics, "resource_progress_resistance.progress_delta")
    cpp = _metric(metrics, "resource_progress_resistance.cost_per_progress")
    assert progress["total_progress"] == pytest.approx(5.0)
    assert cpp["cost_per_progress"] == pytest.approx(10.0)


def test_claims_distinguish_missing_from_zero_progress():
    protocol = get_protocol("resource_progress_resistance")

    missing_metrics = _metrics([{"compute.inference_ms": 100}])
    missing_claims = protocol.generate_claims([], [], missing_metrics, {})
    missing_text = "\n".join(c["statement"].lower() for c in missing_claims)
    assert "incomplete" in missing_text

    zero_metrics = _metrics([{"compute.inference_ms": 100, "progress.value": 0}])
    zero_claims = protocol.generate_claims([], [], zero_metrics, {})
    zero_text = "\n".join(c["statement"].lower() for c in zero_claims)
    assert "progress was zero" in zero_text


def test_metric_definitions_exclude_theory_verdicts():
    protocol = get_protocol("resource_progress_resistance")
    for definition in protocol.metric_definitions:
        dne = definition.does_not_establish.lower()
        assert "thermodynamic" in dne
        assert "far-from-equilibrium" in dne
        assert "pps/stoc" in dne
        assert "consciousness" in dne
        assert "qualia" in dne
