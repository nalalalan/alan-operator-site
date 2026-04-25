from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OutputQualityResult:
    allow_send: bool
    score: int
    reasons: list[str]


def evaluate_packet_quality(packet: dict) -> OutputQualityResult:
    score = 100
    reasons: list[str] = []

    text = " ".join(
        str(packet.get(key, ""))
        for key in [
            "what_we_heard",
            "immediate_next_step",
            "biggest_open_risk",
            "external_follow_up_email",
            "proposal_direction",
        ]
    ).lower()

    if "[your name]" in text or "[name if available]" in text:
        score -= 40
        reasons.append("placeholder survived")

    if "unknown" in text:
        score -= 10
        reasons.append("unknown filler present")

    if len((packet.get("what_we_heard") or "").strip()) < 40:
        score -= 20
        reasons.append("summary too thin")

    if len((packet.get("immediate_next_step") or "").strip()) < 20:
        score -= 20
        reasons.append("next step too weak")

    allow_send = score >= 70
    return OutputQualityResult(allow_send=allow_send, score=score, reasons=reasons)
