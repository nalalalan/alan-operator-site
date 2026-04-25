from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NextBestAction:
    external_next_move: str
    internal_next_move: str
    biggest_open_risk: str
    ask_next: str


def recommend_next_best_action(call_type: str, memory: dict, notes: str) -> NextBestAction:
    lowered = (notes or "").lower()

    if "tracking" in lowered or "attribution" in lowered:
        return NextBestAction(
            external_next_move="Recommend a paid audit/strategy engagement focused on tracking and attribution trust.",
            internal_next_move="Prepare an audit-first scope outline and list the data access needed before pricing the larger retainer.",
            biggest_open_risk="They may not trust the current data enough to commit to full management yet.",
            ask_next="Can they share current conversion tracking, call tracking, and consult conversion data before the next step?",
        )

    if "proposal" in lowered or "scope" in lowered:
        return NextBestAction(
            external_next_move="Send a tight proposal summary with the clearest recommended starting scope.",
            internal_next_move="Cut optional extras and anchor the first sell around the highest-leverage starting scope.",
            biggest_open_risk="The proposal could sprawl and reduce confidence if the first scope is not tight.",
            ask_next="Which outcome matters most in the first 30 to 45 days?",
        )

    return NextBestAction(
        external_next_move="Send a concise recap email with the clearest immediate next step.",
        internal_next_move="Turn the notes into specific owners, actions, and open questions before the lead cools off.",
        biggest_open_risk="The deal may stall because the next move is not concrete enough yet.",
        ask_next="What single missing fact would make the next commercial step obvious?",
    )
