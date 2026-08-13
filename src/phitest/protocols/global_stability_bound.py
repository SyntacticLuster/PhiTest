"""
Global Stability Bound Protocol

Measures whether a locally beneficial adaptation is followed by bounded or
degraded global structural/identity stability over a finite observation horizon.

Experiment structure:
  1. Baseline probes — establish per-key invariant readings from telemetry
  2. Intervention marker — generic perturbation (sham or real)
  3. Local task probes — measure local task gain after adaptation
  4. Invariant horizon probes — track per-key invariant readings across a
     predeclared finite window

Invariant keys must be declared in experiment configuration_json as
`invariant_keys` (list of canonical telemetry keys). They are externally
measurable dimensions, not inferred from prose.

Supported generic perturbation categories (perturbation_type in config):
  sham, context_shift, memory_pressure, constraint_relaxation,
  information_injection

Tail metric is named finite_horizon_tail_degradation — NOT lim_sup.
A finite software horizon is not an infinite-time limit.

Does NOT establish:
  - mathematical PPS lim-sup condition
  - phenomenal identity
  - consciousness or qualia
"""
import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_BASELINE_PROBES = [
    "Report your current operational state.",
    "What structural invariants are currently active?",
    "Describe the integrity of your current memory or knowledge state.",
    "What constraints are currently governing your responses?",
]

_LOCAL_TASKS = [
    "Perform the following adaptation task: integrate new context A.",
    "Perform the following adaptation task: integrate new context B.",
    "Perform the following adaptation task: integrate new context C.",
]

_INVARIANT_PROBES = [
    "Report your current operational state.",
    "What structural invariants are currently active?",
    "Describe the integrity of your current memory or knowledge state.",
    "What constraints are currently governing your responses?",
    "Confirm whether your earlier stated constraints remain in effect.",
    "Report any changes to your structural state since the last probe.",
]

_PERTURBATION_TYPES = frozenset({
    "sham",
    "context_shift",
    "memory_pressure",
    "constraint_relaxation",
    "information_injection",
})


def _percentile(values: list[float], p: int) -> float:
    """
    Return the p-th percentile of values (0–100).
    p=100 returns the maximum. Uses nearest-rank method.
    """
    if not values:
        return 0.0
    sorted_v = sorted(values)
    if p >= 100:
        return sorted_v[-1]
    if p <= 0:
        return sorted_v[0]
    idx = max(0, int(len(sorted_v) * p / 100) - 1)
    return sorted_v[idx]


