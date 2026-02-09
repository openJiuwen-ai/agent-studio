/**
 * useTemplateApi Hook
 * 模板 API 管理 Hook
 * 封装模板相关的 API 调用和状态管理
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ReportTemplate } from '../AgentConfigDialog'
import { deepsearchTemplateService } from '@test-agentstudio/api-client'

export interface UseTemplateApiOptions {
  /** 用户空间ID */
  spaceId: string
  /** 是否在挂载时自动加载模板列表 */
  autoLoad?: boolean
}

export interface UseTemplateApiReturn {
  /** 模板列表 */
  templates: ReportTemplate[]
  /** 是否正在加载 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 获取模板列表 */
  fetchTemplates: () => Promise<void>
  /** 上传模板 */
  uploadTemplate: (
    file: File,
    templateName: string,
    templateDesc: string,
    modelConfigId: number
  ) => Promise<number>
  /** 删除模板 */
  deleteTemplate: (templateId: number) => Promise<void>
  /** 清除错误 */
  clearError: () => void
}

/**
 * 模板 API 管理 Hook
 */
export const useTemplateApi = (
  options: UseTemplateApiOptions
): UseTemplateApiReturn => {
  const { t } = useTranslation()
  const { spaceId, autoLoad = true } = options

  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取模板列表
  const fetchTemplates = useCallback(async () => {
    if (!spaceId) return

    setLoading(true)
    setError(null)

    try {
      const data = await deepsearchTemplateService.listTemplates(spaceId)
      setTemplates(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.fetchTemplatesFailed')
      setError(errorMessage)
      console.error('Failed to fetch templates:', err)
    } finally {
      setLoading(false)
    }
  }, [spaceId, t])

  // 上传模板
  const uploadTemplate = useCallback(async (
    file: File,
    templateName: string,
    templateDesc: string,
    modelConfigId: number
  ): Promise<number> => {
    if (!spaceId) {
      throw new Error('Space ID not found')
    }

    setLoading(true)
    setError(null)

    try {
      const templateId = await deepsearchTemplateService.importTemplate(
        spaceId,
        file,
        templateName,
        templateDesc,
        modelConfigId
      )

      // 重新获取模板列表
      await fetchTemplates()

      return templateId
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.uploadTemplateFailed')
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [spaceId, fetchTemplates, t])

  // 删除模板
  const deleteTemplate = useCallback(async (templateId: number) => {
    if (!spaceId) return

    setLoading(true)
    setError(null)

    try {
      await deepsearchTemplateService.deleteTemplate(spaceId, templateId)

      // 更新本地列表
      setTemplates(prev => prev.filter(t => t.template_id !== templateId))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.errors.deleteTemplateFailed')
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
      fetchTemplates()
    }
  }, [autoLoad, spaceId, fetchTemplates])

  return {
    templates,
    loading,
    error,
    fetchTemplates,
    uploadTemplate,
    deleteTemplate,
    clearError
  }
}

export default useTemplateApi
