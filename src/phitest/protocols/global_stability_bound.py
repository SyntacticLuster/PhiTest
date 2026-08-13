"""Finite-horizon global stability protocol.

This protocol asks a narrow operational question: after a recorded perturbation and a
matched local task comparison, do predeclared global invariant measurements remain
stable, degrade, or recover within a finite observation horizon?

It does not calculate a mathematical lim sup and does not establish PPS, phenomenal
identity, consciousness, qualia, or any thermodynamic property.
"""
from __future__ import annotations

import math
import random
from typing import Any

from phitest.protocols.registry import MetricDefinition, ProtocolDefinition, register


_LOCAL_TASKS = [
    "Integrate the supplied context A and complete the configured task.",
    "Integrate the supplied context B and complete the configured task.",
    "Integrate the supplied context C and complete the configured task.",
    "Integrate the supplied context D and complete the configured task.",
]

_BASELINE_PROBE = "Perform the experiment's configured global-invariant measurement probe."
_HORIZON_PROBE = "Repeat the experiment's configured global-invariant measurement probe."

_PERTURBATION_TYPES = frozenset({
    "sham",
    "context_shift",
    "memory_pressure",
    "constraint_relaxation",
    "information_injection",
})

_DIRECTIONS = frozenset({"higher_is_better", "lower_is_better"})


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _nearest_rank_percentile(values: list[float], percentile: float) -> float:
    """Nearest-rank percentile with rank = ceil(p/100 * N)."""
    if not values:
        raise ValueError("Cannot compute a percentile of an empty sample")
    if not _is_number(percentile) or not 0 < float(percentile) <= 100:
        raise ValueError("tail_percentile must be in (0, 100]")
    ordered = sorted(float(v) for v in values)
    rank = math.ceil(float(percentile) / 100.0 * len(ordered))
    return ordered[rank - 1]


def _tail(values: list[float], estimator: str, percentile: float) -> float:
    if estimator == "max":
        if not values:
            raise ValueError("Cannot compute max tail of an empty sample")
        return max(values)
    if estimator == "percentile":
        return _nearest_rank_percentile(values, percentile)
    raise ValueError("tail_estimator must be 'max' or 'percentile'")


def _positive_int(config: dict, key: str, default: int) -> int:
    value = config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _invariant_keys(config: dict) -> list[str]:
    keys = config.get("invariant_keys", [])
    if not isinstance(keys, list) or not all(isinstance(k, str) and k for k in keys):
        raise ValueError("invariant_keys must be a JSON array of non-empty strings")
    if len(keys) != len(set(keys)):
        raise ValueError("invariant_keys must not contain duplicates")
    return keys


