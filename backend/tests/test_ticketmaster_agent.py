from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agents.attractions.ticketmaster_agent import TicketmasterAgent
from models.query import SearchQuery
from models.results import ProviderCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def query():
    return SearchQuery(
        origin_iata="JFK",
        destination_iata="LAS",
        destination_name="Las Vegas, USA",
        budget_usd=2000,
        duration_days=5,
        travelers=1,
        departure_date=date(2026, 11, 15),
    )


@pytest.fixture
def two_traveler_query():
    return SearchQuery(
        origin_iata="JFK",
        destination_iata="LAS",
        destination_name="Las Vegas, USA",
        budget_usd=3000,
        duration_days=5,
        travelers=2,
        departure_date=date(2026, 11, 15),
    )


@pytest.fixture
def event_response():
    return {
        "_embedded": {
            "events": [
                {
                    "name": "Coldplay: Music of the Spheres",
                    "url": "https://www.ticketmaster.com/event/ABC123",
                    "dates": {"start": {"localDate": "2026-11-17"}},
                    "priceRanges": [{"type": "standard", "currency": "USD", "min": 75.0, "max": 200.0}],
                    "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Rock"}}],
                },
                {
                    "name": "Vegas Golden Knights vs Kings",
                    "url": "https://www.ticketmaster.com/event/DEF456",
                    "dates": {"start": {"localDate": "2026-11-18"}},
                    "priceRanges": [{"type": "standard", "currency": "USD", "min": 55.0, "max": 300.0}],
                    "classifications": [{"segment": {"name": "Sports"}, "genre": {"name": "Ice Hockey"}}],
                },
            ]
        }
    }


def _mock_response(payload: dict, status: int = 200):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status
    mock.json.return_value = payload
    mock.raise_for_status = MagicMock()
    if status >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock
        )
    return mock


# ---------------------------------------------------------------------------
# No API key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_api_key_returns_empty(query):
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings:
        mock_settings.ticketmaster_api_key = ""
        results = await TicketmasterAgent().search(query)
    assert results == []


# ---------------------------------------------------------------------------
# Unknown destination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_destination_returns_empty():
    q = SearchQuery(
        origin_iata="JFK",
        destination_iata="XYZ",
        budget_usd=2000,
        duration_days=5,
        travelers=1,
    )
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings:
        mock_settings.ticketmaster_api_key = "testkey"
        results = await TicketmasterAgent().search(q)
    assert results == []


# ---------------------------------------------------------------------------
# Successful response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_events(query, event_response):
    mock_resp = _mock_response(event_response)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(query)

    assert len(results) == 2
    assert all(r.category == ProviderCategory.ATTRACTION for r in results)
    assert all(r.provider == "ticketmaster" for r in results)


@pytest.mark.asyncio
async def test_result_fields(query, event_response):
    mock_resp = _mock_response(event_response)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(query)

    first = results[0]
    assert first.title == "Coldplay: Music of the Spheres"
    assert first.price_usd == 75.0
    assert first.affiliate_url == "https://www.ticketmaster.com/event/ABC123"
    assert first.details["price_per_person"] == 75.0
    assert first.details["date"] == "2026-11-17"
    assert first.details["category"] == "Music · Rock"
    assert first.details["price_estimated"] is False


@pytest.mark.asyncio
async def test_price_multiplied_by_travelers(two_traveler_query, event_response):
    mock_resp = _mock_response(event_response)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(two_traveler_query)

    assert results[0].price_usd == 150.0  # 75 * 2
    assert results[1].price_usd == 110.0  # 55 * 2


# ---------------------------------------------------------------------------
# Events without price ranges are skipped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_events_without_prices_use_default(query):
    payload = {
        "_embedded": {
            "events": [
                {
                    "name": "Metallica: Life Burns Faster",
                    "url": "https://www.ticketmaster.com/event/FREE",
                    "dates": {"start": {"localDate": "2026-11-16"}},
                    "priceRanges": [],
                    "classifications": [],
                },
                {
                    "name": "Paid Show",
                    "url": "https://www.ticketmaster.com/event/PAID",
                    "dates": {"start": {"localDate": "2026-11-17"}},
                    "priceRanges": [{"min": 50.0, "max": 100.0}],
                    "classifications": [],
                },
            ]
        }
    }
    mock_resp = _mock_response(payload)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(query)

    assert len(results) == 2
    no_price_result = results[0]
    assert no_price_result.title == "Metallica: Life Burns Faster"
    assert no_price_result.price_usd == 75.0
    assert no_price_result.details["price_estimated"] is True
    paid_result = results[1]
    assert paid_result.price_usd == 50.0
    assert paid_result.details["price_estimated"] is False


# ---------------------------------------------------------------------------
# Empty response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_events_returns_empty(query):
    mock_resp = _mock_response({})
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(query)

    assert results == []


# ---------------------------------------------------------------------------
# HTTP errors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_http_error_returns_empty(query):
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("connection failed")
        )
        results = await TicketmasterAgent().search(query)

    assert results == []


@pytest.mark.asyncio
async def test_status_error_returns_empty(query):
    mock_resp = _mock_response({}, status=401)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(query)

    assert results == []


# ---------------------------------------------------------------------------
# No departure date uses default
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_departure_date_uses_default(event_response):
    q = SearchQuery(
        origin_iata="JFK",
        destination_iata="LAS",
        budget_usd=2000,
        duration_days=5,
        travelers=1,
    )
    mock_resp = _mock_response(event_response)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        get_mock = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__.return_value.get = get_mock
        results = await TicketmasterAgent().search(q)

    assert len(results) == 2
    call_params = get_mock.call_args.kwargs["params"]
    assert "startDateTime" in call_params
    assert "endDateTime" in call_params


# ---------------------------------------------------------------------------
# destination_name falls back to city name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_destination_name_fallback(event_response):
    q = SearchQuery(
        origin_iata="JFK",
        destination_iata="LAS",
        budget_usd=2000,
        duration_days=5,
        travelers=1,
        departure_date=date(2026, 11, 15),
    )
    mock_resp = _mock_response(event_response)
    with patch("agents.attractions.ticketmaster_agent.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client:
        mock_settings.ticketmaster_api_key = "testkey"
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        results = await TicketmasterAgent().search(q)

    assert results[0].destination_name == "Las Vegas"
