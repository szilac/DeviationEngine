/**
 * Temporal Atlas Page
 *
 * Full-viewport alternate history visualization. Migrated from HomePage.
 * Users select timelines from a manuscript-styled sidebar; the D3 canvas
 * renders them simultaneously for comparison.
 *
 * Route: /atlas
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import BranchingTimeline from '../components/BranchingTimelineAdv';
import { getTimelines } from '../services/api';
import { ScenarioType } from '../types';
import type { TimelineListItem } from '../types';

// ── Types ────────────────────────────────────────────────────────────────────

interface AtlasFilters {
  scenarioTypes: ScenarioType[];
  yearFrom: number | null;
  yearTo: number | null;
}

// ── AtlasTimelineSelector ────────────────────────────────────────────────────

interface AtlasTimelineSelectorProps {
  timelines: TimelineListItem[];
  allTimelines: TimelineListItem[];
  visibleTimelineIds: string[];
  onVisibilityToggle: (id: string) => void;
  onViewReport: (id: string) => void;
  filters: AtlasFilters;
  onFiltersChange: (f: AtlasFilters) => void;
}

const SCENARIO_LABELS: Record<ScenarioType, string> = {
  [ScenarioType.LOCAL_DEVIATION]:       'Local Deviation',
  [ScenarioType.GLOBAL_DEVIATION]:      'Global Deviation',
  [ScenarioType.REALITY_FRACTURE]:      'Reality Fracture',
  [ScenarioType.GEOLOGICAL_SHIFT]:      'Geological Shift',
  [ScenarioType.EXTERNAL_INTERVENTION]: 'External Intervention',
};

const ALL_SCENARIO_TYPES = Object.values(ScenarioType);
const MAX_VISIBLE = 6;

const AtlasTimelineSelector: React.FC<AtlasTimelineSelectorProps> = ({
  timelines,
  allTimelines,
  visibleTimelineIds,
  onVisibilityToggle,
  onViewReport,
  filters,
  onFiltersChange,
}) => {
  const atCapacity = visibleTimelineIds.length >= MAX_VISIBLE;

  const toggleScenarioType = (type: ScenarioType) => {
    const updated = filters.scenarioTypes.includes(type)
      ? filters.scenarioTypes.filter(t => t !== type)
      : [...filters.scenarioTypes, type];
    onFiltersChange({ ...filters, scenarioTypes: updated });
  };

  const selectAll = () => {
    const ids = timelines.slice(0, MAX_VISIBLE).map(t => t.id);
    ids.forEach(id => { if (!visibleTimelineIds.includes(id)) onVisibilityToggle(id); });
  };

  const clearAll = () => {
    visibleTimelineIds.forEach(id => onVisibilityToggle(id));
  };

  return (
    <aside className="w-60 shrink-0 h-full flex flex-col border-r border-border bg-parchment overflow-hidden">
      {/* Filters */}
      <div className="p-4 border-b border-border shrink-0">
        <p className="rubric-label mb-3">§ Filters</p>

        <div className="space-y-1">
          {ALL_SCENARIO_TYPES.map(type => (
            <label key={type} className="flex items-center gap-2 cursor-pointer group">
              <div
                onClick={() => toggleScenarioType(type)}
                className={`w-3.5 h-3.5 border shrink-0 flex items-center justify-center transition-colors ${
                  filters.scenarioTypes.includes(type) ? 'border-gold bg-gold/15' : 'border-faint'
                }`}
              >
                {filters.scenarioTypes.includes(type) && (
                  <span className="text-gold text-[9px] leading-none">✓</span>
                )}
              </div>
              <span className="font-mono text-[9px] tracking-wider text-dim group-hover:text-ink transition-colors">
                {SCENARIO_LABELS[type]}
              </span>
            </label>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 mt-3">
          <div>
            <p className="font-mono text-[8px] tracking-wider text-faint mb-1">From</p>
            <input
              type="number"
              value={filters.yearFrom ?? ''}
              onChange={e => onFiltersChange({ ...filters, yearFrom: e.target.value ? parseInt(e.target.value) : null })}
              placeholder="1880"
              min="1880" max="2100"
              className="w-full bg-vellum border border-border text-ink font-mono text-[10px] px-2 py-1 focus:outline-none focus:border-gold [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>
          <div>
            <p className="font-mono text-[8px] tracking-wider text-faint mb-1">To</p>
            <input
              type="number"
              value={filters.yearTo ?? ''}
              onChange={e => onFiltersChange({ ...filters, yearTo: e.target.value ? parseInt(e.target.value) : null })}
              placeholder="2100"
              min="1880" max="2100"
              className="w-full bg-vellum border border-border text-ink font-mono text-[10px] px-2 py-1 focus:outline-none focus:border-gold [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>
        </div>
      </div>

      {/* Chronicle list */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 pb-2 flex items-center justify-between">
          <p className="rubric-label">§ Chronicles</p>
          <div className="flex gap-2">
            <button onClick={selectAll} className="font-mono text-[8px] tracking-wider text-faint hover:text-gold-dim transition-colors">All</button>
            <span className="text-faint text-[8px]">·</span>
            <button onClick={clearAll} className="font-mono text-[8px] tracking-wider text-faint hover:text-rubric-dim transition-colors">Clear</button>
          </div>
        </div>

        <div className="px-2 pb-4 space-y-0.5">
          {timelines.length === 0 ? (
            <p className="font-mono text-[9px] text-faint px-2 py-4 text-center">No timelines match filters</p>
          ) : (
            timelines.map(timeline => {
              const isVisible = visibleTimelineIds.includes(timeline.id);
              const isDisabled = !isVisible && atCapacity;
              const year = new Date(timeline.root_deviation_date).getFullYear();

              return (
                <div
                  key={timeline.id}
                  className={`flex items-start gap-2 px-2 py-2 cursor-pointer transition-all group ${
                    isVisible ? 'border-l-2 border-gold bg-surface/30' : 'border-l-2 border-transparent hover:bg-surface/20'
                  } ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                  onClick={() => !isDisabled && onVisibilityToggle(timeline.id)}
                >
                  {/* Checkbox */}
                  <div className={`w-3.5 h-3.5 border shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                    isVisible ? 'border-gold bg-gold/15' : 'border-faint'
                  }`}>
                    {isVisible && <span className="text-gold text-[9px] leading-none">✓</span>}
                  </div>

                  {/* Entry */}
                  <div className="flex-1 min-w-0">
                    <span className="font-mono text-[9px] text-rubric">{year}</span>
                    <p className="font-body text-xs text-ink leading-tight truncate mt-0.5">
                      {timeline.timeline_name || timeline.root_deviation_description}
                    </p>
                    <div className="flex items-center justify-between mt-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[8px] text-faint">{SCENARIO_LABELS[timeline.scenario_type as ScenarioType] || timeline.scenario_type}</span>
                        <span className="text-faint text-[8px]">·</span>
                        <span className="font-mono text-[8px] text-faint">{timeline.generation_count} gen{timeline.generation_count !== 1 ? 's' : ''}</span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); onViewReport(timeline.id); }}
                        className="font-mono text-[8px] tracking-widest uppercase text-gold-dim hover:text-gold border border-gold-dim/50 hover:border-gold-dim bg-surface/40 hover:bg-gold/10 px-2 py-0.5 transition-colors shrink-0"
                      >
                        Report →
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer: showing count */}
      <div className="px-4 py-2.5 border-t border-border shrink-0">
        <p className="font-mono text-[8px] tracking-wider text-faint text-center">
          {visibleTimelineIds.length} of {allTimelines.length} shown · max {MAX_VISIBLE}
        </p>
      </div>
    </aside>
  );
};

// ── TemporalAtlasPage ────────────────────────────────────────────────────────

const TemporalAtlasPage = () => {
  const navigate = useNavigate();

  const [allTimelines, setAllTimelines] = useState<TimelineListItem[]>([]);
  const [visibleTimelineIds, setVisibleTimelineIds] = useState<string[]>([]);
  const [filters, setFilters] = useState<AtlasFilters>({ scenarioTypes: [], yearFrom: null, yearTo: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filteredTimelines = useMemo(() => {
    return allTimelines.filter(timeline => {
      if (filters.scenarioTypes.length > 0 && !filters.scenarioTypes.includes(timeline.scenario_type)) return false;
      const year = new Date(timeline.root_deviation_date).getFullYear();
      if (filters.yearFrom !== null && year < filters.yearFrom) return false;
      if (filters.yearTo !== null && year > filters.yearTo) return false;
      return true;
    });
  }, [allTimelines, filters]);

  const visibleTimelines = useMemo(
    () => allTimelines.filter(t => visibleTimelineIds.includes(t.id)),
    [allTimelines, visibleTimelineIds]
  );

  useEffect(() => {
    const fetchAndInit = async () => {
      try {
        const response = await getTimelines();
        if (response.error) {
          setError(response.error.message || 'Failed to load timelines');
        } else if (response.data) {
          const sorted = response.data.sort((a: TimelineListItem, b: TimelineListItem) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
          setAllTimelines(sorted);
          setVisibleTimelineIds(sorted.slice(0, 6).map((t: TimelineListItem) => t.id));
        }
      } catch {
        setError('An unexpected error occurred while loading timelines');
      } finally {
        setLoading(false);
      }
    };
    fetchAndInit();
  }, []);

  const handleVisibilityToggle = (timelineId: string) => {
    setVisibleTimelineIds(prev => {
      if (prev.includes(timelineId)) return prev.filter(id => id !== timelineId);
      if (prev.length >= MAX_VISIBLE) return [...prev.slice(1), timelineId];
      return [...prev, timelineId];
    });
  };

  const handleTimelineClick = (timelineId: string) => {
    if (timelineId.startsWith('ground-truth:')) {
      navigate(`/ground-truth/${timelineId.replace('ground-truth:', '')}`);
    } else {
      navigate(`/reports/${timelineId}`);
    }
  };

  const handleReset = () => {
    setVisibleTimelineIds(allTimelines.slice(0, 6).map(t => t.id));
    setFilters({ scenarioTypes: [], yearFrom: null, yearTo: null });
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-56px)] bg-vellum flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="inline-block w-10 h-10 border border-gold border-t-transparent rounded-full animate-spin" />
          <p className="font-mono text-[9px] tracking-widest uppercase text-dim">Loading chronicles...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-56px)] bg-vellum flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-parchment border border-rubric/50 p-6 corner-brackets">
          <h3 className="font-mono text-[9px] tracking-widest uppercase text-rubric mb-2">Error</h3>
          <p className="font-body text-sm text-dim mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="font-mono text-[9px] tracking-widest uppercase border border-rubric/50 text-rubric px-3 py-1.5 hover:bg-rubric/10 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-56px)] flex flex-col overflow-hidden bg-vellum">
      {/* Controls bar */}
      <div className="shrink-0 flex items-center justify-between px-5 py-2 border-b border-border bg-parchment">
        <div className="flex items-center gap-3">
          <span className="font-display text-gold text-base leading-none">§ Temporal Atlas</span>
          <span className="text-faint font-mono text-[9px]">|</span>
          <span className="font-mono text-[9px] tracking-wider text-dim">
            Showing {visibleTimelineIds.length} of {allTimelines.length} chronicles
          </span>
        </div>

        <button
          onClick={handleReset}
          className="font-mono text-[9px] tracking-widest uppercase border border-border text-dim px-3 py-1.5 hover:border-gold-dim hover:text-ink transition-all"
        >
          Reset
        </button>
      </div>

      {/* Main area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <AtlasTimelineSelector
          timelines={filteredTimelines}
          allTimelines={allTimelines}
          visibleTimelineIds={visibleTimelineIds}
          onVisibilityToggle={handleVisibilityToggle}
          onViewReport={id => navigate(`/reports/${id}`)}
          filters={filters}
          onFiltersChange={setFilters}
        />

        {/* Canvas */}
        <div className="flex-1 overflow-hidden">
          {allTimelines.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-sm space-y-4">
                <p className="font-display text-2xl text-ink">No Chronicles Yet</p>
                <p className="font-body text-sm text-dim">Create your first alternate history timeline to begin exploring the atlas.</p>
                <button
                  onClick={() => navigate('/console')}
                  className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold px-5 py-2.5 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all"
                >
                  Define the Deviation
                </button>
              </div>
            </div>
          ) : visibleTimelines.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-sm space-y-2">
                <p className="font-display text-xl text-ink">No Chronicles Selected</p>
                <p className="font-body text-sm text-dim">Select timelines from the sidebar to visualize them on the atlas.</p>
              </div>
            </div>
          ) : (
            <BranchingTimeline
              selectedTimelines={visibleTimelines}
              onTimelineClick={handleTimelineClick}
              className="h-full bg-vellum"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default TemporalAtlasPage;
