"""
Duffel Flights API — https://duffel.com
Free to search; fees apply only when completing a booking through Duffel.
Sandbox keys start with duffel_test_; production keys start with duffel_live_.
"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from config import settings
from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.duffel.com"
_DUFFEL_VERSION = "v2"

# Load pool destinations once at module startup so inspiration mode knows where to search.
_POOL: list[dict] = json.loads(
    (Path(__file__).parent.parent.parent / "data" / "destinations.json").read_text()
)
_POOL_DESTINATIONS: dict[str, str] = {
    d["iata"]: f"{d['city']}, {d['country']}" for d in _POOL
}


def _skyscanner_url(origin: str, destination: str, departure: str, return_date: str, travelers: int) -> str:
    dep = datetime.strptime(departure, "%Y-%m-%d").strftime("%d%m%y")
    ret = datetime.strptime(return_date, "%Y-%m-%d").strftime("%d%m%y")
    # Add partner_id=YOUR_SKYSCANNER_PARTNER_ID here once enrolled in Skyscanner affiliate program
    return (
        f"https://www.skyscanner.net/transport/flights"
        f"/{origin.lower()}/{destination.lower()}/{dep}/{ret}"
        f"/?adults={travelers}&currency=USD"
    )


def _default_dates(query: SearchQuery) -> tuple[str, str]:
    """Return (departure, return) ISO date strings, defaulting to 30 days out."""
    depart = query.departure_date or (date.today() + timedelta(days=30))
    ret = depart + timedelta(days=query.duration_days)
    return depart.isoformat(), ret.isoformat()


def _build_request_body(
    origin: str,
    destination: str,
    departure: str,
    return_date: str,
    travelers: int,
) -> dict:
    return {
        "data": {
            "slices": [
                {"origin": origin, "destination": destination, "departure_date": departure},
                {"origin": destination, "destination": origin, "departure_date": return_date},
            ],
            "passengers": [{"type": "adult"} for _ in range(travelers)],
            "cabin_class": "economy",
        }
    }


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.duffel_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Duffel-Version": _DUFFEL_VERSION,
    }


async def _fetch_offers(
    client: httpx.AsyncClient,
    origin: str,
    destination: str,
    destination_name: str,
    departure: str,
    return_date: str,
    travelers: int,
) -> list[ProviderResult]:
    """Search one origin→destination route and return all offers as ProviderResults."""
    body = _build_request_body(origin, destination, departure, return_date, travelers)

    try:
        resp = await client.post(
            f"{_BASE_URL}/air/offer_requests",
            json=body,
            headers=_headers(),
            params={"return_offers": "true"},
            timeout=20.0,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Duffel %s→%s returned %s: %s",
            origin, destination, exc.response.status_code, exc.response.text[:200],
        )
        return []
    except httpx.RequestError as exc:
        logger.warning("Duffel network error %s→%s: %s", origin, destination, exc)
        return []

    offers = resp.json().get("data", {}).get("offers", [])
    results = []

    for offer in offers:
        try:
            # total_amount covers ALL passengers (Duffel prices per order, not per person)
            price = float(offer["total_amount"])
            currency = offer.get("total_currency", "USD")
            airline = offer.get("owner", {}).get("name", "Unknown Airline")
            airline_code = offer.get("owner", {}).get("iata_code", "")

            if currency != "USD":
                logger.debug("Skipping non-USD offer (%s) for %s", currency, destination)
                continue
            if price <= 0:
                continue

            results.append(
                ProviderResult(
                    provider="duffel",
                    category=ProviderCategory.FLIGHT,
                    destination_iata=destination,
                    destination_name=destination_name,
                    title=f"{airline} round-trip {origin} → {destination}",
                    price_usd=round(price, 2),
                    details={
                        "offer_id": offer.get("id"),
                        "airline": airline,
                        "airline_code": airline_code,
                        "departure_date": departure,
                        "return_date": return_date,
                        "travelers": travelers,
                    },
                    affiliate_url=_skyscanner_url(origin, destination, departure, return_date, travelers),
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.debug("Skipping malformed offer for %s: %s", destination, exc)

    return results


class DuffelAgent(TravelAgent):
    """
    Inspiration mode  (destination_iata=None): fans out to all 15 pool destinations
    concurrently and returns the cheapest offer per route.  The orchestrator then
    picks the top 5 cheapest destinations to evaluate further.

    Specific mode (destination_iata set): searches a single route.
    """

    @property
    def provider_name(self) -> str:
        return "duffel"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        if query.destination_iata is None:
            return await self._inspiration_search(query)
        return await self._route_search(query)

    async def _inspiration_search(self, query: SearchQuery) -> list[ProviderResult]:
        departure, return_date = _default_dates(query)

        async with httpx.AsyncClient() as client:
            tasks = [
                _fetch_offers(
                    client,
                    origin=query.origin_iata,
                    destination=iata,
                    destination_name=name,
                    departure=departure,
                    return_date=return_date,
                    travelers=query.travelers,
                )
                for iata, name in _POOL_DESTINATIONS.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: list[ProviderResult] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Inspiration search task failed: %s", r)
            else:
                combined.extend(r)

        return combined

    async def _route_search(self, query: SearchQuery) -> list[ProviderResult]:
        departure, return_date = _default_dates(query)
        destination_name = query.destination_name or query.destination_iata

        async with httpx.AsyncClient() as client:
            return await _fetch_offers(
                client,
                origin=query.origin_iata,
                destination=query.destination_iata,
                destination_name=destination_name,
                departure=departure,
                return_date=return_date,
                travelers=query.travelers,
            )
