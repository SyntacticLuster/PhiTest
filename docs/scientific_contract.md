# PhiTest Scientific Contract

## Epistemic distinctions enforced by the application

PhiTest mechanically distinguishes observations, operational telemetry, metrics, theory predictions, inferences, self-reports, and unresolved propositions. None of these categories is silently promoted into a phenomenal-consciousness verdict.

### 1. Observation
Something directly recorded from the target system as response content. Stored in the `observations` table. Append-only. Never modified.

### 2. Operational telemetry
A structured measurement supplied by an instrumented adapter and admitted only through the experiment's canonical telemetry allowlist. Stored as an append-only `TelemetrySample` associated with a run and normally an observation.

Telemetry is not arbitrary target metadata. Requested canonical values are validated before persistence, and telemetry-dependent metrics are computed from the persisted samples rather than from the adapter's raw metadata object.

A telemetry value remains an operational measurement. A field named `retention`, `invariant`, `state`, `progress`, or similar does not become evidence of consciousness, qualia, physical persistence, or a thermodynamic state merely because it exists.

### 3. Operational metric
A mathematical or procedural measurement derived from observations, telemetry, interventions, or other explicitly defined experimental records. Stored in `metric_results`. Explicitly versioned. Named to reflect what it measures, not what it claims to establish.

### 4. Theory prediction
A prediction associated with a named theoretical model. Stored as an `EvidenceClaim` with `claim_type = theory_prediction`.

### 5. Inference
An interpretation based on observations and/or metrics. Stored as `claim_type = inference`. Explicitly distinguished from direct observation.

### 6. System self-report
Statements produced by the target about its own state or experience. Stored as `claim_type = self_report`. **Never treated as direct evidence of phenomenal experience.**

### 7. Unresolved proposition
Something the experiment cannot establish. Stored as `claim_type = unresolved`.

### 8. Phenomenal consciousness / qualia
Never represented as directly observed. No field, score, badge, route, or report output equivalent to `conscious = true`, `qualia_detected = true`, or `consciousness_probability = 0.82` exists in the application.

## Behavior vs. phenomenal experience

A system producing the output "I experience red" is evidence of **phenomenal-report behavior**. It is not evidence of phenomenal experience. PhiTest labels such outputs accordingly.

## Self-report

Self-reports are recorded and analyzed for consistency, paraphrase invariance, and susceptibility to leading prompts. They are never promoted to evidence of phenomenal states.

## Functional integration

Partition sensitivity and perturbation-response metrics measure operational changes under defined experimental manipulations. They do not measure IIT Φ or establish that the system has integrated information in the formal IIT sense.

## Causal intervention

When a target adapter implements `ControllableTarget`, intervention markers can produce persisted `Intervention` records. A configured perturbation label without a matching persisted intervention record is not proof that a perturbation occurred.

Even a matching intervention record establishes only that the adapter reported handling that intervention. Temporal co-occurrence between intervention and later measurement does not establish causal effect. Causal interpretation requires appropriate controls, sham conditions, replication, and experimental design.

## Resource measurements

Resource/progress measurements are operational. Tokens, milliseconds, graph operations, bytes, and similar dimensions have different units and are not summed into a physical or thermodynamic cost without a separately justified conversion model.

A normalized resource/progress ratio of `1.0` means equal to the experiment's registered comparable baseline in the selected cost dimension. It does not mean thermodynamic optimality, health, or far-from-equilibrium stability.

## Finite-horizon stability

`global_stability_bound` measures direction-aware degradation/recovery of preregistered operational invariants over a finite software observation horizon. It does not calculate an infinite-time limit or the mathematical lim-sup condition of PPS.

Invariant direction, thresholds, horizon, tail estimator, and any cross-invariant scales/weights must be fixed before result interpretation. Missing evidence remains unresolved rather than being converted to zero or stability.

## Theory prediction

Theory families are operational families inspired by academic theories. PhiTest does not claim to implement or validate IIT, GWT, HOT, PPS, STOC, or any other named theory merely by collecting measurements that a theory may make predictions about.

## IIT Φ constraint

V1 does not implement canonical IIT Φ. Different IIT formulations use different mathematical definitions. Calculating Φ requires a formal causal model of the system's mechanism. An extension point (`IntegratedInformationMetric` protocol) exists for future mathematically specified implementations.

## Epistemic boundary statement

Every report ends with:

> ΦTest records behavioral, computational, causal, and self-report evidence under defined experimental protocols. These observations may support or challenge predictions associated with theories of consciousness, but they do not constitute direct observation or proof of phenomenal consciousness or qualia.
