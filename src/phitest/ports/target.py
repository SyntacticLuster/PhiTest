from typing import Protocol, runtime_checkable
from phitest.domain.models import TargetResponse


@runtime_checkable
class TargetAdapter(Protocol):
    adapter_type: str

    def send(self, stimulus: str, context: dict | None = None) -> TargetResponse: ...


@runtime_checkable
class ControllableTarget(Protocol):
    """Optional capability: adapter can receive and apply controlled interventions."""

    def apply_intervention(self, intervention_type: str, config: dict) -> dict:
        """Apply a named intervention. Returns a result dict (may be empty)."""
        ...
