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
