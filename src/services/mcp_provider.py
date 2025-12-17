from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from typing import List

from ..services.domain_service import DomainService
from ..constants.schema import AvailabilityOutput, PricingOutput


mcp = FastMCP("namesilo-domains", json_response=True)
_service = DomainService()


@mcp.tool()
async def search_domains(
    query: str,
    tlds: List[str] = [],
    max_results: int = 50,
) -> dict:
    """
    Search NameSilo for domains based on a query.
    """
    return await _service.search_domains(
        query=query,
        tlds=tlds or None,
        max_results=max_results,
    )


@mcp.tool()
async def search_domains_under_budget(
    query: str,
    budget: float,
    count: int,
    tlds: List[str] = [],
) -> dict:
    """
    Search domains and select domains under a given budget.
    """
    return await _service.search_domains_under_budget(
        query=query,
        budget=budget,
        count=count,
        tlds=tlds or None,
    )


@mcp.tool()
async def check_domain_availability(domain: str) -> dict:
    """
    Raw NameSilo availability response for a domain.
    """
    return await _service.check_domain(domain)


@mcp.tool()
async def check_domains_availability(domains: List[str]) -> dict:
    """
    Check availability for multiple domains using NameSilo.
    Accepts up to 200 domains.
    Returns raw NameSilo JSON response.
    """
    return await _service.check_domains(domains)



# @mcp.tool()
# async def get_domain_pricing(tld: str) -> PricingOutput:
#     """
#     Get registration and renewal pricing for a TLD on NameSilo.
#     """
#     return await _service.get_tld_pricing(tld)
