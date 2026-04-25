from __future__ import annotations

import re

from app.schemas.revenue_ops import BuyerFitResult

GOOD_NICHES = {"paid media", "seo", "web design", "growth", "cro", "marketing", "agency"}
BAD_FIT_HINTS = {"enterprise", "self-serve", "summary only", "transcript", "massive org"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def score_buyer_fit(agency_name: str, website: str, calls_per_week: str, bottleneck: str) -> BuyerFitResult:
    score = 0
    reasons: list[str] = []
    merged = " ".join([agency_name, website, bottleneck]).lower()

    if any(token in merged for token in GOOD_NICHES):
        score += 30
        reasons.append("agency-style service positioning present")

    if "follow-up" in merged or "post-call" in merged or "proposal" in merged or "crm" in merged:
        score += 25
        reasons.append("post-call execution pain is visible")

    m = re.search(r"\d+", calls_per_week or "")
    if m:
        count = int(m.group(0))
        if 3 <= count <= 40:
            score += 25
            reasons.append("call volume is high enough to matter")
        elif count > 40:
            score += 10
            reasons.append("high call volume, but may be heavier process fit")
    else:
        reasons.append("call volume unknown")

    if any(token in merged for token in BAD_FIT_HINTS):
        score -= 35
        reasons.append("bad-fit language present")

    if score >= 70:
        band = "strong_fit"
    elif score >= 50:
        band = "likely_fit"
    elif score >= 30:
        band = "maybe_fit"
    elif score >= 10:
        band = "low_fit"
    else:
        band = "not_fit"

    reason = "; ".join(reasons) if reasons else "not enough information"
    return BuyerFitResult(fit_band=band, score=score, reason=reason)
