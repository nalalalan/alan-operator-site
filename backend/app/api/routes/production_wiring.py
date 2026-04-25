from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.services.production_wiring_v1 import process_production_event, production_digest

router = APIRouter()


@router.post("/event")
async def production_event(request: Request) -> dict:
    payload = await request.json()
    if not payload:
        raise HTTPException(status_code=400, detail="empty payload")
    result = process_production_event(payload, auto_send=False)
    return {"status": result.status, "summary": result.summary, **result.__dict__}


@router.get("/digest")
async def production_digest_view() -> dict:
    return production_digest()
