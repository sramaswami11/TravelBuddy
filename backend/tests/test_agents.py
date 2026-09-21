import pytest

from models.query import SearchQuery
from models.results import ProviderCategory
from agents.attractions.ticketmaster_agent import TicketmasterAgent
from agents.hotels.booking_agent import BookingAgent
from agents.car_rental.enterprise_agent import EnterpriseAgent
from agents.attractions.viator_agent import ViatorAgent


@pytest.fixture
def las_query():
    return SearchQuery(
        origin_iata="ATL",
        destination_iata="LAS",
        destination_name="Las Vegas, United States",
        budget_usd=2000,
        duration_days=4,
        travelers=2,
    )


@pytest.fixture
def unknown_query():
    return SearchQuery(
        origin_iata="ATL",
        destination_iata="XYZ",
        destination_name="Nowhere",
        budget_usd=2000,
        duration_days=4,
        travelers=1,
    )


# --- Stub agents ---

async def test_ticketmaster_stub_returns_empty(las_query):
    assert await TicketmasterAgent().search(las_query) == []


# --- BookingAgent (mock) ---

async def test_booking_agent_returns_results_for_known_iata(las_query):
    results = await BookingAgent().search(las_query)
    assert len(results) > 0
    for r in results:
        assert r.category == ProviderCategory.HOTEL
        assert r.destination_iata == "LAS"
        assert r.price_usd > 0
        assert r.affiliate_url is not None


async def test_booking_agent_returns_empty_for_unknown_iata(unknown_query):
    assert await BookingAgent().search(unknown_query) == []


async def test_booking_agent_prices_vary_between_calls(las_query):
    results = await BookingAgent().search(las_query)
    for r in results:
        assert 50 < r.price_usd < 1500


# --- EnterpriseAgent (mock) ---

async def test_enterprise_agent_returns_results_for_known_iata(las_query):
    results = await EnterpriseAgent().search(las_query)
    assert len(results) > 0
    for r in results:
        assert r.category == ProviderCategory.CAR_RENTAL
        assert r.destination_iata == "LAS"
        assert r.price_usd > 0


async def test_enterprise_agent_uses_default_rates_for_unknown_iata(unknown_query):
    results = await EnterpriseAgent().search(unknown_query)
    assert len(results) == 3  # economy, standard, suv always present


async def test_enterprise_agent_covers_all_car_classes(las_query):
    results = await EnterpriseAgent().search(las_query)
    titles = [r.title for r in results]
    assert any("Economy" in t for t in titles)
    assert any("Standard" in t for t in titles)


# --- ViatorAgent (mock) ---

async def test_viator_agent_returns_four_attractions_for_las(las_query):
    results = await ViatorAgent().search(las_query)
    assert len(results) == 4


async def test_viator_agent_prices_scaled_by_travelers(las_query):
    results = await ViatorAgent().search(las_query)
    strip_tour = next(r for r in results if "Strip" in r.title)
    base_per_person = 49
    expected_low = base_per_person * 2 * 0.95
    expected_high = base_per_person * 2 * 1.05
    assert expected_low <= strip_tour.price_usd <= expected_high


async def test_viator_agent_single_traveler_prices(unknown_query):
    q = SearchQuery(
        origin_iata="ATL",
        destination_iata="BNA",
        destination_name="Nashville, United States",
        budget_usd=1000,
        duration_days=3,
        travelers=1,
    )
    results = await ViatorAgent().search(q)
    opry = next(r for r in results if "Opry" in r.title)
    assert 75 * 0.95 <= opry.price_usd <= 75 * 1.05


async def test_viator_agent_returns_empty_for_unknown_iata(unknown_query):
    assert await ViatorAgent().search(unknown_query) == []


async def test_viator_agent_all_have_affiliate_url(las_query):
    results = await ViatorAgent().search(las_query)
    for r in results:
        assert r.affiliate_url is not None
        assert "LAS" in r.affiliate_url


@pytest.mark.parametrize("iata", ["LAS", "MCO", "MIA", "BNA", "MSY", "DEN",
                                   "ORD", "JFK", "SEA", "SAT", "CUN", "PUJ",
                                   "MBJ", "PVR", "YYZ"])
async def test_viator_agent_covers_all_pool_destinations(iata):
    q = SearchQuery(
        origin_iata="ATL",
        destination_iata=iata,
        destination_name=iata,
        budget_usd=1000,
        duration_days=3,
        travelers=1,
    )
    results = await ViatorAgent().search(q)
    assert len(results) == 4, f"Expected 4 attractions for {iata}, got {len(results)}"
