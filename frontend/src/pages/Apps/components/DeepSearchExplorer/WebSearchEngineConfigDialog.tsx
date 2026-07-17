import React, { useEffect, useMemo, useState } from 'react';
import { Eye, EyeOff, Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import {
  WEB_SEARCH_ENGINE_PRESETS,
  type DeepSearchWebSearchEngineConfig,
  type WebSearchEngineName,
} from './webSearchFetchTypes';

interface WebSearchEngineConfigDialogProps {
  open: boolean;
  config?: DeepSearchWebSearchEngineConfig;
  onConfirm: (config: DeepSearchWebSearchEngineConfig) => void;
  onCancel: () => void;
}

interface DomainEditorProps {
  label: string;
  domains: string[];
  onChange: (domains: string[]) => void;
}

const emptyConfig = {
  searchEngineName: undefined as WebSearchEngineName | undefined,
  searchApiKey: '',
  searchUrl: '',
  extensionJson: '',
  includeDomains: [] as string[],
  excludeDomains: [] as string[],
  maxWebSearchResults: 5,
};

const normalizeDomains = (domains: string[]) => [...new Set(domains.map(domain => domain.trim()).filter(Boolean))];

const DomainEditor: React.FC<DomainEditorProps> = ({ label, domains, onChange }) => {
  const [domain, setDomain] = useState('');

  const addDomain = () => {
    const additions = domain
      .split(';')
      .map(item => item.trim())
      .filter(Boolean);
    if (additions.length === 0) return;
    onChange(normalizeDomains([...domains, ...additions]));
    setDomain('');
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div className="flex gap-2">
        <input
          aria-label={label}
          value={domain}
          onChange={event => setDomain(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter') {
              event.preventDefault();
              addDomain();
            }
          }}
          placeholder="example.com"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={addDomain}
          className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-blue-700 hover:bg-blue-100"
          aria-label={`${label} add`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {domains.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {domains.map(item => (
            <span
              key={item}
              className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700"
            >
              {item}
              <button
                type="button"
                onClick={() => onChange(domains.filter(domainItem => domainItem !== item))}
                aria-label={`${label} remove ${item}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export const WebSearchEngineSummaryCard: React.FC<{
  config?: DeepSearchWebSearchEngineConfig;
  onConfigure: () => void;
  onTest?: () => void;
  testStatus?: 'untested' | 'passed' | 'failed';
}> = ({ config, onConfigure, onTest, testStatus = 'untested' }) => {
  const { t } = useTranslation();
  const testStatusClass = testStatus === 'passed'
    ? 'bg-green-100 text-green-700'
    : testStatus === 'failed'
      ? 'bg-red-100 text-red-700'
      : 'bg-amber-100 text-amber-700';
  const testStatusLabel = testStatus === 'passed'
    ? t('apps.config.deepSearchProviderTest.passed')
    : testStatus === 'failed'
      ? t('apps.config.deepSearchProviderTest.failedStatus')
      : t('apps.config.deepSearchProviderTest.required');

  return (
    <div data-testid="web-search-summary-card" className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-gray-900">{t('apps.config.deepSearchWebSearch.summaryTitle')}</p>
          <p className="mt-1 text-sm text-gray-500">
            {config
              ? t('apps.config.deepSearchWebSearch.configuredProvider', { provider: config.searchEngineName })
              : t('apps.config.deepSearchWebSearch.notConfigured')}
          </p>
          {config && (
            <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${testStatusClass}`}>
              {testStatusLabel}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onTest && (
            <button
              type="button"
              onClick={onTest}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {t('apps.config.deepSearchProviderTest.test')}
            </button>
          )}
          <button
            type="button"
            onClick={onConfigure}
            className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            {t('apps.config.deepSearchWebSearch.configure')}
          </button>
        </div>
      </div>
    </div>
  );
};

const WebSearchEngineConfigDialog: React.FC<WebSearchEngineConfigDialogProps> = ({
  open,
  config,
  onConfirm,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(emptyConfig);
  const [showApiKey, setShowApiKey] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setDraft({
      searchEngineName: config?.searchEngineName,
      searchApiKey: config?.searchApiKey ?? '',
      searchUrl: config?.searchUrl ?? '',
      extensionJson: config?.extensionJson ?? '',
      includeDomains: config?.includeDomains ?? [],
      excludeDomains: config?.excludeDomains ?? [],
      maxWebSearchResults: config?.maxWebSearchResults ?? 5,
    });
    setShowApiKey(false);
    setError('');
  }, [config, open]);

  const selectedPreset = useMemo(
    () => WEB_SEARCH_ENGINE_PRESETS.find(preset => preset.name === draft.searchEngineName),
    [draft.searchEngineName],
  );

  if (!open) return null;

  const confirm = () => {
    if (!draft.searchEngineName || !draft.searchApiKey.trim() || !draft.searchUrl.trim()) {
      setError(t('apps.config.deepSearchWebSearch.required'));
      return;
    }

    if (draft.extensionJson.trim()) {
      try {
        const extension: unknown = JSON.parse(draft.extensionJson);
        if (extension === null || typeof extension !== 'object' || Array.isArray(extension)) {
          setError(t('apps.config.deepSearchWebSearch.invalidExtensionObject'));
          return;
        }
      } catch {
        setError(t('apps.config.deepSearchWebSearch.invalidExtension'));
        return;
      }
    }

    onConfirm({
      searchEngineName: draft.searchEngineName,
      searchApiKey: draft.searchApiKey.trim(),
      searchUrl: draft.searchUrl.trim(),
      ...(draft.extensionJson.trim() ? { extensionJson: draft.extensionJson.trim() } : {}),
      ...(draft.searchEngineName === 'tavily'
        ? {
            includeDomains: normalizeDomains(draft.includeDomains),
            excludeDomains: normalizeDomains(draft.excludeDomains),
          }
        : {}),
      maxWebSearchResults: draft.maxWebSearchResults,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{t('apps.config.deepSearchWebSearch.title')}</h2>
          <button type="button" onClick={onCancel} aria-label={t('apps.config.deepSearchWebSearch.cancel')}>
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">{t('apps.config.deepSearchWebSearch.preset')}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {WEB_SEARCH_ENGINE_PRESETS.map(preset => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => {
                    setDraft(current => {
                      if (current.searchEngineName === preset.name) return current;
                      return {
                        ...emptyConfig,
                        searchEngineName: preset.name,
                        searchUrl: preset.defaultSearchUrl,
                      };
                    });
                    setError('');
                  }}
                  className={`rounded-lg border px-3 py-2 text-left text-sm ${
                    selectedPreset?.name === preset.name
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700">
              {t('apps.config.deepSearchWebSearch.apiKey')}
            </span>
            <div className="relative">
              <input
                aria-label={t('apps.config.deepSearchWebSearch.apiKey')}
                type={showApiKey ? 'text' : 'password'}
                value={draft.searchApiKey}
                onChange={event => setDraft(current => ({ ...current, searchApiKey: event.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 text-sm"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(current => !current)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500"
                aria-label={
                  showApiKey
                    ? t('apps.config.deepSearchWebSearch.hideApiKey')
                    : t('apps.config.deepSearchWebSearch.showApiKey')
                }
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700">
              {t('apps.config.deepSearchWebSearch.searchUrl')}
            </span>
            <input
              aria-label={t('apps.config.deepSearchWebSearch.searchUrl')}
              type="url"
              value={draft.searchUrl}
              onChange={event => setDraft(current => ({ ...current, searchUrl: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>

          {draft.searchEngineName === 'tavily' && (
            <div className="space-y-4 rounded-xl bg-gray-50 p-4">
              <DomainEditor
                label={t('apps.config.deepSearchWebSearch.includeDomains')}
                domains={draft.includeDomains}
                onChange={includeDomains => setDraft(current => ({ ...current, includeDomains }))}
              />
              <DomainEditor
                label={t('apps.config.deepSearchWebSearch.excludeDomains')}
                domains={draft.excludeDomains}
                onChange={excludeDomains => setDraft(current => ({ ...current, excludeDomains }))}
              />
            </div>
          )}

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700">
              {t('apps.config.deepSearchWebSearch.extension')}
            </span>
            <textarea
              aria-label={t('apps.config.deepSearchWebSearch.extension')}
              value={draft.extensionJson}
              onChange={event => {
                setDraft(current => ({ ...current, extensionJson: event.target.value }));
                setError('');
              }}
              className="min-h-24 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
              placeholder='{"max_results": 5}'
            />
          </label>

          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t border-gray-200 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            {t('apps.config.deepSearchWebSearch.cancel')}
          </button>
          <button
            type="button"
            onClick={confirm}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t('apps.config.deepSearchWebSearch.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WebSearchEngineConfigDialog;
