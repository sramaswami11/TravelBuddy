"""
Skyscanner Partner API — requires partner approval at partners.skyscanner.net.
Stub until access is granted; returns empty list gracefully.
"""
import logging

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderResult

logger = logging.getLogger(__name__)


class SkyscannerAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "skyscanner"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        # TODO: implement with Skyscanner Partner API
        logger.debug("Skyscanner agent not yet implemented, skipping")
        return []
