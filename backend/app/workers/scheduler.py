
"""
Recurring jobs for the acquisition supervisor.

Suggested cadence:
- hourly or daily tick for enrichment + queueing
- webhook-driven reply / payment / intake state transitions
"""

from app.services.acquisition_supervisor import tick_supervisor


async def run_scheduled_jobs() -> dict:
    result = await tick_supervisor(send_live=False)
    return {
        "acquisition_supervisor": "ok",
        "summary": result.summary,
        "queued": result.queued,
        "enriched": result.enriched,
        "sent_live": result.sent_live,
    }
