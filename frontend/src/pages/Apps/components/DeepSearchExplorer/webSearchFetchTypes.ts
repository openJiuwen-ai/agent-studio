export const WEB_SEARCH_ENGINE_NAMES = [
  'xunfei',
  'petal',
  'tavily',
  'google',
  'jina',
  'serper',
  'bocha',
  'perplexity',
  'custom',
] as const;

export type WebSearchEngineName = (typeof WEB_SEARCH_ENGINE_NAMES)[number];
export type WebFetchProviderName = 'jina';

export interface WebSearchEnginePreset {
  name: WebSearchEngineName;
  labelKey: `presets.${WebSearchEngineName}`;
  defaultSearchUrl: string;
}

export interface WebFetchProviderPreset {
  name: WebFetchProviderName;
  labelKey: `presets.${WebFetchProviderName}`;
  defaultBaseUrl: string;
}

export const WEB_SEARCH_ENGINE_PRESETS: readonly WebSearchEnginePreset[] = [
  { name: 'xunfei', labelKey: 'presets.xunfei', defaultSearchUrl: 'https://api.xunfei.cn' },
  { name: 'petal', labelKey: 'presets.petal', defaultSearchUrl: 'https://api.petal.dev' },
  { name: 'tavily', labelKey: 'presets.tavily', defaultSearchUrl: 'https://api.tavily.com' },
  { name: 'google', labelKey: 'presets.google', defaultSearchUrl: 'https://google.serper.dev' },
  { name: 'jina', labelKey: 'presets.jina', defaultSearchUrl: 'https://s.jina.ai' },
  { name: 'serper', labelKey: 'presets.serper', defaultSearchUrl: 'https://google.serper.dev' },
  { name: 'bocha', labelKey: 'presets.bocha', defaultSearchUrl: 'https://api.bocha.cn/v1/web-search' },
  {
    name: 'perplexity',
    labelKey: 'presets.perplexity',
    defaultSearchUrl: 'https://api.perplexity.ai/chat/completions',
  },
  { name: 'custom', labelKey: 'presets.custom', defaultSearchUrl: '' },
];

export const WEB_FETCH_PROVIDER_PRESETS: readonly WebFetchProviderPreset[] = [
  { name: 'jina', labelKey: 'presets.jina', defaultBaseUrl: 'https://r.jina.ai' },
];

/**
 * Browser-local search configuration. `extensionJson` is kept as user-entered
 * JSON; its object form is only created when a telemetry payload is built.
 */
export interface DeepSearchWebSearchEngineConfig {
  searchEngineName: WebSearchEngineName;
  searchApiKey: string;
  searchUrl: string;
  extensionJson?: string;
  includeDomains?: string[];
  excludeDomains?: string[];
  maxWebSearchResults?: number;
}

/** Browser-local fetch configuration. It is independent from search settings. */
export interface DeepSearchWebFetchProviderConfig {
  providerName: WebFetchProviderName;
  apiKey: string;
  baseUrl: string;
  extensionJson?: string;
}

export interface TelemetryWebSearchEngineConfig {
  search_engine_name: WebSearchEngineName;
  search_api_key: string;
  search_url: string;
  max_web_search_results: number;
  extension: Record<string, unknown>;
}

export interface TelemetryWebFetchProviderConfig {
  provider_name: WebFetchProviderName;
  api_key: string;
  base_url: string;
  extension: Record<string, unknown>;
}

type UnknownRecord = Record<string, unknown>;

const DEFAULT_MAX_WEB_SEARCH_RESULTS = 5;

function asRecord(value: unknown): UnknownRecord | null {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

function normalizeDomainList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return [
    ...new Set(
      value
        .filter((domain): domain is string => typeof domain === 'string')
        .map(domain => domain.trim())
        .filter(Boolean),
    ),
  ];
}

function normalizeExtensionJson(value: unknown): string | undefined | null {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  if (typeof value !== 'string') {
    return null;
  }
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return undefined;
  }
  try {
    return asRecord(JSON.parse(trimmedValue)) ? trimmedValue : null;
  } catch {
    return null;
  }
}

function parseExtensionJson(extensionJson: string | undefined): Record<string, unknown> {
  if (!extensionJson) {
    return {};
  }
  const extension = asRecord(JSON.parse(extensionJson));
  if (!extension) {
    throw new Error('extensionJson must be a JSON object');
  }
  return extension;
}

