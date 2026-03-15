import React from 'react';

interface StepperNavigationProps {
  currentStep: number;
  totalSteps: number;
  canGoNext: boolean;
  canGoBack: boolean;
  onNext: () => void;
  onBack: () => void;
  nextLabel?: string;
  isGenerating?: boolean;
}

const StepperNavigation: React.FC<StepperNavigationProps> = ({
  currentStep,
  totalSteps,
  canGoNext,
  canGoBack,
  onNext,
  onBack,
  nextLabel,
  isGenerating = false,
}) => {
  const getNextButtonLabel = (): string => {
    if (isGenerating) return 'Generating…';
    if (nextLabel) return nextLabel;
    if (currentStep === totalSteps - 1) return 'Generate Timeline';
    if (currentStep === totalSteps - 2) return 'Review Configuration';
    return 'Next';
  };

  return (
    <div className="flex justify-between items-center mt-6 pt-5 border-t border-border">
      {canGoBack ? (
        <button
          onClick={onBack}
          disabled={isGenerating}
          className="px-5 py-2 border border-border text-dim font-mono text-[11px] tracking-widest uppercase hover:border-gold-dim hover:text-ink transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Go to previous step"
        >
          ← Back
        </button>
      ) : (
        <div />
      )}

      <button
        onClick={onNext}
        disabled={!canGoNext || isGenerating}
        className={`
          px-6 py-2 font-mono text-[11px] tracking-widest uppercase flex items-center gap-2 transition-all duration-200
          ${canGoNext && !isGenerating
            ? 'border border-gold text-gold hover:bg-gold/10 hover:shadow-[var(--shadow-gold)]'
            : 'border border-faint text-faint cursor-not-allowed'
          }
        `}
        aria-label={currentStep === totalSteps - 1 ? 'Generate timeline' : 'Go to next step'}
      >
        {isGenerating && (
          <svg aria-hidden="true" focusable="false" className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        <span>{getNextButtonLabel()}</span>
      </button>
    </div>
  );
};

export default StepperNavigation;
