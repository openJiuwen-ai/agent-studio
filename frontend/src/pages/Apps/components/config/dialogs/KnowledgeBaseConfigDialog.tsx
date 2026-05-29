/**
 * Knowledge Base Configuration Dialog Component
 * 知识库配置对话框组件
 * 用于选择本地搜索的知识库，参考 WebSearchEngineConfigDialog 的设计风格
 */

import React, { useState, useEffect, useCallback } from 'react'
import { X, Check, AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { RADIUS_CONTAINER, RADIUS_BUTTON } from '../../../constants/styles'
import { KnowledgeBaseService } from '@test-agentstudio/api-client'

// 知识库类型
interface KnowledgeBaseItem {
  id: string
  name: string
  desc?: string
  status?: string
}

export interface KnowledgeBaseConfigDialogProps {
  open: boolean
  onClose: () => void
  spaceId: string
  initialSelected?: string[]
  onConfirm: (selectedIds: string[]) => void
  selectionMode?: 'single' | 'multiple'
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
  selectionMode = 'multiple',
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

  const pageSize = 10

  // 判断知识库是否可用（只有 indexed 状态可用）
  const isAvailable = useCallback((status?: string): boolean => {
    return status === 'indexed'
  }, [])

  // 获取状态显示信息
  const getStatusDisplay = useCallback(
    (status?: string): { text: string; color: string } => {
      if (status === 'indexed') {
        return { text: t('apps.config.knowledge.status.ready'), color: 'bg-green-100 text-green-700' }
      }
      if (status === 'failed') {
        return { text: t('apps.config.knowledge.status.failed'), color: 'bg-red-100 text-red-700' }
      }
      // 其他所有状态统一显示"处理中"
      return { text: t('apps.config.knowledge.status.processing'), color: 'bg-gray-100 text-gray-700' }
    },
    [t],
  )

  // 加载知识库列表
  const loadKnowledgeBases = useCallback(
    async (pageNum: number, append = false) => {
      try {
        if (append) {
          setLoadingMore(true)
        } else {
          setLoading(true)
        }
        setError(null)

        // 使用 DeepSearch 知识库 API
        const response = await KnowledgeBaseService.getDeepSearchKnowledgeBasesList({
          space_id: spaceId,
          page: pageNum,
          size: pageSize,
        })

        if (response.code === 200 && response.data) {
          const newItems = (response.data.items || []).map((item: any) => ({
            id: item.id,
            name: item.name,
            desc: item.desc,
            status: item.status,
          }))
          setKnowledgeBases(prev => (append ? [...prev, ...newItems] : newItems))
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
    },
    [spaceId, t],
  )

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
    }
  }, [open, initialSelected])

  // 加载完成后，过滤掉已不存在的知识库ID（解决知识库被删除后残留问题）
  useEffect(() => {
    if (open && !loading && knowledgeBases.length >= 0 && selectedIds.length > 0) {
      const validIds = selectedIds.filter(id => knowledgeBases.some(kb => kb.id === id))
      if (validIds.length !== selectedIds.length) {
        setSelectedIds(validIds)
      }
    }
  }, [open, loading, knowledgeBases])

  // 处理选择/取消选择
  const handleToggle = (kbId: string) => {
    setSelectedIds(prev => {
      if (selectionMode === 'single') {
        return prev.includes(kbId) ? [] : [kbId]
      }
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

  // 刷新列表
  const handleRefresh = () => {
    setPage(1)
    loadKnowledgeBases(1, false)
  }

  // 确认提交
  const handleConfirm = () => {
    if (selectedIds.length === 0) {
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
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('apps.config.knowledge.refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {selectionMode === 'single' && (
            <div className="p-2 bg-blue-50 border border-blue-100 rounded-lg">
              <p className="text-xs text-blue-700">{t('apps.config.knowledge.singleSelectTip')}</p>
            </div>
          )}

          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">{error}</p>
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
                  window.open('/dashboard/knowledge-bases', '_blank')
                }}
                className="inline-flex items-center gap-1 px-4 py-2 text-sm text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
              >
                {t('apps.config.knowledge.gotoCreate')} →
              </button>
            </div>
          ) : (
            <>
              {/* 知识库列表 */}
              {knowledgeBases.map(kb => {
                const disabled = !isAvailable(kb.status)
                const statusDisplay = getStatusDisplay(kb.status)
                return (
                  <div
                    key={kb.id}
                    onClick={() => !disabled && handleToggle(kb.id)}
                    className={`p-3 ${RADIUS_BUTTON} border-2 transition-all duration-200 cursor-pointer
                      ${
                        disabled
                          ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
                          : selectedIds.includes(kb.id)
                            ? 'border-blue-400 bg-blue-50'
                            : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">📚</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className={`text-sm font-medium truncate ${disabled ? 'text-gray-500' : 'text-gray-900'}`}>{kb.name}</p>
                            {kb.status && <span className={`px-1.5 py-0.5 text-xs rounded-full ${statusDisplay.color}`}>{statusDisplay.text}</span>}
                          </div>
                          {kb.desc && <p className={`text-xs truncate ${disabled ? 'text-gray-400' : 'text-gray-500'}`}>{kb.desc}</p>}
                        </div>
                      </div>
                      {selectedIds.includes(kb.id) && !disabled && <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />}
                    </div>
                  </div>
                )
              })}

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
            disabled={selectedIds.length === 0}
            className={`px-4 py-2 text-sm font-medium ${RADIUS_BUTTON} transition-all duration-200
              ${selectedIds.length === 0 ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'}`}
          >
            {t('apps.config.knowledge.confirm', { count: selectedIds.length })}
          </button>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeBaseConfigDialog
