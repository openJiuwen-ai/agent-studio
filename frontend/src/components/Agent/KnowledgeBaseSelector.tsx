import React, { useState, useEffect, useMemo } from 'react'
import { Typography, Button, Pagination, Box } from '@mui/material'
import { X, Cpu, AlertCircle } from 'lucide-react'
import { KnowledgeBaseService, useEmbeddingModel, embeddingModelService } from '@test-agentstudio/api-client'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { KnowledgeBaseItem } from '@test-agentstudio/api-client'
import { useScopedTranslation } from '@/i18n'

interface KnowledgeBaseSelectorProps {
  open: boolean
  onClose: () => void
  onConfirm: (selectedKnowledgeBaseIds: string[]) => void
  initialSelected?: string[]
}

const KnowledgeBaseItemComponent: React.FC<{
  kb: KnowledgeBaseItem
  isSelected: boolean
  spaceId: string
  onToggle: () => void
}> = ({ kb, isSelected, spaceId, onToggle }) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  const { data: embeddingModel } = useEmbeddingModel(kb.embedding_model_config_id?.toString() || '', spaceId)

  return (
    <div
      className={`p-4 rounded-xl border-2 transition-all duration-300 cursor-pointer ${
        isSelected ? 'border-blue-400 bg-blue-50 shadow-lg' : 'border-gray-200 bg-white'
      }`}
      onClick={onToggle}
      aria-selected={isSelected}
      role="option"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0 ${
              isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
            }`}
          >
            📚
          </div>
          <div className="flex-1 min-w-0 overflow-hidden">
            <h4 
              className={`font-semibold text-base truncate ${isSelected ? 'text-blue-800' : 'text-gray-800'}`}
              title={kb.name}
            >
              {kb.name}
            </h4>
            {kb.desc && <p className="text-gray-600 text-sm truncate" title={kb.desc}>{kb.desc}</p>}
            {embeddingModel && (
              <div
                className="flex items-center space-x-1 mt-1"
                title={t('knowledgeBaseSelector.embeddingModelLabel', { name: embeddingModel.name, modelId: embeddingModel.modelId || '' })}
              >
                <Cpu className="w-3 h-3 text-gray-500" />
                <span className="text-xs text-gray-500 truncate max-w-[200px]">
                  {embeddingModel.name}
                  {embeddingModel.modelId && <span className="ml-1">({embeddingModel.modelId})</span>}
                </span>
              </div>
            )}
          </div>
        </div>

        {isSelected && (
          <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm text-blue-700 font-medium">{t('knowledgeBaseSelector.selected')}</span>
          </div>
        )}
      </div>
    </div>
  )
}

const KnowledgeBaseSelector: React.FC<KnowledgeBaseSelectorProps> = ({ open, onClose, onConfirm, initialSelected = [] }) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  const [selectedKnowledgeBases, setSelectedKnowledgeBases] = useState<string[]>(initialSelected)
  const [knowledgeBaseList, setKnowledgeBaseList] = useState<KnowledgeBaseItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [embeddingModelError, setEmbeddingModelError] = useState<string | null>(null)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 10
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  const spaceId = useMemo(() => getDefaultSpaceId() || '', [])

  // 验证选中知识库的 embedding 模型一致性
  useEffect(() => {
    if (selectedKnowledgeBases.length <= 1) {
      setEmbeddingModelError(null)
      return
    }

    const validateEmbeddingModels = async () => {
      try {
        const selectedKBs = knowledgeBaseList.filter(kb => selectedKnowledgeBases.includes(kb.id))
        if (selectedKBs.length === 0) return

        const modelIds: string[] = []
        const kbModelMap: Record<string, { name: string; modelId: string }> = {}

        for (const kb of selectedKBs) {
          if (!kb.embedding_model_config_id) {
            setEmbeddingModelError(t('knowledgeBaseSelector.errors.noEmbeddingModel'))
            return
          }

          try {
            const model = await embeddingModelService.getEmbeddingModelConfig(kb.embedding_model_config_id.toString(), spaceId)
            const modelKey = `${model.modelId}-${model.protocol}`
            modelIds.push(modelKey)
            kbModelMap[kb.id] = { name: model.name, modelId: model.modelId }
          } catch (err) {
            console.error(`Failed to fetch embedding model for KB ${kb.id}:`, err)
            setEmbeddingModelError(t('knowledgeBaseSelector.errors.validateFailed'))
            return
          }
        }

        // 检查所有模型是否一致
        const uniqueModelIds = Array.from(new Set(modelIds))
        if (uniqueModelIds.length > 1) {
          const modelInfo = Object.values(kbModelMap)
            .map(m => `${m.name} (${m.modelId})`)
            .join('、')
          setEmbeddingModelError(t('knowledgeBaseSelector.errors.modelMismatch', { modelInfo }))
        } else {
          setEmbeddingModelError(null)
        }
      } catch (err) {
        console.error('Error validating embedding models:', err)
        setEmbeddingModelError(t('knowledgeBaseSelector.errors.validateError'))
      }
    }

    validateEmbeddingModels()
  }, [selectedKnowledgeBases, knowledgeBaseList, spaceId, t])

  // 加载知识库列表
  useEffect(() => {
    if (!open || !spaceId) return

    const loadKnowledgeBases = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await KnowledgeBaseService.getKnowledgeBases({
          space_id: spaceId,
          page: currentPage,
          size: pageSize,
        })

        if (response.code === 200 && response.data) {
          setKnowledgeBaseList(response.data.items)
          setTotal(response.data.total)
          setTotalPages(Math.ceil(response.data.total / pageSize))
        } else {
          setError(t('knowledgeBaseSelector.errors.fetchFailed'))
        }
      } catch (err) {
        console.error('Failed to load knowledge bases:', err)
        setError(t('knowledgeBaseSelector.errors.loadFailed'))
      } finally {
        setIsLoading(false)
      }
    }

    loadKnowledgeBases()
  }, [open, spaceId, currentPage, t])

  // 当对话框打开时，重置选中状态
  useEffect(() => {
    if (open) {
      setSelectedKnowledgeBases(initialSelected || [])
      setCurrentPage(1)
    }
  }, [open, initialSelected])

  const handleToggle = (kbId: string) => {
    setSelectedKnowledgeBases(prev => {
      if (prev.includes(kbId)) {
        return prev.filter(id => id !== kbId)
      } else {
        return [...prev, kbId]
      }
    })
  }

  const handleConfirm = () => {
    if (embeddingModelError) {
      return // 如果有错误，不允许确认
    }
    onConfirm(selectedKnowledgeBases)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={onClose}></div>

        <div className="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-xl">
          <div className="flex items-center justify-between p-6 border-b">
            <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold' }}>
              {t('knowledgeBaseSelector.title')}
            </Typography>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6 max-h-[60vh] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span className="ml-2 text-gray-600">{t('knowledgeBaseSelector.loading')}</span>
              </div>
            ) : error ? (
              <div className="text-center py-12 text-red-500">{error}</div>
            ) : knowledgeBaseList.length === 0 ? (
              <div className="text-center py-12 text-gray-500">{t('knowledgeBaseSelector.empty')}</div>
            ) : (
              <>
                {embeddingModelError && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2">
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-red-800 font-medium">{t('knowledgeBaseSelector.embeddingModelMismatch')}</p>
                      <p className="text-sm text-red-600 mt-1">{embeddingModelError}</p>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {knowledgeBaseList.map(kb => (
                    <KnowledgeBaseItemComponent
                      key={kb.id}
                      kb={kb}
                      isSelected={selectedKnowledgeBases.includes(kb.id)}
                      spaceId={spaceId}
                      onToggle={() => handleToggle(kb.id)}
                    />
                  ))}
                </div>

                {totalPages > 1 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                    <Pagination
                      count={totalPages}
                      page={currentPage}
                      onChange={(_, page) => setCurrentPage(page)}
                      color="primary"
                    />
                  </Box>
                )}
              </>
            )}
          </div>

          <div className="flex items-center justify-end space-x-2 p-6 border-t">
            <Button variant="outlined" onClick={onClose}>
              {t('knowledgeBaseSelector.cancel')}
            </Button>
            <Button
              variant="contained"
              onClick={handleConfirm}
              disabled={!!embeddingModelError || selectedKnowledgeBases.length === 0}
            >
              {t('knowledgeBaseSelector.confirm', { count: selectedKnowledgeBases.length })}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeBaseSelector

