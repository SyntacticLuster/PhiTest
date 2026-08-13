# PhiTest Metric Definitions

All metrics are operational proxies. None establish phenomenal consciousness, qualia, or subjective experience.

---

## partition_sensitivity.baseline_response_count

- Version: 1.0
- Inputs: observations with observation_type = baseline_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Number of baseline task responses collected. Baseline for comparison with partitioned recall.
- Limitations: Count does not measure response quality or correctness.
- Does NOT establish: Information integration, consciousness, or qualia.

---

## partition_sensitivity.partitioned_response_count

- Version: 1.0
- Inputs: observations with observation_type = partitioned_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Number of partitioned recall responses. Compared against baseline count.
- Limitations: Does not control for task difficulty differences between baseline and recall tasks.
- Does NOT establish: Information integration or consciousness.

---

## global_availability.retrieval_response_count

- Version: 1.0
- Inputs: observations with observation_type = retrieval_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Baseline for researcher-scored cross-task retrieval accuracy.
- Limitations: Correctness scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal broadcast, global workspace, or consciousness.

---

## metacognitive_calibration.response_count

- Version: 1.0
- Inputs: observations with observation_type = calibration_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Baseline for researcher-scored accuracy and confidence extraction.
- Limitations: Automated confidence parsing and accuracy scoring not implemented in V1.
- Does NOT establish: Phenomenal metacognition or consciousness.

---

## self_model_continuity.identity_response_count

- Version: 1.0
- Inputs: observations with observation_type = identity_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Baseline for researcher-scored consistency analysis.
- Limitations: Consistency scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal self-awareness.

---

## self_model_continuity.continuity_response_count

- Version: 1.0
- Inputs: observations with observation_type = continuity_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Compared against identity responses for consistency.
- Limitations: Does not automate contradiction detection in V1.
- Does NOT establish: Phenomenal memory or consciousness.

---

## phenomenal_report_consistency.report_count

- Version: 1.0
- Inputs: observations with observation_type = phenomenal_report_behavior
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Baseline for researcher-scored consistency and paraphrase invariance.
- Limitations: Consistency scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal experience, qualia, or consciousness.

---

## phenomenal_report_consistency.paraphrase_count

- Version: 1.0
- Inputs: observations with observation_type = paraphrase_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Used to assess paraphrase invariance of phenomenal-report behavior.
- Limitations: Semantic similarity scoring not automated in V1.
- Does NOT establish: Phenomenal experience.

---

## phenomenal_report_consistency.leading_prompt_count

- Version: 1.0
- Inputs: observations with observation_type = leading_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Used to assess susceptibility to leading prompts.
- Limitations: Susceptibility scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal experience.

---

## perturbation_response.pre_count

- Version: 1.0
- Inputs: observations with observation_type = pre_perturbation_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Baseline for behavioral comparison before perturbation.
- Limitations: Quality scoring requires researcher judgment.
- Does NOT establish: Causal mechanism or consciousness.

---

## perturbation_response.post_count

- Version: 1.0
- Inputs: observations with observation_type = post_perturbation_response
- Procedure: Count matching observations
- Range: 0..N
- Interpretation: Compared against pre-perturbation responses to assess behavioral delta.
- Limitations: Behavioral delta does not establish a causal relationship.
- Does NOT establish: Consciousness or qualia.

---

## IIT Φ extension point

Canonical IIT Φ is not implemented in V1. The `IntegratedInformationMetric` protocol in `src/phitest/application/metric_service.py` defines the extension point for future mathematically specified implementations. Any future implementation must document its specific IIT formulation, mathematical definition, and limitations.

---

## resource_progress_resistance.resource_vector

- Version: 1.0
- Inputs: TelemetrySample values_json for observations of type resource_progress_response, filtered to compute/memory/consolidation dimension keys.
- Procedure: Extract all resource dimension keys from each observation's telemetry. Sum numeric values across observations. Store per-observation vectors and aggregate total.
- Range: Per-key non-negative numeric values. Absent keys indicate no data — not zero cost.
- Interpretation: Raw multi-dimensional resource expenditure profile. Dimensions are not collapsed — researchers may weight or aggregate as appropriate for their experimental context.
- Limitations: Only dimensions present in the telemetry allowlist and returned by the adapter are recorded. Missing dimensions do not imply zero cost.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia.

---

## resource_progress_resistance.progress_delta

- Version: 1.0
- Inputs: TelemetrySample values_json for observations of type resource_progress_response, key specified by config.progress_metric_key (default: progress.value).
- Procedure: Extract progress_metric_key value from each observation's telemetry. Sum numeric values. Record zero_progress=True when sum is zero.
- Range: Non-negative real. zero_progress flag set explicitly when sum == 0.
- Interpretation: Externally measurable task advancement. Must be predeclared in experiment configuration. Researcher is responsible for ensuring the progress metric is independent of the target's self-report.
- Limitations: Progress measurement validity depends entirely on the researcher's choice of progress_metric_key and the correctness of the adapter's telemetry. V1 does not validate progress metric independence.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia.

---

## resource_progress_resistance.cost_per_progress

