/**
 * Settings Page Component.
 *
 * Provider setup page: LLM configuration and link to advanced settings.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import LLMConfigForm from '../components/LLMConfigForm';
import {
  getLLMConfig,
  updateLLMConfig,
  getAvailableModels,
} from '../services/api';
import type {
  LLMConfig,
  LLMConfigRequest,
  AvailableModels,
} from '../types';

export default function SettingsPage() {
  const [currentConfig, setCurrentConfig] = useState<LLMConfig | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [configResponse, modelsResponse] = await Promise.all([
          getLLMConfig(),
          getAvailableModels(),
        ]);
        if (configResponse.error) {
          setError(configResponse.error.message);
        } else if (configResponse.data) {
          setCurrentConfig(configResponse.data);
        }
        if (modelsResponse.error) {
          setError(modelsResponse.error.message);
        } else if (modelsResponse.data) {
          setAvailableModels(modelsResponse.data);
        }
      } catch {
        setError('Failed to load settings. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSave = async (config: LLMConfigRequest) => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await updateLLMConfig(config);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setCurrentConfig(response.data);
      }
    } catch {
      setError('Failed to save configuration. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-[720px] mx-auto">

        {/* Page header */}
        <div className="mb-10">
          <h1 className="font-display text-4xl text-gold mb-1">Configuration</h1>
          <p className="font-caption text-base text-dim italic">
            Deviation Engine operational parameters
          </p>
          <div className="double-rule mt-4" />
        </div>

        {/* Global loading spinner */}
        {isLoading && (
          <div className="flex items-center justify-center py-16" role="status" aria-label="Loading settings…">
            <div aria-hidden="true" className="animate-spin h-8 w-8 border border-gold rounded-full border-t-transparent" />
          </div>
        )}

        {!isLoading && (
          <>
            {/* Section I — Language Model */}
            <section className="border border-border bg-surface">
              <div className="px-6 py-5">
                <div className="rubric-label mb-1.5">§ I.&nbsp;&nbsp;LANGUAGE MODEL</div>
                <p className="font-caption text-sm text-dim">
                  Global LLM provider, model selection, and API keys
                </p>
              </div>
              <div className="border-t border-border px-6 py-6">
                <LLMConfigForm
                  currentConfig={currentConfig}
                  availableModels={availableModels}
                  onSave={handleSave}
                  isLoading={isSaving}
                  error={error}
                />
              </div>
            </section>

            {/* Advanced link */}
            <div className="mt-4">
              <Link
                to="/settings/advanced"
                className="block border border-border bg-surface px-6 py-5 hover:bg-overlay transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="rubric-label mb-1.5">§ II–V.&nbsp;&nbsp;ADVANCED CONFIGURATION</div>
                    <p className="font-caption text-sm text-dim">
                      Per-agent models, translation, debug settings, and integrations
                    </p>
                  </div>
                  <span className="font-mono text-xs text-dim group-hover:text-gold transition-colors">→</span>
                </div>
              </Link>
            </div>
          </>
        )}

        {/* Global config summary */}
        {currentConfig && !isLoading && (
          <div className="mt-8 border border-border bg-surface">
            <div className="px-6 pt-5 pb-2">
              <div className="rubric-label mb-4">§ Global Configuration Summary</div>
            </div>
            <div className="double-rule mx-6" />
            <dl className="px-6 py-4 space-y-2.5">
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">Provider</dt>
                <dd className="font-mono text-xs text-ink">
                  {currentConfig.provider === 'google' && 'Google Gemini'}
                  {currentConfig.provider === 'openrouter' && 'OpenRouter'}
                  {currentConfig.provider === 'ollama' && 'Ollama (Local)'}
                  {currentConfig.provider === 'anthropic' && 'Anthropic Claude'}
                  {currentConfig.provider === 'openai' && 'OpenAI (ChatGPT)'}
                  {currentConfig.provider === 'cliproxy' && 'CLIProxy (Subscription)'}
                </dd>
              </div>
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">Model</dt>
                <dd className="font-mono text-xs text-ink">{currentConfig.model_name}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
