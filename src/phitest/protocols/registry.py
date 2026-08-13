from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any

_REGISTRY: dict[str, "ProtocolDefinition"] = {}

# Explicit rather than filesystem discovery: protocol availability is deterministic,
# reviewable, and does not depend on pytest collection order or app.py side effects.
_BUILTIN_PROTOCOL_MODULES: tuple[tuple[str, str], ...] = (
    ("partition_sensitivity", "phitest.protocols.partition_sensitivity"),
    ("global_availability", "phitest.protocols.global_availability"),
    ("metacognitive_calibration", "phitest.protocols.metacognitive_calibration"),
    ("self_model_continuity", "phitest.protocols.self_model_continuity"),
    ("phenomenal_report_consistency", "phitest.protocols.phenomenal_report_consistency"),
    ("perturbation_response", "phitest.protocols.perturbation_response"),
    ("resource_progress_resistance", "phitest.protocols.resource_progress_resistance"),
    ("global_stability_bound", "phitest.protocols.global_stability_bound"),
)


@dataclass
class MetricDefinition:
    key: str
    version: str
    description: str
    inputs: str
    procedure: str
    range: str
    interpretation: str
    limitations: str
    does_not_establish: str


@dataclass
class ProtocolDefinition:
    key: str
    version: str
    name: str
    description: str
    theory_relevance: list[str]
    required_capabilities: list[str]
    stimulus_description: str
    intervention_sequence: list[str]
    metric_definitions: list[MetricDefinition]
    limitations: str

    def generate_stimuli(self, config: dict, seed: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def compute_metrics(
        self,
        stimuli: list[Any],
        observations: list[Any],
        interventions: list[Any],
        config: dict,
    ) -> list[dict[str, Any]]:
        return []

    def generate_claims(
        self,
        stimuli: list[Any],
        observations: list[Any],
        metrics: list[dict],
        config: dict,
    ) -> list[dict[str, Any]]:
        return []


def register(p: ProtocolDefinition) -> ProtocolDefinition:
    _REGISTRY[p.key] = p
    return p


def _ensure_builtin_protocols_loaded() -> None:
    """Load every built-in protocol independent of caller import order.

    The reload fallback matters for tests/tools that reload this registry after protocol
    modules are already cached: import_module alone would not re-run their register()
    calls, leaving a deceptively empty registry.
    """
    for key, module_name in _BUILTIN_PROTOCOL_MODULES:
        if key in _REGISTRY:
            continue
        module = importlib.import_module(module_name)
        if key not in _REGISTRY:
            importlib.reload(module)
        if key not in _REGISTRY:
            raise RuntimeError(f"Built-in protocol {key!r} failed to register from {module_name}")


def get_protocol(key: str) -> ProtocolDefinition | None:
    _ensure_builtin_protocols_loaded()
    return _REGISTRY.get(key)


def list_protocols() -> list[ProtocolDefinition]:
    _ensure_builtin_protocols_loaded()
    return list(_REGISTRY.values())
