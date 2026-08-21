import { useState } from 'react';
import { searchTrips, TripQuery, TripSuggestion } from './api';
import { SearchForm } from './components/SearchForm';
import { TripCard } from './components/TripCard';

export default function App() {
  const [results, setResults] = useState<TripSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function handleSearch(query: TripQuery) {
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await searchTrips(query);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-indigo-700 py-12 px-4">
        <div className="max-w-3xl mx-auto text-center mb-8">
          <h1 className="text-4xl font-extrabold text-white tracking-tight">TravelBuddy</h1>
          <p className="mt-2 text-indigo-200 text-lg">
            Enter your budget and we'll find the best complete trip for you.
          </p>
        </div>
        <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg p-6">
          <SearchForm onSearch={handleSearch} loading={loading} />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-10">
        {loading && (
          <div className="flex flex-col items-center py-16 text-gray-400">
            <div className="w-10 h-10 border-4 border-indigo-300 border-t-indigo-600 rounded-full animate-spin mb-4" />
            <p className="text-sm">Searching flights, hotels, and activities…</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-red-700 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && results.length > 0 && (
          <>
            <h2 className="text-lg font-semibold text-gray-700 mb-5">
              Top {results.length} trip{results.length !== 1 ? 's' : ''} for your budget
            </h2>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {results.map(trip => (
                <TripCard key={trip.destination_iata} trip={trip} />
              ))}
            </div>
          </>
        )}

        {!loading && !error && searched && results.length === 0 && (
          <p className="text-center text-gray-400 py-16 text-sm">
            No trips found. Try a higher budget or different dates.
          </p>
        )}
      </div>
    </div>
  );
}
