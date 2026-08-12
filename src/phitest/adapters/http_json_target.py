import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from phitest.domain.errors import AdapterError, OversizedResponseError
from phitest.domain.models import TargetResponse
from phitest import config

_ALLOWED_SCHEMES = re.compile(r"^https?://", re.IGNORECASE)


def _validate_url(url: str) -> None:
    if not _ALLOWED_SCHEMES.match(url):
        raise AdapterError(f"Invalid target URL scheme: {url!r}. Only http/https allowed.")


class HTTPJsonTarget:
    """Generic HTTP JSON target adapter. Secrets supplied via environment variables only."""

    adapter_type = "http_json"

    def __init__(self, adapter_config: dict):
        self._endpoint: str = adapter_config["endpoint"]
        _validate_url(self._endpoint)
        self._method: str = adapter_config.get("method", "POST").upper()
        self._request_template: dict = adapter_config.get("request_template", {"prompt": "{stimulus}"})
        self._response_field: str = adapter_config.get("response_field", "text")
        self._timeout: int = int(adapter_config.get("timeout", 30))
        self._auth_env: str | None = adapter_config.get("auth_env")

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._auth_env:
            token = os.environ.get(self._auth_env, "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def _render_body(self, stimulus: str) -> bytes:
        rendered = {
            k: v.replace("{stimulus}", stimulus) if isinstance(v, str) else v
            for k, v in self._request_template.items()
        }
        return json.dumps(rendered).encode("utf-8")

    def send(self, stimulus: str, context: dict | None = None) -> TargetResponse:
        body = self._render_body(stimulus)
        headers = self._build_headers()
        req = urllib.request.Request(
            self._endpoint, data=body, headers=headers, method=self._method
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read(config.MAX_OBSERVATION_LENGTH + 1)
        except urllib.error.URLError as exc:
            raise AdapterError(f"HTTP target request failed: {exc}") from exc

        if len(raw) > config.MAX_OBSERVATION_LENGTH:
            raise OversizedResponseError(
                f"Response exceeded {config.MAX_OBSERVATION_LENGTH} bytes"
            )

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise AdapterError(f"Malformed JSON response: {exc}") from exc

        text = data.get(self._response_field, "")
        if not isinstance(text, str):
            text = json.dumps(text)

        # Never expose auth headers in metadata
        return TargetResponse(
            text=text,
            metadata={"adapter": "http_json", "endpoint": self._endpoint},
            received_at=datetime.now(timezone.utc),
        )
