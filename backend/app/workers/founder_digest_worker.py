from __future__ import annotations

from app.services.founder_digest import build_founder_digest


def run_founder_digest(opportunities: list[dict]) -> dict:
    digest = build_founder_digest(opportunities)
    return digest.model_dump()
