/**
 * Per-Language Audio Generation Implementation
 *
 * This component provides language-specific audio generation and playback functionality.
 * Key features:
 * - Audio files are tracked and loaded per language independently
 * - Language selection shows audio specific to that language or allows generation
 * - Generate audio action works with current language's script content
 * - Per-language generation state tracking prevents concurrent generation
 * - localStorage persistence maintains audio references across sessions
 * - Error handling preserves previous state and provides user feedback
 */

import { useState, useEffect } from 'react';
import type { AudioScript, AudioFile, ScriptTranslation } from '../types';
import { AudioScriptUtils } from '../types';
import * as audioService from '../services/audioService';
import AudioPlayer from './AudioPlayer';
import ScriptTranslationDialog from './ScriptTranslationDialog';
import { X } from 'lucide-react';

// LocalStorage keys for per-language audio state
const getAudioStateKey = (scriptId: string) => `audio_state_${scriptId}`;

interface PersistedAudioState {
  generatedLanguages: string[];
  errors: Record<string, string>;
  lastUpdated: string;
}

const saveAudioState = (scriptId: string, state: PersistedAudioState) => {
  try { localStorage.setItem(getAudioStateKey(scriptId), JSON.stringify(state)); }
  catch (error) { console.warn('Failed to save audio state:', error); }
};

const loadAudioState = (scriptId: string): PersistedAudioState | null => {
  try {
    const saved = localStorage.getItem(getAudioStateKey(scriptId));
    return saved ? JSON.parse(saved) : null;
  } catch { return null; }
};

interface ScriptEditorProps {
  script: AudioScript;
  onUpdate: (updatedScript: AudioScript) => void;
  onClose: () => void;
  onDelete?: (scriptId: string) => void;
}

