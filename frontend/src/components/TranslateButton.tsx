import { useState } from 'react';
import { X, Zap, Brain } from 'lucide-react';
import { translateGeneration, translateNarrative, deleteGenerationTranslation } from '../services/api';
import type { SupportedLanguage } from '../types';

interface TranslationMethodDialogProps {
  onSelect: (method: 'deepl' | 'llm') => void;
  onCancel: () => void;
}

function TranslationMethodDialog({ onSelect, onCancel }: TranslationMethodDialogProps) {
  const METHODS = [
    { id: 'deepl' as const, icon: <Zap size={13} />, label: 'DeepL', sub: 'Fast, reliable translation', time: '~5 seconds' },
    { id: 'llm'   as const, icon: <Brain size={13} />, label: 'AI Translation', sub: 'Native quality, context-aware', time: '~30 seconds' },
  ];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-parchment border border-border w-full max-w-sm shadow-[var(--shadow-panel)]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <div>
            <p className="rubric-label">§ Translation</p>
            <h3 className="font-display text-lg text-gold leading-tight">Choose Method</h3>
          </div>
          <button onClick={onCancel} className="text-dim hover:text-ink transition-colors cursor-pointer">
            <X size={15} />
          </button>
        </div>

        {/* Method options */}
        <div className="p-4 space-y-2">
          {METHODS.map(({ id, icon, label, sub, time }) => (
            <button
              key={id}
              onClick={() => onSelect(id)}
              className="w-full text-left p-4 border border-border hover:border-gold-dim hover:bg-surface transition-colors duration-150 cursor-pointer"
            >
              <div className="flex items-center gap-2 font-mono text-[10px] tracking-widest uppercase text-gold mb-1.5">
                {icon}
                {label}
              </div>
              <p className="font-body text-xs text-dim">{sub}</p>
              <p className="font-mono text-[9px] text-faint mt-0.5">{time}</p>
            </button>
          ))}
        </div>

        {/* Cancel */}
        <div className="px-4 pb-4">
          <button
            onClick={onCancel}
            className="w-full py-2 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors border border-border hover:border-gold-dim/50 cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

interface TranslateButtonProps {
  generationId: string;
  targetLanguage: SupportedLanguage;
  onTranslated: () => void;
  onDelete?: (languageCode: string, contentType: 'report' | 'narrative') => void;
  type: 'generation' | 'narrative';
  className?: string;
}

export default function TranslateButton({
  generationId,
  targetLanguage,
  onTranslated,
  onDelete,
  type,
  className = '',
}: TranslateButtonProps) {
  const [showMethodDialog, setShowMethodDialog] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);

  const handleTranslate = async (method: 'deepl' | 'llm') => {
    setShowMethodDialog(false);
    setIsTranslating(true);
    try {
      const result = type === 'generation'
        ? await translateGeneration(generationId, targetLanguage, method)
        : await translateNarrative(generationId, targetLanguage, method);
      if (result.error) { alert(`Translation failed: ${result.error.message || 'Unknown error'}`); return; }
      onTranslated?.();
    } catch {
      alert('Translation failed');
    } finally {
      setIsTranslating(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    const contentType = type === 'generation' ? 'report' : 'narrative';
    if (!confirm(`Delete ${targetLanguage.toUpperCase()} ${contentType} translation?`)) return;
    try {
      await deleteGenerationTranslation(generationId, targetLanguage, contentType);
      onDelete(targetLanguage, contentType);
    } catch {
      alert('Failed to delete translation');
    }
  };

  return (
    <>
      <div className={`flex items-center gap-2 ${className}`}>
        <button
          onClick={() => setShowMethodDialog(true)}
          disabled={isTranslating}
          className={[
            'flex items-center gap-1.5 px-3 py-1.5 border font-mono text-[10px] tracking-widest uppercase transition-colors',
            isTranslating
              ? 'border-border text-faint cursor-not-allowed opacity-60'
              : 'border-gold-dim text-gold hover:border-gold hover:bg-gold/5 cursor-pointer',
          ].join(' ')}
        >
          {isTranslating && (
            <span className="w-2.5 h-2.5 border border-gold border-t-transparent rounded-full animate-spin" />
          )}
          {isTranslating ? 'Translating…' : `Translate ${type === 'generation' ? 'Report' : 'Narrative'}`}
        </button>

        {onDelete && targetLanguage !== 'en' && (
          <button
            onClick={handleDelete}
            className="font-mono text-[10px] tracking-widest uppercase text-rubric-dim hover:text-rubric transition-colors cursor-pointer"
          >
            Delete
          </button>
        )}
      </div>

      {showMethodDialog && (
        <TranslationMethodDialog
          onSelect={handleTranslate}
          onCancel={() => setShowMethodDialog(false)}
        />
      )}
    </>
  );
}
