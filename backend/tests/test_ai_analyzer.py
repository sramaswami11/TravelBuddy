import copy
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ai_analyzer import rank_trips, _fallback_ranking
from models.query import TripQuery


@pytest.fixture
def query():
    return TripQuery(origin_iata="ATL", budget_usd=2000.0, duration_days=4, travelers=2)


def _groq_response(rankings: list[dict]) -> MagicMock:
    """Build a mock OpenAI-compatible response containing a JSON rankings array."""
    msg = MagicMock()
    msg.content = json.dumps(rankings)
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


# --- rank_trips ---

async def test_rank_trips_empty_input_returns_empty(query):
    assert await rank_trips([], query) == []


async def test_rank_trips_returns_suggestions_from_groq(query, sample_combo):
    response = _groq_response([
        {
            "rank": 1,
            "destination_iata": "LAS",
            "ai_summary": "Las Vegas delivers spectacular value.",
            "highlights": ["Strip Night Tour", "Bellagio Hotel", "Economy Car"],
            "ranking_reason": "Best value-for-money of the candidates.",
        }
    ])
    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo], query)

    assert len(suggestions) == 1
    s = suggestions[0]
    assert s.rank == 1
    assert s.destination_iata == "LAS"
    assert "Las Vegas" in s.ai_summary
    assert len(s.highlights) == 3
    assert s.affiliate_links["flight"] is not None


async def test_rank_trips_results_sorted_by_rank(query, sample_combo):
    combo2 = copy.deepcopy(sample_combo)
    combo2.destination_iata = "MCO"
    combo2.destination_name = "Orlando, United States"

    response = _groq_response([
        {"rank": 2, "destination_iata": "LAS", "ai_summary": "...", "highlights": [], "ranking_reason": "..."},
        {"rank": 1, "destination_iata": "MCO", "ai_summary": "...", "highlights": [], "ranking_reason": "..."},
    ])
    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo, combo2], query)

    ranks = [s.rank for s in suggestions]
    assert ranks == sorted(ranks)
    assert suggestions[0].destination_iata == "MCO"


async def test_rank_trips_skips_unknown_iata_from_groq(query, sample_combo):
    response = _groq_response([
        {"rank": 1, "destination_iata": "ZZZ", "ai_summary": "...", "highlights": [], "ranking_reason": "..."},
    ])
    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo], query)

    assert suggestions == []


async def test_rank_trips_falls_back_when_response_has_no_json(query, sample_combo):
    msg = MagicMock()
    msg.content = "I cannot rank these trips at this time."
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]

    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo], query)

    assert len(suggestions) == 1
    assert "AI analysis unavailable" in suggestions[0].ranking_reason


async def test_rank_trips_falls_back_on_api_exception(query, sample_combo):
    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(side_effect=Exception("network error"))
        suggestions = await rank_trips([sample_combo], query)

    assert len(suggestions) == 1
    assert "AI analysis unavailable" in suggestions[0].ranking_reason


async def test_rank_trips_affiliate_links_populated(query, sample_combo):
    response = _groq_response([
        {"rank": 1, "destination_iata": "LAS", "ai_summary": "...", "highlights": [], "ranking_reason": "..."},
    ])
    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo], query)

    links = suggestions[0].affiliate_links
    assert links["flight"] == "https://amadeus.example.com/flight/LAS"
    assert links["hotel"] == "https://booking.example.com/hotel/LAS"
    assert links["car_rental"] == "https://enterprise.example.com/car/LAS"
    assert links["attractions"] == "https://www.viator.com/search/LAS"


async def test_rank_trips_extracts_json_embedded_in_prose(query, sample_combo):
    """The bracket-match parser should find the JSON array even when the model wraps it in prose."""
    rankings = [{"rank": 1, "destination_iata": "LAS", "ai_summary": "Great pick.", "highlights": [], "ranking_reason": "Best value."}]
    prose_wrapped = f"Here are the rankings:\n\n{json.dumps(rankings)}\n\nI hope this helps!"
    msg = MagicMock()
    msg.content = prose_wrapped
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]

    with patch("ai_analyzer.AsyncOpenAI") as MockClient:
        MockClient.return_value.chat.completions.create = AsyncMock(return_value=response)
        suggestions = await rank_trips([sample_combo], query)

    assert len(suggestions) == 1
    assert suggestions[0].destination_iata == "LAS"


# --- _fallback_ranking ---

def test_fallback_returns_max_three(query, sample_combo):
    combos = []
    for i, iata in enumerate(["LAS", "MCO", "MIA", "BNA", "MSY"]):
        c = copy.deepcopy(sample_combo)
        c.destination_iata = iata
        c.total_cost = 800 + i * 100
        combos.append(c)

    results = _fallback_ranking(combos, query)
    assert len(results) == 3


def test_fallback_sorted_by_cost(query, sample_combo):
    cheap = copy.deepcopy(sample_combo)
    cheap.destination_iata = "SAT"
    cheap.total_cost = 900.0

    pricier = copy.deepcopy(sample_combo)
    pricier.destination_iata = "LAS"
    pricier.total_cost = 1278.0

    results = _fallback_ranking([pricier, cheap], query)
    assert results[0].total_cost < results[1].total_cost


def test_fallback_assigns_sequential_ranks(query, sample_combo):
    results = _fallback_ranking([sample_combo], query)
    assert results[0].rank == 1


def test_fallback_highlights_include_flight_and_hotel(query, sample_combo):
    results = _fallback_ranking([sample_combo], query)
    highlights = results[0].highlights
    assert any("Flight" in h for h in highlights)
    assert any("Hotel" in h for h in highlights)