export default function ScriptEditor({ script, onUpdate, onClose, onDelete }: ScriptEditorProps) {
  const [editedContent, setEditedContent] = useState(script.script_content);
  const [editedTitle, setEditedTitle] = useState(script.title);
  const [isSaving, setIsSaving] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [audioFilesByLanguage, setAudioFilesByLanguage] = useState<Record<string, AudioFile[]>>({});
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [showTranslationDialog, setShowTranslationDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [translations, setTranslations] = useState<ScriptTranslation[]>([]);
  const [isLoadingTranslations, setIsLoadingTranslations] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [generatingLanguages, setGeneratingLanguages] = useState<Set<string>>(new Set());
  const [audioGenerationErrors, setAudioGenerationErrors] = useState<Record<string, string>>({});

  const canEdit = AudioScriptUtils.canEdit(script);
  const canApprove = AudioScriptUtils.canApprove(script);
  const currentTranslation = translations.find(t => t.language_code === selectedLanguage);
  const currentAudioFiles = audioFilesByLanguage[selectedLanguage] || [];

  const hasChanges = selectedLanguage === 'en'
    ? editedContent !== script.script_content || editedTitle !== script.title
    : currentTranslation && editedContent !== currentTranslation.translated_content;

  const wordCount = editedContent.split(/\s+/).filter(w => w.length > 0).length;
  const estimatedMinutes = Math.floor(
    (wordCount / 150) * (script.preset?.pacing === 'fast' ? 0.8 : script.preset?.pacing === 'slow' ? 1.2 : 1)
  );

  useEffect(() => {
    setEditedContent(script.script_content);
    setEditedTitle(script.title);
    setSelectedLanguage('en');
    loadTranslations();
    const persisted = loadAudioState(script.id);
    if (persisted) setAudioGenerationErrors(persisted.errors);
    if (AudioScriptUtils.canGenerateAudio(script)) loadAudioFiles();
  }, [script]);

  const loadAudioFiles = async () => {
    try {
      setIsLoadingAudio(true);
      const files = await audioService.getScriptAudioFiles(script.id);
      const grouped = files.reduce((acc, file) => {
        const lang = file.language_code;
        if (!acc[lang]) acc[lang] = [];
        acc[lang].push(file);
        return acc;
      }, {} as Record<string, AudioFile[]>);
      setAudioFilesByLanguage(grouped);

      const persisted = loadAudioState(script.id);
      saveAudioState(script.id, {
        generatedLanguages: Object.keys(grouped),
        errors: persisted?.errors || {},
        lastUpdated: new Date().toISOString(),
      });
    } catch (err: any) {
      console.error('Failed to load audio files:', err);
    } finally {
      setIsLoadingAudio(false);
    }
  };

  const loadTranslations = async () => {
    try {
      setIsLoadingTranslations(true);
      const fetched = await audioService.getScriptTranslations(script.id);
      setTranslations(fetched);
    } catch (err: any) {
      console.error('Failed to load translations:', err);
    } finally {
      setIsLoadingTranslations(false);
    }
  };

  const handleLanguageChange = (languageCode: string) => {
    if (languageCode === 'en') {
      setEditedContent(script.script_content);
      setSelectedLanguage('en');
    } else {
      const translation = translations.find(t => t.language_code === languageCode);
      if (translation) {
        setEditedContent(translation.translated_content);
        setSelectedLanguage(languageCode);
      }
    }
  };

  const handleSave = async () => {
    if (!canEdit) return;
    try {
      setIsSaving(true);
      setError(null);
      if (selectedLanguage === 'en') {
        const updated = await audioService.updateScript(script.id, {
          script_content: editedContent,
          title: editedTitle,
        });
        onUpdate(updated);
      } else if (currentTranslation) {
        await audioService.updateTranslation(currentTranslation.id, editedContent);
        await loadTranslations();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!canApprove) return;
    if (!confirm('Approve this script for audio generation? (You can still edit it later)')) return;
    try {
      setIsApproving(true);
      setError(null);
      const updated = await audioService.approveScript(script.id);
      onUpdate(updated);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to approve script');
    } finally {
      setIsApproving(false);
    }
  };

  const generateAudioForCurrentLanguage = async () => {
    const languageCode = selectedLanguage;
    if (generatingLanguages.has(languageCode)) return;
    try {
      setGeneratingLanguages(prev => new Set([...prev, languageCode]));
      setError(null);
      setAudioGenerationErrors(prev => ({ ...prev, [languageCode]: '' }));

      const audioFile = await audioService.generateAudio({ script_id: script.id, language_code: languageCode });
      setAudioFilesByLanguage(prev => ({
        ...prev,
        [languageCode]: [...(prev[languageCode] || []), audioFile],
      }));

      const persisted = loadAudioState(script.id);
      saveAudioState(script.id, {
        generatedLanguages: [...(persisted?.generatedLanguages || []), languageCode],
        errors: { ...(persisted?.errors || {}), [languageCode]: '' },
        lastUpdated: new Date().toISOString(),
      });
    } catch (err: any) {
      let errorMessage = 'Failed to generate audio';
      if (err.response?.data?.detail) {
        errorMessage = Array.isArray(err.response.data.detail)
          ? err.response.data.detail.map((e: any) => e.msg).join(', ')
          : err.response.data.detail;
      }
      setAudioGenerationErrors(prev => ({ ...prev, [languageCode]: errorMessage }));
      setError(errorMessage);
    } finally {
      setGeneratingLanguages(prev => {
        const next = new Set(prev);
        next.delete(languageCode);
        return next;
      });
    }
  };

  const handleDeleteAudio = async (audioFileId: string) => {
    try {
      await audioService.deleteAudioFile(audioFileId);
      setAudioFilesByLanguage(prev => {
        const updated = { ...prev, [selectedLanguage]: (prev[selectedLanguage] || []).filter(af => af.id !== audioFileId) };
        const persisted = loadAudioState(script.id);
        saveAudioState(script.id, {
          generatedLanguages: Object.keys(updated).filter(lang => updated[lang]?.length > 0),
          errors: { ...(persisted?.errors || {}), [selectedLanguage]: '' },
          lastUpdated: new Date().toISOString(),
        });
        return updated;
      });
    } catch (err: any) {
      alert('Failed to delete audio file');
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    if (!confirm('Delete this script? This action cannot be undone.')) return;
    onDelete(script.id);
    onClose();
  };

  const handleDeleteTranslation = async (languageCode: string) => {
    if (!confirm(`Delete ${languageCode.toUpperCase()} translation?`)) return;
    try {
      await audioService.deleteScriptTranslation(script.id, languageCode);
      await loadTranslations();
      setSelectedLanguage('en');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete translation');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-parchment border border-border corner-brackets max-w-6xl w-full h-[90vh] flex flex-col">

        {/* Header */}
        <div className="px-5 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex-1 min-w-0 mr-4">
            {canEdit ? (
              <input
                type="text"
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                className="font-display text-xl text-gold bg-transparent border-b border-border focus:outline-none focus:border-gold-dim w-full pb-0.5 transition-colors"
                placeholder="Script title"
              />
            ) : (
              <h2 className="font-display text-xl text-gold">{script.title}</h2>
            )}
            <div className="flex items-center gap-3 mt-1.5 font-mono text-[10px] text-faint flex-wrap">
              <span className={`capitalize ${AudioScriptUtils.getStatusColor(script.status)}`}>
                {script.status}
              </span>
              {(script.status === 'approved' || script.status === 'audio_generated') && (
                <span className="text-quantum">(editable — resets to draft)</span>
              )}
              {script.preset?.name && <span>{script.preset.name}</span>}
              <span>{script.word_count} words</span>
              <span>~{AudioScriptUtils.formatDuration(script.estimated_duration_seconds)}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-dim hover:text-ink cursor-pointer p-1 shrink-0">
            <X size={14} />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-5 mt-3 border border-rubric-dim px-3 py-2 shrink-0">
            <p className="font-mono text-[10px] text-rubric">{error}</p>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 flex flex-col px-5 py-4 overflow-hidden min-h-0">
          {/* Language bar */}
          <div className="mb-3 flex-shrink-0">
            <div className="flex items-center gap-3 flex-wrap">
              {translations.length > 0 && (
                <select
                  value={selectedLanguage}
                  onChange={(e) => handleLanguageChange(e.target.value)}
                  disabled={isLoadingTranslations}
                  className="bg-transparent border-b border-border text-dim font-mono text-[10px] tracking-widest uppercase focus:outline-none focus:border-gold-dim disabled:opacity-50 cursor-pointer"
                >
                  <option value="en">EN — English (Original)</option>
                  {translations.map(t => (
                    <option key={t.id} value={t.language_code}>
                      {t.language_code.toUpperCase()} — {t.language_name}
                      {t.translation_method === 'llm' ? ' ✦' : ''}
                      {t.is_human_translated ? ' ✎' : ''}
                    </option>
                  ))}
                </select>
              )}

              {selectedLanguage !== 'en' && (
                <button
                  onClick={() => handleDeleteTranslation(selectedLanguage)}
                  className="font-mono text-[10px] uppercase tracking-widest text-faint hover:text-rubric transition-colors cursor-pointer"
                >
                  Delete Translation
                </button>
              )}

              <button
                onClick={() => setShowTranslationDialog(true)}
                className="font-mono text-[10px] uppercase tracking-widest border border-border text-dim hover:border-gold-dim hover:text-gold px-3 py-1 transition-colors cursor-pointer"
              >
                Translate
              </button>

              {canEdit && hasChanges && (
                <span className="font-mono text-[10px] text-warning ml-auto">Unsaved changes</span>
              )}
              {selectedLanguage !== 'en' && !hasChanges && (
                <span className="font-mono text-[10px] text-quantum ml-auto">Viewing translation</span>
              )}
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 min-h-[200px]">
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              disabled={!canEdit}
              className={`w-full h-full bg-surface border border-border text-ink font-mono text-sm
                          p-4 resize-none focus:outline-none focus:border-gold-dim transition-colors
                          placeholder:text-faint ${!canEdit ? 'opacity-40 cursor-not-allowed' : ''}`}
              placeholder="Script content…"
            />
          </div>

          {canEdit && (
            <div className="mt-2 flex items-center gap-4 font-mono text-[9px] text-faint flex-shrink-0">
              <span>{wordCount} words</span>
              <span>Est. ~{estimatedMinutes}m</span>
            </div>
          )}
        </div>

        {/* Audio section */}
        {AudioScriptUtils.canGenerateAudio(script) && (
          <div className="px-5 py-3 border-t border-border flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <p className="rubric-label">§ Audio ({selectedLanguage.toUpperCase()})</p>
              {currentAudioFiles.length === 0 && (
                <button
                  onClick={generateAudioForCurrentLanguage}
                  disabled={generatingLanguages.has(selectedLanguage)}
                  className={[
                    'font-mono text-[10px] tracking-widest uppercase border px-3 py-1.5 transition-colors',
                    generatingLanguages.has(selectedLanguage)
                      ? 'border-border text-faint opacity-50 cursor-not-allowed'
                      : 'border-gold-dim text-gold hover:border-gold cursor-pointer',
                  ].join(' ')}
                >
                  {generatingLanguages.has(selectedLanguage) ? (
                    <span className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 border border-faint border-t-transparent animate-spin" />
                      Generating…
                    </span>
                  ) : 'Generate Audio'}
                </button>
              )}
            </div>

            {audioGenerationErrors[selectedLanguage] && (
              <div className="mb-3 border border-rubric-dim px-3 py-2">
                <p className="font-mono text-[10px] text-rubric">{audioGenerationErrors[selectedLanguage]}</p>
              </div>
            )}

            {isLoadingAudio ? (
              <p className="font-mono text-[10px] text-faint tracking-widest uppercase animate-pulse">
                Loading audio…
              </p>
            ) : (
              <AudioPlayer audioFiles={currentAudioFiles} onDelete={handleDeleteAudio} />
            )}
          </div>
        )}

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border flex items-center justify-between flex-shrink-0">
          <div>
            {onDelete && (
              <button
                onClick={handleDelete}
                className="font-mono text-[10px] uppercase tracking-widest text-faint hover:text-rubric transition-colors cursor-pointer"
              >
                Delete Script
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="font-mono text-[10px] uppercase tracking-widest text-dim hover:text-ink transition-colors cursor-pointer"
            >
              Close
            </button>
            {canEdit && (
              <button
                onClick={handleSave}
                disabled={!hasChanges || isSaving}
                className={[
                  'font-mono text-[10px] tracking-widest uppercase border px-4 py-1.5 transition-colors',
                  hasChanges && !isSaving
                    ? 'border-gold-dim text-gold hover:border-gold cursor-pointer'
                    : 'border-border text-faint cursor-not-allowed opacity-40',
                ].join(' ')}
              >
                {isSaving ? 'Saving…' : selectedLanguage === 'en' ? 'Save Draft' : 'Save Translation'}
              </button>
            )}
            {canApprove && (
              <button
                onClick={handleApprove}
                disabled={isApproving}
                className="font-mono text-[10px] tracking-widest uppercase border border-gold-dim text-gold hover:border-gold px-4 py-1.5 transition-colors disabled:opacity-40 cursor-pointer"
              >
                {isApproving ? 'Approving…' : 'Approve for Audio'}
              </button>
            )}
          </div>
        </div>
      </div>

      {showTranslationDialog && (
        <ScriptTranslationDialog
          script={script}
          onClose={() => setShowTranslationDialog(false)}
          onTranslationCreated={() => { loadTranslations(); loadAudioFiles(); }}
        />
      )}
    </div>
  );
}
