# ɸTest

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

A standalone, local-first research framework for conducting controlled, repeatable, falsification-oriented experiments on artificial systems with respect to theories and observable correlates associated with consciousness, self-modeling, integration, metacognition, memory continuity, and phenomenal-report behavior.

---

## Epistemic boundary

> ΦTest records behavioral, computational, causal, and self-report evidence under defined experimental protocols. These observations may support or challenge predictions associated with theories of consciousness, but they **do not constitute** direct observation or proof of phenomenal consciousness or qualia.

ɸTest does **not**:
- claim to detect consciousness
- prove or disprove consciousness
- measure qualia directly
- produce a binary "conscious / not conscious" verdict
- implement canonical IIT Φ
- connect to any cloud service or external API

A system saying "I experience red" is evidence of a **self-report**, not direct evidence of phenomenal experience. ɸTest preserves this distinction mechanically in the data model and every generated report.

---

## What ɸTest does

ɸTest collects reproducible observations, performs controlled perturbations, computes explicitly defined operational metrics, and reports which theory-derived predictions are supported, contradicted, unresolved, or untestable by the available evidence.

Evidence is classified into exactly six types — enforced in the schema, not just documented:

| Type | Meaning |
|------|---------|
| `observation` | Directly recorded output from the target system |
| `operational_metric` | Derived measurement with explicit definition and version |
| `theory_prediction` | Prediction associated with a named theoretical family |
| `inference` | Interpretation based on observations and/or metrics |
| `self_report` | Target statement about its own state — never promoted to phenomenal evidence |
| `unresolved` | Proposition the experiment cannot establish |

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

---

## Architecture

```
app.py                      FastAPI routes
src/phitest/
  config.py                 Environment-based configuration
  domain/                   Pure domain models, enums, errors
  ports/                    Repository and TargetAdapter protocols
  adapters/                 SQLiteRepository, ManualTarget, HTTPJsonTarget
  application/              experiment_service, run_service, report_service, audit_service
  theories/                 Theory registry (integration, global_availability, metacognition, self_model)
  protocols/                Six experimental protocols
migrations/                 Explicit SQL migrations
templates/                  Jinja2 HTML templates
static/                     CSS
tests/                      pytest test suite
docs/                       Scientific contract, architecture, metric definitions
```

Dependency direction: `domain ← ports ← application ← adapters ← app.py`

The application layer depends only on port protocols, never on SQLite or HTTP directly.

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

Expected: 47 passed, 0 failed.

---

## Minimal example workflow

1. Open http://localhost:9092
2. Create a subject (the AI system under test)
3. Create an experiment — choose a protocol and optionally associate theory families
4. Execute the run — ɸTest sends stimuli to the target adapter and records all responses
5. View the report — observations, metrics, evidence claims, and the epistemic boundary statement

For automated targets, set `PHITEST_TARGET_TOKEN` in your environment and configure an `HTTPJsonTarget` adapter pointing to your local endpoint. See `.env.example`.

---

## Evidence and audit model

Every experiment run produces an append-only, tamper-evident audit chain:

- All observations, interventions, metric results, and evidence claims are stored in append-only tables enforced by database triggers
- Each audit event is SHA-256 hashed against the previous event hash
- `verify_audit_chain()` detects payload tampering, event deletion, and reordering
- Authentication secrets are never stored in the database or audit log

---

## Target adapters

| Adapter | Use |
|---------|-----|
| `ManualTarget` | Researcher enters responses manually — no network required |
| `HTTPJsonTarget` | Sends stimuli to a local HTTP endpoint; auth token via `PHITEST_TARGET_TOKEN` env var |

The adapter interface is a simple protocol — custom adapters can be added without modifying application code.

---

## Project status

V1 — initial implementation. All six protocols operational. 47/47 tests passing.

V1 metrics are behavioral proxies. Automated scoring of response correctness is not implemented. Canonical IIT Φ is not implemented. See [`docs/scientific_contract.md`](docs/scientific_contract.md) and [`docs/metric_definitions.md`](docs/metric_definitions.md).

---

## Scientific limitations

- V1 metrics are count-based behavioral proxies. They do not establish phenomenal consciousness.
- Canonical IIT Φ is not implemented. An extension point exists for future mathematically specified implementations.
- Self-reports are labeled as self-report behavior, not phenomenal evidence.
- Automated scoring of response correctness requires researcher judgment in V1.
- V1 does not establish causal relationships — only behavioral correlations with interventions.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
