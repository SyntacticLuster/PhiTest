import hashlib
from datetime import datetime, timezone

import pytest

from phitest.domain.models import Intervention, Observation
from phitest.protocols.global_stability_bound import _nearest_rank_percentile
from phitest.protocols.registry import get_protocol


def _now():
    return datetime.now(timezone.utc)


def _obs(obs_id: str, seq: int, obs_type: str) -> Observation:
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


def _intervention(kind: str = "context_shift") -> Intervention:
    return Intervention(
        id="int-1",
        run_id="run-1",
        sequence_no=2,
        intervention_type=kind,
        configuration_json='{"status":"ok"}',
        rationale="test",
        created_at=_now(),
    )


def _metric(metrics, key):
    return next(m for m in metrics if m["metric_key"] == key)["value"]


def _case(
    *,
    baseline=1.0,
    pre_progress=5.0,
    post_progress=8.0,
    horizon=(1.0, 1.0, 1.0),
    direction="higher_is_better",
    perturbation="context_shift",
    with_intervention=True,
    tail_estimator="max",
    tail_percentile=95.0,
    threshold=0.05,
):
    observations = [
        _obs("b", 0, "gsb_baseline_response"),
        _obs("pre", 1, "gsb_local_baseline_response"),
        _obs("post", 3, "gsb_local_task_response"),
    ]
    telemetry = {
        "b": {"state.invariant_measurements": {"retention": baseline}},
        "pre": {"progress.value": pre_progress},
        "post": {"progress.value": post_progress},
    }
    for idx, value in enumerate(horizon):
        obs_id = f"h{idx}"
        observations.append(_obs(obs_id, 4 + idx, "gsb_invariant_response"))
        telemetry[obs_id] = {"state.invariant_measurements": {"retention": value}}

    config = {
        "invariant_keys": ["retention"],
        "invariant_directions": {"retention": direction},
        "horizon": len(horizon),
        "perturbation_type": perturbation,
        "tail_estimator": tail_estimator,
        "tail_percentile": tail_percentile,
        "recovery_thresholds": {"retention": threshold},
        "_telemetry_by_obs_id": telemetry,
    }
    interventions = [_intervention(perturbation)] if with_intervention else []
    protocol = get_protocol("global_stability_bound")
    metrics = protocol.compute_metrics([], observations, interventions, config)
    return protocol, metrics, config, observations, interventions


def test_protocol_registered_and_versioned():
    protocol = get_protocol("global_stability_bound")
    assert protocol is not None
    assert protocol.version == "1.0"
    assert protocol.name == "Finite-Horizon Global Stability Bound"


def test_generate_stimuli_is_deterministic_and_local_tasks_are_matched():
    protocol = get_protocol("global_stability_bound")
    config = {"num_baseline_probes": 1, "num_local_tasks": 3, "horizon": 2}
    first = protocol.generate_stimuli(config, 42)
    second = protocol.generate_stimuli(config, 42)
    assert first == second

    pre = [s["content"] for s in first if s["stimulus_type"] == "gsb_local_baseline_task"]
    post = [s["content"] for s in first if s["stimulus_type"] == "gsb_local_task"]
    assert pre == post
    assert len(pre) == 3
    assert len([s for s in first if s["stimulus_type"] == "gsb_invariant_probe"]) == 2


def test_nearest_rank_percentile_is_mathematically_correct():
    values = [1.0, 2.0, 3.0, 4.0]
    assert _nearest_rank_percentile(values, 25) == 1.0
    assert _nearest_rank_percentile(values, 50) == 2.0
    assert _nearest_rank_percentile(values, 75) == 3.0
    assert _nearest_rank_percentile(values, 100) == 4.0
    assert _nearest_rank_percentile([0.1, 0.2, 0.3], 50) == 0.2


