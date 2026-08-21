import logging

from fastapi import APIRouter, HTTPException

from ai_analyzer import rank_trips
from models.query import TripQuery
from models.results import TripSuggestion
from orchestrator import find_trips

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/search", response_model=list[TripSuggestion])
async def search_trips(query: TripQuery) -> list[TripSuggestion]:
    """
    Search for complete trip packages within the given budget.

    Returns up to 3 AI-ranked suggestions, each with flight + hotel + car + attractions.
    """
    logger.info(
        "Trip search: origin=%s budget=$%.0f days=%d travelers=%d",
        query.origin_iata,
        query.budget_usd,
        query.duration_days,
        query.travelers,
    )

    try:
        combos = await find_trips(query)
    except Exception:
        logger.exception("Orchestrator failed for origin=%s", query.origin_iata)
        raise HTTPException(status_code=502, detail="Failed to fetch travel data. Please try again.")

    if not combos:
        return []

    try:
        suggestions = await rank_trips(combos, query)
    except Exception:
        logger.exception("AI ranking failed; returning empty list")
        raise HTTPException(status_code=502, detail="AI ranking failed. Please try again.")

    logger.info("Returning %d suggestions for origin=%s", len(suggestions), query.origin_iata)
    return suggestions
