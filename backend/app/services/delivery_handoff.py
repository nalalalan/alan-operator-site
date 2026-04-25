from __future__ import annotations


def build_delivery_handoff(company: str, sold_scope: str, notes: str) -> dict:
    return {
        "company": company,
        "sold_scope": sold_scope,
        "promises_made": [
            "Summarize promises directly from the sales notes before kickoff.",
            "Flag any assumption that could surprise delivery later.",
        ],
        "risks": [
            "Underspecified scope",
            "Missing data access",
            "Unclear owner on the client side",
        ],
        "first_actions": [
            "Confirm access requirements",
            "Confirm success metric for the first 30 days",
            "Restate the agreed starting scope in writing",
        ],
        "source_notes_excerpt": (notes or "")[:600],
    }
