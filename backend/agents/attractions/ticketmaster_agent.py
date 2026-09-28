"""
Ticketmaster Discovery API — free tier, 5,000 calls/day.
Returns live events (concerts, sports, shows) for the destination city.
Skips gracefully if API key is not configured.
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

import httpx

from config import settings
from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult

logger = logging.getLogger(__name__)

_API_BASE = "https://app.ticketmaster.com/discovery/v2"

_DEST_MAP: dict[str, dict] = {
    d["iata"]: d
    for d in json.loads(
        (Path(__file__).parent.parent.parent / "data" / "destinations.json").read_text()
    )
}


class TicketmasterAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "ticketmaster"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        key = settings.ticketmaster_api_key
        if not key:
            logger.info("TM-DIAG: API key not set — skipping")
            return []

        logger.info("TM-DIAG: key present (len=%d, prefix=%s)", len(key), key[:4])

        dest = _DEST_MAP.get(query.destination_iata or "")
        if not dest:
            logger.info("TM-DIAG: destination %r not in pool — skipping", query.destination_iata)
            return []

        depart = query.departure_date or (date.today() + timedelta(days=30))
        ret = depart + timedelta(days=query.duration_days)

        logger.info("TM-DIAG: querying %s (%s) %s → %s", dest["city"], dest["country_code"], depart, ret)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_API_BASE}/events.json",
                    params={
                        "city": dest["city"],
                        "countryCode": dest["country_code"],
                        "apikey": key,
                        "startDateTime": f"{depart.isoformat()}T00:00:00Z",
                        "endDateTime": f"{ret.isoformat()}T23:59:59Z",
                        "size": 5,
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("TM-DIAG: request failed: %s", exc)
            return []

        events = resp.json().get("_embedded", {}).get("events", [])
        logger.info("TM-DIAG: %d events returned for %s", len(events), dest["city"])
        results = []

        _DEFAULT_PRICE = 75.0  # Ticketmaster rarely exposes priceRanges; use realistic fallback

        for event in events:
            price_ranges = event.get("priceRanges", [])
            price_per_person = price_ranges[0].get("min", 0) if price_ranges else 0
            estimated = price_per_person <= 0
            if estimated:
                price_per_person = _DEFAULT_PRICE

            classification = (event.get("classifications") or [{}])[0]
            segment = classification.get("segment", {}).get("name", "")
            genre = classification.get("genre", {}).get("name", "")
            category_label = f"{segment} · {genre}" if genre and genre not in ("Undefined", "") else segment

            event_date = event.get("dates", {}).get("start", {}).get("localDate", "")

            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.ATTRACTION,
                    destination_iata=query.destination_iata,
                    destination_name=query.destination_name or dest["city"],
                    title=event["name"],
                    price_usd=round(price_per_person * query.travelers, 2),
                    details={
                        "category": category_label,
                        "date": event_date,
                        "price_per_person": price_per_person,
                        "travelers": query.travelers,
                        "price_estimated": estimated,
                    },
                    affiliate_url=event.get("url", f"https://www.ticketmaster.com/search?q={dest['city']}"),
                )
            )

        return results