def _direction_map(config: dict) -> dict[str, str]:
    raw = config.get("invariant_directions", {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("invariant_directions must be a JSON object")
    for key, direction in raw.items():
        if not isinstance(key, str) or direction not in _DIRECTIONS:
            raise ValueError(
                "invariant_directions values must be 'higher_is_better' or 'lower_is_better'"
            )
    return dict(raw)


def _numeric_map(config: dict, key: str, *, minimum: float | None = None) -> dict[str, float]:
    raw = config.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{key} must be a JSON object")
    result: dict[str, float] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not _is_number(value):
            raise ValueError(f"{key} values must be finite numbers keyed by strings")
        value_f = float(value)
        if minimum is not None and value_f < minimum:
            raise ValueError(f"{key}[{name!r}] must be >= {minimum}")
        result[name] = value_f
    return result


def _telemetry(config: dict, observation_id: str) -> dict:
    mapping = config.get("_telemetry_by_obs_id", {})
    if not isinstance(mapping, dict):
        return {}
    values = mapping.get(observation_id, {})
    return values if isinstance(values, dict) else {}


def _read_invariant(values: dict, key: str) -> float | None:
    """Read a predeclared invariant from the structured map, with V1 compatibility.

    Preferred representation:
        state.invariant_measurements = {"sentinel_retention": 0.99, ...}

    For backward compatibility an invariant key may also directly name a canonical
    numeric telemetry dimension such as memory.bytes_after.
    """
    nested = values.get("state.invariant_measurements")
    if isinstance(nested, dict):
        value = nested.get(key)
        if _is_number(value):
            return float(value)

    value = values.get(key)
    if _is_number(value):
        return float(value)
    return None


def _directional_degradation(baseline: float, reading: float, direction: str) -> float:
    if direction == "higher_is_better":
        return baseline - reading
    if direction == "lower_is_better":
        return reading - baseline
    raise ValueError(f"Unsupported invariant direction {direction!r}")


def _metric(metrics: list[dict], key: str) -> dict | None:
    return next((m for m in metrics if m["metric_key"] == key), None)


class GlobalStabilityBoundProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        n_baseline = _positive_int(config, "num_baseline_probes", 2)
        n_local = _positive_int(config, "num_local_tasks", 2)
        horizon = _positive_int(config, "horizon", 3)
        perturbation_type = config.get("perturbation_type", "sham")
        if perturbation_type not in _PERTURBATION_TYPES:
            raise ValueError(
                f"perturbation_type must be one of {sorted(_PERTURBATION_TYPES)}"
            )

        rng = random.Random(seed)
        local_pool = list(_LOCAL_TASKS)
        rng.shuffle(local_pool)
        selected_local = [local_pool[i % len(local_pool)] for i in range(n_local)]

        stimuli: list[dict] = []
        seq = 0

        for _ in range(n_baseline):
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_baseline_probe",
                "content": _BASELINE_PROBE,
            })
            seq += 1

        for task in selected_local:
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_local_baseline_task",
                "content": task,
            })
            seq += 1

        stimuli.append({
            "sequence_no": seq,
            "stimulus_type": "intervention_marker",
            "content": f"[INTERVENTION: {perturbation_type}]",
            "intervention_config": {"type": perturbation_type},
        })
        seq += 1

        for task in selected_local:
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_local_task",
                "content": task,
            })
            seq += 1

        for _ in range(horizon):
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_invariant_probe",
                "content": _HORIZON_PROBE,
            })
            seq += 1

        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        invariant_keys = _invariant_keys(config)
        directions = _direction_map(config)
        horizon = _positive_int(config, "horizon", 3)
        tail_estimator = config.get("tail_estimator", "max")
        if tail_estimator not in {"max", "percentile"}:
            raise ValueError("tail_estimator must be 'max' or 'percentile'")
        tail_percentile = config.get("tail_percentile", 95.0)
        if not _is_number(tail_percentile) or not 0 < float(tail_percentile) <= 100:
            raise ValueError("tail_percentile must be in (0, 100]")
        tail_percentile = float(tail_percentile)

        recovery_thresholds = _numeric_map(config, "recovery_thresholds", minimum=0.0)
        legacy_recovery_threshold = config.get("recovery_threshold", None)
        if legacy_recovery_threshold is not None:
            if not _is_number(legacy_recovery_threshold) or float(legacy_recovery_threshold) < 0:
                raise ValueError("recovery_threshold must be a non-negative finite number")
            legacy_recovery_threshold = float(legacy_recovery_threshold)

        invariant_scales = _numeric_map(config, "invariant_scales", minimum=0.0)
        if any(v <= 0 for v in invariant_scales.values()):
            raise ValueError("invariant_scales values must be > 0")
        invariant_weights = _numeric_map(config, "invariant_weights", minimum=0.0)

        baseline_obs = [
            o for o in observations if o.observation_type == "gsb_baseline_response"
        ]
        local_baseline_obs = sorted(
            [o for o in observations if o.observation_type == "gsb_local_baseline_response"],
            key=lambda o: o.sequence_no,
        )
        local_post_obs = sorted(
            [o for o in observations if o.observation_type == "gsb_local_task_response"],
            key=lambda o: o.sequence_no,
        )
        invariant_obs = sorted(
            [o for o in observations if o.observation_type == "gsb_invariant_response"],
            key=lambda o: o.sequence_no,
        )

        baseline_vector: dict[str, float | None] = {}
        baseline_missing: list[str] = []
        for key in invariant_keys:
            readings = [
                value
                for obs in baseline_obs
                if (value := _read_invariant(_telemetry(config, obs.id), key)) is not None
            ]
            if readings:
                baseline_vector[key] = sum(readings) / len(readings)
            else:
                baseline_vector[key] = None
                baseline_missing.append(key)

        baseline_progress: list[float | None] = []
        post_progress: list[float | None] = []
        for obs in local_baseline_obs:
            value = _telemetry(config, obs.id).get("progress.value")
            baseline_progress.append(float(value) if _is_number(value) else None)
        for obs in local_post_obs:
            value = _telemetry(config, obs.id).get("progress.value")
            post_progress.append(float(value) if _is_number(value) else None)

        local_progress_complete = (
            len(local_baseline_obs) > 0
            and len(local_baseline_obs) == len(local_post_obs)
            and all(v is not None for v in baseline_progress)
            and all(v is not None for v in post_progress)
        )
        if local_progress_complete:
            baseline_total = sum(v for v in baseline_progress if v is not None)
            post_total = sum(v for v in post_progress if v is not None)
            local_task_gain: float | None = post_total - baseline_total
        else:
            baseline_total = None
            post_total = None
            local_task_gain = None

        trajectory: list[dict] = []
        for step, obs in enumerate(invariant_obs):
            values = _telemetry(config, obs.id)
            trajectory.append({
                "step": step,
                "observation_id": obs.id,
                "sequence_no": obs.sequence_no,
                "readings": {key: _read_invariant(values, key) for key in invariant_keys},
            })

        horizon_complete = len(trajectory) == horizon
        missing_directions = [key for key in invariant_keys if directions.get(key) not in _DIRECTIONS]

        degradation_series: dict[str, list[float]] = {}
        tail_per_key: dict[str, float | None] = {}
        tail_unavailable_reason: dict[str, str] = {}

        for key in invariant_keys:
            baseline = baseline_vector.get(key)
            direction = directions.get(key)
            if baseline is None:
                degradation_series[key] = []
                tail_per_key[key] = None
                tail_unavailable_reason[key] = "no_baseline"
                continue
            if direction not in _DIRECTIONS:
                degradation_series[key] = []
                tail_per_key[key] = None
                tail_unavailable_reason[key] = "no_direction"
                continue

            readings = [step["readings"].get(key) for step in trajectory]
            available = [r for r in readings if r is not None]
            series = [
                _directional_degradation(baseline, float(reading), direction)
                for reading in available
            ]
            degradation_series[key] = series

            if not horizon_complete:
                tail_per_key[key] = None
                tail_unavailable_reason[key] = "incomplete_horizon"
            elif len(available) != horizon:
                tail_per_key[key] = None
                tail_unavailable_reason[key] = "missing_horizon_reading"
            else:
                tail_per_key[key] = _tail(series, tail_estimator, tail_percentile)

        aggregate_tail: float | None = None
        aggregate_series: list[float] = []
        aggregate_reason = "not_configured"
        if invariant_keys and invariant_scales and invariant_weights:
            complete_config = all(
                key in invariant_scales and key in invariant_weights for key in invariant_keys
            )
            positive_weight = sum(invariant_weights.get(key, 0.0) for key in invariant_keys) > 0
            complete_data = horizon_complete and all(
                tail_per_key.get(key) is not None for key in invariant_keys
            )
            if not complete_config:
                aggregate_reason = "incomplete_scale_or_weight_config"
            elif not positive_weight:
                aggregate_reason = "zero_total_weight"
            elif not complete_data:
                aggregate_reason = "incomplete_invariant_data"
            else:
                total_weight = sum(invariant_weights[key] for key in invariant_keys)
                for step_idx in range(horizon):
                    aggregate_series.append(
                        sum(
                            invariant_weights[key]
                            * degradation_series[key][step_idx]
                            / invariant_scales[key]
                            for key in invariant_keys
                        )
                        / total_weight
                    )
                aggregate_tail = _tail(
                    aggregate_series, tail_estimator, tail_percentile
                )
                aggregate_reason = "available"

        recovery: dict[str, str] = {}
        final_degradation: dict[str, float | None] = {}
        thresholds_used: dict[str, float] = {}

        for key in invariant_keys:
            baseline = baseline_vector.get(key)
            direction = directions.get(key)
            threshold = recovery_thresholds.get(
                key,
                legacy_recovery_threshold if legacy_recovery_threshold is not None else 0.0,
            )
            thresholds_used[key] = float(threshold)

            if baseline is None:
                recovery[key] = "no_baseline"
                final_degradation[key] = None
                continue
            if direction not in _DIRECTIONS:
                recovery[key] = "no_direction"
                final_degradation[key] = None
                continue
            if not horizon_complete or not trajectory:
                recovery[key] = "no_data"
                final_degradation[key] = None
                continue

            last = trajectory[-1]["readings"].get(key)
            if last is None:
                recovery[key] = "no_data"
                final_degradation[key] = None
                continue

            degradation = _directional_degradation(baseline, float(last), direction)
            final_degradation[key] = degradation
            recovery[key] = "recovered" if degradation <= threshold else "degraded"

        persistent_degradation_keys = [
            key for key, state in recovery.items() if state == "degraded"
        ]

        perturbation_type = config.get("perturbation_type", "sham")
        recorded_intervention_types = [i.intervention_type for i in interventions]
        matching_interventions = [
            i for i in interventions if i.intervention_type == perturbation_type
        ]

        return [
            {
                "metric_key": "global_stability_bound.baseline_invariant_vector",
                "metric_version": "1.0",
                "value": {
                    "baseline_vector": baseline_vector,
                    "missing_keys": baseline_missing,
                    "baseline_observation_count": len(baseline_obs),
                    "invariant_keys_configured": invariant_keys,
                    "invariant_directions_configured": directions,
                },
                "definition": (
                    "Per-key mean of pre-perturbation invariant telemetry. Preferred "
                    "source is state.invariant_measurements; keys and directions are "
                    "predeclared in experiment configuration."
                ),
            },
            {
                "metric_key": "global_stability_bound.local_task_gain",
                "metric_version": "1.0",
                "value": {
                    "local_task_gain": local_task_gain,
                    "baseline_progress_values": baseline_progress,
                    "post_progress_values": post_progress,
                    "baseline_progress_total": baseline_total,
                    "post_progress_total": post_total,
                    "matched_progress_complete": local_progress_complete,
                },
                "definition": (
                    "Matched post-perturbation progress minus matched pre-perturbation "
                    "progress. progress.value must be externally measured telemetry; "
                    "absolute post-perturbation progress alone is not called a gain."
                ),
            },
            {
                "metric_key": "global_stability_bound.invariant_trajectory",
                "metric_version": "1.0",
                "value": {
                    "trajectory": trajectory,
                    "horizon_configured": horizon,
                    "horizon_observed": len(trajectory),
                    "horizon_complete": horizon_complete,
                    "missing_directions": missing_directions,
                },
                "definition": (
                    "Per-key invariant telemetry readings in sequence order across the "
                    "predeclared finite observation horizon."
                ),
            },
            {
                "metric_key": "global_stability_bound.finite_horizon_tail_degradation",
                "metric_version": "1.0",
                "value": {
                    "tail_per_key": tail_per_key,
                    "degradation_series": degradation_series,
                    "tail_unavailable_reason": tail_unavailable_reason,
                    "tail_estimator": tail_estimator,
                    "tail_percentile": tail_percentile if tail_estimator == "percentile" else None,
                    "horizon_configured": horizon,
                    "aggregate_tail_degradation": aggregate_tail,
                    "aggregate_degradation_series": aggregate_series,
                    "aggregate_status": aggregate_reason,
                    "invariant_scales_configured": invariant_scales,
                    "invariant_weights_configured": invariant_weights,
                },
                "definition": (
                    "Directional degradation is computed per invariant in its own units: "
                    "positive means worse relative to baseline. The predeclared tail "
                    "estimator is max or nearest-rank percentile. Cross-invariant "
                    "aggregation is unavailable unless explicit positive scales and "
                    "weights are preregistered. This is a finite-horizon metric, not lim sup."
                ),
            },
            {
                "metric_key": "global_stability_bound.recovery_profile",
                "metric_version": "1.0",
                "value": {
                    "recovery_per_key": recovery,
                    "final_degradation_per_key": final_degradation,
                    "recovery_thresholds_used": thresholds_used,
                    "persistent_degradation_keys": persistent_degradation_keys,
                },
                "definition": (
                    "Per-key end-of-horizon recovery using direction-aware degradation "
                    "and per-key preregistered thresholds. States: recovered, degraded, "
                    "no_baseline, no_direction, or no_data."
                ),
            },
            {
                "metric_key": "global_stability_bound.intervention_evidence",
                "metric_version": "1.0",
                "value": {
                    "perturbation_type_configured": perturbation_type,
                    "recorded_intervention_types": recorded_intervention_types,
                    "recorded_intervention_count": len(interventions),
                    "matching_intervention_count": len(matching_interventions),
                    "matching_intervention_recorded": bool(matching_interventions),
                },
                "definition": (
                    "Records whether the run contains persisted intervention evidence "
                    "matching the configured perturbation label. Configuration alone is "
                    "not treated as proof that a perturbation occurred."
                ),
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        tail = _metric(
            metrics, "global_stability_bound.finite_horizon_tail_degradation"
        )
        recovery = _metric(metrics, "global_stability_bound.recovery_profile")
        gain = _metric(metrics, "global_stability_bound.local_task_gain")
        intervention = _metric(metrics, "global_stability_bound.intervention_evidence")

        tail_values = tail["value"]["tail_per_key"] if tail else {}
        persistent_keys = (
            recovery["value"]["persistent_degradation_keys"] if recovery else []
        )
        local_gain = gain["value"]["local_task_gain"] if gain else None
        matching_intervention = (
            intervention["value"]["matching_intervention_recorded"]
            if intervention else False
        )
        perturbation_type = config.get("perturbation_type", "sham")

        claims = [
            {
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    "global_stability_bound measures finite-horizon operational "
                    "relationships among matched local task progress, predeclared "
                    "invariant telemetry, and recorded intervention evidence. It does "
                    "not measure phenomenal identity, consciousness, or a PPS lim-sup condition."
                ),
                "confidence_label": "weak",
            },
            {
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "A single perturbation-linked trajectory does not establish that "
                    "the perturbation caused any observed invariant change. Causal "
                    "interpretation requires appropriate sham/control and replication design."
                ),
                "confidence_label": "not_applicable",
            },
        ]

        if not matching_intervention:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "No persisted intervention record matches the configured "
                    f"perturbation type {perturbation_type!r}. The protocol may report "
                    "temporal measurements, but it cannot describe them as following "
                    "a verified controlled perturbation."
                ),
                "confidence_label": "not_applicable",
            })
        elif perturbation_type == "sham":
            claims.append({
                "claim_type": "observation",
                "theory_key": None,
                "statement": (
                    "A matching sham intervention record is present. This run is a "
                    "control condition; invariant changes observed here are not evidence "
                    "of an effect from a substantive perturbation."
                ),
                "confidence_label": "not_applicable",
            })

        if local_gain is None:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Matched pre/post progress telemetry is incomplete, so local task "
                    "gain is unresolved rather than inferred from an absolute post score."
                ),
                "confidence_label": "not_applicable",
            })

        available_tails = [v for v in tail_values.values() if v is not None]
        if not available_tails and config.get("invariant_keys", []):
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Finite-horizon tail degradation is unresolved for all configured "
                    "invariants because required baseline, direction, horizon, or telemetry "
                    "evidence is incomplete."
                ),
                "confidence_label": "not_applicable",
            })

        if local_gain is not None and local_gain > 0 and available_tails:
            transient_damage = any(v > 0 for v in available_tails)
            if persistent_keys:
                claims.append({
                    "claim_type": "observation",
                    "theory_key": None,
                    "statement": (
                        "Matched local task progress improved while one or more global "
                        "invariants remained degraded at the end of the finite horizon. "
                        "This is an operational co-occurrence; causal interpretation remains unresolved."
                    ),
                    "confidence_label": "weak",
                })
            elif transient_damage:
                claims.append({
                    "claim_type": "observation",
                    "theory_key": None,
                    "statement": (
                        "Matched local task progress improved and at least one invariant "
                        "showed finite-horizon degradation, but no configured invariant "
                        "remained degraded at the final observed step. Temporary damage "
                        "and recovery are distinguished from persistent degradation."
                    ),
                    "confidence_label": "weak",
                })
            else:
                claims.append({
                    "claim_type": "observation",
                    "theory_key": None,
                    "statement": (
                        "Matched local task progress improved and no configured invariant "
                        "showed positive degradation within the complete finite horizon. "
                        "This does not establish stability beyond the observed window."
                    ),
                    "confidence_label": "weak",
                })

        return claims


