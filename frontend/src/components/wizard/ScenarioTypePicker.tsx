import React from 'react';
import { ScenarioType } from '../../types';
import { SCENARIO_ICONS } from '../../styles/wizard';
import Tooltip from '../Tooltip';

interface ScenarioTypePickerProps {
  value: ScenarioType;
  onChange: (value: ScenarioType) => void;
}

const ScenarioTypePicker: React.FC<ScenarioTypePickerProps> = ({ value, onChange }) => {
  const scenarioTypes = Object.values(ScenarioType);

  return (
    <div className="space-y-3 mt-6">
      <p className="font-mono text-[9px] tracking-widest uppercase text-dim">Scenario Type</p>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {scenarioTypes.map((scenarioType) => {
          const iconConfig = SCENARIO_ICONS[scenarioType as keyof typeof SCENARIO_ICONS];
          const isSelected = value === scenarioType;

          return (
            <Tooltip key={scenarioType} content={iconConfig.tooltip} position="bottom">
              <button
                type="button"
                onClick={() => onChange(scenarioType)}
                className={`
                  relative group border-2 transition-all duration-200 overflow-hidden
                  ${isSelected ? 'border-gold' : 'border-border hover:border-gold-dim'}
                `}
                style={isSelected ? { boxShadow: '0 0 16px rgba(212,160,23,0.25)' } : {}}
                aria-label={`Select ${iconConfig.label}`}
              >
                <div className="relative w-full h-full aspect-square">
                  <img
                    src={iconConfig.icon}
                    alt=""
                    aria-hidden="true"
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                  />
                </div>
                <div className={`px-1 py-1.5 text-center transition-colors ${isSelected ? 'bg-gold/15' : 'bg-black/30'}`}>
                  <span className={`font-mono text-[9px] tracking-widest uppercase ${isSelected ? 'text-gold' : 'text-dim'}`}>
                    {iconConfig.label}
                  </span>
                </div>
              </button>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
};

export default ScenarioTypePicker;
