"""
Travelpayouts Data API flight agent.
Inspiration search: GET /v2/prices/latest — one call, cached prices from origin
  to many destinations; we filter to our pool.
Specific route: GET /v1/prices/cheap — cheapest fares for a given route/month.
Booking links go to Aviasales (Travelpayouts property) with affiliate marker.
"""
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

_API_BASE = "https://api.travelpayouts.com"

_POOL: dict[str, str] = {
    d["iata"]: f"{d['city']}, {d['country']}"
    for d in json.loads(
        (Path(__file__).parent.parent.parent / "data" / "destinations.json").read_text()
    )
}


def _aviasales_url(origin: str, destination: str, depart: str, ret: str, travelers: int) -> str:
    """Build an Aviasales search URL with affiliate marker.
    Dates are ISO strings (YYYY-MM-DD). URL format: /search/JFK1210CUN17101
    where each date segment is DDMM (day+month, zero-padded).
    """
    try:
        d = datetime.strptime(depart[:10], "%Y-%m-%d")
        r = datetime.strptime(ret[:10], "%Y-%m-%d")
        dep_seg = d.strftime("%d%m")
        ret_seg = r.strftime("%d%m")
    except (ValueError, TypeError):
        dep_seg = ""
        ret_seg = ""

    path = f"{origin}{dep_seg}{destination}{ret_seg}{travelers}" if dep_seg else f"{origin}{destination}{travelers}"
    return f"https://www.aviasales.com/search/{path}?marker={settings.travelpayouts_marker}"


def _default_dates(query: SearchQuery) -> tuple[str, str]:
    depart = query.departure_date or (date.today() + timedelta(days=30))
    ret = depart + timedelta(days=query.duration_days)
    return depart.isoformat(), ret.isoformat()


def _depart_month(query: SearchQuery) -> str:
    d = query.departure_date or (date.today() + timedelta(days=30))
    return d.strftime("%Y-%m")


def _return_month(query: SearchQuery) -> str:
    d = query.departure_date or (date.today() + timedelta(days=30))
    return (d + timedelta(days=query.duration_days)).strftime("%Y-%m")


class TravelpayoutsAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "travelpayouts"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        if query.destination_iata is None:
            return await self._inspiration_search(query)
        return await self._route_search(query)

    async def _inspiration_search(self, query: SearchQuery) -> list[ProviderResult]:
        """
        v2/prices/latest response shape:
          data[]: { origin, destination, depart_date, return_date, value (price),
                    gate (booking platform), number_of_changes, ... }
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_API_BASE}/v2/prices/latest",
                    params={
                        "origin": query.origin_iata,
                        "currency": "usd",
                        "token": settings.travelpayouts_token,
                        "limit": 1000,
                        "period_type": "month",
                        "one_way": "false",
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Travelpayouts inspiration search failed: %s", exc)
            return []

        body = resp.json()
        if body.get("error"):
            logger.warning("Travelpayouts API error: %s", body["error"])
            return []

        depart_default, return_default = _default_dates(query)
        results = []

        for item in body.get("data", []):
            dest = item.get("destination")
            if dest not in _POOL:
                continue
            price = item.get("value", 0)
            if price <= 0:
                continue

            depart = item.get("depart_date") or depart_default
            ret = item.get("return_date") or return_default
            gate = item.get("gate", "")

            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.FLIGHT,
                    destination_iata=dest,
                    destination_name=_POOL[dest],
                    title=f"Round-trip {query.origin_iata} → {dest}",
                    price_usd=round(price * query.travelers, 2),
                    details={
                        "airline": gate,
                        "departure_at": depart,
                        "return_at": ret,
                        "transfers": item.get("number_of_changes", 0),
                        "travelers": query.travelers,
                    },
                    affiliate_url=_aviasales_url(query.origin_iata, dest, depart, ret, query.travelers),
                )
            )

        return results

    async def _route_search(self, query: SearchQuery) -> list[ProviderResult]:
        """
        v1/prices/cheap response shape:
          data[DEST][TRANSFERS]: { airline, departure_at, return_at, price, ... }
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_API_BASE}/v1/prices/cheap",
                    params={
                        "origin": query.origin_iata,
                        "destination": query.destination_iata,
                        "depart_date": _depart_month(query),
                        "return_date": _return_month(query),
                        "currency": "usd",
                        "token": settings.travelpayouts_token,
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning(
                "Travelpayouts route search %s→%s failed: %s",
                query.origin_iata, query.destination_iata, exc,
            )
            return []

        body = resp.json()
        if not body.get("success"):
            return []

        dest_data = body.get("data", {}).get(query.destination_iata, {})
        destination_name = query.destination_name or query.destination_iata

        results = []
        for transfers_key, offer in dest_data.items():
            price = offer.get("price", 0)
            if price <= 0:
                continue
            airline = offer.get("airline", "")
            depart = offer.get("departure_at", "")
            ret = offer.get("return_at", "")
            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.FLIGHT,
                    destination_iata=query.destination_iata,
                    destination_name=destination_name,
                    title=f"{airline} round-trip {query.origin_iata} → {query.destination_iata}".strip(),
                    price_usd=round(price * query.travelers, 2),
                    details={
                        "airline": airline,
                        "departure_at": depart,
                        "return_at": ret,
                        "transfers": int(transfers_key),
                        "travelers": query.travelers,
                    },
                    affiliate_url=_aviasales_url(query.origin_iata, query.destination_iata, depart, ret, query.travelers),
                )
            )

        return results
