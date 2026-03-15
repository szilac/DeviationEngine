import React from 'react';
import { WORKFLOW_CONFIG } from '../../styles/wizard';
import Tooltip from '../Tooltip';

const WORKFLOW_TOOLTIPS: Record<'direct' | 'skeleton', React.ReactNode> = {
  direct: (
    <div className="p-1 space-y-3">
      <div className="flex items-baseline justify-between gap-4">
        <span className="font-mono text-[10px] tracking-widest uppercase text-gold">Direct Generation</span>
        <span className="font-mono text-[10px] text-faint">~1–2 minutes</span>
      </div>
      <div className="border-t border-border pt-3">
        <p className="font-body text-sm text-ink leading-snug mb-3">
          Best for quick exploration and testing ideas. The AI handles everything in a single pass with no review step.
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
          {[
            ['1', 'Fill in deviation date, description & years'],
            ['2', 'Select scenario type'],
            ['3', 'Choose a narrative mode'],
            ['4', 'Click Generate — done'],
          ].map(([n, s]) => (
            <div key={n} className="flex gap-2 items-start">
              <span className="font-mono text-[10px] text-gold-dim shrink-0 mt-0.5">{n}.</span>
              <span className="font-body text-xs text-dim leading-snug">{s}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-border pt-2 flex gap-4">
        {['Immediate results', 'No review step', 'Full narrative support'].map(tag => (
          <span key={tag} className="flex items-center gap-1 font-mono text-[10px] text-faint">
            <span className="text-gold-dim">✓</span> {tag}
          </span>
        ))}
      </div>
    </div>
  ),
  skeleton: (
    <div className="p-1 space-y-3">
      <div className="flex items-baseline justify-between gap-4">
        <span className="font-mono text-[10px] tracking-widest uppercase text-gold">Skeleton Workflow — Recommended</span>
        <span className="font-mono text-[10px] text-faint">~2–5 minutes</span>
      </div>
      <div className="border-t border-border pt-3">
        <p className="font-body text-sm text-ink leading-snug mb-3">
          Best for polished, coherent alternate histories. You review and refine the key events before committing to a full report. Once the skeleton is approved, you choose the narrative mode before generating.
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
          {[
            ['1', 'Generate skeleton: 15–25 key events (~30–60s)'],
            ['2', 'Review, edit, add, delete or reorder events'],
            ['3', 'Approve the skeleton when satisfied'],
            ['4', 'Generate full report (~1–2 minutes)'],
          ].map(([n, s]) => (
            <div key={n} className="flex gap-2 items-start">
              <span className="font-mono text-[10px] text-gold-dim shrink-0 mt-0.5">{n}.</span>
              <span className="font-body text-xs text-dim leading-snug">{s}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-border pt-2 flex gap-4">
        {['Classroom use', 'Serious writing', 'Publishable results'].map(tag => (
          <span key={tag} className="flex items-center gap-1 font-mono text-[10px] text-faint">
            <span className="text-gold-dim">✓</span> {tag}
          </span>
        ))}
      </div>
    </div>
  ),
};

interface WorkflowSelectorProps {
  value: 'direct' | 'skeleton';
  onChange: (value: 'direct' | 'skeleton') => void;
}

const WorkflowSelector: React.FC<WorkflowSelectorProps> = ({ value, onChange }) => {
  return (
    <div className="space-y-3">
      <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-4">Generation Workflow</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(['direct', 'skeleton'] as const).map((type) => {
          const config = WORKFLOW_CONFIG[type];
          const isSelected = value === type;

          return (
            <button
              key={type}
              type="button"
              onClick={() => onChange(type)}
              className={`
                text-left p-5 border-2 transition-all duration-200 corner-brackets
                ${isSelected
                  ? 'border-gold bg-surface/80'
                  : 'border-border bg-surface/20 hover:border-gold-dim hover:bg-surface/40 opacity-60 hover:opacity-80'
                }
              `}
              style={isSelected ? { boxShadow: '0 0 32px rgba(212,160,23,0.22), inset 0 0 24px rgba(212,160,23,0.04)' } : {}}
            >
              <div className="flex items-center justify-between gap-3 mb-3">
                <h4 className={`font-display text-lg ${isSelected ? 'text-gold' : 'text-ink'}`}>{config.title}</h4>
                <div className="flex items-center gap-2 shrink-0">
                  {isSelected && (
                    <span className="flex items-center gap-1 font-mono text-[9px] tracking-widest uppercase text-gold border border-gold px-1.5 py-0.5">
                      Selected
                    </span>
                  )}
                  <Tooltip content={WORKFLOW_TOOLTIPS[type]} position="bottom" maxWidth="520px">
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                      className="inline-flex items-center justify-center w-4 h-4 font-mono text-[9px] text-faint border border-border hover:border-gold-dim hover:text-gold transition-colors cursor-default"
                      aria-label="Workflow details"
                    >
                      ?
                    </span>
                  </Tooltip>
                </div>
              </div>

              <p className={`font-body text-sm mb-4 ${isSelected ? 'text-ink' : 'text-dim'}`}>{config.description}</p>

              <div className={`flex items-center gap-2 font-mono text-[10px] tracking-wider mb-3 ${isSelected ? 'text-gold' : 'text-gold-dim'}`}>
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{config.estimatedTime}</span>
              </div>

              <ul className="space-y-1">
                {config.features.map((feature, i) => (
                  <li key={i} className={`flex items-start gap-2 font-body text-xs ${isSelected ? 'text-dim' : 'text-faint'}`}>
                    <span className={`mt-0.5 shrink-0 ${isSelected ? 'text-gold-dim' : 'text-border'}`}>—</span>
                    {feature}
                  </li>
                ))}
              </ul>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowSelector;
