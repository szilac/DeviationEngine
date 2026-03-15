import { useState, useEffect } from 'react';
import type { ImagePromptSkeleton, ImagePrompt, ImagePromptUpdate, Timeline } from '../types';
import { ImageUtils, ImagePromptSkeletonStatus } from '../types';
import {
  getImagePromptSkeleton,
  updateImagePrompts,
  approveImagePromptSkeleton,
  generateImages,
} from '../services/api';

interface ImagePromptEditorProps {
  skeletonId: string;
  timeline: Timeline;
  onComplete?: () => void;
  onCancel?: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  [ImagePromptSkeletonStatus.PENDING]:    'border-gold-dim text-gold',
  [ImagePromptSkeletonStatus.EDITING]:    'border-gold-dim text-gold',
  [ImagePromptSkeletonStatus.APPROVED]:   'border-success text-success',
  [ImagePromptSkeletonStatus.GENERATING]: 'border-gold text-gold',
};

const inputClass =
  'w-full bg-transparent border border-border text-ink font-body text-sm px-3 py-2 ' +
  'placeholder:text-faint placeholder:font-mono placeholder:text-[10px] ' +
  'focus:outline-none focus:border-gold-dim disabled:opacity-40 disabled:cursor-not-allowed transition-colors';

const labelClass = 'font-mono text-[10px] tracking-widest uppercase text-dim block mb-1.5';

