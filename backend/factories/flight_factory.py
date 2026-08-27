from factories.base import TravelProviderFactory, TravelAgent
from agents.flights.travelpayouts_agent import TravelpayoutsAgent


class FlightProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            TravelpayoutsAgent(),
        ]
