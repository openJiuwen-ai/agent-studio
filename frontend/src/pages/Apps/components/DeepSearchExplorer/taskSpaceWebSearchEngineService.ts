import { getApiClient } from '@test-agentstudio/api-client'

export interface TaskSpaceWebSearchProviderTestResponse {
  code: number
  msg: string
  search_engine_name: string
  datas: Record<string, any>[]
}

interface TaskSpaceWebSearchProviderTestRequest {
  space_id: string
  provider: 'jina' | 'serper'
  api_key: string
}

const TASK_SPACE_WEB_SEARCH_PROVIDER_TEST_ENDPOINT = '/agent/deepsearch/task_space/web_search/provider_test'

const toProviderTestErrorResponse = (
  status: number,
  data: unknown
): TaskSpaceWebSearchProviderTestResponse => {
  const errorData = data as { detail?: string; msg?: string; message?: string } | undefined
  return {
    code: status,
    msg: errorData?.detail || errorData?.msg || errorData?.message || '',
    search_engine_name: '',
    datas: [],
  }
}

export const taskSpaceWebSearchEngineService = {
  async testProviderConnection(
    spaceId: string,
    provider: 'jina' | 'serper',
    apiKey: string
  ): Promise<TaskSpaceWebSearchProviderTestResponse> {
    const client = getApiClient()
    const request: TaskSpaceWebSearchProviderTestRequest = {
      space_id: spaceId,
      provider,
      api_key: apiKey,
    }
    const response = await client.post<TaskSpaceWebSearchProviderTestResponse>(
      TASK_SPACE_WEB_SEARCH_PROVIDER_TEST_ENDPOINT,
      request,
      { validateStatus: status => status < 600 }
    )

    if (response.status < 200 || response.status >= 300) {
      return toProviderTestErrorResponse(response.status, response.data)
    }

    return response.data
  },
}
