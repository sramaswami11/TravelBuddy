import { useState, FormEvent } from 'react';
import { TripQuery } from '../api';
import { AirportInput } from './AirportInput';
import { airports } from '../data/airports';

interface Props {
  onSearch: (query: TripQuery) => void;
  loading: boolean;
  initialValues?: Partial<TripQuery>;
}

export function SearchForm({ onSearch, loading, initialValues }: Props) {
  const [originIata, setOriginIata] = useState(initialValues?.origin_iata ?? '');
  const [budget, setBudget] = useState(initialValues?.budget_usd ? String(initialValues.budget_usd) : '');
  const [days, setDays] = useState(initialValues?.duration_days ? String(initialValues.duration_days) : '7');
  const [travelers, setTravelers] = useState(initialValues?.travelers ? String(initialValues.travelers) : '1');
  const [departureDate, setDepartureDate] = useState(initialValues?.departure_date ?? '');

  const initialAirportLabel = initialValues?.origin_iata
    ? (() => {
        const a = airports.find(ap => ap.iata === initialValues.origin_iata);
        return a ? `${a.city} (${a.iata})` : '';
      })()
    : '';
  const [budgetError, setBudgetError] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!originIata) return;

    const budgetNum = parseFloat(budget);
    if (budgetNum < 500) {
      setBudgetError('Minimum budget is $500');
      return;
    }
    setBudgetError('');

    onSearch({
      origin_iata: originIata,
      budget_usd: budgetNum,
      duration_days: parseInt(days),
      travelers: parseInt(travelers),
      departure_date: departureDate || undefined,
    });
  }

  const inputClass =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500';
  const labelClass = 'block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="min-w-0">
          <label htmlFor="flying-from" className={labelClass}>Flying from</label>
          <AirportInput
            id="flying-from"
            value={originIata}
            onChange={setOriginIata}
            inputClass={inputClass}
            required
            initialLabel={initialAirportLabel}
          />
        </div>
        <div className="min-w-0">
          <label htmlFor="budget" className={labelClass}>Budget (USD)</label>
          <input
            id="budget"
            className={`${inputClass} ${budgetError ? 'border-red-400 focus:border-red-400 focus:ring-red-400' : ''}`}
            type="number"
            placeholder="2000"
            min={500}
            required
            value={budget}
            onChange={e => {
              setBudget(e.target.value);
              if (budgetError) setBudgetError('');
            }}
          />
          {budgetError && <p className="mt-1 text-xs text-red-500">{budgetError}</p>}
        </div>
        <div className="min-w-0">
          <label htmlFor="days" className={labelClass}>Days</label>
          <input
            id="days"
            className={inputClass}
            type="number"
            min={1}
            max={30}
            required
            value={days}
            onChange={e => setDays(e.target.value)}
          />
        </div>
        <div className="min-w-0">
          <label htmlFor="travelers" className={labelClass}>Travelers</label>
          <input
            id="travelers"
            className={inputClass}
            type="number"
            min={1}
            max={10}
            value={travelers}
            onChange={e => setTravelers(e.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-end gap-3">
        <div className="flex-1 sm:max-w-xs">
          <label htmlFor="departure-date" className={labelClass}>Departure date (optional)</label>
          <input
            id="departure-date"
            className={inputClass}
            type="date"
            value={departureDate}
            onChange={e => setDepartureDate(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !originIata}
          className="w-full sm:w-auto px-8 py-2 rounded-lg bg-indigo-600 text-white font-semibold text-sm hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Searching…' : 'Find Trips'}
        </button>
      </div>
    </form>
  );
}
