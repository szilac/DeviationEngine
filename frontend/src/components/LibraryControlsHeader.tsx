/**
 * Library Controls Header Component
 *
 * Header section with management tools for timeline library.
 */

import type { ScenarioType } from '../types';
import { Link } from 'react-router-dom';

interface LibraryControlsHeaderProps {
  onCreateNew: () => void;
  onImport: () => void;
  isImporting: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  scenarioFilter: ScenarioType | 'all';
  onScenarioFilterChange: (type: ScenarioType | 'all') => void;
  sortBy: 'date_created' | 'name';
  onSortByChange: (sortBy: 'date_created' | 'name') => void;
}

export const LibraryControlsHeader: React.FC<LibraryControlsHeaderProps> = ({
  onImport,
  isImporting,
  searchQuery,
  onSearchChange,
  scenarioFilter,
  onScenarioFilterChange,
  sortBy,
  onSortByChange,
}) => {
  const selectClass = "bg-vellum border border-border text-dim font-mono text-[10px] tracking-wider px-3 py-2 focus:outline-none focus:border-gold transition-colors cursor-pointer appearance-none pr-6";

  return (
    <div className="bg-parchment border-b border-border px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
        {/* Left: Actions */}
        <div className="flex items-center gap-3">
          <Link
            to="/console"
            className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold px-4 py-2 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all"
          >
            + New Timeline
          </Link>

          <button
            onClick={onImport}
            disabled={isImporting}
            className="font-mono text-[10px] tracking-widest uppercase border border-border text-dim px-4 py-2 hover:border-gold-dim hover:text-ink transition-all flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isImporting ? (
              <>
                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Importing...
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Import
              </>
            )}
          </button>
        </div>

        {/* Right: Search / Filter / Sort */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative">
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search..."
              className="pl-8 pr-3 py-2 w-48 bg-vellum border border-border text-ink font-body text-sm placeholder:text-faint focus:outline-none focus:border-gold transition-colors"
            />
          </div>

          {/* Scenario Filter */}
          <div className="relative">
            <select
              value={scenarioFilter}
              onChange={(e) => onScenarioFilterChange(e.target.value as ScenarioType | 'all')}
              className={selectClass}
            >
              <option value="all">All Types</option>
              <option value="local_deviation">Local Deviation</option>
              <option value="global_deviation">Global Deviation</option>
              <option value="reality_fracture">Reality Fracture</option>
              <option value="geological_shift">Geological Shift</option>
              <option value="external_intervention">External Intervention</option>
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => onSortByChange(e.target.value as 'date_created' | 'name')}
              className={selectClass}
            >
              <option value="date_created">By Date</option>
              <option value="name">By Name</option>
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-faint" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};
