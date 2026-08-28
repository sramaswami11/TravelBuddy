"""
Uses Llama 3.3 70B (via Groq) to rank TripCombo objects by value-for-money and
experience quality, returning enriched TripSuggestion objects with AI-generated summaries.
Falls back to cost-sort if the Groq API call fails or no key is configured.
"""
import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from config import settings
from models.query import TripQuery
from models.results import TripCombo, TripSuggestion

logger = logging.getLogger(__name__)

_MODEL = "openai/gpt-oss-120b"
_MAX_SUGGESTIONS = 3



def _format_combo(combo: TripCombo, budget_usd: float) -> str:
    bd = combo.breakdown
    pct = (combo.total_cost / budget_usd) * 100
    attraction_lines = "\n".join(f"    • {a.title} (${a.price_usd:.0f})" for a in combo.attractions)
    car_line = f"${bd['car_rental']:.0f} — {combo.car_rental.title}" if combo.car_rental else "none"
    return (
        f"{combo.destination_name} ({combo.destination_iata})\n"
        f"  Total: ${combo.total_cost:.0f}  ({pct:.0f}% of budget)\n"
        f"  Flight: ${bd['flight']:.0f} — {combo.flight.title}\n"
        f"  Hotel:  ${bd['hotel']:.0f} — {combo.hotel.title}\n"
        f"  Car:    {car_line}\n"
        f"  Attractions: ${bd['attractions']:.0f}\n"
        f"{attraction_lines or '    (none)'}"
    )


async def rank_trips(combos: list[TripCombo], query: TripQuery) -> list[TripSuggestion]:
    """
    Rank trip combos with Llama via Groq and return top 3 enriched TripSuggestions.
    Falls back to cost-sort if the API call fails or no key is configured.
    """
    if not combos:
        return []

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set; using fallback ranking")
        return _fallback_ranking(combos, query)

    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    packages_text = "\n\n".join(_format_combo(c, query.budget_usd) for c in combos)
    n = min(len(combos), _MAX_SUGGESTIONS)

    prompt = (
        f"Analyze these {len(combos)} trip packages for a traveler with:\n"
        f"  Budget: ${query.budget_usd:,.0f}  |  Duration: {query.duration_days} days  "
        f"|  Travelers: {query.travelers}  |  Flying from: {query.origin_iata}\n\n"
        f"{packages_text}\n\n"
        f"Rank the top {n} by value-for-money and overall experience quality. "
        f"Favor packages that use the budget efficiently and offer a strong mix of "
        f"accommodation, transport, and activities.\n\n"
        f"Reply with ONLY a JSON array (no markdown, no explanation) of {n} objects, each with:\n"
        f"  rank (int 1-{n}), destination_iata (string), ai_summary (2-3 sentences),\n"
        f"  highlights (array of 3-5 strings), ranking_reason (one sentence)\n"
        f"Use only plain ASCII punctuation (hyphens, straight quotes). No curly quotes, em dashes, or non-ASCII characters."
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content or ""

        # Model may wrap JSON in prose; find the last "[ {" to locate the rankings array.
        parsed: Any = None
        array_starts = [m.start() for m in re.finditer(r"\[\s*\{", raw)]
        last_start = array_starts[-1] if array_starts else -1
        if last_start != -1:
            depth = end = 0
            for i, ch in enumerate(raw[last_start:], last_start):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end:
                try:
                    parsed = json.loads(raw[last_start : end + 1])
                except json.JSONDecodeError:
                    logger.warning("JSON parse failed on extracted slice; using fallback")

        if isinstance(parsed, dict):
            parsed = parsed.get("rankings", [])

        rankings: list[dict[str, Any]] = [r for r in (parsed or []) if isinstance(r, dict)]
        if not rankings:
            logger.warning("No valid ranking objects in Groq response; using fallback")
            return _fallback_ranking(combos, query)

    except Exception:
        logger.exception("Groq ranking failed; using fallback ranking")
        return _fallback_ranking(combos, query)

    combo_by_iata = {c.destination_iata: c for c in combos}
    suggestions: list[TripSuggestion] = []

    for entry in rankings:
        iata = entry.get("destination_iata", "")
        combo = combo_by_iata.get(iata)
        if not combo:
            logger.warning("Llama returned unknown destination %r — skipping", iata)
            continue

        suggestions.append(
            TripSuggestion(
                rank=entry["rank"],
                destination=combo.destination_name,
                destination_iata=iata,
                total_cost=combo.total_cost,
                breakdown=combo.breakdown,
                ai_summary=entry.get("ai_summary", ""),
                highlights=entry.get("highlights", []),
                ranking_reason=entry.get("ranking_reason", ""),
                affiliate_links={
                    "flight": combo.flight.affiliate_url,
                    "hotel": combo.hotel.affiliate_url,
                    "car_rental": combo.car_rental.affiliate_url if combo.car_rental else None,
                    "attractions": combo.attractions[0].affiliate_url if combo.attractions else None,
                },
                departure_date=combo.flight.details.get("departure_date", ""),
                return_date=combo.flight.details.get("return_date", ""),
            )
        )

    return sorted(suggestions, key=lambda s: s.rank)


def _fallback_ranking(combos: list[TripCombo], query: TripQuery) -> list[TripSuggestion]:
    """Cost-sort fallback when Groq is unavailable."""
    top = sorted(combos, key=lambda c: c.total_cost)[:_MAX_SUGGESTIONS]
    return [
        TripSuggestion(
            rank=i + 1,
            destination=c.destination_name,
            destination_iata=c.destination_iata,
            total_cost=c.total_cost,
            breakdown=c.breakdown,
            ai_summary=(
                f"{c.destination_name} is a solid {query.duration_days}-day trip "
                f"within your ${query.budget_usd:,.0f} budget."
            ),
            highlights=[
                f"Flight: {c.flight.title}",
                f"Hotel: {c.hotel.title}",
                *(f"Activity: {a.title}" for a in c.attractions),
            ],
            ranking_reason="Ranked by total cost — AI analysis unavailable.",
            affiliate_links={
                "flight": c.flight.affiliate_url,
                "hotel": c.hotel.affiliate_url,
                "car_rental": c.car_rental.affiliate_url if c.car_rental else None,
                "attractions": c.attractions[0].affiliate_url if c.attractions else None,
            },
            departure_date=c.flight.details.get("departure_date", ""),
            return_date=c.flight.details.get("return_date", ""),
        )
        for i, c in enumerate(top)
    ]
