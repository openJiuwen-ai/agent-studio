/**
 * useWebSearchEngineApi Hook
 * 搜索引擎 API 管理 Hook
 * 封装搜索引擎相关的 API 调用和状态管理
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { webSearchEngineService, WebSearchEngineConfig } from '@test-agentstudio/api-client'

export interface UseWebSearchEngineApiOptions {
  /** 用户空间ID */
  spaceId: string
  /** 是否在挂载时自动加载 */
  autoLoad?: boolean
}

export interface UseWebSearchEngineApiReturn {
  /** 搜索引擎列表 */
  engines: WebSearchEngineConfig[]
  /** 是否正在加载 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 获取搜索引擎列表 */
  fetchEngines: () => Promise<void>
  /** 创建搜索引擎 */
  createEngine: (
    engineName: string,
    apiKey: string,
    url: string
  ) => Promise<number>
  /** 删除搜索引擎 */
  deleteEngine: (engineId: number) => Promise<void>
  /** 清除错误 */
  clearError: () => void
}

/**
 * 搜索引擎 API 管理 Hook
 */
export const useWebSearchEngineApi = (
  options: UseWebSearchEngineApiOptions
): UseWebSearchEngineApiReturn => {
  const { t } = useTranslation()
  const { spaceId, autoLoad = true } = options

  const [engines, setEngines] = useState<WebSearchEngineConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取搜索引擎列表
  const fetchEngines = useCallback(async () => {
    if (!spaceId) return

    setLoading(true)
    setError(null)

    try {
      const data = await webSearchEngineService.listEngines(spaceId)
      setEngines(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.fetchEnginesFailed')
      setError(errorMessage)
      console.error('Failed to fetch search engines:', err)
    } finally {
      setLoading(false)
    }
  }, [spaceId, t])

  // 创建搜索引擎
  const createEngine = useCallback(async (
    engineName: string,
    apiKey: string,
    url: string
  ): Promise<number> => {
    if (!spaceId) {
      throw new Error('Space ID not found')
    }

    setLoading(true)
    setError(null)

    try {
      const engineId = await webSearchEngineService.createEngine(
        spaceId,
        engineName,
        apiKey,
        url
      )

      // 重新获取列表
      await fetchEngines()

      return engineId
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.createEngineFailed')
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [spaceId, fetchEngines, t])

  // 删除搜索引擎
  const deleteEngine = useCallback(async (engineId: number) => {
    if (!spaceId) return

    setLoading(true)
    setError(null)

    try {
      await webSearchEngineService.deleteEngine(spaceId, engineId)

      // 更新本地列表
      setEngines(prev => prev.filter(e => e.web_search_engine_id !== engineId))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.deleteEngineFailed')
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [spaceId, t])

  // 清除错误
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // 初始化加载
  useEffect(() => {
    if (autoLoad && spaceId) {
      fetchEngines()
    }
  }, [autoLoad, spaceId, fetchEngines])

  return {
    engines,
    loading,
    error,
    fetchEngines,
    createEngine,
    deleteEngine,
    clearError
  }
}

export default useWebSearchEngineApi
