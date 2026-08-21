import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from models.query import SearchQuery
from models.results import ProviderCategory
from agents.flights.skyscanner_agent import SkyscannerAgent
from agents.flights.duffel_agent import DuffelAgent
from agents.hotels.expedia_agent import ExpediaAgent
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


# --- DuffelAgent (mocked HTTP) ---

def _duffel_offer(price: str, airline: str = "Delta Air Lines", iata: str = "DL") -> dict:
    return {
        "id": f"off_test_{price}",
        "total_amount": price,
        "total_currency": "USD",
        "owner": {"name": airline, "iata_code": iata},
    }


async def test_duffel_agent_returns_results_for_specific_route(las_query):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"offers": [_duffel_offer("389.50"), _duffel_offer("412.00", "American Airlines", "AA")]}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("agents.flights.duffel_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        results = await DuffelAgent().search(las_query)

    assert len(results) == 2
    assert all(r.category == ProviderCategory.FLIGHT for r in results)
    assert all(r.destination_iata == "LAS" for r in results)
    prices = {r.price_usd for r in results}
    assert 389.50 in prices
    assert 412.00 in prices


async def test_duffel_agent_skips_non_usd_offers(las_query):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {"offers": [
            {**_duffel_offer("389.50"), "total_currency": "EUR"},  # should be skipped
            _duffel_offer("412.00"),                               # USD — kept
        ]}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("agents.flights.duffel_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        results = await DuffelAgent().search(las_query)

    assert len(results) == 1
    assert results[0].price_usd == 412.00


async def test_duffel_agent_returns_empty_on_http_error(las_query):
    import httpx
    mock_req = httpx.Request("POST", "https://api.duffel.com/air/offer_requests")
    mock_err_resp = httpx.Response(503, request=mock_req)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503 Service Unavailable", request=mock_req, response=mock_err_resp
    )

    with patch("agents.flights.duffel_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        results = await DuffelAgent().search(las_query)

    assert results == []


async def test_duffel_agent_returns_empty_on_network_error(las_query):
    import httpx
    mock_req = httpx.Request("POST", "https://api.duffel.com/air/offer_requests")

    with patch("agents.flights.duffel_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused", request=mock_req)
        )
        results = await DuffelAgent().search(las_query)

    assert results == []


async def test_duffel_agent_inspiration_fans_out_to_all_pool_destinations():
    """Inspiration search (destination_iata=None) must query all 15 pool destinations."""
    inspiration_query = SearchQuery(
        origin_iata="ATL",
        destination_iata=None,
        budget_usd=2000,
        duration_days=4,
        travelers=1,
    )

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"offers": [_duffel_offer("300.00")]}}
    mock_resp.raise_for_status = MagicMock()

    with patch("agents.flights.duffel_agent.httpx.AsyncClient") as MockClient:
        mock_post = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__.return_value.post = mock_post
        results = await DuffelAgent().search(inspiration_query)

    # One call per pool destination (15 destinations)
    assert mock_post.call_count == 15
    # Each call returns one offer → 15 results total
    assert len(results) == 15


# --- Stub agents always return [] ---

async def test_skyscanner_stub_returns_empty(las_query):
    assert await SkyscannerAgent().search(las_query) == []


async def test_expedia_stub_returns_empty(las_query):
    assert await ExpediaAgent().search(las_query) == []


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
    # Mock uses ±15% random variation — two independent calls should differ occasionally
    # Just verify prices are in a plausible range rather than asserting exact values
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
    # Enterprise falls back to _DEFAULT_RATES rather than returning empty
    results = await EnterpriseAgent().search(unknown_query)
    assert len(results) == 3  # economy, standard, suv always present


async def test_enterprise_agent_covers_all_car_classes(las_query):
    results = await EnterpriseAgent().search(las_query)
    titles = [r.title for r in results]
    # Should have at least economy and standard tiers
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
    # Reuse unknown_query shape but with a known destination
    from models.query import SearchQuery
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
