from __future__ import annotations

from app.schemas.revenue_ops import CallContext, PremiumPacket
from app.services.next_best_action import recommend_next_best_action
from app.services.proposal_launcher import launch_proposal_direction
from app.services.output_quality import evaluate_packet_quality


def build_premium_packet(context: CallContext) -> dict:
    action = recommend_next_best_action(context.call_type, memory={}, notes=context.raw_notes)
    proposal = launch_proposal_direction(context.raw_notes)

    packet = PremiumPacket(
        what_we_heard=context.raw_notes[:900],
        what_matters_most=[
            "Reduce delay between the call and the next commercial move.",
            "Clarify what is blocking buyer confidence.",
            "Turn vague follow-up into a concrete decision path.",
        ],
        immediate_next_step=action.external_next_move,
        biggest_open_risk=action.biggest_open_risk,
        external_follow_up_email=(
            f"Subject: Next steps for {context.company or 'the opportunity'}\n\n"
            "Thanks again for the conversation. Based on what we heard, the clearest next move is to keep the scope tight "
            f"and move forward with {proposal.likely_first_sell.lower()}."
        ),
        internal_action_block=[
            action.internal_next_move,
            f"Ask next: {action.ask_next}",
        ],
        crm_update=(
            f"Stage: {context.call_type}. "
            f"Likely first sell: {proposal.likely_first_sell}. "
            f"Biggest open risk: {action.biggest_open_risk}"
        ),
        proposal_direction=(
            f"Likely first sell: {proposal.likely_first_sell}. "
            f"Why now: {proposal.why_now}. "
            f"Workstreams: {', '.join(proposal.workstreams)}. "
            f"Missing inputs: {', '.join(proposal.missing_inputs)}."
        ),
        confidence_notes=[
            "Recommendations are grounded in the current notes and should be tightened if more specific metrics arrive.",
            "Missing inputs should be resolved before a larger retainer is priced.",
        ],
    ).model_dump()

    quality = evaluate_packet_quality(packet)
    packet["quality"] = {
        "allow_send": quality.allow_send,
        "score": quality.score,
        "reasons": quality.reasons,
    }
    return packet
