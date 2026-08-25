import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { airports, Airport } from '../data/airports';

interface Props {
  value: string;
  onChange: (iata: string) => void;
  inputClass: string;
  required?: boolean;
}

export function AirportInput({ value, onChange, inputClass, required }: Props) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!value) setQuery('');
  }, [value]);

  const filtered =
    query.length >= 2
      ? airports
          .filter(
            a =>
              a.city.toLowerCase().includes(query.toLowerCase()) ||
              a.iata.toLowerCase().includes(query.toLowerCase()) ||
              a.name.toLowerCase().includes(query.toLowerCase()) ||
              a.country.toLowerCase().includes(query.toLowerCase()),
          )
          .slice(0, 8)
      : [];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function select(airport: Airport) {
    setQuery(`${airport.city} (${airport.iata})`);
    onChange(airport.iata);
    setOpen(false);
    setHighlighted(0);
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (!open || filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlighted(h => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlighted(h => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[highlighted]) select(filtered[highlighted]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        className={inputClass}
        placeholder="City or airport"
        value={query}
        autoComplete="off"
        required={required}
        onChange={e => {
          setQuery(e.target.value);
          setHighlighted(0);
          setOpen(true);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => {
          if (query.length >= 2) setOpen(true);
        }}
        onKeyDown={handleKeyDown}
      />
      {open && filtered.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full min-w-[280px] bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {filtered.map((airport, i) => (
            <li
              key={airport.iata}
              className={`px-3 py-2 cursor-pointer ${
                i === highlighted ? 'bg-indigo-50' : 'hover:bg-gray-50'
              }`}
              onMouseDown={() => select(airport)}
              onMouseEnter={() => setHighlighted(i)}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-indigo-600 w-8 shrink-0">{airport.iata}</span>
                <div>
                  <span className="text-sm font-medium text-gray-900">{airport.city}</span>
                  <span className="text-xs text-gray-400 ml-1">· {airport.country}</span>
                  <p className="text-xs text-gray-400 leading-tight">{airport.name}</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
