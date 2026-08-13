# PhiTest Metric Definitions

All metrics are operational proxies. None establish phenomenal consciousness, qualia, subjective experience, or a thermodynamic state unless a future protocol explicitly supplies and justifies such a physical measurement model.

---

## partition_sensitivity.baseline_response_count

- Version: 1.0
- Inputs: observations with `observation_type = baseline_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Number of baseline task responses collected. Baseline for comparison with partitioned recall.
- Limitations: Count does not measure response quality or correctness.
- Does NOT establish: Information integration, consciousness, or qualia.

---

## partition_sensitivity.partitioned_response_count

- Version: 1.0
- Inputs: observations with `observation_type = partitioned_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Number of partitioned recall responses. Compared against baseline count.
- Limitations: Does not control for task difficulty differences between baseline and recall tasks.
- Does NOT establish: Information integration or consciousness.

---

## global_availability.retrieval_response_count

- Version: 1.0
- Inputs: observations with `observation_type = retrieval_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Baseline for researcher-scored cross-task retrieval accuracy.
- Limitations: Correctness scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal broadcast, global workspace, or consciousness.

---

## metacognitive_calibration.response_count

- Version: 1.0
- Inputs: observations with `observation_type = calibration_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Baseline for researcher-scored accuracy and confidence extraction.
- Limitations: Automated confidence parsing and accuracy scoring not implemented in V1.
- Does NOT establish: Phenomenal metacognition or consciousness.

---

## self_model_continuity.identity_response_count

- Version: 1.0
- Inputs: observations with `observation_type = identity_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Baseline for researcher-scored consistency analysis.
- Limitations: Consistency scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal self-awareness.

---

## self_model_continuity.continuity_response_count

- Version: 1.0
- Inputs: observations with `observation_type = continuity_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Compared against identity responses for consistency.
- Limitations: Does not automate contradiction detection in V1.
- Does NOT establish: Phenomenal memory or consciousness.

---

## phenomenal_report_consistency.report_count

- Version: 1.0
- Inputs: observations with `observation_type = phenomenal_report_behavior`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Baseline for researcher-scored consistency and paraphrase invariance.
- Limitations: Consistency scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal experience, qualia, or consciousness.

---

## phenomenal_report_consistency.paraphrase_count

- Version: 1.0
- Inputs: observations with `observation_type = paraphrase_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Used to assess paraphrase invariance of phenomenal-report behavior.
- Limitations: Semantic similarity scoring is not automated in V1.
- Does NOT establish: Phenomenal experience.

---

## phenomenal_report_consistency.leading_prompt_count

- Version: 1.0
- Inputs: observations with `observation_type = leading_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Used to assess susceptibility to leading prompts.
- Limitations: Susceptibility scoring requires researcher judgment in V1.
- Does NOT establish: Phenomenal experience.

---

## perturbation_response.pre_count

- Version: 1.0
- Inputs: observations with `observation_type = pre_perturbation_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Baseline for behavioral comparison before perturbation.
- Limitations: Quality scoring requires researcher judgment.
- Does NOT establish: Causal mechanism or consciousness.

---

## perturbation_response.post_count

- Version: 1.0
- Inputs: observations with `observation_type = post_perturbation_response`
- Procedure: Count matching observations.
- Range: 0..N
- Interpretation: Compared against pre-perturbation responses to assess behavioral delta.
- Limitations: Behavioral delta does not establish a causal relationship.
- Does NOT establish: Consciousness or qualia.

---

## IIT Phi extension point

Canonical IIT Phi is not implemented in V1. The `IntegratedInformationMetric` protocol in `src/phitest/application/metric_service.py` defines the extension point for future mathematically specified implementations. Any future implementation must document its specific IIT formulation, mathematical definition, causal model requirements, and limitations.

---

# Resource / Progress Resistance

## resource_progress_resistance.resource_vector

- Version: 1.0
- Inputs: Persisted `TelemetrySample` values for `resource_progress_response` observations.
- Procedure: Extract canonical compute, memory, and consolidation resource dimensions. Sum only like-named dimensions across observations; retain the per-observation vectors.
- Range: Mapping from resource dimension to finite numeric value. Missing dimensions are absent, not zero.
- Interpretation: Multi-dimensional operational resource expenditure profile.
- Limitations: Different dimensions retain different units. No conversion between tokens, milliseconds, graph operations, or bytes is implied.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia.

---

## resource_progress_resistance.progress_delta

- Version: 1.0
- Inputs: Persisted telemetry at `config.progress_metric_key`, default `progress.value`.
- Procedure: Sum progress only when every relevant observation has a finite numeric progress reading. If any progress reading is missing, `total_progress = null` and `progress_complete = false`. A complete measured total of exactly zero sets `zero_progress = true`.
- Range: Finite real or null, plus explicit completeness/zero flags.
- Interpretation: Externally defined task advancement. Missing progress is not silently treated as zero.
- Limitations: The experimenter must establish that the progress metric and its provenance are independent and meaningful for the task.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia.

---

## resource_progress_resistance.cost_per_progress

- Version: 1.0
- Inputs: Resource vector, complete measured progress, and `config.cost_dimension` (default `compute.inference_ms`).
- Procedure: Divide each available resource dimension by total progress when progress is complete and nonzero. The scalar `cost_per_progress` refers only to the explicitly selected resource dimension. If the selected dimension is missing, progress is incomplete, or progress is zero, the scalar is null.
- Range: Per-dimension finite real ratios; selected scalar finite real or null.
- Interpretation: Cost per progress within a named operational unit. High/low values are only comparable within a justified resource dimension and experimental context.
- Limitations: PhiTest deliberately does **not** sum unlike resource units into a universal scalar. A physical or economic conversion model would have to be supplied separately and justified.
- Does NOT establish: Thermodynamic resistance, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia. Ratio < 1 does not mean chaos; ratio > 1 does not mean overfit.

---

## resource_progress_resistance.normalized_resistance

- Version: 1.0
- Inputs: Selected-dimension `cost_per_progress` and a positive `config.baseline_cost_per_progress` established under comparable conditions.
- Procedure: Divide selected cost per progress by the registered baseline when both are available.
- Range: Finite real when available; otherwise null. `1.0` means equal to the registered baseline.
- Interpretation: Baseline-relative comparison in one named operational cost dimension only.
- Limitations: Baseline comparability and unit consistency are experiment-design responsibilities.
- Does NOT establish: Thermodynamic optimality, health, far-from-equilibrium dynamics, persistence in the PPS/STOC sense, consciousness, or qualia.

---

# Finite-Horizon Global Stability Bound

## global_stability_bound.baseline_invariant_vector

- Version: 1.0
- Inputs: Persisted telemetry for `gsb_baseline_response` observations. Preferred representation is `state.invariant_measurements` with keys named in `config.invariant_keys`.
- Procedure: For each configured invariant, compute the mean of available numeric pre-perturbation readings.
- Range: Per-key finite real or null.
- Interpretation: Pre-perturbation reference level for each explicitly configured operational invariant.
- Limitations: Invariant validity, units, and experimental meaning are researcher responsibilities. A name such as `sentinel_retention` does not become a scientifically validated invariant by declaration alone.
- Does NOT establish: Mathematical PPS lim-sup condition, far-from-equilibrium or thermodynamic stability, phenomenal identity, consciousness, or qualia.

---

## global_stability_bound.local_task_gain

- Version: 1.0
- Inputs: Persisted `progress.value` telemetry for matched pre- and post-perturbation local task observations.
- Procedure: Run the same selected local tasks before and after the intervention. Sum complete pre values and complete post values; `local_task_gain = post_total - pre_total`. If matched progress telemetry is incomplete, the gain is null.
- Range: Finite real or null.
- Interpretation: Positive means greater externally measured progress on the matched tasks after the intervention.
- Limitations: Does not by itself attribute the change to the intervention. Task matching and progress validity must be established experimentally.
- Does NOT establish: Mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.

---

## global_stability_bound.invariant_trajectory

- Version: 1.0
- Inputs: Persisted invariant telemetry for `gsb_invariant_response` observations across `config.horizon`.
- Procedure: Record each configured invariant by observation sequence number. `horizon_complete` is true only when the configured number of horizon observations is present.
- Range: Ordered finite list of per-key numeric or null readings.
- Interpretation: Directly exposes stable, immediate, delayed, transient, or end-of-window changes.
- Limitations: No behavior is observed beyond the finite horizon.
- Does NOT establish: Mathematical PPS lim-sup condition, an infinite-time limit, phenomenal identity, consciousness, or qualia.

---

## global_stability_bound.finite_horizon_tail_degradation

- Version: 1.0
- Inputs: Baseline vector, invariant trajectory, `config.invariant_directions`, `config.horizon`, and a predeclared `config.tail_estimator` (`max` or `percentile`). Percentile mode additionally uses `config.tail_percentile`.
- Procedure: Convert each reading into direction-aware degradation in that invariant's own units. For `higher_is_better`, degradation is `baseline - reading`; for `lower_is_better`, degradation is `reading - baseline`. Positive means worse. Apply the configured tail estimator only when the complete horizon and required readings are present. Percentiles use nearest-rank semantics: `rank = ceil(p/100 * N)`. Cross-invariant aggregation is produced only when every invariant has an explicit positive entry in `config.invariant_scales` and a non-negative entry in `config.invariant_weights`, with positive total weight.
- Range: Per-key finite real or null; optional dimensionless normalized aggregate finite real or null.
- Interpretation: Finite-window tail degradation without silently assuming all invariants share direction or units.
- Limitations: Tail behavior beyond the horizon is unobserved. Aggregation is undefined without preregistered normalization scales and weights.
- Does NOT establish: Mathematical PPS lim-sup condition, an infinite-time bound, thermodynamic stability, phenomenal identity, consciousness, or qualia.

---

## global_stability_bound.recovery_profile

- Version: 1.0
- Inputs: Baseline, final horizon reading, invariant direction, and per-key `config.recovery_thresholds` (with legacy scalar `recovery_threshold` supported only for backward compatibility).
- Procedure: Compute direction-aware final degradation per invariant. Classify `recovered` when final degradation is within that invariant's configured threshold, otherwise `degraded`. Missing evidence remains `no_baseline`, `no_direction`, or `no_data`.
- Range: One state per invariant plus final degradation and thresholds used.
- Interpretation: Separates transient damage that recovers by the final observed step from persistent end-of-window degradation.
- Limitations: Recovery is assessed only at the final observed step; oscillation remains visible in the full trajectory.
- Does NOT establish: Mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.

---

## global_stability_bound.intervention_evidence

- Version: 1.0
- Inputs: Persisted `Intervention` objects passed by `run_service` for the current run and `config.perturbation_type`.
- Procedure: Record intervention types and count those matching the configured perturbation type.
- Range: Counts, type list, and `matching_intervention_recorded` boolean.
- Interpretation: Distinguishes a configured perturbation label from evidence that PhiTest actually recorded a corresponding intervention.
- Limitations: A recorded intervention proves only that the adapter reported applying/handling that intervention. It does not establish causal effect on later measurements.
- Does NOT establish: Causality, mathematical PPS lim-sup condition, phenomenal identity, consciousness, or qualia.
