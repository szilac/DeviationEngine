import type { Generation } from '../types';
import { TimelineUtils } from '../types';

interface ContentSelection {
  generationIds: Set<string>;
  includeReports: Set<string>;
  includeNarratives: Set<string>;
}

interface GenerationContentSelectorProps {
  generations: Generation[];
  selection: ContentSelection;
  onSelectionChange: (selection: ContentSelection) => void;
  disabled?: boolean;
}

export default function GenerationContentSelector({
  generations,
  selection,
  onSelectionChange,
  disabled = false,
}: GenerationContentSelectorProps) {
  const sortedGenerations = TimelineUtils.sortGenerationsByOrder(generations);

  const toggleGeneration = (generationId: string) => {
    const newGenerationIds = new Set(selection.generationIds);
    const newReports = new Set(selection.includeReports);
    const newNarratives = new Set(selection.includeNarratives);

    if (newGenerationIds.has(generationId)) {
      newGenerationIds.delete(generationId);
      newReports.delete(generationId);
      newNarratives.delete(generationId);
    } else {
      newGenerationIds.add(generationId);
      newReports.add(generationId);
      if (hasNarrative(generationId)) newNarratives.add(generationId);
    }
    onSelectionChange({ generationIds: newGenerationIds, includeReports: newReports, includeNarratives: newNarratives });
  };

  const toggleReport = (generationId: string) => {
    const newReports = new Set(selection.includeReports);
    newReports.has(generationId) ? newReports.delete(generationId) : newReports.add(generationId);
    onSelectionChange({ ...selection, includeReports: newReports });
  };

  const toggleNarrative = (generationId: string) => {
    const newNarratives = new Set(selection.includeNarratives);
    newNarratives.has(generationId) ? newNarratives.delete(generationId) : newNarratives.add(generationId);
    onSelectionChange({ ...selection, includeNarratives: newNarratives });
  };

  const hasNarrative = (generationId: string): boolean => {
    const g = generations.find(g => g.id === generationId);
    return !!(g?.narrative_prose && g.narrative_prose.length > 0);
  };

  const clearSelection = () => {
    onSelectionChange({
      generationIds: new Set(),
      includeReports: new Set(),
      includeNarratives: new Set(),
    });
  };

  const selectedCount = selection.generationIds.size;
  const sourceCount = selection.includeReports.size + selection.includeNarratives.size;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[9px] tracking-widest uppercase text-faint">
          Select Content for Script
        </p>
        {selectedCount > 0 && (
          <button
            onClick={clearSelection}
            disabled={disabled}
            className="font-mono text-[9px] tracking-widest uppercase text-dim hover:text-gold transition-colors cursor-pointer"
          >
            Clear
          </button>
        )}
      </div>

      <div className="space-y-2">
        {sortedGenerations.map(generation => {
          const isSelected = selection.generationIds.has(generation.id);
          const reportChecked = selection.includeReports.has(generation.id);
          const narrativeChecked = selection.includeNarratives.has(generation.id);
          const narrativeAvailable = hasNarrative(generation.id);

          return (
            <div
              key={generation.id}
              className={`border transition-colors ${
                isSelected ? 'border-gold-dim' : 'border-border'
              }`}
            >
              {/* Generation row */}
              <div
                className={`px-3 py-2.5 flex items-center gap-3 ${
                  disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                }`}
                onClick={() => !disabled && toggleGeneration(generation.id)}
              >
                {/* Square checkbox */}
                <div className={`w-3 h-3 border shrink-0 flex items-center justify-center ${
                  isSelected ? 'border-gold' : 'border-border'
                }`}>
                  {isSelected && <div className="w-1.5 h-1.5 bg-gold" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`font-mono text-[11px] tracking-widest ${isSelected ? 'text-gold' : 'text-ink'}`}>
                    Chronicle {generation.generation_order}
                    {' · '}
                    {TimelineUtils.getGenerationPeriodDescription(generation)}
                  </div>
                  {generation.executive_summary && (
                    <div className="font-body text-xs text-dim mt-0.5 line-clamp-1">
                      {generation.executive_summary}
                    </div>
                  )}
                </div>
              </div>

              {/* Content toggles */}
              {isSelected && (
                <div className="px-3 pb-2.5 pt-2 border-t border-border flex gap-4">
                  {[
                    { label: 'Report', checked: reportChecked, toggle: () => !disabled && toggleReport(generation.id), available: true },
                    { label: 'Narrative', checked: narrativeChecked, toggle: () => !disabled && toggleNarrative(generation.id), available: narrativeAvailable },
                  ].map(({ label, checked, toggle, available }) => (
                    <label
                      key={label}
                      className={`flex items-center gap-1.5 ${
                        !available || disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
                      }`}
                      onClick={available && !disabled ? toggle : undefined}
                    >
                      <div className={`w-3 h-3 border shrink-0 flex items-center justify-center ${
                        checked ? 'border-gold' : 'border-border'
                      }`}>
                        {checked && <div className="w-1.5 h-1.5 bg-gold" />}
                      </div>
                      <span className="font-mono text-[10px] tracking-widest text-dim">
                        {label}
                        {!available && <span className="text-faint ml-1">(n/a)</span>}
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedCount > 0 && (
        <div className="px-3 py-2 border border-border bg-surface/50 font-mono text-[9px] tracking-widest uppercase text-dim">
          {selectedCount} chronicle{selectedCount !== 1 ? 's' : ''} · {sourceCount} source{sourceCount !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
