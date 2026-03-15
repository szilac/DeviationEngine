import React from 'react';

export interface StepDefinition {
  id: number;
  title: string;
  icon?: React.ReactNode;
}

interface StepperProps {
  steps: StepDefinition[];
  currentStep: number;
  completedSteps: number[];
}

const Stepper: React.FC<StepperProps> = ({ steps, currentStep, completedSteps }) => {
  const getCircleStyle = (index: number): string => {
    if (completedSteps.includes(index)) return 'bg-gold border-gold text-vellum';
    if (index === currentStep) return 'bg-transparent border-gold text-gold';
    return 'bg-transparent border-faint text-faint';
  };

  const getTitleStyle = (index: number): string => {
    if (completedSteps.includes(index)) return 'text-gold';
    if (index === currentStep) return 'text-gold-2';
    return 'text-faint';
  };

  const getConnectorColor = (index: number): string => {
    if (completedSteps.includes(index)) return '#7A5C10';
    return '#5A4E30';
  };

  return (
    <div className="w-full mb-10">
      {/* Desktop & Tablet */}
      <div className="hidden sm:flex items-center justify-between w-full max-w-4xl mx-auto">
        {steps.map((step, index) => (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={`w-10 h-10 border-2 flex items-center justify-center transition-all duration-300 ${getCircleStyle(index)}`}
                style={index === currentStep ? { boxShadow: '0 0 12px rgba(212,160,23,0.3)' } : {}}
              >
                {completedSteps.includes(index) ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="font-mono text-sm">{index + 1}</span>
                )}
              </div>
              <span
                className={`mt-2 font-mono text-[9px] tracking-widest uppercase text-center max-w-[100px] transition-colors duration-300 ${getTitleStyle(index)}`}
              >
                {step.title}
              </span>
            </div>

            {index < steps.length - 1 && (
              <div
                className="flex-1 h-px mx-3 transition-colors duration-300"
                style={{ backgroundColor: getConnectorColor(index) }}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Mobile */}
      <div className="sm:hidden">
        <div className="flex items-center justify-center">
          {steps.map((step, index) => (
            <React.Fragment key={step.id}>
              <div
                className={`w-8 h-8 border-2 flex items-center justify-center transition-all duration-300 ${getCircleStyle(index)}`}
                style={index === currentStep ? { boxShadow: '0 0 10px rgba(212,160,23,0.3)' } : {}}
              >
                {completedSteps.includes(index) ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span className="font-mono text-xs">{index + 1}</span>
                )}
              </div>
              {index < steps.length - 1 && (
                <div
                  className="w-6 h-px mx-1 transition-colors duration-300"
                  style={{ backgroundColor: getConnectorColor(index) }}
                />
              )}
            </React.Fragment>
          ))}
        </div>
        <div className="text-center mt-3">
          <span className={`font-mono text-[9px] tracking-widest uppercase ${getTitleStyle(currentStep)}`}>
            {steps[currentStep]?.title}
          </span>
        </div>
      </div>
    </div>
  );
};

export default Stepper;
