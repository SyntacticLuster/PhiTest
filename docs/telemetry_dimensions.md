# PhiTest Telemetry Dimensions

Telemetry samples record structured operational measurements from target adapters. All dimensions are optional. No target is required to expose any dimension. Absent dimensions are absent from the sample's `values_json`; absence does not mean zero.

No telemetry dimension name implies or measures phenomenal consciousness, qualia, sentience, or far-from-equilibrium dynamics. All dimensions are operational measurements.

---

## Enabling telemetry

Telemetry is disabled by default. To enable it, add a `telemetry_allowlist` to the experiment's `configuration_json`:

```json
{
  "telemetry_allowlist": [
    "compute.input_tokens",
    "compute.output_tokens",
    "memory.reads"
  ]
}
```

Only keys present in both the researcher-declared allowlist and the canonical dimension set below are persisted. Unknown metadata is dropped. Values on requested canonical keys are type-validated before persistence; malformed allowlisted telemetry fails the run visibly rather than being silently coerced into evidence.

Metric computation consumes telemetry only after it has been normalized and persisted as `TelemetrySample` evidence. The runtime reconstructs its internal observation-to-telemetry map from those persisted samples; raw adapter metadata is not a metric input.

---

## Canonical dimension keys

### compute

| Key | Type | Description |
|-----|------|-------------|
| `compute.input_tokens` | number | Tokens in the input/prompt |
| `compute.output_tokens` | number | Tokens in the generated output |
| `compute.inference_ms` | number | Wall-clock inference time in milliseconds |
| `compute.cpu_ms` | number | CPU time consumed in milliseconds |
| `compute.gpu_ms` | number | GPU time consumed in milliseconds |
| `compute.runtime_ms` | number | Total runtime including overhead |

### memory

| Key | Type | Description |
|-----|------|-------------|
| `memory.reads` | number | Memory read operations |
| `memory.writes` | number | Memory write operations |
| `memory.mutations` | number | In-place memory mutations |
| `memory.nodes_scanned` | number | Graph/store nodes examined |
| `memory.nodes_returned` | number | Nodes returned to caller |
| `memory.nodes_added` | number | Nodes added to store |
| `memory.nodes_pruned` | number | Nodes removed from store |
| `memory.edges_added` | number | Edges added |
| `memory.edges_removed` | number | Edges removed |
| `memory.edges_reweighted` | number | Edges with updated weights |
| `memory.bytes_before` | number | Store size in bytes before operation |
| `memory.bytes_after` | number | Store size in bytes after operation |

### retrieval

| Key | Type | Description |
|-----|------|-------------|
| `retrieval.query_id` | string | Identifier for the query, if supplied |
| `retrieval.target_id` | string | Identifier for the retrieval target, if supplied |
| `retrieval.rank` | number | Rank of the result of interest |
| `retrieval.score` | number | Retrieval/relevance score |
| `retrieval.path_cost` | number | Search path cost |
| `retrieval.search_depth` | number | Search depth reached |

### consolidation

| Key | Type | Description |
|-----|------|-------------|
| `consolidation.cycle_id` | string | Identifier for the consolidation cycle |
| `consolidation.duration_ms` | number | Duration of consolidation in milliseconds |
| `consolidation.nodes_examined` | number | Nodes examined during consolidation |
| `consolidation.nodes_retained` | number | Nodes retained after consolidation |
| `consolidation.nodes_pruned` | number | Nodes pruned during consolidation |
| `consolidation.edges_reweighted` | number | Edges reweighted during consolidation |
| `consolidation.bytes_reclaimed` | number | Bytes reclaimed |

### state

| Key | Type | Description |
|-----|------|-------------|
| `state.target_state_id` | string | Opaque identifier for the target's current state snapshot |
| `state.topology_id` | string | Opaque identifier for the target's current topology |
| `state.invariant_hash` | string | Opaque hash of an invariant-measurement set, if supplied |
| `state.invariant_measurements` | object | Researcher/adapter-supplied named numeric invariant measurements |

`state.invariant_measurements` is the structured channel for target-agnostic numeric invariant evidence. Example:

```json
{
  "state.invariant_measurements": {
    "sentinel_retention": 0.99,
    "constraint_adherence": 1.0,
    "error_rate": 0.04
  }
}
```

Invariant names must match `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` and values must be finite numbers. The field is still only operational telemetry. Names do not acquire scientific meaning merely by being placed in this object; their units, direction, provenance, and experimental interpretation must be preregistered by the experiment.

### progress

| Key | Type | Description |
|-----|------|-------------|
| `progress.value` | number | Externally defined task-progress measurement |
| `progress.source_type` | string | Type/identifier of the progress source |
| `progress.provenance` | string | Description or identifier for how the progress value was derived |

`progress.value` must not be treated as independent evidence merely because a target asserted that it made progress. Protocols that depend on progress remain responsible for defining an externally meaningful measurement and provenance.

---

## Evidence lifecycle

For a normal instrumented response:

1. the adapter returns `TargetResponse.metadata`;
2. the experiment's `telemetry_allowlist` is intersected with the canonical key set;
3. requested canonical values are type-validated and normalized;
4. the resulting `TelemetrySample` is persisted and audit-recorded;
5. before metrics are computed, PhiTest reconstructs the internal telemetry map from persisted samples;
6. telemetry-aware protocols consume that reconstructed evidence, not the adapter's raw metadata object.

This keeps metric computation reproducible from stored PhiTest evidence and prevents test-only metadata injection from masquerading as the production execution path.

---

## Evidence status

Telemetry samples are operational measurements. They are:

- **not** evidence of phenomenal consciousness
- **not** evidence of qualia
- **not** evidence of sentience
- **not** direct measurements of thermodynamic or far-from-equilibrium state
- subject to the same epistemic boundary as all other PhiTest evidence

---

## Security and privacy boundary

- Only canonical keys explicitly requested in `telemetry_allowlist` may be persisted.
- Unknown/raw metadata is not copied into evidence.
- `state.invariant_measurements` accepts numeric values only; it is not a back door for arbitrary nested target state.
- Invariant names are constrained identifiers rather than free-form text.
- Auth headers, credentials, hidden reasoning, prompts, environment values, and arbitrary private target internals are outside the telemetry contract.
- Researchers and adapter authors remain responsible for not placing sensitive information inside explicitly allowed string-valued identifier/provenance fields.
