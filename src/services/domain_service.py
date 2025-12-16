from __future__ import annotations

from ..services.namesilo_client import NameSiloClient
from ..constants.schema import AvailabilityOutput, PricingOutput


class DomainService:
    def __init__(self, client: NameSiloClient | None = None) -> None:
        self._client = client or NameSiloClient()

    async def check_domain(self, domain: str) -> dict:
        return await self._client.check_availability(domain)
    
    async def check_domains(self, domains: list[str]) -> dict:
        return await self._client.check_availability_bulk(domains)



    # async def get_tld_pricing(self, tld: str) -> PricingOutput:
    #     register, renew = await self._client.get_pricing(tld)
    #     return {
    #         "tld": tld,
    #         "register": register,
    #         "renew": renew,
    #         "currency": "USD",
    #     }
