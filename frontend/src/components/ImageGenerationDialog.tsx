import { useState } from 'react';
import type { Timeline } from '../types';
import { ImageUtils } from '../types';
import { generateImagePrompts } from '../services/api';

interface ImageGenerationDialogProps {
  timeline: Timeline;
  generationId: string;
  onSuccess: (skeletonId: string) => void;
  className?: string;
}

const ImageGenerationDialog = ({
  timeline,
  generationId,
  onSuccess,
  className,
}: ImageGenerationDialogProps) => {
  const [numImages, setNumImages] = useState<number>(10);
  const [selectedFocusAreas, setSelectedFocusAreas] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const focusAreas = ImageUtils.getValidFocusAreas();

  const handleToggleFocusArea = (area: string) => {
    setSelectedFocusAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await generateImagePrompts(
        timeline.id,
        generationId,
        numImages,
        selectedFocusAreas.length > 0 ? selectedFocusAreas : null
      );
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        onSuccess(response.data.id);
      }
    } catch {
      setError('Failed to generate image prompts');
    } finally {
      setIsGenerating(false);
    }
  };

  const selectedGeneration = timeline.generations.find(g => g.id === generationId);
  const deviationYear = parseInt(timeline.root_deviation_date.split('-')[0]);
  const genStart = selectedGeneration ? deviationYear + selectedGeneration.start_year : null;
  const genEnd = selectedGeneration ? deviationYear + selectedGeneration.end_year : null;
  const genSpan = selectedGeneration ? selectedGeneration.end_year - selectedGeneration.start_year + 1 : null;

  const sliderPct = ((numImages - 3) / 17) * 100;

  return (
    <div className={`space-y-5 text-ink ${className ?? ''}`}>
      {/* Error */}
      {error && (
        <div className="border border-rubric-dim px-3 py-2">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
        </div>
      )}

      {/* Context */}
      <div className="space-y-2">
        <div className="border border-border bg-surface/50 p-3">
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-1.5">Timeline Context</p>
          <p className="font-body text-sm text-dim leading-relaxed">
            {timeline.root_deviation_description}
          </p>
        </div>
        <div className="border border-border bg-surface/50 px-3 py-2 flex flex-wrap gap-x-4 gap-y-0.5 font-mono text-[10px]">
          <span><span className="text-gold">Deviation:</span> <span className="text-dim">{timeline.root_deviation_date}</span></span>
          {genStart && genEnd && (
            <span><span className="text-gold">Generation:</span> <span className="text-dim">{genStart}–{genEnd}</span></span>
          )}
          {genSpan && (
            <span><span className="text-gold">Span:</span> <span className="text-dim">{genSpan} years</span></span>
          )}
        </div>
      </div>

      {/* Count slider */}
      <div>
        <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">
          Number of Images <span className="text-gold ml-1">{numImages}</span>
        </label>
        <input
          type="range"
          min="3"
          max="20"
          value={numImages}
          onChange={(e) => setNumImages(parseInt(e.target.value))}
          disabled={isGenerating}
          className="w-full h-px appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: `linear-gradient(to right, #D4A017 0%, #D4A017 ${sliderPct}%, #4A3D1A ${sliderPct}%, #4A3D1A 100%)`,
          }}
        />
        <div className="flex justify-between font-mono text-[9px] text-faint mt-1">
          <span>3</span>
          <span>20</span>
        </div>
        <p className="font-mono text-[9px] text-faint mt-1">
          Recommended: 6–12 prompts for a focused visual set
        </p>
      </div>

      {/* Focus areas */}
      <div>
        <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">
          Focus Areas <span className="text-faint font-normal">(Optional)</span>
        </label>
        <p className="font-body text-xs text-faint mb-2">
          Leave empty for balanced coverage across the timeline.
        </p>
        <div className="grid grid-cols-2 gap-1.5">
          {focusAreas.map((area) => {
            const selected = selectedFocusAreas.includes(area);
            return (
              <button
                key={area}
                type="button"
                onClick={() => handleToggleFocusArea(area)}
                disabled={isGenerating}
                className={[
                  'flex items-center justify-between px-3 py-1.5 border transition-colors',
                  'font-mono text-[10px] tracking-widest capitalize',
                  selected
                    ? 'border-gold-dim text-gold bg-surface'
                    : 'border-border text-dim hover:border-gold-dim/50',
                  isGenerating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
                ].join(' ')}
              >
                <span>{area}</span>
                {selected && <span className="w-1.5 h-1.5 bg-gold shrink-0" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Summary + action */}
      <div className="space-y-3 pt-1">
        <div className="border border-border bg-surface/50 px-3 py-2.5">
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-1.5">Summary</p>
          <ul className="space-y-0.5 font-body text-xs text-dim">
            <li>· Will generate <span className="text-gold">{numImages}</span> image prompts</li>
            {selectedFocusAreas.length > 0 ? (
              <li>· Focusing on: <span className="text-gold">{selectedFocusAreas.join(', ')}</span></li>
            ) : (
              <li>· Balanced coverage across all major aspects</li>
            )}
            <li>· Review and refine prompts before final generation</li>
          </ul>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className={[
            'w-full px-5 py-2.5 font-mono text-[10px] tracking-widest uppercase border transition-all flex items-center justify-center gap-2',
            isGenerating
              ? 'border-border text-faint cursor-not-allowed opacity-50'
              : 'border-gold text-gold hover:bg-gold/10 cursor-pointer',
          ].join(' ')}
        >
          {isGenerating ? (
            <>
              <span className="w-3 h-3 border border-faint border-t-transparent animate-spin" />
              Generating Prompts…
            </>
          ) : (
            '§ Generate Image Prompts'
          )}
        </button>
      </div>
    </div>
  );
};

export default ImageGenerationDialog;
