/**
 * Deviation Console Component (Wizard Redesign)
 *
 * Multi-step wizard for creating alternate history timelines.
 * Supports both direct generation and skeleton workflows.
 */

import React, { useState, useMemo, useEffect } from 'react';
import type { TimelineCreationRequest, SkeletonGenerationRequest } from '../types';
import { ScenarioType, NarrativeMode } from '../types';
import type { ScenarioExample } from '../data/scenarioExamples';
import { getDebugSettings } from '../services/api';

import Stepper from './Stepper';
import type { StepDefinition } from './Stepper';
import StepperNavigation from './StepperNavigation';
import WorkflowSelector from './wizard/WorkflowSelector';
import ScenarioTypePicker from './wizard/ScenarioTypePicker';
import ScenarioExamplePicker from './wizard/ScenarioExamplePicker';
import DeviationInputs from './wizard/DeviationInputs';
import NarrativeModeSelector from './wizard/NarrativeModeSelector';
import ReviewSummary from './wizard/ReviewSummary';
import { AdvancedOptionsPanel } from './AdvancedOptionsPanel';

interface DeviationConsoleProps {
  onSubmit: (request: TimelineCreationRequest) => void;
  onSkeletonSubmit: (request: SkeletonGenerationRequest) => void;
  isLoading: boolean;
  onBack?: () => void;
}

interface FormData {
  deviation_date: string;
  deviation_description: string;
  simulation_years: number;
  scenario_type: ScenarioType;
  narrative_mode: NarrativeMode;
  narrative_custom_pov: string;
  use_rag: boolean;
}

interface FormErrors {
  date?: string;
  description?: string;
}

