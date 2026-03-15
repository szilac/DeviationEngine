import { useState, useEffect } from 'react';
import type { Timeline, Generation, ImagePromptSkeleton } from '../types';
import { getImagePromptSkeleton } from '../services/api';
import ImagePromptEditor from './ImagePromptEditor';

interface ImagePromptEditorModalProps {
  skeletonId: string;
  timeline: Timeline;
  generation: Generation;
  onComplete: () => void;
  onCancel: () => void;
}

const ImagePromptEditorModal = ({
  skeletonId,
  timeline,
  onComplete,
  onCancel,
}: ImagePromptEditorModalProps) => {
  const [skeleton, setSkeleton] = useState<ImagePromptSkeleton | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSkeleton();
  }, [skeletonId]);

  const loadSkeleton = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getImagePromptSkeleton(skeletonId);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setSkeleton(response.data);
      }
    } catch (_err) {
      setError('Failed to load image prompt skeleton');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div className="bg-parchment border border-border shadow-[var(--shadow-panel)] px-10 py-8 flex flex-col items-center gap-4">
          <span className="w-6 h-6 border border-gold border-t-transparent animate-spin" />
          <p className="font-mono text-[10px] tracking-widest uppercase text-dim">Loading image prompt editor…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div className="bg-parchment border border-border shadow-[var(--shadow-panel)] max-w-md w-full p-6 space-y-4">
          <h2 className="font-mono text-[10px] tracking-widest uppercase text-rubric">Error Loading Editor</h2>
          <div className="border border-rubric-dim px-4 py-2.5">
            <p className="font-mono text-[10px] text-rubric">{error}</p>
          </div>
          <div className="flex justify-end gap-3">
            <button
              onClick={onCancel}
              className="px-5 py-2 font-mono text-[10px] tracking-widest uppercase border border-border text-dim hover:border-gold-dim hover:text-ink transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={loadSkeleton}
              className="px-5 py-2 font-mono text-[10px] tracking-widest uppercase border border-gold text-gold hover:bg-gold/10 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!skeleton) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 overflow-y-auto bg-black/60">
      <div className="relative max-w-6xl w-full my-8">
        {/* Close button */}
        <div className="sticky top-0 flex justify-end mb-4 z-20">
          <button
            onClick={onCancel}
            className="px-3 py-2 bg-parchment border border-border text-dim hover:border-gold-dim hover:text-ink font-mono text-[10px] tracking-widest uppercase transition-colors"
            title="Close editor"
          >
            ✕ Close
          </button>
        </div>

        {/* Editor content */}
        <div className="bg-parchment border border-border shadow-[var(--shadow-panel)] overflow-hidden">
          <ImagePromptEditor
            skeletonId={skeletonId}
            timeline={timeline}
            onComplete={onComplete}
            onCancel={onCancel}
          />
        </div>
      </div>
    </div>
  );
};

export default ImagePromptEditorModal;
