/**
 * Advanced Settings Page Component.
 *
 * Advanced configuration: per-agent models, translation, debug, and integrations.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useNotebookLMEnabled } from '../hooks/useNotebookLMEnabled';
import { useCLIProxyEnabled } from '../hooks/useCLIProxyEnabled';
import AgentLLMConfigManager from '../components/AgentLLMConfigManager';
import TranslationConfigManager from '../components/TranslationConfigManager';
import DebugSettingsManager from '../components/DebugSettingsManager';
import {
  getAvailableModels,
  getAllLLMConfigs,
  setAgentLLMConfig,
  deleteAgentLLMConfig,
} from '../services/api';
import type {
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

const ADVANCED_SECTIONS = [
  { id: 'agents',       roman: 'II',  label: 'Per-Agent Models',     desc: 'Override model configuration per AI agent' },
  { id: 'translation',  roman: 'III', label: 'Translation',          desc: 'DeepL API configuration and usage statistics' },
  { id: 'debug',        roman: 'IV',  label: 'Debug & Vector Store', desc: 'RAG settings, debug toggles, and data management' },
  { id: 'integrations', roman: 'V',   label: 'Integrations',         desc: 'Enable optional third-party CLI integrations' },
] as const;

type AdvancedSectionId = (typeof ADVANCED_SECTIONS)[number]['id'];

export default function AdvancedSettingsPage() {
  const [allLLMConfigs, setAllLLMConfigs] = useState<AllLLMConfigs | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);

  const [openSection, setOpenSection] = useState<AdvancedSectionId | null>(null);
  const [nlmEnabled, setNlmEnabled] = useNotebookLMEnabled();
  const [clipProxyEnabled, setClipProxyEnabled] = useCLIProxyEnabled();

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setAgentError(null);
      try {
        const [allConfigsResponse, modelsResponse] = await Promise.all([
          getAllLLMConfigs(),
          getAvailableModels(),
        ]);
        if (allConfigsResponse.error) {
          setAgentError(allConfigsResponse.error.message);
        } else if (allConfigsResponse.data) {
          setAllLLMConfigs(allConfigsResponse.data);
        }
        if (modelsResponse.data) {
          setAvailableModels(modelsResponse.data);
        }
      } catch {
        setAgentError('Failed to load settings. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

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

  const toggle = (id: AdvancedSectionId) =>
    setOpenSection((prev) => (prev === id ? null : id));

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-[720px] mx-auto">

        {/* Back link */}
        <div className="mb-6">
          <Link
            to="/settings"
            className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold transition-colors"
          >
            ← Provider Setup
          </Link>
        </div>

        {/* Page header */}
        <div className="mb-10">
          <h1 className="font-display text-4xl text-gold mb-1">Advanced Configuration</h1>
          <p className="font-caption text-base text-dim italic">
            Per-agent models, translation, debug, and integrations
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
            {ADVANCED_SECTIONS.map((section, idx) => {
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
                        {section.id === 'agents' && (
                          <AgentLLMConfigManager
                            allConfigs={allLLMConfigs}
                            availableModels={availableModels}
                            onSaveAgentConfig={handleSaveAgentConfig}
                            onDeleteAgentConfig={handleDeleteAgentConfig}
                            isLoading={isSaving}
                            error={agentError}
                          />
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

                            {/* NotebookLM */}
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

                            {/* CLIProxy */}
                            <div className="border border-border rounded bg-surface">
                              <div className="flex items-center justify-between px-4 py-3">
                                <div>
                                  <div className="font-body text-sm text-ink font-medium">CLIProxy — Subscription API Bridge</div>
                                  <div className="font-caption text-xs text-dim mt-0.5">
                                    Use your existing <strong className="text-ink">Claude Pro/Max</strong> or <strong className="text-ink">OpenAI</strong> subscription
                                    as an API — no extra token costs.
                                    When enabled, "CLIProxy (Subscription)" appears as a provider option in § I.
                                  </div>
                                </div>
                                <button
                                  role="switch"
                                  aria-checked={clipProxyEnabled}
                                  aria-label="CLIProxy Subscription Bridge"
                                  onClick={() => setClipProxyEnabled(!clipProxyEnabled)}
                                  className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-vellum ${
                                    clipProxyEnabled ? 'bg-gold' : 'bg-border'
                                  }`}
                                >
                                  <span
                                    className={`inline-block h-4 w-4 transform rounded-full bg-surface shadow transition-transform ${
                                      clipProxyEnabled ? 'translate-x-6' : 'translate-x-1'
                                    }`}
                                  />
                                </button>
                              </div>

                              {/* Installation instructions — shown when enabled */}
                              {clipProxyEnabled && (
                                <div className="border-t border-border px-4 py-4 space-y-3">
                                  <p className="font-caption text-xs text-dim">
                                    CLIProxyAPI wraps the Claude Code or OpenAI CLI and exposes a local OpenAI-compatible endpoint at{' '}
                                    <code className="font-mono text-gold">http://localhost:8317/v1</code>.
                                    No API key is required — it authenticates through your subscription.
                                  </p>
                                  <div className="space-y-1.5">
                                    <p className="font-mono text-xs text-dim tracking-widest uppercase">Installation</p>
                                    <ol className="space-y-1 font-caption text-xs text-dim list-decimal list-inside">
                                      <li>
                                        Install:{' '}
                                        <code className="font-mono text-gold">
                                          bash &lt;(curl -fsSL https://github.com/router-for-me/CLIProxyAPI/releases/latest/download/install.sh)
                                        </code>
                                      </li>
                                      <li>
                                        Authenticate:{' '}
                                        <code className="font-mono text-gold">cliproxyapi --browser-auth</code>
                                        {' '}(one-time, opens a browser)
                                      </li>
                                      <li>
                                        Start the proxy:{' '}
                                        <code className="font-mono text-gold">cliproxyapi</code>
                                        {' '}(keep it running while using Deviation Engine)
                                      </li>
                                      <li>
                                        Go to § I. Language Model, select <strong className="text-ink">CLIProxy (Subscription)</strong>,
                                        pick a model, and save.
                                      </li>
                                    </ol>
                                  </div>
                                  <p className="font-caption text-xs text-faint">
                                    Source & docs: github.com/router-for-me/CLIProxyAPI
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </section>

                  {/* Inter-section gap (not after last) */}
                  {idx < ADVANCED_SECTIONS.length - 1 && <div className="h-px" />}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
