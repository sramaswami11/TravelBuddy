"""
Hotel agent with mock pricing and real Hotellook affiliate links (Travelpayouts marker).
Prices are estimated — the ~$ prefix on the UI sets user expectation.
Affiliate links go to search.hotellook.com where users see real prices and book.
Replace with a real hotel data API once one is identified.
"""
import random
import logging
from datetime import date, timedelta

from config import settings
from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult

logger = logging.getLogger(__name__)

_HOTEL_TEMPLATES: dict[str, list[dict]] = {
    "LAS": [
        {"name": "The LINQ Hotel + Experience", "stars": 3, "base_rate": 79},
        {"name": "Excalibur Hotel & Casino", "stars": 3, "base_rate": 65},
        {"name": "Bellagio Las Vegas", "stars": 5, "base_rate": 289},
        {"name": "Park MGM Las Vegas", "stars": 4, "base_rate": 145},
    ],
    "MCO": [
        {"name": "Rosen Inn at Pointe Orlando", "stars": 3, "base_rate": 89},
        {"name": "DoubleTree by Hilton Orlando", "stars": 3, "base_rate": 109},
        {"name": "Loews Royal Pacific Resort", "stars": 4, "base_rate": 249},
        {"name": "Extended Stay America Orlando", "stars": 2, "base_rate": 72},
    ],
    "MIA": [
        {"name": "Freehand Miami", "stars": 3, "base_rate": 115},
        {"name": "Fontainebleau Miami Beach", "stars": 5, "base_rate": 375},
        {"name": "The Catalina Hotel", "stars": 3, "base_rate": 135},
        {"name": "Holiday Inn Miami Beach", "stars": 3, "base_rate": 129},
    ],
    "BNA": [
        {"name": "Drury Plaza Hotel Nashville", "stars": 3, "base_rate": 109},
        {"name": "Graduate Nashville", "stars": 3, "base_rate": 129},
        {"name": "Thompson Nashville", "stars": 4, "base_rate": 219},
        {"name": "Noelle Nashville", "stars": 4, "base_rate": 179},
    ],
    "MSY": [
        {"name": "Bourbon Orleans Hotel", "stars": 3, "base_rate": 99},
        {"name": "Hotel Monteleone", "stars": 4, "base_rate": 189},
        {"name": "Hyatt Centric French Quarter", "stars": 4, "base_rate": 159},
        {"name": "La Quinta by Wyndham New Orleans", "stars": 2, "base_rate": 75},
    ],
    "DEN": [
        {"name": "The Crawford Hotel", "stars": 4, "base_rate": 149},
        {"name": "Courtyard Denver Downtown", "stars": 3, "base_rate": 119},
        {"name": "Brown Palace Hotel", "stars": 5, "base_rate": 259},
        {"name": "Residence Inn Denver Downtown", "stars": 3, "base_rate": 109},
    ],
    "ORD": [
        {"name": "Freehand Chicago", "stars": 3, "base_rate": 105},
        {"name": "Loews Chicago Hotel", "stars": 4, "base_rate": 189},
        {"name": "Ace Hotel Chicago", "stars": 4, "base_rate": 169},
        {"name": "Holiday Inn Chicago Downtown", "stars": 3, "base_rate": 119},
    ],
    "JFK": [
        {"name": "Ace Hotel New York", "stars": 4, "base_rate": 189},
        {"name": "Row NYC", "stars": 3, "base_rate": 159},
        {"name": "The Standard High Line", "stars": 4, "base_rate": 279},
        {"name": "Pod 51 Hotel", "stars": 2, "base_rate": 119},
    ],
    "SEA": [
        {"name": "Ace Hotel Seattle", "stars": 3, "base_rate": 129},
        {"name": "The Edgewater Hotel", "stars": 4, "base_rate": 219},
        {"name": "Hyatt at Olive 8", "stars": 4, "base_rate": 179},
        {"name": "Green Tortoise Hostel", "stars": 1, "base_rate": 55},
    ],
    "SAT": [
        {"name": "Hotel Emma Pearl", "stars": 4, "base_rate": 189},
        {"name": "Drury Plaza Hotel San Antonio", "stars": 3, "base_rate": 99},
        {"name": "Courtyard San Antonio Riverwalk", "stars": 3, "base_rate": 119},
        {"name": "Homewood Suites San Antonio", "stars": 3, "base_rate": 89},
    ],
    "CUN": [
        {"name": "Secrets The Vine Cancun", "stars": 5, "base_rate": 189},
        {"name": "Iberostar Selection Cancun", "stars": 5, "base_rate": 159},
        {"name": "Hotel Zone Budget Inn", "stars": 2, "base_rate": 55},
        {"name": "Grand Fiesta Americana Coral Beach", "stars": 5, "base_rate": 229},
    ],
    "PUJ": [
        {"name": "Hard Rock Hotel Punta Cana", "stars": 5, "base_rate": 219},
        {"name": "Bahia Principe Grand Bavaro", "stars": 5, "base_rate": 179},
        {"name": "Club Med Punta Cana", "stars": 4, "base_rate": 149},
        {"name": "Barcelo Bavaro Palace", "stars": 5, "base_rate": 199},
    ],
    "MBJ": [
        {"name": "Sandals Montego Bay", "stars": 5, "base_rate": 299},
        {"name": "Iberostar Rose Hall Beach", "stars": 4, "base_rate": 169},
        {"name": "Courtyard Montego Bay", "stars": 3, "base_rate": 119},
        {"name": "Round Hill Hotel & Villas", "stars": 5, "base_rate": 399},
    ],
    "PVR": [
        {"name": "Garza Blanca Preserve Resort", "stars": 5, "base_rate": 199},
        {"name": "Marriott Puerto Vallarta", "stars": 4, "base_rate": 149},
        {"name": "Hotel Rosita", "stars": 3, "base_rate": 79},
        {"name": "Hilton Puerto Vallarta", "stars": 5, "base_rate": 189},
    ],
    "YYZ": [
        {"name": "The Omni King Edward Hotel", "stars": 4, "base_rate": 179},
        {"name": "Hotel X Toronto", "stars": 4, "base_rate": 159},
        {"name": "Pantages Hotel Toronto", "stars": 4, "base_rate": 139},
        {"name": "Delta Hotels Toronto", "stars": 4, "base_rate": 129},
    ],
}

def _hotellook_url(query: SearchQuery) -> str:
    check_in = query.departure_date or (date.today() + timedelta(days=30))
    check_out = check_in + timedelta(days=query.duration_days)
    return (
        f"https://search.hotellook.com/"
        f"?destination={query.destination_iata}"
        f"&checkIn={check_in.isoformat()}"
        f"&checkOut={check_out.isoformat()}"
        f"&adults={query.travelers}"
        f"&marker={settings.travelpayouts_marker}"
    )


class BookingAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "hotellook"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        return self._mock_search(query)

    def _mock_search(self, query: SearchQuery) -> list[ProviderResult]:
        templates = _HOTEL_TEMPLATES.get(query.destination_iata, [])
        if not templates:
            return []

        affiliate_url = _hotellook_url(query)
        results = []
        for hotel in templates:
            nightly = hotel["base_rate"] * random.uniform(0.85, 1.15)
            total = round(nightly * query.duration_days, 2)

            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.HOTEL,
                    destination_iata=query.destination_iata,
                    destination_name=query.destination_name or query.destination_iata,
                    title=hotel["name"],
                    price_usd=total,
                    details={
                        "stars": hotel["stars"],
                        "nightly_rate": round(nightly, 2),
                        "nights": query.duration_days,
                    },
                    affiliate_url=affiliate_url,
                )
            )

        return results
