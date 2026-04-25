from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.daily_lead_drop_runner_v1 import run_daily_lead_drop_runner

router = APIRouter()


@router.post("/run")
async def run_daily(request: Request) -> dict:
    payload = await request.json()
    result = run_daily_lead_drop_runner(
        base_dir=str(payload.get("base_dir", "")).strip(),
        auto_send=bool(payload.get("auto_send", False)),
        include_b=bool(payload.get("include_b", False)),
        daily_send_cap=int(payload.get("daily_send_cap", 10)),
    )
    return result.__dict__
