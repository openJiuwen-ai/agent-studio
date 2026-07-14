import type { DeepSearchExplorerConfig } from '../../utils/deepsearchConstants';
import { DEFAULT_DEEPSEARCH_EXPLORER_CONFIG } from '../../utils/deepsearchConstants';
import {
  mapWebFetchProviderConfigToTelemetry,
  mapWebSearchEngineConfigToTelemetry,
} from './webSearchFetchTypes';
import {
  getDeepSearchKnowledgeBaseRuntimeConfig,
  getDeepSearchModelRuntimeConfig,
} from './runtimeConfigService';

export async function buildDeepSearchBackendConfig(
  dsConfig: DeepSearchExplorerConfig,
  spaceId: string,
  fallbackModelId: number,
): Promise<Record<string, unknown>> {
  const parseModelConfigId = (rawId?: string): string | null => {
    if (!rawId) return null;
    const parsed = Number.parseInt(rawId, 10);
    if (!Number.isFinite(parsed) || parsed < 0) return null;
    return String(parsed);
  };

  const searchMode = dsConfig.searchMode ?? DEFAULT_DEEPSEARCH_EXPLORER_CONFIG.searchMode;
  const selectedModelConfigId =
    parseModelConfigId(dsConfig.searchModelId)
    ?? parseModelConfigId(dsConfig.generalModelId)
    ?? parseModelConfigId(dsConfig.planningModelId)
    ?? (fallbackModelId >= 0 ? String(fallbackModelId) : null);

  if (!selectedModelConfigId) {
    throw new Error('A model is required for DeepSearch search-mode runs');
  }

  const runtime = await getDeepSearchModelRuntimeConfig(selectedModelConfigId, spaceId);
  if (!runtime.api_key) {
    throw new Error('Selected model does not have an API key configured');
  }

  const toolMap = searchMode === 'local' ? 'retrieve' : 'search_fetch';
  const payload: Record<string, unknown> = {
    space_id: spaceId,
    search_mode: 'search',
    enable_question_router: dsConfig.enableQuestionRouter ?? false,
    llm: {
      model_name: runtime.model_name,
      model_type: runtime.model_type,
      base_url: runtime.base_url,
      api_key: runtime.api_key,
    },
    tool_map: toolMap,
    search_workflow_per_question_params: {
      time_limit: dsConfig.timeLimit,
      actions_explored_limit: dsConfig.actionsExploredLimit,
    },
  };

  if (toolMap === 'search_fetch') {
    if (!dsConfig.webSearchEngineConfig || !dsConfig.webFetchProviderConfig) {
      throw new Error('Search mode requires both web search and web fetch configuration');
    }
    payload.web_search_engine_config = mapWebSearchEngineConfigToTelemetry(dsConfig.webSearchEngineConfig);
    payload.web_fetch_provider_config = mapWebFetchProviderConfigToTelemetry(dsConfig.webFetchProviderConfig);
    return payload;
  }

  const selectedKnowledgeBaseId = dsConfig.selectedKnowledgeBaseIds.find(kbId => kbId.trim().length > 0);
  if (!selectedKnowledgeBaseId) {
    throw new Error('Local mode requires selecting a knowledge base');
  }

  const runtimeConfig = await getDeepSearchKnowledgeBaseRuntimeConfig(selectedKnowledgeBaseId, spaceId);
  const embedderApiKey = runtimeConfig.embedder_api_key;
  const embedderBaseUrl = runtimeConfig.embedder_base_url;
  const embedderModelName = runtimeConfig.embedder_model_name;
  if (!embedderApiKey || !embedderBaseUrl || !embedderModelName) {
    throw new Error('Selected knowledge base is missing embedder runtime config');
  }

  if (
    !runtimeConfig.milvus_host
    || !runtimeConfig.milvus_port
    || !runtimeConfig.database_name
    || !runtimeConfig.collection_name
  ) {
    throw new Error('Selected knowledge base is missing Milvus runtime config');
  }

  payload.milvus = {
    milvus_host: runtimeConfig.milvus_host,
    milvus_port: runtimeConfig.milvus_port,
    database_name: runtimeConfig.database_name,
    collection_name: runtimeConfig.collection_name,
    embedder_model_name: embedderModelName,
    embedder_api_key: embedderApiKey,
    embedder_base_url: embedderBaseUrl,
    embedder_timeout: runtimeConfig.embedder_timeout ?? 100,
  };
  return payload;
}
