import asyncio
import json
import logging
from pathlib import Path

from models.query import SearchQuery, TripQuery
from models.results import ProviderResult, ProviderCategory, TripCombo
from factories.flight_factory import FlightProviderFactory
from factories.hotel_factory import HotelProviderFactory
from factories.car_rental_factory import CarRentalProviderFactory
from factories.attraction_factory import AttractionProviderFactory

logger = logging.getLogger(__name__)

_DESTINATIONS: list[dict] = json.loads(
    (Path(__file__).parent / "data" / "destinations.json").read_text()
)
_DEST_BY_IATA: dict[str, dict] = {d["iata"]: d for d in _DESTINATIONS}

# Budget allocation — rough splits, AI re-ranks regardless
_FLIGHT_BUDGET_RATIO = 0.40
_HOTEL_BUDGET_RATIO = 0.35
_CAR_BUDGET_RATIO = 0.12
_ATTRACTION_BUDGET_RATIO = 0.13

_MAX_DESTINATIONS_TO_EVALUATE = 5
_MAX_ATTRACTIONS_PER_COMBO = 2


def _pick_best(results: list[ProviderResult], budget: float) -> ProviderResult | None:
    """Return the most expensive option that still fits within budget, or cheapest if all exceed."""
    within = [r for r in results if r.price_usd <= budget]
    if within:
        return max(within, key=lambda r: r.price_usd)
    return min(results, key=lambda r: r.price_usd) if results else None


def _pick_attractions(
    results: list[ProviderResult], budget: float, n: int = _MAX_ATTRACTIONS_PER_COMBO
) -> list[ProviderResult]:
    """Pick up to n attractions within the remaining budget."""
    sorted_results = sorted(results, key=lambda r: r.price_usd)
    picked, spent = [], 0.0
    for attraction in sorted_results:
        if len(picked) >= n:
            break
        if spent + attraction.price_usd <= budget:
            picked.append(attraction)
            spent += attraction.price_usd
    return picked


async def _build_combo_for_destination(
    dest: dict,
    flight: ProviderResult,
    query: TripQuery,
) -> TripCombo | None:
    remaining = query.budget_usd - flight.price_usd
    if remaining <= 0:
        return None

    dest_query = SearchQuery(
        origin_iata=query.origin_iata,
        destination_iata=dest["iata"],
        destination_name=f"{dest['city']}, {dest['country']}",
        budget_usd=remaining,
        duration_days=query.duration_days,
        travelers=query.travelers,
        departure_date=query.departure_date,
    )

    hotel_budget = remaining * (_HOTEL_BUDGET_RATIO / (1 - _FLIGHT_BUDGET_RATIO))
    car_budget = remaining * (_CAR_BUDGET_RATIO / (1 - _FLIGHT_BUDGET_RATIO))
    attraction_budget = remaining * (_ATTRACTION_BUDGET_RATIO / (1 - _FLIGHT_BUDGET_RATIO))

    hotels, cars, attractions = await asyncio.gather(
        HotelProviderFactory().search_all(dest_query),
        CarRentalProviderFactory().search_all(dest_query),
        AttractionProviderFactory().search_all(dest_query),
    )

    best_hotel = _pick_best(hotels, hotel_budget)
    best_car = _pick_best(cars, car_budget)
    picked_attractions = _pick_attractions(attractions, attraction_budget)

    if not best_hotel:
        logger.warning("No hotel results for %s, skipping", dest["iata"])
        return None

    total = (
        flight.price_usd
        + best_hotel.price_usd
        + (best_car.price_usd if best_car else 0)
        + sum(a.price_usd for a in picked_attractions)
    )

    return TripCombo(
        destination_iata=dest["iata"],
        destination_name=f"{dest['city']}, {dest['country']}",
        flight=flight,
        hotel=best_hotel,
        car_rental=best_car,
        attractions=picked_attractions,
        total_cost=round(total, 2),
    )


async def find_trips(query: TripQuery) -> list[TripCombo]:
    """
    1. Ask flight factory for cheapest destinations (inspiration search).
    2. Filter to our destination pool.
    3. For the top N cheapest destinations, fan out to hotel/car/attraction factories.
    4. Return assembled TripCombos sorted by total cost.
    """
    inspiration_query = SearchQuery(
        origin_iata=query.origin_iata,
        destination_iata=None,
        budget_usd=query.budget_usd,
        duration_days=query.duration_days,
        travelers=query.travelers,
        departure_date=query.departure_date,
    )

    flight_results = await FlightProviderFactory().search_all(inspiration_query)

    # Filter to our pool and deduplicate by destination (keep cheapest flight)
    pool_flights: dict[str, ProviderResult] = {}
    for flight in flight_results:
        iata = flight.destination_iata
        if iata not in _DEST_BY_IATA:
            continue
        if iata not in pool_flights or flight.price_usd < pool_flights[iata].price_usd:
            pool_flights[iata] = flight

    if not pool_flights:
        logger.warning("No flights found within pool for origin %s", query.origin_iata)
        return []

    # Sort by flight price, evaluate cheapest destinations first
    sorted_flights = sorted(pool_flights.values(), key=lambda f: f.price_usd)
    candidates = sorted_flights[:_MAX_DESTINATIONS_TO_EVALUATE]

    combo_tasks = [
        _build_combo_for_destination(_DEST_BY_IATA[f.destination_iata], f, query)
        for f in candidates
    ]
    results = await asyncio.gather(*combo_tasks, return_exceptions=True)

    combos = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("Combo build failed: %s", r)
        elif r is not None and r.total_cost <= query.budget_usd:
            combos.append(r)

    return sorted(combos, key=lambda c: c.total_cost)
