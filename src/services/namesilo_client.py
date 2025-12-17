from __future__ import annotations

import httpx
import xml.etree.ElementTree as ET
from typing import Optional, List

from ..helper.config import namesilo_settings

class NameSiloClient:
    def __init__(self) -> None:
        self.api_key = namesilo_settings.api_key
        self.base_url = namesilo_settings.base_url

    async def _request(self, endpoint: str, params: dict) -> str:
        q = {
            "version": 1,
            "type": "json",
            "key": self.api_key,
        }
        q.update(params)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{self.base_url}{endpoint}", params=q)
            resp.raise_for_status()
            # return resp.text
            return resp.json()

    async def check_availability(self, domain: str) -> dict:
        data = await self._request(
            "checkRegisterAvailability",
            {"domains": domain},
        )

        return data

    async def check_availability_bulk(self, domains: list[str]) -> dict:
        if not domains:
            return {}

        if len(domains) > 200:
            raise ValueError("Maximum 200 domains allowed")

        domain_list = ",".join(domains)

        return await self._request(
            "checkRegisterAvailability",
            {"domains": domain_list},
        )




    # async def get_pricing(self, tld: str) -> tuple[Optional[float], Optional[float]]:
    #     xml = await self._request("getPrices", {})
    #     root = ET.fromstring(xml)

    #     for price in root.findall(".//price"):
    #         if price.attrib.get("tld", "").lower() == tld.lower():
    #             reg = price.attrib.get("registration")
    #             ren = price.attrib.get("renew")
    #             return (
    #                 float(reg) if reg else None,
    #                 float(ren) if ren else None,
    #             )

    #     return None, None
