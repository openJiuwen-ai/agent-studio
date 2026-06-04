import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { X, ArrowLeft, ArrowRight, Check, HelpCircle, Play, Loader2, CheckCircle, Info } from 'lucide-react'
import { Tooltip } from '@mui/material'
import { KnowledgeBase } from '@/types/knowledgeBase'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { KnowledgeBaseService, embeddingModelService } from '@test-agentstudio/api-client'
import { useModels, useTestModel, useTestEmbeddingModel } from '@test-agentstudio/api-client'

function getAxiosErrorMessage(e: unknown, fallback: string): string {
  if (e && typeof e === 'object' && 'response' in e) {
    const data = (e as { response?: { data?: { detail?: string; message?: string } } }).response?.data
    const msg = data?.detail ?? data?.message
    if (typeof msg === 'string' && msg.trim()) return msg
  }
  return (e as Error)?.message || fallback
}

interface SyncToDeepSearchDialogProps {
  open: boolean
  knowledgeBase: KnowledgeBase
  onClose: () => void
  /** 同步成功（第二步已提交创建索引） */
  onSuccess: (result: { dsKbId: string; taskId?: string }) => void
  /** 仅首次同步未完成即关闭且已删除 DS 镜像后，刷新 Studio 知识库状态 */
  onAbort?: () => void
}

interface FormData {
  parsingStrategy: string
  segmentationStrategy: string
  maxTokens: number
  chunkOverlapPercent: number
  enableGraphEnhancement: boolean
  llmModelId: number | string | null
}

const PAGE_SIZE = 100