const ImagePromptEditor = ({ skeletonId, timeline, onComplete, onCancel }: ImagePromptEditorProps) => {
  const [skeleton, setSkeleton] = useState<ImagePromptSkeleton | null>(null);
  const [prompts, setPrompts] = useState<ImagePrompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

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
        setPrompts(ImageUtils.sortPromptsByOrder(response.data.prompts));
      }
    } catch (_err) {
      setError('Failed to load image prompt skeleton');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!skeleton) return;
    setIsSaving(true);
    setError(null);
    try {
      const promptsUpdate: ImagePromptUpdate[] = prompts.map((prompt, index) => ({
        id: null,
        prompt_text: prompt.prompt_text,
        event_year: prompt.event_year,
        title: prompt.title,
        description: prompt.description,
        prompt_order: index,
        style_notes: prompt.style_notes,
        is_user_modified: prompt.is_user_modified || false,
      }));
      const response = await updateImagePrompts(skeletonId, {
        prompts_update: promptsUpdate,
        deleted_prompt_indices: [],
      });
      if (response.error) {
        setError(`Failed to save changes: ${response.error.message}`);
      } else if (response.data) {
        setSkeleton(response.data);
        setPrompts(ImageUtils.sortPromptsByOrder(response.data.prompts));
        setEditingIndex(null);
      }
    } catch (_err) {
      setError('Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!skeleton) return;
    setIsApproving(true);
    setError(null);
    try {
      const response = await approveImagePromptSkeleton(skeletonId);
      if (response.error) {
        setError(`Failed to approve: ${response.error.message}`);
      } else if (response.data) {
        setSkeleton(response.data);
      }
    } catch (_err) {
      setError('Failed to approve skeleton');
    } finally {
      setIsApproving(false);
    }
  };

  const handleGenerateImages = async () => {
    if (!skeleton) return;
    setIsGenerating(true);
    setError(null);
    try {
      const response = await generateImages(skeletonId);
      if (response.error) {
        setError(`Failed to generate images: ${response.error.message}`);
      } else {
        if (onComplete) onComplete();
      }
    } catch (_err) {
      setError('Failed to generate images');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUpdatePrompt = (index: number, field: keyof ImagePrompt, value: any) => {
    setPrompts((prev) =>
      prev.map((prompt, i) =>
        i === index ? { ...prompt, [field]: value, is_user_modified: true } : prompt
      )
    );
  };

  const handleDeletePrompt = (index: number) => {
    if (confirm('Are you sure you want to delete this prompt?')) {
      setPrompts((prev) => prev.filter((_, i) => i !== index));
    }
  };

  const handleAddPrompt = () => {
    const newPrompt: ImagePrompt = {
      prompt_text: '',
      event_year: 0,
      title: 'New Image',
      description: null,
      prompt_order: prompts.length,
      style_notes: null,
      is_user_modified: true,
    };
    setPrompts((prev) => [...prev, newPrompt]);
    setEditingIndex(prompts.length);
  };

  const getAbsoluteYear = (eventYear: number | null): string => {
    if (eventYear === null) return 'Unknown';
    const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
    return `${deviationYear + eventYear}`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <span className="w-6 h-6 border border-gold border-t-transparent animate-spin" />
        <p className="font-mono text-[10px] tracking-widest uppercase text-dim">Loading image prompts…</p>
      </div>
    );
  }

  if (error && !skeleton) {
    return (
      <div className="p-6 space-y-4">
        <div className="border border-rubric-dim px-4 py-2.5">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
        </div>
        <button
          onClick={loadSkeleton}
          className="px-5 py-2 font-mono text-[10px] tracking-widest uppercase border border-gold text-gold hover:bg-gold/10 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!skeleton) return null;

  const canEdit     = ImageUtils.canEdit(skeleton);
  const canApprove  = ImageUtils.canApprove(skeleton);
  const canGenerate = ImageUtils.canGenerateImages(skeleton);
  const statusStyle = STATUS_STYLES[skeleton.status] ?? 'border-border text-dim';

  return (
    <div className="text-ink">

      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-xl text-ink mb-1">Edit Image Prompts</h2>
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint">
            {prompts.length} prompts
            {skeleton.focus_areas && skeleton.focus_areas.length > 0 && (
              <> · Focus: {skeleton.focus_areas.join(', ')}</>
            )}
            {skeleton.model_provider && (
              <> · {skeleton.model_provider} / {skeleton.model_name}</>
            )}
          </p>
        </div>
        <span className={`font-mono text-[9px] tracking-widest uppercase border px-2 py-1 shrink-0 ${statusStyle}`}>
          {skeleton.status}
        </span>
      </div>

      {/* Inline error */}
      {error && (
        <div className="mx-6 mt-4 border border-rubric-dim px-4 py-2.5">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
        </div>
      )}

      {/* Prompt list */}
      <div className="space-y-4 p-6 pb-24">
        {prompts.map((prompt, index) => (
          <div
            key={index}
            className={`border transition-colors ${
              editingIndex === index ? 'border-gold-dim' : 'border-border'
            }`}
            onClick={() => setEditingIndex(index)}
          >
            {/* Prompt header */}
            <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3 border-b border-border">
              <div className="flex-1 min-w-0">
                <input
                  type="text"
                  value={prompt.title}
                  onChange={(e) => handleUpdatePrompt(index, 'title', e.target.value)}
                  disabled={!canEdit}
                  className="w-full bg-transparent text-ink font-display text-base border-b border-transparent hover:border-gold-dim focus:border-gold-dim focus:outline-none disabled:hover:border-transparent transition-colors"
                  placeholder="Image title"
                />
                {prompt.event_year !== null && (
                  <p className="font-mono text-[9px] tracking-widest uppercase text-gold mt-1">
                    Year {getAbsoluteYear(prompt.event_year)}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {prompt.is_user_modified && (
                  <span className="font-mono text-[9px] tracking-widest uppercase border border-gold-dim text-gold px-2 py-0.5">
                    Modified
                  </span>
                )}
                {canEdit && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeletePrompt(index); }}
                    className="font-mono text-[9px] tracking-widest uppercase text-faint hover:text-rubric transition-colors"
                    title="Delete prompt"
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>

            {/* Fields */}
            <div className="p-4 space-y-4">
              <div>
                <label className={labelClass}>Image Prompt</label>
                <textarea
                  value={prompt.prompt_text}
                  onChange={(e) => handleUpdatePrompt(index, 'prompt_text', e.target.value)}
                  disabled={!canEdit}
                  className={inputClass}
                  rows={4}
                  placeholder="Detailed prompt for image generation…"
                />
              </div>

              <div>
                <label className={labelClass}>
                  Description <span className="text-faint font-normal normal-case">(Optional)</span>
                </label>
                <textarea
                  value={prompt.description || ''}
                  onChange={(e) => handleUpdatePrompt(index, 'description', e.target.value || null)}
                  disabled={!canEdit}
                  className={inputClass}
                  rows={2}
                  placeholder="Brief context or caption…"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>
                    Style Notes <span className="text-faint font-normal normal-case">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={prompt.style_notes || ''}
                    onChange={(e) => handleUpdatePrompt(index, 'style_notes', e.target.value || null)}
                    disabled={!canEdit}
                    className={inputClass}
                    placeholder="e.g. '1920s documentary'"
                  />
                </div>
                <div>
                  <label className={labelClass}>Event Year (Relative)</label>
                  <input
                    type="number"
                    value={prompt.event_year ?? ''}
                    onChange={(e) =>
                      handleUpdatePrompt(
                        index,
                        'event_year',
                        e.target.value ? parseInt(e.target.value) : null
                      )
                    }
                    disabled={!canEdit}
                    className={inputClass}
                    placeholder="0 = deviation year"
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sticky action bar */}
      <div className="sticky bottom-0 bg-parchment border-t border-border px-6 py-4 flex items-center justify-between gap-4">
        <div>
          {canEdit && (
            <button
              onClick={handleAddPrompt}
              className="font-mono text-[10px] tracking-widest uppercase border border-border text-dim hover:border-gold-dim hover:text-ink px-4 py-2 transition-colors"
            >
              + Add Prompt
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="font-mono text-[10px] tracking-widest uppercase border border-border text-dim hover:border-gold-dim hover:text-ink px-4 py-2 transition-colors"
            >
              Cancel
            </button>
          )}

          {canEdit && (
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="font-mono text-[10px] tracking-widest uppercase border border-gold-dim text-gold hover:bg-gold/10 px-5 py-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving && <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />}
              {isSaving ? 'Saving…' : 'Save Changes'}
            </button>
          )}

          {canApprove && (
            <button
              onClick={handleApprove}
              disabled={isApproving}
              className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold hover:bg-gold/10 px-5 py-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isApproving && <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />}
              {isApproving ? 'Approving…' : 'Approve'}
            </button>
          )}

          {canGenerate && (
            <button
              onClick={handleGenerateImages}
              disabled={isGenerating}
              className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold hover:bg-gold/10 px-6 py-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isGenerating && <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />}
              {isGenerating ? 'Generating…' : '§ Generate Images'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ImagePromptEditor;
