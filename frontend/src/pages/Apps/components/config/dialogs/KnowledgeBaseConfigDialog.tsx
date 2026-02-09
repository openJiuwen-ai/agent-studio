/**
 * Knowledge Base Configuration Dialog Component
 * 知识库配置对话框组件
 * 用于选择本地搜索的知识库，参考 WebSearchEngineConfigDialog 的设计风格
 */

import React, { useState, useEffect, useCallback } from 'react'
import { X, Check, AlertCircle, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { RADIUS_CONTAINER, RADIUS_BUTTON } from '../../../constants/styles'
import { KnowledgeBaseService, embeddingModelService } from '@test-agentstudio/api-client'

// 知识库类型
interface KnowledgeBaseItem {
  id: string
  name: string
  desc?: string
  embedding_model_config_id?: number
}

export interface KnowledgeBaseConfigDialogProps {
  open: boolean
  onClose: () => void
  spaceId: string
  initialSelected?: string[]
  onConfirm: (selectedIds: string[]) => void
}

/**
 * 知识库配置对话框组件
 */
export const KnowledgeBaseConfigDialog: React.FC<KnowledgeBaseConfigDialogProps> = ({
  open,
  onClose,
  spaceId,
  initialSelected = [],
  onConfirm,
}) => {
  const { t } = useTranslation()

  // 状态管理
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelected)
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseItem[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [embeddingModelError, setEmbeddingModelError] = useState<string | null>(null)

  const pageSize = 10

  // 加载知识库列表
  const loadKnowledgeBases = useCallback(async (pageNum: number, append = false) => {
    try {
      if (append) {
        setLoadingMore(true)
      } else {
        setLoading(true)
      }
      setError(null)

      const response = await KnowledgeBaseService.getKnowledgeBases({
        space_id: spaceId,
        page: pageNum,
        size: pageSize,
      })

      if (response.code === 200 && response.data) {
        const newItems = response.data.items
        setKnowledgeBases(prev => append ? [...prev, ...newItems] : newItems)
        setHasMore(newItems.length === pageSize)
      } else {
        setError(t('apps.config.knowledge.error.loadFailed'))
      }
    } catch (err) {
      console.error('Failed to load knowledge bases:', err)
      setError(t('apps.config.knowledge.error.loadError'))
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [spaceId])

  // 验证 Embedding 模型一致性
  const validateEmbeddingModels = useCallback(async (ids: string[]) => {
    if (ids.length <= 1) {
      setEmbeddingModelError(null)
      return
    }

    try {
      // 获取所有已选知识库的详细信息（不仅仅是当前页的知识库）
      const response = await KnowledgeBaseService.getKnowledgeBases({
        space_id: spaceId,
        page: 1,
        size: 100,
      })

      if (!response || response.code !== 200 || !response.data?.items) {
        setEmbeddingModelError(t('apps.config.knowledge.error.noInfo'))
        return
      }

      const allKnowledgeBases = response.data.items
      const selectedKBs = allKnowledgeBases.filter((kb: any) => ids.includes(kb.id))

      if (selectedKBs.length === 0) return

      const modelKeys: string[] = []
      const kbModelMap: Record<string, { name: string; modelId: string }> = {}

      for (const kb of selectedKBs) {
        const embeddingId = kb.embedding_model_config_id

        // 检查是否配置了 embedding_model_config_id
        if (embeddingId === null || embeddingId === undefined) {
          setEmbeddingModelError(t('apps.config.knowledge.error.noConfig', { name: kb.name }))
          return
        }

        try {
          const model = await embeddingModelService.getEmbeddingModelConfig(
            embeddingId.toString(),
            spaceId
          )
          const modelKey = `${model.modelId}-${model.protocol}`
          modelKeys.push(modelKey)
          kbModelMap[kb.id] = { name: model.name, modelId: model.modelId }
        } catch (err) {
          console.error(`Failed to fetch embedding model for KB ${kb.id}:`, err)
          setEmbeddingModelError(t('apps.config.knowledge.error.validateFailed', { name: kb.name }))
          return
        }
      }

      const uniqueModelKeys = Array.from(new Set(modelKeys))
      if (uniqueModelKeys.length > 1) {
        const modelInfo = Object.values(kbModelMap)
          .map(m => `${m.name} (${m.modelId})`)
          .join('、')
        setEmbeddingModelError(t('apps.config.knowledge.error.inconsistent', { models: modelInfo }))
      } else {
        setEmbeddingModelError(null)
      }
    } catch (err) {
      console.error('Error validating embedding models:', err)
      setEmbeddingModelError(t('apps.config.knowledge.error.validateError'))
    }
  }, [spaceId, t])

  // 初始化加载
  useEffect(() => {
    if (open && spaceId) {
      setPage(1)
      setKnowledgeBases([])
      loadKnowledgeBases(1, false)
    }
  }, [open, spaceId, loadKnowledgeBases])

  // 重置选中状态
  useEffect(() => {
    if (open) {
      setSelectedIds(initialSelected)
      setEmbeddingModelError(null)
    }
  }, [open, initialSelected])

  // 验证 Embedding 模型
  useEffect(() => {
    if (open && selectedIds.length > 1) {
      validateEmbeddingModels(selectedIds)
    } else {
      setEmbeddingModelError(null)
    }
  }, [selectedIds, open, validateEmbeddingModels])

  // 处理选择/取消选择
  const handleToggle = (kbId: string) => {
    setSelectedIds(prev => {
      if (prev.includes(kbId)) {
        return prev.filter(id => id !== kbId)
      } else {
        return [...prev, kbId]
      }
    })
  }

  // 加载更多
  const handleLoadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    loadKnowledgeBases(nextPage, true)
  }

  // 确认提交
  const handleConfirm = () => {
    if (embeddingModelError || selectedIds.length === 0) {
      return
    }
    onConfirm(selectedIds)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className={`bg-white ${RADIUS_CONTAINER} shadow-2xl w-full max-w-md mx-4 overflow-hidden`}>
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{t('apps.config.knowledge.title')}</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">{error}</p>
            </div>
          )}

          {/* Embedding 模型不一致错误 */}
          {embeddingModelError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">{embeddingModelError}</p>
            </div>
          )}

          {/* 加载状态 */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
            </div>
          ) : knowledgeBases.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
                <span className="text-2xl">📚</span>
              </div>
              <p className="text-sm text-gray-500 mb-3">{t('apps.config.knowledge.noAvailable')}</p>
              <p className="text-xs text-gray-400 mb-4">{t('apps.config.knowledge.needCreate')}</p>
              <button
                onClick={() => {
                  // 打开知识库管理页面（在新标签页中）
                  window.open('/knowledge-bases', '_blank')
                }}
                className="inline-flex items-center gap-1 px-4 py-2 text-sm text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
              >
                {t('apps.config.knowledge.gotoCreate')} →
              </button>
            </div>
          ) : (
            <>
              {/* 知识库列表 */}
              {knowledgeBases.map(kb => (
                <div
                  key={kb.id}
                  onClick={() => handleToggle(kb.id)}
                  className={`p-3 ${RADIUS_BUTTON} border-2 transition-all duration-200 cursor-pointer
                    ${selectedIds.includes(kb.id)
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">
                        📚
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{kb.name}</p>
                        {kb.desc && (
                          <p className="text-xs text-gray-500 truncate">{kb.desc}</p>
                        )}
                      </div>
                    </div>
                    {selectedIds.includes(kb.id) && (
                      <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />
                    )}
                  </div>
                </div>
              ))}

              {/* 加载更多按钮 */}
              {hasMore && (
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="w-full py-2 text-sm text-blue-600 hover:text-blue-700 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loadingMore ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('apps.config.knowledge.loading')}
                    </>
                  ) : (
                    t('apps.config.knowledge.loadMore')
                  )}
                </button>
              )}
            </>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
          >
            {t('apps.config.knowledge.cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={!!embeddingModelError || selectedIds.length === 0}
            className={`px-4 py-2 text-sm font-medium ${RADIUS_BUTTON} transition-all duration-200
              ${embeddingModelError || selectedIds.length === 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
              }`}
          >
            {t('apps.config.knowledge.confirm', { count: selectedIds.length })}
          </button>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeBaseConfigDialog
