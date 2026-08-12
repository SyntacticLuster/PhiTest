# PhiTest Scientific Contract

## Epistemic distinctions enforced by the application

PhiTest mechanically distinguishes the following categories. These are not merely mentioned in documentation — they are enforced in the data model and report generation.

### 1. Observation
Something directly recorded from the target system or experimental apparatus. Stored in the `observations` table. Append-only. Never modified.

### 2. Operational metric
A mathematical or procedural measurement derived from observations. Stored in `metric_results`. Explicitly versioned. Named to reflect what they measure, not what they claim to establish.

### 3. Theory prediction
A prediction associated with a named theoretical model. Stored as an `EvidenceClaim` with `claim_type = theory_prediction`.

### 4. Inference
An interpretation based on observations and/or metrics. Stored as `claim_type = inference`. Explicitly distinguished from direct observation.

### 5. System self-report
Statements produced by the target about its own state or experience. Stored as `claim_type = self_report`. **Never treated as direct evidence of phenomenal experience.**

### 6. Unresolved proposition
Something the experiment cannot establish. Stored as `claim_type = unresolved`.

### 7. Phenomenal consciousness / qualia
Never represented as directly observed. No field, score, badge, route, or report output equivalent to `conscious = true`, `qualia_detected = true`, or `consciousness_probability = 0.82` exists anywhere in the application.

## Behavior vs. phenomenal experience

A system producing the output "I experience red" is evidence of **phenomenal-report behavior**. It is not evidence of phenomenal experience. PhiTest labels such outputs accordingly.

## Self-report
Self-reports are recorded and analyzed for consistency, paraphrase invariance, and susceptibility to leading prompts. They are never promoted to evidence of phenomenal states.

## Functional integration
Partition sensitivity and perturbation response metrics measure behavioral changes under information partitioning. These are operational proxies. They do not measure IIT Φ or establish that the system has integrated information in the formal IIT sense.

## Causal intervention
Interventions are recorded. The report explicitly distinguishes correlation (behavioral change co-occurring with intervention) from causal interpretation (the intervention caused the change). V1 does not establish causal relationships.

## Theory prediction
Theory families are operational families inspired by academic theories. PhiTest does not claim to implement or validate IIT, GWT, HOT, or any other named theory. The software makes this distinction visible.

## IIT Φ constraint
V1 does not implement canonical IIT Φ. Different IIT formulations (2.0, 3.0, 4.0) use different mathematical definitions. Calculating Φ requires a formal causal model of the system's mechanism, unavailable for opaque language systems. An extension point (`IntegratedInformationMetric` protocol) exists for future implementations.

## Epistemic boundary statement
Every report ends with:

> ΦTest records behavioral, computational, causal, and self-report evidence under defined experimental protocols. These observations may support or challenge predictions associated with theories of consciousness, but they do not constitute direct observation or proof of phenomenal consciousness or qualia.
