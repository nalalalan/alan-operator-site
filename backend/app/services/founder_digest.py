from __future__ import annotations

from collections import Counter

from app.schemas.revenue_ops import FounderDigestOut


def build_founder_digest(opportunities: list[dict]) -> FounderDigestOut:
    hottest: list[str] = []
    blocked: list[str] = []
    lagging: list[str] = []
    founder_attention: list[str] = []
    objection_counter: Counter[str] = Counter()

    for opp in opportunities:
        stage = (opp.get("stage") or "").lower()
        risk = opp.get("biggest_risk") or ""
        company = opp.get("company") or "Unknown company"
        if stage in {"proposal", "negotiation"}:
            hottest.append(company)
        if risk:
            blocked.append(f"{company}: {risk}")
        if opp.get("follow_up_lag_days", 0) >= 3:
            lagging.append(f"{company}: {opp.get('follow_up_lag_days')} days")
        if opp.get("needs_founder_attention"):
            founder_attention.append(company)
        for obj in opp.get("objections", []):
            if obj:
                objection_counter[obj] += 1

    recurring = [k for k, _ in objection_counter.most_common(5)]
    return FounderDigestOut(
        hottest_opportunities=hottest[:5],
        blocked_deals=blocked[:5],
        recurring_objections=recurring,
        lagging_follow_up=lagging[:5],
        founder_attention=founder_attention[:5],
    )
