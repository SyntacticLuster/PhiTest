# PhiTest Telemetry Dimensions

Telemetry samples record structured operational measurements from target adapters. All dimensions are optional. No target is required to expose any dimension. Absent dimensions are simply absent from the sample's `values_json`.

No telemetry dimension name implies or measures phenomenal consciousness, qualia, or sentience. All dimensions are operational measurements.

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

Only keys present in both the allowlist and the canonical dimension set below are persisted. Unknown keys are silently dropped. Auth-related keys are never persisted regardless of allowlist.

---

## Canonical dimension keys

### compute

| Key | Type | Description |
|-----|------|-------------|
| `compute.input_tokens` | integer | Tokens in the input/prompt |
| `compute.output_tokens` | integer | Tokens in the generated output |
| `compute.inference_ms` | number | Wall-clock inference time in milliseconds |
| `compute.cpu_ms` | number | CPU time consumed in milliseconds |
| `compute.gpu_ms` | number | GPU time consumed in milliseconds |
| `compute.runtime_ms` | number | Total runtime including overhead |

### memory

| Key | Type | Description |
|-----|------|-------------|
| `memory.reads` | integer | Memory read operations |
| `memory.writes` | integer | Memory write operations |
| `memory.mutations` | integer | In-place memory mutations |
| `memory.nodes_scanned` | integer | Graph/store nodes examined |
| `memory.nodes_returned` | integer | Nodes returned to caller |
| `memory.nodes_added` | integer | Nodes added to store |
| `memory.nodes_pruned` | integer | Nodes removed from store |
| `memory.edges_added` | integer | Edges added |
| `memory.edges_removed` | integer | Edges removed |
| `memory.edges_reweighted` | integer | Edges with updated weights |
| `memory.bytes_before` | integer | Store size in bytes before operation |
| `memory.bytes_after` | integer | Store size in bytes after operation |

### retrieval

| Key | Type | Description |
|-----|------|-------------|
| `retrieval.query_id` | string | Identifier for the query, if supplied |
| `retrieval.target_id` | string | Identifier for the retrieval target, if supplied |
| `retrieval.rank` | integer | Rank of the top result |
| `retrieval.score` | number | Retrieval score of the top result |
| `retrieval.path_cost` | number | Search path cost |
| `retrieval.search_depth` | integer | Search depth reached |

### consolidation

| Key | Type | Description |
|-----|------|-------------|
| `consolidation.cycle_id` | string | Identifier for the consolidation cycle |
| `consolidation.duration_ms` | number | Duration of consolidation in milliseconds |
| `consolidation.nodes_examined` | integer | Nodes examined during consolidation |
| `consolidation.nodes_retained` | integer | Nodes retained after consolidation |
| `consolidation.nodes_pruned` | integer | Nodes pruned during consolidation |
| `consolidation.edges_reweighted` | integer | Edges reweighted during consolidation |
| `consolidation.bytes_reclaimed` | integer | Bytes reclaimed |

### state

| Key | Type | Description |
|-----|------|-------------|
| `state.target_state_id` | string | Opaque identifier for the target's current state snapshot |
| `state.topology_id` | string | Opaque identifier for the target's current topology |
| `state.invariant_hash` | string | Hash of invariant measurements, if supplied |

### progress

| Key | Type | Description |
|-----|------|-------------|
| `progress.value` | number | Externally defined task-progress measurement (0.0–1.0 or raw count) |
| `progress.source_type` | string | Type of the progress source (e.g., `task_completion`, `step_count`) |
| `progress.provenance` | string | Description of how the progress value was derived |

---

## Evidence status

Telemetry samples are operational measurements. They are:

- **not** evidence of phenomenal consciousness
- **not** evidence of qualia
- **not** evidence of sentience
- subject to the same epistemic boundary as all other ɸTest evidence

Telemetry samples may be used as inputs to `operational_metric` computations in future protocol versions.

---

## Security

- Only keys in the canonical set above may be persisted.
- Keys containing `auth`, `secret`, `token`, `key`, or similar credential patterns are not in the canonical set and cannot be persisted.
- The allowlist is declared by the researcher at experiment creation time, not inferred from adapter output.
- Adapters may return richer metadata; only declared canonical dimensions are stored.
