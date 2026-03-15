import { useState, useEffect } from 'react';
import { useNotebookLMEnabled } from '../hooks/useNotebookLMEnabled';
import type { Timeline, AudioScript, ScriptPreset } from '../types';
import { AudioScriptUtils } from '../types';
import * as audioService from '../services/audioService';
import PresetSelector from './PresetSelector';
import GenerationContentSelector from './GenerationContentSelector';
import ScriptEditor from './ScriptEditor';
import NotebookLMPanel from './NotebookLMPanel';

interface AudioStudioPanelProps {
  timeline: Timeline;
  onScriptCreated?: (script: AudioScript) => void;
}

interface ContentSelection {
  generationIds: Set<string>;
  includeReports: Set<string>;
  includeNarratives: Set<string>;
}

export default function AudioStudioPanel({
  timeline,
  onScriptCreated,
}: AudioStudioPanelProps) {
  const [nlmEnabled] = useNotebookLMEnabled();
  type AudioMode = 'tts' | 'notebooklm';
  const [audioMode, setAudioMode] = useState<AudioMode>('tts');
  const [presets, setPresets] = useState<ScriptPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [isLoadingPresets, setIsLoadingPresets] = useState(true);

  const [selection, setSelection] = useState<ContentSelection>({
    generationIds: new Set(),
    includeReports: new Set(),
    includeNarratives: new Set(),
  });

  const [timelineScripts, setTimelineScripts] = useState<AudioScript[]>([]);
  const [selectedScript, setSelectedScript] = useState<AudioScript | null>(null);
  const [isLoadingScripts, setIsLoadingScripts] = useState(false);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customInstructions, setCustomInstructions] = useState<string>('');

  useEffect(() => { loadPresets(); }, []);
  useEffect(() => {
    if (timeline.generations.length > 0) loadTimelineScripts();
  }, [timeline]);

  const loadPresets = async () => {
    try {
      setIsLoadingPresets(true);
      const fetchedPresets = await audioService.getPresets();
      setPresets(fetchedPresets);
      const first = fetchedPresets.find(p => p.is_system);
      if (first) setSelectedPresetId(first.id);
    } catch (err: any) {
      console.error('Failed to load presets:', err);
      setError('Failed to load presets');
    } finally {
      setIsLoadingPresets(false);
    }
  };

  const loadTimelineScripts = async () => {
    try {
      setIsLoadingScripts(true);
      const generationIds = timeline.generations.map(g => g.id);
      const scripts = await audioService.getScriptsForTimeline(generationIds);
      setTimelineScripts(scripts);
    } catch (err: any) {
      console.error('Failed to load scripts:', err);
    } finally {
      setIsLoadingScripts(false);
    }
  };

  const handleGenerateScript = async () => {
    if (!selectedPresetId) { setError('Please select a preset'); return; }
    if (selection.generationIds.size === 0) { setError('Please select at least one chronicle'); return; }
    if (selection.includeReports.size === 0 && selection.includeNarratives.size === 0) {
      setError('Please select at least one report or narrative');
      return;
    }

    try {
      setIsGeneratingScript(true);
      setError(null);

      const script = await audioService.generateScript({
        generation_ids: Array.from(selection.generationIds),
        preset_id: selectedPresetId,
        custom_instructions: customInstructions.trim() || undefined,
        title: undefined,
      });

      setTimelineScripts(prev => [script, ...prev]);
      if (onScriptCreated) onScriptCreated(script);

      setSelection({ generationIds: new Set(), includeReports: new Set(), includeNarratives: new Set() });
      setCustomInstructions('');
    } catch (err: any) {
      console.error('Script generation failed:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to generate script');
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const handleScriptUpdate = (updatedScript: AudioScript) => {
    setTimelineScripts(prev => prev.map(s => s.id === updatedScript.id ? updatedScript : s));
    setSelectedScript(updatedScript);
  };

  const handleDeleteScript = async (scriptId: string) => {
    try {
      await audioService.deleteScript(scriptId);
      setTimelineScripts(prev => prev.filter(s => s.id !== scriptId));
      if (selectedScript?.id === scriptId) setSelectedScript(null);
    } catch (err: any) {
      console.error('Failed to delete script:', err);
      alert('Failed to delete script');
    }
  };

  const canGenerate = selectedPresetId && selection.generationIds.size > 0 &&
    (selection.includeReports.size > 0 || selection.includeNarratives.size > 0);

  return (
    <div className="px-6 pb-6 pt-4 text-ink">
      {/* Mode toggle — only visible when NotebookLM is enabled */}
      {nlmEnabled && (
        <div className="flex border border-border mb-6">
          {(['tts', 'notebooklm'] as AudioMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setAudioMode(mode)}
              className={[
                'flex-1 px-4 py-3 font-mono text-[10px] tracking-widest uppercase transition-all border-r border-border last:border-r-0',
                audioMode === mode
                  ? 'bg-gold text-parchment font-bold'
                  : 'text-dim hover:text-ink hover:bg-surface/60',
              ].join(' ')}
            >
              {mode === 'tts' ? 'Script + Google TTS' : 'NotebookLM'}
            </button>
          ))}
        </div>
      )}

      {audioMode === 'tts' ? (
        <>
          {/* Error */}
          {error && (
            <div className="border border-rubric-dim px-4 py-2.5 mb-4">
              <p className="font-mono text-[10px] text-rubric">{error}</p>
            </div>
          )}

          {/* Two-column layout */}
          <div className="grid grid-cols-[1fr_1.3fr] gap-6">

            {/* ── Left column: content + generate + scripts ── */}
            <div className="space-y-4">

              {/* Step 1 */}
              <section className="space-y-2">
                <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
                  <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">1</span>
                  Select Content
                </h3>
                <div className="border border-border bg-surface/40 p-3">
                  <GenerationContentSelector
                    generations={timeline.generations}
                    selection={selection}
                    onSelectionChange={setSelection}
                    disabled={isGeneratingScript}
                  />
                </div>
              </section>

              {/* Step 3 — generate */}
              <button
                onClick={handleGenerateScript}
                disabled={!canGenerate || isGeneratingScript}
                className={[
                  'w-full px-6 py-3 font-mono text-[10px] tracking-widest uppercase border transition-all flex items-center justify-center gap-3',
                  canGenerate && !isGeneratingScript
                    ? 'border-gold text-gold hover:bg-gold/10 cursor-pointer'
                    : 'border-border text-faint cursor-not-allowed opacity-50',
                ].join(' ')}
              >
                {isGeneratingScript ? (
                  <>
                    <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />
                    Generating Script…
                  </>
                ) : (
                  '§ Generate Audio Script'
                )}
              </button>

              {/* Existing Scripts */}
              {timelineScripts.length > 0 && (
                <section className="space-y-2">
                  <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
                    <span className="text-gold">§</span>
                    Scripts ({timelineScripts.length})
                  </h3>
                  {isLoadingScripts ? (
                    <p className="font-mono text-[10px] text-faint tracking-widest uppercase animate-pulse">Loading scripts…</p>
                  ) : (
                    <div className="space-y-1.5">
                      {timelineScripts.map(script => (
                        <div
                          key={script.id}
                          onClick={() => setSelectedScript(script)}
                          className="flex items-center justify-between px-3 py-2.5 border border-border hover:border-gold-dim cursor-pointer transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="font-display text-sm text-ink truncate">{script.title}</div>
                            <div className="flex flex-wrap items-center gap-2 font-mono text-[9px] text-faint mt-0.5">
                              <span className={`capitalize ${AudioScriptUtils.getStatusColor(script.status)}`}>{script.status}</span>
                              <span>{script.word_count}w</span>
                              <span>~{AudioScriptUtils.formatDuration(script.estimated_duration_seconds)}</span>
                              {script.preset && <span>{script.preset.name}</span>}
                            </div>
                          </div>
                          <span className="text-gold-dim font-mono text-[10px] ml-2">→</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}
            </div>

            {/* ── Right column: style + instructions ── */}
            <div className="space-y-4">

              {/* Step 2 */}
              <section className="space-y-2">
                <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
                  <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">2</span>
                  Select Audio Style
                </h3>
                <div className="border border-border bg-surface/40 p-3">
                  {isLoadingPresets ? (
                    <p className="font-mono text-[10px] text-faint tracking-widest uppercase animate-pulse">Loading presets…</p>
                  ) : (
                    <PresetSelector
                      presets={presets}
                      selectedPresetId={selectedPresetId}
                      onSelect={setSelectedPresetId}
                      disabled={isGeneratingScript}
                    />
                  )}
                </div>
              </section>

              {/* Custom instructions */}
              <section className="space-y-2">
                <label htmlFor="custom-instructions" className="font-mono text-[10px] tracking-widest uppercase text-dim block">
                  Custom Instructions <span className="text-faint font-normal">(Optional)</span>
                </label>
                <textarea
                  id="custom-instructions"
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  disabled={isGeneratingScript}
                  placeholder="e.g. 'Focus on economic impacts' or 'Use more dramatic language'"
                  maxLength={1000}
                  rows={4}
                  className="w-full bg-transparent border border-border text-ink font-body text-sm
                             px-3 py-2 placeholder:text-faint placeholder:font-mono placeholder:text-[10px]
                             focus:outline-none focus:border-gold-dim
                             disabled:opacity-40 disabled:cursor-not-allowed
                             resize-none transition-colors"
                />
                <div className="flex justify-between items-center font-mono text-[9px] text-faint">
                  <span>Guidance for the AI narrator</span>
                  <span>{customInstructions.length}/1000</span>
                </div>
              </section>
            </div>
          </div>

          {selectedScript && (
            <ScriptEditor
              script={selectedScript}
              onUpdate={handleScriptUpdate}
              onClose={() => setSelectedScript(null)}
              onDelete={handleDeleteScript}
            />
          )}
        </>
      ) : nlmEnabled ? (
        <NotebookLMPanel timeline={timeline} />
      ) : null}
    </div>
  );
}
