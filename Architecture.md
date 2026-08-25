# packedNbooked — Architecture (Living Document)

> **Status:** Live in production  
> **Last updated:** 2026-08-25  
> **Stack:** Python 3.12 / FastAPI · React 18 / Vite · Deployed on Render  
> **Live URL:** https://packednbooked.com

---

## 1. Problem Statement

A user has a fixed budget (e.g. $2,000) and a trip duration (e.g. 7 days) and wants to know **where they should go** — with a complete, costed itinerary covering flights, hotel, rental car, and attraction tickets — sourced from real-time pricing APIs and ranked by AI.

Revenue model: affiliate commissions from Booking.com, Skyscanner, Viator, and Ticketmaster links embedded in every result.

---

## 2. High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER (Browser)                              │
│          React + Vite frontend · packednbooked.com (Render)          │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  HTTPS / REST (JSON)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                  travelbuddy-yfhy.onrender.com                       │
│                                                                      │
│   ┌──────────────┐    ┌────────────────┐    ┌─────────────────────┐ │
│   │  Trip Router │───►│  Orchestrator  │───►│   AI Analyzer       │ │
│   │  (REST API)  │    │  (async fan-out│    │  (Groq + GPT-OSS)   │ │
│   └──────────────┘    │   per factory) │    └─────────────────────┘ │
│                       └───────┬────────┘                            │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
  ┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
  │ Flight       │    │ Hotel            │    │ Attractions       │
  │ Factory      │    │ Factory          │    │ Factory           │
  └──────┬───────┘    └────────┬─────────┘    └────────┬──────────┘
         │                     │                       │
   ┌─────┴──────┐       ┌──────┴──────┐        ┌──────┴──────────┐
   │ Duffel     │       │ Booking.com │        │ Viator          │
   │ Agent ✅   │       │ Agent (mock)│        │ Agent (mock)    │
   └────────────┘       └─────────────┘        ├─────────────────┤
                                               │ Ticketmaster    │
                                               │ Agent (stub)    │
                                               └─────────────────┘
                                                      +
                                              ┌───────────────┐
                                              │ Car Rental    │
                                              │ Factory       │
                                              └───────┬───────┘
                                                      │
                                              ┌───────┴───────┐
                                              │ Enterprise    │
                                              │ Agent (mock)  │
                                              └───────────────┘
```

Legend: ✅ = live API  |  (mock) = realistic hardcoded data  |  (stub) = always returns []

---

## 3. Design Pattern: Abstract Factory

Each travel **category** (flights, hotels, car rentals, attractions) is a **Factory**. Each **provider** within that category is a concrete **Agent** produced by that factory.

```
TravelProviderFactory (abstract)
    └── search(query: SearchQuery) → list[ProviderResult]

FlightProviderFactory(TravelProviderFactory)
    └── DuffelAgent       → calls api.duffel.com  (LIVE)

HotelProviderFactory(TravelProviderFactory)
    └── BookingAgent      → mock data  (pending partner approval)

CarRentalProviderFactory(TravelProviderFactory)
    └── EnterpriseAgent   → mock data  (pending API access)

AttractionProviderFactory(TravelProviderFactory)
    ├── ViatorAgent       → mock data  (pending partner approval)
    └── TicketmasterAgent → stub  (TICKETMASTER_API_KEY not yet set)
```

**Why Abstract Factory here:**  
Every provider exposes completely different auth schemes, request shapes, and response formats — but the orchestrator only needs to call `search(query)` on each. Adding a new provider means adding one Agent class without touching the orchestrator.

---

## 4. Request / Response Data Flow

```
User submits:
  { origin: "JFK", budget: 2000, days: 7, travelers: 1 }
          │
          ▼
Orchestrator — Phase 1 (inspiration search):
  DuffelAgent fans out concurrently to all 15 pool destinations.
  Returns cheapest round-trip offer per destination.
  Filter + keep the 5 cheapest within budget.
          │
          ▼
Orchestrator — Phase 2 (deep evaluation, concurrent across 5 destinations):
  ├── HotelFactory.search()      → BookingAgent
  ├── CarRentalFactory.search()  → EnterpriseAgent
  └── AttractionFactory.search() → ViatorAgent + TicketmasterAgent
          │
          ▼
Budget allocation + combo assembly:
  40% flights · 35% hotel · 12% car · 13% activities
  Drop combos exceeding total budget.
          │
          ▼
AI Analyzer (Groq · openai/gpt-oss-120b):
  Ranks combos by value-for-money, activity quality, destination appeal.
  Returns rank + ai_summary + highlights + ranking_reason per combo.
  Falls back to cost-sort if Groq fails.
          │
          ▼
Response to frontend:
  [
    {
      rank: 1,
      destination: "Cancún, MX",
      total_cost: 1847,
      breakdown: { flight: 480, hotel: 720, car_rental: 210, attractions: 437 },
      ai_summary: "...",
      affiliate_links: { flight: "skyscanner.net/...", hotel: "booking.com/...", ... }
    },
    ...
  ]
