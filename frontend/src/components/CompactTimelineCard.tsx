/**
 * Compact Timeline Card Component
 *
 * Scannable timeline card designed for 2-column library grid.
 */

import React, { useState, useEffect, useRef } from 'react';
import type { TimelineListItem } from '../types';

const SCENARIO_BADGE_COLORS: Record<string, string> = {
  local_deviation:       'text-gold-dim border-gold-dim/40',
  global_deviation:      'text-rubric-dim border-rubric-dim/40',
  reality_fracture:      'text-quantum border-quantum/30',
  geological_shift:      'text-success border-success/40',
  external_intervention: 'text-wave border-wave/30',
};

const formatScenarioLabel = (type: string) =>
  type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

interface CompactTimelineCardProps {
  timeline: TimelineListItem;
  onClick: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}

export const CompactTimelineCard: React.FC<CompactTimelineCardProps> = ({
  timeline,
  onClick,
  onDelete,
  isDeleting,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });

  return (
    <div
      className="bg-parchment border border-border cursor-pointer transition-all duration-200 hover:border-gold-dim hover:bg-surface/60 hover:shadow-[0_0_18px_rgba(212,160,23,0.12)] corner-brackets group"
      onClick={onClick}
      onMouseEnter={() => setShowMenu(true)}
      onMouseLeave={() => { if (!menuOpen) setShowMenu(false); }}
    >
      {/* Header */}
      <div className="p-5 pb-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-display text-base text-ink leading-snug truncate">
              {timeline.timeline_name || 'Unnamed Timeline'}
            </h3>
            <span className={`inline-block font-mono text-[8px] tracking-widest uppercase border px-1.5 py-0.5 mt-1 ${SCENARIO_BADGE_COLORS[timeline.scenario_type] ?? 'text-dim border-border'}`}>
              {formatScenarioLabel(timeline.scenario_type)}
            </span>
          </div>

          {/* Menu */}
          <div
            ref={menuRef}
            className={`relative shrink-0 transition-opacity ${showMenu || menuOpen ? 'opacity-100' : 'opacity-0'}`}
          >
            <button
              onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
              className="w-6 h-6 flex items-center justify-center text-faint hover:text-dim transition-colors"
              aria-label="More options"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
              </svg>
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-7 z-20 w-32 bg-parchment border border-border shadow-[var(--shadow-panel)] py-1">
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(); setMenuOpen(false); }}
                  disabled={isDeleting}
                  className="w-full px-3 py-2 text-left font-mono text-[10px] tracking-wider text-rubric hover:bg-rubric/10 transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isDeleting ? (
                    <>
                      <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Deleting...
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="font-body text-sm text-dim line-clamp-2 leading-relaxed">
          {timeline.root_deviation_description}
        </p>
      </div>

      {/* Metadata footer */}
      <div className="px-5 py-2.5 border-t border-border flex items-center justify-between">
        <div className="flex items-center gap-3 font-mono text-[9px] tracking-wider text-faint">
          <span>{timeline.root_deviation_date}</span>
          <span className="text-border">|</span>
          <span className="text-gold-dim">{timeline.generation_count} {timeline.generation_count !== 1 ? 'chronicles' : 'chronicle'}</span>
          {timeline.audio_script_count > 0 && (
            <>
              <span className="text-border">|</span>
              <span>{timeline.audio_script_count} audio</span>
            </>
          )}
        </div>
        <span className="font-mono text-[9px] text-faint">{formatDate(timeline.created_at)}</span>
      </div>
    </div>
  );
};
