"""
Ticketmaster Discovery API — free tier, 5,000 calls/day.
Stub until API key is configured; returns empty list gracefully.
"""
import logging

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderResult

logger = logging.getLogger(__name__)


class TicketmasterAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "ticketmaster"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        # TODO: implement with Ticketmaster Discovery API
        # GET https://app.ticketmaster.com/discovery/v2/events.json
        #   ?city={city}&apikey={key}&startDateTime=...&endDateTime=...&size=5
        logger.debug("Ticketmaster agent not yet implemented, skipping")
        return []
