/**
 * Translation Configuration Manager Component
 *
 * Manages DeepL API configuration and displays translation usage statistics.
 * Includes API key management, tier selection, usage tracking, and connection testing.
 */

import { useState, useEffect } from 'react';
import { getTranslationConfig, updateTranslationConfig, getTranslationUsage } from '../services/api';
import type { TranslationConfig, TranslationConfigRequest, TranslationUsage } from '../types';

interface TranslationConfigManagerProps {
  isLoading?: boolean;
}

const fieldLabel = "block font-caption text-xs text-dim tracking-widest uppercase mb-2";
const bottomInput = "w-full bg-transparent border-0 border-b border-border text-ink font-mono text-sm py-2 px-0 focus:outline-none focus:border-gold placeholder-faint transition-colors";

const LANGUAGES = [
  { code: 'hu', name: 'Magyar', flag: '🇭🇺' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'pt', name: 'Português', flag: '🇵🇹' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
];

export const TranslationConfigManager: React.FC<TranslationConfigManagerProps> = ({
  isLoading: externalLoading = false,
}) => {
  const [config, setConfig] = useState<TranslationConfig | null>(null);
  const [usage, setUsage] = useState<TranslationUsage | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [apiKey, setApiKey] = useState('');
  const [apiTier, setApiTier] = useState<'free' | 'pro'>('free');
  const [enabled, setEnabled] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    setIsLoadingData(true);
    setError(null);
    try {
      const [configResponse, usageResponse] = await Promise.all([
        getTranslationConfig(),
        getTranslationUsage(),
      ]);
      if (configResponse.error) {
        setError(configResponse.error.message);
      } else if (configResponse.data) {
        setConfig(configResponse.data);
        setApiTier(configResponse.data.api_tier);
        setEnabled(configResponse.data.enabled);
      }
      if (usageResponse.data) {
        setUsage(usageResponse.data);
      }
    } catch (err) {
      setError('Failed to load translation settings');
      console.error('Translation config fetch error:', err);
    } finally {
      setIsLoadingData(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) { setError('Please enter a DeepL API key'); return; }
    setIsSaving(true); setError(null); setSuccessMessage(null);
    try {
      const request: TranslationConfigRequest = { api_key: apiKey.trim(), api_tier: apiTier, enabled };
      const response = await updateTranslationConfig(request);
      if (response.error) {
        setError(response.error.message);
      } else if (response.data) {
        setConfig(response.data);
        setSuccessMessage('Translation configuration saved successfully');
        setApiKey('');
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (err) {
      setError('Failed to save configuration. Please try again.');
      console.error('Translation config save error:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnection = async () => {
    if (!config?.api_key_set) { setError('Please save your API key first before testing'); return; }
    setIsTesting(true); setError(null); setSuccessMessage(null);
    try {
      const response = await getTranslationUsage();
      if (response.error) {
        setError(`Connection test failed: ${response.error.message}`);
      } else {
        setSuccessMessage('Connection successful — DeepL API is working correctly');
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch {
      setError('Connection test failed. Please check your API key.');
    } finally {
      setIsTesting(false);
    }
  };

  const formatNumber = (num: number) => new Intl.NumberFormat().format(num);

  const getUsageBarColor = (pct: number) => {
    if (pct >= 90) return 'bg-rubric';
    if (pct >= 75) return 'bg-warning';
    return 'bg-success';
  };

  const isLoading = isLoadingData || externalLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin h-8 w-8 border border-gold rounded-full border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Error / Success */}
      {error && (
        <div className="border-l-2 border-rubric pl-4 py-1">
          <p className="font-caption text-sm text-rubric">{error}</p>
        </div>
      )}
      {successMessage && (
        <div className="border-l-2 border-success pl-4 py-1">
          <p className="font-caption text-sm text-success">{successMessage}</p>
        </div>
      )}

      {/* API Configuration */}
      <div className="space-y-5">
        <p className="rubric-label">DeepL API Configuration</p>

        {/* API Key */}
        <div>
          <label htmlFor="deepl-api-key" className={fieldLabel}>
            API Key
            {config?.api_key_set && (
              <span className="ml-2 text-success normal-case font-mono">✓ configured</span>
            )}
          </label>
          <div className="flex items-end gap-4">
            <input
              id="deepl-api-key"
              type={showApiKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config?.api_key_set ? '••••••••••••••••••••••:fx' : 'enter your DeepL API key'}
              className={`flex-1 ${bottomInput}`}
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="font-mono text-xs text-dim hover:text-gold transition-colors pb-2 whitespace-nowrap"
            >
              {showApiKey ? 'HIDE' : 'SHOW'}
            </button>
          </div>
          <p className="mt-1.5 font-caption text-xs text-faint">
            Free API key at{' '}
            <a
              href="https://www.deepl.com/pro-api"
              target="_blank"
              rel="noopener noreferrer"
              className="text-quantum hover:text-wave transition-colors"
            >
              deepl.com/pro-api
            </a>
            {' '}— 500,000 chars/month free
          </p>
        </div>

        {/* API Tier */}
        <div>
          <label className={fieldLabel}>API Tier</label>
          <div className="flex gap-6">
            {(['free', 'pro'] as const).map((tier) => (
              <label key={tier} className="flex items-center gap-2.5 cursor-pointer group">
                <span
                  onClick={() => setApiTier(tier)}
                  className={`w-4 h-4 border flex items-center justify-center transition-colors cursor-pointer
                    ${apiTier === tier ? 'border-gold bg-gold/10' : 'border-border hover:border-gold-dim'}`}
                >
                  {apiTier === tier && (
                    <span className="w-2 h-2 bg-gold block" />
                  )}
                </span>
                <span
                  onClick={() => setApiTier(tier)}
                  className={`font-mono text-xs tracking-wide transition-colors cursor-pointer
                    ${apiTier === tier ? 'text-ink' : 'text-dim group-hover:text-ink'}`}
                >
                  {tier === 'free' ? 'FREE (500k chars/mo)' : 'PRO'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Enable toggle */}
        <div className="flex items-center justify-between py-2">
          <div>
            <div className="font-caption text-sm text-ink">Enable Translation Service</div>
            <div className="font-caption text-xs text-dim mt-0.5">Allow users to translate generated content</div>
          </div>
          <button
            type="button"
            onClick={() => setEnabled(!enabled)}
            className={`relative w-10 h-5 border transition-colors shrink-0
              ${enabled ? 'border-gold bg-gold/10' : 'border-border bg-transparent'}`}
            aria-label="Toggle translation service"
          >
            <span
              className={`absolute top-1 w-3 h-3 transition-all duration-200
                ${enabled ? 'left-5 bg-gold' : 'left-1 bg-faint'}`}
            />
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 pt-1">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex-1 bg-gold/10 hover:bg-gold/20 border border-gold text-gold
                       font-mono text-xs tracking-widest uppercase px-5 py-2.5
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isSaving ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                SAVING...
              </>
            ) : 'SAVE CONFIGURATION'}
          </button>
          <button
            onClick={handleTestConnection}
            disabled={isTesting || !config?.api_key_set}
            className="px-5 py-2.5 border border-border text-dim hover:border-gold-dim hover:text-ink
                       font-mono text-xs tracking-widest uppercase transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed
                       flex items-center gap-2"
          >
            {isTesting ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                TESTING...
              </>
            ) : 'TEST CONNECTION'}
          </button>
        </div>
      </div>

      {/* Double rule */}
      <div className="double-rule" />

      {/* Supported Languages */}
      <div className="space-y-3">
        <p className="rubric-label">Supported Languages</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-y-2 gap-x-4">
          {LANGUAGES.map((lang) => (
            <div key={lang.code} className="flex items-center gap-2">
              <span className="text-xl">{lang.flag}</span>
              <span className="font-caption text-sm text-dim">{lang.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Usage Statistics */}
      {usage && (
        <>
          <div className="double-rule" />
          <div className="space-y-4">
            <p className="rubric-label">Usage — {usage.year_month}</p>

            {/* Progress bar */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="font-caption text-xs text-dim">Monthly usage</span>
                <span className="font-mono text-xs text-ink">{usage.percentage_used.toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-surface border border-border overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getUsageBarColor(usage.percentage_used)}`}
                  style={{ width: `${Math.min(usage.percentage_used, 100)}%` }}
                />
              </div>
              <div className="flex justify-between mt-1.5">
                <span className="font-mono text-xs text-dim">{formatNumber(usage.characters_used)} chars used</span>
                <span className="font-mono text-xs text-faint">{formatNumber(usage.characters_limit)} limit</span>
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="border border-border bg-surface p-4">
                <div className="font-caption text-xs text-dim mb-1 tracking-wide uppercase">Characters Used</div>
                <div className="font-mono text-xl text-ink">{formatNumber(usage.characters_used)}</div>
              </div>
              <div className="border border-border bg-surface p-4">
                <div className="font-caption text-xs text-dim mb-1 tracking-wide uppercase">API Calls</div>
                <div className="font-mono text-xl text-ink">{usage.api_calls}</div>
              </div>
            </div>

            {usage.percentage_used >= 90 && (
              <div className="border-l-2 border-rubric pl-4 py-1">
                <div className="font-caption text-sm text-rubric font-semibold">Quota Warning</div>
                <div className="font-caption text-xs text-rubric/80 mt-0.5">
                  {usage.percentage_used.toFixed(1)}% of monthly limit used. Consider upgrading to Pro.
                </div>
              </div>
            )}
            {usage.percentage_used >= 75 && usage.percentage_used < 90 && (
              <div className="border-l-2 border-warning pl-4 py-1">
                <div className="font-caption text-xs text-warning/90">
                  {usage.percentage_used.toFixed(1)}% used — {formatNumber(usage.characters_limit - usage.characters_used)} characters remaining.
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Config Status */}
      {config && (
        <>
          <div className="double-rule" />
          <div className="space-y-3">
            <p className="rubric-label">Configuration Status</p>
            <dl className="space-y-2">
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">Service Status</dt>
                <dd className={`font-mono text-xs ${config.enabled ? 'text-success' : 'text-faint'}`}>
                  {config.enabled ? '◉ ACTIVE' : '○ DISABLED'}
                </dd>
              </div>
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">API Key</dt>
                <dd className={`font-mono text-xs ${config.api_key_set ? 'text-success' : 'text-faint'}`}>
                  {config.api_key_set ? '✓ CONFIGURED' : 'NOT SET'}
                </dd>
              </div>
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">API Tier</dt>
                <dd className="font-mono text-xs text-ink capitalize">{config.api_tier}</dd>
              </div>
              <div className="flex justify-between items-baseline">
                <dt className="font-caption text-xs text-dim tracking-wide uppercase">Last Updated</dt>
                <dd className="font-mono text-xs text-dim">{new Date(config.updated_at).toLocaleString()}</dd>
              </div>
            </dl>
          </div>
        </>
      )}
    </div>
  );
};

export default TranslationConfigManager;
