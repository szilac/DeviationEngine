/**
 * Extension Form Component
 *
 * Form for extending an existing timeline with additional years.
 */

import { useState } from 'react';
import type { Timeline } from '../types';
import { NarrativeMode } from '../types';
import { NARRATIVE_MODE_CONFIG } from '../styles/wizard';
import { InfoIcon } from './Tooltip';

interface ExtensionFormProps {
  onSubmit: (additionalYears: number, narrativeMode: NarrativeMode, customPov?: string, additionalContext?: string, useSkeletonWorkflow?: boolean) => void;
  isLoading: boolean;
  timeline: Timeline;
}

const ExtensionForm = ({ onSubmit, isLoading, timeline }: ExtensionFormProps) => {
  const [additionalYears, setAdditionalYears] = useState(5);
  const [narrativeMode, setNarrativeMode] = useState<NarrativeMode>(NarrativeMode.BASIC);
  const [narrativeCustomPov, setNarrativeCustomPov] = useState('');
  const [additionalContext, setAdditionalContext] = useState('');
  const [useSkeletonWorkflow, setUseSkeletonWorkflow] = useState(false);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(additionalYears, narrativeMode, narrativeCustomPov, additionalContext, useSkeletonWorkflow);
  };

  const totalYearsSimulated = timeline.generations.length > 0
    ? Math.max(...timeline.generations.map(g => g.end_year))
    : 0;
  const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
  const currentEndYear = deviationYear + totalYearsSimulated;
  const newEndYear = currentEndYear + additionalYears;

  const badgeClass = (badge?: string) => {
    if (badge === 'Recommended') return 'border-gold text-gold';
    if (badge === 'Fastest') return 'border-gold-dim text-gold-dim';
    return 'border-gold-dim text-gold-dim';
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 text-ink">

      {/* Timeline info row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="border border-border bg-surface/40 p-3">
          <p className="font-mono text-[10px] tracking-widest uppercase text-dim mb-2">Current Timeline</p>
          <div className="space-y-1 font-caption text-sm text-ink">
            <div>Start: {timeline.root_deviation_date}</div>
            <div>End: {currentEndYear}</div>
            <div className="text-dim">{totalYearsSimulated} years simulated</div>
          </div>
        </div>
        <div className="border border-gold-dim bg-surface/30 p-3">
          <p className="font-mono text-[10px] tracking-widest uppercase text-gold mb-2">After Extension</p>
          <div className="space-y-1 font-caption text-sm text-ink">
            <div>Start: {timeline.root_deviation_date}</div>
            <div>End: {newEndYear}</div>
            <div className="text-dim">{totalYearsSimulated + additionalYears} years simulated</div>
          </div>
        </div>
      </div>

      {/* Skeleton toggle + years slider */}
      <div className="border border-border bg-surface/40 p-4 space-y-4 md:space-y-0 md:flex md:items-center md:gap-8">

        {/* Skeleton toggle */}
        <label className="flex items-start gap-3 cursor-pointer md:flex-[0_0_auto]">
          <div
            role="checkbox"
            aria-checked={useSkeletonWorkflow}
            onClick={() => !isLoading && setUseSkeletonWorkflow(!useSkeletonWorkflow)}
            className={`mt-0.5 w-4 h-4 border flex items-center justify-center shrink-0 cursor-pointer transition-colors ${
              useSkeletonWorkflow ? 'border-gold bg-gold/20' : 'border-border'
            } ${isLoading ? 'opacity-40 cursor-not-allowed' : ''}`}
          >
            {useSkeletonWorkflow && (
              <span className="font-mono text-[10px] text-gold leading-none">✓</span>
            )}
          </div>
          <div>
            <div className="font-mono text-[10px] tracking-widest uppercase text-ink">
              Skeleton Workflow
            </div>
            <div className="font-caption text-xs text-dim mt-0.5 leading-snug max-w-[180px]">
              {useSkeletonWorkflow
                ? 'Review & edit key events before generating the full report.'
                : 'Generate directly — faster, no review step.'}
            </div>
          </div>
        </label>

        {/* Divider */}
        <div className="hidden md:block w-px h-12 bg-border" />

        {/* Years slider */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <label className="font-mono text-[10px] tracking-widest uppercase text-dim">
              Additional Years
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="number"
                min="1"
                max="30"
                value={additionalYears}
                onChange={(e) => setAdditionalYears(Number(e.target.value))}
                disabled={isLoading}
                className="w-12 bg-transparent border-b border-border text-center font-mono text-[10px] text-gold focus:outline-none focus:border-gold-dim disabled:opacity-40"
              />
              <span className="font-mono text-[9px] text-faint">yrs</span>
            </div>
          </div>
          <input
            type="range"
            min="1"
            max="30"
            value={additionalYears}
            onChange={(e) => setAdditionalYears(Number(e.target.value))}
            disabled={isLoading}
            className="w-full h-px cursor-pointer appearance-none bg-border disabled:opacity-40 slider-thumb-gold"
            style={{
              background: `linear-gradient(to right, var(--color-gold) 0%, var(--color-gold) ${((additionalYears - 1) / 29) * 100}%, var(--color-border) ${((additionalYears - 1) / 29) * 100}%, var(--color-border) 100%)`,
            }}
          />
          <p className="font-mono text-[9px] text-faint mt-2">
            {currentEndYear} → {newEndYear}
          </p>
        </div>
      </div>

      {/* Context + Narrative Mode */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">

        {/* Additional context */}
        <div className="flex flex-col">
          <label htmlFor="additional_context" className="font-mono text-[10px] tracking-widest uppercase text-dim mb-2">
            Additional Context <span className="text-faint font-normal normal-case">(Optional)</span>
          </label>
          <textarea
            id="additional_context"
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            rows={4}
            maxLength={2000}
            disabled={isLoading}
            placeholder="Provide circumstances or events to consider during the extension…"
            className="flex-1 w-full bg-transparent border border-border text-ink font-body text-sm px-3 py-2 placeholder:text-faint placeholder:font-mono placeholder:text-[10px] focus:outline-none focus:border-gold-dim disabled:opacity-40 resize-none transition-colors"
          />
          <div className="flex justify-between mt-1 font-mono text-[9px] text-faint">
            <span>Leave blank to extend based on existing timeline only</span>
            <span>{additionalContext.length}/2000</span>
          </div>
        </div>

        {/* Narrative mode cards */}
        <div className="border border-border bg-surface/40 p-4 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <p className="font-mono text-[10px] tracking-widest uppercase text-dim">Narrative Mode</p>
            <InfoIcon content="Choose how detailed and narrative-driven the extension report should be." />
          </div>

          <div className="space-y-2 flex-1">
            {Object.values(NarrativeMode).map((mode) => {
              const config = NARRATIVE_MODE_CONFIG[mode as keyof typeof NARRATIVE_MODE_CONFIG];
              const isSelected = narrativeMode === mode;

              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setNarrativeMode(mode as NarrativeMode)}
                  disabled={isLoading}
                  className={`w-full text-left p-3 border transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${
                    isSelected
                      ? 'border-gold bg-surface/50'
                      : 'border-border bg-surface/20 hover:border-gold-dim hover:bg-surface/40'
                  }`}
                  style={isSelected ? { boxShadow: '0 0 12px rgba(212,160,23,0.15)' } : {}}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <h4 className="font-display text-sm text-ink">{config?.title ?? mode}</h4>
                        {config?.badge && (
                          <span className={`font-mono text-[9px] tracking-widest uppercase border px-1.5 py-0.5 shrink-0 ${badgeClass(config.badge)}`}>
                            {config.badge}
                          </span>
                        )}
                      </div>
                      <p className="font-body text-xs text-dim">{config?.description}</p>
                    </div>
                    {config?.estimatedTime && (
                      <span className="font-mono text-[9px] text-faint shrink-0">{config.estimatedTime}</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {narrativeMode === NarrativeMode.ADVANCED_CUSTOM_POV && (
            <div className="border-t border-border pt-3">
              <div className="flex items-center gap-2 mb-1">
                <label htmlFor="narrative_custom_pov" className="font-mono text-[10px] tracking-widest uppercase text-dim">
                  Custom Perspective
                </label>
                <InfoIcon content='Describe the viewpoint from which the story should be told.' />
              </div>
              <textarea
                id="narrative_custom_pov"
                value={narrativeCustomPov}
                onChange={(e) => setNarrativeCustomPov(e.target.value)}
                rows={3}
                disabled={isLoading}
                placeholder='e.g., "A journalist in 1920s Berlin"'
                className="w-full bg-transparent border border-border text-ink font-body text-sm px-3 py-2 placeholder:text-faint focus:outline-none focus:border-gold-dim disabled:opacity-40 resize-none transition-colors"
              />
            </div>
          )}
        </div>
      </div>

      {/* Submit */}
      <div className="flex justify-end pt-1">
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-2.5 font-mono text-[10px] tracking-widest uppercase border border-gold text-gold hover:bg-gold/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading && <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />}
          {isLoading
            ? (useSkeletonWorkflow ? 'Generating Skeleton…' : 'Extending Timeline…')
            : (useSkeletonWorkflow ? 'Generate Skeleton' : 'Extend Timeline')}
        </button>
      </div>

      {isLoading && (
        <div className="border border-gold-dim bg-surface/30 px-4 py-3">
          <p className="font-mono text-[10px] tracking-widest uppercase text-gold mb-0.5">
            {useSkeletonWorkflow ? `Generating skeleton — ${additionalYears} years…` : `Extending timeline — ${additionalYears} years…`}
          </p>
          <p className="font-caption text-xs text-dim">
            {useSkeletonWorkflow
              ? 'Creating key events based on the existing timeline. You will review them next.'
              : 'This may take up to 2 minutes as the AI analyses the existing timeline.'}
          </p>
        </div>
      )}

      <style>{`
        .slider-thumb-gold::-webkit-slider-thumb {
          appearance: none;
          width: 14px;
          height: 14px;
          background: var(--color-gold, #d4a017);
          border-radius: 0;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(212,160,23,0.3);
          transition: transform 0.15s ease, box-shadow 0.15s ease;
          margin-top: -6px;
        }
        .slider-thumb-gold::-webkit-slider-thumb:hover {
          transform: scale(1.15);
          box-shadow: 0 0 16px rgba(212,160,23,0.5);
        }
        .slider-thumb-gold::-moz-range-thumb {
          width: 14px;
          height: 14px;
          background: var(--color-gold, #d4a017);
          border-radius: 0;
          border: none;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(212,160,23,0.3);
        }
      `}</style>
    </form>
  );
};

export default ExtensionForm;
