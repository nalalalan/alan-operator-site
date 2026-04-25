from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.client_gate_v1 import redeem_client_access_code

router = APIRouter()


@router.post("/redeem")
async def redeem(request: Request) -> dict:
    payload = await request.json()
    code = str(payload.get("access_code", "")).strip()
    result = redeem_client_access_code(code)
    return result.__dict__
