"""
Mock car rental agent using realistic day rates per destination.
Swap for real Enterprise / CARS API when partner access is available.
"""
import random

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult

_DAY_RATES: dict[str, dict] = {
    "LAS": {"economy": 38, "standard": 55, "suv": 80},
    "MCO": {"economy": 42, "standard": 60, "suv": 88},
    "MIA": {"economy": 48, "standard": 68, "suv": 95},
    "BNA": {"economy": 40, "standard": 58, "suv": 82},
    "MSY": {"economy": 36, "standard": 52, "suv": 75},
    "DEN": {"economy": 44, "standard": 62, "suv": 90},
    "ORD": {"economy": 50, "standard": 70, "suv": 98},
    "JFK": {"economy": 65, "standard": 90, "suv": 130},
    "SEA": {"economy": 48, "standard": 68, "suv": 95},
    "SAT": {"economy": 35, "standard": 50, "suv": 72},
    "CUN": {"economy": 28, "standard": 42, "suv": 65},
    "PUJ": {"economy": 32, "standard": 48, "suv": 70},
    "MBJ": {"economy": 38, "standard": 55, "suv": 80},
    "PVR": {"economy": 30, "standard": 45, "suv": 68},
    "YYZ": {"economy": 52, "standard": 72, "suv": 105},
}
_DEFAULT_RATES = {"economy": 45, "standard": 65, "suv": 90}

_ENTERPRISE_AFFILIATE = "https://www.enterprise.com/en/car-rental/locations/"


class EnterpriseAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "enterprise"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        rates = _DAY_RATES.get(query.destination_iata, _DEFAULT_RATES)
        results = []

        for car_class, base_rate in rates.items():
            daily = base_rate * random.uniform(0.9, 1.1)
            total = round(daily * query.duration_days, 2)
            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.CAR_RENTAL,
                    destination_iata=query.destination_iata,
                    destination_name=query.destination_name or query.destination_iata,
                    title=f"Enterprise {car_class.title()} Car",
                    price_usd=total,
                    details={
                        "class": car_class,
                        "daily_rate": round(daily, 2),
                        "days": query.duration_days,
                        "mock": True,
                    },
                    affiliate_url=_ENTERPRISE_AFFILIATE,
                )
            )

        return results
