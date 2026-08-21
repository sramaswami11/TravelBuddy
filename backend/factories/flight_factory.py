from factories.base import TravelProviderFactory, TravelAgent
from agents.flights.duffel_agent import DuffelAgent


class FlightProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            DuffelAgent(),
            # SkyscannerAgent(),  # add when partner access is approved
        ]
