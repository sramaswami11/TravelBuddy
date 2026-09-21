from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agents.flights.travelpayouts_agent import (
    TravelpayoutsAgent,
    _aviasales_url,
    _default_dates,
    _depart_month,
    _return_month,
)
from models.query import SearchQuery
from models.results import ProviderCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def inspiration_query():
    return SearchQuery(
        origin_iata="JFK",
        destination_iata=None,
        budget_usd=2000,
        duration_days=7,
        travelers=1,
    )


@pytest.fixture
def route_query():
    return SearchQuery(
        origin_iata="JFK",
        destination_iata="CUN",
        destination_name="Cancun, Mexico",
        budget_usd=2000,
        duration_days=7,
        travelers=1,
        departure_date=date(2026, 11, 15),
    )


@pytest.fixture
def two_traveler_query():
    return SearchQuery(
        origin_iata="ATL",
        destination_iata=None,
        budget_usd=3000,
        duration_days=5,
        travelers=2,
    )


# ---------------------------------------------------------------------------
# _aviasales_url
# ---------------------------------------------------------------------------

def test_aviasales_url_encodes_dates_correctly():
    url = _aviasales_url("JFK", "CUN", "2026-11-15", "2026-11-22", 1)
    # depart 15/11 → 1511, return 22/11 → 2211
    assert "JFK1511CUN22111" in url


def test_aviasales_url_includes_affiliate_marker():
    url = _aviasales_url("JFK", "CUN", "2026-11-15", "2026-11-22", 1)
    assert "marker=" in url


def test_aviasales_url_encodes_traveler_count():
    url = _aviasales_url("ATL", "LAS", "2026-12-01", "2026-12-08", 2)
    assert url.endswith("2?marker=") or "LAS08122" in url


def test_aviasales_url_falls_back_gracefully_on_bad_date():
    url = _aviasales_url("JFK", "CUN", "", "", 1)
    assert "JFKCUN1" in url
    assert "marker=" in url


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_default_dates_uses_departure_date_when_set():
    q = SearchQuery(
        origin_iata="JFK", budget_usd=1000, duration_days=7, travelers=1,
        departure_date=date(2026, 12, 1),
    )
    depart, ret = _default_dates(q)
    assert depart == "2026-12-01"
    assert ret == "2026-12-08"


def test_default_dates_return_is_departure_plus_duration():
    q = SearchQuery(
        origin_iata="JFK", budget_usd=1000, duration_days=10, travelers=1,
        departure_date=date(2026, 6, 1),
    )
    _, ret = _default_dates(q)
    assert ret == "2026-06-11"


def test_depart_month_format():
    q = SearchQuery(
        origin_iata="JFK", budget_usd=1000, duration_days=7, travelers=1,
        departure_date=date(2026, 11, 15),
    )
    assert _depart_month(q) == "2026-11"


def test_return_month_format():
    q = SearchQuery(
        origin_iata="JFK", budget_usd=1000, duration_days=20, travelers=1,
        departure_date=date(2026, 11, 15),
    )
    # 15 Nov + 20 days = 5 Dec
    assert _return_month(q) == "2026-12"


# ---------------------------------------------------------------------------
# _inspiration_search — happy path
# ---------------------------------------------------------------------------

def _mock_inspiration_response(items: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"success": True, "data": items}
    resp.raise_for_status = MagicMock()
    return resp


def _pool_item(dest: str, price: int, depart="2026-11-15", ret="2026-11-22") -> dict:
    return {
        "destination": dest,
        "value": price,
        "depart_date": depart,
        "return_date": ret,
        "gate": "S7 Airlines",
        "number_of_changes": 0,
    }


async def test_inspiration_search_returns_pool_destinations_only(inspiration_query):
    items = [
        _pool_item("LAS", 350),   # in pool
        _pool_item("SFO", 200),   # NOT in pool
        _pool_item("CUN", 420),   # in pool
    ]
    resp = _mock_inspiration_response(items)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    iatas = {r.destination_iata for r in results}
    assert "LAS" in iatas
    assert "CUN" in iatas
    assert "SFO" not in iatas


async def test_inspiration_search_result_shape(inspiration_query):
    items = [_pool_item("LAS", 350)]
    resp = _mock_inspiration_response(items)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert len(results) == 1
    r = results[0]
    assert r.category == ProviderCategory.FLIGHT
    assert r.destination_iata == "LAS"
    assert r.price_usd == 350.0
    assert r.affiliate_url is not None
    assert "marker=" in r.affiliate_url


