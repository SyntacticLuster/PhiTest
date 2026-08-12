from typing import Protocol, runtime_checkable
from phitest.domain.models import TargetResponse


@runtime_checkable
class TargetAdapter(Protocol):
    adapter_type: str

    def send(self, stimulus: str, context: dict | None = None) -> TargetResponse: ...
