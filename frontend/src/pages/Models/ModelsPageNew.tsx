import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useAuthStore } from '../../stores/useAuthStore'
import { useTranslation } from 'react-i18next'
import { Plus, Settings, Play, Search, X, Loader2 } from 'lucide-react'
import {
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Typography,
  Grid,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar,
  Slider,
  Box,
} from '@mui/material'
import { useModels, useCreateModel, useUpdateModel, useDeleteModel, useToggleModelStatus, useTestModel } from '@test-agentstudio/api-client'
import {
  useEmbeddingModels,
  useCreateEmbeddingModel,
  useUpdateEmbeddingModel,
  useDeleteEmbeddingModel,
  useToggleEmbeddingModelStatus,
  useTestEmbeddingModel,
} from '@test-agentstudio/api-client'
import type { FrontendModelConfig, FrontendEmbeddingModelConfig } from '@test-agentstudio/api-client'
import { ModelProvider } from '@test-agentstudio/api-client'
import DeleteConfirmationDialog from '../../components/Common/DeleteConfirmationDialog'
import { CommonPageLayout, type TabConfig } from '@/components/Common/common-page'
import { LLMModelsTable } from './components/LLMModelsTable'
import { EmbeddingModelsTable } from './components/EmbeddingModelsTable'

// 使用FrontendModelConfig作为ModelConfig的类型别名
type ModelConfig = FrontendModelConfig

// 模型类型枚举
type ModelType = 'LLM' | 'Embedding'

// 统一的模型列表项类型（用于渲染列表）
interface UnifiedModelListItem {
  id: string
  name: string
  provider: string
  modelId: string
  isActive: boolean
  tags: string[]
  description: string
  createdAt: string
  updatedAt: string
  isSystemModel: boolean // 是否系统预置模型
  modelType: ModelType // 添加模型类型字段
  // LLM 特有属性
  usage?: {
    totalRequests: number
    totalTokens: number
    successRate: number
    averageResponseTime: number
    lastUsed: string
  }
  temperature?: number
  maxTokens?: number
  apiKey?: string
  baseUrl?: string
  topp?: number
  timeout?: number
  retryCount?: number
  enableStreaming?: boolean
  enableFunctionCalling?: boolean
  // Embedding 特有属性
  maxBatchSize?: number
}

const initialModelConfig: Partial<ModelConfig> = {
  name: '',
  provider: ModelProvider.OPENAI,
  modelId: '',
  apiKey: '',
  baseUrl: '',
  isActive: true,
  maxTokens: 4000,
  temperature: 0.7,
  topp: 0.9,
  timeout: 60,
  retryCount: 3,
  enableStreaming: true,
  enableFunctionCalling: true,
  tags: [],
  description: '',
}

// Embedding 模型的初始配置
const initialEmbeddingConfig: Partial<ModelConfig> & { maxBatchSize?: number } = {
  name: '',
  provider: ModelProvider.OPENAI,
  modelId: '',
  apiKey: '',
  baseUrl: '',
  isActive: true,
  tags: [],
  maxBatchSize: 5,
}

