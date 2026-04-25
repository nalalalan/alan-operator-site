from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.lead_drop_intake_v1 import process_lead_drop_inbox

router = APIRouter()


@router.post("/run")
async def run_intake(request: Request) -> dict:
    payload = await request.json()
    result = process_lead_drop_inbox(
        base_dir=str(payload.get("base_dir", "")).strip(),
        auto_send=bool(payload.get("auto_send", False)),
        include_b=bool(payload.get("include_b", False)),
        daily_send_cap=int(payload.get("daily_send_cap", 10)),
    )
    return result.__dict__
