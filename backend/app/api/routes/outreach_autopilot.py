from __future__ import annotations

from fastapi import APIRouter, Request

from app.services.outreach_autopilot_v1 import (
    ingest_reply_autopilot,
    run_outreach_autopilot_batch,
    write_outreach_autopilot_digest,
)
from app.services.production_wiring_v1 import production_digest

router = APIRouter()


@router.post("/batch")
async def run_batch(request: Request) -> dict:
    payload = await request.json()
    csv_path = str(payload.get("csv_path", "")).strip()
    include_b = bool(payload.get("include_b", False))
    auto_send = bool(payload.get("auto_send", False))
    result = run_outreach_autopilot_batch(csv_path=csv_path, auto_send=auto_send, include_b=include_b)
    return result.__dict__


@router.post("/reply")
async def ingest_reply(request: Request) -> dict:
    payload = await request.json()
    result = ingest_reply_autopilot(
        from_email=str(payload.get("from_email", "")).strip(),
        reply_text=str(payload.get("reply_text", "")).strip(),
        provider_message_id=str(payload.get("provider_message_id", "")).strip(),
        auto_send=bool(payload.get("auto_send", False)),
    )
    return result.__dict__


@router.get("/digest")
async def digest() -> dict:
    return production_digest()


@router.post("/write-digest")
async def write_digest(request: Request) -> dict:
    payload = await request.json()
    path = write_outreach_autopilot_digest(str(payload.get("target_path", "")).strip())
    return {"target_path": path}
