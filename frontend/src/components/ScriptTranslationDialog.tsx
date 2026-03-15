import { useState } from 'react';
import { X, Zap, Brain } from 'lucide-react';
import type { AudioScript, ScriptTranslation } from '../types';
import { LANGUAGES } from '../types';
import * as audioService from '../services/audioService';

interface ScriptTranslationDialogProps {
  script: AudioScript;
  onClose: () => void;
  onTranslationCreated: (translations: ScriptTranslation[]) => void;
}

export default function ScriptTranslationDialog({
  script,
  onClose,
  onTranslationCreated,
}: ScriptTranslationDialogProps) {
  const [method, setMethod] = useState<'deepl' | 'llm'>('deepl');
  const [selectedLanguages, setSelectedLanguages] = useState<Set<string>>(new Set());
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleLanguage = (code: string) => {
    const next = new Set(selectedLanguages);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setSelectedLanguages(next);
  };

  const handleTranslate = async () => {
    if (selectedLanguages.size === 0) { setError('Select at least one language'); return; }
    setIsTranslating(true);
    setError(null);
    try {
      const translations = await audioService.translateScript(script.id, {
        target_languages: Array.from(selectedLanguages),
        method,
      });
      onTranslationCreated(translations);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Translation failed');
    } finally {
      setIsTranslating(false);
    }
  };

  const METHODS = [
    { id: 'deepl' as const, icon: <Zap size={14} />, label: 'DeepL', sub: 'Fast, reliable translation', time: '~5s per language' },
    { id: 'llm'   as const, icon: <Brain size={14} />, label: 'AI Translation', sub: 'Native quality, context-aware', time: '~30s per language' },
  ];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-parchment border border-border w-full max-w-2xl max-h-[90vh] flex flex-col shadow-[var(--shadow-panel)]">

        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div>
            <p className="rubric-label">§ Translation</p>
            <h2 className="font-display text-xl text-gold leading-tight">Translate Script</h2>
          </div>
          <button onClick={onClose} className="text-dim hover:text-ink transition-colors cursor-pointer">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Error */}
          {error && (
            <div className="border border-rubric-dim px-4 py-2.5 font-mono text-[10px] text-rubric tracking-wide">
              {error}
            </div>
          )}

          {/* Method */}
          <div className="space-y-2">
            <p className="font-mono text-[10px] tracking-widest uppercase text-dim mb-3">Translation Method</p>
            <div className="grid grid-cols-2 gap-3">
              {METHODS.map(({ id, icon, label, sub, time }) => {
                const active = method === id;
                return (
                  <button
                    key={id}
                    onClick={() => setMethod(id)}
                    className={[
                      'text-left p-4 border transition-colors duration-150 cursor-pointer',
                      active ? 'border-gold bg-surface' : 'border-border hover:border-gold-dim',
                    ].join(' ')}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className={`flex items-center gap-2 font-mono text-[11px] tracking-widest uppercase ${active ? 'text-gold' : 'text-dim'}`}>
                        {icon}
                        {label}
                      </div>
                      {active && <div className="w-2 h-2 bg-gold shrink-0 mt-0.5" />}
                    </div>
                    <p className="font-body text-xs text-dim">{sub}</p>
                    <p className="font-mono text-[9px] text-faint mt-1">{time}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Languages */}
          <div className="space-y-2">
            <p className="font-mono text-[10px] tracking-widest uppercase text-dim">
              Select Languages
              {selectedLanguages.size > 0 && (
                <span className="ml-2 text-gold">({selectedLanguages.size} selected)</span>
              )}
            </p>
            <div className="grid grid-cols-2 gap-2">
              {LANGUAGES.filter(l => l.code !== 'en').map(lang => {
                const checked = selectedLanguages.has(lang.code);
                return (
                  <button
                    key={lang.code}
                    onClick={() => toggleLanguage(lang.code)}
                    className={[
                      'flex items-center gap-3 px-3 py-2.5 border text-left transition-colors duration-150 cursor-pointer',
                      checked ? 'border-gold-dim bg-surface' : 'border-border hover:border-gold-dim/50',
                    ].join(' ')}
                  >
                    <div className={`w-3 h-3 border shrink-0 flex items-center justify-center ${checked ? 'border-gold' : 'border-border'}`}>
                      {checked && <div className="w-1.5 h-1.5 bg-gold" />}
                    </div>
                    <span className="text-base leading-none">{lang.flag}</span>
                    <span className={`font-mono text-[10px] tracking-wide ${checked ? 'text-ink' : 'text-dim'}`}>{lang.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex items-center justify-end gap-3 shrink-0">
          <button
            onClick={onClose}
            disabled={isTranslating}
            className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors disabled:opacity-50 cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleTranslate}
            disabled={selectedLanguages.size === 0 || isTranslating}
            className={[
              'flex items-center gap-2 px-5 py-2 border font-mono text-[10px] tracking-widest uppercase transition-colors',
              selectedLanguages.size > 0 && !isTranslating
                ? 'border-gold text-gold hover:bg-gold/10 cursor-pointer'
                : 'border-border text-faint cursor-not-allowed opacity-50',
            ].join(' ')}
          >
            {isTranslating && (
              <span className="w-3 h-3 border border-gold border-t-transparent rounded-full animate-spin" />
            )}
            {isTranslating ? 'Translating…' : `Translate with ${method === 'deepl' ? 'DeepL' : 'AI'}`}
          </button>
        </div>
      </div>
    </div>
  );
}
