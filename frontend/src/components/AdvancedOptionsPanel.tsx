import React, { useState } from 'react';

interface AdvancedOptionsPanelProps {
  useRag: boolean;
  onUseRagChange: (value: boolean) => void;
}

export const AdvancedOptionsPanel: React.FC<AdvancedOptionsPanelProps> = ({
  useRag,
  onUseRagChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-border">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left px-4 py-3 hover:bg-surface/30 transition-colors"
        aria-expanded={isExpanded}
        aria-controls="advanced-options-content"
      >
        <span className="font-mono text-[9px] tracking-widest uppercase text-dim">
          Advanced Options
        </span>
        <span className="font-mono text-[10px] text-faint">
          {isExpanded ? '▲' : '▼'}
        </span>
      </button>

      {isExpanded && (
        <div id="advanced-options-content" className="px-4 pb-4 pt-2 border-t border-border space-y-4">
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint">Historical Context Mode</p>

          <div className="space-y-3">
            {/* RAG */}
            <label className="flex items-start gap-3 cursor-pointer group">
              <div
                className={`w-4 h-4 border shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                  useRag ? 'border-gold bg-gold/10' : 'border-border'
                }`}
                onClick={() => onUseRagChange(true)}
              >
                {useRag && <span className="text-gold text-[10px] leading-none">✓</span>}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] tracking-wider text-ink">Smart Search</span>
                  <span className="font-mono text-[9px] border border-success/50 text-success px-1.5 py-0.5 tracking-wider">
                    Recommended
                  </span>
                </div>
                <p className="font-body text-xs text-dim mt-0.5">
                  AI finds only the most relevant historical events — faster with focused context.
                </p>
              </div>
            </label>

            {/* Legacy */}
            <label className="flex items-start gap-3 cursor-pointer group">
              <div
                className={`w-4 h-4 border shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                  !useRag ? 'border-gold bg-gold/10' : 'border-border'
                }`}
                onClick={() => onUseRagChange(false)}
              >
                {!useRag && <span className="text-gold text-[10px] leading-none">✓</span>}
              </div>
              <div className="flex-1">
                <span className="font-mono text-[10px] tracking-wider text-ink">Full Context</span>
                <p className="font-body text-xs text-dim mt-0.5">
                  Loads all historical data from the time period — more comprehensive but slower.
                </p>
              </div>
            </label>
          </div>

          <div className="pt-3 border-t border-border">
            <p className="font-body text-xs text-faint italic">
              Smart Search uses semantic retrieval for ~99% token reduction while maintaining generation quality.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
