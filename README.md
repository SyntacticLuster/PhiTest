# PhiTest

A standalone, local-first research framework for conducting controlled, repeatable, falsification-oriented experiments on artificial systems with respect to theories and observable correlates associated with consciousness, self-modeling, integration, metacognition, memory continuity, and phenomenal-report behavior.

## What PhiTest is

PhiTest collects reproducible observations, performs controlled perturbations, computes explicitly defined operational metrics, and reports which theory-derived predictions are supported, contradicted, unresolved, or untestable by the available evidence.

## What PhiTest is not

PhiTest does **not**:
- claim to detect consciousness
- prove or disprove consciousness
- measure qualia directly
- produce a binary "conscious / not conscious" verdict
- implement canonical IIT Φ
- connect to any cloud service or external API

A system saying "I experience red" is evidence of a **self-report**, not direct evidence of phenomenal experience. PhiTest preserves this distinction mechanically.

## Installation

```bash
python -m venv venv-wsl
source venv-wsl/bin/activate          # Linux/WSL
# or: venv-wsl\Scripts\activate       # Windows
pip install -e ".[dev]"
```

## Canonical run command

```bash
source venv-wsl/bin/activate
uvicorn app:app --reload --port 9092
```

Then open http://localhost:9092

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

Dependency direction: domain ← application ← adapters. The application layer knows only ports (protocols/interfaces), never concrete adapters.

## Protocols

| Key | Name |
|-----|------|
| `partition_sensitivity` | Partition Sensitivity |
| `global_availability` | Global Availability |
| `metacognitive_calibration` | Metacognitive Calibration |
| `self_model_continuity` | Self-Model Continuity |
| `phenomenal_report_consistency` | Phenomenal-Report Consistency |
| `perturbation_response` | Perturbation Response |

## Scientific limitations

- V1 metrics are behavioral proxies. They do not establish phenomenal consciousness.
- Canonical IIT Φ is not implemented. See `docs/scientific_contract.md`.
- Self-reports are labeled as self-report behavior, not phenomenal evidence.
- Automated scoring of response correctness is not implemented in V1.

## Test command

```bash
pytest -q
```
