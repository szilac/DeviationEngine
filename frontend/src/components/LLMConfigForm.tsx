/**
 * LLM Configuration Form Component.
 *
 * Form for configuring LLM provider, model selection, and API keys.
 */

import { useState, useEffect } from 'react';
import type { LLMProvider, LLMConfig, LLMConfigRequest, AvailableModels } from '../types';

interface LLMConfigFormProps {
  currentConfig: LLMConfig | null;
  availableModels: AvailableModels | null;
  onSave: (config: LLMConfigRequest) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const fieldLabel = "block font-caption text-xs text-dim tracking-widest uppercase mb-2";
const bottomInput = "w-full bg-transparent border-0 border-b border-border text-ink font-mono text-sm py-2 px-0 focus:outline-none focus:border-gold placeholder-faint transition-colors disabled:opacity-50";
const bottomSelect = "w-full appearance-none bg-transparent border-0 border-b border-border text-ink font-mono text-sm py-2 pl-0 pr-8 focus:outline-none focus:border-gold transition-colors cursor-pointer disabled:opacity-50";

export default function LLMConfigForm({
  currentConfig,
  availableModels,
  onSave,
  isLoading,
  error,
}: LLMConfigFormProps) {
  const [provider, setProvider] = useState<LLMProvider>('google');
  const [modelName, setModelName] = useState('');
  const [apiKeyGoogle, setApiKeyGoogle] = useState('');
  const [apiKeyOpenRouter, setApiKeyOpenRouter] = useState('');
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState('');
  const [showGoogleKey, setShowGoogleKey] = useState(false);
  const [showOpenRouterKey, setShowOpenRouterKey] = useState(false);
  const [apiKeyAnthropic, setApiKeyAnthropic] = useState('');
  const [apiKeyOpenAI, setApiKeyOpenAI] = useState('');
  const [showAnthropicKey, setShowAnthropicKey] = useState(false);
  const [showOpenAIKey, setShowOpenAIKey] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (currentConfig) {
      setProvider(currentConfig.provider);
      setModelName(currentConfig.model_name);
      setOllamaBaseUrl(currentConfig.ollama_base_url || '');
    }
  }, [currentConfig]);

  useEffect(() => {
    if (availableModels && provider) {
      const models = availableModels[provider];
      if (models && models.length > 0 && !models.includes(modelName)) {
        setModelName(models[0]);
      }
    }
  }, [provider, availableModels, modelName]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(false);

    const config: LLMConfigRequest = {
      provider,
      model_name: modelName,
      api_key_google: apiKeyGoogle || undefined,
      api_key_openrouter: apiKeyOpenRouter || undefined,
      api_key_anthropic: apiKeyAnthropic || undefined,
      api_key_openai: apiKeyOpenAI || undefined,
      ollama_base_url: ollamaBaseUrl || undefined,
    };

    await onSave(config);

    setSaveSuccess(true);
    setApiKeyGoogle('');
    setApiKeyOpenRouter('');
    setApiKeyAnthropic('');
    setApiKeyOpenAI('');
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleReset = () => {
    if (currentConfig) {
      setProvider(currentConfig.provider);
      setModelName(currentConfig.model_name);
      setApiKeyGoogle('');
      setApiKeyOpenRouter('');
      setApiKeyAnthropic('');
      setApiKeyOpenAI('');
      setOllamaBaseUrl(currentConfig.ollama_base_url || '');
      setSaveSuccess(false);
    }
  };

  const currentModels = availableModels?.[provider] || [];

  const providerHint: Record<LLMProvider, string> = {
    google: 'Direct Google Gemini API access',
    openrouter: 'OpenRouter provides access to multiple LLM providers',
    ollama: 'Run models locally with Ollama',
    anthropic: 'Direct Anthropic Claude API access',
    openai: 'Direct OpenAI API access',
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Provider */}
      <div>
        <label htmlFor="provider" className={fieldLabel}>LLM Provider</label>
        <div className="relative">
          <select
            id="provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value as LLMProvider)}
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
        <p className="mt-1.5 font-caption text-xs text-faint">{providerHint[provider]}</p>
      </div>

      {/* Model */}
      <div>
        <label htmlFor="model" className={fieldLabel}>
          Model
          <span className="ml-2 text-faint normal-case font-mono">{currentModels.length} available</span>
        </label>
        <div className="relative">
          <select
            id="model"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
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

      {/* Google API Key */}
      <div>
        <label htmlFor="apiKeyGoogle" className={fieldLabel}>
          Google Gemini API Key
        </label>
        <div className="flex items-end gap-4">
          <input
            type={showGoogleKey ? 'text' : 'password'}
            id="apiKeyGoogle"
            value={apiKeyGoogle}
            onChange={(e) => setApiKeyGoogle(e.target.value)}
            placeholder={currentConfig?.api_key_google_set ? '••••••••••••••••' : 'enter API key…'}
            autoComplete="off"
            spellCheck={false}
            className={`flex-1 ${bottomInput}`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowGoogleKey(!showGoogleKey)}
            aria-label={showGoogleKey ? 'Hide Google API key' : 'Show Google API key'}
            className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
            disabled={isLoading}
          >
            {showGoogleKey ? 'HIDE' : 'SHOW'}
          </button>
        </div>
        <p className="mt-1.5 font-caption text-xs text-faint">Leave empty to use environment variable</p>
      </div>

      {/* OpenRouter API Key */}
      <div>
        <label htmlFor="apiKeyOpenRouter" className={fieldLabel}>
          OpenRouter API Key
        </label>
        <div className="flex items-end gap-4">
          <input
            type={showOpenRouterKey ? 'text' : 'password'}
            id="apiKeyOpenRouter"
            value={apiKeyOpenRouter}
            onChange={(e) => setApiKeyOpenRouter(e.target.value)}
            placeholder={currentConfig?.api_key_openrouter_set ? '••••••••••••••••' : 'enter API key…'}
            autoComplete="off"
            spellCheck={false}
            className={`flex-1 ${bottomInput}`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowOpenRouterKey(!showOpenRouterKey)}
            aria-label={showOpenRouterKey ? 'Hide OpenRouter API key' : 'Show OpenRouter API key'}
            className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
            disabled={isLoading}
          >
            {showOpenRouterKey ? 'HIDE' : 'SHOW'}
          </button>
        </div>
        <p className="mt-1.5 font-caption text-xs text-faint">Leave empty to use environment variable</p>
      </div>

      {/* Anthropic API Key */}
      <div>
        <label htmlFor="apiKeyAnthropic" className={fieldLabel}>
          Anthropic API Key
        </label>
        <div className="flex items-end gap-4">
          <input
            type={showAnthropicKey ? 'text' : 'password'}
            id="apiKeyAnthropic"
            value={apiKeyAnthropic}
            onChange={(e) => setApiKeyAnthropic(e.target.value)}
            placeholder={currentConfig?.api_key_anthropic_set ? '••••••••••••••••' : 'enter API key…'}
            autoComplete="off"
            spellCheck={false}
            className={`flex-1 ${bottomInput}`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowAnthropicKey(!showAnthropicKey)}
            aria-label={showAnthropicKey ? 'Hide Anthropic API key' : 'Show Anthropic API key'}
            className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
            disabled={isLoading}
          >
            {showAnthropicKey ? 'HIDE' : 'SHOW'}
          </button>
        </div>
        <p className="mt-1.5 font-caption text-xs text-faint">Leave empty to use environment variable</p>
      </div>

      {/* OpenAI API Key */}
      <div>
        <label htmlFor="apiKeyOpenAI" className={fieldLabel}>
          OpenAI API Key
        </label>
        <div className="flex items-end gap-4">
          <input
            type={showOpenAIKey ? 'text' : 'password'}
            id="apiKeyOpenAI"
            value={apiKeyOpenAI}
            onChange={(e) => setApiKeyOpenAI(e.target.value)}
            placeholder={currentConfig?.api_key_openai_set ? '••••••••••••••••' : 'enter API key…'}
            autoComplete="off"
            spellCheck={false}
            className={`flex-1 ${bottomInput}`}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={() => setShowOpenAIKey(!showOpenAIKey)}
            aria-label={showOpenAIKey ? 'Hide OpenAI API key' : 'Show OpenAI API key'}
            className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
            disabled={isLoading}
          >
            {showOpenAIKey ? 'HIDE' : 'SHOW'}
          </button>
        </div>
        <p className="mt-1.5 font-caption text-xs text-faint">Leave empty to use environment variable</p>
      </div>

      {/* Warning */}
      <div className="border-l-2 border-warning pl-4 py-1">
        <p className="font-caption text-sm text-warning/90">
          Changes apply to all new timeline generations
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="border-l-2 border-rubric pl-4 py-1">
          <p className="font-caption text-sm text-rubric">{error}</p>
        </div>
      )}

      {/* Success */}
      {saveSuccess && (
        <div className="border-l-2 border-success pl-4 py-1">
          <p className="font-caption text-sm text-success">Configuration saved successfully</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={isLoading || !modelName}
          className="flex-1 bg-gold/10 hover:bg-gold/20 border border-gold text-gold
                     font-mono text-xs tracking-widest uppercase px-6 py-2.5
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isLoading ? 'SAVING…' : 'SAVE CONFIGURATION'}
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={isLoading}
          className="px-6 py-2.5 border border-border text-dim hover:border-gold-dim hover:text-ink
                     font-mono text-xs tracking-widest uppercase transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          RESET
        </button>
      </div>
    </form>
  );
}
