import time
import logging
from dataclasses import dataclass, field

import httpx

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult
from config import settings

logger = logging.getLogger(__name__)

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_INSPIRATION_URL = "https://test.api.amadeus.com/v1/shopping/flight-destinations"
AMADEUS_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0


_token_cache = _TokenCache()


async def _get_access_token() -> str:
    if time.time() < _token_cache.expires_at - 60:
        return _token_cache.access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            AMADEUS_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.amadeus_api_key,
                "client_secret": settings.amadeus_api_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache.access_token = data["access_token"]
        _token_cache.expires_at = time.time() + data["expires_in"]
        return _token_cache.access_token


class AmadeusAgent(TravelAgent):
    """
    Calls Amadeus APIs for flight data.
    - Inspiration mode (destination_iata=None): finds cheapest destinations from origin.
    - Specific mode (destination_iata set): gets flight offers for that route.
    """

    @property
    def provider_name(self) -> str:
        return "amadeus"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        if query.destination_iata is None:
            return await self._inspiration_search(query)
        return await self._offers_search(query)

    async def _inspiration_search(self, query: SearchQuery) -> list[ProviderResult]:
        token = await _get_access_token()
        max_flight_budget = query.budget_usd * 0.40 / query.travelers

        params = {
            "origin": query.origin_iata,
            "maxPrice": int(max_flight_budget),
            "currency": "USD",
            "oneWay": "false",
        }
        if query.duration_days:
            params["duration"] = query.duration_days

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                AMADEUS_INSPIRATION_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            resp.raise_for_status()

        data = resp.json().get("data", [])
        results = []
        for item in data:
            dest_iata = item.get("destination", "")
            price = float(item.get("price", {}).get("total", 0)) * query.travelers
            if not dest_iata or price <= 0:
                continue

            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.FLIGHT,
                    destination_iata=dest_iata,
                    destination_name=dest_iata,  # orchestrator enriches with full name
                    title=f"Round-trip flight {query.origin_iata} → {dest_iata}",
                    price_usd=round(price, 2),
                    details={
                        "departure_date": item.get("departureDate"),
                        "return_date": item.get("returnDate"),
                        "origin": query.origin_iata,
                    },
                    affiliate_url=item.get("links", {}).get("flightOffers"),
                )
            )

        return results

    async def _offers_search(self, query: SearchQuery) -> list[ProviderResult]:
        token = await _get_access_token()

        if not query.departure_date:
            from datetime import date, timedelta
            departure = (date.today() + timedelta(days=30)).isoformat()
        else:
            departure = query.departure_date.isoformat()

        params = {
            "originLocationCode": query.origin_iata,
            "destinationLocationCode": query.destination_iata,
            "departureDate": departure,
            "adults": query.travelers,
            "currencyCode": "USD",
            "max": 5,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                AMADEUS_OFFERS_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            resp.raise_for_status()

        data = resp.json().get("data", [])
        results = []
        for offer in data:
            price = float(offer.get("price", {}).get("grandTotal", 0))
            if price <= 0:
                continue

            itinerary = offer.get("itineraries", [{}])[0]
            segments = itinerary.get("segments", [{}])
            carrier = segments[0].get("carrierCode", "") if segments else ""

            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.FLIGHT,
                    destination_iata=query.destination_iata,
                    destination_name=query.destination_name or query.destination_iata,
                    title=f"{carrier} flight {query.origin_iata} → {query.destination_iata}",
                    price_usd=round(price, 2),
                    details={
                        "carrier": carrier,
                        "departure_date": departure,
                        "duration": itinerary.get("duration"),
                        "stops": len(segments) - 1,
                    },
                )
            )

        return results