def test_nearest_rank_percentile_rejects_invalid_percentile():
    with pytest.raises(ValueError):
        _nearest_rank_percentile([1.0], 0)
    with pytest.raises(ValueError):
        _nearest_rank_percentile([1.0], 101)


def test_local_task_gain_is_matched_delta_not_absolute_post_score():
    _, metrics, *_ = _case(pre_progress=5.0, post_progress=8.0)
    gain = _metric(metrics, "global_stability_bound.local_task_gain")
    assert gain["baseline_progress_total"] == 5.0
    assert gain["post_progress_total"] == 8.0
    assert gain["local_task_gain"] == 3.0
    assert gain["matched_progress_complete"] is True


def test_stable_global_invariant_has_zero_tail_and_recovers():
    _, metrics, *_ = _case(horizon=(1.0, 1.0, 1.0))
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.0)
    assert recovery["recovery_per_key"]["retention"] == "recovered"
    assert recovery["persistent_degradation_keys"] == []


def test_local_improvement_with_delayed_global_collapse_is_visible():
    _, metrics, *_ = _case(horizon=(1.0, 0.95, 0.40), threshold=0.1)
    gain = _metric(metrics, "global_stability_bound.local_task_gain")
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert gain["local_task_gain"] == 3.0
    assert tail["degradation_series"]["retention"] == pytest.approx([0.0, 0.05, 0.60])
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.60)
    assert recovery["recovery_per_key"]["retention"] == "degraded"


def test_immediate_global_damage_is_visible():
    _, metrics, *_ = _case(horizon=(0.40, 0.50, 0.60), threshold=0.1)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.60)
    assert recovery["final_degradation_per_key"]["retention"] == pytest.approx(0.40)
    assert recovery["recovery_per_key"]["retention"] == "degraded"


def test_temporary_damage_and_recovery_are_distinguished():
    _, metrics, *_ = _case(horizon=(0.50, 0.80, 0.98), threshold=0.05)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.50)
    assert recovery["final_degradation_per_key"]["retention"] == pytest.approx(0.02)
    assert recovery["recovery_per_key"]["retention"] == "recovered"
    assert recovery["persistent_degradation_keys"] == []


def test_lower_is_better_direction_is_not_treated_as_higher_is_better():
    _, metrics, *_ = _case(
        baseline=10.0,
        horizon=(12.0, 9.0, 11.0),
        direction="lower_is_better",
        threshold=0.5,
    )
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["degradation_series"]["retention"] == pytest.approx([2.0, -1.0, 1.0])
    assert tail["tail_per_key"]["retention"] == pytest.approx(2.0)
    assert recovery["recovery_per_key"]["retention"] == "degraded"


def test_percentile_tail_uses_nearest_rank_not_floor_indexing():
    _, metrics, *_ = _case(
        horizon=(1.0, 0.8, 0.6, 0.4),
        tail_estimator="percentile",
        tail_percentile=50,
    )
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    assert tail["tail_per_key"]["retention"] == pytest.approx(0.2)


def test_missing_baseline_telemetry_keeps_tail_unresolved():
    protocol = get_protocol("global_stability_bound")
    observations = [
        _obs("b", 0, "gsb_baseline_response"),
        _obs("h0", 1, "gsb_invariant_response"),
    ]
    config = {
        "invariant_keys": ["retention"],
        "invariant_directions": {"retention": "higher_is_better"},
        "horizon": 1,
        "_telemetry_by_obs_id": {
            "b": {},
            "h0": {"state.invariant_measurements": {"retention": 0.9}},
        },
    }
    metrics = protocol.compute_metrics([], observations, [], config)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["tail_per_key"]["retention"] is None
    assert tail["tail_unavailable_reason"]["retention"] == "no_baseline"
    assert recovery["recovery_per_key"]["retention"] == "no_baseline"


