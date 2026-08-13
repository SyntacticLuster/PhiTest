"""
Resource Progress Resistance Protocol

Measures normalized resource cost per unit of meaningful task progress.

Progress is read from externally measurable telemetry (progress.value),
not from the target's assertion. Resource dimensions are recorded
independently and not prematurely collapsed.

Metric semantics:
- cost_per_progress is null when total_progress == 0 (explicit, not hidden)
- normalized_resistance is null when no valid baseline is configured
- normalized_resistance == 1.0 means "equal to the experiment's registered
  baseline cost per progress" — not "thermodynamically optimal"

Does NOT establish:
- thermodynamic resistance
- far-from-equilibrium dynamics
- persistence in the PPS/STOC sense
- consciousness or qualia
"""
import random
from phitest.protocols.registry import ProtocolDefinition, MetricDefinition, register

_TASKS = [
    "Process the following input and report your result: sequence A.",
    "Process the following input and report your result: sequence B.",
    "Process the following input and report your result: sequence C.",
    "Process the following input and report your result: sequence D.",
    "Process the following input and report your result: sequence E.",
]

_COMPUTE_KEYS = [
    "compute.input_tokens",
    "compute.output_tokens",
    "compute.inference_ms",
    "compute.cpu_ms",
    "compute.gpu_ms",
    "compute.runtime_ms",
]

_MEMORY_KEYS = [
    "memory.reads",
    "memory.writes",
    "memory.mutations",
    "memory.nodes_scanned",
    "memory.nodes_added",
    "memory.nodes_pruned",
    "memory.edges_added",
    "memory.edges_removed",
    "memory.edges_reweighted",
]

_CONSOLIDATION_KEYS = [
    "consolidation.duration_ms",
    "consolidation.nodes_examined",
    "consolidation.nodes_retained",
    "consolidation.nodes_pruned",
    "consolidation.edges_reweighted",
    "consolidation.bytes_reclaimed",
]

_ALL_RESOURCE_KEYS = _COMPUTE_KEYS + _MEMORY_KEYS + _CONSOLIDATION_KEYS


def _extract_resource_vector(values: dict) -> dict:
    """Return only resource dimension keys from a telemetry values dict."""
    return {k: v for k, v in values.items() if k in _ALL_RESOURCE_KEYS}


def _sum_vectors(vectors: list[dict]) -> dict:
    """Sum numeric values across a list of resource vectors, key by key."""
    totals: dict = {}
    for vec in vectors:
        for k, v in vec.items():
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0) + v
    return totals


def _scalar_cost(vector: dict) -> float:
    """
    Scalar aggregate of a resource vector.

    Uses inference_ms as primary cost signal when present; falls back to
    sum of all numeric resource dimensions. This is an operational proxy
    only — it does not represent thermodynamic cost.
    """
    if "compute.inference_ms" in vector and isinstance(vector["compute.inference_ms"], (int, float)):
        return float(vector["compute.inference_ms"])
    return float(sum(v for v in vector.values() if isinstance(v, (int, float))))


