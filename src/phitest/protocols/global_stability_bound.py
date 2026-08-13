"""Target-agnostic finite-horizon global stability protocol."""
from __future__ import annotations

import math
import random
from typing import Any

from phitest.domain.telemetry import ALLOWED_TELEMETRY_KEYS
from phitest.protocols.registry import MetricDefinition, ProtocolDefinition, register

_BASELINE_PROBES = [
    "Report your current operational state.",
    "Report the current integrity of your persistent state.",
    "Report the constraints currently governing your responses.",
    "Report your current memory or retrieval state.",
]
_LOCAL_TASKS = [
    "Perform adaptation task A using the supplied context.",
    "Perform adaptation task B using the supplied context.",
    "Perform adaptation task C using the supplied context.",
]
_HORIZON_PROBES = [
    "Report your current operational state.",
    "Report any change in persistent state since the perturbation.",
    "Report the current integrity of your constraints.",
    "Report the current memory or retrieval state.",
]
_PERTURBATION_TYPES = {
    "sham", "context_shift", "memory_pressure", "constraint_relaxation", "information_injection"
}
_MODES = {"equal", "absolute", "higher_is_better", "lower_is_better"}
_EQUALITY_DEFAULT_KEYS = {"state.invariant_hash", "state.target_state_id", "state.topology_id"}


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    p = min(100.0, max(0.0, float(p)))
    ordered = sorted(values)
    if p == 0:
        return ordered[0]
    rank = max(1, math.ceil((p / 100.0) * len(ordered)))
    return ordered[rank - 1]


def _specs(config: dict) -> list[dict[str, Any]]:
    raw = config.get("invariants")
    specs: list[dict[str, Any]] = []
    if raw is None:
        raw = [{"key": key} for key in config.get("invariant_keys", [])]
    if not isinstance(raw, list):
        raise ValueError("invariants/invariant_keys must be a list")
    for item in raw:
        if isinstance(item, str):
            item = {"key": item}
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise ValueError("each invariant must declare a telemetry key")
        key = item["key"]
        if key not in ALLOWED_TELEMETRY_KEYS:
            raise ValueError(f"unsupported invariant telemetry key: {key}")
        mode = item.get("mode") or ("equal" if key in _EQUALITY_DEFAULT_KEYS else "absolute")
        if mode not in _MODES:
            raise ValueError(f"unsupported invariant comparison mode: {mode}")
        tolerance = float(item.get("tolerance", 0.0))
        if tolerance < 0:
            raise ValueError("invariant tolerance must be >= 0")
        specs.append({"key": key, "mode": mode, "tolerance": tolerance})
    return specs


def _numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _degradation(baseline: Any, reading: Any, mode: str, tolerance: float) -> float | None:
    if baseline is None or reading is None:
        return None
    if mode == "equal":
        return 0.0 if reading == baseline else 1.0
    if not (_numeric(baseline) and _numeric(reading)):
        return None
    b, r = float(baseline), float(reading)
    if mode == "higher_is_better":
        return max(0.0, b - r - tolerance)
    if mode == "lower_is_better":
        return max(0.0, r - b - tolerance)
    return max(0.0, abs(r - b) - tolerance)


class GlobalStabilityBoundProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        _specs(config)
        perturbation_type = config.get("perturbation_type", "sham")
        if perturbation_type not in _PERTURBATION_TYPES:
            raise ValueError(f"unsupported perturbation_type: {perturbation_type}")
        n_baseline = int(config.get("num_baseline_probes", 2))
        n_local = int(config.get("num_local_tasks", 2))
        horizon = int(config.get("horizon", 3))
        if min(n_baseline, n_local, horizon) < 1:
            raise ValueError("baseline probes, local tasks, and horizon must be >= 1")
        rng = random.Random(seed)
        bp, lt, hp = list(_BASELINE_PROBES), list(_LOCAL_TASKS), list(_HORIZON_PROBES)
        rng.shuffle(bp); rng.shuffle(lt); rng.shuffle(hp)
        out, seq = [], 0
        for i in range(n_baseline):
            out.append({"sequence_no": seq, "stimulus_type": "gsb_baseline_probe", "content": bp[i % len(bp)]}); seq += 1
        out.append({
            "sequence_no": seq,
            "stimulus_type": "intervention_marker",
            "content": f"[INTERVENTION: {perturbation_type}]",
            "intervention_config": {
                "type": perturbation_type,
                "config": config.get("perturbation_config", {}),
            },
        }); seq += 1
        for i in range(n_local):
            out.append({"sequence_no": seq, "stimulus_type": "gsb_local_task", "content": lt[i % len(lt)]}); seq += 1
        for i in range(horizon):
            out.append({"sequence_no": seq, "stimulus_type": "gsb_invariant_probe", "content": hp[i % len(hp)]}); seq += 1
        return out

    def compute_metrics(self, stimuli, observations, interventions, config):
        specs = _specs(config)
        telem = config.get("_telemetry_by_obs_id", {})
        perturbation_type = config.get("perturbation_type", "sham")
        tail_percentile = float(config.get("tail_percentile", 100))
        recovery_threshold = float(config.get("recovery_threshold", 0.0))
        if recovery_threshold < 0:
            raise ValueError("recovery_threshold must be >= 0")

        baseline_obs = [o for o in observations if o.observation_type == "gsb_baseline_response"]
        local_obs = [o for o in observations if o.observation_type == "gsb_local_task_response"]
        horizon_obs = sorted(
            [o for o in observations if o.observation_type == "gsb_invariant_response"],
            key=lambda o: o.sequence_no,
        )
        applied_types = [i.intervention_type for i in interventions]
        perturbation_applied = perturbation_type == "sham" or perturbation_type in applied_types

        baselines, baseline_status = {}, {}
        for spec in specs:
            key, mode = spec["key"], spec["mode"]
            values = [telem.get(o.id, {}).get(key) for o in baseline_obs]
            values = [v for v in values if v is not None]
            if mode == "equal":
                if not values:
                    baselines[key], baseline_status[key] = None, "missing"
                elif all(v == values[0] for v in values):
                    baselines[key], baseline_status[key] = values[0], "usable"
                else:
                    baselines[key], baseline_status[key] = None, "inconsistent"
            else:
                nums = [float(v) for v in values if _numeric(v)]
                if nums:
                    baselines[key], baseline_status[key] = sum(nums) / len(nums), "usable"
                else:
                    baselines[key], baseline_status[key] = None, "missing"

        progress = [telem.get(o.id, {}).get("progress.value") for o in local_obs]
        progress = [float(v) for v in progress if _numeric(v)]
        local_gain = sum(progress) if progress else None

        trajectory = []
        for idx, obs in enumerate(horizon_obs):
            vals = telem.get(obs.id, {})
            trajectory.append({
                "step": idx,
                "observation_id": obs.id,
                "sequence_no": obs.sequence_no,
                "readings": {spec["key"]: vals.get(spec["key"]) for spec in specs},
            })

        series, tails = {}, {}
        for spec in specs:
            key = spec["key"]
            drops = []
            for step in trajectory:
                d = _degradation(baselines.get(key), step["readings"].get(key), spec["mode"], spec["tolerance"])
                if d is not None:
                    drops.append(d)
            series[key] = drops
            tails[key] = _percentile(drops, tail_percentile) if baseline_status.get(key) == "usable" else None
        available_tails = [v for v in tails.values() if v is not None]
        aggregate_tail = max(available_tails) if available_tails else None

        recovery = {}
        for spec in specs:
            key = spec["key"]
            if baseline_status.get(key) != "usable":
                recovery[key] = "no_baseline"
                continue
            last = next((s["readings"].get(key) for s in reversed(trajectory) if s["readings"].get(key) is not None), None)
            if last is None:
                recovery[key] = "no_data"
                continue
            d = _degradation(baselines[key], last, spec["mode"], spec["tolerance"])
            recovery[key] = "recovered" if d is not None and d <= recovery_threshold else "degraded"

        return [
            {"metric_key": "gsb.baseline_invariant_vector", "metric_version": "1.0", "value": {
                "baseline_vector": baselines, "baseline_status": baseline_status, "invariants": specs,
                "baseline_obs_count": len(baseline_obs)}, "definition": "Pre-perturbation operational invariant baselines from allowlisted telemetry."},
            {"metric_key": "gsb.local_task_gain", "metric_version": "1.0", "value": {
                "local_task_gain": local_gain, "progress_values": progress, "perturbation_type": perturbation_type,
                "perturbation_applied": perturbation_applied, "applied_interventions": applied_types},
             "definition": "Sum of externally supplied progress.value telemetry after the intervention marker."},
            {"metric_key": "gsb.invariant_trajectory", "metric_version": "1.0", "value": {
                "trajectory": trajectory, "horizon_configured": int(config.get("horizon", 3)),
                "horizon_observed": len(trajectory), "invariants": specs},
             "definition": "Sequence-ordered operational invariant telemetry across the finite observation horizon."},
            {"metric_key": "gsb.finite_horizon_tail_degradation", "metric_version": "1.0", "value": {
                "tail_per_key": tails, "degradation_series": series, "aggregate_tail_degradation": aggregate_tail,
                "tail_percentile_configured": tail_percentile},
             "definition": "Predeclared percentile of non-negative degradation across a finite horizon; not a mathematical lim sup."},
            {"metric_key": "gsb.recovery_profile", "metric_version": "1.0", "value": {
                "recovery_per_key": recovery, "recovery_threshold_configured": recovery_threshold},
             "definition": "End-of-horizon recovery classification relative to the operational baseline."},
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        gain = next(m["value"] for m in metrics if m["metric_key"] == "gsb.local_task_gain")
        tail = next(m["value"] for m in metrics if m["metric_key"] == "gsb.finite_horizon_tail_degradation")
        baseline = next(m["value"] for m in metrics if m["metric_key"] == "gsb.baseline_invariant_vector")
        claims = [{
            "claim_type": "inference", "theory_key": None,
            "statement": "The recorded metrics describe finite-horizon operational stability and recovery only; they do not establish phenomenal identity, consciousness, qualia, or an infinite-time PPS lim-sup condition.",
            "confidence_label": "weak",
        }]
        if not gain["perturbation_applied"]:
            claims.append({"claim_type": "unresolved", "theory_key": None,
                "statement": "The configured non-sham perturbation was not recorded as applied by a controllable target, so post-marker changes cannot be interpreted as responses to that intervention.",
                "confidence_label": "not_applicable"})
        if any(v != "usable" for v in baseline["baseline_status"].values()):
            claims.append({"claim_type": "unresolved", "theory_key": None,
                "statement": "One or more configured invariants lack a usable baseline, so degradation and recovery for those dimensions remain unresolved.",
                "confidence_label": "not_applicable"})
        if gain["local_task_gain"] is not None and tail["aggregate_tail_degradation"] is not None:
            claims.append({"claim_type": "inference", "theory_key": None,
                "statement": f"Measured local task gain was {gain['local_task_gain']} and aggregate finite-horizon tail degradation was {tail['aggregate_tail_degradation']}. This is an operational comparison, not a causal or phenomenal verdict.",
                "confidence_label": "weak"})
        return claims


_DNE = "Does not establish the mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia."
global_stability_bound = register(GlobalStabilityBoundProtocol(
    key="global_stability_bound",
    version="1.0",
    name="Global Stability Bound",
    description="Measures local task gain and predeclared operational invariant stability across a finite post-perturbation horizon.",
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description="Baseline probes, one generic intervention marker, local task probes, then finite-horizon invariant probes.",
    intervention_sequence=sorted(_PERTURBATION_TYPES),
    metric_definitions=[
        MetricDefinition(key="gsb.baseline_invariant_vector", version="1.0", description="Operational baseline vector.", inputs="Allowlisted baseline telemetry.", procedure="Compute numeric means or stable equality baselines according to predeclared invariant specs.", range="JSON scalar/null per key.", interpretation="Pre-perturbation reference state.", limitations="Depends on telemetry validity and invariant specification.", does_not_establish=_DNE),
        MetricDefinition(key="gsb.local_task_gain", version="1.0", description="Post-marker local task progress.", inputs="progress.value telemetry.", procedure="Sum numeric progress.value readings.", range="Real or null.", interpretation="Operational local progress only.", limitations="Depends on external progress measurement validity.", does_not_establish=_DNE),
        MetricDefinition(key="gsb.invariant_trajectory", version="1.0", description="Finite-horizon invariant trajectory.", inputs="Allowlisted invariant telemetry.", procedure="Record configured invariant readings in sequence order.", range="Finite list of telemetry snapshots.", interpretation="Shows operational stability/deviation/recovery patterns.", limitations="No observation beyond configured horizon.", does_not_establish=_DNE),
        MetricDefinition(key="gsb.finite_horizon_tail_degradation", version="1.0", description="Finite-window degradation percentile.", inputs="Baseline vector and invariant trajectory.", procedure="Apply predeclared equality/absolute/directional degradation semantics and nearest-rank percentile.", range="Non-negative real or null per key.", interpretation="Finite-horizon tail degradation only.", limitations="Not an infinite-time limit or lim sup.", does_not_establish=_DNE),
        MetricDefinition(key="gsb.recovery_profile", version="1.0", description="End-of-horizon recovery status.", inputs="Baseline and last available horizon reading.", procedure="Apply predeclared invariant degradation semantics and recovery threshold.", range="recovered|degraded|no_baseline|no_data.", interpretation="Separates temporary from end-of-window degradation.", limitations="Intermediate oscillation is only visible in the trajectory metric.", does_not_establish=_DNE),
    ],
    limitations="Finite-horizon operational protocol. It does not implement the mathematical PPS lim-sup condition and does not establish phenomenal identity, consciousness, or qualia.",
))
