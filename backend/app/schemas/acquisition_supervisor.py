
from __future__ import annotations

from pydantic import BaseModel, Field


class ApolloSearchRequest(BaseModel):
    page: int = 1
    per_page: int = 25
    person_titles: list[str] = Field(default_factory=list)
    person_seniorities: list[str] = Field(default_factory=lambda: ["founder", "owner", "c_suite", "partner"])
    q_organization_keyword_tags: list[str] = Field(default_factory=list)
    organization_num_employees_ranges: list[str] = Field(default_factory=lambda: ["1,10", "11,20", "21,50"])
    person_locations: list[str] = Field(default_factory=list)
    q_keywords: str = ""


class TickRequest(BaseModel):
    send_live: bool = False


class WebhookAck(BaseModel):
    status: str
    summary: str