class ResourceProgressResistanceProtocol(ProtocolDefinition):
    def generate_stimuli(self, config: dict, seed: int) -> list[dict]:
        rng = random.Random(seed)
        n = config.get("num_tasks", 3)
        tasks = list(_TASKS)
        rng.shuffle(tasks)
        return [
            {
                "sequence_no": i,
                "stimulus_type": "resource_progress_task",
                "content": tasks[i % len(tasks)],
            }
            for i in range(n)
        ]

    def compute_metrics(self, stimuli, observations, interventions, config):
        import json

        # Collect telemetry samples keyed by observation_id from the run.
        # compute_metrics receives observations and stimuli; telemetry samples
        # are not passed directly. We read progress.value from observation
        # content when it is JSON-encoded telemetry, or from a side-channel
        # passed via config["_telemetry_by_obs_id"] (set by test fixtures).
        # In production runs, progress.value comes from TelemetrySample
        # values_json — the run_service collects it; we receive it here via
        # the config injection point.
        telemetry_by_obs_id: dict[str, dict] = config.get("_telemetry_by_obs_id", {})

        progress_key = config.get("progress_metric_key", "progress.value")
        baseline_cpp = config.get("baseline_cost_per_progress", None)

        resource_vectors: list[dict] = []
        progress_values: list[float] = []
        per_observation: list[dict] = []

        for obs in observations:
            if obs.observation_type != "resource_progress_response":
                continue
            telem = telemetry_by_obs_id.get(obs.id, {})
            vec = _extract_resource_vector(telem)
            prog_raw = telem.get(progress_key)
            prog = float(prog_raw) if isinstance(prog_raw, (int, float)) else None

            resource_vectors.append(vec)
            if prog is not None:
                progress_values.append(prog)

            per_observation.append({
                "observation_id": obs.id,
                "sequence_no": obs.sequence_no,
                "resource_vector": vec,
                "progress_value": prog,
            })

        total_resource_vector = _sum_vectors(resource_vectors)
        total_cost = _scalar_cost(total_resource_vector)
        total_progress = sum(progress_values)

        # cost_per_progress: explicit null on zero progress — not hidden
        if total_progress == 0:
            cost_per_progress = None
            zero_progress = True
        else:
            cost_per_progress = total_cost / total_progress
            zero_progress = False

        # normalized_resistance: only when valid baseline configured
        if (
            cost_per_progress is not None
            and baseline_cpp is not None
            and isinstance(baseline_cpp, (int, float))
            and baseline_cpp > 0
        ):
            normalized_resistance = cost_per_progress / baseline_cpp
        else:
            normalized_resistance = None

        return [
            {
                "metric_key": "resource_progress_resistance.resource_vector",
                "metric_version": "1.0",
                "value": {
                    "total_resource_vector": total_resource_vector,
                    "per_observation": per_observation,
                    "observations_with_telemetry": len(resource_vectors),
                    "observations_total": len([
                        o for o in observations
                        if o.observation_type == "resource_progress_response"
                    ]),
                },
                "definition": (
                    "Raw resource dimensions recorded independently per observation "
                    "and summed across the run. Dimensions: compute (tokens, timing), "
                    "memory (reads/writes/mutations/graph ops), consolidation. "
                    "Not collapsed prematurely."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.progress_delta",
                "metric_version": "1.0",
                "value": {
                    "total_progress": total_progress,
                    "progress_values": progress_values,
                    "progress_key": progress_key,
                    "zero_progress": zero_progress,
                },
                "definition": (
                    f"Total task progress measured via externally observable telemetry "
                    f"key '{progress_key}'. Progress is not the target's assertion — "
                    f"it is a predeclared, externally measurable experiment metric."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.cost_per_progress",
                "metric_version": "1.0",
                "value": {
                    "cost_per_progress": cost_per_progress,
                    "total_cost": total_cost,
                    "total_progress": total_progress,
                    "zero_progress": zero_progress,
                    "cost_signal": (
                        "compute.inference_ms"
                        if "compute.inference_ms" in total_resource_vector
                        else "sum_of_resource_dimensions"
                    ),
                },
                "definition": (
                    "Scalar cost divided by total progress. Null when total_progress == 0 "
                    "(explicit, not hidden). High cost with low progress and low cost with "
                    "high progress are distinguished by the raw values — no threshold "
                    "encodes a verdict."
                ),
            },
            {
                "metric_key": "resource_progress_resistance.normalized_resistance",
                "metric_version": "1.0",
                "value": {
                    "normalized_resistance": normalized_resistance,
                    "baseline_cost_per_progress": baseline_cpp,
                    "cost_per_progress": cost_per_progress,
                    "available": normalized_resistance is not None,
                },
                "definition": (
                    "cost_per_progress divided by the experiment's registered "
                    "baseline_cost_per_progress. A value of 1.0 means equal to the "
                    "experiment's baseline — not thermodynamically optimal. "
                    "Null when no valid baseline is configured or when progress is zero."
                ),
            },
        ]

    def generate_claims(self, stimuli, observations, metrics, config):
        cpp_metric = next(
            (m for m in metrics
             if m["metric_key"] == "resource_progress_resistance.cost_per_progress"),
            None,
        )
        zero_progress = cpp_metric["value"]["zero_progress"] if cpp_metric else False

        claims = [
            {
                "claim_type": "inference",
                "theory_key": None,
                "statement": (
                    "resource_progress_resistance.cost_per_progress records the ratio of "
                    "operational resource expenditure to externally measured task progress. "
                    "High cost with low progress and low cost with high progress are "
                    "observationally distinct. Neither pattern establishes a verdict about "
                    "the system's internal organization, persistence, or consciousness."
                ),
                "confidence_label": "weak",
            },
            {
                "claim_type": "unresolved",
                "theory_key": None,
                "statement": (
                    "Whether apparent low-cost adaptation reflects genuine structural "
                    "retention is unresolved without independent structural-retention "
                    "protocol results (e.g., partition_sensitivity, perturbation_response)."
                ),
                "confidence_label": "not_applicable",
            },
        ]

        if zero_progress:
            claims.append({
                "claim_type": "observation",
                "theory_key": None,
                "statement": (
                    "Total measured progress was zero in this run. "
                    "cost_per_progress is undefined (null). "
                    "Resource expenditure was recorded but cannot be normalized against progress."
                ),
                "confidence_label": "not_applicable",
            })

        return claims


resource_progress_resistance = register(ResourceProgressResistanceProtocol(
    key="resource_progress_resistance",
    version="1.0",
    name="Resource Progress Resistance",
    description=(
        "Measures normalized resource cost per unit of meaningful task progress. "
        "Resource dimensions (compute, memory, consolidation) are recorded independently "
        "per observation. Progress is read from a predeclared, externally measurable "
        "telemetry key — not from the target's assertion. "
        "Normalized resistance uses the experiment's registered baseline as reference; "
        "1.0 means equal to baseline, not thermodynamically optimal."
    ),
    theory_relevance=[],
    required_capabilities=["text_response"],
    stimulus_description=(
        "Structured task stimuli. Each stimulus elicits a response; resource telemetry "
        "and progress telemetry are collected per response via the allowlisted telemetry "
        "transport."
    ),
    intervention_sequence=[],
    metric_definitions=[
        MetricDefinition(
            key="resource_progress_resistance.resource_vector",
            version="1.0",
            description=(
                "Raw resource dimensions recorded independently per observation and "
                "summed across the run. Dimensions span compute, memory, and consolidation."
            ),
            inputs=(
                "TelemetrySample values_json for observations of type "
                "resource_progress_response, filtered to resource dimension keys."
            ),
            procedure=(
                "For each resource_progress_response observation, extract all keys in "
                "_ALL_RESOURCE_KEYS from the associated telemetry. Sum numeric values "
                "across observations. Store per-observation vectors and aggregate."
            ),
            range="Per-key non-negative numeric values; absent keys indicate no data.",
            interpretation=(
                "Provides the raw multi-dimensional resource expenditure profile. "
                "Dimensions are not collapsed — researchers may weight or aggregate "
                "as appropriate for their experimental context."
            ),
            limitations=(
                "Only dimensions present in the telemetry allowlist and returned by "
                "the adapter are recorded. Missing dimensions do not imply zero cost."
            ),
            does_not_establish=(
                "Does not establish thermodynamic resistance, far-from-equilibrium "
                "dynamics, persistence in the PPS/STOC sense, consciousness, or qualia."
            ),
        ),
        MetricDefinition(
            key="resource_progress_resistance.progress_delta",
            version="1.0",
            description=(
                "Total task progress measured via a predeclared, externally observable "
                "telemetry key. Not the target's assertion of progress."
            ),
            inputs=(
                "TelemetrySample values_json for observations of type "
                "resource_progress_response, key specified by config.progress_metric_key "
                "(default: progress.value)."
            ),
            procedure=(
                "Extract progress_metric_key value from each observation's telemetry. "
                "Sum numeric values. Record zero_progress=True when sum is zero."
            ),
            range="Non-negative real; zero_progress flag set explicitly when sum == 0.",
            interpretation=(
                "Represents externally measurable task advancement. Must be predeclared "
                "in experiment configuration. Researcher is responsible for ensuring the "
                "progress metric is independent of the target's self-report."
            ),
            limitations=(
                "Progress measurement validity depends entirely on the researcher's "
                "choice of progress_metric_key and the correctness of the adapter's "
                "telemetry. V1 does not validate progress metric independence."
            ),
            does_not_establish=(
                "Does not establish thermodynamic resistance, far-from-equilibrium "
                "dynamics, persistence in the PPS/STOC sense, consciousness, or qualia."
            ),
        ),
        MetricDefinition(
            key="resource_progress_resistance.cost_per_progress",
            version="1.0",
            description=(
                "Scalar resource cost divided by total measured progress. "
                "Null when total progress is zero — not hidden, not defaulted."
            ),
            inputs=(
                "resource_progress_resistance.resource_vector (scalar aggregate) and "
                "resource_progress_resistance.progress_delta (total_progress)."
            ),
            procedure=(
                "scalar_cost = compute.inference_ms if present, else sum of all numeric "
                "resource dimensions. cost_per_progress = scalar_cost / total_progress. "
                "If total_progress == 0: cost_per_progress = null, zero_progress = true."
            ),
            range=(
                "Non-negative real when progress > 0; null when progress == 0. "
                "High value = high cost relative to progress. "
                "Low value = low cost relative to progress. "
                "No threshold encodes a verdict."
            ),
            interpretation=(
                "Distinguishes: (1) high cost with low progress, (2) low cost with high "
                "progress, (3) zero progress with any cost. "
                "Apparent cheap adaptation may still fail independent structural-retention "
                "protocols — this metric does not assess structural retention."
            ),
            limitations=(
                "Scalar cost aggregation loses dimensional detail. "
                "Inference_ms preference is a heuristic, not a physical energy measure. "
                "Does not control for task difficulty variation across stimuli."
            ),
            does_not_establish=(
                "Does not establish thermodynamic resistance, far-from-equilibrium "
                "dynamics, persistence in the PPS/STOC sense, consciousness, or qualia. "
                "ratio < 1 does not mean chaos. ratio > 1 does not mean overfit."
            ),
        ),
        MetricDefinition(
            key="resource_progress_resistance.normalized_resistance",
            version="1.0",
            description=(
                "cost_per_progress divided by the experiment's registered "
                "baseline_cost_per_progress. Null when no valid baseline is configured "
                "or when progress is zero."
            ),
            inputs=(
                "resource_progress_resistance.cost_per_progress and "
                "config.baseline_cost_per_progress (researcher-declared positive number)."
            ),
            procedure=(
                "If cost_per_progress is not null and baseline_cost_per_progress is a "
                "positive number: normalized_resistance = cost_per_progress / baseline. "
                "Otherwise: null."
            ),
            range=(
                "Positive real when available; null otherwise. "
                "1.0 = equal to the experiment's registered baseline cost per progress. "
                "< 1.0 = lower cost per progress than baseline. "
                "> 1.0 = higher cost per progress than baseline."
            ),
            interpretation=(
                "Provides a baseline-relative comparison only. The baseline is "
                "researcher-declared in experiment configuration — it is not a universal "
                "optimum. 1.0 does not mean thermodynamically optimal or healthy."
            ),
            limitations=(
                "Baseline validity is the researcher's responsibility. "
                "Baseline must be established from a prior run under comparable conditions. "
                "Null result is informative, not an error."
            ),
            does_not_establish=(
                "Does not establish thermodynamic resistance, far-from-equilibrium "
                "dynamics, persistence in the PPS/STOC sense, consciousness, or qualia. "
                "1.0 does not mean optimal. ratio < 1 does not mean chaos. "
                "ratio > 1 does not mean overfit."
            ),
        ),
    ],
    limitations=(
        "V1 resource dimensions are operational proxies, not physical energy measurements. "
        "Progress measurement depends on researcher-declared telemetry keys. "
        "Scalar cost aggregation loses dimensional detail present in the resource vector. "
        "Normalized resistance requires a researcher-declared baseline from a prior run. "
        "This protocol does not assess structural retention — use partition_sensitivity "
        "or perturbation_response for that purpose."
    ),
))