const DeviationConsole: React.FC<DeviationConsoleProps> = ({
  onSubmit,
  onSkeletonSubmit,
  isLoading,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [workflowType, setWorkflowType] = useState<'direct' | 'skeleton'>('direct');
  const [selectedScenario, setSelectedScenario] = useState<string>('custom');

  const [formData, setFormData] = useState<FormData>({
    deviation_date: '',
    deviation_description: '',
    simulation_years: 5,
    scenario_type: ScenarioType.LOCAL_DEVIATION,
    narrative_mode: NarrativeMode.BASIC,
    narrative_custom_pov: '',
    use_rag: true,
  });

  useEffect(() => {
    const fetchDefaultMode = async () => {
      try {
        const response = await getDebugSettings();
        if (response.data) {
          const defaultMode = response.data.context_retrieval_mode === 'rag';
          setFormData(prev => ({ ...prev, use_rag: defaultMode }));
        }
      } catch (error) {
        console.error('Failed to fetch default context mode:', error);
      }
    };
    fetchDefaultMode();
  }, []);

  const [errors, setErrors] = useState<FormErrors>({});

  const totalSteps = workflowType === 'direct' ? 4 : 3;

  const steps: StepDefinition[] = useMemo(() => {
    const baseSteps = [
      { id: 1, title: 'Workflow & Scenario' },
      { id: 2, title: 'Deviation Details' },
    ];
    if (workflowType === 'direct') {
      return [...baseSteps, { id: 3, title: 'Narrative Config' }, { id: 4, title: 'Review & Generate' }];
    } else {
      return [...baseSteps, { id: 3, title: 'Review & Generate' }];
    }
  }, [workflowType]);

  const handleScenarioTypeChange = (newScenarioType: ScenarioType) => {
    setFormData(prev => ({ ...prev, scenario_type: newScenarioType, deviation_date: '', deviation_description: '', simulation_years: 5 }));
    setSelectedScenario('custom');
  };

  const handleScenarioSelect = (scenario: ScenarioExample | 'custom') => {
    if (scenario === 'custom') {
      setSelectedScenario('custom');
      setFormData(prev => ({ ...prev, deviation_date: '', deviation_description: '', simulation_years: 5 }));
    } else {
      setSelectedScenario(scenario.id);
      setFormData(prev => ({ ...prev, deviation_date: scenario.date, deviation_description: scenario.description, simulation_years: scenario.years }));
    }
  };

  const getValidationErrors = (): FormErrors => {
    const newErrors: FormErrors = {};
    switch (currentStep) {
      case 0: return {};
      case 1:
        if (!formData.deviation_date) {
          newErrors.date = 'Deviation date is required';
        } else {
          const date = new Date(formData.deviation_date);
          if (date < new Date('1880-01-01') || date > new Date('2004-12-31')) {
            newErrors.date = 'Date must be between 1880 and 2004';
          }
        }
        if (!formData.deviation_description) {
          newErrors.description = 'Deviation description is required';
        } else if (formData.deviation_description.length < 10) {
          newErrors.description = 'Description must be at least 10 characters';
        } else if (formData.deviation_description.length > 1500) {
          newErrors.description = 'Description must not exceed 1500 characters';
        }
        return newErrors;
      case 2:
        if (workflowType === 'direct' && formData.narrative_mode === NarrativeMode.ADVANCED_CUSTOM_POV && !formData.narrative_custom_pov.trim()) {
          return { description: 'Custom perspective is required for this narrative mode' };
        }
        return {};
      case 3: return {};
      default: return {};
    }
  };

  const isCurrentStepValid = (): boolean => Object.keys(getValidationErrors()).length === 0;

  const handleNext = () => {
    const validationErrors = getValidationErrors();
    if (Object.keys(validationErrors).length === 0) {
      setCompletedSteps([...completedSteps, currentStep]);
      setCurrentStep(currentStep + 1);
      setErrors({});
    } else {
      setErrors(validationErrors);
    }
  };

  const handleBack = () => {
    setCurrentStep(currentStep - 1);
    setErrors({});
  };

  const handleEditStep = (stepNumber: number) => {
    setCurrentStep(stepNumber);
    setErrors({});
  };

  const handleSubmit = () => {
    const validationErrors = getValidationErrors();
    if (Object.keys(validationErrors).length > 0) { setErrors(validationErrors); return; }

    if (workflowType === 'skeleton') {
      const skeletonRequest: SkeletonGenerationRequest = {
        deviation_date: formData.deviation_date,
        deviation_description: formData.deviation_description,
        simulation_years: formData.simulation_years,
        scenario_type: formData.scenario_type,
        use_rag: formData.use_rag,
      };
      onSkeletonSubmit(skeletonRequest);
    } else {
      const directRequest: TimelineCreationRequest = {
        deviation_date: formData.deviation_date,
        deviation_description: formData.deviation_description,
        simulation_years: formData.simulation_years,
        scenario_type: formData.scenario_type,
        narrative_mode: formData.narrative_mode,
        narrative_custom_pov: formData.narrative_mode === NarrativeMode.ADVANCED_CUSTOM_POV ? formData.narrative_custom_pov : undefined,
        use_rag: formData.use_rag,
      };
      onSubmit(directRequest);
    }
  };

  const getNextLabel = (): string | undefined => {
    if (currentStep === totalSteps - 1) return workflowType === 'direct' ? 'Generate Timeline' : 'Generate Skeleton';
    if (currentStep === totalSteps - 2) return 'Review Configuration';
    return undefined;
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-8">
            <WorkflowSelector
              value={workflowType}
              onChange={(value) => {
                setWorkflowType(value);
                setCurrentStep(0);
                setCompletedSteps([]);
              }}
            />
            <ScenarioTypePicker value={formData.scenario_type} onChange={handleScenarioTypeChange} />
          </div>
        );
      case 1:
        return (
          <div className="space-y-8">
            <ScenarioExamplePicker
              scenarioType={formData.scenario_type}
              selectedId={selectedScenario}
              onSelect={handleScenarioSelect}
            />
            <DeviationInputs
              deviationDate={formData.deviation_date}
              deviationDescription={formData.deviation_description}
              simulationYears={formData.simulation_years}
              onDateChange={(date) => setFormData({ ...formData, deviation_date: date })}
              onDescriptionChange={(desc) => setFormData({ ...formData, deviation_description: desc })}
              onYearsChange={(years) => setFormData({ ...formData, simulation_years: years })}
              errors={errors}
            />
          </div>
        );
      case 2:
        if (workflowType === 'skeleton') {
          return (
            <>
              <ReviewSummary
                workflowType={workflowType}
                scenarioType={formData.scenario_type}
                deviationDate={formData.deviation_date}
                deviationDescription={formData.deviation_description}
                simulationYears={formData.simulation_years}
                onEditStep={handleEditStep}
              />
              <div className="mt-6">
                <AdvancedOptionsPanel useRag={formData.use_rag} onUseRagChange={(value) => setFormData({ ...formData, use_rag: value })} />
              </div>
            </>
          );
        } else {
          return (
            <NarrativeModeSelector
              narrativeMode={formData.narrative_mode}
              customPov={formData.narrative_custom_pov}
              onModeChange={(mode) => setFormData({ ...formData, narrative_mode: mode })}
              onCustomPovChange={(pov) => setFormData({ ...formData, narrative_custom_pov: pov })}
            />
          );
        }
      case 3:
        return (
          <>
            <ReviewSummary
              workflowType={workflowType}
              scenarioType={formData.scenario_type}
              deviationDate={formData.deviation_date}
              deviationDescription={formData.deviation_description}
              simulationYears={formData.simulation_years}
              narrativeMode={formData.narrative_mode}
              customPov={formData.narrative_custom_pov}
              onEditStep={handleEditStep}
            />
            <div className="mt-6">
              <AdvancedOptionsPanel useRag={formData.use_rag} onUseRagChange={(value) => setFormData({ ...formData, use_rag: value })} />
            </div>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Stepper */}
      <Stepper steps={steps} currentStep={currentStep} completedSteps={completedSteps} />

      {/* Step Content */}
      <div className="bg-parchment border border-border p-8 corner-brackets">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <StepperNavigation
        currentStep={currentStep}
        totalSteps={totalSteps}
        canGoNext={isCurrentStepValid()}
        canGoBack={currentStep > 0}
        onNext={currentStep === totalSteps - 1 ? handleSubmit : handleNext}
        onBack={handleBack}
        nextLabel={getNextLabel()}
        isGenerating={isLoading}
      />
    </div>
  );
};

export default DeviationConsole;
