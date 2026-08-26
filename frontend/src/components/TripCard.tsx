import { TripSuggestion } from '../api';

const RANK_STYLES = [
  'bg-yellow-400 text-yellow-900',
  'bg-gray-300 text-gray-700',
  'bg-amber-600 text-amber-100',
];

const RANK_LABELS = ['#1', '#2', '#3'];

function formatDate(iso: string): string {
  if (!iso) return '';
  const [year, month, day] = iso.split('-');
  const d = new Date(Number(year), Number(month) - 1, Number(day));
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

interface Props {
  trip: TripSuggestion;
}

function BookLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-block rounded px-3 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors"
    >
      {label}
    </a>
  );
}

export function TripCard({ trip }: Props) {
  const rankIdx = trip.rank - 1;

  const breakdown = [
    { label: 'Flight', value: trip.breakdown.flight, link: trip.affiliate_links.flight, linkLabel: 'Book flight' },
    { label: 'Hotel', value: trip.breakdown.hotel, link: trip.affiliate_links.hotel, linkLabel: 'Book hotel' },
    { label: 'Car rental', value: trip.breakdown.car_rental, link: trip.affiliate_links.car_rental, linkLabel: 'Book car' },
    { label: 'Activities', value: trip.breakdown.attractions, link: trip.affiliate_links.attractions, linkLabel: 'Browse activities' },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-md overflow-hidden flex flex-col">
      <div className="bg-indigo-600 px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-indigo-200 text-xs font-semibold uppercase tracking-wide">
            {trip.destination_iata}
          </p>
          <h2 className="text-white text-lg font-bold leading-tight">{trip.destination}</h2>
        </div>
        <span
          className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${RANK_STYLES[rankIdx] ?? 'bg-gray-200 text-gray-600'}`}
        >
          {RANK_LABELS[rankIdx] ?? `#${trip.rank}`}
        </span>
      </div>

      {trip.departure_date && (
        <div className="px-5 py-2 bg-indigo-50 border-b border-indigo-100 flex items-center gap-2 text-xs text-indigo-700 font-medium">
          <span>✈</span>
          <span>{formatDate(trip.departure_date)} → {formatDate(trip.return_date)}</span>
        </div>
      )}

      <div className="px-5 py-4 flex-1 space-y-4">
        <p className="text-gray-600 text-sm leading-relaxed">{trip.ai_summary}</p>

        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Cost breakdown</p>
          <div className="space-y-1">
            {breakdown.map(({ label, value }) => (
              <div key={label} className="flex justify-between text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-800">${value.toFixed(0)}</span>
              </div>
            ))}
            <div className="flex justify-between text-sm font-bold border-t pt-1 mt-1">
              <span className="text-gray-700">Total</span>
              <span className="text-indigo-600">${trip.total_cost.toFixed(0)}</span>
            </div>
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Highlights</p>
          <ul className="space-y-1">
            {trip.highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="text-indigo-400 mt-0.5">•</span>
                {h}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-gray-400 italic">{trip.ranking_reason}</p>
      </div>

      <div className="px-5 py-3 bg-gray-50 border-t flex flex-wrap gap-2">
        {breakdown.map(({ link, linkLabel }) => (
          <BookLink key={linkLabel} href={link} label={linkLabel} />
        ))}
      </div>

      <div className="px-5 py-2 bg-amber-50 border-t border-amber-100">
        <p className="text-xs text-amber-700">
          ⚠ Flight prices are estimates and may differ from actual fares. Always confirm on the booking site before purchasing.
        </p>
      </div>
    </div>
  );
}
