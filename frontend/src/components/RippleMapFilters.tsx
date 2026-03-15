/**
 * RippleMapFilters
 *
 * Floating toolbar overlay for filtering the ripple map visualization.
 * Controls: domain toggles, confidence level, generation visibility, reset.
 */

import type { CausalDomain } from '../types';

// ─── Types ───────────────────────────────────────────────────────────────────

interface RippleMapFiltersProps {
  activeDomains: Set<CausalDomain>;
  onToggleDomain: (domain: CausalDomain) => void;
  generationIds: string[];
  activeGenerationIds: Set<string>;
  onToggleGeneration: (id: string) => void;
  onReset: () => void;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const ALL_DOMAINS: CausalDomain[] = [
  'political',
  'economic',
  'technological',
  'social',
  'cultural',
  'military',
];

// Manuscript palette — domain semantics mapped to design system tokens
const DOMAIN_COLOR: Record<CausalDomain, string> = {
  political:    '#C0392B', // rubric
  economic:     '#6A8040', // success (olive)
  technological:'#4FC3F7', // quantum
  social:       '#D4A017', // gold
  cultural:     '#B8820A', // warning (amber)
  military:     '#8B2218', // rubric-dim
};

// ─── Component ───────────────────────────────────────────────────────────────

export default function RippleMapFilters({
  activeDomains,
  onToggleDomain,
  generationIds,
  activeGenerationIds,
  onToggleGeneration,
  onReset,
}: RippleMapFiltersProps) {
  return (
    <div
      className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2 px-3 py-2 bg-parchment border border-border"
      style={{ maxWidth: 'calc(100% - 340px)' }}
    >
      {/* Domain toggles */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {ALL_DOMAINS.map((domain) => {
          const active = activeDomains.has(domain);
          const color = DOMAIN_COLOR[domain];
          return (
            <button
              key={domain}
              onClick={() => onToggleDomain(domain)}
              title={`Toggle ${domain}`}
              className="px-2 py-0.5 font-mono text-[9px] tracking-widest uppercase transition-colors"
              style={{
                color: active ? color : '#5A4E30',
                border: `1px solid ${active ? color + '80' : '#4A3D1A'}`,
                background: active ? `${color}10` : 'transparent',
                outline: 'none',
              }}
            >
              {domain}
            </button>
          );
        })}
      </div>

      {/* Generation toggles (only shown if multiple generations) */}
      {generationIds.length > 1 && (
        <>
          <div className="w-px h-4 bg-border mx-0.5" />
          <div className="flex items-center gap-1">
            <span className="font-mono text-[9px] text-faint mr-1">GEN</span>
            {generationIds.map((id, idx) => {
              const active = activeGenerationIds.has(id);
              return (
                <button
                  key={id}
                  onClick={() => onToggleGeneration(id)}
                  title={`Toggle generation ${idx + 1}`}
                  className="w-5 h-5 font-mono text-[9px] flex items-center justify-center transition-colors"
                  style={{
                    color: active ? '#D4A017' : '#5A4E30',
                    border: `1px solid ${active ? '#D4A017' : '#4A3D1A'}`,
                    background: active ? 'rgba(212,160,23,0.1)' : 'transparent',
                    outline: 'none',
                  }}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>
        </>
      )}

      {/* Divider */}
      <div className="w-px h-4 bg-border mx-0.5" />

      {/* Reset */}
      <button
        onClick={onReset}
        className="font-mono text-[9px] tracking-widest uppercase text-dim hover:text-gold transition-colors px-1"
        style={{ outline: 'none' }}
      >
        Reset
      </button>
    </div>
  );
}
