import React from 'react';
import { ScenarioType } from '../../types';
import { SCENARIO_EXAMPLES } from '../../data/scenarioExamples';
import type { ScenarioExample } from '../../data/scenarioExamples';

interface ScenarioExamplePickerProps {
  scenarioType: ScenarioType;
  selectedId: string;
  onSelect: (scenario: ScenarioExample | 'custom') => void;
}

const ScenarioExamplePicker: React.FC<ScenarioExamplePickerProps> = ({
  scenarioType,
  selectedId,
  onSelect,
}) => {
  const scenarios = SCENARIO_EXAMPLES[scenarioType] || [];

  return (
    <div className="space-y-3">
      <p className="font-mono text-[9px] tracking-widest uppercase text-dim">Starting Point</p>

      <div className="overflow-x-auto overflow-y-hidden pb-3 -mx-1 px-1">
        <div className="grid grid-rows-2 grid-flow-col gap-3 min-w-min">
          {/* Custom Card */}
          <button
            type="button"
            onClick={() => onSelect('custom')}
            className={`
              flex-shrink-0 w-44 h-28 border border-dashed
              flex flex-col items-center justify-center
              transition-all duration-200
              ${selectedId === 'custom'
                ? 'border-gold bg-surface/60'
                : 'border-faint hover:border-gold-dim hover:bg-surface/30'
              }
            `}
            style={selectedId === 'custom' ? { boxShadow: '0 0 14px rgba(212,160,23,0.15)' } : {}}
          >
            <span className="font-mono text-2xl text-gold-dim mb-1">✎</span>
            <span className="font-mono text-[10px] tracking-widest uppercase text-ink">Custom</span>
            <span className="font-body text-xs text-faint mt-0.5">Define your own</span>
          </button>

          {/* Example Cards */}
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              type="button"
              onClick={() => onSelect(scenario)}
              className={`
                flex-shrink-0 w-44 h-28 border p-3
                text-left transition-all duration-200 flex flex-col
                ${selectedId === scenario.id
                  ? 'border-gold bg-surface/60'
                  : 'border-border bg-surface/30 hover:border-gold-dim hover:bg-surface/50'
                }
              `}
              style={selectedId === scenario.id ? { boxShadow: '0 0 14px rgba(212,160,23,0.15)' } : {}}
              title={scenario.description}
            >
              <h4 className="font-body text-xs font-semibold text-ink mb-1 line-clamp-2 leading-tight">
                {scenario.title}
              </h4>
              <div className="font-mono text-[10px] text-gold mb-1">
                {new Date(scenario.date).getFullYear()}
              </div>
              <p className="font-body text-xs text-dim line-clamp-2 flex-1">{scenario.description}</p>
            </button>
          ))}
        </div>
      </div>

      <p className="font-body text-xs text-faint italic">
        {selectedId === 'custom'
          ? 'Fill in the deviation details below to create a custom timeline.'
          : 'Selected example auto-fills fields below — edit as needed.'}
      </p>
    </div>
  );
};

export default ScenarioExamplePicker;
