import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DeviationConsole from '../components/DeviationConsole';
import GenerationProgress from '../components/GenerationProgress';
import { useGenerationProgress } from '../hooks/useGenerationProgress';
import { generateTimeline, generateSkeleton } from '../services/api';
import type { TimelineCreationRequest, SkeletonGenerationRequest, ErrorResponse } from '../types';

function ConsolePage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [progressToken, setProgressToken] = useState<string | null>(null);
  const { steps } = useGenerationProgress(progressToken);
  const navigate = useNavigate();

  const handleSubmit = async (request: TimelineCreationRequest) => {
    const token = crypto.randomUUID();
    setProgressToken(token);
    setIsLoading(true);
    setError(null);
    try {
      const response = await generateTimeline({ ...request, progress_token: token });
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        navigate(`/reports/${response.data.id}`);
      }
    } catch (_err) {
      setError({ error: 'GenerationError', message: 'An unexpected error occurred during timeline generation. Please try again.' });
    } finally {
      setIsLoading(false);
      setProgressToken(null);
    }
  };

  const handleSkeletonSubmit = async (request: SkeletonGenerationRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await generateSkeleton(request);
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        navigate(`/skeleton-workflow?id=${response.data.id}`);
      }
    } catch (_err) {
      setError({ error: 'GenerationError', message: 'An unexpected error occurred while generating skeleton. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-vellum">
      <main className="container mx-auto px-4 py-12">
        <DeviationConsole
          onSubmit={handleSubmit}
          onSkeletonSubmit={handleSkeletonSubmit}
          isLoading={isLoading}
          onBack={() => navigate('/')}
        />

        {/* Generation Progress */}
        {isLoading && progressToken && (
          <div className="mt-8 max-w-4xl mx-auto">
            <GenerationProgress steps={steps} />
          </div>
        )}

        {/* Error Toast */}
        {error && (
          <div
            role="alert"
            className="fixed top-4 right-4 z-50 bg-parchment border border-rubric text-ink px-6 py-4 shadow-[var(--shadow-rubric)] max-w-md corner-brackets"
          >
            <div className="flex items-start gap-3">
              <span className="font-mono text-rubric text-sm shrink-0">ERR</span>
              <div className="flex-1">
                <h4 className="font-mono text-[10px] tracking-widest uppercase text-rubric mb-1">
                  {error.error}
                </h4>
                <p className="font-body text-sm text-ink/80">{error.message}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-dim hover:text-ink transition-colors font-mono text-lg leading-none"
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default ConsolePage;
