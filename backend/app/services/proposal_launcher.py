from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProposalLaunch:
    likely_first_sell: str
    why_now: str
    workstreams: list[str]
    missing_inputs: list[str]


def launch_proposal_direction(notes: str) -> ProposalLaunch:
    lowered = (notes or "").lower()

    if "attribution" in lowered or "tracking" in lowered:
        return ProposalLaunch(
            likely_first_sell="Paid audit + strategy engagement",
            why_now="The buyer does not fully trust current measurement, so a narrow diagnostic scope is easier to say yes to than a broad retainer.",
            workstreams=[
                "Measurement and attribution audit",
                "Lead quality diagnosis",
                "Follow-up conversion bottleneck review",
            ],
            missing_inputs=[
                "Current CAC or CPL",
                "Consult conversion rate",
                "Tracking stack details",
                "Call-tracking / CRM setup",
            ],
        )

    if "landing page" in lowered or "conversion" in lowered:
        return ProposalLaunch(
            likely_first_sell="Conversion-focused audit + prioritized implementation plan",
            why_now="They appear to have traffic or interest already, but the path from click to qualified conversation is leaking.",
            workstreams=[
                "Landing page review",
                "Offer/message alignment",
                "Follow-up flow cleanup",
            ],
            missing_inputs=[
                "Current landing pages",
                "Traffic source mix",
                "Lead-to-booking rate",
            ],
        )

    return ProposalLaunch(
        likely_first_sell="Short diagnostic engagement",
        why_now="A smaller first step reduces risk and sharpens the longer-term proposal around what matters most.",
        workstreams=[
            "Current-state diagnosis",
            "Immediate wins",
            "90-day direction",
        ],
        missing_inputs=[
            "Current goals",
            "Main bottlenecks",
            "Who owns implementation",
        ],
    )
