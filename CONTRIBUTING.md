# Contributing to ɸTest

## Development environment

Requires Python 3.12+ and Linux/WSL.

```bash
git clone <repository-url>
cd PhiTest
python3.12 -m venv venv-wsl
source venv-wsl/bin/activate
pip install -e ".[dev]"
```

Canonical Python version: **3.12**.

## Running the test suite

```bash
source venv-wsl/bin/activate
pytest -q
```

Expected: 47 passed, 0 failed. All contributions must maintain this baseline.

## Running the server

```bash
source venv-wsl/bin/activate
uvicorn app:app --reload --port 9092
```

## Branch and PR workflow

- Work on a feature branch
- Open a pull request against `master`
- Describe the behavioral change and its scientific motivation
- Include or update tests for any changed behavior

## Test requirements

- Every behavioral change must be accompanied by a focused test
- Tests must assert the actual application behavior, not an assumed exception type or substring
- Tests must not encode conclusions the framework cannot establish (e.g., asserting that a metric "detects consciousness")
- Do not broaden exception assertions to `Exception` to make tests pass

## Epistemic boundary — non-negotiable

ɸTest mechanically enforces that evidence is classified into exactly six types:

```
observation
operational_metric
theory_prediction
inference
self_report
unresolved
```

Contributions must not:

- Add fields, routes, scores, or report outputs equivalent to:
  - `conscious = true`
  - `consciousness_probability`
  - `sentience_score`
  - `qualia_detected`
  - any binary consciousness verdict
- Promote self-reports to evidence of phenomenal experience
- Claim that passing a protocol demonstrates subjective experience
- Weaken the epistemic boundary statement in reports

If a contribution introduces a new claim type, it must be justified against this taxonomy and reviewed against `docs/scientific_contract.md`.

## Protocol contributions

New protocols must:

- Define a unique `key` and `version`
- Declare `generate_stimuli()` deterministically given a seed
- Define `MetricDefinition` entries with explicit `does_not_establish` fields
- Generate `EvidenceClaim` entries using only the six permitted claim types
- Include a `limitations` statement
- Be accompanied by tests covering stimulus generation, metric computation, and claim generation

## Metric contributions

New metrics must:

- Have a unique `key` and explicit `version`
- Document inputs, procedure, range, and interpretation
- Include a `does_not_establish` field that names what the metric cannot prove
- Not claim to measure phenomenal consciousness, qualia, or subjective experience

## Adapter contributions

New target adapters must:

- Implement the `TargetAdapter` protocol in `src/phitest/ports/target.py`
- Never store authentication secrets in the database, audit log, or observation content
- Enforce `MAX_OBSERVATION_LENGTH`
- Raise `AdapterError` on recoverable failures and `OversizedResponseError` on length violations
- Be accompanied by tests using a mock or local endpoint

## Theory family contributions

New theory families must:

- Be explicitly labeled as operational families *inspired by* academic theories, not authoritative implementations
- Not claim to implement or validate IIT, GWT, HOT, or any other named theory
- Document which named theory they are inspired by and what the operational approximation omits

## Scientific claims in documentation

- Distinguish implementation from named academic theory
- Do not claim peer review, external validation, or replication that has not occurred
- Do not claim the framework detects, measures, or proves consciousness or qualia

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).
