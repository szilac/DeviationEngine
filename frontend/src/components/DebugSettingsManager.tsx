/**
 * Debug Settings Manager Component.
 *
 * Provides UI controls for managing debug settings including RAG debug mode,
 * agent prompt logging, and RAG vs Legacy mode toggle.
 */

import { useState, useEffect } from 'react';
import { getDebugSettings, updateDebugSettings, purgeAllData } from '../services/api';
import type { DebugSettings, DebugSettingsUpdate, PurgeDataResponse } from '../types';

interface DebugSettingsManagerProps {
  isLoading?: boolean;
}

const ManuscriptToggle = ({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  label: string;
}) => (
  <button
    type="button"
    onClick={onChange}
    disabled={disabled}
    aria-label={label}
    className={`relative w-10 h-5 border transition-colors shrink-0
      ${checked ? 'border-gold bg-gold/10' : 'border-border bg-transparent'}
      ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
  >
    <span
      className={`absolute top-1 w-3 h-3 transition-all duration-200
        ${checked ? 'left-5 bg-gold' : 'left-1 bg-faint'}`}
    />
  </button>
);

export default function DebugSettingsManager({ isLoading: parentLoading }: DebugSettingsManagerProps) {
  const [settings, setSettings] = useState<DebugSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [showPurgeConfirmation, setShowPurgeConfirmation] = useState(false);
  const [purgeInProgress, setPurgeInProgress] = useState(false);
  const [purgeResult, setPurgeResult] = useState<PurgeDataResponse | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await getDebugSettings();
        if (response.error) {
          setError(response.error.message);
        } else if (response.data) {
          setSettings(response.data);
        }
      } catch (err) {
        setError('Failed to load debug settings. Please try again.');
        console.error('Debug settings fetch error:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleToggle = async (field: keyof DebugSettings) => {
    if (!settings) return;
    setIsSaving(true); setError(null); setSuccessMessage(null);
    const update: DebugSettingsUpdate = { [field]: !settings[field] };
    try {
      const response = await updateDebugSettings(update);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setSettings(response.data);
        setSuccessMessage('Settings updated');
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch {
      setError('Failed to update settings. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleModeChange = async (mode: 'rag' | 'legacy') => {
    if (!settings) return;
    setIsSaving(true); setError(null); setSuccessMessage(null);
    const update: DebugSettingsUpdate = { context_retrieval_mode: mode };
    try {
      const response = await updateDebugSettings(update);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setSettings(response.data);
        setSuccessMessage('Context retrieval mode updated');
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch {
      setError('Failed to update mode. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePurgeData = async () => {
    setPurgeInProgress(true); setError(null); setPurgeResult(null);
    try {
      const response = await purgeAllData(true);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setPurgeResult(response.data);
        setSuccessMessage('Data purge completed successfully');
        setTimeout(() => {
          setSuccessMessage(null);
          setPurgeResult(null);
          setShowPurgeConfirmation(false);
        }, 10000);
      }
    } catch {
      setError('Failed to purge data. Please try again.');
    } finally {
      setPurgeInProgress(false);
    }
  };

  if (isLoading || parentLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin h-8 w-8 border border-gold rounded-full border-t-transparent" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="py-8 text-center">
        <p className="font-caption text-sm text-dim">Failed to load debug settings</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Feedback messages */}
      {successMessage && (
        <div className="border-l-2 border-success pl-4 py-1">
          <p className="font-caption text-sm text-success">{successMessage}</p>
        </div>
      )}
      {error && (
        <div className="border-l-2 border-rubric pl-4 py-1">
          <p className="font-caption text-sm text-rubric">{error}</p>
        </div>
      )}

      {/* Context Retrieval Mode */}
      <div className="space-y-3">
        <p className="rubric-label">Default Context Mode for New Timelines</p>
        <p className="font-caption text-sm text-dim">
          Set your preferred default for timeline generation. Can be overridden per-timeline in Advanced Options.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {(['rag', 'legacy'] as const).map((mode) => {
            const isActive = settings?.context_retrieval_mode === mode;
            return (
              <button
                key={mode}
                onClick={() => handleModeChange(mode)}
                disabled={isSaving}
                className={`p-4 border text-left transition-colors
                  ${isActive
                    ? 'border-gold bg-gold/5'
                    : 'border-border bg-transparent hover:bg-overlay'
                  }
                  ${isSaving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <div className={`font-mono text-xs tracking-widest uppercase mb-1.5
                  ${isActive ? 'text-gold' : 'text-dim'}`}>
                  {mode === 'rag' ? 'Smart Search' : 'Full Context'}
                  {mode === 'rag' && (
                    <span className="ml-2 text-success normal-case">(Recommended)</span>
                  )}
                </div>
                <div className="font-caption text-xs text-dim">
                  {mode === 'rag'
                    ? 'AI finds most relevant context (~99% fewer tokens)'
                    : 'Loads all historical data from period'}
                </div>
              </button>
            );
          })}
        </div>
        <div className="border-l-2 border-quantum pl-4 py-1">
          <p className="font-caption text-xs text-dim">
            This sets the default for all new timelines. Individual timelines can override this via
            Advanced Options at the review step.
          </p>
        </div>
      </div>

      <div className="double-rule" />

      {/* Toggle rows */}
      <div className="space-y-5">
        <p className="rubric-label">Debug Toggles</p>

        {/* Vector RAG Mode */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="font-body text-sm text-ink">Vector RAG Mode</div>
            <div className="font-caption text-xs text-dim mt-0.5">
              Enable vector-based RAG for historical context retrieval.
              <span className="block mt-1 text-warning">Requires server restart to take effect.</span>
            </div>
          </div>
          <ManuscriptToggle
            checked={settings.vector_store_enabled}
            onChange={() => handleToggle('vector_store_enabled')}
            disabled={isSaving}
            label="Toggle Vector RAG mode"
          />
        </div>

        {/* RAG Debug Mode */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="font-body text-sm text-ink">RAG Debug Mode</div>
            <div className="font-caption text-xs text-dim mt-0.5">
              Log detailed RAG retrieval information: query strategies, chunk counts, retrieval scores.
              Output in backend terminal.
            </div>
          </div>
          <ManuscriptToggle
            checked={settings.rag_debug_mode}
            onChange={() => handleToggle('rag_debug_mode')}
            disabled={isSaving}
            label="Toggle RAG debug mode"
          />
        </div>

        {/* Agent Prompt Logging */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="font-body text-sm text-ink">Agent Prompt Logging</div>
            <div className="font-caption text-xs text-dim mt-0.5">
              Save complete agent prompts to{' '}
              <code className="font-mono text-quantum">backend/data/agent_prompts/</code>.
              Useful for debugging exact inputs sent to LLMs.
            </div>
          </div>
          <ManuscriptToggle
            checked={settings.debug_agent_prompts}
            onChange={() => handleToggle('debug_agent_prompts')}
            disabled={isSaving}
            label="Toggle agent prompt logging"
          />
        </div>
      </div>

      <div className="double-rule" />

      {/* Info note */}
      <div className="border-l-2 border-quantum pl-4 py-1">
        <p className="font-caption text-xs text-dim">
          Debug settings are stored as environment variables. Some changes (like RAG mode toggle) may
          require a backend restart. Debug logs appear in the backend terminal, not the frontend.
        </p>
      </div>

      <div className="double-rule" />

      {/* Danger Zone */}
      <div className="border border-rubric-dim bg-rubric/5 p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-rubric tracking-widest uppercase">§ Danger Zone</span>
          <span className="text-rubric-dim">—</span>
          <span className="font-caption text-sm text-rubric">Purge All Data</span>
        </div>
        <p className="font-caption text-sm text-dim">
          Permanently delete all timelines, skeleton drafts, generations, audio, images, and vector data.
          This action <strong className="text-ink">cannot be undone</strong>.
          Configuration and ground truth data will be preserved.
        </p>

        {!showPurgeConfirmation ? (
          <button
            onClick={() => setShowPurgeConfirmation(true)}
            disabled={isSaving || purgeInProgress}
            className="bg-rubric/10 hover:bg-rubric/20 border border-rubric-dim text-rubric
                       font-mono text-xs tracking-widest uppercase px-5 py-2.5
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            PURGE ALL DATA
          </button>
        ) : (
          <div className="space-y-4">
            <div className="border border-warning/40 bg-warning/5 p-4">
              <p className="font-caption text-sm text-warning font-semibold mb-2">Are you absolutely sure?</p>
              <p className="font-caption text-xs text-dim mb-2">This will permanently delete:</p>
              <ul className="font-caption text-xs text-dim space-y-1 mb-3">
                <li>• All timelines and generations</li>
                <li>• All skeleton drafts (workflow drafts)</li>
                <li>• All audio scripts and files</li>
                <li>• All images and media</li>
                <li>• Vector store data (generated content only)</li>
              </ul>
              <p className="font-caption text-xs text-success">
                ✓ Configuration settings and ground truth historical data will be preserved.
              </p>
            </div>

            {purgeResult && (
              <div className="border-l-2 border-success pl-4 py-1 space-y-1">
                <div className="font-caption text-sm text-success font-semibold">Purge Completed</div>
                <div className="font-mono text-xs text-dim space-y-0.5">
                  <div>timelines deleted: {purgeResult.stats.timelines_deleted}</div>
                  <div>skeleton drafts deleted: {purgeResult.stats.skeletons_deleted}</div>
                  <div>image prompts deleted: {purgeResult.stats.image_prompts_deleted}</div>
                  <div>script translations deleted: {purgeResult.stats.script_translations_deleted}</div>
                  <div>audio files deleted: {purgeResult.stats.filesystem_audio_deleted}</div>
                  <div>images deleted: {purgeResult.stats.filesystem_images_deleted}</div>
                  <div>vector store purged: {purgeResult.stats.vector_store_purged ? 'yes' : 'no'}</div>
                  {purgeResult.stats.errors.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-warning/30 text-warning space-y-0.5">
                      {purgeResult.stats.errors.map((e, i) => <div key={i}>— {e}</div>)}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={handlePurgeData}
                disabled={purgeInProgress}
                className="bg-rubric/10 hover:bg-rubric/20 border border-rubric text-rubric
                           font-mono text-xs tracking-widest uppercase px-5 py-2.5
                           transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                           flex items-center gap-2"
              >
                {purgeInProgress ? (
                  <>
                    <div className="animate-spin rounded-full h-3 w-3 border border-rubric border-t-transparent" />
                    PURGING...
                  </>
                ) : 'YES, DELETE EVERYTHING'}
              </button>
              <button
                onClick={() => setShowPurgeConfirmation(false)}
                disabled={purgeInProgress}
                className="px-5 py-2.5 border border-border text-dim hover:border-gold-dim hover:text-ink
                           font-mono text-xs tracking-widest uppercase transition-colors
                           disabled:opacity-40 disabled:cursor-not-allowed"
              >
                CANCEL
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
