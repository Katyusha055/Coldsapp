import backend.whatsapp.repository as rep
from backend.database.connect import connect
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

async def get_or_create_instance(user_id):
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
        if instance is not None:
            return instance

        instance_name = f"{user_id}_whatsapp"
        await rep.create_evolution_instance(instance_name)
        return rep.create_instance(conn, user_id, instance_name)

@handle_evo_errors
async def get_qr(user_id):
    instance = await get_or_create_instance(user_id)
    qr = await rep.get_evolution_qr(instance["instance_name"])
    return {"qr": qr}

@handle_evo_errors
async def instance_status(user_id):
    with connect() as conn:
        instance = rep.get_instance_by_user_id(conn, user_id)
    if instance is None:
        return {"status": "not_found"}
    status = await rep.get_evolution_instance_status(instance["instance_name"])
    return {"status": status}
