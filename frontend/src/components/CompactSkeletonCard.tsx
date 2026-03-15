/**
 * Compact Skeleton Card Component
 *
 * Scannable skeleton card designed for 2-column library grid.
 */

import React, { useState, useEffect, useRef } from 'react';
import { SkeletonStatus } from '../types';
import type { Skeleton } from '../types';

interface CompactSkeletonCardProps {
  skeleton: Skeleton;
  onClick: () => void;
  onDelete: () => void;
  onGenerate: () => void;
  isDeleting: boolean;
  isGenerating: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  [SkeletonStatus.PENDING]:          'border-warning/50 text-warning',
  [SkeletonStatus.EDITING]:          'border-quantum/50 text-quantum',
  [SkeletonStatus.APPROVED]:         'border-success/50 text-success',
  [SkeletonStatus.REPORT_GENERATED]: 'border-gold/50 text-gold',
};

const STATUS_LABEL: Record<string, string> = {
  [SkeletonStatus.PENDING]:          'Pending Review',
  [SkeletonStatus.EDITING]:          'Editing',
  [SkeletonStatus.APPROVED]:         'Approved',
  [SkeletonStatus.REPORT_GENERATED]: 'Report Generated',
};

const SKELETON_TYPE_LABEL: Record<string, string> = {
  timeline_draft:  'Timeline Draft',
  extension_draft: 'Extension Draft',
  branch_draft:    'Branch Draft',
};

const SCENARIO_LABEL: Record<string, string> = {
  local_deviation:       'Local Deviation',
  global_deviation:      'Global Deviation',
  reality_fracture:      'Reality Fracture',
  geological_shift:      'Geological Shift',
  external_intervention: 'External Intervention',
};

export const CompactSkeletonCard: React.FC<CompactSkeletonCardProps> = ({
  skeleton,
  onClick,
  onDelete,
  onGenerate,
  isDeleting,
  isGenerating,
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

  const statusStyle = STATUS_STYLE[skeleton.status] ?? 'border-border text-dim';
  const statusLabel = STATUS_LABEL[skeleton.status] ?? skeleton.status;

  return (
    <div
      className="bg-parchment border border-border cursor-pointer transition-all duration-200 hover:border-gold-dim corner-brackets"
      onClick={onClick}
      onMouseEnter={() => setShowMenu(true)}
      onMouseLeave={() => { if (!menuOpen) setShowMenu(false); }}
    >
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          {/* Tags row */}
          <div className="flex items-center gap-1.5 flex-wrap flex-1">
            {skeleton.scenario_type && (
              <span className="font-mono text-[9px] tracking-wider border border-border text-dim px-1.5 py-0.5">
                {SCENARIO_LABEL[skeleton.scenario_type] ?? skeleton.scenario_type}
              </span>
            )}
            <span className="font-mono text-[9px] tracking-wider border border-border text-dim px-1.5 py-0.5">
              {SKELETON_TYPE_LABEL[skeleton.skeleton_type] ?? skeleton.skeleton_type}
            </span>
            <span className={`font-mono text-[9px] tracking-wider border px-1.5 py-0.5 ${statusStyle}`}>
              {statusLabel}
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
              <div className="absolute right-0 top-7 z-20 w-40 bg-parchment border border-border shadow-[var(--shadow-panel)] py-1">
                <button
                  onClick={(e) => { e.stopPropagation(); onGenerate(); setMenuOpen(false); }}
                  disabled={isGenerating}
                  className="w-full px-3 py-2 text-left font-mono text-[10px] tracking-wider text-gold hover:bg-gold/10 transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isGenerating ? (
                    <>
                      <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Generating...
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3l14 9-14 9V3z" />
                      </svg>
                      Generate
                    </>
                  )}
                </button>
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
        {skeleton.deviation_description && (
          <p className="font-body text-sm text-dim line-clamp-2 leading-relaxed">
            {skeleton.deviation_description}
          </p>
        )}
      </div>

      {/* Metadata footer */}
      <div className="px-4 py-2.5 border-t border-border flex items-center justify-between">
        <div className="flex items-center gap-3 font-mono text-[9px] tracking-wider text-faint">
          {skeleton.deviation_date && <span>{skeleton.deviation_date}</span>}
          <span className="text-border">|</span>
          <span className="text-gold-dim">{skeleton.events.length} event{skeleton.events.length !== 1 ? 's' : ''}</span>
        </div>
        <span className="font-mono text-[9px] text-faint">{formatDate(skeleton.generated_at)}</span>
      </div>
    </div>
  );
};
