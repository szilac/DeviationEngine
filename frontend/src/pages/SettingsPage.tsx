/**
 * Settings Page Component.
 *
 * Main settings page for configuring application settings including LLM provider.
 */

import { useState, useEffect } from 'react';
import { useNotebookLMEnabled } from '../hooks/useNotebookLMEnabled';
import LLMConfigForm from '../components/LLMConfigForm';
import AgentLLMConfigManager from '../components/AgentLLMConfigManager';
import TranslationConfigManager from '../components/TranslationConfigManager';
import DebugSettingsManager from '../components/DebugSettingsManager';
import {
  getLLMConfig,
  updateLLMConfig,
  getAvailableModels,
  getAllLLMConfigs,
  setAgentLLMConfig,
  deleteAgentLLMConfig,
} from '../services/api';
import type {
  LLMConfig,
  LLMConfigRequest,
  AvailableModels,
  AllLLMConfigs,
  AgentType,
  AgentLLMConfigRequest,
} from '../types';

const ChevronIcon = ({ open }: { open: boolean }) => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="12" height="8" viewBox="0 0 12 8" fill="none"
    className={`transition-transform duration-300 ${open ? 'rotate-180' : ''}`}
  >
    <path d="M1 1l5 5 5-5" stroke="currentColor" strokeWidth="1.2"/>
  </svg>
);

const SECTIONS = [
  { id: 'llm',          roman: 'I',   label: 'Language Model',      desc: 'Global LLM provider, model selection, and API keys' },
  { id: 'agents',       roman: 'II',  label: 'Per-Agent Models',     desc: 'Override model configuration per AI agent' },
  { id: 'translation',  roman: 'III', label: 'Translation',          desc: 'DeepL API configuration and usage statistics' },
  { id: 'debug',        roman: 'IV',  label: 'Debug & Vector Store', desc: 'RAG settings, debug toggles, and data management' },
  { id: 'integrations', roman: 'V',   label: 'Integrations',         desc: 'Enable optional third-party CLI integrations' },
] as const;

type SectionId = (typeof SECTIONS)[number]['id'];

export default function SettingsPage() {
  const [currentConfig, setCurrentConfig] = useState<LLMConfig | null>(null);
  const [allLLMConfigs, setAllLLMConfigs] = useState<AllLLMConfigs | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);

  const [openSection, setOpenSection] = useState<SectionId | null>(null);
  const [nlmEnabled, setNlmEnabled] = useNotebookLMEnabled();

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      setAgentError(null);
      try {
        const [configResponse, allConfigsResponse, modelsResponse] = await Promise.all([
          getLLMConfig(),
          getAllLLMConfigs(),
          getAvailableModels(),
        ]);
        if (configResponse.error) {
          setError(configResponse.error.message);
        } else if (configResponse.data) {
          setCurrentConfig(configResponse.data);
        }
        if (allConfigsResponse.error) {
          setAgentError(allConfigsResponse.error.message);
        } else if (allConfigsResponse.data) {
          setAllLLMConfigs(allConfigsResponse.data);
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
        const allConfigsResponse = await getAllLLMConfigs();
        if (allConfigsResponse.data) setAllLLMConfigs(allConfigsResponse.data);
      }
    } catch {
      setError('Failed to save configuration. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAgentConfig = async (agentType: AgentType, config: AgentLLMConfigRequest) => {
    setIsSaving(true);
    setAgentError(null);
    try {
      const response = await setAgentLLMConfig(agentType, config);
      if (response.error) {
        setAgentError(response.error.message);
      } else {
        const allConfigsResponse = await getAllLLMConfigs();
        if (allConfigsResponse.data) setAllLLMConfigs(allConfigsResponse.data);
      }
    } catch {
      setAgentError('Failed to save agent configuration. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteAgentConfig = async (agentType: AgentType) => {
    setIsSaving(true);
    setAgentError(null);
    try {
      const response = await deleteAgentLLMConfig(agentType);
      if (response.error) {
        setAgentError(response.error.message);
      } else {
        const allConfigsResponse = await getAllLLMConfigs();
        if (allConfigsResponse.data) setAllLLMConfigs(allConfigsResponse.data);
      }
    } catch {
      setAgentError('Failed to delete agent configuration. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const toggle = (id: SectionId) =>
    setOpenSection((prev) => (prev === id ? null : id));

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
          <div className="space-y-0">
            {SECTIONS.map((section, idx) => {
              const isOpen = openSection === section.id;
              return (
                <div key={section.id}>
                  {/* Section */}
                  <section className="border border-border bg-surface">
                    {/* Section header button */}
                    <button
                      onClick={() => toggle(section.id)}
                      className="w-full px-6 py-5 flex items-start justify-between text-left hover:bg-overlay transition-colors"
                      aria-expanded={isOpen}
                      aria-controls={`settings-panel-${section.id}`}
                    >
                      <div>
                        <div className="rubric-label mb-1.5">
                          § {section.roman}.&nbsp;&nbsp;{section.label.toUpperCase()}
                        </div>
                        <p className="font-caption text-sm text-dim">{section.desc}</p>
                      </div>
                      <span className={`text-dim mt-1 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}>
                        <ChevronIcon open={isOpen} />
                      </span>
                    </button>

                    {/* Section content */}
                    {isOpen && (
                      <div
                        id={`settings-panel-${section.id}`}
                        className="border-t border-border px-6 py-6"
                      >
                        {section.id === 'llm' && (
                          isLoading ? null : (
                            <LLMConfigForm
                              currentConfig={currentConfig}
                              availableModels={availableModels}
                              onSave={handleSave}
                              isLoading={isSaving}
                              error={error}
                            />
                          )
                        )}
                        {section.id === 'agents' && (
                          isLoading ? null : (
                            <AgentLLMConfigManager
                              allConfigs={allLLMConfigs}
                              availableModels={availableModels}
                              onSaveAgentConfig={handleSaveAgentConfig}
                              onDeleteAgentConfig={handleDeleteAgentConfig}
                              isLoading={isSaving}
                              error={agentError}
                            />
                          )
                        )}
                        {section.id === 'translation' && (
                          <TranslationConfigManager isLoading={isSaving} />
                        )}
                        {section.id === 'debug' && (
                          <DebugSettingsManager isLoading={isSaving} />
                        )}
                        {section.id === 'integrations' && (
                          <div className="space-y-4">
                            <p className="font-caption text-sm text-dim">
                              Enable optional integrations that require third-party CLI tools installed on your machine.
                            </p>
                            <div className="flex items-center justify-between border border-border rounded px-4 py-3 bg-surface">
                              <div>
                                <div className="font-body text-sm text-ink font-medium">NotebookLM Podcast Generation</div>
                                <div className="font-caption text-xs text-dim mt-0.5">
                                  Requires the <code className="font-mono text-gold">nlm</code> CLI tool and a Google account.
                                  When enabled, a "NotebookLM Podcast" mode appears in the Audio Studio panel.
                                </div>
                              </div>
                              <button
                                role="switch"
                                aria-checked={nlmEnabled}
                                aria-label="NotebookLM Podcast Generation"
                                onClick={() => setNlmEnabled(!nlmEnabled)}
                                className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-vellum ${
                                  nlmEnabled ? 'bg-gold' : 'bg-border'
                                }`}
                              >
                                <span
                                  className={`inline-block h-4 w-4 transform rounded-full bg-surface shadow transition-transform ${
                                    nlmEnabled ? 'translate-x-6' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </section>

                  {/* Inter-section gap (not after last) */}
                  {idx < SECTIONS.length - 1 && <div className="h-px" />}
                </div>
              );
            })}
          </div>
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
