from pydantic import BaseModel


class BuyerRequestIn(BaseModel):
    email: str
    agency_name: str = ""
    website: str = ""
    calls_per_week: str = ""
    bottleneck: str = ""


class BuyerFitResult(BaseModel):
    fit_band: str
    score: int
    reason: str


class CallContext(BaseModel):
    company: str = ""
    contact_name: str = ""
    contact_email: str = ""
    call_type: str = "discovery"
    raw_notes: str
    focus: str = ""
    tone: str = "direct_and_practical"


class PremiumPacket(BaseModel):
    what_we_heard: str
    what_matters_most: list[str]
    immediate_next_step: str
    biggest_open_risk: str
    external_follow_up_email: str
    internal_action_block: list[str]
    crm_update: str
    proposal_direction: str
    confidence_notes: list[str]


class FounderDigestOut(BaseModel):
    hottest_opportunities: list[str]
    blocked_deals: list[str]
    recurring_objections: list[str]
    lagging_follow_up: list[str]
    founder_attention: list[str]
