import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { X, Loader2 } from 'lucide-react'
import { useQueryClient } from 'react-query'
import { KnowledgeBase, CreateKnowledgeBaseRequest } from '@/types/knowledgeBase'
import { useKnowledgeBaseStore } from '@/stores/useKnowledgeBaseStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import { useEmbeddingModels, useTestEmbeddingModel, useToggleEmbeddingModelStatus } from '@test-agentstudio/api-client'
import { KnowledgeBaseService } from '@test-agentstudio/api-client'
import { validateKnowledgeBaseName } from '../utils/validation'

// 自定义输入组件 - 移到主组件外部以避免重新创建导致失焦
const CustomInput = ({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  required = false,
  ...props
}: {
  label: string
  type?: string
  value: string | number
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  required?: boolean
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'required'>) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      {...props}
    />
  </div>
)

const CustomTextarea = ({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
  ...props
}: {
  label: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  rows?: number
} & React.TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
    <textarea
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows={rows}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      {...props}
    />
  </div>
)

const CustomSelect = ({
  label,
  value,
  onChange,
  options,
  ...props
}: {
  label: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  options: { value: string; label: string }[]
} & React.SelectHTMLAttributes<HTMLSelectElement>) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
    <select
      value={value}
      onChange={onChange}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      {...props}
    >
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
)

interface KnowledgeBaseFormDialogProps {
  open: boolean
  knowledgeBase: KnowledgeBase | null
  onClose: () => void
  onSuccess: () => void
  onCreateAndContinue?: (knowledgeBaseId: string) => void
}

