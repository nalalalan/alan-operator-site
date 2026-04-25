from __future__ import annotations

from typing import Any, Dict

from app.services.lead_drop_intake_v1 import process_lead_drop_inbox


def run_lead_drop_intake(
    base_dir: str,
    session_factory=None,
    auto_send: bool = False,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> Dict[str, Any]:
    result = process_lead_drop_inbox(
        base_dir=base_dir,
        session_factory=session_factory,
        auto_send=auto_send,
        include_b=include_b,
        daily_send_cap=daily_send_cap,
    )
    return result.__dict__