def test_missing_direction_does_not_assume_higher_is_better():
    protocol, metrics, config, observations, interventions = _case()
    config = dict(config)
    config["invariant_directions"] = {}
    metrics = protocol.compute_metrics([], observations, interventions, config)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    recovery = _metric(metrics, "global_stability_bound.recovery_profile")
    assert tail["tail_per_key"]["retention"] is None
    assert tail["tail_unavailable_reason"]["retention"] == "no_direction"
    assert recovery["recovery_per_key"]["retention"] == "no_direction"


def test_incomplete_horizon_does_not_report_a_tail_from_partial_data():
    protocol, metrics, config, observations, interventions = _case(horizon=(1.0, 0.8, 0.7))
    config = dict(config)
    config["horizon"] = 4
    metrics = protocol.compute_metrics([], observations, interventions, config)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    trajectory = _metric(metrics, "global_stability_bound.invariant_trajectory")
    assert trajectory["horizon_complete"] is False
    assert tail["tail_per_key"]["retention"] is None
    assert tail["tail_unavailable_reason"]["retention"] == "incomplete_horizon"


def test_cross_invariant_scalar_is_not_created_without_scales_and_weights():
    _, metrics, *_ = _case(horizon=(0.9, 0.8, 0.7))
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    assert tail["aggregate_tail_degradation"] is None
    assert tail["aggregate_status"] == "not_configured"


def test_cross_invariant_aggregate_requires_explicit_normalization():
    protocol = get_protocol("global_stability_bound")
    observations = [
        _obs("b", 0, "gsb_baseline_response"),
        _obs("h0", 1, "gsb_invariant_response"),
        _obs("h1", 2, "gsb_invariant_response"),
    ]
    config = {
        "invariant_keys": ["retention", "error_rate"],
        "invariant_directions": {
            "retention": "higher_is_better",
            "error_rate": "lower_is_better",
        },
        "invariant_scales": {"retention": 0.1, "error_rate": 10.0},
        "invariant_weights": {"retention": 1.0, "error_rate": 1.0},
        "horizon": 2,
        "tail_estimator": "max",
        "_telemetry_by_obs_id": {
            "b": {"state.invariant_measurements": {"retention": 1.0, "error_rate": 10.0}},
            "h0": {"state.invariant_measurements": {"retention": 0.9, "error_rate": 20.0}},
            "h1": {"state.invariant_measurements": {"retention": 1.0, "error_rate": 10.0}},
        },
    }
    metrics = protocol.compute_metrics([], observations, [], config)
    tail = _metric(metrics, "global_stability_bound.finite_horizon_tail_degradation")
    assert tail["aggregate_status"] == "available"
    assert tail["aggregate_tail_degradation"] == pytest.approx(1.0)


def test_sham_intervention_is_recorded_as_control_not_causal_proof():
    protocol, metrics, config, observations, interventions = _case(
        perturbation="sham", with_intervention=True
    )
    evidence = _metric(metrics, "global_stability_bound.intervention_evidence")
    assert evidence["matching_intervention_recorded"] is True
    claims = protocol.generate_claims([], observations, metrics, config)
    text = "\n".join(c["statement"].lower() for c in claims)
    assert "sham" in text
    assert "control" in text
    assert "causal" in text


def test_missing_intervention_record_is_explicitly_unresolved():
    protocol, metrics, config, observations, _ = _case(with_intervention=False)
    evidence = _metric(metrics, "global_stability_bound.intervention_evidence")
    assert evidence["matching_intervention_recorded"] is False
    claims = protocol.generate_claims([], observations, metrics, config)
    text = "\n".join(c["statement"].lower() for c in claims)
    assert "no persisted intervention record" in text


def test_metric_definitions_keep_the_epistemic_boundary():
    protocol = get_protocol("global_stability_bound")
    assert len(protocol.metric_definitions) == 6
    for definition in protocol.metric_definitions:
        dne = definition.does_not_establish.lower()
        assert "lim-sup" in dne
        assert "consciousness" in dne
        assert "qualia" in dne
        assert "phenomenal identity" in dne
