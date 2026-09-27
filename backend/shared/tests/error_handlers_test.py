import httpx
import pytest
from fastapi import HTTPException

from backend.shared.error_handlers import handle_evo_errors


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
