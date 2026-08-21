import pytest
from unittest.mock import AsyncMock, patch

from models.query import TripQuery
from models.results import ProviderCategory, ProviderResult
from orchestrator import _pick_best, _pick_attractions, find_trips


def _result(price: float, iata: str = "LAS", category: ProviderCategory = ProviderCategory.HOTEL) -> ProviderResult:
    return ProviderResult(
        provider="test",
        category=category,
        destination_iata=iata,
        destination_name="Test City",
        title=f"Option ${price:.0f}",
        price_usd=price,
    )


# --- _pick_best ---

def test_pick_best_returns_most_expensive_within_budget():
    options = [_result(100), _result(200), _result(300)]
    assert _pick_best(options, budget=250).price_usd == 200


def test_pick_best_returns_cheapest_when_all_exceed_budget():
    options = [_result(500), _result(300), _result(400)]
    assert _pick_best(options, budget=100).price_usd == 300


def test_pick_best_exact_budget_match():
    options = [_result(200), _result(300)]
    assert _pick_best(options, budget=200).price_usd == 200


def test_pick_best_single_option_within_budget():
    assert _pick_best([_result(150)], budget=200).price_usd == 150


def test_pick_best_returns_none_on_empty_list():
    assert _pick_best([], budget=500) is None


# --- _pick_attractions ---

def test_pick_attractions_stays_within_budget():
    options = [_result(50), _result(80), _result(30), _result(60)]
    picked = _pick_attractions(options, budget=100)
    assert sum(r.price_usd for r in picked) <= 100


def test_pick_attractions_respects_count_limit():
    options = [_result(10), _result(20), _result(30), _result(40)]
    assert len(_pick_attractions(options, budget=500, n=2)) <= 2


def test_pick_attractions_picks_cheapest_first():
    options = [_result(90), _result(30), _result(20)]
    picked = _pick_attractions(options, budget=60, n=2)
    prices = {r.price_usd for r in picked}
    assert 20 in prices
    assert 30 in prices


def test_pick_attractions_returns_empty_when_all_exceed_budget():
    options = [_result(200), _result(300)]
    assert _pick_attractions(options, budget=50) == []


def test_pick_attractions_empty_input():
    assert _pick_attractions([], budget=500) == []


# --- find_trips ---

@pytest.fixture
def base_query():
    return TripQuery(origin_iata="ATL", budget_usd=2000.0, duration_days=4, travelers=2)


def _pool_flight(iata: str, price: float) -> ProviderResult:
    return ProviderResult(
        provider="amadeus",
        category=ProviderCategory.FLIGHT,
        destination_iata=iata,
        destination_name=f"{iata} City",
        title=f"ATL → {iata}",
        price_usd=price,
    )


async def test_find_trips_empty_when_flights_outside_pool(base_query):
    outside_pool = _pool_flight("SFO", 300.0)  # SFO not in our 15-dest pool
    with patch("orchestrator.FlightProviderFactory") as MockFF:
        MockFF.return_value.search_all = AsyncMock(return_value=[outside_pool])
        result = await find_trips(base_query)
    assert result == []


async def test_find_trips_empty_when_no_flights_returned(base_query):
    with patch("orchestrator.FlightProviderFactory") as MockFF:
        MockFF.return_value.search_all = AsyncMock(return_value=[])
        result = await find_trips(base_query)
    assert result == []


async def test_find_trips_returns_combos_sorted_by_cost(
    base_query, sample_hotel, sample_car, sample_attraction
):
    cheap = _pool_flight("SAT", 200.0)   # San Antonio — in pool
    pricier = _pool_flight("LAS", 400.0) # Las Vegas — in pool

    with (
        patch("orchestrator.FlightProviderFactory") as MockFF,
        patch("orchestrator.HotelProviderFactory") as MockHF,
        patch("orchestrator.CarRentalProviderFactory") as MockCRF,
        patch("orchestrator.AttractionProviderFactory") as MockAF,
    ):
        MockFF.return_value.search_all = AsyncMock(return_value=[cheap, pricier])
        MockHF.return_value.search_all = AsyncMock(return_value=[sample_hotel])
        MockCRF.return_value.search_all = AsyncMock(return_value=[sample_car])
        MockAF.return_value.search_all = AsyncMock(return_value=[sample_attraction])

        combos = await find_trips(base_query)

    assert len(combos) == 2
    costs = [c.total_cost for c in combos]
    assert costs == sorted(costs)


async def test_find_trips_excludes_combos_over_budget(base_query, sample_hotel, sample_car):
    # Flight that consumes almost all the budget → hotel pushes it over
    near_limit_flight = _pool_flight("LAS", 1950.0)  # $1950 of $2000 budget

    with (
        patch("orchestrator.FlightProviderFactory") as MockFF,
        patch("orchestrator.HotelProviderFactory") as MockHF,
        patch("orchestrator.CarRentalProviderFactory") as MockCRF,
        patch("orchestrator.AttractionProviderFactory") as MockAF,
    ):
        MockFF.return_value.search_all = AsyncMock(return_value=[near_limit_flight])
        MockHF.return_value.search_all = AsyncMock(return_value=[sample_hotel])  # $600 — over the $50 remaining
        MockCRF.return_value.search_all = AsyncMock(return_value=[sample_car])
        MockAF.return_value.search_all = AsyncMock(return_value=[])

        combos = await find_trips(base_query)

    # Total ($1950 flight + $600 hotel + ...) exceeds $2000 budget → filtered out
    assert combos == []


async def test_find_trips_deduplicates_flights_by_destination(base_query, sample_hotel, sample_car):
    # Two flights to LAS at different prices — only cheapest should be used
    cheap_las = _pool_flight("LAS", 250.0)
    expensive_las = _pool_flight("LAS", 450.0)

    with (
        patch("orchestrator.FlightProviderFactory") as MockFF,
        patch("orchestrator.HotelProviderFactory") as MockHF,
        patch("orchestrator.CarRentalProviderFactory") as MockCRF,
        patch("orchestrator.AttractionProviderFactory") as MockAF,
    ):
        MockFF.return_value.search_all = AsyncMock(return_value=[cheap_las, expensive_las])
        MockHF.return_value.search_all = AsyncMock(return_value=[sample_hotel])
        MockCRF.return_value.search_all = AsyncMock(return_value=[sample_car])
        MockAF.return_value.search_all = AsyncMock(return_value=[])

        combos = await find_trips(base_query)

    las_combos = [c for c in combos if c.destination_iata == "LAS"]
    assert len(las_combos) == 1
    assert las_combos[0].flight.price_usd == 250.0


async def test_find_trips_handles_agent_exceptions_gracefully(base_query):
    good_flight = _pool_flight("LAS", 300.0)

    with (
        patch("orchestrator.FlightProviderFactory") as MockFF,
        patch("orchestrator.HotelProviderFactory") as MockHF,
        patch("orchestrator.CarRentalProviderFactory") as MockCRF,
        patch("orchestrator.AttractionProviderFactory") as MockAF,
    ):
        MockFF.return_value.search_all = AsyncMock(return_value=[good_flight])
        # Hotel factory raises — combo should be skipped, not crash the whole pipeline
        MockHF.return_value.search_all = AsyncMock(side_effect=RuntimeError("hotel API down"))
        MockCRF.return_value.search_all = AsyncMock(return_value=[])
        MockAF.return_value.search_all = AsyncMock(return_value=[])

        # Should not raise
        combos = await find_trips(base_query)

    assert isinstance(combos, list)
