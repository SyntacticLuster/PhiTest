from __future__ import annotations
from dataclasses import dataclass
from importlib import import_module
from typing import Any

_REGISTRY: dict[str, "ProtocolDefinition"] = {}
_BUILTIN_MODULES = (
    "partition_sensitivity",
    "global_availability",
    "metacognitive_calibration",
    "self_model_continuity",
    "phenomenal_report_consistency",
    "perturbation_response",
    "resource_progress_resistance",
    "global_stability_bound",
    "retrieval_induced_plasticity",
)
_BUILTINS_LOADED = False


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


def _ensure_builtins_loaded() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    for module_name in _BUILTIN_MODULES:
        import_module(f"phitest.protocols.{module_name}")
    _BUILTINS_LOADED = True


def get_protocol(key: str) -> ProtocolDefinition | None:
    _ensure_builtins_loaded()
    return _REGISTRY.get(key)


def list_protocols() -> list[ProtocolDefinition]:
    _ensure_builtins_loaded()
    return list(_REGISTRY.values())
