from factories.base import TravelProviderFactory, TravelAgent
from agents.hotels.booking_agent import BookingAgent


class HotelProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            BookingAgent(),
            # ExpediaAgent(),  # add when partner access is approved
        ]
