from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "origin_iata": "ATL",
    "budget_usd": 2000,
    "duration_days": 4,
    "travelers": 2,
}


# --- Input validation ---

def test_missing_origin_iata_returns_422():
    resp = client.post("/api/trips/search", json={"budget_usd": 2000, "duration_days": 4})
    assert resp.status_code == 422


def test_missing_budget_returns_422():
    resp = client.post("/api/trips/search", json={"origin_iata": "ATL", "duration_days": 4})
    assert resp.status_code == 422


def test_zero_budget_returns_422():
    resp = client.post("/api/trips/search", json={**VALID_PAYLOAD, "budget_usd": 0})
    assert resp.status_code == 422


def test_duration_out_of_range_returns_422():
    resp = client.post("/api/trips/search", json={**VALID_PAYLOAD, "duration_days": 31})
    assert resp.status_code == 422


def test_too_many_travelers_returns_422():
    resp = client.post("/api/trips/search", json={**VALID_PAYLOAD, "travelers": 11})
    assert resp.status_code == 422


# --- Happy path ---

def test_search_returns_empty_list_when_no_combos_found():
    with (
        patch("routers.trips.find_trips", AsyncMock(return_value=[])),
        patch("routers.trips.rank_trips", AsyncMock(return_value=[])),
    ):
        resp = client.post("/api/trips/search", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == []


def test_search_returns_suggestions_on_success(sample_suggestion):
    with (
        patch("routers.trips.find_trips", AsyncMock(return_value=[MagicMock()])),
        patch("routers.trips.rank_trips", AsyncMock(return_value=[sample_suggestion])),
    ):
        resp = client.post("/api/trips/search", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["destination_iata"] == "LAS"
    assert data[0]["rank"] == 1
    assert "ai_summary" in data[0]
    assert "affiliate_links" in data[0]


def test_search_response_shape_matches_schema(sample_suggestion):
    with (
        patch("routers.trips.find_trips", AsyncMock(return_value=[MagicMock()])),
        patch("routers.trips.rank_trips", AsyncMock(return_value=[sample_suggestion])),
    ):
        resp = client.post("/api/trips/search", json=VALID_PAYLOAD)

    item = resp.json()[0]
    required_fields = {"rank", "destination", "destination_iata", "total_cost",
                       "breakdown", "ai_summary", "highlights", "ranking_reason", "affiliate_links"}
    assert required_fields.issubset(item.keys())


# --- Error handling ---

def test_orchestrator_failure_returns_502():
    with patch("routers.trips.find_trips", AsyncMock(side_effect=RuntimeError("provider down"))):
        resp = client.post("/api/trips/search", json=VALID_PAYLOAD)

    assert resp.status_code == 502
    assert "travel data" in resp.json()["detail"].lower()


def test_ai_ranker_failure_returns_502():
    with (
        patch("routers.trips.find_trips", AsyncMock(return_value=[MagicMock()])),
        patch("routers.trips.rank_trips", AsyncMock(side_effect=RuntimeError("claude down"))),
    ):
        resp = client.post("/api/trips/search", json=VALID_PAYLOAD)

    assert resp.status_code == 502
    assert "ranking" in resp.json()["detail"].lower()


def test_departure_date_field_is_optional():
    with (
        patch("routers.trips.find_trips", AsyncMock(return_value=[])),
        patch("routers.trips.rank_trips", AsyncMock(return_value=[])),
    ):
        resp_without = client.post("/api/trips/search", json=VALID_PAYLOAD)
        resp_with = client.post(
            "/api/trips/search",
            json={**VALID_PAYLOAD, "departure_date": "2025-06-15"},
        )

    assert resp_without.status_code == 200
    assert resp_with.status_code == 200
