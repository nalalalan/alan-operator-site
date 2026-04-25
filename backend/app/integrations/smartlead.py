from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List

import httpx

from app.core.config import settings


class SmartleadClient:
    base_url = "https://server.smartlead.ai/api/v1"

    def _params(self) -> Dict[str, str]:
        return {"api_key": settings.smartlead_api_key}

    async def add_lead_to_campaign(self, campaign_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/campaigns/{campaign_id}/leads",
                params=self._params(),
                json={"lead_list": [payload]},
            )
            print("SMARTLEAD STATUS:", response.status_code)
            print("SMARTLEAD BODY:", response.text)
            response.raise_for_status()
            return response.json()

    async def add_leads_to_campaign(self, campaign_id: str, payloads: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for payload in payloads:
            try:
                out.append(await self.add_lead_to_campaign(campaign_id, payload))
            except Exception as exc:
                out.append({"error": str(exc), "payload": payload})
        return out

    async def pause_lead(self, campaign_id: str, lead_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/campaigns/{campaign_id}/leads/{lead_id}/pause",
                params=self._params(),
            )
            response.raise_for_status()
            return response.json()

    async def reply_to_lead(self, campaign_id: str, lead_id: str, message: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/campaigns/{campaign_id}/leads/{lead_id}/reply",
                params=self._params(),
                json={"message": message},
            )
            print("SMARTLEAD REPLY STATUS:", response.status_code)
            print("SMARTLEAD REPLY BODY:", response.text)
            response.raise_for_status()
            return response.json()

    def reply_to_lead_sync(self, campaign_id: str, lead_id: str, message: str) -> Dict[str, Any]:
        return asyncio.run(self.reply_to_lead(campaign_id, lead_id, message))