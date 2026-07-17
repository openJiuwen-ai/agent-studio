import React, { useEffect, useMemo, useState } from 'react';
import { Eye, EyeOff, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import {
  WEB_FETCH_PROVIDER_PRESETS,
  type DeepSearchWebFetchProviderConfig,
  type WebFetchProviderName,
} from './webSearchFetchTypes';

interface WebFetchProviderConfigDialogProps {
  open: boolean;
  config?: DeepSearchWebFetchProviderConfig;
  onConfirm: (config: DeepSearchWebFetchProviderConfig) => void;
  onCancel: () => void;
}

const emptyConfig = {
  providerName: undefined as WebFetchProviderName | undefined,
  apiKey: '',
  baseUrl: '',
  extensionJson: '',
};

export const WebFetchProviderSummaryCard: React.FC<{
  config?: DeepSearchWebFetchProviderConfig;
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
    <div data-testid="web-fetch-summary-card" className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-gray-900">{t('apps.config.deepSearchWebFetch.summaryTitle')}</p>
          <p className="mt-1 text-sm text-gray-500">
            {config
              ? t('apps.config.deepSearchWebFetch.configuredProvider', { provider: config.providerName })
              : t('apps.config.deepSearchWebFetch.notConfigured')}
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
            {t('apps.config.deepSearchWebFetch.configure')}
          </button>
        </div>
      </div>
    </div>
  );
};

const WebFetchProviderConfigDialog: React.FC<WebFetchProviderConfigDialogProps> = ({
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
    const defaultPreset = WEB_FETCH_PROVIDER_PRESETS[0];
    setDraft({
      providerName: config?.providerName ?? defaultPreset?.name,
      apiKey: config?.apiKey ?? '',
      baseUrl: config?.baseUrl ?? defaultPreset?.defaultBaseUrl ?? '',
      extensionJson: config?.extensionJson ?? '',
    });
    setShowApiKey(false);
    setError('');
  }, [config, open]);

  const selectedPreset = useMemo(
    () => WEB_FETCH_PROVIDER_PRESETS.find(preset => preset.name === draft.providerName),
    [draft.providerName],
  );

  if (!open) return null;

  const confirm = () => {
    if (!draft.providerName || !draft.apiKey.trim()) {
      setError(t('apps.config.deepSearchWebFetch.required'));
      return;
    }

    if (draft.extensionJson.trim()) {
      try {
        const extension: unknown = JSON.parse(draft.extensionJson);
        if (extension === null || typeof extension !== 'object' || Array.isArray(extension)) {
          setError(t('apps.config.deepSearchWebFetch.invalidExtensionObject'));
          return;
        }
      } catch {
        setError(t('apps.config.deepSearchWebFetch.invalidExtension'));
        return;
      }
    }

    onConfirm({
      providerName: draft.providerName,
      apiKey: draft.apiKey.trim(),
      baseUrl: draft.baseUrl.trim(),
      ...(draft.extensionJson.trim() ? { extensionJson: draft.extensionJson.trim() } : {}),
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
          <h2 className="text-lg font-semibold text-gray-900">{t('apps.config.deepSearchWebFetch.title')}</h2>
          <button type="button" onClick={onCancel} aria-label={t('apps.config.deepSearchWebFetch.cancel')}>
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">{t('apps.config.deepSearchWebFetch.preset')}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {WEB_FETCH_PROVIDER_PRESETS.map(preset => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => {
                    setDraft(current => {
                      if (current.providerName === preset.name) return current;
                      return {
                        ...emptyConfig,
                        providerName: preset.name,
                        baseUrl: preset.defaultBaseUrl,
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
              {t('apps.config.deepSearchWebFetch.apiKey')}
            </span>
            <div className="relative">
              <input
                aria-label={t('apps.config.deepSearchWebFetch.apiKey')}
                type={showApiKey ? 'text' : 'password'}
                value={draft.apiKey}
                onChange={event => setDraft(current => ({ ...current, apiKey: event.target.value }))}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 text-sm"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(current => !current)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500"
                aria-label={
                  showApiKey
                    ? t('apps.config.deepSearchWebFetch.hideApiKey')
                    : t('apps.config.deepSearchWebFetch.showApiKey')
                }
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700">
              {t('apps.config.deepSearchWebFetch.baseUrl')}
            </span>
            <input
              aria-label={t('apps.config.deepSearchWebFetch.baseUrl')}
              type="url"
              value={draft.baseUrl}
              onChange={event => setDraft(current => ({ ...current, baseUrl: event.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700">
              {t('apps.config.deepSearchWebFetch.extension')}
            </span>
            <textarea
              aria-label={t('apps.config.deepSearchWebFetch.extension')}
              value={draft.extensionJson}
              onChange={event => {
                setDraft(current => ({ ...current, extensionJson: event.target.value }));
                setError('');
              }}
              className="min-h-24 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
              placeholder='{"timeout": 15}'
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
            {t('apps.config.deepSearchWebFetch.cancel')}
          </button>
          <button
            type="button"
            onClick={confirm}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t('apps.config.deepSearchWebFetch.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WebFetchProviderConfigDialog;
