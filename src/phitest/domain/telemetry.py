"""Canonical, allowlisted telemetry contract for PhiTest.

Telemetry is operational evidence only. Adapter metadata is never persisted wholesale:
only researcher-allowlisted canonical keys survive normalization. Malformed values on
an allowlisted key fail visibly instead of being silently converted into evidence.
"""
from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from typing import Any


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
    "state.invariant_measurements",
    # Progress
    "progress.value",
    "progress.source_type",
    "progress.provenance",
})

_NUMERIC_KEYS: frozenset[str] = frozenset({
    "compute.input_tokens",
    "compute.output_tokens",
    "compute.inference_ms",
    "compute.cpu_ms",
    "compute.gpu_ms",
    "compute.runtime_ms",
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
    "retrieval.rank",
    "retrieval.score",
    "retrieval.path_cost",
    "retrieval.search_depth",
    "consolidation.duration_ms",
    "consolidation.nodes_examined",
    "consolidation.nodes_retained",
    "consolidation.nodes_pruned",
    "consolidation.edges_reweighted",
    "consolidation.bytes_reclaimed",
    "progress.value",
})

_STRING_KEYS: frozenset[str] = frozenset({
    "retrieval.query_id",
    "retrieval.target_id",
    "consolidation.cycle_id",
    "state.target_state_id",
    "state.topology_id",
    "state.invariant_hash",
    "progress.source_type",
    "progress.provenance",
})

_INVARIANT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _normalize_invariant_measurements(value: Any) -> dict[str, int | float]:
    if not isinstance(value, Mapping):
        raise ValueError("state.invariant_measurements must be an object mapping names to numbers")

    normalized: dict[str, int | float] = {}
    for raw_name, measurement in value.items():
        if not isinstance(raw_name, str) or _INVARIANT_NAME.fullmatch(raw_name) is None:
            raise ValueError(
                "state.invariant_measurements keys must match "
                "[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
            )
        if not _is_finite_number(measurement):
            raise ValueError(
                f"state.invariant_measurements[{raw_name!r}] must be a finite number"
            )
        normalized[raw_name] = measurement
    return dict(sorted(normalized.items()))


def normalize_telemetry(
    metadata: Mapping[str, Any],
    requested_keys: Iterable[str],
) -> dict[str, Any]:
    """Return the canonical, validated subset of adapter metadata.

    Unknown metadata is ignored. A malformed value for a requested canonical key is
    an error because silently accepting or coercing malformed evidence would make
    downstream metrics non-reproducible.
    """
    if not isinstance(metadata, Mapping):
        raise ValueError("TargetResponse.metadata must be a mapping")

    requested = frozenset(requested_keys) & ALLOWED_TELEMETRY_KEYS
    normalized: dict[str, Any] = {}

    for key in sorted(requested):
        if key not in metadata:
            continue
        value = metadata[key]

        if key in _NUMERIC_KEYS:
            if not _is_finite_number(value):
                raise ValueError(f"Telemetry field {key!r} must be a finite number")
            normalized[key] = value
            continue

        if key in _STRING_KEYS:
            if not isinstance(value, str):
                raise ValueError(f"Telemetry field {key!r} must be a string")
            normalized[key] = value
            continue

        if key == "state.invariant_measurements":
            normalized[key] = _normalize_invariant_measurements(value)
            continue

        raise ValueError(f"Telemetry field {key!r} has no normalization rule")

    return normalized