function isWebSearchEngineName(value: unknown): value is WebSearchEngineName {
  return typeof value === 'string' && WEB_SEARCH_ENGINE_NAMES.includes(value as WebSearchEngineName);
}

function isWebFetchProviderName(value: unknown): value is WebFetchProviderName {
  return typeof value === 'string' && WEB_FETCH_PROVIDER_PRESETS.some(preset => preset.name === value);
}

function normalizeMaxWebSearchResults(value: unknown): number | null {
  if (value === undefined || value === null) {
    return DEFAULT_MAX_WEB_SEARCH_RESULTS;
  }
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= 10 ? value : null;
}

export function normalizeDeepSearchWebSearchEngineConfig(value: unknown): DeepSearchWebSearchEngineConfig | null {
  const config = asRecord(value);
  if (!config || !isWebSearchEngineName(config.searchEngineName) || typeof config.searchApiKey !== 'string') {
    return null;
  }

  const extensionJson = normalizeExtensionJson(config.extensionJson);
  const maxWebSearchResults = normalizeMaxWebSearchResults(config.maxWebSearchResults);
  if (extensionJson === null || maxWebSearchResults === null) {
    return null;
  }

  return {
    searchEngineName: config.searchEngineName,
    searchApiKey: config.searchApiKey.trim(),
    searchUrl: typeof config.searchUrl === 'string' ? config.searchUrl.trim() : '',
    ...(extensionJson ? { extensionJson } : {}),
    includeDomains: normalizeDomainList(config.includeDomains),
    excludeDomains: normalizeDomainList(config.excludeDomains),
    maxWebSearchResults,
  };
}

export function normalizeDeepSearchWebFetchProviderConfig(value: unknown): DeepSearchWebFetchProviderConfig | null {
  const config = asRecord(value);
  if (!config || !isWebFetchProviderName(config.providerName) || typeof config.apiKey !== 'string') {
    return null;
  }

  const extensionJson = normalizeExtensionJson(config.extensionJson);
  if (extensionJson === null) {
    return null;
  }

  return {
    providerName: config.providerName,
    apiKey: config.apiKey.trim(),
    baseUrl: typeof config.baseUrl === 'string' ? config.baseUrl.trim() : '',
    ...(extensionJson ? { extensionJson } : {}),
  };
}

function mergeTavilyDomains(
  extension: Record<string, unknown>,
  config: DeepSearchWebSearchEngineConfig,
): Record<string, unknown> {
  if (config.searchEngineName !== 'tavily') {
    return extension;
  }

  const includeDomains = [
    ...new Set([...normalizeDomainList(extension.include_domains), ...normalizeDomainList(config.includeDomains)]),
  ];
  const excludeDomains = [
    ...new Set([...normalizeDomainList(extension.exclude_domains), ...normalizeDomainList(config.excludeDomains)]),
  ];

  return {
    ...extension,
    ...(includeDomains.length > 0 ? { include_domains: includeDomains } : {}),
    ...(excludeDomains.length > 0 ? { exclude_domains: excludeDomains } : {}),
  };
}

export function mapWebSearchEngineConfigToTelemetry(
  config: DeepSearchWebSearchEngineConfig,
): TelemetryWebSearchEngineConfig {
  const extension = mergeTavilyDomains(parseExtensionJson(config.extensionJson), config);
  const maxWebSearchResults = normalizeMaxWebSearchResults(config.maxWebSearchResults);
  if (maxWebSearchResults === null) {
    throw new Error('maxWebSearchResults must be an integer between 1 and 10');
  }

  return {
    search_engine_name: config.searchEngineName,
    search_api_key: config.searchApiKey.trim(),
    search_url: config.searchUrl.trim(),
    max_web_search_results: maxWebSearchResults,
    extension,
  };
}

export function mapWebFetchProviderConfigToTelemetry(
  config: DeepSearchWebFetchProviderConfig,
): TelemetryWebFetchProviderConfig {
  return {
    provider_name: config.providerName,
    api_key: config.apiKey.trim(),
    base_url: config.baseUrl.trim(),
    extension: parseExtensionJson(config.extensionJson),
  };
}

export function getWebSearchEngineConfigLabel(
  config: Pick<DeepSearchWebSearchEngineConfig, 'searchEngineName'>,
): string {
  return config.searchEngineName;
}

export function getWebFetchProviderConfigLabel(config: Pick<DeepSearchWebFetchProviderConfig, 'providerName'>): string {
  return config.providerName;
}
