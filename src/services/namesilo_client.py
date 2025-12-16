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
            return resp.text

    async def check_availability(self, domain: str) -> dict:
        data = await self._request(
            "checkRegisterAvailability",
            {"domains": domain},
        )

        return data

    async def check_availability_bulk(self, domains: List[str]) -> dict:
        """
        Check availability for multiple domains (NameSilo supports up to 200).
        Returns raw JSON response.
        """
        if not domains:
            return {
                "error": "no_domains_provided",
                "domains": [],
            }

        if len(domains) > 200:
            raise ValueError("NameSilo API supports a maximum of 200 domains per request")

        domain_list = ",".join(domains)

        data = await self._request(
            "checkRegisterAvailability",
            {"domains": domain_list},
        )

        return data



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
