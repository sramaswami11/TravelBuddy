from factories.base import TravelProviderFactory, TravelAgent
from agents.car_rental.enterprise_agent import EnterpriseAgent


class CarRentalProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            EnterpriseAgent(),
            # TuroAgent(),  # peer-to-peer option, add later
        ]
