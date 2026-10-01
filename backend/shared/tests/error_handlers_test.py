from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from backend.shared.error_handlers import handle_evo_errors, safe_dispatch


@pytest.mark.asyncio
async def test_handle_evo_errors_passes_through_successful_result():
    @handle_evo_errors
    async def ok():
        return {"value": 42}

    assert await ok() == {"value": 42}


@pytest.mark.asyncio
async def test_handle_evo_errors_maps_timeout_to_504():
    @handle_evo_errors
    async def times_out():
        raise httpx.TimeoutException("timed out")

    with pytest.raises(HTTPException) as exc_info:
        await times_out()
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_handle_evo_errors_maps_connect_error_to_503():
    @handle_evo_errors
    async def unreachable():
        raise httpx.ConnectError("unreachable")

    with pytest.raises(HTTPException) as exc_info:
        await unreachable()
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_handle_evo_errors_propagates_evo_status_and_detail():
    request = httpx.Request("GET", "http://evo.example/instance/connect/1_whatsapp")
    response = httpx.Response(422, request=request, text="invalid instance")
    error = httpx.HTTPStatusError("bad request", request=request, response=response)

    @handle_evo_errors
    async def bad_status():
        raise error

    with pytest.raises(HTTPException) as exc_info:
        await bad_status()
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid instance"


def test_safe_dispatch_passes_through_successful_result():
    @safe_dispatch("some_feature")
    def ok(instance, payload):
        return {"value": 42}

    assert ok({"id": 1}, {}) == {"value": 42}


def test_safe_dispatch_catches_any_exception_and_returns_none():
    @safe_dispatch("some_feature")
    def boom(instance, payload):
        raise RuntimeError("kaboom")

    assert boom({"id": 1}, {}) is None


def test_safe_dispatch_logs_feature_name_and_payload_context():
    @safe_dispatch("some_feature")
    def boom(instance, payload):
        raise RuntimeError("kaboom")

    payload = {"data": {"key": {"remoteJid": "111@s.whatsapp.net"}}}
    with patch('backend.shared.error_handlers.logger') as mock_logger:
        boom({"id": 7}, payload)

    mock_logger.error.assert_called_once()
    args = mock_logger.error.call_args.args
    assert args[0].startswith("[webhook:messages.upsert]")
    assert "some_feature" in args
    assert "111@s.whatsapp.net" in args
    assert 7 in args
    assert mock_logger.error.call_args.kwargs == {"exc_info": True}


def test_safe_dispatch_does_not_affect_other_dispatched_functions():
    """
    The whole point: a decorated function raising must not stop a second,
    independently decorated function from running.
    """
    calls = []

    @safe_dispatch("a")
    def fails(instance, payload):
        calls.append("a")
        raise RuntimeError("kaboom")

    @safe_dispatch("b")
    def succeeds(instance, payload):
        calls.append("b")
        return "b result"

    fails({"id": 1}, {})
    result = succeeds({"id": 1}, {})

    assert calls == ["a", "b"]
    assert result == "b result"