const SyncToDeepSearchDialog: React.FC<SyncToDeepSearchDialogProps> = ({
  open,
  knowledgeBase,
  onClose,
  onSuccess,
  onAbort,
}) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { showSuccess, showError } = useUnifiedSnackbar()
  const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [deepSearchKbId, setDeepSearchKbId] = useState<string | null>(null)
  const [uploadedCount, setUploadedCount] = useState(0)
  /** 覆盖同步时后端返回的 DS 侧 doc_id 列表，第二步建索引需用此列表，否则 process 找不到文档 */
  const [uploadDocIdList, setUploadDocIdList] = useState<string[] | null>(null)
  const [deepSearchEmbeddingConfigs, setDeepSearchEmbeddingConfigs] = useState<Array<{ id: number; model_name: string }>>([])
  const [deepSearchEmbeddingConfigsLoading, setDeepSearchEmbeddingConfigsLoading] = useState(false)
  const [selectedDeepSearchEmbeddingConfigId, setSelectedDeepSearchEmbeddingConfigId] = useState<number | null>(null)
  /** 第二步已成功提交创建索引，关闭对话框时不再调用撤销接口 */
  const [syncFullyFinished, setSyncFullyFinished] = useState(false)
  const [formData, setFormData] = useState<FormData>({
    parsingStrategy: '1',
    segmentationStrategy: '1',
    maxTokens: 512,
    chunkOverlapPercent: 10,
    enableGraphEnhancement: false,
    llmModelId: null,
  })

  const { data: modelsData, isLoading: modelsLoading } = useModels({
    spaceId,
    is_active: true,
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })
  const modelsList =
    (modelsData?.items ?? [])
      .filter(m => m != null && m.id != null && String(m.id).trim() !== '')
      .map(m => ({ id: parseInt(String(m.id), 10), name: String(m.name || '') }))
      .filter(m => !Number.isNaN(m.id))
  const testModelMutation = useTestModel()
  const testEmbeddingModelMutation = useTestEmbeddingModel()
  const [isTestingModel, setIsTestingModel] = useState(false)
  const [modelTestPassed, setModelTestPassed] = useState(false)
  const [testedModelId, setTestedModelId] = useState<number | null>(null)

  /** 打开对话框瞬间是否已有 ds_kb_id（再次同步取消时不得删已有 DeepSearch 知识库） */
  const hadExistingDsKbAtOpenRef = useRef(false)
  /** 打开时已有的 DeepSearch 知识库 id，用于二次同步推迟上传 */
  const existingDsKbIdAtOpenRef = useRef<string | null>(null)
  const prevOpenRef = useRef(false)
  /** 二次同步：第一步不调用 sync_upload，待第二步提交时再上传，避免取消时已清空 DeepSearch */
  const [deferUploadToStep2, setDeferUploadToStep2] = useState(false)

  useEffect(() => {
    if (formData.llmModelId !== testedModelId) setModelTestPassed(false)
  }, [formData.llmModelId, testedModelId])

  useEffect(() => {
    if (open && !prevOpenRef.current) {
      const raw = knowledgeBase.ds_kb_id?.trim()
      existingDsKbIdAtOpenRef.current = raw && raw !== '' ? raw : null
      hadExistingDsKbAtOpenRef.current = Boolean(raw && raw !== '')
    }
    prevOpenRef.current = open

    if (!open) {
      setCurrentStep(1)
      setDeepSearchKbId(null)
      setUploadedCount(0)
      setUploadDocIdList(null)
      setDeepSearchEmbeddingConfigs([])
      setSelectedDeepSearchEmbeddingConfigId(null)
      setFormData({
        parsingStrategy: '1',
        segmentationStrategy: '1',
        maxTokens: 512,
        chunkOverlapPercent: 10,
        enableGraphEnhancement: false,
        llmModelId: null,
      })
      setModelTestPassed(false)
      setTestedModelId(null)
      setSyncFullyFinished(false)
      setDeferUploadToStep2(false)
    } else {
      setSyncFullyFinished(false)
    }
  }, [open, knowledgeBase.ds_kb_id])

  // 使用 Studio 的嵌入模型列表（与 DeepSearch 共用库后，同步时直接使用 Studio 的 embedding 表）
  useEffect(() => {
    if (!open || !spaceId) return
    setDeepSearchEmbeddingConfigsLoading(true)
    embeddingModelService
      .getEmbeddingModelConfigs(spaceId, { is_active: true, size: 100 })
      .then(({ items }) => {
        const list = items.map(m => ({ id: Number(m.id), model_name: m.name }))
        setDeepSearchEmbeddingConfigs(list)
        if (list.length === 1) setSelectedDeepSearchEmbeddingConfigId(list[0].id)
        else setSelectedDeepSearchEmbeddingConfigId(null)
      })
      .catch(() => setDeepSearchEmbeddingConfigs([]))
      .finally(() => setDeepSearchEmbeddingConfigsLoading(false))
  }, [open, spaceId])

  const handleTestModel = async () => {
    if (!formData.llmModelId) {
      showError(t('knowledgeBases.addDocument.modelRequired') || '请先选择LLM模型')
      return
    }
    setIsTestingModel(true)
    try {
      await testModelMutation.mutateAsync({
        id: String(formData.llmModelId),
        prompt: '你好，请用一句话介绍自己',
        spaceId,
      })
      setModelTestPassed(true)
      setTestedModelId(Number(formData.llmModelId))
      showSuccess('模型测试成功！')
    } catch (error: unknown) {
      setModelTestPassed(false)
      const msg = error && typeof error === 'object' && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : (error as Error)?.message || '模型测试失败'
      showError(`模型测试失败: ${msg}`)
    } finally {
      setIsTestingModel(false)
    }
  }

  const fetchAllDocumentIds = async (): Promise<string[]> => {
    const ids: string[] = []
    let page = 1
    while (true) {
      const res = await KnowledgeBaseService.getDocumentsList({
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        page,
        size: PAGE_SIZE,
      })
      const list = res.data?.items ?? []
      list.forEach((d: { id?: string }) => {
        if (d.id) ids.push(d.id)
      })
      const total = res.data?.total ?? 0
      if (ids.length >= total || list.length < PAGE_SIZE) break
      page += 1
    }
    return ids
  }

  /** 关闭对话框：仅「首次同步」且已完成第一步、未完成第二步时，删除本次新建的 DeepSearch 镜像；再次同步取消不删已有知识库 */
  const handleCloseAttempt = async () => {
    if (isLoading) return
    const dsKbIdForMirror = deepSearchKbId
    const shouldRollbackIncompleteFirstSync =
      Boolean(dsKbIdForMirror && !syncFullyFinished) && !hadExistingDsKbAtOpenRef.current
    if (shouldRollbackIncompleteFirstSync && dsKbIdForMirror) {
      setIsLoading(true)
      try {
        const delRes = await KnowledgeBaseService.deleteKnowledgeBase({
          space_id: spaceId,
          kb_id: dsKbIdForMirror,
        })
        if (delRes.code !== 200) {
          showError(delRes.message || (t('knowledgeBases.syncToDeepSearch.abortFailed') || '撤销同步失败'))
          return
        }
        onAbort?.()
      } catch (e) {
        showError(
          getAxiosErrorMessage(e, t('knowledgeBases.syncToDeepSearch.abortFailed') || '撤销同步失败，请稍后重试'),
        )
        return
      } finally {
        setIsLoading(false)
      }
    }
    onClose()
  }

  const validateSelectedEmbedding = async (): Promise<boolean> => {
    if (selectedDeepSearchEmbeddingConfigId == null) {
      showError(t('knowledgeBases.syncToDeepSearch.selectEmbedder') || '请选择 Deep Search 嵌入模型')
      return false
    }
    try {
      await testEmbeddingModelMutation.mutateAsync({
        id: String(selectedDeepSearchEmbeddingConfigId),
        testRequest: {
          text: t('knowledgeBases.form.testText') || 'DeepSearch sync probe',
        },
      })
      return true
    } catch (error: unknown) {
      const err = error as {
        detail?: string
        message?: string
        response?: { data?: { detail?: string; message?: string } }
      }
      const msg =
        err?.detail ||
        err?.message ||
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        t('knowledgeBases.form.testFailed') ||
        '嵌入模型测试失败'
      showError(
        t('knowledgeBases.syncToDeepSearch.embeddingTestFailed', { detail: msg }) ||
          `嵌入模型不可用，无法同步：${msg}`,
      )
      return false
    }
  }

  const handleStep1Next = async () => {
    setIsLoading(true)
    try {
      if (selectedDeepSearchEmbeddingConfigId == null) {
        showError(t('knowledgeBases.syncToDeepSearch.selectEmbedder') || '请选择 Deep Search 嵌入模型')
        return
      }
      if (!(await validateSelectedEmbedding())) {
        return
      }
      // 二次同步：不在此步调用 sync_upload（避免清空 DeepSearch），上传推迟到第二步「完成」时
      if (hadExistingDsKbAtOpenRef.current && existingDsKbIdAtOpenRef.current) {
        setDeferUploadToStep2(true)
        setDeepSearchKbId(existingDsKbIdAtOpenRef.current)
        setUploadedCount(0)
        setUploadDocIdList(null)
        showSuccess(
          t('knowledgeBases.syncToDeepSearch.resyncStep1Ready') ||
            '已选择嵌入模型；提交第二步时将把文件同步到 Deep Search（取消不会改动已有内容）',
        )
        setCurrentStep(2)
        return
      }

      setDeferUploadToStep2(false)
      const res = await KnowledgeBaseService.syncUpload({
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        deepsearch_embedding_model_config_id: selectedDeepSearchEmbeddingConfigId,
      })
      if (res.code === 200 && res.data?.ds_kb_id) {
        setDeepSearchKbId(res.data.ds_kb_id)
        setUploadedCount(res.data.uploaded_count ?? 0)
        setUploadDocIdList(Array.isArray(res.data.doc_id_list) ? res.data.doc_id_list : null)
        showSuccess(t('knowledgeBases.syncToDeepSearch.uploadSuccess') || '文件同步完成')
        setCurrentStep(2)
      } else {
        showError(res.message || (t('knowledgeBases.syncToDeepSearch.uploadFailed') || '同步上传失败'))
      }
    } catch (e) {
      showError(getAxiosErrorMessage(e, t('knowledgeBases.syncToDeepSearch.uploadFailed') || '同步上传失败'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleStep2Complete = async () => {
    if (!deepSearchKbId) {
      showError(t('knowledgeBases.syncToDeepSearch.uploadRequired') || '请先完成文件同步')
      return
    }
    if (formData.enableGraphEnhancement && (!formData.llmModelId || !modelTestPassed)) {
      showError(t('knowledgeBases.addDocument.modelRequired') || '启用图增强需要选择并测试通过LLM模型')
      return
    }
    setIsLoading(true)
    try {
      let dsId = deepSearchKbId
      let docIdsFromUpload = uploadDocIdList

      if (!(await validateSelectedEmbedding())) {
        return
      }

      if (deferUploadToStep2) {
        if (selectedDeepSearchEmbeddingConfigId == null) {
          showError(t('knowledgeBases.syncToDeepSearch.selectEmbedder') || '请选择 Deep Search 嵌入模型')
          return
        }
        const up = await KnowledgeBaseService.syncUpload({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          deepsearch_embedding_model_config_id: selectedDeepSearchEmbeddingConfigId,
        })
        if (up.code !== 200 || !up.data?.ds_kb_id) {
          showError(up.message || (t('knowledgeBases.syncToDeepSearch.uploadFailed') || '同步上传失败'))
          return
        }
        dsId = up.data.ds_kb_id
        docIdsFromUpload = Array.isArray(up.data.doc_id_list) ? up.data.doc_id_list : null
      }

      const docIdList =
        docIdsFromUpload && docIdsFromUpload.length > 0
          ? docIdsFromUpload
          : await fetchAllDocumentIds()
      const res = await KnowledgeBaseService.syncProcess({
        space_id: spaceId,
        ds_kb_id: dsId,
        studio_kb_id: knowledgeBase.id,
        deepsearch_embedding_model_config_id: selectedDeepSearchEmbeddingConfigId ?? undefined,
        doc_id_list: docIdList.length > 0 ? docIdList : [],
        parsing_strategy: { strategy_type: formData.parsingStrategy, strategy_config: {} },
        segmentation_strategy: {
          strategy_type: formData.segmentationStrategy,
          strategy_config: {
            max_tokens: formData.maxTokens,
            chunk_overlap_percent: formData.chunkOverlapPercent,
            ...(formData.segmentationStrategy === '2' ? { chunk_unit: 'token' as const } : {}),
          },
        },
        indexing_strategy: {
          enable_graph_enhancement: formData.enableGraphEnhancement,
          llm_model_id: formData.enableGraphEnhancement && formData.llmModelId ? Number(formData.llmModelId) : undefined,
        },
      })
      if (res.code !== 200) {
        showError(res.message || (t('knowledgeBases.syncToDeepSearch.processFailed') || '创建索引提交失败'))
        return
      }
      const processedCount = res.data?.processed_count ?? 0
      const failedCount = res.data?.failed_count ?? 0
      const taskId = res.data?.task_id
      if (!res.data?.skipped && processedCount === 0) {
        showError(
          t('knowledgeBases.syncToDeepSearch.processNoDocsStarted') ||
            '未能启动任何文档的索引。请确认文件已上传到 Deep Search，且嵌入模型可用。',
        )
        return
      }
      setSyncFullyFinished(true)
      if (failedCount > 0) {
        showError(
          t('knowledgeBases.syncToDeepSearch.processPartialFailed', { count: failedCount }) ||
            `${failedCount} 个文档未能进入索引流程，请在 Deep Search 镜像知识库中查看失败原因。`,
        )
      } else {
        showSuccess(
          res.data?.skipped
            ? t('knowledgeBases.syncToDeepSearch.processSuccessNoDocs') || '同步流程已完成（当前无可索引文档）'
            : t('knowledgeBases.syncToDeepSearch.processSuccess') ||
                '已提交创建索引任务，正在 Deep Search 侧建索引，请在镜像知识库中查看进度。',
        )
      }
      onSuccess({ dsKbId: dsId, taskId })
      onClose()
    } catch (e) {
      showError(getAxiosErrorMessage(e, t('knowledgeBases.syncToDeepSearch.processFailed') || '创建索引提交失败'))
    } finally {
      setIsLoading(false)
    }
  }

  if (!open) return null

  const totalSteps = 2
  const progressPct =
    totalSteps > 1 ? ((currentStep - 1) / (totalSteps - 1)) * 100 : currentStep > 1 ? 100 : 0
  const step2Valid = !formData.enableGraphEnhancement || (!!formData.llmModelId && modelTestPassed)

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={() => void handleCloseAttempt()} />
        <div className="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900">
              {t('knowledgeBases.syncToDeepSearch.title') || '同步至 Deep Search'}
            </h2>
            <button type="button" onClick={() => void handleCloseAttempt()} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="px-6 py-4 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full ${
                    currentStep >= 1 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > 1 ? <Check className="w-4 h-4" /> : '1'}
                </div>
                <div className={`ml-3 ${currentStep >= 1 ? 'text-blue-600' : 'text-gray-500'} font-medium`}>
                  {t('knowledgeBases.syncToDeepSearch.stepUpload') || '创建知识库并上传文档'}
                </div>
              </div>
              <div className="flex-1 h-1 mx-4 bg-gray-200">
                <div
                  className={`h-1 ${currentStep > 1 ? 'bg-blue-500' : 'bg-transparent'} transition-colors`}
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <div className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full ${
                    currentStep >= 2 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > 2 ? <Check className="w-4 h-4" /> : '2'}
                </div>
                <div className={`ml-3 ${currentStep >= 2 ? 'text-blue-600' : 'text-gray-500'} font-medium`}>
                  {t('knowledgeBases.syncToDeepSearch.stepProcess') || '创建索引'}
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 max-h-[60vh] overflow-y-auto">
            {currentStep === 1 && (
              <div>
                <p className="text-gray-600 mb-4">
                  {t('knowledgeBases.syncToDeepSearch.uploadDescription') ||
                    '将当前知识库的文件同步到 Deep Search，用于后续检索。'}
                </p>
                {knowledgeBase.ds_kb_id?.trim() ? (
                  <p className="text-sm text-gray-500 mb-4">
                    {t('knowledgeBases.syncToDeepSearch.resyncStep1Hint') ||
                      '再次同步时，仅在最后提交「创建索引」时才会更新 Deep Search 中的文件；在此之前关闭不会改动远端已有内容。'}
                  </p>
                ) : null}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('knowledgeBases.syncToDeepSearch.embedderLabel') || 'Deep Search 嵌入模型'}
                    <span className="text-red-500 ml-1">*</span>
                  </label>
                  {deepSearchEmbeddingConfigsLoading ? (
                    <div className="flex items-center text-gray-500">
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      {t('common.loading') || '加载中...'}
                    </div>
                  ) : deepSearchEmbeddingConfigs.length === 0 ? (
                    <p className="text-amber-600 text-sm">
                      {t('knowledgeBases.syncToDeepSearch.noEmbedder') || '暂无 Deep Search 嵌入模型，请先在 Deep Search 服务中配置嵌入模型后再同步。'}
                    </p>
                  ) : (
                    <select
                      value={selectedDeepSearchEmbeddingConfigId ?? ''}
                      onChange={e => setSelectedDeepSearchEmbeddingConfigId(e.target.value ? Number(e.target.value) : null)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">{t('knowledgeBases.syncToDeepSearch.selectEmbedderPlaceholder') || '请选择嵌入模型'}</option>
                      {deepSearchEmbeddingConfigs.map(ec => (
                        <option key={ec.id} value={ec.id}>
                          {ec.model_name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                {uploadedCount > 0 && (
                  <p className="mt-2 text-sm text-green-600">
                    {t('knowledgeBases.syncToDeepSearch.uploadedCount', { count: uploadedCount }) ||
                      `已同步 ${uploadedCount} 个文件`}
                  </p>
                )}
              </div>
            )}

            {currentStep === 2 && (
              <div>
                <p className="text-gray-600 mb-6">
                  {t('knowledgeBases.syncToDeepSearch.processDescription') ||
                    '设置解析、分段与索引策略，并提交创建索引任务。'}
                </p>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('knowledgeBases.addDocument.parsingStrategy')}
                    </label>
                    <select
                      value={formData.parsingStrategy}
                      onChange={e => setFormData(prev => ({ ...prev, parsingStrategy: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">{t('knowledgeBases.addDocument.quickParsing')}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('knowledgeBases.addDocument.segmentationStrategy')}
                    </label>
                    <select
                      value={formData.segmentationStrategy}
                      onChange={e => setFormData(prev => ({ ...prev, segmentationStrategy: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">{t('knowledgeBases.addDocument.autoSegmentation')}</option>
                      <option value="2">{t('knowledgeBases.addDocument.customSegmentation')}</option>
                    </select>
                    {formData.segmentationStrategy === '2' && (
                      <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">最大Token数 (16-1024)</label>
                          <input
                            type="number"
                            value={formData.maxTokens}
                            onChange={e => setFormData(prev => ({ ...prev, maxTokens: Math.min(1024, Math.max(16, parseInt(e.target.value) || 16)) }))}
                            min={16}
                            max={1024}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">分段重叠百分比 (0-50)</label>
                          <input
                            type="number"
                            value={formData.chunkOverlapPercent}
                            onChange={e =>
                              setFormData(prev => ({
                                ...prev,
                                chunkOverlapPercent: Math.min(50, Math.max(0, parseInt(e.target.value) || 0)),
                              }))
                            }
                            min={0}
                            max={50}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="syncGraphEnhancement"
                          checked={formData.enableGraphEnhancement}
                          onChange={e => setFormData(prev => ({ ...prev, enableGraphEnhancement: e.target.checked }))}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="syncGraphEnhancement" className="text-sm font-medium text-gray-700 cursor-pointer flex items-center space-x-2">
                          <span>{t('knowledgeBases.addDocument.enableGraphEnhancement')}</span>
                          <Tooltip
                            title={
                              t('knowledgeBases.addDocument.enableGraphEnhancementTooltip') ||
                              '图增强检索开启可以获取更好的检索效果，但是会增加耗时以及消耗额外的大模型token。'
                            }
                            arrow
                            placement="top"
                          >
                            <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                          </Tooltip>
                        </label>
                      </div>
                    </div>
                    {formData.enableGraphEnhancement && (
                      <>
                        <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800">
                          <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                          <span>
                            {t('knowledgeBases.addDocument.enableGraphEnhancementTooltip') ||
                              '构建文档图可以获取更好的检索效果，但是会增加耗时以及消耗额外的大模型token。'}
                          </span>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            {t('knowledgeBases.addDocument.selectLLMModel') || '选择LLM模型'}
                            <span className="text-red-500 ml-1">*</span>
                          </label>
                          <div className="flex items-center gap-2">
                            <select
                              value={formData.llmModelId ?? ''}
                              onChange={e =>
                                setFormData(prev => ({
                                  ...prev,
                                  llmModelId: e.target.value ? Number(e.target.value) : null,
                                }))
                              }
                              className={`flex-1 min-w-0 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                modelTestPassed && formData.llmModelId === testedModelId
                                  ? 'border-green-500 bg-green-50'
                                  : 'border-gray-300'
                              }`}
                              disabled={modelsLoading || isTestingModel}
                            >
                              <option value="">{t('knowledgeBases.addDocument.selectModelPlaceholder') || '请选择模型'}</option>
                              {modelsList.map(model => (
                                <option key={model.id} value={model.id}>
                                  {model.name}
                                </option>
                              ))}
                            </select>
                            <button
                              type="button"
                              onClick={handleTestModel}
                              disabled={!formData.llmModelId || isTestingModel}
                              className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg ${
                                modelTestPassed && formData.llmModelId === testedModelId
                                  ? 'text-green-600 bg-green-50'
                                  : !formData.llmModelId || isTestingModel
                                    ? 'text-gray-400 bg-gray-100 cursor-not-allowed'
                                    : 'text-blue-600 hover:bg-blue-50'
                              }`}
                            >
                              {isTestingModel ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                              ) : modelTestPassed && formData.llmModelId === testedModelId ? (
                                <CheckCircle className="w-5 h-5" />
                              ) : (
                                <Play className="w-5 h-5" />
                              )}
                            </button>
                          </div>
                          {formData.enableGraphEnhancement && !formData.llmModelId && (
                            <p className="mt-1 text-xs text-amber-600">
                              {t('knowledgeBases.addDocument.modelRequired') || '启用图增强需要选择LLM模型'}
                            </p>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between p-6 border-t bg-gray-50">
            <button type="button" onClick={() => void handleCloseAttempt()} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white">
              {t('common.cancel')}
            </button>
            <div className="flex items-center space-x-2">
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  disabled={isLoading}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white flex items-center disabled:opacity-50"
                >
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  {t('common.buttons.previous')}
                </button>
              )}
              {currentStep === 1 ? (
                <button
                  type="button"
                  onClick={handleStep1Next}
                  disabled={
                    isLoading ||
                    deepSearchEmbeddingConfigsLoading ||
                    deepSearchEmbeddingConfigs.length === 0 ||
                    selectedDeepSearchEmbeddingConfigId == null
                  }
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t('knowledgeBases.syncToDeepSearch.syncing') || '同步中...'}
                    </>
                  ) : (
                    <>
                      {t('common.buttons.next')}
                      <ArrowRight className="w-4 h-4 ml-1" />
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStep2Complete}
                  disabled={isLoading || !step2Valid}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  ) : null}
                  {t('knowledgeBases.syncToDeepSearch.complete') || '完成并提交创建索引'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SyncToDeepSearchDialog