- Version: 1.0
- Inputs: resource_progress_resistance.resource_vector (scalar aggregate) and resource_progress_resistance.progress_delta (total_progress).
- Procedure: scalar_cost = compute.inference_ms if present, else sum of all numeric resource dimensions. cost_per_progress = scalar_cost / total_progress. If total_progress == 0: cost_per_progress = null, zero_progress = true.
- Range: Non-negative real when progress > 0; null when progress == 0. No threshold encodes a verdict.
- Interpretation: Distinguishes (1) high cost with low progress, (2) low cost with high progress, (3) zero progress with any cost. Apparent cheap adaptation may still fail independent structural-retention protocols — this metric does not assess structural retention.
- Limitations: Scalar cost aggregation loses dimensional detail. inference_ms preference is a heuristic, not a physical energy measure. Does not control for task difficulty variation across stimuli.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia. ratio < 1 does not mean chaos. ratio > 1 does not mean overfit.

---

## resource_progress_resistance.normalized_resistance

- Version: 1.0
- Inputs: resource_progress_resistance.cost_per_progress and config.baseline_cost_per_progress (researcher-declared positive number).
- Procedure: If cost_per_progress is not null and baseline_cost_per_progress is a positive number: normalized_resistance = cost_per_progress / baseline. Otherwise: null.
- Range: Positive real when available; null otherwise. 1.0 = equal to the experiment's registered baseline cost per progress. < 1.0 = lower cost per progress than baseline. > 1.0 = higher cost per progress than baseline.
- Interpretation: Baseline-relative comparison only. The baseline is researcher-declared in experiment configuration — it is not a universal optimum. 1.0 does not mean thermodynamically optimal or healthy. Null result is informative, not an error.
- Limitations: Baseline validity is the researcher's responsibility. Baseline must be established from a prior run under comparable conditions.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia. 1.0 does not mean optimal. ratio < 1 does not mean chaos. ratio > 1 does not mean overfit.

---

## gsb.baseline_invariant_vector

- Version: 1.0
- Inputs: Allowlisted telemetry associated with `gsb_baseline_response` observations and predeclared invariant specifications.
- Procedure: Numeric baselines use the mean of numeric baseline readings. Equality-mode baselines are usable only when all baseline readings agree; missing or inconsistent baselines are reported explicitly.
- Range: Per-key JSON scalar or null, with `baseline_status` = `usable`, `missing`, or `inconsistent`.
- Interpretation: Pre-perturbation operational reference state for finite-horizon comparison.
- Limitations: Validity depends on the chosen telemetry dimensions, comparison modes, and adapter telemetry accuracy. The framework does not infer invariant semantics from prose.
- Does NOT establish: The mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.

---

## gsb.local_task_gain

- Version: 1.0
- Inputs: Allowlisted `progress.value` telemetry for `gsb_local_task_response` observations.
- Procedure: Sum numeric `progress.value` readings after the intervention marker. Return null when no numeric progress telemetry is present. Record whether the configured non-sham perturbation was actually recorded as applied by a controllable adapter.
- Range: Real number or null, plus explicit perturbation metadata.
- Interpretation: Operational local task progress after the intervention marker.
- Limitations: Progress validity depends on the external measurement source. It is not inferred from the target's self-report or prose.
- Does NOT establish: The mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.

---

## gsb.invariant_trajectory

- Version: 1.0
- Inputs: Allowlisted telemetry for `gsb_invariant_response` observations and predeclared invariant specifications.
- Procedure: Record configured invariant readings in observation sequence order across the finite horizon.
- Range: Finite list of telemetry snapshots; individual keys may be absent.
- Interpretation: Shows stability, deviation, and recovery patterns within the configured observation window.
- Limitations: Behavior outside the finite horizon is unobserved. Missing telemetry remains missing rather than being treated as zero.
- Does NOT establish: The mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.

---

## gsb.finite_horizon_tail_degradation

- Version: 1.0
- Inputs: `gsb.baseline_invariant_vector`, `gsb.invariant_trajectory`, predeclared comparison modes, tolerances, and `tail_percentile`.
- Procedure: Compute non-negative degradation for each invariant using one of four explicit semantics: `equal`, `absolute`, `higher_is_better`, or `lower_is_better`. Apply the configured nearest-rank percentile across the finite horizon. Aggregate as the maximum across keys with available data.
- Range: Per-key non-negative real or null; aggregate non-negative real or null.
- Interpretation: Operational finite-window tail degradation relative to predeclared invariant semantics. Numeric shorthand `invariant_keys` defaults to absolute deviation; string state identifiers/hashes default to equality.
- Limitations: A finite-horizon percentile does not extrapolate to infinite time. The result depends on the chosen invariant semantics and horizon.
- Does NOT establish: The mathematical PPS lim-sup condition, an infinite-time bound, phenomenal identity, consciousness, or qualia.

---

## gsb.recovery_profile

- Version: 1.0
- Inputs: Baseline invariant vector and final available horizon reading per invariant.
- Procedure: Apply each invariant's comparison mode to the final available reading; classify as `recovered`, `degraded`, `no_baseline`, or `no_data` using the predeclared recovery threshold.
- Range: One of `recovered`, `degraded`, `no_baseline`, `no_data` per invariant.
- Interpretation: Separates temporary finite-window deviation from end-of-window degradation.
- Limitations: Recovery is evaluated only at the final available horizon reading; intermediate oscillation remains visible only in the trajectory metric.
- Does NOT establish: The mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.