const ModelsPage: React.FC = () => {
  const { t } = useTranslation()
  // 使用 hooks 管理模型数据
  const { user } = useAuthStore()

  // 分页状态
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(10)

  // 获取 LLM 模型数据 - 为了支持全量搜索，获取最大量数据
  const {
    data: modelsResponse,
    isFetching: isLoadingLLM,
    error: errorLLM,
    refetch: refetchLLM,
  } = useModels({
    spaceId: user?.spaceId,
    page: 1,
    size: 100, // 获取最大量数据用于前端筛选
    sort_by: 'update_time',
    sort_order: 'desc',
  })

  // 获取 Embedding 模型数据
  const {
    data: embeddingModelsResponse,
    isFetching: isLoadingEmbedding,
    error: errorEmbedding,
    refetch: refetchEmbedding,
  } = useEmbeddingModels({
    spaceId: user?.spaceId,
    page: 1,
    size: 100,
    sort_by: 'updated_at',
    sort_order: 'desc',
  })

  // 合并加载状态和错误状态
  const isLoading = isLoadingLLM || isLoadingEmbedding
  const error = errorLLM || errorEmbedding
  const refetch = () => {
    refetchLLM()
    refetchEmbedding()
  }

  // 当API返回为空时显示空列表
  const displayLLMModels = (modelsResponse?.items || []).map((model: any) => ({
    ...model,
    modelType: 'LLM' as ModelType,
  }))
  const displayEmbeddingModels = (embeddingModelsResponse?.items || []).map((model: any) => ({
    ...model,
    modelType: 'Embedding' as ModelType,
  }))

  // Tab 状态：改为字符串以适配 CommonPageLayout
  const [activeTab, setActiveTab] = useState<string>('llm')

  const [showModelDialog, setShowModelDialog] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [showTestDialog, setShowTestDialog] = useState(false)
  const [selectedModel, setSelectedModel] = useState<UnifiedModelListItem | null>(null)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'warning' })
  const [searchTerm, setSearchTerm] = useState('')
  const [filterProvider, setFilterProvider] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  // 合并所有模型到一个列表
  const allModels: UnifiedModelListItem[] = [...displayLLMModels, ...displayEmbeddingModels] as UnifiedModelListItem[]
  // 根据当前 tab 计算总数和总页数
  const currentTabTotalItems = activeTab === 'llm' ? modelsResponse?.total || 0 : embeddingModelsResponse?.total || 0
  const totalItems = currentTabTotalItems
  const totalPages = pageSize > 0 ? Math.ceil(totalItems / pageSize) : 0

  // 筛选结果的分页状态
  const [filteredPage, setFilteredPage] = useState(1)
  const [deleteDialog, setDeleteDialog] = useState<{
    isOpen: boolean
    modelId: string
    modelName: string
    modelType: ModelType
    knowledgeBases?: string[] // 使用该模型的知识库列表
  }>({
    isOpen: false,
    modelId: '',
    modelName: '',
    modelType: 'LLM',
    knowledgeBases: undefined,
  })

  // New model form state
  const [newModel, setNewModel] = useState<Partial<ModelConfig> & { maxBatchSize?: number }>(initialModelConfig)

  // 模型类型状态
  const [modelType, setModelType] = useState<ModelType>('LLM')

  // Test state
  const [testPrompt, setTestPrompt] = useState('')
  const [testResult, setTestResult] = useState('')
  const [isTesting, setIsTesting] = useState(false)
  const [testingModelId, setTestingModelId] = useState<string | null>(null) // 用于 UI 显示
  const testingModelIdRef = useRef<string | null>(null) // 用于异步操作中持久化跟踪
  const testGenerationRef = useRef(0) // 测试代数，用于防止旧测试覆盖新测试状态

  // Tag input state
  const [newTag, setNewTag] = useState('')

  // URL validation state
  const [baseUrlError, setBaseUrlError] = useState('')

  // 表单验证状态
  const isFormValid = () => {
    // 基础验证
    const nameValid = newModel.name?.trim() && (newModel.name?.length || 0) <= 100
    const modelIdValid = newModel.modelId?.trim() && (newModel.modelId?.length || 0) <= 100
    const apiKeyValid = editMode ? true : newModel.apiKey?.trim() || false // 编辑时可选，创建时必填
    const baseUrlValid = newModel.baseUrl?.trim() && !baseUrlError
    const tagsValid = (newModel.tags?.length || 0) <= 10

    if (modelType === 'Embedding') {
      // Embedding 类型：不需要 description 验证
      const baseValid = nameValid && modelIdValid && apiKeyValid && baseUrlValid && tagsValid
      const maxBatchSize = newModel.maxBatchSize
      return baseValid && maxBatchSize !== undefined && maxBatchSize >= 1 && maxBatchSize <= 10
    } else {
      // LLM 类型：description 为可选字段，只验证长度
      const descriptionLengthValid = (newModel.description?.length || 0) <= 500
      const baseValid = nameValid && modelIdValid && apiKeyValid && baseUrlValid && descriptionLengthValid && tagsValid
      const timeout = newModel.timeout
      return baseValid && timeout !== undefined && timeout >= 1 && timeout <= 3600 // 超时时间范围验证
    }
  }

  const handleOpenModelDialog = (model: UnifiedModelListItem | null) => {
    if (model) {
      // Edit mode
      setEditMode(true)
      setSelectedModel(model)
      // 将列表项转换为表单数据
      if (model.modelType === 'Embedding') {
        setNewModel({
          name: model.name,
          provider: ModelProvider.OPENAI,
          modelId: model.modelId,
          apiKey: model.apiKey || '', // 显示脱敏的 API 密钥（如果存在）
          baseUrl: (model as any).baseUrl || '',
          isActive: model.isActive,
          tags: model.tags || [],
          maxBatchSize: (model as any).maxBatchSize || 8,
        })
      } else {
        setNewModel(model as any)
      }
      // 根据模型类型判断
      setModelType(model.modelType)
    } else {
      // Add mode - 根据当前 tab 设置默认模型类型
      setEditMode(false)
      setSelectedModel(null)
      const defaultType: ModelType = activeTab === 'llm' ? 'LLM' : 'Embedding'
      setNewModel(defaultType === 'LLM' ? initialModelConfig : initialEmbeddingConfig)
      setModelType(defaultType)
    }
    setShowModelDialog(true)
  }

  // URL validation function
  const validateBaseUrl = (url: string): boolean => {
    if (!url.trim()) {
      setBaseUrlError('')
      return true // Empty URL is allowed
    }

    const urlPattern = /^https?:\/\//i
    if (!urlPattern.test(url)) {
      setBaseUrlError(t('models.modelConfig.parameters.endpointError'))
      return false
    }

    setBaseUrlError('')
    return true
  }

  // 使用 hooks 进行 LLM 模型数据操作
  const createModelMutation = useCreateModel()
  const updateModelMutation = useUpdateModel()
  const deleteModelMutation = useDeleteModel()
  const toggleStatusMutation = useToggleModelStatus()
  const testModelMutation = useTestModel()

  // 使用 hooks 进行 Embedding 模型数据操作
  const createEmbeddingModelMutation = useCreateEmbeddingModel()
  const updateEmbeddingModelMutation = useUpdateEmbeddingModel()
  const deleteEmbeddingModelMutation = useDeleteEmbeddingModel()
  const toggleEmbeddingStatusMutation = useToggleEmbeddingModelStatus()
  const testEmbeddingModelMutation = useTestEmbeddingModel()

  // 根据当前 tab 确定显示的模型类型
  const currentModelType: ModelType = activeTab === 'llm' ? 'LLM' : 'Embedding'

  // 首先根据当前 tab 过滤模型类型
  const currentTabModels = allModels.filter(model => model.modelType === currentModelType)

  // 筛选状态检查
  const hasFilters: boolean = !!(searchTerm || filterProvider !== 'all' || filterStatus !== 'all')

  const filteredModels = currentTabModels
    .filter(model => {
      const searchLower = searchTerm.toLowerCase()
      const matchesSearch =
        model.name.toLowerCase().includes(searchLower) ||
        model.provider.toLowerCase().includes(searchLower) ||
        model.modelId.toLowerCase().includes(searchLower) ||
        (currentModelType === 'LLM' && model.tags && model.tags.some(tag => tag.toLowerCase().includes(searchLower)))
      const matchesProvider = filterProvider === 'all' || model.provider === filterProvider
      const matchesStatus = filterStatus === 'all' || (filterStatus === 'active' && model.isActive) || (filterStatus === 'inactive' && !model.isActive)

      return matchesSearch && matchesProvider && matchesStatus
    })
    .sort((a, b) => {
      // 按更新时间降序排序，最新创建/更新的排在最前面
      const dateA = new Date(a.updatedAt).getTime()
      const dateB = new Date(b.updatedAt).getTime()
      return dateB - dateA
    })

  // 筛选结果的分页计算
  const filteredTotalItems = filteredModels.length
  const filteredTotalPages = pageSize > 0 ? Math.ceil(filteredTotalItems / pageSize) : 0

  // 非筛选状态下的前端分页
  const paginatedDisplayModels = currentTabModels.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  // 筛选状态下的前端分页
  const paginatedFilteredModels = filteredModels.slice((filteredPage - 1) * pageSize, filteredPage * pageSize)

  // 监听筛选条件和 tab 变化，重置筛选分页
  useEffect(() => {
    setFilteredPage(1)
    setCurrentPage(1)
  }, [searchTerm, filterProvider, filterStatus, activeTab])

  // 监听测试对话框关闭，确保重置测试状态
  useEffect(() => {
    if (!showTestDialog) {
      // 对话框关闭时，增加代数使正在进行的测试失效
      testGenerationRef.current += 1
      // 重置所有测试相关状态
      setIsTesting(false)
      setTestingModelId(null)
      testingModelIdRef.current = null
      setTestPrompt('')
      setTestResult('')
    }
  }, [showTestDialog])

  // 确定最终显示的模型数据
  const finalModels = hasFilters ? paginatedFilteredModels : paginatedDisplayModels
  const finalTotalItems = hasFilters ? filteredTotalItems : totalItems
  const finalTotalPages = hasFilters ? filteredTotalPages : totalPages
  const finalCurrentPage = hasFilters ? filteredPage : currentPage

  const handleSave = async () => {
    // 验证名称长度
    if ((newModel.name || '').length > 100) {
      setSnackbar({ open: true, message: t('models.messages.nameMaxLength'), severity: 'error' })
      return
    }

    // 验证模型ID长度
    if ((newModel.modelId || '').length > 100) {
      setSnackbar({ open: true, message: t('models.messages.modelIdMaxLength'), severity: 'error' })
      return
    }

    // 验证描述长度（仅 LLM 模型）
    if (modelType === 'LLM' && (newModel.description || '').length > 500) {
      setSnackbar({ open: true, message: t('models.messages.descriptionMaxLength'), severity: 'error' })
      return
    }

    // LLM 模型需要验证超时时间范围
    if (modelType === 'LLM') {
      const timeout = newModel.timeout
      if (timeout === undefined || timeout < 1 || timeout > 3600) {
        setSnackbar({ open: true, message: t('models.messages.timeoutRange'), severity: 'error' })
        return
      }
    }

    // 验证必填字段
    if (!isFormValid()) {
      setSnackbar({ open: true, message: t('models.messages.fillRequiredFields'), severity: 'error' })
      return
    }

    // 根据模型类型选择不同的保存逻辑
    if (modelType === 'Embedding') {
      await handleSaveEmbeddingModel()
    } else {
      await handleSaveLLMModel()
    }
  }

  // 保存 LLM 模型
  const handleSaveLLMModel = async () => {
    if (editMode) {
      // Handle edit logic
      if (selectedModel) {
        try {
          await updateModelMutation.mutateAsync({ id: selectedModel.id, model: newModel as ModelConfig, spaceId: user?.spaceId || '' })
          setShowModelDialog(false)
          setCurrentPage(1) // 重置到第一页
          setSnackbar({ open: true, message: t('models.messages.updateSuccess'), severity: 'success' })
        } catch (error: any) {
          let errorMessage = t('models.messages.updateFailed')

          // 尝试多种访问路径来获取detail数据
          let detailData = null

          // 路径1: error?.response?.data?.detail
          if (error?.response?.data?.detail) {
            detailData = error.response.data.detail
          }
          // 路径2: error?.response?.data // 检查data是否直接包含detail
          else if (error?.response?.data && Object.keys(error.response.data).includes('detail')) {
            detailData = error.response.data.detail
          }
          // 路径3: error?.data // 检查error是否直接包含data
          else if (error?.data?.detail) {
            detailData = error.data.detail
          }
          // 路径4: 检查error本身是否有detail属性
          else if ((error as any)?.detail) {
            detailData = (error as any).detail
          }

          // 解析后端详细错误信息
          if (detailData) {
            const detail = detailData

            if (Array.isArray(detail)) {
              // 处理字段验证错误数组
              const fieldErrors = detail.map((errorDetail: any) => {
                let errorInfo = ''

                if (errorDetail.loc && errorDetail.loc.length > 1) {
                  // 当loc数组有第二个元素时，显示这个元素
                  const fieldName = errorDetail.loc[1]
                  const fieldMap: Record<string, string> = {
                    name: t('models.messages.fieldNames.name'),
                    modelId: t('models.messages.fieldNames.modelId'),
                    apiKey: t('models.messages.fieldNames.apiKey'),
                    provider: t('models.messages.fieldNames.provider'),
                    baseUrl: t('models.messages.fieldNames.baseUrl'),
                    description: t('models.messages.fieldNames.description'),
                  }
                  const displayName = fieldMap[fieldName] || fieldName

                  // 根据错误类型生成友好的提示信息
                  let friendlyMessage = ''
                  if (errorDetail.msg?.includes('at least 1 character')) {
                    friendlyMessage = t('models.messages.validationErrors.minLength')
                  } else if (errorDetail.msg?.includes('at most') && errorDetail.msg?.includes('characters')) {
                    const match = errorDetail.msg.match(/at most (\d+) characters/)
                    const maxLength = match ? match[1] : t('models.messages.validationErrors.maxLengthFallback')
                    friendlyMessage = t('models.messages.validationErrors.maxLength', { max: maxLength })
                  } else if (errorDetail.msg?.includes('required') || errorDetail.msg?.includes('field required')) {
                    friendlyMessage = t('models.messages.validationErrors.required')
                  } else if (errorDetail.msg?.includes('valid') && errorDetail.msg?.includes('url')) {
                    friendlyMessage = t('models.messages.validationErrors.invalidUrl')
                  } else if (errorDetail.msg?.includes('valid email')) {
                    friendlyMessage = t('models.messages.validationErrors.invalidEmail')
                  } else if (errorDetail.msg?.includes('already exists')) {
                    friendlyMessage = t('models.messages.validationErrors.alreadyExists')
                  } else if (errorDetail.msg?.includes('invalid')) {
                    friendlyMessage = t('models.messages.validationErrors.invalidFormat')
                  } else {
                    friendlyMessage = errorDetail.msg || t('models.messages.validationErrors.incorrectFormat')
                  }

                  errorInfo = `${displayName}${friendlyMessage}`
                } else {
                  // 没有loc第二个元素时，显示msg
                  errorInfo = errorDetail.msg || t('models.messages.validationErrors.formatError')
                }

                return errorInfo
              })
              errorMessage = fieldErrors.join('; ')
            } else if (typeof detail === 'string') {
              // 处理简单的字符串错误
              errorMessage = detail
            }
          } else if (error?.response?.data?.message) {
            errorMessage = error.response.data.message
          } else if (error?.message) {
            errorMessage = error.message
          }

          setSnackbar({
            open: true,
            message: errorMessage,
            severity: 'error',
          })
        }
      }
    } else {
      // Handle add logic
      if (!validateBaseUrl(newModel.baseUrl || '')) {
        setSnackbar({ open: true, message: t('models.messages.invalidBaseUrl'), severity: 'error' })
        return
      }

      try {
        const model: ModelConfig = {
          id: Date.now().toString(),
          ...newModel,
          maxTokens: newModel.maxTokens || 4000,
          timeout: newModel.timeout || 60,
          usage: {
            totalRequests: 0,
            totalTokens: 0,
            successRate: 100,
            averageResponseTime: 0,
            lastUsed: '-',
          },
        } as ModelConfig

        await createModelMutation.mutateAsync({ model, spaceId: user?.spaceId || '' })
        setShowModelDialog(false)
        setCurrentPage(1) // 重置到第一页
        setSnackbar({ open: true, message: t('models.messages.addSuccess'), severity: 'success' })
      } catch (error: any) {
        let errorMessage = t('models.messages.addFailed')

        // 尝试多种访问路径来获取detail数据
        let detailData = null

        // 路径1: error?.response?.data?.detail
        if (error?.response?.data?.detail) {
          detailData = error.response.data.detail
        }
        // 路径2: error?.response?.data // 检查data是否直接包含detail
        else if (error?.response?.data && Object.keys(error.response.data).includes('detail')) {
          detailData = error.response.data.detail
        }
        // 路径3: error?.data // 检查error是否直接包含data
        else if (error?.data?.detail) {
          detailData = error.data.detail
        }
        // 路径4: 检查error本身是否有detail属性
        else if ((error as any)?.detail) {
          detailData = (error as any).detail
        }

        // 解析后端详细错误信息
        if (detailData) {
          const detail = detailData

          if (Array.isArray(detail)) {
            // 处理字段验证错误数组
            const fieldErrors = detail.map((errorDetail: any) => {
              let errorInfo = ''

              if (errorDetail.loc && errorDetail.loc.length > 1) {
                // 当loc数组有第二个元素时，显示这个元素
                const fieldName = errorDetail.loc[1]
                const fieldMap: Record<string, string> = {
                  name: t('models.messages.fieldNames.name'),
                  modelId: t('models.messages.fieldNames.modelId'),
                  apiKey: t('models.messages.fieldNames.apiKey'),
                  provider: t('models.messages.fieldNames.provider'),
                  baseUrl: t('models.messages.fieldNames.baseUrl'),
                  description: t('models.messages.fieldNames.description'),
                }
                const displayName = fieldMap[fieldName] || fieldName

                // 根据错误类型生成友好的提示信息
                let friendlyMessage = ''
                if (errorDetail.msg?.includes('at least 1 character')) {
                  friendlyMessage = t('models.messages.validationErrors.minLength')
                } else if (errorDetail.msg?.includes('at most') && errorDetail.msg?.includes('characters')) {
                  const match = errorDetail.msg.match(/at most (\d+) characters/)
                  const maxLength = match ? match[1] : t('models.messages.validationErrors.maxLengthFallback')
                  friendlyMessage = t('models.messages.validationErrors.maxLength', { max: maxLength })
                } else if (errorDetail.msg?.includes('required') || errorDetail.msg?.includes('field required')) {
                  friendlyMessage = t('models.messages.validationErrors.required')
                } else if (errorDetail.msg?.includes('valid') && errorDetail.msg?.includes('url')) {
                  friendlyMessage = t('models.messages.validationErrors.invalidUrl')
                } else if (errorDetail.msg?.includes('valid email')) {
                  friendlyMessage = t('models.messages.validationErrors.invalidEmail')
                } else {
                  friendlyMessage = errorDetail.msg || t('models.messages.validationErrors.incorrectFormat')
                }

                errorInfo = `${displayName}${friendlyMessage}`
              } else {
                // 没有loc第二个元素时，显示msg
                errorInfo = errorDetail.msg || t('models.messages.validationErrors.formatError')
              }

              return errorInfo
            })
            errorMessage = fieldErrors.join('; ')
          } else if (typeof detail === 'string') {
            // 处理简单的字符串错误
            errorMessage = detail
          }
        } else if (error?.response?.data?.message) {
          errorMessage = error.response.data.message
        } else if (error?.message) {
          errorMessage = error.message
        }

        setSnackbar({
          open: true,
          message: errorMessage,
          severity: 'error',
        })
      }
    }
  }

  // 保存 Embedding 模型
  const handleSaveEmbeddingModel = async () => {
    if (!validateBaseUrl(newModel.baseUrl || '')) {
      setSnackbar({ open: true, message: t('models.messages.invalidBaseUrl'), severity: 'error' })
      return
    }

    // 构建 Embedding 模型数据
    const embeddingModel: Partial<FrontendEmbeddingModelConfig> = {
      name: newModel.name || '',
      protocol: 'openai', // Embedding 目前只支持 OpenAI 协议
      modelId: newModel.modelId || '',
      // 编辑模式下：如果 apiKey 为空或与脱敏密钥相同，则不更新密钥（不传 apiKey 字段）
      // 创建模式下：必须提供 apiKey
      apiKey: editMode && (!newModel.apiKey || newModel.apiKey === selectedModel?.apiKey) ? undefined : newModel.apiKey || '',
      baseUrl: newModel.baseUrl || '',
      maxBatchSize: newModel.maxBatchSize || 8,
      isActive: newModel.isActive ?? true,
    }

    if (editMode && selectedModel) {
      // 更新 Embedding 模型
      try {
        await updateEmbeddingModelMutation.mutateAsync({
          id: selectedModel.id,
          model: embeddingModel,
          spaceId: user?.spaceId || '',
        })
        setShowModelDialog(false)
        setCurrentPage(1)
        setSnackbar({ open: true, message: t('models.messages.embeddingModel.updateSuccess'), severity: 'success' })
      } catch (error: any) {
        console.error('更新 Embedding 模型失败:', error)
        const errorMessage = error?.response?.data?.message || error?.message || t('models.messages.embeddingModel.updateFailed')
        setSnackbar({ open: true, message: errorMessage, severity: 'error' })
      }
    } else {
      // 创建 Embedding 模型
      try {
        await createEmbeddingModelMutation.mutateAsync({
          model: embeddingModel,
          spaceId: user?.spaceId || '',
        })
        setShowModelDialog(false)
        setCurrentPage(1)
        setSnackbar({ open: true, message: t('models.messages.embeddingModel.createSuccess'), severity: 'success' })
      } catch (error: any) {
        console.error('创建 Embedding 模型失败:', error)
        const errorMessage = error?.response?.data?.message || error?.message || t('models.messages.embeddingModel.createFailed')
        setSnackbar({ open: true, message: errorMessage, severity: 'error' })
      }
    }
  }

  const handleDeleteModel = async (modelId: string, modelName: string) => {
    setDeleteDialog({
      isOpen: true,
      modelId,
      modelName,
      modelType: currentModelType,
    })
  }

  const confirmDeleteModel = async () => {
    if (deleteDialog.modelId) {
      try {
        // 根据保存的模型类型调用不同的删除 API
        if (deleteDialog.modelType === 'Embedding') {
          await deleteEmbeddingModelMutation.mutateAsync({ id: deleteDialog.modelId, spaceId: user?.spaceId || '' })
        } else {
          await deleteModelMutation.mutateAsync({ id: deleteDialog.modelId, spaceId: user?.spaceId || '' })
        }
        setSnackbar({ open: true, message: t('models.messages.deleteSuccess'), severity: 'success' })
        setDeleteDialog({ isOpen: false, modelId: '', modelName: '', modelType: 'LLM', knowledgeBases: undefined })
      } catch (error: any) {
        // 检查是否是"正在被使用"的错误
        // 错误可能来自 error.response.data.detail 或 error.detail 或 error.message
        const errorMessage = error?.response?.data?.detail || error?.detail || error?.message || String(error)
        const isInUseError =
          errorMessage.toLowerCase().includes('in use') ||
          errorMessage.toLowerCase().includes('being used') ||
          errorMessage.toLowerCase().includes('cannot delete') ||
          errorMessage.toLowerCase().includes(t('models.messages.inUse').toLowerCase())

        if (isInUseError && deleteDialog.modelType === 'Embedding') {
          // 解析知识库列表
          // 错误信息格式: "Cannot delete embedding model config 'xxx' (ID: 4) because it is being used by 96 knowledge base(s): name1, name2, ..."
          // 使用更宽松的正则表达式，匹配到字符串末尾
          const kbMatch = errorMessage.match(/knowledge base\(s\):\s*(.+)/i)
          let knowledgeBases: string[] = []

          if (kbMatch && kbMatch[1]) {
            // 分割知识库名称（用逗号分隔）
            knowledgeBases = kbMatch[1]
              .split(',')
              .map((kb: string) => kb.trim())
              .filter((kb: string) => kb.length > 0)
          }

          // 显示警告对话框，列出使用的知识库
          setDeleteDialog({
            isOpen: true,
            modelId: deleteDialog.modelId,
            modelName: deleteDialog.modelName,
            modelType: deleteDialog.modelType,
            knowledgeBases: knowledgeBases.length > 0 ? knowledgeBases : undefined,
          })
        } else {
          setSnackbar({ open: true, message: t('models.messages.deleteFailed'), severity: 'error' })
          setDeleteDialog({ isOpen: false, modelId: '', modelName: '', modelType: 'LLM', knowledgeBases: undefined })
        }
      }
    }
  }

  const cancelDeleteModel = () => {
    setDeleteDialog({ isOpen: false, modelId: '', modelName: '', modelType: 'LLM', knowledgeBases: undefined })
  }

  // 测试 Embedding 模型
  const handleTestEmbeddingModel = async (modelId: string) => {
    setTestingModelId(modelId)
    testingModelIdRef.current = modelId
    try {
      const result = await testEmbeddingModelMutation.mutateAsync({
        id: modelId,
        testRequest: { text: t('models.messages.testText') },
      })

      // 格式化测试结果（result 是 EmbeddingModelTestResponse，包含 data, model, usage 等字段）
      const embeddingData = result.data?.[0]
      const dimension = embeddingData?.embedding?.length || 0
      const usage = result.usage || {}
      const model = result.model || 'unknown'

      setSnackbar({
        open: true,
        message: t('models.messages.embeddingModel.testSuccess', {
          model,
          dimension,
          tokens: usage.total_tokens || 0,
        }),
        severity: 'success',
      })
    } catch (error: any) {
      const errorDetail = error?.detail || error?.response?.data?.detail || error?.message || ''
      const raw = String(errorDetail || '')
      // 后端统一返回英文，按英文匹配后 replace 为当前语言的 i18n
      if (!raw) {
        setSnackbar({ open: true, message: t('models.messages.modelTestError.testFailed'), severity: 'error' })
      } else {
        const modelNameMatch = raw.match(/Embedding model '([^']+)'/i)
        const modelName = modelNameMatch ? modelNameMatch[1] : ''
        if (raw.toLowerCase().includes('is not active') || raw.toLowerCase().includes('not active')) {
          setSnackbar({ open: true, message: t('models.messages.modelTestError.modelNotActive', { modelName }), severity: 'error' })
        } else {
          let detail = ''
          const colonIndex = raw.indexOf(':')
          if (colonIndex > 0) detail = raw.substring(colonIndex + 1).trim()
          if (!detail) detail = raw
          let errorType = 'unknownError'
          if (raw.includes('model name') && raw.includes('is invalid')) errorType = 'modelNameInvalid'
          else if (raw.includes('API key') && raw.includes('is invalid')) errorType = 'apiKeyInvalid'
          else if (raw.includes('API URL') && raw.includes('is invalid')) errorType = 'apiUrlInvalid'
          else if (raw.includes('request parameters') && raw.includes('is invalid')) errorType = 'requestParamsInvalid'
          else if (raw.includes('API server') && raw.includes('error')) errorType = 'apiServerError'
          else if (raw.includes('configuration') && raw.includes('is invalid')) errorType = 'configInvalid'
          else if (raw.includes('insufficient quota') && raw.includes('is invalid')) errorType = 'insufficientQuota'
          else if (raw.includes('API call failed')) errorType = 'apiCallFailed'
          setSnackbar({
            open: true,
            message: t(`models.messages.modelTestError.${errorType}`, { modelName, detail }),
            severity: 'error',
          })
        }
      }
    } finally {
      setTestingModelId(null)
      testingModelIdRef.current = null
    }
  }

  const handleTestModel = async () => {
    if (!testPrompt.trim() || !selectedModel) return
    if (testPrompt.length > 1000) {
      return
    }

    const currentModelId = selectedModel.id
    // 增加测试代数，使旧测试的失效
    testGenerationRef.current += 1
    const currentGeneration = testGenerationRef.current

    setIsTesting(true)
    setTestingModelId(currentModelId)
    testingModelIdRef.current = currentModelId

    try {
      const result = await testModelMutation.mutateAsync({
        id: currentModelId,
        prompt: testPrompt,
        spaceId: user?.spaceId || '',
        parameters: {
          temperature: selectedModel.temperature ?? 0.7,
          top_p: selectedModel.topp ?? 0.9,
          max_tokens: selectedModel.maxTokens ?? 4096,
        },
      })

      // 只有当代数匹配、对话框仍然打开且模型ID匹配时才设置结果
      if (currentGeneration === testGenerationRef.current && showTestDialog && testingModelIdRef.current === currentModelId) {
        setTestResult(
          `${t('models.testSuccess')}\n${t('models.modelList.name')}: ${selectedModel.name}\n${t('models.testPrompt')}: ${testPrompt}\n\n${t('models.testResponse')}: ${result.response || t('models.testCompletion')}\n\n${t('models.averageResponseTime')}: ${result.latency.toFixed(3)}s\n\n${t('models.configInfo')}: \n- ${t('models.modelConfig.parameters.temperature')}: ${selectedModel.temperature}\n- top_p: ${selectedModel.topp}\n- max_tokens: ${selectedModel.maxTokens}\n- ${t('models.modelList.provider')}: ${selectedModel.provider}`,
        )
      }
    } catch (error: any) {
      let errorMessage = t('models.testFailed')

      // 尝试多种访问路径来获取detail数据
      let detailData = null

      // 路径1: error?.response?.data?.detail
      if (error?.response?.data?.detail) {
        detailData = error.response.data.detail
      }
      // 路径2: error?.response?.data // 检查data是否直接包含detail
      else if (error?.response?.data && Object.keys(error.response.data).includes('detail')) {
        detailData = error.response.data.detail
      }
      // 路径3: error?.data // 检查error是否直接包含data
      else if (error?.data?.detail) {
        detailData = error.data.detail
      }
      // 路径4: 检查error本身是否有detail属性
      else if ((error as any)?.detail) {
        detailData = (error as any).detail
      }

      // 解析后端详细错误信息
      if (detailData) {
        if (typeof detailData === 'string') {
          errorMessage = detailData
        } else {
          errorMessage = JSON.stringify(detailData)
        }
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error?.message) {
        errorMessage = error.message
      }

      if (currentGeneration === testGenerationRef.current && showTestDialog && testingModelIdRef.current === currentModelId) {
        // 后端统一返回英文，按英文匹配后 replace 为当前语言的 i18n
        const localizedError = errorMessage
          .replace(/Model call failed, please check model configuration/gi, t('models.messages.modelTestError.modelCallFailedCheckConfig'))
          .replace(/API Key or model ID invalid, please check model configuration/gi, t('models.messages.modelTestError.apiKeyOrModelInvalid'))
          .replace(/Model service address unreachable, please check base URL or network configuration/gi, t('models.messages.modelTestError.serviceUnreachable'))
        setTestResult(
          `${t('models.testFailed')}: ${localizedError}\n${t('models.modelList.name')}: ${selectedModel.name}\n${t('models.testPrompt')}: ${testPrompt}`,
        )
      }
    } finally {
      // 只有当正在测试的模型ID仍等于当前模型ID时才重置 isTesting
      // 这确保不会取消新测试的状态
      if (testingModelIdRef.current === currentModelId) {
        setIsTesting(false)
        setTestingModelId(null)
      }
      // 只有当代数和模型ID都匹配时才清除 testingModelIdRef
      if (currentGeneration === testGenerationRef.current && testingModelIdRef.current === currentModelId) {
        testingModelIdRef.current = null
      }
      // 无论测试成功还是失败，都刷新模型列表以更新统计信息
      await Promise.all([refetchLLM(), refetchEmbedding()])
    }
  }

  // Clear all filters function
  const handleClearFilters = useCallback(() => {
    setSearchTerm('')
    setFilterProvider('all')
    setFilterStatus('all')
    setFilteredPage(1) // 重置筛选分页到第一页
    setCurrentPage(1) // 重置到第一页
  }, [])

  // Tag management functions
  const handleAddTag = () => {
    const currentTags = newModel.tags || []
    const trimmedTag = newTag.trim()
    if (!trimmedTag) return
    if (trimmedTag.length > 100) {
      setSnackbar({
        open: true,
        message: t('models.messages.tagLengthLimit'),
        severity: 'warning',
      })
      return
    }
    if (!currentTags.includes(trimmedTag)) {
      if (currentTags.length >= 10) {
        setSnackbar({
          open: true,
          message: t('models.messages.tagsLimit'),
          severity: 'warning',
        })
        return
      }
      setNewModel({ ...newModel, tags: [...currentTags, trimmedTag] })
      setNewTag('')
    }
  }

  const handleRemoveTag = (tagIndex: number) => {
    const updatedTags = (newModel.tags || []).filter((_, index) => index !== tagIndex)
    setNewModel({ ...newModel, tags: updatedTags })
  }

  const toggleModelStatus = async (modelId: string) => {
    try {
      // 根据当前 tab 的模型类型调用不同的切换状态 API
      if (currentModelType === 'Embedding') {
        await toggleEmbeddingStatusMutation.mutateAsync({ id: modelId, spaceId: user?.spaceId || '' })
      } else {
        await toggleStatusMutation.mutateAsync({ id: modelId, spaceId: user?.spaceId || '' })
      }
    } catch (error) {
      setSnackbar({ open: true, message: t('models.messages.toggleStatusFailed'), severity: 'error' })
    }
  }

  const removeTag = async (model: UnifiedModelListItem, tagIndex: number) => {
    try {
      const updatedModel = {
        ...model,
        tags: model.tags.filter((_, i) => i !== tagIndex),
      }
      if (currentModelType === 'Embedding') {
        await updateEmbeddingModelMutation.mutateAsync({ id: model.id, model: updatedModel, spaceId: user?.spaceId || '' })
      } else {
        await updateModelMutation.mutateAsync({ id: model.id, model: updatedModel, spaceId: user?.spaceId || '' })
        refetch()
      }
    } catch (error) {
      setSnackbar({ open: true, message: t('models.messages.removeTagFailed'), severity: 'error' })
    }
  }

  // Toolbar components for CommonPageLayout
  const toolbarLeft = useMemo(
    () => (
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative w-80">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
          <input
            type="text"
            placeholder={
              currentModelType === 'LLM'
                ? t('models.modelList.searchPlaceholder')
                : t('models.modelList.searchPlaceholder')
                    .replace(/或标签|标签/g, '')
                    .replace(/\s+/g, ' ')
                    .trim()
            }
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full h-8 pl-8 pr-7 bg-white border border-[#E5E7EB] rounded-[6px] text-sm text-[#1F2937] placeholder-[#9CA3AF] focus:outline-none focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] transition-colors"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
              type="button"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Provider filter */}
        <select
          value={filterProvider}
          onChange={e => setFilterProvider(e.target.value)}
          className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
        >
          <option value="all">{t('models.modelList.allProviders')}</option>
          <option value={ModelProvider.OPENAI}>OpenAI</option>
          <option value={ModelProvider.SILICONFLOW}>SiliconFlow</option>
        </select>

        {/* Status filter */}
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
        >
          <option value="all">{t('models.modelList.allStatuses')}</option>
          <option value="active">{t('models.status.active')}</option>
          <option value="inactive">{t('models.status.inactive')}</option>
        </select>

        {/* Clear filters */}
        {(searchTerm || filterProvider !== 'all' || filterStatus !== 'all') && (
          <button
            onClick={handleClearFilters}
            className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] hover:border-[#d1d5db] transition-colors"
          >
            {t('models.modelList.clearFilters')}
          </button>
        )}
      </div>
    ),
    [searchTerm, filterProvider, filterStatus, t, currentModelType, handleClearFilters],
  )

  const toolbarRight = useMemo(
    () => (
      <button
        onClick={() => handleOpenModelDialog(null)}
        className="btn-primary h-8 flex items-center gap-2 text-sm px-4"
      >
        <Plus className="w-4 h-4" />
        <span>{t('models.addModel')}</span>
      </button>
    ),
    [t, activeTab], // 添加 activeTab 依赖，确保 tab 切换时重新创建
  )

  const tableView = useMemo(() => {
    if (activeTab === 'llm') {
      return (
        <LLMModelsTable
          models={finalModels as unknown as FrontendModelConfig[]}
          loading={isLoading}
          onEdit={model => handleOpenModelDialog({ ...model, modelType: 'LLM' } as UnifiedModelListItem)}
          onDelete={model => handleDeleteModel(model.id, model.name)}
          onToggleStatus={model => toggleModelStatus(model.id)}
          onTest={model => {
            setSelectedModel({ ...model, modelType: 'LLM' } as UnifiedModelListItem)
            setShowTestDialog(true)
          }}
          searchTerm={searchTerm}
          hasFilters={hasFilters}
          onCreateClick={() => handleOpenModelDialog(null)}
        />
      )
    } else {
      return (
        <EmbeddingModelsTable
          models={finalModels as unknown as FrontendEmbeddingModelConfig[]}
          loading={isLoading}
          onEdit={model => handleOpenModelDialog({ ...model, modelType: 'Embedding' } as UnifiedModelListItem)}
          onDelete={model => handleDeleteModel(model.id, model.name)}
          onToggleStatus={model => toggleModelStatus(model.id)}
          onTest={model => handleTestEmbeddingModel(model.id)}
          testingModelId={testingModelId}
          searchTerm={searchTerm}
          hasFilters={hasFilters}
          onCreateClick={() => handleOpenModelDialog(null)}
        />
      )
    }
  }, [activeTab, finalModels, isLoading, testingModelId, searchTerm, hasFilters])

  const tabs: TabConfig[] = useMemo(
    () => [
      { key: 'llm', label: `${t('models.tabs.llm')} (${isLoadingLLM ? '...' : modelsResponse?.total || 0})` },
      { key: 'embedding', label: `${t('models.tabs.embedding')} (${isLoadingEmbedding ? '...' : embeddingModelsResponse?.total || 0})` },
    ],
    [modelsResponse?.total, embeddingModelsResponse?.total, isLoadingLLM, isLoadingEmbedding, t],
  )

  return (
    <>
      <CommonPageLayout
        title={t('models.title')}
        tabs={tabs}
        defaultTabKey="llm"
        onTabChange={setActiveTab}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
        tableView={tableView}
        pager={{
          currentPage: finalCurrentPage,
          pageSize: pageSize,
          total: finalTotalItems,
          pageSizeOptions: [10, 20, 50],
        }}
        onPagerChange={(page, size) => {
          if (size !== pageSize) setPageSize(size)
          if (hasFilters) setFilteredPage(page)
          else setCurrentPage(page)
        }}
        viewType="table"
        showViewToggle={false}
        loading={isLoading}
        error={error ? (error instanceof Error ? error.message : String(error)) : null}
      />

      {/* Add/Edit Model Dialog */}
      <Dialog
        open={showModelDialog}
        onClose={() => {}} // 完全禁用自动关闭，只能通过取消按钮退出
        maxWidth="md"
        fullWidth
        disableRestoreFocus
        // 禁用ESC键
        disableEscapeKeyDown={true}
      >
        <DialogTitle className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              {editMode ? <Settings className="w-4 h-4 text-white" /> : <Plus className="w-4 h-4 text-white" />}
            </div>
            <Typography variant="h6" className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">
              {editMode ? t('models.dialog.editModel') : t('models.dialog.addNewModel')}
            </Typography>
          </div>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={3} className="pt-4">
            {/* 模型基础信息区域 */}
            <Grid item xs={12}>
              <Typography variant="h6" className="text-gray-800 mb-3 font-semibold border-b border-gray-200 pb-2">
                {t('models.dialog.basicInfo')}
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label={t('models.modelConfig.basicInfo.name')}
                sx={{
                  '& .MuiInputLabel-asterisk': {
                    color: 'red',
                  },
                }}
                value={newModel.name}
                onChange={e => {
                  const value = e.target.value
                  if (value.length <= 100) {
                    setNewModel({ ...newModel, name: value })
                  }
                }}
                placeholder=""
                variant="outlined"
                error={(newModel.name || '').length > 100}
                helperText={
                  (newModel.name || '').length > 80 ? (
                    <span style={{ color: 'orange' }}>{t('models.modelConfig.basicInfo.nameError')}</span>
                  ) : (
                    <span style={{ color: '#666' }}>
                      {modelType === 'Embedding' ? t('models.modelConfig.basicInfo.embeddingNameHint') : t('models.modelConfig.basicInfo.nameHint')} |{' '}
                      {t('models.modelConfig.basicInfo.charNum')}
                      {newModel.name?.length || 0}/100
                    </span>
                  )
                }
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>{t('models.modelConfig.basicInfo.provider')}</InputLabel>
                <Select
                  value={newModel.provider}
                  label={t('models.modelConfig.basicInfo.provider')}
                  onChange={e => setNewModel({ ...newModel, provider: e.target.value })}
                  disabled={modelType === 'Embedding'} // Embedding 只支持 OpenAI
                >
                  <MenuItem value={ModelProvider.OPENAI}>OpenAI</MenuItem>
                  {modelType === 'LLM' && <MenuItem value={ModelProvider.SILICONFLOW}>SiliconFlow</MenuItem>}
                </Select>
                <Typography variant="caption" className="text-gray-600 mt-1">
                  {modelType === 'Embedding' ? t('models.modelConfig.basicInfo.embeddingProviderHint') : t('models.modelConfig.basicInfo.providerHint')}
                </Typography>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label={t('models.modelConfig.basicInfo.type')}
                sx={{
                  '& .MuiInputLabel-asterisk': {
                    color: 'red',
                  },
                }}
                value={newModel.modelId}
                onChange={e => {
                  const value = e.target.value
                  if (value.length <= 100) {
                    setNewModel({ ...newModel, modelId: value })
                  }
                }}
                placeholder=""
                variant="outlined"
                error={(newModel.modelId || '').length > 100}
                helperText={
                  (newModel.modelId || '').length > 80 ? (
                    <span style={{ color: 'orange' }}>{t('models.messages.modelIdMaxLength')}</span>
                  ) : (
                    <span style={{ color: '#666' }}>
                      {modelType === 'Embedding' ? t('models.modelConfig.basicInfo.embeddingTypeHint') : t('models.modelConfig.basicInfo.typeHint')} |{' '}
                      {t('models.modelConfig.basicInfo.charNum')}
                      {newModel.modelId?.length || 0}/100
                    </span>
                  )
                }
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label={t('models.modelConfig.parameters.apiKey')}
                sx={{
                  '& .MuiInputLabel-asterisk': {
                    color: 'red',
                  },
                }}
                type="password"
                value={newModel.apiKey}
                onChange={e => {
                  const value = e.target.value
                  if (value.length <= 500) {
                    setNewModel({ ...newModel, apiKey: value })
                  }
                }}
                placeholder={editMode ? t('models.messages.apiKeyEmptyHint') : ''}
                variant="outlined"
                error={(newModel.apiKey || '').length > 500}
                helperText={
                  (newModel.apiKey || '').length > 500 ? (
                    <span style={{ color: 'orange' }}>{t('models.messages.apiKeyMaxLength')}</span>
                  ) : (
                    <span style={{ color: '#666' }}>
                      {editMode ? t('models.messages.apiKeyEditHint') : t('models.modelConfig.parameters.apiKeyHint')}: {newModel.apiKey?.length || 0}/500
                    </span>
                  )
                }
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label={t('models.modelConfig.parameters.baseUrl')}
                sx={{
                  '& .MuiInputLabel-asterisk': {
                    color: 'red',
                  },
                }}
                value={newModel.baseUrl}
                onChange={e => {
                  const value = e.target.value
                  if (value.length <= 100) {
                    setNewModel({ ...newModel, baseUrl: value })
                    validateBaseUrl(value)
                  }
                }}
                placeholder=""
                variant="outlined"
                disabled={false} // 允许编辑基础URL
                error={!!baseUrlError || (newModel.baseUrl || '').length > 100}
                helperText={
                  baseUrlError ? (
                    <span style={{ color: 'red' }}>{baseUrlError}</span>
                  ) : (newModel.baseUrl || '').length > 100 ? (
                    <span style={{ color: 'orange' }}>{t('models.messages.baseUrlMaxLength')}</span>
                  ) : (
                    <span style={{ color: '#666' }}>
                      {modelType === 'Embedding' ? t('models.messages.embeddingBaseUrlHint') : t('models.modelConfig.parameters.baseUrlHint')}:{' '}
                      {newModel.baseUrl?.length || 0}/100
                    </span>
                  )
                }
              />
            </Grid>
            {/* 标签字段 - 仅 LLM 模型显示 */}
            {modelType === 'LLM' && (
              <Grid item xs={12}>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <TextField
                      label={t('models.modelConfig.basicInfo.tags')}
                      placeholder=""
                      value={newTag}
                      onChange={e => {
                        const value = e.target.value
                        if (value.length <= 100) {
                          setNewTag(value)
                        }
                      }}
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          const currentTags = newModel.tags || []
                          const trimmedTag = newTag.trim()
                          if (!trimmedTag) return
                          if (trimmedTag.length > 100) {
                            setSnackbar({
                              open: true,
                              message: t('models.messages.tagLengthLimit'),
                              severity: 'warning',
                            })
                            return
                          }
                          if (!currentTags.includes(trimmedTag)) {
                            if (currentTags.length >= 10) {
                              setSnackbar({
                                open: true,
                                message: t('models.messages.tagsLimit'),
                                severity: 'warning',
                              })
                              return
                            }
                            setNewModel({
                              ...newModel,
                              tags: [...currentTags, trimmedTag],
                            })
                            setNewTag('')
                          }
                        }
                      }}
                      variant="outlined"
                      className="flex-1 !mr-4"
                      disabled={(newModel.tags || []).length >= 10}
                      helperText={t('models.messages.tagLength', { length: newTag.length })}
                      FormHelperTextProps={{
                        className: newTag.length >= 100 ? 'text-red-600' : 'text-gray-600',
                      }}
                    />
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={handleAddTag}
                      className="border-gray-300 text-gray-700"
                      disabled={(newModel.tags || []).length >= 10}
                    >
                      {t('common.buttons.add')}
                    </Button>
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <Typography variant="caption" className={(newModel.tags || []).length >= 10 ? 'text-red-600' : 'text-gray-600'}>
                      {t('models.modelConfig.basicInfo.tagsNum')}：{(newModel.tags || []).length}/10
                      {(newModel.tags || []).length >= 10 && ` (${t('models.modelConfig.basicInfo.tagsLimit')})`}
                    </Typography>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(newModel.tags || []).map((tag, index) => (
                      <Chip
                        key={index}
                        label={tag}
                        onDelete={() => handleRemoveTag(index)}
                        className="bg-blue-100 text-blue-800 border border-blue-200 hover:bg-blue-200"
                        size="small"
                      />
                    ))}
                  </div>
                </div>
              </Grid>
            )}
            {/* 描述字段 - 仅 LLM 模型显示 */}
            {modelType === 'LLM' && (
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label={t('models.modelConfig.basicInfo.description')}
                  value={newModel.description}
                  onChange={e => {
                    const value = e.target.value
                    if (value.length <= 500) {
                      setNewModel({ ...newModel, description: value })
                    }
                  }}
                  placeholder=""
                  variant="outlined"
                  error={(newModel.description || '').length > 500} // 只在长度超限时显示红色边框
                  helperText={
                    (newModel.description || '').length > 500 ? (
                      <span style={{ color: 'orange' }}>{t('models.messages.descriptionMaxLength')}</span>
                    ) : (
                      <span style={{ color: '#666' }}>
                        {t('models.modelConfig.basicInfo.descriptionLimit')} {newModel.description?.length || 0}/500
                      </span>
                    )
                  }
                />
              </Grid>
            )}

            {/* 模型参数配置区域 */}
            <Grid item xs={12}>
              <Typography variant="h6" className="text-gray-800 mb-3 font-semibold border-b border-gray-200 pb-2 mt-4">
                {t('models.modelConfig.parameters.title')}
              </Typography>
            </Grid>
            {/* LLM 模型参数 */}
            {modelType === 'LLM' && (
              <>
                <Grid item xs={12} md={12}>
                  <TextField
                    fullWidth
                    required
                    label={t('models.modelConfig.parameters.timeout')}
                    type="number"
                    placeholder=""
                    value={newModel.timeout || ''}
                    error={!(newModel.timeout && newModel.timeout >= 1 && newModel.timeout <= 3600)} // 只在URL格式错误时显示红色边框
                    onChange={e => {
                      const value = e.target.value
                      if (value === '') {
                        setNewModel({ ...newModel, timeout: undefined })
                        return
                      }

                      let numValue = parseInt(value)
                      if (!isNaN(numValue)) {
                        // 自动将值限制在有效范围内
                        if (numValue < 1) {
                          numValue = 1
                        } else if (numValue > 3600) {
                          numValue = 3600
                        }
                        setNewModel({ ...newModel, timeout: numValue })
                      }
                    }}
                    inputProps={{
                      style: {
                        MozAppearance: 'textfield',
                      },
                    }}
                    sx={{
                      '& input[type=number]::-webkit-outer-spin-button': {
                        WebkitAppearance: 'none',
                        margin: 0,
                      },
                      '& input[type=number]::-webkit-inner-spin-button': {
                        WebkitAppearance: 'none',
                        margin: 0,
                      },
                      '& input[type=number]': {
                        MozAppearance: 'textfield',
                      },
                      '& .MuiInputLabel-asterisk': {
                        color: 'red',
                      },
                    }}
                    variant="outlined"
                    helperText={t('models.modelConfig.parameters.timeoutDesc')}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <Typography gutterBottom sx={{ mb: 0 }}>
                      {t('models.modelConfig.parameters.temperature')}
                    </Typography>
                    <Tooltip title={t('models.modelConfig.parameters.temperatureDesc')} placement="top" arrow>
                      <IconButton size="small" sx={{ p: 0, color: 'text.secondary', '&:hover': { color: 'text.primary' } }}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Slider
                    value={newModel.temperature}
                    onChange={(_, value) =>
                      setNewModel({
                        ...newModel,
                        temperature: value as number,
                      })
                    }
                    min={0}
                    max={2}
                    step={0.1}
                    valueLabelDisplay="on"
                    marks={[
                      { value: 0, label: '0' },
                      { value: 1, label: '1' },
                      { value: 2, label: '2' },
                    ]}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <Typography gutterBottom sx={{ mb: 0 }}>
                      {t('models.modelConfig.parameters.topp')}
                    </Typography>
                    <Tooltip title={t('models.modelConfig.parameters.toppDesc')} placement="top" arrow>
                      <IconButton size="small" sx={{ p: 0, color: 'text.secondary', '&:hover': { color: 'text.primary' } }}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Slider
                    value={newModel.topp}
                    onChange={(_, value) =>
                      setNewModel({
                        ...newModel,
                        topp: value as number,
                      })
                    }
                    min={0}
                    max={1}
                    step={0.1}
                    valueLabelDisplay="on"
                    marks={[
                      { value: 0, label: '0' },
                      { value: 0.5, label: '0.5' },
                      { value: 1, label: '1' },
                    ]}
                  />
                </Grid>
              </>
            )}

            {/* Embedding 模型参数 */}
            {modelType === 'Embedding' && (
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label={t('models.messages.maxBatchSize')}
                  type="number"
                  placeholder=""
                  value={newModel.maxBatchSize || ''}
                  onChange={e => {
                    const value = e.target.value
                    if (value === '') {
                      setNewModel({ ...newModel, maxBatchSize: undefined })
                      return
                    }

                    let numValue = parseInt(value)
                    if (!isNaN(numValue)) {
                      // 自动将值限制在有效范围内
                      if (numValue < 1) {
                        numValue = 1
                      } else if (numValue > 10) {
                        numValue = 10
                      }
                      setNewModel({ ...newModel, maxBatchSize: numValue })
                    }
                  }}
                  inputProps={{
                    min: 1,
                    max: 10,
                  }}
                  sx={{
                    '& input[type=number]::-webkit-outer-spin-button': {
                      WebkitAppearance: 'none',
                      margin: 0,
                    },
                    '& input[type=number]::-webkit-inner-spin-button': {
                      WebkitAppearance: 'none',
                      margin: 0,
                    },
                    '& input[type=number]': {
                      MozAppearance: 'textfield',
                    },
                  }}
                  variant="outlined"
                  helperText={t('models.messages.maxBatchSizeHint')}
                />
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions className="bg-gray-50 px-6 py-4">
          <Button
            onClick={() => setShowModelDialog(false)}
            className="text-gray-600 hover:text-gray-700 hover:bg-gray-100 px-4 py-2 rounded-lg transition-all duration-200"
          >
            {t('common.buttons.cancel')}
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!isFormValid()}
            className={`px-6 py-2 rounded-lg font-semibold transform transition-all duration-300 shadow-sm ${
              !isFormValid()
                ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white hover:scale-105 hover:shadow-xl'
            }`}
          >
            {editMode ? t('models.saveModel') : t('models.addModel')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Model Dialog */}
      <Dialog
        open={showTestDialog}
        onClose={() => {
          setShowTestDialog(false)
          // useEffect 会处理状态重置
        }}
        maxWidth="md"
        fullWidth
        PaperProps={{
          className: 'rounded-2xl shadow-2xl border border-gray-100',
        }}
        disableRestoreFocus
      >
        <DialogTitle className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <Play className="w-4 h-4 text-white" />
            </div>
            <Typography variant="h6" className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">
              {t('models.testModel')}: {selectedModel?.name}
            </Typography>
          </div>
        </DialogTitle>
        <DialogContent>
          <div className="space-y-4 pt-4">
            {/* 常用语句 */}
            <div>
              <Typography variant="subtitle2" className="text-gray-700 mb-2 font-medium">
                {t('models.commonTestPrompts')}
              </Typography>
              <div className="flex flex-wrap gap-2 mb-3">
                <Chip
                  label={t('models.introducePrompt')}
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt(t('models.introducePrompt'))}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
                <Chip
                  label={t('models.aiConceptsPrompt')}
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt(t('models.aiConceptsPrompt'))}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
                <Chip
                  label={t('models.helloWorldPrompt')}
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt(t('models.helloWorldPrompt'))}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
              </div>
            </div>

            <TextField
              fullWidth
              multiline
              rows={4}
              label={t('models.testPrompt')}
              value={testPrompt}
              onChange={e => setTestPrompt(e.target.value)}
              placeholder=""
              disabled={isTesting}
              helperText={
                testPrompt.length > 1000 ? t('models.promptLimit', { length: testPrompt.length }) : t('models.promptLength', { length: testPrompt.length })
              }
              error={testPrompt.length > 1000}
            />

            <div className="flex space-x-3">
              <Button
                variant="contained"
                startIcon={isTesting ? <Loader2 className="animate-spin" /> : <Play />}
                onClick={handleTestModel}
                disabled={isTesting || !testPrompt.trim()}
                className={`px-6 py-2 rounded-lg font-semibold transform transition-all duration-300 shadow-lg ${
                  isTesting
                    ? 'bg-gray-600 text-white cursor-not-allowed'
                    : !testPrompt.trim()
                      ? 'bg-gray-400 text-white cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white hover:scale-105 hover:shadow-xl'
                }`}
              >
                {isTesting ? t('models.testing') : t('models.startTest')}
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setTestPrompt('')
                  setTestResult('')
                }}
                disabled={isTesting}
                className={`${isTesting ? 'opacity-50 cursor-not-allowed text-gray-400 border-gray-300' : 'text-gray-600 hover:text-gray-700 hover:bg-gray-100 border-gray-300 hover:border-gray-400'} px-4 py-2 rounded-lg transition-all duration-200`}
              >
                {t('models.reset')}
              </Button>
            </div>

            {testResult && (
              <div>
                <Typography variant="h6" className="mb-2 text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800 font-bold">
                  {t('models.testResult')}
                </Typography>
                <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-blue-200 p-4">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-white p-3 rounded-lg border border-gray-200">{testResult}</pre>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
        <DialogActions className="bg-gray-50 px-6 py-4">
          <Button
            onClick={() => {
              setShowTestDialog(false)
              setTestPrompt('')
              setTestResult('')
            }}
            className="text-gray-600 hover:text-gray-700 hover:bg-gray-100 px-4 py-2 rounded-lg transition-all duration-200"
          >
            {t('models.close')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={cancelDeleteModel}
        onConfirm={
          deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0
            ? cancelDeleteModel // 如果有知识库使用，点击确认只是关闭对话框
            : confirmDeleteModel // 否则执行删除
        }
        itemType="model"
        itemName={deleteDialog.modelName}
        isLoading={deleteModelMutation.isLoading || deleteEmbeddingModelMutation.isLoading}
        iconType={deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0 ? 'warning' : 'danger'}
        title={deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0 ? t('models.messages.cannotDeleteModel') : undefined}
        message={
          deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0 ? (
            <div className="space-y-3 text-base text-left">
              <p className="text-gray-600">{t('models.messages.modelInUseByKnowledgeBases')}</p>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 max-h-60 overflow-y-auto">
                <ul className="list-disc list-inside space-y-1">
                  {deleteDialog.knowledgeBases.map((kbName: string, index: number) => (
                    <li key={index} className="text-gray-800 font-medium">
                      {kbName}
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-gray-600">{t('models.messages.modelInUseHint')}</p>
            </div>
          ) : undefined
        }
        confirmButtonText={deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0 ? t('models.messages.iKnow') : undefined}
        cancelButtonText={deleteDialog.knowledgeBases && deleteDialog.knowledgeBases.length > 0 ? undefined : t('common.cancel')}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnackbar({ ...snackbar, open: false })} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  )
}

export default ModelsPage