```

---

## 5. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | Fast builds, full type safety, great DX |
| Styling | Tailwind CSS | Utility-first, no runtime CSS overhead |
| State | useState + fetch | Simple enough; no state library needed at this scale |
| Backend | Python 3.12 + FastAPI | Async-native, perfect for concurrent API fan-out |
| Concurrency | asyncio + httpx | Non-blocking HTTP for all provider calls in parallel |
| AI Analysis | Groq · openai/gpt-oss-120b | Fast inference, low cost; uses openai SDK pointed at Groq endpoint |
| Frontend deploy | Render (Static Site) | packednbooked.com — custom domain with auto-SSL |
| Backend deploy | Render (Web Service) | travelbuddy-yfhy.onrender.com |

**Why Groq instead of Anthropic/OpenAI:**  
Free-tier inference during development; openai/gpt-oss-120b handles the structured JSON ranking task reliably. Groq's speed (~3–5× faster than OpenAI) keeps total search latency acceptable.

---

## 6. External API Providers

| Category | Provider | Status | Revenue Model |
|---|---|---|---|
| Flights | Duffel | ✅ Sandbox live — production key pending | Deep links via Skyscanner affiliate |
| Hotels | Booking.com | Mock — affiliate application pending | Commission per booking |
| Car Rental | Enterprise | Mock — API access pending | Commission per booking |
| Attractions | Viator | Mock — partner application pending | ~8% affiliate commission |
| Attractions | Ticketmaster | Stub — API key not set | Affiliate links |
| AI Ranking | Groq (openai/gpt-oss-120b) | ✅ Live | Per-token cost |

**Affiliate link status:**
- Flights: Skyscanner deep links wired. Add `&partner_id=YOUR_ID` once enrolled.
- Hotels: `YOUR_AFFILIATE_ID` placeholder in `booking_agent.py:108`.
- Skyscanner: `&partner_id=YOUR_SKYSCANNER_PARTNER_ID` placeholder in `duffel_agent.py:38`.

---

## 7. Revenue Integration

Affiliate links are embedded in every `TripSuggestion` response:

```
suggestion.affiliate_links.flight       → Skyscanner deep link
suggestion.affiliate_links.hotel        → Booking.com affiliate deep link
suggestion.affiliate_links.car_rental   → Enterprise homepage (generic for now)
suggestion.affiliate_links.attractions  → Viator search link
```

When a user clicks and completes a booking, packedNbooked earns a commission (typically 4–10% depending on provider). No cost to the user.

---

## 8. Project Directory Structure

```
packedNbooked/
├── Architecture.md              # This file — high-level design
├── Implementation.md            # Code walkthrough
│
├── backend/
│   ├── main.py                  # FastAPI app + CORS middleware
│   ├── config.py                # Pydantic Settings — reads from .env
│   ├── orchestrator.py          # Two-phase async pipeline
│   ├── ai_analyzer.py           # Groq ranking + fallback cost-sort
│   ├── requirements.txt         # Python dependencies
│   │
│   ├── routers/
│   │   └── trips.py             # POST /api/trips/search
│   │
│   ├── models/
│   │   ├── query.py             # TripQuery + SearchQuery
│   │   └── results.py           # ProviderResult, TripCombo, TripSuggestion
│   │
│   ├── factories/
│   │   ├── base.py              # TravelAgent + TravelProviderFactory ABCs
│   │   ├── flight_factory.py
│   │   ├── hotel_factory.py
│   │   ├── car_rental_factory.py
│   │   └── attraction_factory.py
│   │
│   ├── agents/
│   │   ├── flights/
│   │   │   ├── duffel_agent.py       # LIVE — Duffel sandbox API
│   │   │   └── skyscanner_agent.py   # STUB
│   │   ├── hotels/
│   │   │   └── booking_agent.py      # MOCK
│   │   ├── car_rental/
│   │   │   └── enterprise_agent.py   # MOCK
│   │   └── attractions/
│   │       ├── viator_agent.py       # MOCK
│   │       └── ticketmaster_agent.py # STUB
│   │
│   ├── data/
│   │   └── destinations.json         # 15 curated destinations
│   │
│   └── tests/                        # 88 tests, all passing
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_agents.py
│       ├── test_orchestrator.py
│       ├── test_ai_analyzer.py
│       └── test_router.py
│
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx              # Root — hero, results grid, footer
        ├── api.ts               # fetch wrapper + TypeScript types
        ├── data/
        │   └── airports.ts      # ~250 worldwide airports for autocomplete
        └── components/
            ├── AirportInput.tsx # City/airport autocomplete combobox
            ├── SearchForm.tsx   # Search inputs + validation
            └── TripCard.tsx     # Result card with breakdown + booking links
```

---

## 9. Destination Pool

Rather than searching the entire world, `destinations.json` contains 15 curated destinations: a mix of domestic US and international cities. The Duffel inspiration search fans out concurrently to all 15, picks the 5 cheapest round trips within budget, then evaluates those 5 in depth (hotel + car + activities).

The pool is intentionally small to keep API costs and latency manageable. Adding a destination requires only a new entry in `destinations.json` plus mock data entries in the hotel/car/attraction agents.

---

## 10. Build Phases

### Phase 1 — MVP ✅ Complete
- FastAPI backend with Duffel (flights, live) + mock hotel/car/attractions
- 15-destination pool (10 US + 5 international)
- AI ranking via Groq (openai/gpt-oss-120b)
- React frontend: search form with airport autocomplete + result cards
- Affiliate links embedded (Skyscanner wired; Booking.com placeholder)
- Deployed end-to-end on Render at packednbooked.com

### Phase 2 — Real Data & Affiliate Revenue (In Progress)
- [ ] Duffel production key (apply at duffel.com)
- [ ] Booking.com affiliate approval → real hotel API
- [ ] Skyscanner affiliate partner ID
- [ ] Viator partner approval → real attraction data
- [ ] Ticketmaster API key → real event data
- [ ] Privacy Policy + Terms of Use pages
- [ ] Favicon + brand polish

### Phase 3 — Growth
- [ ] Real car rental API
- [ ] Redis caching (hotel/attraction prices stable for 30 min)
- [ ] Expand destination pool beyond 15
- [ ] User accounts + saved trips
- [ ] Price alerts (background jobs)
- [ ] Multi-currency display
