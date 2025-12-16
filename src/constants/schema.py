from __future__ import annotations
from typing import TypedDict, Optional


class AvailabilityOutput(TypedDict):
    domain: str
    available: bool
    status: Optional[str]


class PricingOutput(TypedDict):
    tld: str
    register: Optional[float]
    renew: Optional[float]
    currency: str
