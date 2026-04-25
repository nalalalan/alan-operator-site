from __future__ import annotations

from typing import Any, Dict

from app.services.daily_lead_drop_runner_v1 import run_daily_lead_drop_runner


def run_daily(
    base_dir: str,
    session_factory=None,
    auto_send: bool = False,
    include_b: bool = False,
    daily_send_cap: int = 10,
) -> Dict[str, Any]:
    result = run_daily_lead_drop_runner(
        base_dir=base_dir,
        session_factory=session_factory,
        auto_send=auto_send,
        include_b=include_b,
        daily_send_cap=daily_send_cap,
    )
    return result.__dict__
