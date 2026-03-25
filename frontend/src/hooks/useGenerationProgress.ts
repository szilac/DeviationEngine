import { useState, useEffect } from 'react';

export interface StepState {
  key: string;
  label: string;
  status: 'pending' | 'active' | 'completed';
}

// Ordered step definitions — drives display order regardless of event arrival order
const STEP_DEFINITIONS = [
  { key: 'context_retrieval', label: 'Retrieving historical context' },
  { key: 'historian',         label: 'Analysing historical deviation' },
  { key: 'storyteller',       label: 'Generating narrative prose' },
  { key: 'saving',            label: 'Saving to library' },
];

export function useGenerationProgress(progressToken: string | null) {
  const [steps, setSteps] = useState<StepState[]>(
    STEP_DEFINITIONS.map(s => ({ ...s, status: 'pending' }))
  );
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    if (!progressToken) return;

    const es = new EventSource(`/api/timelines/progress/${progressToken}`);

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as {
        step: string;
        status?: 'started' | 'completed';
        label?: string;
      };

      if (event.step === 'done') {
        setSteps(prev =>
          prev.map(s => s.status === 'active' ? { ...s, status: 'completed' } : s)
        );
        setIsDone(true);
        es.close();
        return;
      }

      setSteps(prev =>
        prev.map(s => {
          if (s.key !== event.step) return s;
          if (event.status === 'started') return { ...s, status: 'active', label: event.label ?? s.label };
          if (event.status === 'completed') return { ...s, status: 'completed', label: event.label ?? s.label };
          return s;
        })
      );
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [progressToken]);

  return { steps, isDone };
}
