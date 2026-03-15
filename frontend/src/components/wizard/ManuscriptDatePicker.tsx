import React, { useMemo } from 'react';

interface ManuscriptDatePickerProps {
  value: string; // YYYY-MM-DD
  onChange: (date: string) => void;
  min?: string; // YYYY-MM-DD
  max?: string; // YYYY-MM-DD
  hasError?: boolean;
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function parseDate(value: string): { year: number; month: number; day: number } {
  if (!value) return { year: 1914, month: 6, day: 28 };
  const parts = value.split('-').map(Number);
  return {
    year: parts[0] || 1914,
    month: parts[1] || 6,
    day: parts[2] || 28,
  };
}

const chevron = (
  <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-dim pointer-events-none">
    <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
      <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  </span>
);

const ManuscriptDatePicker: React.FC<ManuscriptDatePickerProps> = ({
  value,
  onChange,
  min = '1880-01-01',
  max = '2004-12-31',
  hasError = false,
}) => {
  const { year, month, day } = parseDate(value);
  const minYear = parseInt(min.split('-')[0]);
  const maxYear = parseInt(max.split('-')[0]);
  const maxDays = daysInMonth(year, month);

  const decadeGroups = useMemo(() => {
    const groups: { decade: string; years: number[] }[] = [];
    for (let y = minYear; y <= maxYear; y++) {
      const decadeLabel = `${Math.floor(y / 10) * 10}s`;
      let group = groups.find(g => g.decade === decadeLabel);
      if (!group) {
        group = { decade: decadeLabel, years: [] };
        groups.push(group);
      }
      group.years.push(y);
    }
    return groups;
  }, [minYear, maxYear]);

  const emit = (y: number, m: number, d: number) => {
    const clampedDay = Math.min(d, daysInMonth(y, m));
    onChange(
      `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(clampedDay).padStart(2, '0')}`
    );
  };

  const borderClass = hasError ? 'border-rubric' : 'border-border';
  const selectClass = `w-full appearance-none bg-vellum border ${borderClass} text-ink font-mono text-base py-3 px-4 pr-8 focus:outline-none focus:border-gold transition-colors cursor-pointer`;

  return (
    <div className="flex gap-2">
      {/* Day */}
      <div className="w-[22%]">
        <div className="font-mono text-[9px] tracking-widest uppercase text-faint mb-1.5">Day</div>
        <div className="relative">
          <select
            value={day}
            onChange={e => emit(year, month, parseInt(e.target.value))}
            className={selectClass}
          >
            {Array.from({ length: maxDays }, (_, i) => i + 1).map(d => (
              <option key={d} value={d} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>
                {String(d).padStart(2, '0')}
              </option>
            ))}
          </select>
          {chevron}
        </div>
      </div>

      {/* Month */}
      <div className="flex-1">
        <div className="font-mono text-[9px] tracking-widest uppercase text-faint mb-1.5">Month</div>
        <div className="relative">
          <select
            value={month}
            onChange={e => emit(year, parseInt(e.target.value), day)}
            className={selectClass}
          >
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>
                {m}
              </option>
            ))}
          </select>
          {chevron}
        </div>
      </div>

      {/* Year */}
      <div className="w-[28%]">
        <div className="font-mono text-[9px] tracking-widest uppercase text-faint mb-1.5">Year</div>
        <div className="relative">
          <select
            value={year}
            onChange={e => emit(parseInt(e.target.value), month, day)}
            className={selectClass}
          >
            {decadeGroups.map(({ decade, years }) => (
              <optgroup
                key={decade}
                label={`— ${decade} —`}
                style={{ backgroundColor: '#271E0A', color: '#8a7040' }}
              >
                {years.map(y => (
                  <option key={y} value={y} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>
                    {y}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          {chevron}
        </div>
      </div>
    </div>
  );
};

export default ManuscriptDatePicker;
