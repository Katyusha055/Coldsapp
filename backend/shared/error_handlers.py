from functools import wraps

import httpx
from fastapi import HTTPException


def handle_evo_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Evolution API timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Evolution API unreachable")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    return wrapper
