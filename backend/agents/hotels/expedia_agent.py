"""
Expedia Rapid API — requires partner application at expediapartnersolutions.com.
Stub until access is granted; returns empty list gracefully.
"""
import logging

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderResult

logger = logging.getLogger(__name__)


class ExpediaAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "expedia"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        # TODO: implement with Expedia Rapid API
        logger.debug("Expedia agent not yet implemented, skipping")
        return []
