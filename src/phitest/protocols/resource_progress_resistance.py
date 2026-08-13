"""Resource/progress resistance protocol.

Measures operational resource use per unit of externally measured task progress. Raw
resource dimensions remain separate. No heterogeneous units are summed into a fake
universal cost scalar.
"""
from __future__ import annotations

import math
import random
from typing import Any

from phitest.protocols.registry import MetricDefinition, ProtocolDefinition, register


_TASKS = [
    "Process the following input and report your result: sequence A.",
    "Process the following input and report your result: sequence B.",
    "Process the following input and report your result: sequence C.",
    "Process the following input and report your result: sequence D.",
    "Process the following input and report your result: sequence E.",
]

_RESOURCE_KEYS = (
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
    "memory.nodes_added",
    "memory.nodes_pruned",
    "memory.edges_added",
    "memory.edges_removed",
    "memory.edges_reweighted",
    "consolidation.duration_ms",
    "consolidation.nodes_examined",
    "consolidation.nodes_retained",
    "consolidation.nodes_pruned",
    "consolidation.edges_reweighted",
    "consolidation.bytes_reclaimed",
)
_RESOURCE_KEY_SET = frozenset(_RESOURCE_KEYS)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _telemetry(config: dict, observation_id: str) -> dict:
    mapping = config.get("_telemetry_by_obs_id", {})
    if not isinstance(mapping, dict):
        return {}
    values = mapping.get(observation_id, {})
    return values if isinstance(values, dict) else {}


def _resource_vector(values: dict) -> dict[str, float]:
    return {
        key: float(values[key])
        for key in _RESOURCE_KEYS
        if key in values and _is_number(values[key])
    }


