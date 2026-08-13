# PhiTest Architecture

## Dependency direction

```
domain/          Models, telemetry contract, enums, errors
  ↑
ports/           Protocol interfaces (Repository, TargetAdapter, ControllableTarget)
  ↑
application/     Services — depends on domain and ports, never concrete adapters
  ↑
adapters/        Concrete implementations — depends on domain and ports
  ↑
app.py           FastAPI routes — wires adapters into application services
```

## Domain layer (`src/phitest/domain/`)

- `models.py` — Pydantic models for experimental entities
- `enums.py` — status and type enumerations
- `errors.py` — application-specific exceptions
- `telemetry.py` — canonical telemetry allowlist plus value normalization/validation

The domain layer performs no persistence or network I/O.

## Ports layer (`src/phitest/ports/`)

- `repository.py` — `Repository` protocol defining persistence operations
- `target.py` — `TargetAdapter` plus optional `ControllableTarget`

The application layer depends only on these protocols, never on SQLite or HTTP directly.

## Application layer (`src/phitest/application/`)

- `experiment_service.py` — subject and experiment creation
- `run_service.py` — end-to-end experiment execution engine
- `report_service.py` — report generation
- `audit_service.py` — audit event emission and chain verification
- `metric_service.py` — IIT extension point (no fake implementation)

`run_service.execute_run()` owns the evidence transport sequence: stimulus persistence, target invocation, observation persistence, telemetry normalization/persistence, intervention persistence when supported, telemetry rehydration from the repository, metric computation, claims, and terminal run state.

## Adapters layer (`src/phitest/adapters/`)

- `sqlite_repository.py` — SQLite implementation of `Repository`
- `manual_target.py` — researcher/manual response target
- `http_json_target.py` — generic HTTP JSON target (secrets via environment variables only)

## Protocols (`src/phitest/protocols/`)

Each protocol declares key, version, name, description, theory relevance, required capabilities, deterministic stimulus generation, metric definitions, and limitations.

Built-in registration is centralized in `protocols/registry.py`. `get_protocol()` and `list_protocols()` explicitly ensure all built-ins are loaded, so protocol availability does not depend on `app.py` import order or pytest collection side effects.

Current built-ins:

- `partition_sensitivity`
- `global_availability`
- `metacognitive_calibration`
- `self_model_continuity`
- `phenomenal_report_consistency`
- `perturbation_response`
- `resource_progress_resistance`
- `global_stability_bound`

## Theories (`src/phitest/theories/`)

Theory families map operational observations to explicit predictions. They are labeled as operational families inspired by academic theories, not authoritative implementations.

## Target adapter boundary

The experiment engine calls only `adapter.send(stimulus, context)` and receives a `TargetResponse`. Authentication secrets are supplied through environment variables and must not be copied into target metadata.

Adapters may optionally implement `ControllableTarget` to receive controlled intervention markers. The engine checks `isinstance(adapter, ControllableTarget)` at each `intervention_marker`. A configured perturbation label is not itself evidence that an intervention occurred; protocols can inspect the persisted `Intervention` objects passed to metric computation.

## Telemetry transport

`TargetResponse.metadata` is a transport envelope, **not** an evidence store. The production path is:

1. parse the experiment's `telemetry_allowlist`;
2. intersect it with `ALLOWED_TELEMETRY_KEYS`;
3. validate/normalize values for requested canonical fields;
4. persist the filtered values as an append-only `TelemetrySample` associated with the run/observation/sequence/phase;
5. audit-record the telemetry sample without recording raw values in the audit payload;
6. after stimulus execution, read the run's persisted `TelemetrySample` records back through the `Repository` abstraction;
7. reconstruct the internal observation-id → telemetry mapping;
8. pass that internal mapping to protocol metric computation.

This last step is deliberate: telemetry-dependent metrics are computed from evidence that crossed the same persistence boundary used for reports and later reproducibility, not from an in-memory copy of arbitrary adapter metadata.

Unknown metadata is dropped. A malformed value on a requested canonical field fails visibly rather than being silently converted into evidence.

### Structured invariant measurements

`state.invariant_measurements` is an allowlisted object whose values must be finite numbers and whose names are constrained identifiers. It provides a target-agnostic channel for preregistered measurements such as retention, constraint adherence, error rate, or other externally defined invariants without opening arbitrary nested metadata persistence.

The field does not assign scientific meaning to those names. Protocol configuration must still define direction, units/scales, thresholds, provenance, and interpretation.

See `docs/telemetry_dimensions.md` for the canonical dimension reference.

## Resource/progress metric boundary

`resource_progress_resistance` retains a vector of resource dimensions. It may expose a scalar cost-per-progress only for one explicitly selected resource dimension (default `compute.inference_ms`). It does not sum tokens, milliseconds, graph operations, bytes, or other heterogeneous units into a universal scalar.

## Finite-horizon stability boundary

`global_stability_bound` uses matched pre/post local task progress plus a predeclared finite invariant horizon. Degradation direction is configured per invariant. Tail estimates are per invariant and remain in that invariant's own units. Cross-invariant aggregation is unavailable unless explicit scales and weights are preregistered.

The finite-horizon tail metric is not a mathematical lim sup or infinite-time stability bound.

## Persistence

SQLite with explicit SQL migrations. Foreign keys are enabled on every connection. Evidence tables intended to be append-only are protected by database triggers. No ORM.

## Audit chain

SHA-256 hash chain: `hash(previous_event_hash + canonical_payload_json)`. Verified independently by `verify_audit_chain()`. Tampering with any event breaks subsequent hashes.
