"""
Viator partner API requires approval (apply at viator.com/affiliate-program).
Mock returns real attraction names per destination with realistic pricing.
"""
import random

from factories.base import TravelAgent
from models.query import SearchQuery
from models.results import ProviderCategory, ProviderResult

_ATTRACTIONS: dict[str, list[dict]] = {
    "LAS": [
        {"name": "Las Vegas Strip Night Tour", "price_per_person": 49},
        {"name": "Hoover Dam Half-Day Tour", "price_per_person": 79},
        {"name": "Grand Canyon South Rim Day Trip", "price_per_person": 119},
        {"name": "High Roller Observation Wheel", "price_per_person": 37},
    ],
    "MCO": [
        {"name": "Walt Disney World 1-Day Ticket", "price_per_person": 109},
        {"name": "Universal Studios Florida 1-Day Ticket", "price_per_person": 119},
        {"name": "Kennedy Space Center Admission", "price_per_person": 57},
        {"name": "Everglades Airboat Tour", "price_per_person": 65},
    ],
    "MIA": [
        {"name": "Miami City Sightseeing Tour", "price_per_person": 39},
        {"name": "Everglades National Park Airboat Ride", "price_per_person": 55},
        {"name": "Vizcaya Museum & Gardens", "price_per_person": 22},
        {"name": "Miami Beach Food Tour", "price_per_person": 79},
    ],
    "BNA": [
        {"name": "Country Music Hall of Fame Admission", "price_per_person": 29},
        {"name": "Grand Ole Opry Tour & Show", "price_per_person": 75},
        {"name": "Nashville Honky Tonk Pub Crawl", "price_per_person": 45},
        {"name": "Jack Daniel's Distillery Tour", "price_per_person": 55},
    ],
    "MSY": [
        {"name": "French Quarter Walking Tour", "price_per_person": 25},
        {"name": "New Orleans Ghost & Cemetery Tour", "price_per_person": 35},
        {"name": "Swamp Tour from New Orleans", "price_per_person": 55},
        {"name": "New Orleans Jazz & Food Tour", "price_per_person": 89},
    ],
    "DEN": [
        {"name": "Rocky Mountain National Park Tour", "price_per_person": 95},
        {"name": "Red Rocks Amphitheatre Visit", "price_per_person": 15},
        {"name": "Denver Craft Brewery Tour", "price_per_person": 59},
        {"name": "White Water Rafting Day Trip", "price_per_person": 109},
    ],
    "ORD": [
        {"name": "Chicago Architecture River Cruise", "price_per_person": 45},
        {"name": "Art Institute of Chicago Admission", "price_per_person": 25},
        {"name": "Chicago Deep Dish Pizza & Food Tour", "price_per_person": 69},
        {"name": "Willis Tower Skydeck Admission", "price_per_person": 28},
    ],
    "JFK": [
        {"name": "Statue of Liberty & Ellis Island Tour", "price_per_person": 45},
        {"name": "NYC Hop-On Hop-Off Bus Tour", "price_per_person": 49},
        {"name": "Metropolitan Museum of Art Admission", "price_per_person": 30},
        {"name": "Top of the Rock Observation Deck", "price_per_person": 40},
    ],
    "SEA": [
        {"name": "Space Needle Admission", "price_per_person": 35},
        {"name": "Pike Place Market Food Tour", "price_per_person": 65},
        {"name": "Mount Rainier Day Trip", "price_per_person": 99},
        {"name": "Seattle Underground Tour", "price_per_person": 25},
    ],
    "SAT": [
        {"name": "The Alamo Guided Tour", "price_per_person": 20},
        {"name": "San Antonio River Walk Boat Tour", "price_per_person": 15},
        {"name": "Natural Bridge Caverns Tour", "price_per_person": 29},
        {"name": "San Antonio Food & Culture Tour", "price_per_person": 79},
    ],
    "CUN": [
        {"name": "Chichen Itza Day Trip with Lunch", "price_per_person": 79},
        {"name": "Tulum & Coba Ruins Tour", "price_per_person": 69},
        {"name": "Xcaret Park All-Inclusive", "price_per_person": 99},
        {"name": "Isla Mujeres Catamaran Tour", "price_per_person": 59},
    ],
    "PUJ": [
        {"name": "Saona Island Catamaran Trip", "price_per_person": 79},
        {"name": "Hoyo Azul & Zip Line Adventure", "price_per_person": 89},
        {"name": "Punta Cana Dune Buggy Safari", "price_per_person": 65},
        {"name": "Indigenous Eyes Ecological Park", "price_per_person": 35},
    ],
    "MBJ": [
        {"name": "Dunn's River Falls & Beach Tour", "price_per_person": 65},
        {"name": "Bob Marley Museum & Kingston Tour", "price_per_person": 79},
        {"name": "Negril Seven Mile Beach Transfer", "price_per_person": 45},
        {"name": "Jamaica Zip Line Adventure", "price_per_person": 89},
    ],
    "PVR": [
        {"name": "Marietas Islands Snorkel Tour", "price_per_person": 75},
        {"name": "Sayulita Day Trip & Surf Lesson", "price_per_person": 85},
        {"name": "Vallarta Food & Tequila Tour", "price_per_person": 59},
        {"name": "Rhythms of the Night at Las Caletas", "price_per_person": 109},
    ],
    "YYZ": [
        {"name": "CN Tower Admission + EdgeWalk", "price_per_person": 99},
        {"name": "Niagara Falls Day Trip", "price_per_person": 69},
        {"name": "Royal Ontario Museum Admission", "price_per_person": 23},
        {"name": "Toronto Distillery District Food Tour", "price_per_person": 75},
    ],
}

_VIATOR_AFFILIATE_BASE = "https://www.viator.com/search/"
_VIATOR_AFFILIATE_PARAMS = "pid=P00319033&mcid=42383&medium=link"


class ViatorAgent(TravelAgent):
    @property
    def provider_name(self) -> str:
        return "viator"

    async def search(self, query: SearchQuery) -> list[ProviderResult]:
        attractions = _ATTRACTIONS.get(query.destination_iata, [])
        results = []

        for attraction in attractions:
            price = attraction["price_per_person"] * query.travelers * random.uniform(0.95, 1.05)
            results.append(
                ProviderResult(
                    provider=self.provider_name,
                    category=ProviderCategory.ATTRACTION,
                    destination_iata=query.destination_iata,
                    destination_name=query.destination_name or query.destination_iata,
                    title=attraction["name"],
                    price_usd=round(price, 2),
                    details={
                        "price_per_person": attraction["price_per_person"],
                        "travelers": query.travelers,
                        "mock": True,
                    },
                    affiliate_url=f"{_VIATOR_AFFILIATE_BASE}{query.destination_iata}?{_VIATOR_AFFILIATE_PARAMS}",
                )
            )

        return results
