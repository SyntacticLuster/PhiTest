from datetime import datetime, timezone
from phitest.domain.models import TargetResponse


class ManualTarget:
    """Target adapter for manually-entered responses (offline/human experiments)."""

    adapter_type = "manual"

    def __init__(self, response_text: str = ""):
        self._response_text = response_text

    def set_response(self, text: str) -> None:
        self._response_text = text

    def send(self, stimulus: str, context: dict | None = None) -> TargetResponse:
        return TargetResponse(
            text=self._response_text,
            metadata={"adapter": "manual"},
            received_at=datetime.now(timezone.utc),
        )