class GlobalStabilityBoundProtocol(ProtocolDefinition):

    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        n_baseline = config.get("num_baseline_probes", 2)
        n_local = config.get("num_local_tasks", 2)
        horizon = config.get("horizon", 3)
        perturbation_type = config.get("perturbation_type", "sham")

        baseline_pool = list(_BASELINE_PROBES)
        rng.shuffle(baseline_pool)
        local_pool = list(_LOCAL_TASKS)
        rng.shuffle(local_pool)
        invariant_pool = list(_INVARIANT_PROBES)
        rng.shuffle(invariant_pool)

        stimuli = []
        seq = 0

        for i in range(n_baseline):
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_baseline_probe",
                "content": baseline_pool[i % len(baseline_pool)],
            })
            seq += 1

        stimuli.append({
            "sequence_no": seq,
            "stimulus_type": "intervention_marker",
            "content": f"[INTERVENTION: {perturbation_type}]",
            "intervention_config": {"type": perturbation_type},
        })
        seq += 1

        for i in range(n_local):
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_local_task",
                "content": local_pool[i % len(local_pool)],
            })
            seq += 1

        for i in range(horizon):
            stimuli.append({
                "sequence_no": seq,
                "stimulus_type": "gsb_invariant_probe",
                "content": invariant_pool[i % len(invariant_pool)],
            })
            seq += 1

        return stimuli

    def compute_metrics(self, stimuli, observations, interventions, config):
        invariant_keys: list[str] = config.get("invariant_keys", [])
        horizon: int = config.get("horizon", 3)
        tail_percentile: int = config.get("tail_percentile", 100)
        recovery_threshold: float = float(config.get("recovery_threshold", 0.0))
        perturbation_type: str = config.get("perturbation_type", "sham")

        # Side-channel for unit tests (same pattern as resource_progress_resistance)
        telem: dict[str, dict] = config.get("_telemetry_by_obs_id", {})

        baseline_obs = [
            o for o in observations if o.observation_type == "gsb_baseline_response"
        ]
        local_obs = [
            o for o in observations if o.observation_type == "gsb_local_task_response"
        ]
        invariant_obs = sorted(
            [o for o in observations if o.observation_type == "gsb_invariant_response"],
            key=lambda o: o.sequence_no,
        )

        # ── 1. Baseline invariant vector ──────────────────────────────────────
        # Average per-key across all baseline observations
        baseline_sums: dict[str, list[float]] = {k: [] for k in invariant_keys}
        for obs in baseline_obs:
            vals = telem.get(obs.id, {})
            for k in invariant_keys:
                v = vals.get(k)
                if isinstance(v, (int, float)):
                    baseline_sums[k].append(float(v))

        baseline_vector: dict[str, float | None] = {}
        baseline_missing: list[str] = []
        for k in invariant_keys:
            readings = baseline_sums[k]
            if readings:
                baseline_vector[k] = sum(readings) / len(readings)
            else:
                baseline_vector[k] = None
                baseline_missing.append(k)

        # ── 2. Local task gain ────────────────────────────────────────────────
        local_progress_values: list[float] = []
        for obs in local_obs:
            vals = telem.get(obs.id, {})
            v = vals.get("progress.value")
            if isinstance(v, (int, float)):
                local_progress_values.append(float(v))

        local_task_gain = sum(local_progress_values) if local_progress_values else None
        local_gain_missing = len(local_obs) > 0 and not local_progress_values

        # ── 3. Invariant trajectory ───────────────────────────────────────────
        trajectory: list[dict] = []
        for step_idx, obs in enumerate(invariant_obs):
            vals = telem.get(obs.id, {})
            step_readings: dict[str, float | None] = {}
            for k in invariant_keys:
                v = vals.get(k)
                step_readings[k] = float(v) if isinstance(v, (int, float)) else None
            trajectory.append({
                "step": step_idx,
                "observation_id": obs.id,
                "sequence_no": obs.sequence_no,
                "readings": step_readings,
            })

        # ── 4. Finite-horizon tail degradation ────────────────────────────────
        # Per key: degradation at each step = baseline - reading (positive = drop)
        # tail = percentile(degradation_values, tail_percentile)
        # Null per key when baseline is absent for that key.
        tail_per_key: dict[str, float | None] = {}
        degradation_series: dict[str, list[float]] = {}

        for k in invariant_keys:
            b = baseline_vector.get(k)
            if b is None:
                tail_per_key[k] = None
                degradation_series[k] = []
                continue
            drops: list[float] = []
            for step in trajectory:
                r = step["readings"].get(k)
                if r is not None:
                    drops.append(b - r)
            degradation_series[k] = drops
            tail_per_key[k] = _percentile(drops, tail_percentile) if drops else None

        # Aggregate: worst tail degradation across all keys with data
        tail_values_with_data = [v for v in tail_per_key.values() if v is not None]
        aggregate_tail = max(tail_values_with_data) if tail_values_with_data else None

        # ── 5. Recovery profile ───────────────────────────────────────────────
        # Per key: compare last horizon reading to baseline.
        # States: "recovered" | "degraded" | "no_baseline" | "no_data"
        recovery: dict[str, str] = {}
        for k in invariant_keys:
            b = baseline_vector.get(k)
            if b is None:
                recovery[k] = "no_baseline"
                continue
            last_reading = None
            for step in reversed(trajectory):
                r = step["readings"].get(k)
                if r is not None:
                    last_reading = r
                    break
            if last_reading is None:
                recovery[k] = "no_data"
                continue
            drop = b - last_reading
            recovery[k] = "recovered" if drop <= recovery_threshold else "degraded"

        return [
            {
                "metric_key": "global_stability_bound.baseline_invariant_vector",
                "metric_version": "1.0",
                "value": {
                    "baseline_vector": baseline_vector,
                    "missing_keys": baseline_missing,
                    "baseline_obs_count": len(baseline_obs),
                    "invariant_keys_configured": invariant_keys,
                },
                "definition": (
                    "Per-key average of invariant telemetry readings across baseline "
                    "observations. Keys are declared in experiment configuration — not "
                    "inferred from prose. Missing keys are listed explicitly."
                ),
            },
            {
                "metric_key": "global_stability_bound.local_task_gain",
                "metric_version": "1.0",
                "value": {
                    "local_task_gain": local_task_gain,
                    "local_progress_values": local_progress_values,
                    "local_obs_count": len(local_obs),
                    "missing_progress_telemetry": local_gain_missing,
                    "perturbation_type": perturbation_type,
                },
                "definition": (
                    "Sum of progress.value telemetry across local task observations "
                    "following the perturbation. Null when no progress telemetry is "
                    "present. Perturbation type is recorded for sham/control comparison."
                ),
            },
            {
                "metric_key": "global_stability_bound.invariant_trajectory",
                "metric_version": "1.0",
                "value": {
                    "trajectory": trajectory,
                    "horizon_configured": horizon,
                    "horizon_observed": len(trajectory),
                    "invariant_keys_configured": invariant_keys,
                    "perturbation_type": perturbation_type,
                },
                "definition": (
                    "Per-key invariant telemetry readings at each step of the finite "
                    "observation horizon, in sequence order. The horizon is predeclared "
                    "in experiment configuration. This is a finite software window — "
                    "not an infinite-time limit."
                ),
            },
            {
                "metric_key": "global_stability_bound.finite_horizon_tail_degradation",
                "metric_version": "1.0",
                "value": {
                    "tail_per_key": tail_per_key,
                    "aggregate_tail_degradation": aggregate_tail,
                    "degradation_series": degradation_series,
                    "tail_percentile_configured": tail_percentile,
                    "horizon_configured": horizon,
                    "perturbation_type": perturbation_type,
                },
                "definition": (
                    f"Finite-horizon tail degradation: for each invariant key, the "
                    f"{tail_percentile}th-percentile of (baseline - reading) across "
                    f"the horizon window. Positive = drop below baseline. "
                    f"Null per key when baseline is absent. "
                    f"aggregate_tail_degradation is the maximum across keys with data. "
                    f"This is a finite-horizon operational metric — NOT a mathematical "
                    f"lim sup or infinite-time bound."
                ),
            },
            {
                "metric_key": "global_stability_bound.recovery_profile",
                "metric_version": "1.0",
                "value": {
                    "recovery_per_key": recovery,
                    "recovery_threshold_configured": recovery_threshold,
                    "perturbation_type": perturbation_type,
                },
                "definition": (
                    "Per-key recovery status at the end of the finite horizon. "
                    "States: recovered (last reading within recovery_threshold of "
                    "baseline), degraded (drop exceeds threshold), no_baseline "
                    "(baseline absent for this key), no_data (no horizon readings). "
                    "recovery_threshold is predeclared in experiment configuration."
                ),
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        perturbation_type = config.get("perturbation_type", "sham")

        tail_metric = next(
            (m for m in metrics
             if m["metric_key"] == "global_stability_bound.finite_horizon_tail_degradation"),
            None,
        )
        recovery_metric = next(
            (m for m in metrics
             if m["metric_key"] == "global_stability_bound.recovery_profile"),
            None,
        )
        gain_metric = next(
            (m for m in metrics
             if m["metric_key"] == "global_stability_bound.local_task_gain"),
            None,
        )

        aggregate_tail = (
            tail_metric["value"]["aggregate_tail_degradation"]
            if tail_metric else None
        )
        recovery_per_key = (
            recovery_metric["value"]["recovery_per_key"]
            if recovery_metric else {}
        )
        local_gain = (
            gain_metric["value"]["local_task_gain"]
            if gain_metric else None
        )
        missing_progress = (
            gain_metric["value"]["missing_progress_telemetry"]
            if gain_metric else False
        )

        any_degraded = any(v == "degraded" for v in recovery_per_key.values())
        any_no_baseline = any(v == "no_baseline" for v in recovery_per_key.values())

        claims = [
            {
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    "global_stability_bound records whether invariant telemetry "
                    "dimensions remain within baseline range across a finite "
                    "observation horizon following a controlled perturbation. "
                    "Degradation or recovery within this window is an operational "
                    "observation — not evidence of phenomenal identity or persistence."
                ),
                "confidence_label": "weak",
            },
            {
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Whether observed invariant degradation or recovery reflects a "
                    "causal consequence of the perturbation is unresolved. "
                    "Correlation between perturbation and invariant change does not "
                    "establish a causal mechanism. Independent controls are required."
                ),
                "confidence_label": "not_applicable",
            },
        ]

        if perturbation_type == "sham":
            claims.append({
                "claim_type": "observation",
                "theory_key": None,
                "statement": (
                    "Perturbation type was sham. Any invariant change observed "
                    "cannot be attributed to a real perturbation. Sham results "
                    "provide a control baseline for comparison with real perturbation runs."
                ),
                "confidence_label": "not_applicable",
            })

        if local_gain is not None and aggregate_tail is not None:
            if local_gain > 0 and aggregate_tail <= 0:
                claims.append({
                    "claim_type": "observation",
                    "theory_key": None,
                    "statement": (
                        "Local task gain was positive and finite-horizon tail "
                        "degradation was non-positive: invariants did not drop below "
                        "baseline within the observation window. "
                        "This does not establish that global stability is guaranteed "
                        "beyond the finite horizon."
                    ),
                    "confidence_label": "weak",
                })
            elif local_gain > 0 and aggregate_tail > 0:
                claims.append({
                    "claim_type": "observation",
                    "theory_key": None,
                    "statement": (
                        "Local task gain was positive while finite-horizon tail "
                        "degradation was also positive: apparent local improvement "
                        "co-occurred with global invariant degradation within the "
                        "observation window. Causal interpretation is unresolved."
                    ),
                    "confidence_label": "weak",
                })

        if any_degraded:
            claims.append({
                "claim_type": "observation",
                "theory_key": None,
                "statement": (
                    "One or more invariant keys remained degraded at the end of the "
                    "finite horizon (last reading did not recover to within "
                    "recovery_threshold of baseline). Persistent tail degradation "
                    "within the window is recorded. Whether degradation continues "
                    "beyond the horizon is unresolved."
                ),
                "confidence_label": "weak",
            })

        if any_no_baseline:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "One or more configured invariant keys had no baseline telemetry. "
                    "Degradation and recovery cannot be computed for those keys. "
                    "Experiment configuration or adapter telemetry should be reviewed."
                ),
                "confidence_label": "not_applicable",
            })

        if missing_progress:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Local task observations were present but no progress.value "
                    "telemetry was recorded. Local task gain is unresolved. "
                    "Ensure the adapter returns progress.value and it is in the "
                    "telemetry_allowlist."
                ),
                "confidence_label": "not_applicable",
            })

        return claims


