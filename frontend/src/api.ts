export interface TripQuery {
  origin_iata: string;
  budget_usd: number;
  duration_days: number;
  travelers: number;
  departure_date?: string;
}

export interface TripSuggestion {
  rank: number;
  destination: string;
  destination_iata: string;
  total_cost: number;
  breakdown: {
    flight: number;
    hotel: number;
    car_rental: number;
    attractions: number;
  };
  ai_summary: string;
  highlights: string[];
  ranking_reason: string;
  affiliate_links: {
    flight: string | null;
    hotel: string | null;
    car_rental: string | null;
    attractions: string | null;
  };
  departure_date: string;
  return_date: string;
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export async function searchTrips(query: TripQuery): Promise<TripSuggestion[]> {
  const body: Record<string, unknown> = { ...query };
  if (!body.departure_date) delete body.departure_date;

  const res = await fetch(`${API_BASE}/api/trips/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<TripSuggestion[]>;
}
