import React from 'react';
import { getCharacterCountStyle } from '../../styles/wizard';
import { InfoIcon } from '../Tooltip';
import ManuscriptDatePicker from './ManuscriptDatePicker';

interface DeviationInputsProps {
  deviationDate: string;
  deviationDescription: string;
  simulationYears: number;
  onDateChange: (date: string) => void;
  onDescriptionChange: (description: string) => void;
  onYearsChange: (years: number) => void;
  errors?: {
    date?: string;
    description?: string;
  };
}

const DeviationInputs: React.FC<DeviationInputsProps> = ({
  deviationDate,
  deviationDescription,
  simulationYears,
  onDateChange,
  onDescriptionChange,
  onYearsChange,
  errors,
}) => {
  const descriptionLength = deviationDescription.length;
  const maxLength = 1500;
  const sliderPct = ((simulationYears - 1) / 49) * 100;

  return (
    <div className="space-y-6">
      {/* Deviation Date */}
      <div>
        <div className="w-full md:w-[52%]">
          <div className="flex items-center gap-2 mb-1.5">
            <label htmlFor="deviation-date" className="font-mono text-[9px] tracking-widest uppercase text-dim">
              Deviation Date
            </label>
            <InfoIcon content="Select the historical date when the deviation occurs. Must be between 1880 and 2004 for accurate historical context." maxWidth="360px" />
          </div>

          <ManuscriptDatePicker
            value={deviationDate}
            onChange={onDateChange}
            min="1880-01-01"
            max="2004-12-31"
            hasError={!!errors?.date}
          />

          {errors?.date && (
            <p className="font-mono text-[10px] text-rubric mt-1">{errors.date}</p>
          )}

          <p className="font-body text-xs text-faint italic mt-1">1880–2004</p>
        </div>
      </div>

      {/* Simulation Duration */}
      <div>
          <div className="flex items-center gap-2 mb-1.5">
            <label htmlFor="simulation-years" className="font-mono text-[9px] tracking-widest uppercase text-dim">
              Simulation Duration —{' '}
              <span className="text-gold">{simulationYears} years</span>
            </label>
            <InfoIcon content="How many years to simulate after the deviation point." maxWidth="360px" />
          </div>

          <div className="relative pt-1 pb-5">
            <input
              id="simulation-years"
              type="range"
              min="1"
              max="50"
              value={simulationYears}
              onChange={(e) => onYearsChange(parseInt(e.target.value))}
              className="w-full h-1 appearance-none cursor-pointer slider-manuscript"
              style={{
                background: `linear-gradient(to right, #D4A017 0%, #D4A017 ${sliderPct}%, #4A3D1A ${sliderPct}%, #4A3D1A 100%)`,
              }}
            />

            <div className="relative text-xs text-faint mt-2 h-4">
              <span className="absolute font-mono text-[9px] -translate-x-1/2" style={{ left: '0%' }}>1</span>
              <span className="absolute font-mono text-[9px] -translate-x-1/2" style={{ left: '18.4%' }}>10</span>
              <span className="absolute font-mono text-[9px] -translate-x-1/2" style={{ left: '49%' }}>25</span>
              <span className="absolute font-mono text-[9px] -translate-x-1/2" style={{ left: '100%' }}>50</span>
            </div>
          </div>

          <p className="font-body text-xs text-faint italic">
            Recommended: 5–15 years focused, 20–50 years long-term impact
          </p>
      </div>

      {/* Description */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <label htmlFor="deviation-description" className="font-mono text-[9px] tracking-widest uppercase text-dim">
            Deviation Description
          </label>
          <InfoIcon content="Describe what changed in history at this point. Be specific about the event that differs from our timeline." maxWidth="360px" />
        </div>

        <textarea
          id="deviation-description"
          value={deviationDescription}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Describe what changed in history…"
          rows={6}
          maxLength={1500}
          required
          className={`
            w-full bg-vellum border text-ink px-3 py-2.5 font-body text-sm
            placeholder:text-faint focus:outline-none focus:border-gold
            transition-colors resize-none
            ${errors?.description ? 'border-rubric' : 'border-border'}
          `}
        />

        <div className="flex justify-between items-center mt-1">
          {errors?.description ? (
            <p className="font-mono text-[10px] text-rubric">{errors.description}</p>
          ) : (
            <p className="font-body text-xs text-faint italic">Minimum 10 characters, maximum 1500</p>
          )}
          <span className={getCharacterCountStyle(descriptionLength, maxLength)}>
            {descriptionLength}/{maxLength}
          </span>
        </div>
      </div>

      {/* Slider thumb styles */}
      <style>{`
        .slider-manuscript::-webkit-slider-thumb {
          appearance: none;
          width: 14px;
          height: 14px;
          background: #D4A017;
          border: none;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(212,160,23,0.4);
          transition: transform 0.15s;
        }
        .slider-manuscript::-webkit-slider-thumb:hover { transform: scale(1.2); }
        .slider-manuscript::-moz-range-thumb {
          width: 14px;
          height: 14px;
          background: #D4A017;
          border: none;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(212,160,23,0.4);
          transition: transform 0.15s;
        }
        .slider-manuscript::-moz-range-thumb:hover { transform: scale(1.2); }
        @media (prefers-reduced-motion: reduce) {
          .slider-manuscript::-webkit-slider-thumb,
          .slider-manuscript::-moz-range-thumb {
            transition: none;
          }
          .slider-manuscript::-webkit-slider-thumb:hover,
          .slider-manuscript::-moz-range-thumb:hover {
            transform: none;
          }
        }
      `}</style>
    </div>
  );
};

export default DeviationInputs;
