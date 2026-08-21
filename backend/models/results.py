from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ProviderCategory(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR_RENTAL = "car_rental"
    ATTRACTION = "attraction"


class ProviderResult(BaseModel):
    provider: str
    category: ProviderCategory
    destination_iata: str
    destination_name: str
    title: str
    price_usd: float
    details: dict = {}
    affiliate_url: Optional[str] = None


class TripCombo(BaseModel):
    destination_iata: str
    destination_name: str
    flight: ProviderResult
    hotel: ProviderResult
    car_rental: Optional[ProviderResult] = None
    attractions: list[ProviderResult] = []
    total_cost: float

    @property
    def breakdown(self) -> dict[str, float]:
        return {
            "flight": self.flight.price_usd,
            "hotel": self.hotel.price_usd,
            "car_rental": self.car_rental.price_usd if self.car_rental else 0.0,
            "attractions": sum(a.price_usd for a in self.attractions),
        }


class TripSuggestion(BaseModel):
    rank: int
    destination: str
    destination_iata: str
    total_cost: float
    breakdown: dict[str, float]
    ai_summary: str
    highlights: list[str]
    ranking_reason: str
    affiliate_links: dict[str, Optional[str]]
