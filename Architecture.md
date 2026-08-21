# TravelBuddy — Architecture (Living Document)

> **Status:** Work in Progress  
> **Last updated:** 2026-08-19  
> **Stack:** Python 3.12 / FastAPI · React 18 / Vite · Deployed on Railway + Vercel

---

## 1. Problem Statement

A user has a fixed budget (e.g. $2,000) and a trip duration (e.g. 4 days) and wants to know **where they should go** — with a complete, costed itinerary covering flights, hotel, rental car, and attraction tickets — sourced from real-time pricing APIs and ranked by an AI model.

---

## 2. High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER (Browser)                              │
│          React + Vite frontend  ·  hosted on Vercel                  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  HTTPS / REST (JSON)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                  hosted on Railway / Render                          │
│                                                                      │
│   ┌──────────────┐    ┌────────────────┐    ┌─────────────────────┐ │
│   │  Trip Router │───►│  Orchestrator  │───►│   AI Analyzer       │ │
│   │  (REST API)  │    │  (async fan-out│    │ (Claude / GPT)      │ │
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
   ┌─────┴──────┐       ┌──────┴──────┐        ┌──────┴──────┐
   │ Amadeus    │       │ Booking.com │        │ Viator      │
   │ Agent      │       │ Agent       │        │ Agent       │
   ├────────────┤       ├─────────────┤        ├─────────────┤
   │ Skyscanner │       │ Expedia     │        │ Ticketmaster│
   │ Agent      │       │ Agent       │        │ Agent       │
   └────────────┘       └─────────────┘        └─────────────┘
                                                      +
                                              ┌───────────────┐
                                              │ Car Rental    │
                                              │ Factory       │
                                              └───────┬───────┘
                                                      │
                                              ┌───────┴───────┐
                                              │ Enterprise    │
                                              │ Agent         │
                                              ├───────────────┤
                                              │ Turo Agent    │
                                              └───────────────┘
```

---

## 3. Design Pattern: Abstract Factory

Each travel **category** (flights, hotels, car rentals, attractions) is a **Factory**. Each **provider** within that category is a concrete **Agent** produced by that factory.

```
TravelProviderFactory (abstract)
    └── search(query: SearchQuery) → list[ProviderResult]

FlightProviderFactory(TravelProviderFactory)
    ├── AmadeusAgent      → calls api.amadeus.com
    └── SkyscannerAgent   → calls partners.api.skyscanner.net

HotelProviderFactory(TravelProviderFactory)
    ├── BookingAgent      → calls booking.com Affiliate API
    └── ExpediaAgent      → calls rapidapi.com/expedia

CarRentalProviderFactory(TravelProviderFactory)
    └── EnterpriseAgent   → calls enterprise partner API

AttractionProviderFactory(TravelProviderFactory)
    ├── ViatorAgent       → calls viator.com partner API
    └── TicketmasterAgent → calls discovery.api.ticketmaster.com
```

**Why Abstract Factory here:**  
Every provider exposes completely different auth schemes, request shapes, and response formats — but the orchestrator only needs to call `search(query)` on each. Swapping or adding providers (e.g. adding Priceline for hotels) means adding one new Agent class without touching the orchestrator.

---

## 4. Request / Response Data Flow

```
User submits:
  { origin: "JFK", budget: 2000, days: 4, travelers: 2, dates: "flexible" }
          │
          ▼
Orchestrator fans out CONCURRENTLY (asyncio.gather):
  ├── FlightFactory.search(query)    → [AmadeusResult, SkyscannerResult]
  ├── HotelFactory.search(query)     → [BookingResult, ExpediaResult]
  ├── CarRentalFactory.search(query) → [EnterpriseResult]
  └── AttractionFactory.search(query)→ [ViatorResult, TicketmasterResult]
          │
          ▼
ResultAggregator:
  - Normalizes all results to a common schema
  - Prunes combinations that exceed budget
  - Builds top N trip combos (flight + hotel + car + 2 attractions)
          │
          ▼
AIAnalyzer (Claude API):
  - Ranks combos by value-for-money, experience quality, travel convenience
  - Adds narrative explanation ("This combo gives you 2 nights beachfront...")
  - Returns top 3 ranked packages
          │
          ▼
Response to frontend:
  {
    suggestions: [
      {
        rank: 1,
        destination: "Cancun, MX",
        total_cost: 1847,
        breakdown: { flight: 480, hotel: 720, car: 210, attractions: 437 },
        ai_summary: "...",
        affiliate_links: { flight: "...", hotel: "...", ... }
      },
      ...
    ]
  }
```

---

## 5. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React 18 + Vite | Rich UI ecosystem, fast builds, great travel component libraries |
| Styling | Tailwind CSS + shadcn/ui | Polished components out of the box (cards, sliders, modals) |
| Async state | TanStack Query | Handles loading states per-provider cleanly; shows partial results as they arrive |
| Backend | Python 3.12 + FastAPI | Async-native, perfect for concurrent API fan-out |
| Concurrency | asyncio + httpx | Non-blocking HTTP for all provider calls in parallel |
| AI Analysis | Anthropic Claude API | Ranks trip combos, generates natural-language summaries |
| Frontend deploy | Vercel | Zero-config, free tier, deploys on every git push |
| Backend deploy | Railway | Simple Python deploys, ~$5-7/mo to start |

---

## 6. External API Providers

| Category | Provider | API | Free Tier | Revenue Model |
|---|---|---|---|---|
| Flights | Amadeus | api.amadeus.com | 2,000 calls/mo | Pay-per-call after |
| Flights | Skyscanner | Partner program | Apply required | Revenue share |
| Hotels | Booking.com | Affiliate API | Free | Commission per booking |
| Hotels | Expedia | Rapid API | Partner program | Commission per booking |
| Car Rental | Enterprise | Partner API | TBD | Commission per booking |
| Attractions | Viator | Partner API | Free | 8% affiliate commission |
| Attractions | Ticketmaster | Discovery API | 5,000 calls/day | Free / affiliate |
| Maps/Places | Google Maps | Places API | $200/mo credit | Pay-per-call after |
| AI | Anthropic Claude | API | Pay-per-token | ~$0.003/query |
| Currency | ExchangeRate-API | Free tier | 1,500 calls/mo | Free |

---

## 7. Revenue Integration

Affiliate links are embedded directly in the response for each suggestion:

```
suggestion.affiliate_links.hotel  → Booking.com tracked deep-link
suggestion.affiliate_links.flight → Expedia tracked deep-link
suggestion.affiliate_links.activities → Viator tracked links
```

When a user clicks and completes a booking, TravelBuddy earns a commission (3-8% depending on provider) with no cost to the user.

**Future revenue tiers:**
- Free: 3 destination suggestions, standard refresh rate
- Premium ($9/mo): Unlimited suggestions, price alerts, saved trips, faster results

---

## 8. Project Directory Structure (Planned)

```
TravelBuddy/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── routers/
│   │   └── trips.py               # POST /api/trips/search
│   ├── factories/
│   │   ├── base.py                # Abstract base classes
│   │   ├── flight_factory.py
│   │   ├── hotel_factory.py
│   │   ├── car_rental_factory.py
│   │   └── attraction_factory.py
│   ├── agents/
│   │   ├── flights/
│   │   │   ├── amadeus_agent.py
│   │   │   └── skyscanner_agent.py
│   │   ├── hotels/
│   │   │   ├── booking_agent.py
│   │   │   └── expedia_agent.py
│   │   ├── car_rental/
│   │   │   └── enterprise_agent.py
│   │   └── attractions/
│   │       ├── viator_agent.py
│   │       └── ticketmaster_agent.py
│   ├── models/
│   │   ├── query.py               # TripQuery schema
│   │   └── results.py             # ProviderResult, TripSuggestion schemas
│   ├── orchestrator.py            # Async fan-out + aggregation
│   ├── ai_analyzer.py             # Claude API integration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchForm.tsx
│   │   │   ├── TripCard.tsx
│   │   │   ├── BudgetBreakdown.tsx
│   │   │   └── LoadingState.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   └── Results.tsx
│   │   ├── hooks/
│   │   │   └── useTripSearch.ts   # TanStack Query hook
│   │   └── api/
│   │       └── trips.ts           # API client
│   ├── package.json
│   └── vite.config.ts
└── Architecture.md                # This file
```

---

## 9. Open Questions / WIP

- [ ] **Destination pool:** Do we start with a fixed list of ~20 popular destinations or do we allow open-ended search? Fixed list is easier to build v1 against.
- [ ] **Date handling:** "Flexible" dates vs specific date range — flexible means more API calls; scope TBD.
- [ ] **Car rental scope:** Is a car rental always included, or optional? (Some city trips don't need one.)
- [ ] **Caching strategy:** Flight prices change fast; hotel prices are more stable. Do we cache hotel results for 30 min to reduce API calls?
- [ ] **Skyscanner access:** Requires partner application approval — may need to fall back to Amadeus-only for flights at launch.
- [ ] **Error handling / partial results:** If one provider is down, do we show partial results or wait? Leaning toward partial (show what we have, flag what failed).
- [ ] **Auth / user accounts:** MVP is anonymous (no login). Saved trips and alerts require accounts — Phase 2.
- [ ] **Mobile:** React app will be responsive, but a dedicated React Native app is a later consideration.

---

## 10. Build Phases

### Phase 1 — MVP (prove the concept)
- FastAPI backend with Amadeus (flights) + Booking.com (hotels) only
- Fixed destination pool: top 10 US + 5 international cities
- AI ranking via Claude API
- Basic React UI: search form + results cards
- Affiliate links embedded

### Phase 2 — Expand coverage
- Add car rental + attraction providers
- Flexible date search
- Price caching layer (Redis)
- User accounts + saved trips

### Phase 3 — Scale & monetize
- Premium subscription tier
- Price alerts (background polling jobs)
- Mobile app (React Native)
- White-label API for travel agencies
