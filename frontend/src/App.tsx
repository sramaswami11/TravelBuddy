import { useState } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { searchTrips, TripQuery, TripSuggestion } from './api';
import { SearchForm } from './components/SearchForm';
import { TripCard } from './components/TripCard';
import { PrivacyPolicy } from './pages/PrivacyPolicy';
import { TermsOfUse } from './pages/TermsOfUse';

export default function App() {
  return (
    <Routes>
      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfUse />} />
      <Route path="*" element={<HomePage />} />
    </Routes>
  );
}

function HomePage() {
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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Hero */}
      <div className="bg-gradient-to-br from-indigo-900 via-indigo-700 to-indigo-600 py-14 px-4">
        <div className="max-w-3xl mx-auto text-center mb-10">
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight">
            packed<span className="text-yellow-400">N</span>booked
          </h1>
          <p className="mt-3 text-indigo-200 text-lg">
            Tell us your budget. We'll find your perfect trip.
          </p>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-5 text-indigo-300 text-sm font-medium">
            <span>✈ Flights</span>
            <span>🏨 Hotels</span>
            <span>🚗 Car Rental</span>
            <span>🎭 Activities</span>
          </div>
        </div>

        <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-xl p-6">
          <SearchForm onSearch={handleSearch} loading={loading} />
        </div>
      </div>

      {/* Results */}
      <div className="max-w-5xl mx-auto w-full px-4 py-10 flex-1">
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

      {/* How it works — shown only on landing */}
      {!searched && (
        <div className="bg-white border-t border-gray-100 py-14 px-4">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl font-bold text-gray-800 text-center mb-2">How it works</h2>
            <p className="text-center text-gray-400 text-sm mb-10">
              From budget to booked in seconds.
            </p>
            <div className="grid gap-8 sm:grid-cols-3">
              {[
                {
                  step: '1',
                  title: 'Set your budget',
                  desc: 'Enter your travel budget, departure city, trip length, and number of travelers. No account needed.',
                },
                {
                  step: '2',
                  title: 'We search everything',
                  desc: 'We scan real flights, hotels, car rentals, and activities across providers — all at once, in seconds.',
                },
                {
                  step: '3',
                  title: 'Book your perfect trip',
                  desc: 'Get AI-ranked complete trip packages. Compare costs and highlights, then book each piece directly.',
                },
              ].map(({ step, title, desc }) => (
                <div key={step} className="flex flex-col items-center text-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-indigo-600 text-white flex items-center justify-center text-lg font-bold shrink-0">
                    {step}
                  </div>
                  <h3 className="font-semibold text-gray-800">{title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-6 px-4 mt-auto">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-gray-400">
          <span className="font-bold text-gray-600">
            packed<span className="text-yellow-500">N</span>booked
          </span>
          <div className="flex gap-5">
            <Link to="/privacy" className="hover:text-indigo-600 transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-indigo-600 transition-colors">Terms of Use</Link>
            <a href="mailto:hello@packednbooked.com" className="hover:text-indigo-600 transition-colors">Contact</a>
          </div>
          <span>© {new Date().getFullYear()} packedNbooked</span>
        </div>
      </footer>
    </div>
  );
}
