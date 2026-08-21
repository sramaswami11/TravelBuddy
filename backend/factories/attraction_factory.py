from factories.base import TravelProviderFactory, TravelAgent
from agents.attractions.viator_agent import ViatorAgent
from agents.attractions.ticketmaster_agent import TicketmasterAgent


class AttractionProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            ViatorAgent(),
            TicketmasterAgent(),
        ]