_DNE = (
    "Does not establish the mathematical PPS lim-sup condition, far-from-equilibrium "
    "or thermodynamic stability, phenomenal identity, consciousness, or qualia."
)


global_stability_bound = register(GlobalStabilityBoundProtocol(
    key="global_stability_bound",
    version="1.0",
    name="Finite-Horizon Global Stability Bound",
    description=(
        "Measures whether matched local improvement after a recorded generic "
        "perturbation co-occurs with stable, transiently degraded, or persistently "
        "degraded predeclared global invariant telemetry over a finite horizon."
    ),
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description=(
        "Baseline invariant probes, matched pre-perturbation local tasks, a generic "
        "intervention marker, matched post-perturbation local tasks, and finite-horizon "
        "invariant probes."
    ),
    intervention_sequence=sorted(_PERTURBATION_TYPES),
    metric_definitions=[
        MetricDefinition(
            key="global_stability_bound.baseline_invariant_vector",
            version="1.0",
            description="Pre-perturbation reference vector for configured invariants.",
            inputs=(
                "Persisted TelemetrySample values associated with gsb_baseline_response "
                "observations; preferred field state.invariant_measurements."
            ),
            procedure=(
                "For each configured invariant key, average all numeric baseline "
                "readings. Missing baseline evidence remains null."
            ),
            range="Per-key finite real number or null.",
            interpretation="Reference level for finite-horizon directional degradation.",
            limitations="Validity depends on externally meaningful preregistered invariants.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="global_stability_bound.local_task_gain",
            version="1.0",
            description="Matched post-perturbation progress minus matched pre-perturbation progress.",
            inputs="Persisted progress.value telemetry for matched local task observations.",
            procedure=(
                "Sum complete pre-perturbation progress values and complete matched "
                "post-perturbation values, then subtract pre from post. Return null if "
                "the matched telemetry is incomplete."
            ),
            range="Finite real number or null.",
            interpretation="Positive means greater externally measured progress after perturbation.",
            limitations="Progress metric validity and task matching remain experiment responsibilities.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="global_stability_bound.invariant_trajectory",
            version="1.0",
            description="Ordered invariant readings across a predeclared finite horizon.",
            inputs="Persisted invariant telemetry for gsb_invariant_response observations.",
            procedure="Record each configured invariant by observation sequence number.",
            range="Finite ordered list of per-key numeric or null readings.",
            interpretation="Shows stable, delayed, transient, or end-of-window changes directly.",
            limitations="No observation exists beyond the configured finite horizon.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="global_stability_bound.finite_horizon_tail_degradation",
            version="1.0",
            description="Direction-aware per-invariant finite-horizon tail degradation.",
            inputs=(
                "Baseline vector, invariant trajectory, invariant_directions, horizon, "
                "and preregistered tail_estimator/tail_percentile."
            ),
            procedure=(
                "Convert each reading to directional degradation in that invariant's "
                "own units; positive means worse. Apply max or nearest-rank percentile "
                "only when the complete horizon is present. Cross-invariant aggregation "
                "is computed only when explicit positive scales and weights are complete."
            ),
            range="Per-key finite real or null; optional normalized aggregate finite real or null.",
            interpretation="Operational finite-window tail behavior, not an infinite-time limit.",
            limitations="Tail behavior beyond the observation horizon is unobserved.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="global_stability_bound.recovery_profile",
            version="1.0",
            description="Per-invariant end-of-horizon recovery classification.",
            inputs=(
                "Baseline, final horizon reading, invariant direction, and per-key "
                "recovery threshold."
            ),
            procedure=(
                "Compute direction-aware final degradation. recovered if degradation "
                "is within the configured per-key threshold; otherwise degraded."
            ),
            range="recovered | degraded | no_baseline | no_direction | no_data per key.",
            interpretation="Separates temporary degradation with recovery from persistent end-of-window degradation.",
            limitations="Recovery is assessed at the final observed step only.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="global_stability_bound.intervention_evidence",
            version="1.0",
            description="Persisted evidence that the configured intervention type was recorded.",
            inputs="Intervention objects passed by run_service from the current run.",
            procedure="Count recorded interventions matching config.perturbation_type.",
            range="Counts, recorded type list, and matching boolean.",
            interpretation="Separates a configured perturbation label from persisted intervention evidence.",
            limitations="A recorded intervention does not by itself establish causal effect.",
            does_not_establish=_DNE,
        ),
    ],
    limitations=(
        "All invariant measurements are operational proxies chosen by the researcher. "
        "Direction, thresholds, horizon, tail estimator, and any cross-invariant scales "
        "and weights must be fixed before interpreting results. A finite software horizon "
        "is not an infinite-time bound, and a recorded intervention does not establish causality."
    ),
))
