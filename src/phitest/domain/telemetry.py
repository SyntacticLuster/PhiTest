"""
Canonical telemetry dimension allowlist for PhiTest.

Only keys present in ALLOWED_TELEMETRY_KEYS may be persisted as TelemetrySample values.
All other keys in TargetResponse.metadata are silently dropped before persistence.

Keys are grouped by operational category. All dimensions are optional.
No dimension name implies or measures phenomenal consciousness, qualia, or sentience.
"""

ALLOWED_TELEMETRY_KEYS: frozenset[str] = frozenset({
    # Compute
    "compute.input_tokens",
    "compute.output_tokens",
    "compute.inference_ms",
    "compute.cpu_ms",
    "compute.gpu_ms",
    "compute.runtime_ms",
    # Memory
    "memory.reads",
    "memory.writes",
    "memory.mutations",
    "memory.nodes_scanned",
    "memory.nodes_returned",
    "memory.nodes_added",
    "memory.nodes_pruned",
    "memory.edges_added",
    "memory.edges_removed",
    "memory.edges_reweighted",
    "memory.bytes_before",
    "memory.bytes_after",
    # Retrieval
    "retrieval.query_id",
    "retrieval.target_id",
    "retrieval.rank",
    "retrieval.score",
    "retrieval.path_cost",
    "retrieval.search_depth",
    # Consolidation
    "consolidation.cycle_id",
    "consolidation.duration_ms",
    "consolidation.nodes_examined",
    "consolidation.nodes_retained",
    "consolidation.nodes_pruned",
    "consolidation.edges_reweighted",
    "consolidation.bytes_reclaimed",
    # Structural state
    "state.target_state_id",
    "state.topology_id",
    "state.invariant_hash",
    # Progress
    "progress.value",
    "progress.source_type",
    "progress.provenance",
})
