import asyncio
import logging
from abc import ABC, abstractmethod

from models.query import SearchQuery
from models.results import ProviderResult

logger = logging.getLogger(__name__)


class TravelAgent(ABC):
    """Base class for all provider-specific agents."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[ProviderResult]: ...


class TravelProviderFactory(ABC):
    """
    Abstract factory — one per travel category (flights, hotels, etc.).
    Concrete factories wire in the agents for that category.
    """

    @abstractmethod
    def get_agents(self) -> list[TravelAgent]: ...

    async def search_all(self, query: SearchQuery) -> list[ProviderResult]:
        """Fan out to all agents concurrently; swallow individual failures."""
        tasks = [agent.search(query) for agent in self.get_agents()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined: list[ProviderResult] = []
        for agent, result in zip(self.get_agents(), results):
            if isinstance(result, Exception):
                logger.warning("Agent %s failed: %s", agent.provider_name, result)
                continue
            combined.extend(result)

        return combined
