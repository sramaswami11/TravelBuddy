# packedNbooked — Implementation Guide (Living Document)

> **Status:** Live in production  
> **Last updated:** 2026-08-25  
> **Companion doc:** `Architecture.md` (high-level design)

---

## What This Doc Is

A bottom-up walkthrough of every layer of the system — written so a developer can clone the repo, read this document, and understand not just *what* the code does but *why* it's structured the way it is.

---

## Table of Contents

1. [How a Request Flows Through the System](#1-how-a-request-flows-through-the-system)
2. [Project Structure](#2-project-structure)
3. [Data Models](#3-data-models)
4. [The Abstract Factory Pattern](#4-the-abstract-factory-pattern)
5. [Provider Agents](#5-provider-agents)
6. [The Orchestrator](#6-the-orchestrator)
7. [The AI Analyzer](#7-the-ai-analyzer)
8. [FastAPI Layer](#8-fastapi-layer)
9. [Configuration](#9-configuration)
10. [Frontend](#10-frontend)
11. [Test Suite](#11-test-suite)
12. [Running Locally](#12-running-locally)
13. [Extending the System](#13-extending-the-system)

---

## 1. How a Request Flows Through the System

A user submits: "I have $2,000, 7 days, 1 person, leaving from JFK." Here is exactly what happens:

```
POST /api/trips/search
    │
    ▼
routers/trips.py          — validates the request body into a TripQuery object
    │
    ▼
orchestrator.find_trips() — TWO-PHASE async fan-out (see §6 for detail)
    │
    │  Phase 1: DuffelAgent fans out concurrently to all 15 pool destinations.
    │           Returns the cheapest round-trip offer per destination.
    │           Filter to pool + keep the 5 cheapest within budget.
    │
    │  Phase 2: For each of those 5 destinations, concurrently fan out to:
    │           ├── HotelProviderFactory  → BookingAgent (mock)
    │           ├── CarRentalFactory      → EnterpriseAgent (mock)
    │           └── AttractionFactory    → ViatorAgent (mock) + TicketmasterAgent (stub)
    │
    │  Allocate remaining budget across hotel/car/activities.
    │  Assemble one TripCombo per destination.
    │  Drop any combo whose total_cost exceeds the budget.
    │  Return list[TripCombo] sorted by total cost.
    │
    ▼
ai_analyzer.rank_trips()  — sends all combos to Groq (openai/gpt-oss-120b) in one call.
    │                        Prompt asks for a JSON array: rank + ai_summary +
    │                        highlights + ranking_reason per destination.
    │                        Falls back to cost-sort if Groq fails.
    │
    ▼
list[TripSuggestion]       — returned as JSON to the browser
```

Total wall-clock time: Duffel fan-out (~2–4s across 15 destinations) + Groq call (~1–2s). The hotel/car/attraction fan-out in Phase 2 is all mock so it adds negligible time.

---

## 2. Project Structure

```
packedNbooked/
├── Architecture.md
├── Implementation.md
│
├── backend/
│   ├── main.py              # FastAPI app entry point + CORS
│   ├── config.py            # Pydantic Settings — reads .env
│   ├── orchestrator.py      # Two-phase async pipeline
│   ├── ai_analyzer.py       # Groq ranking + fallback
│   ├── requirements.txt
│   │
│   ├── routers/
│   │   └── trips.py         # POST /api/trips/search
│   │
│   ├── models/
│   │   ├── query.py         # TripQuery + SearchQuery
│   │   └── results.py       # ProviderResult, TripCombo, TripSuggestion
│   │
│   ├── factories/
│   │   ├── base.py          # TravelAgent + TravelProviderFactory ABCs
│   │   ├── flight_factory.py
│   │   ├── hotel_factory.py
│   │   ├── car_rental_factory.py
│   │   └── attraction_factory.py
│   │
│   ├── agents/
│   │   ├── flights/
│   │   │   ├── duffel_agent.py       # LIVE — Duffel sandbox
│   │   │   └── skyscanner_agent.py   # STUB — returns []
│   │   ├── hotels/
│   │   │   └── booking_agent.py      # MOCK
│   │   ├── car_rental/
│   │   │   └── enterprise_agent.py   # MOCK
│   │   └── attractions/
│   │       ├── viator_agent.py       # MOCK
│   │       └── ticketmaster_agent.py # STUB — returns []
│   │
│   ├── data/
│   │   └── destinations.json         # 15 pool destinations
│   │
│   └── tests/                        # 88 tests, all passing
│
└── frontend/
    └── src/
        ├── App.tsx
        ├── api.ts
        ├── data/airports.ts           # ~250 worldwide airports
        └── components/
            ├── AirportInput.tsx
            ├── SearchForm.tsx
            └── TripCard.tsx
```

**Import style:** All imports inside `backend/` are flat — `from models.results import TripCombo`. This works because uvicorn runs from the `backend/` directory. Tests use `pythonpath = ["backend"]` in `pyproject.toml` for the same reason.

---

## 3. Data Models

All models live in `backend/models/`. They're Pydantic v2 classes — validate on construction, serialize to/from JSON automatically.

### `query.py`

**`TripQuery`** — the raw user-facing input validated by FastAPI:

```python
class TripQuery(BaseModel):
    origin_iata: str              # e.g. "JFK"
    budget_usd: float             # must be > 0
    duration_days: int            # 1–30
    travelers: int                # 1–10, default 1
    departure_date: Optional[date]  # None = default to 30 days from today
```

**`SearchQuery`** — internal object created by the orchestrator and passed to every factory/agent. Adds destination info:

```python
class SearchQuery(BaseModel):
    origin_iata: str
    destination_iata: Optional[str]   # None = inspiration mode
    destination_name: Optional[str]
    budget_usd: float
    duration_days: int
    travelers: int
    departure_date: Optional[date]
```

`destination_iata = None` signals an *inspiration search* — "find me the cheapest destinations." When set, the agent searches a specific route.

### `results.py`

**`ProviderResult`** — the atomic unit returned by any agent:

```python
class ProviderResult(BaseModel):
    provider: str                  # "duffel", "booking", "viator", etc.
    category: ProviderCategory     # FLIGHT, HOTEL, CAR_RENTAL, or ATTRACTION
    destination_iata: str
    destination_name: str
    title: str                     # "United Airlines round-trip JFK → LAS"
    price_usd: float
    details: dict                  # provider-specific extras
    affiliate_url: Optional[str]   # the revenue link
```

**`TripCombo`** — one assembled trip package (flight + hotel + optional car + up to 2 attractions):

```python
class TripCombo(BaseModel):
    destination_iata: str
    destination_name: str
    flight: ProviderResult
    hotel: ProviderResult
    car_rental: Optional[ProviderResult]
    attractions: list[ProviderResult]
    total_cost: float

    @property
    def breakdown(self) -> dict[str, float]:
        # {"flight": 400.0, "hotel": 600.0, "car_rental": 180.0, "attractions": 98.0}
```

**`TripSuggestion`** — a `TripCombo` enriched by AI with rank, summary, and flattened affiliate links. This is what the frontend receives.

The pipeline maps cleanly: **agents → `ProviderResult`** | **orchestrator → `TripCombo`** | **AI analyzer → `TripSuggestion`**

---

## 4. The Abstract Factory Pattern

`backend/factories/base.py` defines two abstract base classes every factory and agent must implement.

### Why this pattern?

Each travel provider has a completely different API. Duffel uses Bearer token auth + a custom `Duffel-Version` header. Booking.com uses an affiliate token. Viator has its own partner SDK. The orchestrator doesn't care — it just calls `search(query)` and gets back `list[ProviderResult]`.

Adding a new hotel provider (say, Hotels.com) means writing one `HotelsComAgent` class and adding it to `HotelProviderFactory.get_agents()`. Nothing else changes.

### The two abstract classes

```python
class TravelAgent(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[ProviderResult]: ...


class TravelProviderFactory(ABC):
    @abstractmethod
    def get_agents(self) -> list[TravelAgent]: ...

    async def search_all(self, query: SearchQuery) -> list[ProviderResult]:
        tasks = [agent.search(query) for agent in self.get_agents()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # collects results, logs failures, skips failed agents
```

`search_all()` uses `asyncio.gather` with `return_exceptions=True` — if one agent crashes (timeout, rate limit), the others are unaffected.

---

## 5. Provider Agents

| Tier | Agents | Behavior |
|------|--------|----------|
| Live | `DuffelAgent` | Real API calls to api.duffel.com (sandbox key) |
| Mock | `BookingAgent`, `EnterpriseAgent`, `ViatorAgent` | Hardcoded realistic data with random price variation |
| Stub | `SkyscannerAgent`, `TicketmasterAgent` | Always return `[]` — slots reserved for future |

### DuffelAgent (live)

Two modes depending on `query.destination_iata`:

**Inspiration mode** (`destination_iata = None`):  
Fans out concurrently to all 15 pool destinations via `asyncio.gather`, making one `POST /air/offer_requests` per destination with `return_offers: true`. Returns the cheapest offer per route. This is Phase 1.

**Route mode** (`destination_iata` is set):  
Searches a single route. Used if the orchestrator ever needs to price a specific flight independently of Phase 1.

**Affiliate links:**  
Every `ProviderResult` from Duffel gets a Skyscanner deep link via `_skyscanner_url()`. The link encodes origin, destination, dates, and traveler count. Add `&partner_id=YOUR_ID` once enrolled in the Skyscanner affiliate program.

**Date defaulting:**  
`_default_dates()` returns departure 30 days from today if `query.departure_date` is None. This is a UX choice — results are shown to users without them needing to specify dates.

### BookingAgent (mock)

`_HOTEL_TEMPLATES` contains 4 real hotel options per destination (actual names, star ratings, realistic base rates). Each search applies ±15% random variation:

```python
price = base_rate * query.duration_days * random.uniform(0.85, 1.15)
```

Returns empty list for destinations not in the template — realistic behavior since not every provider covers every market.

### ViatorAgent (mock)

`_ATTRACTIONS` dict keyed by IATA: 4 attractions per destination, per-person pricing multiplied by `query.travelers`:

```python
price = attraction["price_per_person"] * query.travelers * random.uniform(0.95, 1.05)
```

### EnterpriseAgent (mock)

Has a `_DEFAULT_RATES` fallback so it returns results for any destination. Car rental is a commodity — Enterprise operates everywhere, so returning default rates is more realistic than returning empty.

---

## 6. The Orchestrator

`backend/orchestrator.py` is the heart of the system. It solves a combinatorial problem: how to search N destinations across M provider categories without making N×M API calls.

### The two-phase approach

**Phase 1 — Inspiration search (15 concurrent Duffel calls, appears as 1 logical step):**  
`DuffelAgent.search(query_with_no_destination)` fans out to all 15 pool destinations concurrently. Returns cheapest offer per destination. Filter to those within 40% of budget (the flight allocation ratio) and take the top 5 cheapest.

**Phase 2 — Deep evaluation (fan-out across 5 destinations):**  
For each of the 5 shortlisted destinations, concurrently build a full combo:

```python
combo_tasks = [
    _build_combo_for_destination(dest, flight, query)
    for dest, flight in candidates
]
results = await asyncio.gather(*combo_tasks, return_exceptions=True)
```

Each `_build_combo_for_destination` itself fans out to hotel/car/attraction factories concurrently. Total: 5 × 3 category calls = 15, all concurrent.

### Budget allocation

Fixed ratios divide the total budget:

```python
_FLIGHT_BUDGET_RATIO     = 0.40
_HOTEL_BUDGET_RATIO      = 0.35
_CAR_BUDGET_RATIO        = 0.12
_ATTRACTION_BUDGET_RATIO = 0.13
```

Once the actual flight price is known, the remaining budget is redistributed proportionally among hotel/car/activities:

```python
remaining = query.budget_usd - flight.price_usd
hotel_budget = remaining * (_HOTEL_BUDGET_RATIO / (1 - _FLIGHT_BUDGET_RATIO))
```

This recalculates ratios on the non-flight portion, so cheap flights don't leave hotel/activities with an undersized budget.

### Picking the best option

`_pick_best()` selects the best result within budget:

```python
def _pick_best(results, budget):
    within = [r for r in results if r.price_usd <= budget]
    if within:
        return max(within, key=lambda r: r.price_usd)   # most expensive within budget
    return min(results, key=lambda r: r.price_usd)       # cheapest if all over budget
```

"Most expensive within budget" is intentional — given a $700 hotel budget, a $650 option is more compelling than a $200 one, giving the AI better material to rank.

---

## 7. The AI Analyzer

`backend/ai_analyzer.py` takes a `list[TripCombo]` and returns `list[TripSuggestion]` with AI-generated rankings and summaries.

### Why not just rank by cost?

The orchestrator already sorts by cost. Cheapest isn't always best. A $1,100 trip to Nashville with a honky-tonk crawl and distillery tour might be a better *experience* than a $950 trip with nothing included. The AI reasons about activity quality, destination appeal, and the overall package.

### Approach: plain JSON prompt

Unlike the original design (which used Claude tool-calling), the Groq implementation uses a direct JSON prompt — simpler and faster:

```python
prompt = (
    f"Rank the top {n} by value-for-money and overall experience quality.\n\n"
    f"Reply with ONLY a JSON array (no markdown, no explanation) of {n} objects, each with:\n"
    f"  rank (int), destination_iata (string), ai_summary (2-3 sentences),\n"
    f"  highlights (array of 3-5 strings), ranking_reason (one sentence)"
)
```

The response parser uses bracket-matching to locate and extract the JSON array from the raw response text — handles cases where the model wraps output in prose. If parsing fails, falls back to `_fallback_ranking`.

### Model

`openai/gpt-oss-120b` — accessed via the Groq inference endpoint using the `openai` Python SDK pointed at `https://api.groq.com/openai/v1`. The openai SDK is used (not a Groq-specific SDK) because Groq's API is OpenAI-compatible.

Qwen 3.6 27B was tried and abandoned — it wraps output in unclosed `<think>` blocks that break the JSON parser.

### Graceful fallback

If the Groq call fails (network error, API outage, malformed response), `_fallback_ranking()` sorts by cost and generates a template summary. Users still get results — never a 500 error.

---

## 8. FastAPI Layer

### `main.py`

Three responsibilities:
1. **Logging** — structured format with timestamps, applied once at startup.
2. **CORS** — configured via `FRONTEND_URL` env var. Allows the Render frontend URL and `localhost:5173` for local dev.
3. **Router mounting** — `app.include_router(trips.router, prefix="/api")`.

### `routers/trips.py`

One endpoint: `POST /api/trips/search` → `list[TripSuggestion]`.

FastAPI + Pydantic handles all input validation automatically. Invalid `budget_usd`, out-of-range `duration_days`, or missing required fields all return `422 Unprocessable Entity` with field-level details — no custom validation code needed.

The endpoint returns `200 []` (not 4xx) when no combos fit the budget — it's a valid result.

### Interactive API docs

Swagger UI at `http://localhost:8000/docs` — test the endpoint directly without needing the frontend.

---

## 9. Configuration

`backend/config.py` uses Pydantic Settings:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    duffel_api_key: str = ""
    groq_api_key: str = ""
    ticketmaster_api_key: str = ""
    frontend_url: str = "http://localhost:5173"
```

**All fields default to empty strings** — the app starts without crashing even if no `.env` exists. Duffel calls will fail and return empty results; Groq will fall back to cost-sort. The full pipeline still runs with mock data.

### Required env vars (backend)

| Variable | Where to get it | Effect if missing |
|---|---|---|
| `DUFFEL_API_KEY` | duffel.com dashboard | All flight results empty; orchestrator returns [] |
| `GROQ_API_KEY` | console.groq.com | Falls back to cost-sort ranking |
| `FRONTEND_URL` | Your deployed frontend URL | CORS blocks browser requests |
| `TICKETMASTER_API_KEY` | developer.ticketmaster.com | Ticketmaster stub returns [] (already the case) |

### Frontend env vars

| Variable | Where set | Notes |
|---|---|---|
| `VITE_API_URL` | Render Static Site env vars | Build-time — must redeploy frontend after changing |

---

## 10. Frontend

The frontend is a single-page React app built with Vite + TypeScript + Tailwind CSS. No routing library (single page), no state management library (local `useState`), no UI component library (custom Tailwind components).

### Components

**`App.tsx`** — root component. Owns search state (loading, error, results). Renders the hero section, `SearchForm`, results grid, and footer.

**`SearchForm.tsx`** — the search form. Fields: flying from (airport autocomplete), budget, days, travelers, departure date (optional). Validates that an airport has been selected before enabling submit. Shows a visible error if budget is below $500.

**`AirportInput.tsx`** — combobox autocomplete for the flying-from field. Searches `airports.ts` client-side as the user types (≥2 chars). Filters on city name, IATA code, airport name, or country. Supports keyboard navigation (↑↓ arrows, Enter to select, Escape to close). Displays `{city} ({IATA})` after selection; sends only the IATA code to the parent.

**`TripCard.tsx`** — result card for one `TripSuggestion`. Shows rank badge (gold/silver/bronze), destination name, AI summary, cost breakdown, highlights, and booking links. Includes an amber disclaimer strip noting that flight prices are from sandbox data and may differ from real fares.

### `api.ts`

Thin fetch wrapper. `VITE_API_URL` (set at build time) determines the backend URL; falls back to `http://localhost:8000` for local dev. No retries or caching — every search is a fresh request.

### `data/airports.ts`

~250 major commercial airports worldwide, covering US, Canada, Mexico, Caribbean, Central/South America, Europe, Middle East, Africa, South/Southeast/East Asia, and Oceania. Static TypeScript array — no API needed. Can be extended by adding entries to the array.

---

## 11. Test Suite

All tests in `backend/tests/`. Run from the project root.

**88 tests, all passing.** Run time: < 5 seconds (all network calls mocked).

### Test philosophy

- No real API calls — all network calls mocked. Tests run offline.
- Test behavior, not implementation — if internals change but outputs stay the same, tests pass.
- Each test proves one thing.

### Test files

| File | What it covers |
|------|---------------|
| `test_models.py` | Pydantic validation: zero budget, out-of-range values, boundary conditions, `TripCombo.breakdown` property |
| `test_agents.py` | Stub agents return `[]`; mock agents return correct shapes; price scaling by traveler count; all 15 destinations covered by ViatorAgent |
| `test_orchestrator.py` | `_pick_best` unit tests; `find_trips` with AsyncMock factories; no-results, over-budget, duplicate IATA, and agent-exception scenarios |
| `test_ai_analyzer.py` | Groq happy path; malformed response fallback; API exception fallback; `_fallback_ranking` sort order |
| `test_router.py` | HTTP 422 on invalid input; response shape; 502 when orchestrator or analyzer raises |

---

## 12. Running Locally

```powershell
# Backend
cd backend
pip install -r requirements.txt
# Create backend/.env with DUFFEL_API_KEY and GROQ_API_KEY
uvicorn main:app --reload
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# App: http://localhost:5173

# Tests (from project root)
python -m pytest backend/tests/ -v
```

Sample request body:
```json
{
  "origin_iata": "JFK",
  "budget_usd": 2000,
  "duration_days": 7,
  "travelers": 1
}
```

---

## 13. Extending the System

### Adding a new flight/hotel/car/attraction provider

1. Create `backend/agents/{category}/{provider}_agent.py`
2. Implement `TravelAgent` — `provider_name` property + `async search()` method returning `list[ProviderResult]`
3. Register it in the matching factory's `get_agents()` list
4. Add tests in `test_agents.py`

The orchestrator, AI analyzer, and router are untouched.

### Adding a new destination

1. Add an entry to `backend/data/destinations.json`
2. Add mock data for the new IATA in `booking_agent.py`, `enterprise_agent.py`, `viator_agent.py`
3. Restart the backend — picked up automatically

### Replacing a mock agent with a real API

Swap `_mock_search()` for `_real_search()` in the agent file. Keep the mock function commented out until the real API is stable in production. Factory registration, orchestrator, and tests are unaffected.

---

## Open Items

| Item | Status |
|------|--------|
| Duffel production key | Apply at duffel.com — live URL now available |
| Booking.com affiliate ID | Apply at affiliate.booking.com |
| Skyscanner partner ID | Apply at partners.skyscanner.net |
| Viator partner approval | Apply at viator.com/partner |
| Ticketmaster API key | Apply at developer.ticketmaster.com |
| Privacy Policy page | Required before affiliate applications |
| Terms of Use page | Required before affiliate applications |
| Favicon | Brand polish |
| Redis caching | Hotel/attraction prices stable for 30 min — cache to reduce mock variability and future API costs |
| User accounts + saved trips | Phase 3 |

---

*This document is updated alongside the code. When new features land, update the relevant section.*
