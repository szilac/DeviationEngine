/**
 * Agent LLM Configuration Manager Component.
 *
 * Manages per-agent LLM configurations, allowing different models for different AI agents.
 */

import { useState, useEffect } from 'react';
import type {
  AgentType,
  AgentLLMConfigRequest,
  AllLLMConfigs,
  AvailableModels,
  LLMProvider,
} from '../types';
import { AgentConfigUtils, AgentType as AgentTypeEnum } from '../types';

interface AgentLLMConfigManagerProps {
  allConfigs: AllLLMConfigs | null;
  availableModels: AvailableModels | null;
  onSaveAgentConfig: (agentType: AgentType, config: AgentLLMConfigRequest) => Promise<void>;
  onDeleteAgentConfig: (agentType: AgentType) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

interface AgentConfigFormState {
  provider: LLMProvider;
  modelName: string;
  apiKeyGoogle: string;
  apiKeyOpenRouter: string;
  apiKeyAnthropic: string;
  apiKeyOpenAI: string;
  ollamaBaseUrl: string;
  maxTokens: string;
  temperature: string;
  enabled: boolean;
}

const fieldLabel = "block font-caption text-xs text-dim tracking-widest uppercase mb-2";
const bottomInput = "w-full bg-transparent border-0 border-b border-border text-ink font-mono text-sm py-2 px-0 focus:outline-none focus:border-gold placeholder-faint transition-colors disabled:opacity-50";
const bottomSelect = "w-full appearance-none bg-transparent border-0 border-b border-border text-ink font-mono text-sm py-2 pl-0 pr-8 focus:outline-none focus:border-gold transition-colors cursor-pointer disabled:opacity-50";

const ChevronIcon = ({ open }: { open: boolean }) => (
  <svg
    width="12" height="8" viewBox="0 0 12 8" fill="none"
    className={`transition-transform ${open ? 'rotate-180' : ''}`}
  >
    <path d="M1 1l5 5 5-5" stroke="currentColor" strokeWidth="1.2"/>
  </svg>
);

export default function AgentLLMConfigManager({
  allConfigs,
  availableModels,
  onSaveAgentConfig,
  onDeleteAgentConfig,
  isLoading,
  error,
}: AgentLLMConfigManagerProps) {
  const [expandedAgent, setExpandedAgent] = useState<AgentType | null>(null);
  const [editingAgent, setEditingAgent] = useState<AgentType | null>(null);
  const [formState, setFormState] = useState<AgentConfigFormState>({
    provider: 'google',
    modelName: '',
    apiKeyGoogle: '',
    apiKeyOpenRouter: '',
    apiKeyAnthropic: '',
    apiKeyOpenAI: '',
    ollamaBaseUrl: '',
    maxTokens: '',
    temperature: '',
    enabled: true,
  });
  const [showGoogleKey, setShowGoogleKey] = useState(false);
  const [showOpenRouterKey, setShowOpenRouterKey] = useState(false);
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [showOpenAIKey, setShowOpenAIKey] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<AgentType | null>(null);

  const agents: AgentType[] = [
    AgentTypeEnum.HISTORIAN,
    AgentTypeEnum.STORYTELLER,
    AgentTypeEnum.SKELETON,
    AgentTypeEnum.SKELETON_HISTORIAN,
    AgentTypeEnum.ILLUSTRATOR,
    AgentTypeEnum.SCRIPT_WRITER,
    AgentTypeEnum.TRANSLATOR,
    AgentTypeEnum.CHARACTER_PROFILER,
    AgentTypeEnum.IMPERSONATOR,
    AgentTypeEnum.RIPPLE_ANALYST,
  ];

  useEffect(() => {
    if (editingAgent && allConfigs) {
      const config = allConfigs.agent_configs[editingAgent];
      if (config) {
        setFormState({
          provider: config.provider,
          modelName: config.model_name,
          apiKeyGoogle: '',
          apiKeyOpenRouter: '',
          apiKeyAnthropic: '',
          apiKeyOpenAI: '',
          ollamaBaseUrl: config.ollama_base_url || '',
          maxTokens: config.max_tokens?.toString() || '',
          temperature: config.temperature?.toString() || '',
          enabled: config.enabled,
        });
      } else {
        setFormState({
          provider: allConfigs.global_config.provider,
          modelName: allConfigs.global_config.model_name,
          apiKeyGoogle: '',
          apiKeyOpenRouter: '',
          apiKeyAnthropic: '',
          apiKeyOpenAI: '',
          ollamaBaseUrl: allConfigs.global_config.ollama_base_url || '',
          maxTokens: '',
          temperature: '',
          enabled: true,
        });
      }
    }
  }, [editingAgent, allConfigs]);

  useEffect(() => {
    if (availableModels && formState.provider) {
      const models = availableModels[formState.provider];
      if (models && models.length > 0 && !models.includes(formState.modelName)) {
        setFormState((prev) => ({ ...prev, modelName: models[0] }));
      }
    }
  }, [formState.provider, availableModels]);

  const handleSave = async (agentType: AgentType) => {
    setSaveSuccess(null);

    const config: AgentLLMConfigRequest = {
      agent_type: agentType,
      provider: formState.provider,
      model_name: formState.modelName,
      api_key_google: formState.apiKeyGoogle || undefined,
      api_key_openrouter: formState.apiKeyOpenRouter || undefined,
      api_key_anthropic: formState.apiKeyAnthropic || undefined,
      api_key_openai: formState.apiKeyOpenAI || undefined,
      ollama_base_url: formState.ollamaBaseUrl || undefined,
      max_tokens: formState.maxTokens ? parseInt(formState.maxTokens) : undefined,
      temperature: formState.temperature ? parseFloat(formState.temperature) : undefined,
      enabled: formState.enabled,
    };

    await onSaveAgentConfig(agentType, config);

    setSaveSuccess(agentType);
    setFormState((prev) => ({ ...prev, apiKeyGoogle: '', apiKeyOpenRouter: '', apiKeyAnthropic: '', apiKeyOpenAI: '' }));
    setEditingAgent(null);
    setShowGoogleKey(false);
    setShowOpenRouterKey(false);
    setShowAnthropicKey(false);
    setShowOpenAIKey(false);
    setTimeout(() => setSaveSuccess(null), 3000);
  };

  const handleDelete = async (agentType: AgentType) => {
    if (window.confirm(`Remove custom configuration for ${AgentConfigUtils.getAgentDisplayName(agentType)}? It will use the global configuration.`)) {
      await onDeleteAgentConfig(agentType);
      setEditingAgent(null);
    }
  };

  const handleCancel = () => {
    setEditingAgent(null);
    setShowGoogleKey(false);
    setShowOpenRouterKey(false);
    setShowAnthropicKey(false);
    setShowOpenAIKey(false);
  };

  const currentModels = availableModels?.[formState.provider] || [];
  const hasOverride = (agentType: AgentType) =>
    allConfigs?.agents_with_overrides.includes(agentType) || false;

  return (
    <div className="space-y-3">
      {/* Info */}
      <div className="border-l-2 border-quantum pl-4 py-1 mb-4">
        <p className="font-caption text-sm text-dim">
          Configure different LLM models per agent to optimize for cost or quality.
          Agents without custom configuration use the global settings.
        </p>
      </div>

      {/* Agent rows */}
      {agents.map((agentType) => {
        const isExpanded = expandedAgent === agentType;
        const isEditing = editingAgent === agentType;
        const config = allConfigs?.agent_configs[agentType];
        const effectiveConfig = allConfigs
          ? AgentConfigUtils.getEffectiveConfig(allConfigs, agentType)
          : null;

        return (
          <div
            key={agentType}
            className="border border-border bg-surface"
          >
            {/* Row header */}
            <button
              onClick={() => setExpandedAgent(isExpanded ? null : agentType)}
              className="w-full px-5 py-3.5 flex items-center justify-between hover:bg-overlay transition-colors text-left"
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="min-w-0">
                  <div className="font-body text-sm text-ink truncate">
                    {AgentConfigUtils.getAgentDisplayName(agentType)}
                  </div>
                  <div className="font-caption text-xs text-dim truncate mt-0.5">
                    {AgentConfigUtils.getAgentDescription(agentType)}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3 ml-4 shrink-0">
                {hasOverride(agentType) ? (
                  <span className="font-mono text-xs text-gold border border-gold-dim px-2 py-0.5 tracking-wide">
                    CUSTOM
                  </span>
                ) : (
                  <span className="font-mono text-xs text-faint border border-faint/30 px-2 py-0.5 tracking-wide">
                    GLOBAL
                  </span>
                )}
                <span className="text-dim">
                  <ChevronIcon open={isExpanded} />
                </span>
              </div>
            </button>

            {/* Expanded */}
            {isExpanded && (
              <div className="px-5 pb-5 border-t border-border">
                {!isEditing ? (
                  <div className="space-y-4 pt-4">
                    {/* Current config display */}
                    <dl className="space-y-2">
                      <div className="flex justify-between items-baseline">
                        <dt className="font-caption text-xs text-dim tracking-wide uppercase">Provider</dt>
                        <dd className="font-mono text-xs text-ink">
                          {effectiveConfig?.provider === 'google' && 'Google Gemini'}
                          {effectiveConfig?.provider === 'openrouter' && 'OpenRouter'}
                          {effectiveConfig?.provider === 'ollama' && 'Ollama (Local)'}
                          {effectiveConfig?.provider === 'anthropic' && 'Anthropic Claude'}
                          {effectiveConfig?.provider === 'openai' && 'OpenAI (ChatGPT)'}
                        </dd>
                      </div>
                      <div className="flex justify-between items-baseline">
                        <dt className="font-caption text-xs text-dim tracking-wide uppercase">Model</dt>
                        <dd className="font-mono text-xs text-ink">{effectiveConfig?.model_name}</dd>
                      </div>
                      {config?.max_tokens && (
                        <div className="flex justify-between items-baseline">
                          <dt className="font-caption text-xs text-dim tracking-wide uppercase">Max Tokens</dt>
                          <dd className="font-mono text-xs text-ink">{config.max_tokens}</dd>
                        </div>
                      )}
                      {config?.temperature && (
                        <div className="flex justify-between items-baseline">
                          <dt className="font-caption text-xs text-dim tracking-wide uppercase">Temperature</dt>
                          <dd className="font-mono text-xs text-ink">{config.temperature}</dd>
                        </div>
                      )}
                    </dl>

                    {saveSuccess === agentType && (
                      <div className="border-l-2 border-success pl-3 py-1">
                        <p className="font-caption text-xs text-success">Configuration saved</p>
                      </div>
                    )}

                    <div className="flex gap-2 pt-1">
                      <button
                        onClick={() => setEditingAgent(agentType)}
                        disabled={isLoading}
                        className="bg-gold/10 hover:bg-gold/20 border border-gold text-gold
                                   font-mono text-xs tracking-widest uppercase px-4 py-2
                                   transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {hasOverride(agentType) ? 'EDIT' : 'SET CUSTOM'}
                      </button>
                      {hasOverride(agentType) && (
                        <button
                          onClick={() => handleDelete(agentType)}
                          disabled={isLoading}
                          className="bg-rubric/10 hover:bg-rubric/20 border border-rubric-dim text-rubric
                                     font-mono text-xs tracking-widest uppercase px-4 py-2
                                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          REMOVE
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleSave(agentType); }}
                    className="space-y-5 pt-4"
                  >
                    {/* Provider */}
                    <div>
                      <label className={fieldLabel}>LLM Provider</label>
                      <div className="relative">
                        <select
                          value={formState.provider}
                          onChange={(e) => setFormState((prev) => ({ ...prev, provider: e.target.value as LLMProvider }))}
                          className={bottomSelect}
                          disabled={isLoading}
                        >
                          <option value="google" style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>Google Gemini</option>
                          <option value="openrouter" style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>OpenRouter</option>
                          <option value="anthropic" style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>Anthropic Claude</option>
                          <option value="openai" style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>OpenAI (ChatGPT)</option>
                        </select>
                        <span className="absolute right-0 top-1/2 -translate-y-1/2 text-dim pointer-events-none">
                          <svg width="12" height="7" viewBox="0 0 12 7" fill="none">
                            <path d="M1 1l5 5 5-5" stroke="currentColor" strokeWidth="1.2"/>
                          </svg>
                        </span>
                      </div>
                    </div>

                    {/* Model */}
                    <div>
                      <label className={fieldLabel}>Model</label>
                      <div className="relative">
                        <select
                          value={formState.modelName}
                          onChange={(e) => setFormState((prev) => ({ ...prev, modelName: e.target.value }))}
                          className={bottomSelect}
                          disabled={isLoading || currentModels.length === 0}
                        >
                          {currentModels.map((model) => (
                            <option key={model} value={model} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>{model}</option>
                          ))}
                        </select>
                        <span className="absolute right-0 top-1/2 -translate-y-1/2 text-dim pointer-events-none">
                          <svg width="12" height="7" viewBox="0 0 12 7" fill="none">
                            <path d="M1 1l5 5 5-5" stroke="currentColor" strokeWidth="1.2"/>
                          </svg>
                        </span>
                      </div>
                    </div>

                    {/* Advanced — collapsible */}
                    <details className="border border-border">
                      <summary className="px-4 py-2.5 cursor-pointer font-mono text-xs text-dim tracking-widest uppercase hover:text-ink transition-colors">
                        Advanced Settings (Optional)
                      </summary>
                      <div className="px-4 pb-4 pt-3 space-y-4 border-t border-border">
                        <div>
                          <label className={fieldLabel}>Max Tokens (1024–32768)</label>
                          <input
                            type="number"
                            value={formState.maxTokens}
                            onChange={(e) => setFormState((prev) => ({ ...prev, maxTokens: e.target.value }))}
                            placeholder="leave empty for default"
                            min="1024" max="32768"
                            className={bottomInput}
                            disabled={isLoading}
                          />
                        </div>
                        <div>
                          <label className={fieldLabel}>Temperature (0.0–2.0)</label>
                          <input
                            type="number"
                            value={formState.temperature}
                            onChange={(e) => setFormState((prev) => ({ ...prev, temperature: e.target.value }))}
                            placeholder="leave empty for default"
                            min="0" max="2" step="0.1"
                            className={bottomInput}
                            disabled={isLoading}
                          />
                        </div>
                        <div>
                          <label className={fieldLabel}>Google API Key Override</label>
                          <div className="flex items-end gap-4">
                            <input
                              type={showGoogleKey ? 'text' : 'password'}
                              value={formState.apiKeyGoogle}
                              onChange={(e) => setFormState((prev) => ({ ...prev, apiKeyGoogle: e.target.value }))}
                              placeholder="leave empty to use global"
                              className={`flex-1 ${bottomInput}`}
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowGoogleKey(!showGoogleKey)}
                              className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
                            >
                              {showGoogleKey ? 'HIDE' : 'SHOW'}
                            </button>
                          </div>
                        </div>
                        <div>
                          <label className={fieldLabel}>OpenRouter API Key Override</label>
                          <div className="flex items-end gap-4">
                            <input
                              type={showOpenRouterKey ? 'text' : 'password'}
                              value={formState.apiKeyOpenRouter}
                              onChange={(e) => setFormState((prev) => ({ ...prev, apiKeyOpenRouter: e.target.value }))}
                              placeholder="leave empty to use global"
                              className={`flex-1 ${bottomInput}`}
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowOpenRouterKey(!showOpenRouterKey)}
                              className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
                            >
                              {showOpenRouterKey ? 'HIDE' : 'SHOW'}
                            </button>
                          </div>
                        </div>
                        {/* Anthropic API Key Override */}
                        <div>
                          <label className={fieldLabel}>Anthropic API Key Override</label>
                          <div className="flex items-end gap-4">
                            <input
                              type={showAnthropicKey ? 'text' : 'password'}
                              value={formState.apiKeyAnthropic}
                              onChange={(e) => setFormState((prev) => ({ ...prev, apiKeyAnthropic: e.target.value }))}
                              placeholder="leave empty to use global"
                              className={`flex-1 ${bottomInput}`}
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                              className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
                            >
                              {showAnthropicKey ? 'HIDE' : 'SHOW'}
                            </button>
                          </div>
                        </div>
                        {/* OpenAI API Key Override */}
                        <div>
                          <label className={fieldLabel}>OpenAI API Key Override</label>
                          <div className="flex items-end gap-4">
                            <input
                              type={showOpenAIKey ? 'text' : 'password'}
                              value={formState.apiKeyOpenAI}
                              onChange={(e) => setFormState((prev) => ({ ...prev, apiKeyOpenAI: e.target.value }))}
                              placeholder="leave empty to use global"
                              className={`flex-1 ${bottomInput}`}
                              disabled={isLoading}
                            />
                            <button
                              type="button"
                              onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                              className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
                            >
                              {showOpenAIKey ? 'HIDE' : 'SHOW'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </details>

                    {error && (
                      <div className="border-l-2 border-rubric pl-3 py-1">
                        <p className="font-caption text-xs text-rubric">{error}</p>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={isLoading || !formState.modelName}
                        className="flex-1 bg-gold/10 hover:bg-gold/20 border border-gold text-gold
                                   font-mono text-xs tracking-widest uppercase px-4 py-2.5
                                   transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {isLoading ? 'SAVING...' : 'SAVE'}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancel}
                        disabled={isLoading}
                        className="px-4 py-2.5 border border-border text-dim hover:border-gold-dim hover:text-ink
                                   font-mono text-xs tracking-widest uppercase transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        CANCEL
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
