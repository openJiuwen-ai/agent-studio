import { KnowledgeBaseService, modelService } from '@test-agentstudio/api-client'

export interface DeepSearchModelRuntimeConfig {
  model_id: number
  model_name: string
  model_type: string
  base_url: string
  api_key: string | null
}

export interface DeepSearchKnowledgeBaseRuntimeConfig {
  milvus_host?: string
  milvus_port?: number
  database_name?: string
  collection_name?: string
  embedder_model_name?: string
  embedder_api_key?: string | null
  embedder_base_url?: string
  embedder_timeout?: number
}

export const getDeepSearchModelRuntimeConfig = async (
  modelId: string,
  spaceId: string,
): Promise<DeepSearchModelRuntimeConfig> =>
  modelService.getDeepSearchModelRuntime(modelId, spaceId)

export const getDeepSearchKnowledgeBaseRuntimeConfig = async (
  kbId: string,
  spaceId: string,
): Promise<DeepSearchKnowledgeBaseRuntimeConfig> => {
  const response = await KnowledgeBaseService.getDeepSearchRuntimeConfig({
    space_id: spaceId,
    kb_id: kbId,
  })

  if (response.code !== 200 || !response.data?.retrieve_config) {
    throw new Error('Failed to resolve selected knowledge base runtime configuration')
  }

  return response.data.retrieve_config
}
