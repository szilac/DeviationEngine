import React from 'react';
import { NarrativeMode } from '../../types';
import { NARRATIVE_MODE_CONFIG } from '../../styles/wizard';
import { InfoIcon } from '../Tooltip';

interface NarrativeModeSelectorProps {
  narrativeMode: NarrativeMode;
  customPov: string;
  onModeChange: (mode: NarrativeMode) => void;
  onCustomPovChange: (pov: string) => void;
}

const badgeClass = (badge: string): string => {
  if (badge === 'Recommended') return 'border-gold text-gold';
  if (badge === 'Fastest') return 'border-success text-success';
  return 'border-gold-dim text-gold-dim';
};

const NarrativeModeSelector: React.FC<NarrativeModeSelectorProps> = ({
  narrativeMode,
  customPov,
  onModeChange,
  onCustomPovChange,
}) => {
  const modes = Object.values(NarrativeMode);

  return (
    <div className="space-y-3">
      <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-4">Narrative Mode</p>

      <div className="space-y-2">
        {modes.map((mode) => {
          const config = NARRATIVE_MODE_CONFIG[mode as keyof typeof NARRATIVE_MODE_CONFIG];
          const isSelected = narrativeMode === mode;

          return (
            <button
              key={mode}
              type="button"
              onClick={() => onModeChange(mode)}
              className={`
                w-full text-left px-4 py-3.5 border transition-all duration-200
                ${isSelected
                  ? 'border-gold bg-surface/50'
                  : 'border-border bg-surface/20 hover:border-gold-dim hover:bg-surface/40'
                }
              `}
              style={isSelected ? { boxShadow: '0 0 12px rgba(212,160,23,0.15)' } : {}}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-display text-base text-ink">{config.title}</h4>
                    {config.badge && (
                      <span className={`font-mono text-[9px] tracking-widest uppercase border px-1.5 py-0.5 ${badgeClass(config.badge)}`}>
                        {config.badge}
                      </span>
                    )}
                  </div>
                  <p className="font-body text-sm text-dim">{config.description}</p>
                </div>

                <div className="flex items-center gap-1 font-mono text-[9px] tracking-wider text-faint shrink-0 mt-0.5">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{config.estimatedTime}</span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Custom POV textarea */}
      {narrativeMode === NarrativeMode.ADVANCED_CUSTOM_POV && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center gap-2 mb-1.5">
            <label htmlFor="custom-pov" className="font-mono text-[9px] tracking-widest uppercase text-dim">
              Custom Perspective
            </label>
            <InfoIcon content='Describe the viewpoint from which the story should be told. Examples: "A German soldier on the Western Front", "A journalist in 1920s Berlin"' />
          </div>

          <textarea
            id="custom-pov"
            value={customPov}
            onChange={(e) => onCustomPovChange(e.target.value)}
            placeholder={`e.g., "A German soldier on the Western Front"`}
            rows={3}
            required
            className="w-full bg-vellum border border-border text-ink px-3 py-2.5 font-body text-sm placeholder:text-faint focus:outline-none focus:border-gold transition-colors resize-none"
          />

          <p className="font-body text-xs text-faint italic mt-1">
            Specify a character perspective for the narrative
          </p>
        </div>
      )}
    </div>
  );
};

export default NarrativeModeSelector;