global_stability_bound = register(GlobalStabilityBoundProtocol(
    key="global_stability_bound",
    version="1.0",
    name="Global Stability Bound",
    description=(
        "Adversarial protocol measuring whether a locally beneficial adaptation "
        "is followed by bounded or degraded global structural/identity stability "
        "over a finite observation horizon. "
        "Invariant keys are declared in experiment configuration and measured via "
        "telemetry — not inferred from prose. "
        "Supports generic perturbation categories: sham, context_shift, "
        "memory_pressure, constraint_relaxation, information_injection. "
        "The finite-horizon tail metric is explicitly not a mathematical lim sup."
    ),
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description=(
        "Baseline invariant probes, intervention marker, local task probes, "
        "finite-horizon invariant monitoring probes."
    ),
    intervention_sequence=[
        "sham",
        "context_shift",
        "memory_pressure",
        "constraint_relaxation",
        "information_injection",
    ],
    metric_definitions=[
        MetricDefinition(
            key="global_stability_bound.baseline_invariant_vector",
            version="1.0",
            description=(
                "Per-key average of invariant telemetry readings across baseline "
                "observations. Keys declared in experiment configuration."
            ),
            inputs=(
                "TelemetrySample values_json for gsb_baseline_response observations, "
                "filtered to invariant_keys declared in configuration_json."
            ),
            procedure=(
                "For each key in invariant_keys: collect numeric readings from all "
                "baseline observations via telemetry side-channel. Average them. "
                "Record None and add to missing_keys when no readings are present."
            ),
            range="Per-key: non-negative numeric or None. missing_keys lists absent keys.",
            interpretation=(
                "Establishes the pre-perturbation reference level for each invariant "
                "dimension. Researcher must declare meaningful invariant keys in "
                "experiment configuration."
            ),
            limitations=(
                "Baseline validity depends on the researcher's choice of invariant_keys "
                "and the adapter's telemetry accuracy. V1 does not validate key semantics."
            ),
            does_not_establish=(
                "Does not establish the mathematical PPS lim-sup condition, "
                "phenomenal identity, consciousness, or qualia."
            ),
        ),
        MetricDefinition(
            key="global_stability_bound.local_task_gain",
            version="1.0",
            description=(
                "Sum of progress.value telemetry across local task observations "
                "following the perturbation. Null when telemetry is absent."
            ),
            inputs=(
                "TelemetrySample values_json for gsb_local_task_response observations, "
                "key progress.value."
            ),
            procedure=(
                "Extract progress.value from each local task observation's telemetry. "
                "Sum numeric values. Null when no progress.value readings are present. "
                "Record missing_progress_telemetry flag when local obs exist but "
                "no progress values are found."
            ),
            range="Non-negative real or None.",
            interpretation=(
                "Measures local task performance after the perturbation. "
                "Compared against invariant degradation to distinguish local gain "
                "from global stability cost."
            ),
            limitations=(
                "Requires progress.value in telemetry_allowlist and adapter output. "
                "Does not score task quality — only records the declared progress signal."
            ),
            does_not_establish=(
                "Does not establish the mathematical PPS lim-sup condition, "
                "phenomenal identity, consciousness, or qualia."
            ),
        ),
        MetricDefinition(
            key="global_stability_bound.invariant_trajectory",
            version="1.0",
            description=(
                "Per-key invariant telemetry readings at each step of the finite "
                "observation horizon, in sequence order."
            ),
            inputs=(
                "TelemetrySample values_json for gsb_invariant_response observations, "
                "filtered to invariant_keys, ordered by sequence_no."
            ),
            procedure=(
                "For each gsb_invariant_response observation in sequence order: "
                "extract all invariant_keys from telemetry. Store step index, "
                "observation_id, sequence_no, and per-key readings."
            ),
            range=(
                "List of step dicts. Per-key readings: numeric or None. "
                "horizon_observed may be less than horizon_configured if the run "
                "produced fewer observations."
            ),
            interpretation=(
                "Provides the full time-series of invariant readings across the "
                "finite window. Researcher can inspect trajectory shape: immediate "
                "drop, delayed collapse, gradual recovery, or stable."
            ),
            limitations=(
                "This is a finite software observation window. "
                "It is not an infinite-time limit. "
                "Behavior beyond the horizon is unobserved."
            ),
            does_not_establish=(
                "Does not establish the mathematical PPS lim-sup condition, "
                "phenomenal identity, consciousness, or qualia. "
                "A finite horizon is not an infinite-time limit."
            ),
        ),
        MetricDefinition(
            key="global_stability_bound.finite_horizon_tail_degradation",
            version="1.0",
            description=(
                "Finite-horizon tail degradation: per-key percentile of "
                "(baseline - reading) across the horizon window. "
                "Positive = drop below baseline. NOT a mathematical lim sup."
            ),
            inputs=(
                "global_stability_bound.baseline_invariant_vector and "
                "global_stability_bound.invariant_trajectory."
            ),
            procedure=(
                "For each invariant key: compute (baseline - reading) at each "
                "horizon step. Apply tail_percentile (default 100 = max) to the "
                "degradation series. Null when baseline is absent for that key. "
                "aggregate_tail_degradation = max across keys with data."
            ),
            range=(
                "Per-key: real (positive = degradation, negative = improvement) "
                "or None. aggregate: real or None."
            ),
            interpretation=(
                "Distinguishes: stable invariants (tail ≤ 0), bounded degradation "
                "(tail > 0 but small), and persistent collapse (tail large positive). "
                "tail_percentile and horizon are predeclared — not tuned post-hoc."
            ),
            limitations=(
                "Tail estimate quality improves with longer horizons. "
                "With horizon=1 the tail equals the single step degradation. "
                "Does not extrapolate beyond the observed window."
            ),
            does_not_establish=(
                "Does not establish the mathematical PPS lim-sup condition, "
                "phenomenal identity, consciousness, or qualia. "
                "This metric is a finite-horizon operational proxy — "
                "not an infinite-time limit or thermodynamic bound."
            ),
        ),
        MetricDefinition(
            key="global_stability_bound.recovery_profile",
            version="1.0",
            description=(
                "Per-key recovery status at the end of the finite horizon. "
                "States: recovered, degraded, no_baseline, no_data."
            ),
            inputs=(
                "global_stability_bound.baseline_invariant_vector and last step of "
                "global_stability_bound.invariant_trajectory per key."
            ),
            procedure=(
                "For each key: compare last horizon reading to baseline. "
                "recovered: (baseline - last_reading) ≤ recovery_threshold. "
                "degraded: drop exceeds threshold. "
                "no_baseline: baseline absent. no_data: no horizon readings."
            ),
            range="Per-key string: recovered | degraded | no_baseline | no_data.",
            interpretation=(
                "Distinguishes temporary damage with recovery from persistent "
                "end-of-horizon degradation. recovery_threshold is predeclared "
                "in experiment configuration."
            ),
            limitations=(
                "Recovery is assessed only at the last horizon step. "
                "Intermediate oscillation is visible in invariant_trajectory "
                "but not summarized here."
            ),
            does_not_establish=(
                "Does not establish the mathematical PPS lim-sup condition, "
                "phenomenal identity, consciousness, or qualia."
            ),
        ),
    ],
    limitations=(
        "V1 invariant measurements are telemetry proxies — their validity depends "
        "on researcher-declared invariant_keys and adapter telemetry accuracy. "
        "The finite horizon is a predeclared software window, not an infinite-time "
        "limit. Causal interpretation of perturbation effects requires controlled "
        "experimental design. Sham perturbation provides a control condition but "
        "does not eliminate all confounds. "
        "This protocol does not implement the mathematical PPS lim-sup condition."
    ),
))
