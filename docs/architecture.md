# PhiTest Architecture

## Dependency direction

```
domain/          Pure models, enums, errors — no dependencies
  ↑
ports/           Protocol interfaces (Repository, TargetAdapter) — depends on domain only
  ↑
application/     Services — depends on domain and ports, never on concrete adapters
  ↑
adapters/        Concrete implementations — depends on domain and ports
  ↑
app.py           FastAPI routes — wires adapters into application services
```

## Domain layer (`src/phitest/domain/`)

- `models.py` — Pydantic models for all entities
- `enums.py` — Status and type enumerations
- `errors.py` — Application-specific exceptions

No I/O. No framework imports.

## Ports layer (`src/phitest/ports/`)

- `repository.py` — `Repository` Protocol defining all persistence operations
- `target.py` — `TargetAdapter` Protocol defining the target system interface

The application layer depends only on these protocols, never on SQLite or HTTP directly.

## Application layer (`src/phitest/application/`)

- `experiment_service.py` — Subject and experiment creation
- `run_service.py` — End-to-end experiment execution engine
- `report_service.py` — Report generation
- `audit_service.py` — Audit event emission and chain verification
- `metric_service.py` — IIT extension point (no fake implementation)

## Adapters layer (`src/phitest/adapters/`)

- `sqlite_repository.py` — SQLite implementation of Repository
- `manual_target.py` — Researcher-entered responses
- `http_json_target.py` — Generic HTTP JSON target (secrets via env vars only)

## Protocols (`src/phitest/protocols/`)

Each protocol declares key, version, name, description, theory relevance, required capabilities, stimulus generation, metric definitions, and limitations. Stimulus generation is deterministic given a seed.

## Theories (`src/phitest/theories/`)

Theory families map operational observations to explicit predictions. They are explicitly labeled as operational families inspired by academic theories, not authoritative implementations.

## Target adapter boundary

The experiment engine calls only `adapter.send(stimulus, context)` and receives a `TargetResponse`. It never imports vendor SDKs. Authentication secrets are supplied only through environment variables and never appear in logs, audit events, or the database.

## Persistence

SQLite with explicit SQL migrations. Foreign keys enforced on every connection. Append-only tables enforced by database triggers. No ORM.

## Audit chain

SHA-256 hash chain: `hash(previous_event_hash + canonical_payload_json)`. Verified independently by `verify_audit_chain()`. Tampering with any event breaks all subsequent hashes.
