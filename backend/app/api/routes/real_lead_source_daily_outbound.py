from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.real_lead_source_daily_outbound_v1 import (
    run_real_lead_source_daily_outbound_v1,
    write_real_lead_daily_outbound_digest,
)

router = APIRouter()


@router.post("/run")
async def run_daily_outbound(request: Request) -> dict:
    payload = await request.json()
    result = run_real_lead_source_daily_outbound_v1(
        source_paths=list(payload.get("source_paths", [])),
        auto_send=bool(payload.get("auto_send", False)),
        include_b=bool(payload.get("include_b", False)),
        daily_send_cap=int(payload.get("daily_send_cap", 10)),
    )
    return result.__dict__


@router.post("/write-digest")
async def write_digest(request: Request) -> dict:
    payload = await request.json()
    path = write_real_lead_daily_outbound_digest(str(payload.get("target_path", "")).strip())
    return {"target_path": path}
