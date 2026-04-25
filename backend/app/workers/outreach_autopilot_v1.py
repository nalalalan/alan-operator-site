from __future__ import annotations

from typing import Any, Dict

from app.services.outreach_autopilot_v1 import (
    ingest_reply_autopilot,
    run_outreach_autopilot_batch,
    write_outreach_autopilot_digest,
)


def run_batch(csv_path: str, session_factory=None, auto_send: bool = False, include_b: bool = False) -> Dict[str, Any]:
    result = run_outreach_autopilot_batch(
        csv_path=csv_path,
        session_factory=session_factory,
        auto_send=auto_send,
        include_b=include_b,
    )
    return result.__dict__


def ingest_reply(from_email: str, reply_text: str, provider_message_id: str = "", session_factory=None, auto_send: bool = False) -> Dict[str, Any]:
    result = ingest_reply_autopilot(
        from_email=from_email,
        reply_text=reply_text,
        provider_message_id=provider_message_id,
        session_factory=session_factory,
        auto_send=auto_send,
    )
    return result.__dict__


def write_digest(target_path: str, session_factory=None) -> str:
    return write_outreach_autopilot_digest(target_path=target_path, session_factory=session_factory)
