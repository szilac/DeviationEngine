import type { Generation, Timeline, SupportedLanguage } from '../types';
import { exportNarrative, exportNarrativeEnhanced } from '../utils/exportUtils';
import TranslateButton from './TranslateButton';
import { LanguageSelector } from './LanguageSelector';
import { Download, BookOpen } from 'lucide-react';

interface NarrativeViewProps {
  generation: Generation;
  timeline: Timeline;
  translatedNarrative?: string;
  currentLanguage?: SupportedLanguage;
  onTranslated?: () => void;
  onLanguageChange?: (lang: SupportedLanguage) => void;
}

const formatProvider = (p: string) =>
  p === 'google' ? 'Google' : p === 'openrouter' ? 'OpenRouter' : p;

const NarrativeView = ({
  generation,
  timeline,
  translatedNarrative,
  currentLanguage = 'en',
  onTranslated,
  onLanguageChange,
}: NarrativeViewProps) => {
  const { narrative_prose, narrative_model_provider, narrative_model_name } = generation;
  const narrativeText = translatedNarrative || narrative_prose;

  const handleExport = () => {
    try {
      if (narrativeText) {
        if (translatedNarrative && currentLanguage !== 'en') {
          exportNarrativeEnhanced(generation, timeline, translatedNarrative, currentLanguage);
        } else {
          exportNarrative(generation, timeline);
        }
      } else {
        alert('No narrative content available to export.');
      }
    } catch {
      alert('Failed to export. Please try again.');
    }
  };

  // ── No narrative ──────────────────────────────────────────────────────
  if (!narrative_prose) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <BookOpen size={32} className="text-faint mb-4" />
        <p className="font-display text-xl text-dim mb-2">Narrative Not Available</p>
        <p className="font-body text-sm text-faint max-w-sm">
          This chronicle was generated without narrative prose.
          The structured report contains all analytical content.
        </p>
      </div>
    );
  }

  // ── Split into paragraphs for drop-cap treatment ──────────────────────
  const paragraphs = narrativeText?.split(/\n\n+/).filter(Boolean) ?? [];

  return (
    <div className="space-y-0">

      {/* ── Controls bar ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-5 mb-6 border-b border-border">
        <div className="flex items-center gap-3">
          {onLanguageChange && (
            <LanguageSelector currentLanguage={currentLanguage} onLanguageChange={onLanguageChange} />
          )}
          {narrative_prose && currentLanguage !== 'en' && (
            <TranslateButton
              generationId={generation.id}
              targetLanguage={currentLanguage}
              type="narrative"
              onTranslated={() => onTranslated?.()}
              onDelete={() => onTranslated?.()}
            />
          )}
        </div>

        <button
          onClick={handleExport}
          className="flex items-center gap-2 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold transition-colors duration-150 cursor-pointer"
        >
          <Download size={11} />
          Export as Markdown
        </button>
      </div>

      {/* ── Model provenance ──────────────────────────────────────── */}
      {narrative_model_provider && narrative_model_name && (
        <div className="flex items-center gap-2 mb-6 font-mono text-[10px] text-faint tracking-wide">
          <span>Narrated by</span>
          <span className="text-quantum">{formatProvider(narrative_model_provider)}</span>
          <span>·</span>
          <span>{narrative_model_name}</span>
        </div>
      )}

      {/* ── Translation notice ────────────────────────────────────── */}
      {translatedNarrative && currentLanguage !== 'en' && (
        <div className="mb-6 border border-gold-dim px-4 py-2.5 font-mono text-[10px] text-dim tracking-widest uppercase">
          Viewing translation · {currentLanguage.toUpperCase()}
        </div>
      )}

      {/* ── Rubric header ─────────────────────────────────────────── */}
      <div className="mb-6 pb-4 border-b border-border">
        <div className="flex items-baseline gap-3">
          <span className="rubric-label shrink-0">§</span>
          <h3 className="font-display text-2xl text-gold">Chronicle Narrative</h3>
        </div>
        <p className="font-caption text-sm text-dim mt-1 ml-0">
          Prose narrative — part of this generation's report
        </p>
      </div>

      {/* ── Prose ─────────────────────────────────────────────────── */}
      <div id="narrative-content" className="space-y-5">
        {paragraphs.map((para, i) => (
          <p
            key={i}
            className={[
              'font-body text-[17px] text-ink leading-[1.8]',
              // Drop cap on first paragraph
              i === 0
                ? 'first-letter:font-display first-letter:text-5xl first-letter:text-gold first-letter:float-left first-letter:leading-none first-letter:mr-2 first-letter:mt-1'
                : '',
            ].join(' ')}
          >
            {para}
          </p>
        ))}
      </div>
    </div>
  );
};

export default NarrativeView;
