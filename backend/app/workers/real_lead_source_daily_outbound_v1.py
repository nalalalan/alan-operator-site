from __future__ import annotations

from typing import Any, Dict, List

from app.services.real_lead_source_daily_outbound_v1 import (
    run_real_lead_source_daily_outbound_v1,
    write_real_lead_daily_outbound_digest,
)


def run_daily_outbound(
    source_paths: List[str],
    session_factory=None,
    auto_send: bool = False,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> Dict[str, Any]:
    result = run_real_lead_source_daily_outbound_v1(
        source_paths=source_paths,
        session_factory=session_factory,
        auto_send=auto_send,
        include_b=include_b,
        daily_send_cap=daily_send_cap,
    )
    return result.__dict__


def write_digest(target_path: str, session_factory=None) -> str:
    return write_real_lead_daily_outbound_digest(target_path=target_path, session_factory=session_factory)