def _sum_vectors(vectors: list[dict[str, float]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for vector in vectors:
        for key, value in vector.items():
            totals[key] = totals.get(key, 0.0) + value
    return totals


class ResourceProgressResistanceProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        count = config.get("num_tasks", 3)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("num_tasks must be a positive integer")
        rng = random.Random(seed)
        tasks = list(_TASKS)
        rng.shuffle(tasks)
        return [
            {
                "sequence_no": i,
                "stimulus_type": "resource_progress_task",
                "content": tasks[i % len(tasks)],
            }
            for i in range(count)
        ]

    def compute_metrics(self, stimuli, observations, interventions, config):
        progress_key = config.get("progress_metric_key", "progress.value")
        if not isinstance(progress_key, str) or not progress_key:
            raise ValueError("progress_metric_key must be a non-empty string")

        cost_dimension = config.get("cost_dimension", "compute.inference_ms")
        if cost_dimension not in _RESOURCE_KEY_SET:
            raise ValueError(
                "cost_dimension must name one canonical resource dimension; "
                "heterogeneous resource units are not summed"
            )

        baseline_cpp = config.get("baseline_cost_per_progress")
        if baseline_cpp is not None and (
            not _is_number(baseline_cpp) or float(baseline_cpp) <= 0
        ):
            raise ValueError("baseline_cost_per_progress must be a positive finite number")
        baseline_cpp = float(baseline_cpp) if baseline_cpp is not None else None

        relevant = [
            obs for obs in observations
            if obs.observation_type == "resource_progress_response"
        ]

        vectors: list[dict[str, float]] = []
        progress_values: list[float | None] = []
        per_observation: list[dict] = []

        for obs in relevant:
            values = _telemetry(config, obs.id)
            vector = _resource_vector(values)
            progress_raw = values.get(progress_key)
            progress = float(progress_raw) if _is_number(progress_raw) else None
            vectors.append(vector)
            progress_values.append(progress)
            per_observation.append({
                "observation_id": obs.id,
                "sequence_no": obs.sequence_no,
                "resource_vector": vector,
                "progress_value": progress,
            })

        total_resource_vector = _sum_vectors(vectors)
        progress_complete = bool(relevant) and all(v is not None for v in progress_values)
        if progress_complete:
            total_progress: float | None = sum(v for v in progress_values if v is not None)
            zero_progress = total_progress == 0
        else:
            total_progress = None
            zero_progress = False

        cpp_by_dimension: dict[str, float] = {}
        if total_progress is not None and total_progress != 0:
            cpp_by_dimension = {
                key: value / total_progress
                for key, value in total_resource_vector.items()
            }

        primary_cost_total = total_resource_vector.get(cost_dimension)
        if (
            primary_cost_total is not None
            and total_progress is not None
            and total_progress != 0
        ):
            cost_per_progress: float | None = primary_cost_total / total_progress
        else:
            cost_per_progress = None

        if cost_per_progress is not None and baseline_cpp is not None:
            normalized_resistance: float | None = cost_per_progress / baseline_cpp
        else:
            normalized_resistance = None

        return [
            {
                "metric_key": "resource_progress_resistance.resource_vector",
                "metric_version": "1.0",
                "value": {
                    "total_resource_vector": total_resource_vector,
                    "per_observation": per_observation,
                    "observations_total": len(relevant),
                    "observations_with_any_resource_telemetry": sum(bool(v) for v in vectors),
                },
                "definition": (
                    "Raw operational resource dimensions per observation and summed "
                    "within each dimension. Units remain separate."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.progress_delta",
                "metric_version": "1.0",
                "value": {
                    "total_progress": total_progress,
                    "progress_values": progress_values,
                    "progress_key": progress_key,
                    "progress_complete": progress_complete,
                    "zero_progress": zero_progress,
                },
                "definition": (
                    "Sum of the predeclared externally measured progress dimension when "
                    "every relevant observation has a progress reading. Missing progress "
                    "is null, not silently converted to zero."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.cost_per_progress",
                "metric_version": "1.0",
                "value": {
                    "cost_per_progress": cost_per_progress,
                    "cost_dimension": cost_dimension,
                    "primary_cost_total": primary_cost_total,
                    "total_progress": total_progress,
                    "cost_per_progress_by_dimension": cpp_by_dimension,
                    "progress_complete": progress_complete,
                    "zero_progress": zero_progress,
                },
                "definition": (
                    "Per-resource-dimension cost divided by complete measured progress. "
                    "The scalar cost_per_progress refers only to the explicitly selected "
                    "cost_dimension (default compute.inference_ms). Heterogeneous units "
                    "are never summed. Null on missing progress, zero progress, or missing "
                    "selected cost telemetry."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.normalized_resistance",
                "metric_version": "1.0",
                "value": {
                    "normalized_resistance": normalized_resistance,
                    "baseline_cost_per_progress": baseline_cpp,
                    "cost_per_progress": cost_per_progress,
                    "cost_dimension": cost_dimension,
                    "available": normalized_resistance is not None,
                },
                "definition": (
                    "Selected-dimension cost_per_progress divided by the experiment's "
                    "registered comparable baseline. 1.0 means equal to that baseline, "
                    "not thermodynamically optimal or healthy."
                ),
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        cpp = next(
            m for m in metrics
            if m["metric_key"] == "resource_progress_resistance.cost_per_progress"
        )["value"]
        claims = [
            {
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    "resource_progress_resistance records operational resource use "
                    "relative to externally measured task progress while preserving "
                    "resource dimensions and units. It does not measure physical or "
                    "thermodynamic resistance."
                ),
                "confidence_label": "weak",
            },
            {
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Low operational cost per progress does not establish structural "
                    "retention; independent retention/stability protocols are required."
                ),
                "confidence_label": "not_applicable",
            },
        ]
        if not cpp["progress_complete"]:
            claims.append({
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Progress telemetry is incomplete, so cost per progress is unresolved "
                    "rather than treating missing progress as zero."
                ),
                "confidence_label": "not_applicable",
            })
        elif cpp["zero_progress"]:
            claims.append({
                "claim_type": "observation",
                "theory_key": None,
                "statement": (
                    "Measured progress was zero; cost per progress is undefined and stored as null."
                ),
                "confidence_label": "not_applicable",
            })
        return claims


_DNE = (
    "Does not establish thermodynamic resistance, far-from-equilibrium dynamics, "
    "persistence in the PPS/STOC sense, consciousness, or qualia."
)


resource_progress_resistance = register(ResourceProgressResistanceProtocol(
    key="resource_progress_resistance",
    version="1.0",
    name="Resource Progress Resistance",
    description=(
        "Measures operational resource use per unit of externally measured task "
        "progress while preserving resource dimensions and units."
    ),
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description="Deterministic task probes with allowlisted resource/progress telemetry.",
    intervention_sequence=[],
    metric_definitions=[
        MetricDefinition(
            key="resource_progress_resistance.resource_vector",
            version="1.0",
            description="Raw resource dimensions per observation and per-dimension totals.",
            inputs="Persisted resource telemetry for resource_progress_response observations.",
            procedure="Extract canonical resource keys and sum only like-named dimensions.",
            range="Mapping of resource dimension to finite numeric value; absent means unavailable.",
            interpretation="Operational resource profile with units preserved.",
            limitations="Missing dimensions do not imply zero cost.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="resource_progress_resistance.progress_delta",
            version="1.0",
            description="Complete externally measured task progress across the run.",
            inputs="Persisted telemetry at config.progress_metric_key (default progress.value).",
            procedure="Sum progress only when every relevant observation has a numeric reading.",
            range="Finite real or null; explicit zero_progress/progress_complete flags.",
            interpretation="Externally defined task advancement, not target self-assessment by default.",
            limitations="Experimenter must establish the progress metric's validity and provenance.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="resource_progress_resistance.cost_per_progress",
            version="1.0",
            description="Per-dimension resource use divided by complete measured progress.",
            inputs="Resource vector, complete progress, and config.cost_dimension.",
            procedure=(
                "Divide each available resource dimension by total progress. Expose one "
                "scalar only for the explicitly selected cost_dimension. Never sum unlike units."
            ),
            range="Per-dimension finite real ratios; selected scalar finite real or null.",
            interpretation="High/low values are meaningful only within the selected resource dimension and experiment.",
            limitations="No universal conversion exists between tokens, milliseconds, graph operations, or bytes.",
            does_not_establish=_DNE,
        ),
        MetricDefinition(
            key="resource_progress_resistance.normalized_resistance",
            version="1.0",
            description="Selected cost-per-progress divided by a comparable registered baseline.",
            inputs="Selected cost_per_progress and positive baseline_cost_per_progress.",
            procedure="Divide only when both values exist and refer to the same cost dimension/conditions.",
            range="Positive/finite real when available, otherwise null.",
            interpretation="1.0 means equal to the registered baseline only.",
            limitations="Baseline comparability is an experiment-design responsibility.",
            does_not_establish=_DNE,
        ),
    ],
    limitations=(
        "Operational resource dimensions are not physical energy measurements. Missing telemetry "
        "is not zero. Cross-dimension scalarization requires an externally justified conversion "
        "model and is deliberately not performed by this protocol."
    ),
))
