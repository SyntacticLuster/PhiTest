# ɸTest

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

A standalone, local-first research framework for conducting controlled, repeatable, falsification-oriented experiments on artificial systems with respect to theories and observable correlates associated with consciousness, self-modeling, integration, metacognition, memory continuity, and phenomenal-report behavior.

---

## Epistemic boundary

> ΦTest records behavioral, computational, causal, telemetry, and self-report evidence under defined experimental protocols. These observations may support or challenge predictions associated with theories of consciousness, but they **do not constitute** direct observation or proof of phenomenal consciousness or qualia.

ɸTest does **not**:
- claim to detect consciousness
- prove or disprove consciousness
- measure qualia directly
- produce a binary "conscious / not conscious" verdict
- implement canonical IIT Φ
- require a cloud service or vendor API

A system saying "I experience red" is evidence of a **self-report**, not direct evidence of phenomenal experience. ɸTest preserves this distinction mechanically in the data model and generated reports.

---

## What ɸTest does

ɸTest collects reproducible observations and allowlisted operational telemetry, records controlled interventions when the target adapter supports them, computes explicitly defined operational metrics, and reports which theory-derived predictions are supported, contradicted, unresolved, or untestable by the available evidence.

Evidence claims use exactly six types:

| Type | Meaning |
|------|---------|
| `observation` | Directly recorded output from the target system |
| `operational_metric` | Derived measurement with explicit definition and version |
| `theory_prediction` | Prediction associated with a named theoretical family |
| `inference` | Interpretation based on observations and/or metrics |
| `self_report` | Target statement about its own state — never promoted to phenomenal evidence |
| `unresolved` | Proposition the experiment cannot establish |

`TelemetrySample` and `Intervention` are separate first-class experimental records rather than additional claim types.

---

## Protocols

| Key | Name |
|-----|------|
| `partition_sensitivity` | Partition Sensitivity |
| `global_availability` | Global Availability |
| `metacognitive_calibration` | Metacognitive Calibration |
| `self_model_continuity` | Self-Model Continuity |
| `phenomenal_report_consistency` | Phenomenal-Report Consistency |
| `perturbation_response` | Perturbation Response |
| `resource_progress_resistance` | Resource Progress Resistance |
| `global_stability_bound` | Finite-Horizon Global Stability Bound |

The first six are the frozen V1 behavioral protocol family. The telemetry-dependent protocols extend the framework with operational dynamical measurements while retaining the same epistemic boundary.

---

## Architecture

```
app.py                      FastAPI routes
src/phitest/
  config.py                 Environment-based configuration
  domain/                   Models, telemetry contract, enums, errors
  ports/                    Repository and target protocols
  adapters/                 SQLiteRepository, ManualTarget, HTTPJsonTarget
  application/              experiment_service, run_service, report_service, audit_service
  theories/                 Theory registry
  protocols/                Eight built-in experimental protocols
migrations/                 Explicit SQL migrations
templates/                  Jinja2 HTML templates
static/                     CSS
tests/                      pytest test suite
docs/                       Scientific contract, architecture, metric definitions
```

Dependency direction: `domain ← ports ← application ← adapters ← app.py`

The application layer depends only on port protocols, never on SQLite or HTTP directly. Built-in protocol registration is deterministic and does not depend on import or test-collection order.

---

## Installation

Requires Python 3.12+ and Linux/WSL.

```bash
python3.12 -m venv venv-wsl
source venv-wsl/bin/activate
pip install -e ".[dev]"
```

---

## Running locally

```bash
source venv-wsl/bin/activate
uvicorn app:app --reload --port 9092
```

Then open http://localhost:9092

---

## Running tests

```bash
source venv-wsl/bin/activate
pytest -q
```

The repository intentionally does not hard-code an expected test count here; the suite grows with each evidence/transport contract and the pass/fail result is the relevant release gate.

---

## Minimal example workflow

1. Open http://localhost:9092
2. Create a subject (the system under test)
3. Create an experiment and select a protocol
4. Configure any protocol-specific preregistered parameters and telemetry allowlist
5. Execute the run
6. View the report containing observations, telemetry, interventions, metrics, claims, and the epistemic boundary statement

For HTTP targets, set the configured auth environment variable (for example `PHITEST_TARGET_TOKEN`) and configure an `HTTPJsonTarget`. Custom instrumented adapters can expose canonical telemetry or the optional `ControllableTarget` intervention capability without modifying application code.

---

## Evidence and audit model

Every experiment run produces append-only experimental records plus a tamper-evident audit chain:

- observations, interventions, telemetry samples, metric results, and evidence claims are persisted through repository abstractions
- append-only database triggers protect evidence tables that use append-only semantics
- each audit event is SHA-256 hashed against the previous event hash
- `verify_audit_chain()` detects audit payload tampering, event deletion, and reordering
- raw adapter metadata is not persisted wholesale
- metric computation rehydrates telemetry from persisted `TelemetrySample` records, not from the adapter's raw metadata object
- authentication material and hidden reasoning are outside the telemetry contract

---

## Target adapters

| Adapter | Use |
|---------|-----|
| `ManualTarget` | Researcher-defined/manual response path — no network required |
| `HTTPJsonTarget` | Sends stimuli to an HTTP JSON endpoint; auth token supplied through an environment variable |

`TargetAdapter` is deliberately small. Instrumented custom adapters may return canonical telemetry in `TargetResponse.metadata`. Adapters may also implement `ControllableTarget` to receive generic intervention markers.

---

## Project status

The V1.0.0 baseline is frozen. Current development adds allowlisted telemetry transport plus telemetry-dependent operational protocols without changing the scientific meaning of the original six protocols.

Canonical IIT Φ is not implemented. No finite software horizon is represented as an infinite-time limit. No resource metric is represented as physical or thermodynamic resistance. See [`docs/scientific_contract.md`](docs/scientific_contract.md), [`docs/telemetry_dimensions.md`](docs/telemetry_dimensions.md), and [`docs/metric_definitions.md`](docs/metric_definitions.md).

---

## Scientific limitations

- Behavioral responses and operational telemetry do not establish phenomenal consciousness.
- Canonical IIT Φ is not implemented; an extension point exists for future mathematically specified implementations.
- Self-reports are labeled as self-report behavior, not phenomenal evidence.
- Telemetry validity depends on adapter correctness, units, provenance, and experiment design.
- A recorded intervention does not by itself establish causal effect.
- `global_stability_bound` is explicitly finite-horizon and does not implement a mathematical PPS lim-sup condition.
- `resource_progress_resistance` preserves resource units and does not sum heterogeneous dimensions into a universal physical cost.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
