# TravelBuddy — Implementation Guide (Living Document)

> **Status:** In Progress — backend complete, frontend pending  
> **Last updated:** 2026-08-19  
> **Companion docs:** `Architecture.md` (high-level design), this file (code walkthrough)

---

## What This Doc Is

A bottom-up walkthrough of every layer of the backend, written so a developer can clone the repo, read this document, and understand not just *what* the code does but *why* it's structured the way it is. Updated alongside the code as new layers are built.

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
10. [Test Suite](#10-test-suite)
11. [Running Locally](#11-running-locally)
12. [Extending the System](#12-extending-the-system)

---

## 1. How a Request Flows Through the System

A user submits: "I have $2,000, 4 days, 2 people, leaving from Atlanta." Here is exactly what happens:

```
POST /api/trips/search
    │
    ▼
routers/trips.py          — validates the request body into a TripQuery object
    │
    ▼
orchestrator.find_trips() — TWO-PHASE async fan-out (see §6 for detail)
    │
    │  Phase 1: Ask Amadeus "what are the cheapest destinations from ATL?"
    │           Filter results to our 15-destination pool.
    │           Keep the 5 cheapest.
    │
    │  Phase 2: For each of those 5 destinations, concurrently fan out to:
    │           ├── HotelProviderFactory  → BookingAgent (mock)
    │           ├── CarRentalFactory      → EnterpriseAgent (mock)
    │           └── AttractionFactory     → ViatorAgent (mock) + TicketmasterAgent (stub)
    │
    │  Assemble one TripCombo per destination.
    │  Drop any combo whose total_cost exceeds the budget.
    │  Return list[TripCombo] sorted by total cost.
    │
    ▼
ai_analyzer.rank_trips()  — sends all combos to Claude in ONE call
    │                        Claude must call the submit_rankings tool,
    │                        returning rank + ai_summary + highlights + ranking_reason
    │                        for each of the top 3.
    │
    ▼
list[TripSuggestion]       — returned as JSON to the browser
```

Total wall-clock time is dominated by the Amadeus API call in Phase 1 (~1-2s) plus the Claude call (~2-4s). The hotel/car/attraction fan-out in Phase 2 runs concurrently so its latency is the slowest single provider, not the sum of all.

---

## 2. Project Structure

```
TravelBuddy/
├── Architecture.md          # High-level design decisions
├── Implementation.md        # This file — code walkthrough
├── pyproject.toml           # pytest configuration
├── requirements.txt         # Python dependencies
├── .env.example             # Copy to backend/.env and fill in keys
│
└── backend/
    ├── main.py              # FastAPI app + CORS middleware
    ├── config.py            # Pydantic Settings — reads from .env
    ├── orchestrator.py      # The two-phase async pipeline
    ├── ai_analyzer.py       # Claude API integration
    │
    ├── routers/
    │   └── trips.py         # POST /api/trips/search
    │
    ├── models/
    │   ├── query.py         # TripQuery (user input) + SearchQuery (internal)
    │   └── results.py       # ProviderResult, TripCombo, TripSuggestion
    │
    ├── factories/
    │   ├── base.py          # TravelAgent + TravelProviderFactory ABCs
    │   ├── flight_factory.py
    │   ├── hotel_factory.py
    │   ├── car_rental_factory.py
    │   └── attraction_factory.py
    │
    ├── agents/
    │   ├── flights/
    │   │   ├── amadeus_agent.py      # REAL — calls Amadeus REST API
    │   │   └── skyscanner_agent.py   # STUB — returns [] until partner approved
    │   ├── hotels/
    │   │   ├── booking_agent.py      # MOCK — realistic data, no real API
    │   │   └── expedia_agent.py      # STUB
    │   ├── car_rental/
    │   │   └── enterprise_agent.py   # MOCK
    │   └── attractions/
    │       ├── viator_agent.py       # MOCK
    │       └── ticketmaster_agent.py # STUB
    │
    ├── data/
    │   └── destinations.json         # 15 curated destinations with metadata
    │
    └── tests/
        ├── conftest.py               # Shared pytest fixtures
        ├── test_models.py
        ├── test_agents.py
        ├── test_orchestrator.py
        ├── test_ai_analyzer.py
        └── test_router.py
```

**Import style:** All imports inside `backend/` are flat — `from models.results import TripCombo`, never `from backend.models.results import TripCombo`. This is because uvicorn runs from the `backend/` directory, which is on `sys.path`. The same rule applies in tests via `pythonpath = ["backend"]` in `pyproject.toml`.

---

## 3. Data Models

All models live in `backend/models/`. They're Pydantic v2 classes, which means they validate on construction and serialize to/from JSON automatically.

### `query.py`

Two models travel through the system:

**`TripQuery`** — the raw user-facing input. This is what the frontend sends and what FastAPI validates against.

```python
class TripQuery(BaseModel):
    origin_iata: str          # e.g. "ATL"
    budget_usd: float         # must be > 0
    duration_days: int        # 1–30
    travelers: int            # 1–10, default 1
    departure_date: Optional[date]  # None means flexible
```

**`SearchQuery`** — an internal object created by the orchestrator and passed down to every factory and agent. It adds `destination_iata` and `destination_name` so each agent knows where it's searching.

```python
class SearchQuery(BaseModel):
    origin_iata: str
    destination_iata: Optional[str]   # None = inspiration search (find anywhere cheap)
    destination_name: Optional[str]
    budget_usd: float
    duration_days: int
    travelers: int
    departure_date: Optional[date]
```

The key insight: `destination_iata = None` is the signal for an *inspiration search* — "I don't know where I'm going, find me something cheap." When it's set, the agent performs a targeted search for that specific route.

### `results.py`

Three models represent output at different stages of the pipeline:

**`ProviderResult`** — the atomic unit of data returned by any agent. Every agent, regardless of category or provider, must produce this shape.

```python
class ProviderResult(BaseModel):
    provider: str                 # "amadeus", "booking", "viator", etc.
    category: ProviderCategory    # FLIGHT, HOTEL, CAR_RENTAL, or ATTRACTION
    destination_iata: str
    destination_name: str
    title: str                    # Human-readable label ("Bellagio — 4 nights")
    price_usd: float
    details: dict                 # Provider-specific extras (carrier, stars, etc.)
    affiliate_url: Optional[str]  # The money link — embedded in every result
```

**`TripCombo`** — one assembled trip package: exactly one flight + one hotel + one optional car + up to 2 attractions. Built by the orchestrator, not agents.

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
        # Returns {"flight": 400.0, "hotel": 600.0, "car_rental": 180.0, "attractions": 98.0}
```

**`TripSuggestion`** — the final response object. A `TripCombo` enriched by Claude: it adds `rank`, `ai_summary`, `highlights`, `ranking_reason`, and flattens the affiliate URLs into a single dict.

```python
class TripSuggestion(BaseModel):
    rank: int
    destination: str
    destination_iata: str
    total_cost: float
    breakdown: dict[str, float]
    ai_summary: str               # "Las Vegas delivers spectacular value..."
    highlights: list[str]         # ["Strip Night Tour ($98)", "Bellagio Hotel", ...]
    ranking_reason: str           # "Best value-for-money of all candidates."
    affiliate_links: dict[str, Optional[str]]
```

The progression `ProviderResult → TripCombo → TripSuggestion` maps neatly to the three stages of the pipeline: agents produce raw data, the orchestrator assembles packages, Claude enriches and ranks them.

---

## 4. The Abstract Factory Pattern

`backend/factories/base.py` defines two abstract base classes that every factory and agent must implement.

### Why this pattern?

Each travel provider has a completely different API: Amadeus uses OAuth2 client credentials + REST; Booking.com uses an affiliate token in a header; Viator has its own partner SDK. But the orchestrator doesn't care about any of that — it just needs to say "give me hotels in Las Vegas for 4 nights under $700" and get back a list of `ProviderResult` objects.

The Abstract Factory gives us exactly this: a uniform interface over wildly different underlying implementations. Adding a new hotel provider (say, Hotels.com) means writing one new `HotelsComAgent` class and registering it in `HotelProviderFactory.get_agents()`. Nothing else in the codebase changes.

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
        # ... collects results, logs failures, skips failed agents
```

`search_all()` is the key method: it launches all agents for its category concurrently via `asyncio.gather`. If one agent raises an exception (network timeout, rate limit, etc.), it logs a warning and moves on. The factory never crashes because one provider is having a bad day.

### The four concrete factories

Each factory is a single file that just lists which agents it manages:

```python
# factories/flight_factory.py
class FlightProviderFactory(TravelProviderFactory):
    def get_agents(self) -> list[TravelAgent]:
        return [
            AmadeusAgent(),
            # SkyscannerAgent(),  # uncomment when partner access is approved
        ]
```

This also shows the growth path: as new partner agreements are signed, you uncomment one line.

---

## 5. Provider Agents

Agents live in `backend/agents/` organized by category. There are currently three tiers:

| Tier | Agents | Behavior |
|------|--------|----------|
| Real | `AmadeusAgent` | Makes live HTTP calls to api.amadeus.com |
| Mock | `BookingAgent`, `EnterpriseAgent`, `ViatorAgent` | Hardcoded realistic data with random price variation |
| Stub | `SkyscannerAgent`, `ExpediaAgent`, `TicketmasterAgent` | Always return `[]` — slots reserved for future implementation |

The mock/stub split is intentional: it lets the full pipeline run end-to-end while waiting for partner program approvals. When Booking.com approval comes through, `BookingAgent._mock_search()` gets replaced with `_real_search()` that calls the actual API. The orchestrator, factories, tests, and response shapes are all unaffected.

### AmadeusAgent (real)

The only agent making live HTTP calls. It handles two modes:

**Inspiration mode** (`destination_iata = None`):  
Calls `GET /v1/shopping/flight-destinations` with `origin=ATL` and `maxPrice=800` (40% of budget). Amadeus returns a list of destinations with their cheapest available fares. This is Phase 1 of the orchestrator.

**Offers mode** (`destination_iata` is set):  
Calls `GET /v2/shopping/flight-offers` for a specific route. This is used if the orchestrator ever needs to price a specific flight after the inspiration search narrows things down.

**Token caching:**  
Amadeus uses OAuth2 client credentials. Getting a new token on every request would be wasteful and slow. `amadeus_agent.py` uses a module-level `_TokenCache` dataclass:

```python
@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0

_token_cache = _TokenCache()

async def _get_access_token() -> str:
    if time.time() < _token_cache.expires_at - 60:   # refresh 60s early
        return _token_cache.access_token
    # ... fetch new token, update cache
```

Because this is a module-level singleton, it's shared across all requests within a single process. Tokens are reused until 60 seconds before they expire, then refreshed.

### BookingAgent (mock)

Uses a hardcoded dict `_HOTEL_TEMPLATES` with 4 real hotel options per destination (actual hotel names, star ratings, and realistic base rates). Each search applies ±15% random variation to simulate real price fluctuation:

```python
price = base_rate * query.duration_days * random.uniform(0.85, 1.15)
```

Returns an empty list for destinations not in the template dict. This is the expected behavior — not every provider covers every market.

### ViatorAgent (mock)

Similar pattern to BookingAgent: `_ATTRACTIONS` dict keyed by IATA code, 4 attractions per destination with real names and per-person pricing. Prices are multiplied by `query.travelers` since attraction tickets are per-person:

```python
price = attraction["price_per_person"] * query.travelers * random.uniform(0.95, 1.05)
```

### EnterpriseAgent (mock)

Slightly different from the others: it has a `_DEFAULT_RATES` fallback, so it returns results even for destinations not in its main dict. The rationale is that car rental is a commodity — Enterprise operates everywhere, so returning default rates is more realistic than returning empty.

---

## 6. The Orchestrator

`backend/orchestrator.py` is the heart of the system. It implements a two-phase approach to avoid a combinatorial explosion of API calls.

### The combinatorial problem

Naively, you might search flights to all 15 destinations simultaneously, then for each one get hotels, cars, and attractions. That's:
- 15 Amadeus calls for flight offers
- 15 hotel calls
- 15 car calls  
- 15 attraction calls

= 60 concurrent API calls per user request. That would be expensive, slow, and likely get us rate-limited.

### The two-phase solution

**Phase 1 — Inspiration search (1 API call):**  
Ask Amadeus "what are the cheapest round trips from ATL within budget?" in one request. Amadeus returns up to 20 destinations sorted by price. Filter this to our 15-destination pool and take the 5 cheapest.

**Phase 2 — Deep evaluation (fan-out across 5 destinations):**  
For each of the 5 cheapest destinations, concurrently fan out to hotel, car rental, and attraction factories. This is 5 × 3 = 15 calls, all running concurrently.

```python
combo_tasks = [
    _build_combo_for_destination(_DEST_BY_IATA[f.destination_iata], f, query)
    for f in candidates  # top 5 cheapest flights
]
results = await asyncio.gather(*combo_tasks, return_exceptions=True)
```

The `return_exceptions=True` on the outer gather is critical: if one destination's combo build fails entirely (e.g., no hotel results + an agent crash), it shows up as an exception in `results` and gets logged + skipped. The other 4 destinations are unaffected.

### Budget allocation

The orchestrator uses fixed ratios to divide the budget across categories:

```python
_FLIGHT_BUDGET_RATIO    = 0.40   # 40% for flights
_HOTEL_BUDGET_RATIO     = 0.35   # 35% for hotel
_CAR_BUDGET_RATIO       = 0.12   # 12% for car rental
_ATTRACTION_BUDGET_RATIO = 0.13  # 13% for attractions
```

Once the flight price is known (from Amadeus), the remaining budget is redistributed proportionally among hotel/car/attractions:

```python
remaining = query.budget_usd - flight.price_usd
hotel_budget = remaining * (_HOTEL_BUDGET_RATIO / (1 - _FLIGHT_BUDGET_RATIO))
```

This recalculates the ratios on the non-flight portion rather than the total, so cheap flights don't leave the hotel with an undersized budget.

### Picking the best option

`_pick_best()` selects one result from a list given a budget:

```python
def _pick_best(results: list[ProviderResult], budget: float) -> ProviderResult | None:
    within = [r for r in results if r.price_usd <= budget]
    if within:
        return max(within, key=lambda r: r.price_usd)   # most expensive within budget
    return min(results, key=lambda r: r.price_usd)       # cheapest if all exceed budget
```

The "most expensive within budget" heuristic is intentional: given a $700 hotel budget, we'd rather show the $650 Bellagio option than the $200 Motel 6, because it gives Claude better material to rank and the user a more compelling suggestion. If every option is over budget, we return the cheapest one and let the total_cost filter in `find_trips` decide whether to include the combo.

### Destination pool

Rather than searching the entire world, `destinations.json` contains exactly 15 curated destinations: 10 domestic US cities and 5 international. The file includes metadata (avg hotel rates, popular attractions, timezone) that agents can use to generate realistic mock data.

The `_DEST_BY_IATA` dict at module level loads this once at startup:
```python
_DEST_BY_IATA: dict[str, dict] = {d["iata"]: d for d in _DESTINATIONS}
```

Any Amadeus inspiration result whose IATA code is not in this dict gets silently filtered out.

---

## 7. The AI Analyzer

`backend/ai_analyzer.py` is where Claude enters the picture. Its job: take a `list[TripCombo]` and return `list[TripSuggestion]` with AI-generated rankings and narrative summaries.

### Why not rank by cost?

The orchestrator already sorts combos by total cost. But cheapest isn't always best. A $1,100 trip to Nashville with a honky-tonk crawl, distillery tour, and free parking might be a better *experience* than a $950 trip to the same destination with nothing to do. Claude can reason about activity quality, destination appeal for the budget, and the mix of inclusions in a way that a cost sort cannot.

### Getting structured output from Claude

The challenge with LLMs is getting reliable, parseable output. We use **tool use** (also called function calling) to solve this: instead of asking Claude to write JSON in its text response (which it might format inconsistently), we define a tool called `submit_rankings` and tell Claude it *must* call it:

```python
_RANKING_TOOL = {
    "name": "submit_rankings",
    "description": "Submit the final ranked trip suggestions after analysis",
    "input_schema": {
        "type": "object",
        "properties": {
            "rankings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "destination_iata": {"type": "string"},
                        "ai_summary": {"type": "string"},
                        "highlights": {"type": "array", "items": {"type": "string"}},
                        "ranking_reason": {"type": "string"},
                    },
                    ...
                }
            }
        }
    }
}
```

The `tool_choice={"type": "any"}` parameter forces Claude to call a tool rather than responding in free text. The response is then parsed by extracting the `tool_use` block from `response.content`.

### The prompt

The prompt is intentionally lean — it presents each combo in a compact text format and gives Claude clear ranking criteria:

```
Rank these packages from best to worst based on:
1. Value for money (how much experience per dollar spent)
2. Quality and variety of included activities
3. Overall destination appeal for the budget and duration
```

A single call handles all candidates (typically 3-5 combos), so there's one Claude API call per user request regardless of how many destinations were evaluated.

### Graceful fallback

If the Claude call fails for any reason (network error, API outage, tool not called), the system falls back to `_fallback_ranking()` which sorts by cost and generates a simple template-based summary. Users still get results — they're just not AI-enriched. This is logged as a warning but never surfaces as a 500 error.

### Model choice

Uses `claude-sonnet-4-6` — a deliberate balance. The ranking task is conversational-complexity reasoning (not the kind of deep chain-of-thought that would justify Opus), and at ~2,000 tokens of input + 500 tokens of output per call, Sonnet keeps the per-query cost around $0.01.

---

## 8. FastAPI Layer

### `main.py`

The entry point. Three things happen here:

1. **Logging setup** — structured log format with timestamps and level names, applied once at app startup.
2. **CORS middleware** — allows `localhost:5173` (Vite dev server) and `localhost:3000`. In production, this should be locked to the deployed frontend domain.
3. **Router inclusion** — `app.include_router(trips.router, prefix="/api")` mounts all trip routes under `/api`.

### `routers/trips.py`

One endpoint: `POST /api/trips/search`.

```python
@router.post("/search", response_model=list[TripSuggestion])
async def search_trips(query: TripQuery) -> list[TripSuggestion]:
```

FastAPI handles request validation automatically: if `budget_usd = 0` arrives in the body, Pydantic raises a `ValidationError` and FastAPI returns a `422 Unprocessable Entity` with field-level error details — no custom validation code needed.

The endpoint separates orchestrator failures (external APIs down → 502) from AI ranker failures (Claude down → 502), logging each distinctly. If the orchestrator returns an empty list (no combos fit the budget), the endpoint returns `200 []` rather than a 4xx — it's a valid result, just an unfortunate one.

### Interactive API docs

FastAPI auto-generates Swagger UI at `http://localhost:8000/docs`. You can test the search endpoint directly from the browser without needing a frontend or curl.

---

## 9. Configuration

`backend/config.py` uses Pydantic Settings to manage environment variables:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    amadeus_api_key: str = ""
    amadeus_api_secret: str = ""
    ticketmaster_api_key: str = ""

settings = Settings()
```

**All fields default to empty strings**, which means the app starts without crashing even if no `.env` file exists. This is intentional for the mock-first development approach: without any keys set, the full pipeline runs (Amadeus calls will fail and fall back, but mock agents produce results) and Claude calls will fail with an auth error (triggering the `_fallback_ranking` path).

Copy `.env.example` to `backend/.env` and fill in real keys to enable the live integrations.

The `settings` singleton is created at import time and shared across all modules. Agents access it via `from config import settings`.

---

## 10. Test Suite

All tests live in `backend/tests/`. Run from the project root with `pytest`.

### Test philosophy

- **No real API calls.** All network calls are mocked. Tests run offline and complete in under 5 seconds.
- **Test behavior, not implementation.** Tests assert on what comes out, not on internal method calls. If the implementation changes but the behavior stays the same, tests should still pass.
- **Each test proves one thing.** Long test functions with multiple assertions usually indicate the test should be split.

### `conftest.py` — shared fixtures

Defines reusable Pydantic model instances used across test files:

- `sample_query` — a `TripQuery` for 2 people, 4 days, $2,000 from ATL
- `sample_flight` / `sample_hotel` / `sample_car` / `sample_attraction` — individual `ProviderResult` objects
- `sample_combo` — a full `TripCombo` assembled from the above
- `sample_suggestion` — a `TripSuggestion` for router response-shape tests

### `test_models.py` — data validation

Tests Pydantic constraints: zero budget rejected, duration out of 1-30 range rejected, traveler count out of 1-10 range rejected, boundary values accepted. Also tests the `TripCombo.breakdown` property with various combinations of car/no-car and attraction counts.

### `test_agents.py` — agent behavior

Tests each agent category:
- Stub agents (`SkyscannerAgent`, `ExpediaAgent`, `TicketmasterAgent`) always return `[]`
- Mock agents return correctly shaped results for known IATA codes
- `ViatorAgent` is parametrized across all 15 pool destinations to catch missing entries
- Price scaling by traveler count is verified with tight bounds (e.g. `$49 × 2 travelers × ±5%`)

### `test_orchestrator.py` — orchestration logic

Tests `_pick_best` and `_pick_attractions` directly as unit tests (they're pure functions, easy to test). Tests `find_trips` using `unittest.mock.AsyncMock` to replace the factory classes:

```python
with patch("orchestrator.FlightProviderFactory") as MockFF:
    MockFF.return_value.search_all = AsyncMock(return_value=[cheap_flight, pricier_flight])
    combos = await find_trips(base_query)
```

Key scenarios covered: no pool flights → returns [], combos over budget → filtered out, duplicate IATA codes in flight results → deduplicated to cheapest, agent exception → combo skipped gracefully, results returned sorted by cost.

### `test_ai_analyzer.py` — Claude integration

Mocks `anthropic.AsyncAnthropic` to control what Claude "returns":

```python
with patch("ai_analyzer.anthropic.AsyncAnthropic") as MockClient:
    MockClient.return_value.messages.create = AsyncMock(return_value=mock_response)
    suggestions = await rank_trips([sample_combo], query)
```

Tests the happy path (tool called, rankings parsed), fallback paths (tool not called, API exception), edge cases (Claude returns an IATA not in our combo list → skipped), and that `_fallback_ranking` sorts correctly and caps at 3 results.

### `test_router.py` — HTTP contract

Uses FastAPI's `TestClient` (synchronous wrapper around the ASGI app) with mocked orchestrator and analyzer. Tests input validation (422s for missing/invalid fields), response shape, and 502 error paths when either orchestrator or AI analyzer raises.

---

## 11. Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example backend/.env
# Edit backend/.env — at minimum add ANTHROPIC_API_KEY for AI ranking
# AMADEUS keys are needed for real flight data; omit to use inspiration fallback

# 3. Start the backend
cd backend
uvicorn main:app --reload
# API at http://localhost:8000
# Swagger UI at http://localhost:8000/docs

# 4. Run tests (from project root)
pytest            # all tests
pytest -v         # verbose output
pytest backend/tests/test_agents.py -v    # single file
pytest -k "orchestrator"                  # tests matching keyword
```

---

## 12. Extending the System

### Adding a new provider to an existing category

Example: add Hotels.com to the hotel category.

1. Create `backend/agents/hotels/hotelscom_agent.py`
2. Implement `TravelAgent`:
   ```python
   class HotelsComAgent(TravelAgent):
       @property
       def provider_name(self) -> str:
           return "hotels_com"

       async def search(self, query: SearchQuery) -> list[ProviderResult]:
           # ... call Hotels.com API, return list[ProviderResult]
   ```
3. Register it in `backend/factories/hotel_factory.py`:
   ```python
   def get_agents(self) -> list[TravelAgent]:
       return [BookingAgent(), HotelsComAgent()]
   ```
4. Add tests in `backend/tests/test_agents.py`

That's it. The orchestrator, AI analyzer, and router are completely unchanged.

### Adding a new destination

Edit `backend/data/destinations.json` and add a new object with the required fields. Then add mock data entries for the new IATA code in `booking_agent.py`, `enterprise_agent.py`, and `viator_agent.py`. The orchestrator picks it up automatically on next restart.

### Replacing a mock agent with a real one

When a partner API becomes available, the swap is confined to a single file. Keep the `_mock_search` function in the file (commented out or behind a flag) until the real API is proven stable in production.

---

## Open Items

- [ ] React frontend (Task #5) — Vite + TypeScript + Tailwind + shadcn/ui
- [ ] Redis caching layer — cache hotel/attraction results for 30 min (prices are stable)
- [ ] Skyscanner partner approval — stub currently in place
- [ ] Booking.com / Expedia partner approval — mock currently in place
- [ ] Flexible date handling — currently defaults to 30 days out if no date given
- [ ] User accounts + saved trips — Phase 2

---

*This document is updated alongside the code. When new features land, add a section here.*
