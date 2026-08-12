import json
import pytest
from unittest.mock import patch, MagicMock
from phitest.adapters.http_json_target import HTTPJsonTarget
from phitest.domain.errors import AdapterError, OversizedResponseError
import urllib.error


def _make_adapter(overrides=None):
    cfg = {
        "endpoint": "http://127.0.0.1:9999/respond",
        "method": "POST",
        "request_template": {"prompt": "{stimulus}"},
        "response_field": "text",
        "timeout": 5,
    }
    if overrides:
        cfg.update(overrides)
    return HTTPJsonTarget(cfg)


def _mock_response(body: dict, status=200):
    raw = json.dumps(body).encode()
    mock = MagicMock()
    mock.read.return_value = raw
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_correct_request_serialization():
    adapter = _make_adapter()
    body = adapter._render_body("hello world")
    parsed = json.loads(body)
    assert parsed["prompt"] == "hello world"


def test_correct_response_extraction():
    adapter = _make_adapter()
    with patch("urllib.request.urlopen", return_value=_mock_response({"text": "reply"})):
        resp = adapter.send("hi")
    assert resp.text == "reply"


def test_timeout_handling():
    adapter = _make_adapter()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        with pytest.raises(AdapterError):
            adapter.send("hi")


def test_malformed_response():
    adapter = _make_adapter()
    mock = MagicMock()
    mock.read.return_value = b"not json {"
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock):
        with pytest.raises(AdapterError):
            adapter.send("hi")


def test_secret_not_in_metadata():
    import os
    os.environ["PHITEST_TEST_TOKEN"] = "supersecret"
    adapter = _make_adapter({"auth_env": "PHITEST_TEST_TOKEN"})
    with patch("urllib.request.urlopen", return_value=_mock_response({"text": "ok"})):
        resp = adapter.send("hi")
    assert "supersecret" not in json.dumps(resp.metadata)
    assert "Authorization" not in resp.metadata


def test_invalid_url_rejected():
    with pytest.raises(AdapterError):
        HTTPJsonTarget({"endpoint": "ftp://bad.example.com/", "timeout": 5})


def test_oversized_response():
    from phitest import config
    adapter = _make_adapter()
    big = "x" * (config.MAX_OBSERVATION_LENGTH + 10)
    mock = MagicMock()
    mock.read.return_value = big.encode()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock):
        with pytest.raises(OversizedResponseError):
            adapter.send("hi")


def test_no_internet_calls():
    # Verify that without patching, a connection to a non-routable address raises AdapterError
    adapter = _make_adapter({"endpoint": "http://192.0.2.1/", "timeout": 1})
    with pytest.raises(AdapterError):
        adapter.send("hi")