async def test_inspiration_search_multiplies_price_by_travelers(two_traveler_query):
    items = [_pool_item("LAS", 300)]
    resp = _mock_inspiration_response(items)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(two_traveler_query)

    assert results[0].price_usd == 600.0


async def test_inspiration_search_skips_zero_price_items(inspiration_query):
    items = [_pool_item("LAS", 0), _pool_item("CUN", 400)]
    resp = _mock_inspiration_response(items)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert len(results) == 1
    assert results[0].destination_iata == "CUN"


async def test_inspiration_search_returns_empty_on_api_error_flag(inspiration_query):
    resp = MagicMock()
    resp.json.return_value = {"error": True, "data": []}
    resp.raise_for_status = MagicMock()

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert results == []


async def test_inspiration_search_returns_empty_on_http_error(inspiration_query):
    mock_req = httpx.Request("GET", "https://api.travelpayouts.com/v2/prices/latest")
    mock_err_resp = httpx.Response(503, request=mock_req)
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "503", request=mock_req, response=mock_err_resp
    )

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert results == []


async def test_inspiration_search_returns_empty_on_network_error(inspiration_query):
    mock_req = httpx.Request("GET", "https://api.travelpayouts.com/v2/prices/latest")

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused", request=mock_req)
        )
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert results == []


async def test_inspiration_search_returns_empty_on_empty_data(inspiration_query):
    resp = _mock_inspiration_response([])

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(inspiration_query)

    assert results == []


# ---------------------------------------------------------------------------
# _route_search — happy path
# ---------------------------------------------------------------------------

def _mock_route_response(dest_iata: str, offers: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"success": True, "data": {dest_iata: offers}}
    resp.raise_for_status = MagicMock()
    return resp


async def test_route_search_returns_result_per_transfer_option(route_query):
    offers = {
        "0": {"airline": "AA", "price": 380, "departure_at": "2026-11-15", "return_at": "2026-11-22"},
        "1": {"airline": "UA", "price": 290, "departure_at": "2026-11-15", "return_at": "2026-11-22"},
    }
    resp = _mock_route_response("CUN", offers)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(route_query)

    assert len(results) == 2
    assert all(r.destination_iata == "CUN" for r in results)
    assert all(r.category == ProviderCategory.FLIGHT for r in results)


async def test_route_search_result_has_affiliate_url(route_query):
    offers = {
        "0": {"airline": "AA", "price": 380, "departure_at": "2026-11-15", "return_at": "2026-11-22"},
    }
    resp = _mock_route_response("CUN", offers)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(route_query)

    assert results[0].affiliate_url is not None
    assert "marker=" in results[0].affiliate_url


async def test_route_search_multiplies_price_by_travelers():
    q = SearchQuery(
        origin_iata="JFK", destination_iata="CUN", destination_name="Cancun, Mexico",
        budget_usd=3000, duration_days=7, travelers=2,
        departure_date=date(2026, 11, 15),
    )
    offers = {"0": {"airline": "AA", "price": 300, "departure_at": "2026-11-15", "return_at": "2026-11-22"}}
    resp = _mock_route_response("CUN", offers)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(q)

    assert results[0].price_usd == 600.0


async def test_route_search_skips_zero_price_offers(route_query):
    offers = {
        "0": {"airline": "AA", "price": 0, "departure_at": "2026-11-15", "return_at": "2026-11-22"},
        "1": {"airline": "UA", "price": 290, "departure_at": "2026-11-15", "return_at": "2026-11-22"},
    }
    resp = _mock_route_response("CUN", offers)

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(route_query)

    assert len(results) == 1
    assert results[0].price_usd == 290.0


async def test_route_search_returns_empty_when_success_false(route_query):
    resp = MagicMock()
    resp.json.return_value = {"success": False, "data": {}}
    resp.raise_for_status = MagicMock()

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(route_query)

    assert results == []


async def test_route_search_returns_empty_on_http_error(route_query):
    mock_req = httpx.Request("GET", "https://api.travelpayouts.com/v1/prices/cheap")
    mock_err_resp = httpx.Response(401, request=mock_req)
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized", request=mock_req, response=mock_err_resp
    )

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=resp)
        results = await TravelpayoutsAgent().search(route_query)

    assert results == []


async def test_route_search_returns_empty_on_network_error(route_query):
    mock_req = httpx.Request("GET", "https://api.travelpayouts.com/v1/prices/cheap")

    with patch("agents.flights.travelpayouts_agent.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("timeout", request=mock_req)
        )
        results = await TravelpayoutsAgent().search(route_query)

    assert results == []