const KnowledgeBaseFormDialog: React.FC<KnowledgeBaseFormDialogProps> = ({ open, knowledgeBase, onClose, onSuccess, onCreateAndContinue }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<{ name?: string; embedding_model_config_id?: string }>({})
  const [isRefreshingModels, setIsRefreshingModels] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'document',
    embedding_model_config_id: 0, // Embedding 模型配置ID
  })

  const { createKnowledgeBase, updateKnowledgeBase, total } = useKnowledgeBaseStore()
  const [existingNames, setExistingNames] = useState<string[]>([])
  const MAX_KNOWLEDGE_BASES = 100
  const isAtLimit = !knowledgeBase && total >= MAX_KNOWLEDGE_BASES

  const queryClient = useQueryClient()

  // 获取 Embedding 模型列表
  const { data: embeddingModelsResponse, isLoading: isLoadingEmbeddingModels, refetch: refetchEmbeddingModels } = useEmbeddingModels({
    spaceId: user?.spaceId,
    page: 1,
    size: 100,
    is_active: true, // 只获取激活的模型
  })

  const embeddingModels = embeddingModelsResponse?.items || []

  // 测试和禁用 embedding 模型的 hooks
  const testEmbeddingModelMutation = useTestEmbeddingModel()
  const toggleEmbeddingModelStatusMutation = useToggleEmbeddingModelStatus()

  // 当对话框打开时，强制刷新 Embedding 模型列表，确保获取最新数据
  useEffect(() => {
    if (open && user?.spaceId && !knowledgeBase) {
      // 创建知识库时，强制刷新模型列表
      setIsRefreshingModels(true)
      
      // 先 invalidate queries，然后 refetch
      queryClient.invalidateQueries(['embeddingModels', 'list'])
      
      refetchEmbeddingModels()
        .then(() => {
          setIsRefreshingModels(false)
        })
        .catch(() => {
          setIsRefreshingModels(false)
        })
    } else {
      setIsRefreshingModels(false)
    }
  }, [open, user?.spaceId, knowledgeBase, queryClient, refetchEmbeddingModels])

  // 获取所有知识库名称用于重复检查
  useEffect(() => {
    if (open && user?.spaceId) {
      const fetchAllKnowledgeBaseNames = async () => {
        try {
          const allNames: string[] = []
          let page = 1
          const pageSize = 100
          let hasMore = true

          while (hasMore) {
            const response = await KnowledgeBaseService.getKnowledgeBases({
              space_id: user.spaceId,
              page: page,
              size: pageSize,
            })
            if (response.code === 200 && response.data?.items) {
              const names = response.data.items.map((item: any) => item.name).filter((name: string) => name && (!knowledgeBase || name !== knowledgeBase.name)) // 更新模式时排除当前知识库
              allNames.push(...names)

              // 检查是否还有更多数据
              const total = response.data.total || 0
              const fetched = page * pageSize
              hasMore = fetched < total
              page++
            } else {
              hasMore = false
            }
          }

          setExistingNames(allNames)
        } catch (error) {
          console.error('Failed to fetch knowledge base names:', error)
        }
      }
      fetchAllKnowledgeBaseNames()
    }
  }, [open, user?.spaceId, knowledgeBase])

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value
    setFormData(prev => ({ ...prev, name: newName }))

    let nameError: string | null = null

    // 先检查基本验证（特殊字符、长度等）
    nameError = validateKnowledgeBaseName(newName, t, 'knowledgeBases.form.nameRequired')

    // 如果基本验证通过，检查重复名称
    if (!nameError && newName.trim()) {
      const isDuplicate = existingNames.some(existingName => existingName === newName)
      if (isDuplicate) {
        nameError = t('knowledgeBases.form.nameExists')
      }
    }

    setErrors(prev => ({
      ...prev,
      name: nameError || undefined,
    }))
  }

  useEffect(() => {
    if (knowledgeBase) {
      setFormData({
        name: knowledgeBase.name || '',
        description: knowledgeBase.description || '',
        type: knowledgeBase.type || 'document',
        embedding_model_config_id: (knowledgeBase as any).embedding_model_config_id || 0,
      })
    } else {
      // 创建模式：重置表单，不自动选择 embedding 模型，让用户手动选择
      setFormData({
        name: '',
        description: '',
        type: 'document',
        embedding_model_config_id: 0, // 初始值为 0，用户必须手动选择
      })
    }
    setErrors({}) // 清除错误
  }, [knowledgeBase, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const newErrors: { name?: string; embedding_model_config_id?: string } = {}

    const nameError = validateKnowledgeBaseName(formData.name, t, 'knowledgeBases.form.nameRequired')
    if (nameError) {
      newErrors.name = nameError
    } else if (formData.name.trim()) {
      // 如果基本验证通过，检查重复名称
      const isDuplicate = existingNames.some(existingName => existingName === formData.name)
      if (isDuplicate) {
        newErrors.name = t('knowledgeBases.form.nameExists')
      }
    }

    // 检查是否有可用的 embedding 模型（仅在创建时检查）
    if (!knowledgeBase) {
      // 首先检查是否有可用的模型列表
      if (embeddingModels.length === 0) {
        newErrors.embedding_model_config_id = t('knowledgeBases.form.noModelsError')
      } else {
        // 检查是否选择了模型
        if (!formData.embedding_model_config_id || formData.embedding_model_config_id === 0) {
          newErrors.embedding_model_config_id = t('knowledgeBases.form.selectModelError')
        } else {
          // 检查选中的 embedding 模型是否在可用列表中
          const selectedModel = embeddingModels.find(
            model => parseInt(model.id) === formData.embedding_model_config_id
          )
          if (!selectedModel) {
            newErrors.embedding_model_config_id = t('knowledgeBases.form.modelUnavailable')
          }
        }
      }
    }

    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) {
      return
    }

    setIsLoading(true)

    try {
      if (knowledgeBase) {
        // 更新知识库
        const updateData = {
          space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
          kb_id: knowledgeBase.id,
          name: formData.name,
          desc: formData.description || '',
        }
        await updateKnowledgeBase(updateData)
      } else {
        // 创建知识库前，先测试 embedding 模型是否可用
        const selectedModelId = formData.embedding_model_config_id.toString()
        try {
          // 测试 embedding 模型
          await testEmbeddingModelMutation.mutateAsync({
            id: selectedModelId,
            testRequest: { text: t('knowledgeBases.form.testText') },
          })
        } catch (testError: any) {
          // 测试失败，提取错误信息并阻止创建，但不自动禁用模型
          console.error('Embedding 模型测试失败:', testError)
          // 提取错误信息
          // embeddingModelService.handleError 返回的是 error.response.data，所以 error 对象本身就是响应体
          // 同时也要兼容原始的 axios error 格式
          const errorMessage = testError?.detail || 
                              testError?.message || 
                              testError?.error ||
                              testError?.response?.data?.detail || 
                              testError?.response?.data?.message || 
                              testError?.response?.data?.error ||
                              t('knowledgeBases.form.testFailed')
          
          // 设置错误信息并阻止创建
          setErrors({
            embedding_model_config_id: errorMessage,
          })
          setIsLoading(false)
          return
        }

        // 测试通过，继续创建知识库 - 使用V2 API
        const createData: CreateKnowledgeBaseRequest = {
          space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
          name: formData.name,
          description: formData.description || undefined,
          embedding_model_config_id: formData.embedding_model_config_id,
          config: {
            type: formData.type,
          },
        }
        await createKnowledgeBase(createData)
      }

      onSuccess()
    } catch (error: any) {
      console.error('Failed to save knowledge base:', error)
      const errorMessage = error?.message || t('knowledgeBases.form.saveFailed')
      if (errorMessage.includes('已存在')) {
        setErrors(prev => ({ ...prev, name: errorMessage }))
      } else if (errorMessage.includes('已达到上限')) {
        // 达到上限时只显示弹窗，不在名称输入框下方显示错误
      }
    } finally {
      setIsLoading(false)
    }
  }

  // 组件逻辑继续...

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={onClose}></div>

        <div className="relative bg-white rounded-lg max-w-2xl w-full">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900">{knowledgeBase ? t('knowledgeBases.settings.title') : t('knowledgeBases.create.title')}</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6">
            <p className="text-gray-600 mb-6">{knowledgeBase ? t('knowledgeBases.edit.description') : t('knowledgeBases.create.description')}</p>

            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                {/* 基本信息 */}
                <div>
                  <CustomInput
                    label={t('knowledgeBases.form.name')}
                    value={formData.name}
                    onChange={handleNameChange}
                    placeholder={t('knowledgeBases.form.namePlaceholder')}
                    maxLength={100}
                    required
                  />
                  <div className="flex items-center justify-between mt-1">
                    {errors.name && <p className="text-red-500 text-sm">{errors.name}</p>}
                    <p className={`text-xs ml-auto ${formData.name.length >= 100 ? 'text-red-500' : 'text-gray-500'}`}>{formData.name.length}/100</p>
                  </div>
                </div>

                <div>
                  <CustomTextarea
                    label={t('knowledgeBases.form.description')}
                    value={formData.description}
                    onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={t('knowledgeBases.form.descriptionPlaceholder')}
                    rows={3}
                    maxLength={2000}
                  />
                  <div className="flex justify-end mt-1">
                    <p className={`text-xs ${(formData.description?.length || 0) >= 2000 ? 'text-red-500' : 'text-gray-500'}`}>
                      {formData.description?.length || 0}/2000
                    </p>
                  </div>
                </div>

                {/* Embedding 模型选择器 - 仅在创建时显示 */}
                {!knowledgeBase && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {t('knowledgeBases.form.embeddingModelRequired')} <span className="text-red-500">*</span>
                    </label>
                    {(isLoadingEmbeddingModels || isRefreshingModels) ? (
                      <div className="text-sm text-gray-500 flex items-center">
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {t('knowledgeBases.form.loadingModels')}
                      </div>
                    ) : embeddingModels.length === 0 ? (
                      <div className="text-sm text-red-500">
                        {t('knowledgeBases.form.noModels')}{' '}
                        <Link
                          to="/dashboard/models"
                          className="text-blue-600 hover:text-blue-800 underline"
                        >
                          {t('knowledgeBases.form.createModelLink')}
                        </Link>
                      </div>
                    ) : (
                      <select
                        value={formData.embedding_model_config_id || ''}
                        onChange={e => {
                          const selectedValue = e.target.value
                          if (selectedValue === '') {
                            setFormData(prev => ({ ...prev, embedding_model_config_id: 0 }))
                          } else {
                            const selectedId = parseInt(selectedValue)
                            setFormData(prev => ({ ...prev, embedding_model_config_id: selectedId }))
                            // 清除错误（如果用户选择了有效的模型）
                            if (embeddingModels.find(model => parseInt(model.id) === selectedId)) {
                              setErrors(prev => ({ ...prev, embedding_model_config_id: undefined }))
                            }
                          }
                        }}
                        className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          !formData.embedding_model_config_id ? 'text-gray-400' : ''
                        }`}
                        style={!formData.embedding_model_config_id ? { color: '#9ca3af' } : {}}
                      >
                        <option value="" disabled hidden style={{ color: '#9ca3af' }}>{t('knowledgeBases.form.selectModel')}</option>
                        {embeddingModels.map(model => (
                          <option key={model.id} value={parseInt(model.id)} style={{ color: '#111827' }}>
                            {model.name} ({model.modelId})
                          </option>
                        ))}
                      </select>
                    )}
                    {errors.embedding_model_config_id && <p className="text-red-500 text-sm mt-1">{errors.embedding_model_config_id}</p>}
                  </div>
                )}

                <CustomSelect
                  label={t('knowledgeBases.form.type')}
                  value={formData.type}
                  onChange={e => setFormData(prev => ({ ...prev, type: e.target.value as any }))}
                  options={[{ value: 'document', label: t('knowledgeBases.types.document') }]}
                />
              </div>

              {/* 对话框底部按钮 */}
              <div className="mt-6 pt-6 border-t">
                {isAtLimit && (
                  <p className="text-sm text-red-500 mb-3">{t('knowledgeBases.form.limitReached')}</p>
                )}
                <div className="flex items-center justify-end space-x-2">
                  <button type="button" onClick={onClose} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
                    {t('common.cancel')}
                  </button>

                  <button
                    type="submit"
                    disabled={
                      isLoading ||
                      !!errors.name ||
                      !!errors.embedding_model_config_id ||
                      isAtLimit ||
                      (!knowledgeBase && embeddingModels.length === 0)
                    }
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t('common.saving') : knowledgeBase ? t('common.buttons.update') : t('common.buttons.create')}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeBaseFormDialog

