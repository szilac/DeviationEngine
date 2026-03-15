import React from 'react';
import { ScenarioType, NarrativeMode } from '../../types';
import { SCENARIO_ICONS, WORKFLOW_CONFIG, NARRATIVE_MODE_CONFIG } from '../../styles/wizard';

interface ReviewSummaryProps {
  workflowType: 'direct' | 'skeleton';
  scenarioType: ScenarioType;
  deviationDate: string;
  deviationDescription: string;
  simulationYears: number;
  narrativeMode?: NarrativeMode;
  customPov?: string;
  onEditStep: (stepNumber: number) => void;
}

const ReviewSummary: React.FC<ReviewSummaryProps> = ({
  workflowType,
  scenarioType,
  deviationDate,
  deviationDescription,
  simulationYears,
  narrativeMode,
  customPov,
  onEditStep,
}) => {
  const scenarioIcon = SCENARIO_ICONS[scenarioType as keyof typeof SCENARIO_ICONS];
  const workflowConfig = WORKFLOW_CONFIG[workflowType];

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const truncateText = (text: string, maxLength: number): string =>
    text.length <= maxLength ? text : text.substring(0, maxLength) + '…';

  const getEstimatedTime = (): string => {
    if (workflowType === 'skeleton') return '30–60 seconds';
    if (!narrativeMode) return '60 seconds';
    return NARRATIVE_MODE_CONFIG[narrativeMode as keyof typeof NARRATIVE_MODE_CONFIG].estimatedTime.replace('~', '');
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="text-center pb-5 border-b border-border">
        <h2 className="font-display text-2xl text-ink mb-1">Review Configuration</h2>
        <p className="font-body text-sm text-dim">Confirm your settings before generating</p>
      </div>

      {/* Section 1: Workflow & Scenario */}
      <div className="border border-border bg-surface/30 p-5 corner-brackets">
        <div className="flex items-start justify-between mb-3">
          <span className="font-mono text-[9px] tracking-widest uppercase text-dim">Workflow & Scenario</span>
          <button
            onClick={() => onEditStep(0)}
            className="font-mono text-[9px] tracking-widest uppercase border border-gold-dim text-gold-dim px-2 py-1 hover:border-gold hover:text-gold transition-colors"
          >
            Edit
          </button>
        </div>

        <div className="space-y-2 font-body text-sm">
          <div className="flex items-center gap-3">
            <span className="text-faint w-28 shrink-0">Workflow</span>
            <span className="text-ink">{workflowConfig.title}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-faint w-28 shrink-0">Scenario Type</span>
            <span className="text-ink">{scenarioIcon.label}</span>
          </div>
        </div>
      </div>

      {/* Section 2: Deviation Details */}
      <div className="border border-border bg-surface/30 p-5 corner-brackets">
        <div className="flex items-start justify-between mb-3">
          <span className="font-mono text-[9px] tracking-widest uppercase text-dim">Deviation Details</span>
          <button
            onClick={() => onEditStep(1)}
            className="font-mono text-[9px] tracking-widest uppercase border border-gold-dim text-gold-dim px-2 py-1 hover:border-gold hover:text-gold transition-colors"
          >
            Edit
          </button>
        </div>

        <div className="space-y-2 font-body text-sm">
          <div className="flex items-start gap-3">
            <span className="text-faint w-28 shrink-0">Date</span>
            <span className="text-ink">{formatDate(deviationDate)}</span>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-faint w-28 shrink-0">Description</span>
            <span className="text-ink flex-1" title={deviationDescription}>
              {truncateText(deviationDescription, 150)}
            </span>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-faint w-28 shrink-0">Duration</span>
            <span className="text-ink">{simulationYears} year{simulationYears !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      {/* Section 3: Narrative (direct only) */}
      {workflowType === 'direct' && narrativeMode && (
        <div className="border border-border bg-surface/30 p-5 corner-brackets">
          <div className="flex items-start justify-between mb-3">
            <span className="font-mono text-[9px] tracking-widest uppercase text-dim">Narrative Settings</span>
            <button
              onClick={() => onEditStep(2)}
              className="font-mono text-[9px] tracking-widest uppercase border border-gold-dim text-gold-dim px-2 py-1 hover:border-gold hover:text-gold transition-colors"
            >
              Edit
            </button>
          </div>

          <div className="space-y-2 font-body text-sm">
            <div className="flex items-start gap-3">
              <span className="text-faint w-28 shrink-0">Mode</span>
              <span className="text-ink">
                {NARRATIVE_MODE_CONFIG[narrativeMode as keyof typeof NARRATIVE_MODE_CONFIG].title}
              </span>
            </div>
            {narrativeMode === NarrativeMode.ADVANCED_CUSTOM_POV && customPov && (
              <div className="flex items-start gap-3">
                <span className="text-faint w-28 shrink-0">Perspective</span>
                <span className="text-ink flex-1" title={customPov}>{truncateText(customPov, 100)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Generation summary */}
      <div className="border border-border bg-vellum p-5">
        <span className="font-mono text-[9px] tracking-widest uppercase text-dim block mb-3">
          What Will Be Generated
        </span>

        <div className="space-y-2 font-body text-sm">
          <div className="flex items-start gap-2">
            <span className="text-gold mt-0.5">—</span>
            <span className="text-dim">
              {workflowType === 'direct' ? 'Complete timeline generation' : 'Editable skeleton timeline'}
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-gold mt-0.5">—</span>
            <span className="text-dim">
              {workflowType === 'direct' ? 'Structured analytical report (8 sections)' : '15–25 key historical events'}
            </span>
          </div>
          {workflowType === 'direct' && narrativeMode && narrativeMode !== NarrativeMode.NONE && (
            <div className="flex items-start gap-2">
              <span className="text-gold mt-0.5">—</span>
              <span className="text-dim">Immersive narrative prose</span>
            </div>
          )}

          <div className="flex items-center gap-2 pt-3 mt-2 border-t border-border">
            <svg className="w-3.5 h-3.5 text-faint shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-mono text-[10px] text-faint">
              Est. time:{' '}
              <span className="text-gold">{getEstimatedTime()}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Warning */}
      <div className="flex items-start gap-3 p-4 border border-warning/40 bg-warning/5">
        <span className="font-mono text-[10px] text-warning shrink-0 mt-0.5">⚠</span>
        <div>
          <p className="font-mono text-[9px] tracking-widest uppercase text-warning mb-1">Important</p>
          <p className="font-body text-xs text-dim">
            Generation cannot be cancelled once started. Please review your configuration carefully before proceeding.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ReviewSummary;
