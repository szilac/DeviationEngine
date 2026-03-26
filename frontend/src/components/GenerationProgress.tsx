import type { StepState } from '../hooks/useGenerationProgress';

interface GenerationProgressProps {
  steps: StepState[];
}

export default function GenerationProgress({ steps }: GenerationProgressProps) {
  return (
    <div className="border border-gold/30 bg-gold/5 px-6 py-5 space-y-3">
      <p className="font-mono text-[10px] tracking-widest uppercase text-gold mb-4">
        Generating Timeline
      </p>
      {steps.map((step) => (
        <div key={step.key} className="flex items-center gap-3">
          <span className="shrink-0 w-4 flex justify-center">
            {step.status === 'completed' && (
              <span className="text-success text-xs">✓</span>
            )}
            {step.status === 'active' && (
              <span
                className="inline-block w-3 h-3 border border-gold border-t-transparent rounded-full animate-spin"
                aria-hidden="true"
              />
            )}
            {step.status === 'pending' && (
              <span className="w-1.5 h-1.5 rounded-full bg-faint" />
            )}
          </span>
          <span
            className={`font-body text-sm transition-colors ${
              step.status === 'active'
                ? 'text-gold'
                : step.status === 'completed'
                ? 'text-dim line-through decoration-dim/40'
                : 'text-faint'
            }`}
          >
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}
