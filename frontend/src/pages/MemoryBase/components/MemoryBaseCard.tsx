import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Edit, Trash2, Brain, Tag, Check, X, Cpu, ChevronDown, ChevronUp } from 'lucide-react'
import { MemoryBase } from '@/types/memoryBase'
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore'
import { useAuthStore } from '@/stores/useAuthStore'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { useEmbeddingModel, useModels, MemoryBaseService } from '@test-agentstudio/api-client'
import { validateMemoryBaseName } from '../utils/validation'

interface ModelDetail {
  model_id: number
  model_name: string
  model_type: string
  model_provider: string
  max_tokens: number
  temperature: number
  top_p: number
  timeout: number
  retry_count: number
  enable_streaming: boolean
  enable_function_calling: boolean
  is_active: boolean
  api_key: string
  api_base: string
  streaming: boolean
}

interface MemoryBaseCardProps {
  memoryBase: MemoryBase
  viewMode: 'grid' | 'list'
  onEdit: () => void
  onDelete: () => void
  onClick: () => void
}

const MemoryBaseCard: React.FC<MemoryBaseCardProps> = ({ memoryBase, viewMode, onEdit, onDelete, onClick }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { updateMemoryBase, isLoading } = useMemoryBaseStore()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()

  // 获取 Embedding 模型信息
  const { data: embeddingModel } = useEmbeddingModel(
    memoryBase.embedding_model_config_id?.toString() || '', 
    memoryBase.space_id || user?.spaceId || ''
  )

  // 获取 LLM 模型列表
  const { data: modelsData } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })

  const [modelsList, setModelsList] = useState<ModelDetail[]>([])
  
  // 转换LLM模型数据格式
  useEffect(() => {
    if (modelsData?.items) {
      const convertedModels: ModelDetail[] = modelsData.items.map(model => ({
        model_id: parseInt(model.id),
        model_name: model.name || '',
        model_type: model.modelId || '',
        model_provider: model.provider || '',
        max_tokens: model.maxTokens || 0,
        temperature: model.temperature || 0,
        top_p: model.topp || 0,
        timeout: model.timeout || 0,
        retry_count: model.retryCount || 0,
        enable_streaming: model.enableStreaming || false,
        enable_function_calling: model.enableFunctionCalling || false,
        is_active: model.isActive || false,
        api_key: model.apiKey || '',
        api_base: model.baseUrl || '',
        streaming: model.enableStreaming || false,
      }))

      setModelsList(convertedModels)
    }
  }, [modelsData])

  // 获取当前记忆库的LLM模型信息
  const llmModel = modelsList.find(model => model.model_id === memoryBase.llm_model_config_id)

  // 编辑状态相关
  const [editingField, setEditingField] = useState<'name' | 'description' | null>(null)
  const [editingName, setEditingName] = useState<string>('')
  const [editingDescription, setEditingDescription] = useState<string>('')
  const [nameError, setNameError] = useState<string>('')
  const [existingNames, setExistingNames] = useState<string[]>([])

  // LLM模型选择状态
  const [showLlmDropdown, setShowLlmDropdown] = useState<boolean>(false)
  const [selectedLlmModelId, setSelectedLlmModelId] = useState<number>(memoryBase.llm_model_config_id || 0)
  const [isUpdatingLlmModel, setIsUpdatingLlmModel] = useState<boolean>(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowLlmDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // 当 memoryBase prop 更新时，如果不在编辑状态，同步更新编辑状态的值
  useEffect(() => {
    if (!editingField) {
      setEditingName(memoryBase.name)
      setEditingDescription(memoryBase.description || '')
      setSelectedLlmModelId(memoryBase.llm_model_config_id || 0)
    }
  }, [memoryBase, editingField])

  // 获取所有记忆库名称用于重复检查
  useEffect(() => {
    if (editingField === 'name' && user?.spaceId) {
      const fetchAllMemoryBaseNames = async () => {
        try {
          const allNames: string[] = []
          let page = 1
          const pageSize = 100
          let hasMore = true

          while (hasMore) {
            const response = await MemoryBaseService.getMemoryBases({
              space_id: user.spaceId,
              page: page,
              page_size: pageSize,
            })
            if (response.code === 200 && response.data?.items) {
              const names = response.data.items.map((item: any) => item.name).filter((name: string) => name && name !== memoryBase.name) // 排除当前记忆库
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
          console.error('Failed to fetch memory base names:', error)
        }
      }
      fetchAllMemoryBaseNames()
    }
  }, [editingField, user?.spaceId, memoryBase.name])

  // 处理点击进入编辑状态
  const handleStartEditing = (field: 'name' | 'description', e: React.MouseEvent) => {
    e.stopPropagation() // 阻止事件冒泡
    setEditingField(field)
    setEditingName(memoryBase.name)
    setEditingDescription(memoryBase.description || '')
    setNameError('')

    // 短暂延迟后聚焦到输入框
    setTimeout(() => {
      const inputElement = document.getElementById(`edit-input-${memoryBase.mdb_id}-${field}`)
      if (inputElement) {
        inputElement.focus()
        // 全选输入框内容
        if (inputElement instanceof HTMLInputElement || inputElement instanceof HTMLTextAreaElement) {
          inputElement.select()
        }
      }
    }, 100)
  }

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value
    setEditingName(newName)

    let error: string | null = null

    // 先检查基本验证（特殊字符、长度等）
    error = validateMemoryBaseName(newName, t, 'memoryBases.edit.nameRequired')

    // 如果基本验证通过，检查重复名称
    if (!error && newName.trim()) {
      const isDuplicate = existingNames.some(existingName => existingName === newName)
      if (isDuplicate) {
        error = t('memoryBases.form.nameExists')
      }
    }

    setNameError(error || '')
  }

  const handleSaveEditing = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!editingField || !user?.spaceId) return

    if (editingField === 'name') {
      const nameError = validateMemoryBaseName(editingName, t, 'memoryBases.edit.nameRequired')
      if (nameError) {
        setNameError(nameError)
        return
      }
      // 检查重复名称
      if (editingName.trim()) {
        const isDuplicate = existingNames.some(existingName => existingName === editingName)
        if (isDuplicate) {
          setNameError(t('memoryBases.form.nameExists'))
          return
        }
      }
    }

    try {
      await updateMemoryBase({
        mdb_id: memoryBase.mdb_id,
        space_id: user.spaceId,
        name: editingName.trim(), // 去除首尾空格
        description: editingDescription.trim(),
      })
      showSuccess(t('memoryBases.update.success'))
      setEditingField(null)
      setNameError('')
    } catch (error: any) {
      const errorMessage = error?.message || t('memoryBases.update.error')
      if (errorMessage.includes('已存在')) {
        setNameError(errorMessage)
      } else {
        showError(errorMessage)
      }
    }
  }

  const handleCancelEditing = (e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingField(null)
    setNameError('')
  }

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      // 按下Enter键保存编辑，不触发默认行为（表单提交）
      e.preventDefault()
      handleSaveEditing(e as any)
    } else if (e.key === 'Escape') {
      // 按下Escape键取消编辑
      handleCancelEditing(e as any)
    }
  }

  // 处理LLM模型选择
  const handleLlmModelChange = (modelId: number) => {
    setSelectedLlmModelId(modelId)
  }

  // 保存LLM模型更改
  const handleSaveLlmModel = async () => {
    if (!user?.spaceId || selectedLlmModelId === memoryBase.llm_model_config_id) return
    
    setIsUpdatingLlmModel(true)
    try {
      await updateMemoryBase({
        name: memoryBase.name,
        description: memoryBase.description ,
        mdb_id: memoryBase.mdb_id,
        space_id: user.spaceId,
        llm_model_config_id: selectedLlmModelId,
      })
      showSuccess(t('memoryBases.update.success'))
    } catch (error: any) {
      showError(error?.message || t('memoryBases.update.error'))
      // 恢复之前的模型ID
      setSelectedLlmModelId(memoryBase.llm_model_config_id || 0)
    } finally {
      setIsUpdatingLlmModel(false)
    }
  }

  const handleActionClick = (e: React.MouseEvent, action: () => void) => {
    e.stopPropagation()
    action()
  }

  // 列表视图
  if (viewMode === 'list') {
    return (
      <>
        <div className="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer" onClick={onClick}>
          <div className="p-4 pb-3">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3 flex-1">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  {/* 名称编辑 */}
                  {editingField === 'name' ? (
                    <div className="mb-1">
                      <div className="relative">
                        <input
                          id={`edit-input-${memoryBase.mdb_id}-name`}
                          type="text"
                          value={editingName}
                          onChange={handleNameChange}
                          onKeyDown={handleKeyDown}
                          className={`w-full px-3 py-1 border-2 rounded-lg focus:outline-none focus:ring-1 pr-24 ${
                            nameError ? 'border-red-500 focus:ring-red-500' : 'border-purple-500 focus:ring-purple-500'
                          }`}
                          placeholder={t('memoryBases.edit.namePlaceholder')}
                          maxLength={100}
                        />
                        <div className="absolute right-1 top-1/2 transform -translate-y-1/2 flex items-center space-x-1">
                          <span className={`text-xs mr-1 ${editingName.length >= 100 ? 'text-red-500' : 'text-gray-500'}`}>{editingName.length}/100</span>
                          <button
                            onClick={handleSaveEditing}
                            disabled={isLoading || !!nameError}
                            className={`p-1 rounded ${nameError ? 'text-gray-400 cursor-not-allowed' : 'text-green-600 hover:bg-green-100'}`}
                            title={t('common.tooltips.save')}
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button onClick={handleCancelEditing} className="p-1 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      {nameError && <p className="text-red-500 text-xs mt-1">{nameError}</p>}
                    </div>
                  ) : (
                    <h3
                      className="text-lg font-medium text-gray-900 truncate cursor-pointer hover:text-purple-600 transition-colors duration-200"
                      onClick={e => handleStartEditing('name', e)}
                    >
                      {memoryBase.name}
                    </h3>
                  )}
                  
                  {/* 描述编辑 */}
                  {editingField === 'description' ? (
                    <div className="mt-2">
                      <div className="relative">
                        <textarea
                          id={`edit-input-${memoryBase.mdb_id}-description`}
                          value={editingDescription}
                          onChange={(e) => setEditingDescription(e.target.value)}
                          onKeyDown={handleKeyDown}
                          className="w-full px-3 py-1 border-2 border-purple-500 rounded-lg focus:outline-none focus:ring-1 focus:ring-purple-500"
                          placeholder={t('memoryBases.edit.descriptionPlaceholder')}
                          rows={2}
                        />
                        <div className="absolute right-1 bottom-1 flex items-center space-x-1">
                          <button
                            onClick={handleSaveEditing}
                            disabled={isLoading}
                            className="p-1 text-green-600 hover:bg-green-100 rounded"
                            title={t('common.tooltips.save')}
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button onClick={handleCancelEditing} className="p-1 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p
                      className="text-gray-500 mt-1 line-clamp-2 cursor-pointer hover:text-purple-600 transition-colors duration-200"
                      onClick={e => handleStartEditing('description', e)}
                    >
                      {memoryBase.description || t('memoryBases.card.noDescription')}
                    </p>
                  )}
                  
                  {/* 模型信息 */}
                  <div className="flex flex-wrap gap-2 mt-2">
                    <div className="flex items-center text-xs bg-gray-100 px-2 py-1 rounded">
                      <Cpu className="w-3 h-3 mr-1 text-purple-600" />
                      <span className="text-gray-700">
                        {embeddingModel?.name || t('memoryBases.card.unknownEmbeddingModel')}
                      </span>
                    </div>
                    
                    {/* LLM模型选择下拉框 */}
                    <div className="relative" ref={dropdownRef}>
                      <div 
                        className="flex items-center text-xs bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation()
                          setShowLlmDropdown(!showLlmDropdown)
                        }}
                      >
                        <Tag className="w-3 h-3 mr-1 text-blue-600" />
                        <span className="text-gray-700">
                          {modelsList.find(m => m.model_id === selectedLlmModelId)?.model_name || 
                           t('memoryBases.card.unknownLlmModel')}
                        </span>
                        {showLlmDropdown ? 
                          <ChevronUp className="w-3 h-3 ml-1 text-gray-500" /> : 
                          <ChevronDown className="w-3 h-3 ml-1 text-gray-500" />
                        }
                      </div>
                      
                      {showLlmDropdown && (
                        <div className="absolute left-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                          <div className="p-2">
                            <p className="text-xs text-gray-500 mb-2">选择新的LLM模型</p>
                            {modelsList.filter(model => model.is_active).map(model => (
                              <div
                                key={model.model_id}
                                className={`p-2 rounded cursor-pointer hover:bg-gray-100 flex justify-between items-center ${
                                  selectedLlmModelId === model.model_id ? 'bg-blue-100' : ''
                                }`}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleLlmModelChange(model.model_id)
                                }}
                              >
                                <div>
                                  <div className="text-sm font-medium">{model.model_name}</div>
                                  <div className="text-xs text-gray-500">{model.model_provider}</div>
                                </div>
                                {selectedLlmModelId === model.model_id && (
                                  <Check className="w-4 h-4 text-blue-600" />
                                )}
                              </div>
                            ))}
                            {modelsList.filter(model => model.is_active).length === 0 && (
                              <div className="p-2 text-sm text-gray-500">没有可用的模型</div>
                            )}
                          </div>
                          <div className="p-2 border-t border-gray-200 flex justify-end space-x-2">
                            <button
                              className="px-2 py-1 text-xs bg-gray-200 rounded hover:bg-gray-300"
                              onClick={(e) => {
                                e.stopPropagation()
                                setShowLlmDropdown(false)
                                setSelectedLlmModelId(memoryBase.llm_model_config_id || 0)
                              }}
                            >
                              取消
                            </button>
                            <button
                              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSaveLlmModel()
                                setShowLlmDropdown(false)
                              }}
                              disabled={isUpdatingLlmModel || selectedLlmModelId === memoryBase.llm_model_config_id}
                            >
                              {isUpdatingLlmModel ? '保存中...' : '保存'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center text-xs bg-gray-100 px-2 py-1 rounded">
                    </div>
                  </div>
                </div>
              </div>
              
              {/* 操作按钮 */}
              <div className="flex space-x-1 flex-shrink-0">
                <button
                  onClick={(e) => handleActionClick(e, onEdit)}
                  className="p-2 text-gray-500 hover:text-purple-600 hover:bg-gray-100 rounded-lg"
                  title={t('common.buttons.edit')}
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={(e) => handleActionClick(e, onDelete)}
                  className="p-2 text-gray-500 hover:text-red-600 hover:bg-gray-100 rounded-lg"
                  title={t('common.buttons.delete')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            
            {/* 状态和时间信息 */}
            <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
              <div>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  memoryBase.status === 'active' 
                    ? 'bg-green-100 text-green-800' 
                    : memoryBase.status === 'processing'
                    ? 'bg-yellow-100 text-yellow-800'
                    : memoryBase.status === 'error'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {t(`memoryBases.status.active`)}
                </span>
              </div>
              <div>
                {new Date(memoryBase.updated_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
        
        <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
      </>
    )
  }

  // 网格视图
  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer flex flex-col h-full" onClick={onClick}>
        <div className="p-4 flex-1">
          <div className="flex justify-between items-start mb-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div className="flex space-x-1">
              <button
                onClick={(e) => handleActionClick(e, onEdit)}
                className="p-1 text-gray-500 hover:text-purple-600 hover:bg-gray-100 rounded"
                title={t('common.buttons.edit')}
              >
                <Edit className="w-3 h-3" />
              </button>
              <button
                onClick={(e) => handleActionClick(e, onDelete)}
                className="p-1 text-gray-500 hover:text-red-600 hover:bg-gray-100 rounded"
                title={t('common.buttons.delete')}
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
          
          {/* 名称编辑 */}
          {editingField === 'name' ? (
            <div className="mb-2">
              <div className="relative">
                <input
                  id={`edit-input-${memoryBase.mdb_id}-name`}
                  type="text"
                  value={editingName}
                  onChange={handleNameChange}
                  onKeyDown={handleKeyDown}
                  className={`w-full px-2 py-1 text-sm border-2 rounded-lg focus:outline-none focus:ring-1 pr-16 ${
                    nameError ? 'border-red-500 focus:ring-red-500' : 'border-purple-500 focus:ring-purple-500'
                  }`}
                  placeholder={t('memoryBases.edit.namePlaceholder')}
                  maxLength={100}
                />
                <div className="absolute right-1 top-1/2 transform -translate-y-1/2 flex items-center space-x-1">
                  <button
                    onClick={handleSaveEditing}
                    disabled={isLoading || !!nameError}
                    className={`p-0.5 rounded ${nameError ? 'text-gray-400 cursor-not-allowed' : 'text-green-600 hover:bg-green-100'}`}
                    title={t('common.tooltips.save')}
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button onClick={handleCancelEditing} className="p-0.5 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>
              {nameError && <p className="text-red-500 text-xs mt-1">{nameError}</p>}
            </div>
          ) : (
            <h3
              className="font-medium text-gray-900 truncate cursor-pointer hover:text-purple-600 transition-colors duration-200"
              onClick={e => handleStartEditing('name', e)}
            >
              {memoryBase.name}
            </h3>
          )}
          
          {/* 描述编辑 */}
          {editingField === 'description' ? (
            <div className="mt-2 mb-3">
              <div className="relative">
                <textarea
                  id={`edit-input-${memoryBase.mdb_id}-description`}
                  value={editingDescription}
                  onChange={(e) => setEditingDescription(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full px-2 py-1 text-sm border-2 border-purple-500 rounded-lg focus:outline-none focus:ring-1 focus:ring-purple-500"
                  placeholder={t('memoryBases.edit.descriptionPlaceholder')}
                  rows={2}
                />
                <div className="absolute right-1 bottom-1 flex items-center space-x-1">
                  <button
                    onClick={handleSaveEditing}
                    disabled={isLoading}
                    className="p-0.5 text-green-600 hover:bg-green-100 rounded"
                    title={t('common.tooltips.save')}
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button onClick={handleCancelEditing} className="p-0.5 text-gray-600 hover:bg-gray-100 rounded" title={t('common.tooltips.cancel')}>
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <p
              className="text-gray-500 text-sm mt-1 line-clamp-2 cursor-pointer hover:text-purple-600 transition-colors duration-200"
              onClick={e => handleStartEditing('description', e)}
            >
              {memoryBase.description || t('memoryBases.card.noDescription')}
            </p>
          )}
          
          {/* 模型和状态信息 */}
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap gap-1">
              <div className="flex items-center text-xs bg-gray-100 px-2 py-0.5 rounded">
                <Cpu className="w-2.5 h-2.5 mr-1 text-purple-600" />
                <span className="text-gray-700 truncate max-w-[100px]">
                  {embeddingModel?.name || t('memoryBases.card.unknownEmbeddingModel')}
                </span>
              </div>
              
              {/* LLM模型选择下拉框 */}
              <div className="relative" ref={dropdownRef}>
                <div 
                  className="flex items-center text-xs bg-gray-100 px-2 py-0.5 rounded cursor-pointer hover:bg-gray-200 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowLlmDropdown(!showLlmDropdown)
                  }}
                >
                  <Tag className="w-2.5 h-2.5 mr-1 text-blue-600" />
                  <span className="text-gray-700 truncate max-w-[100px]">
                    {modelsList.find(m => m.model_id === selectedLlmModelId)?.model_name || 
                     t('memoryBases.card.unknownLlmModel')}
                  </span>
                  {showLlmDropdown ? 
                    <ChevronUp className="w-2.5 h-2.5 ml-1 text-gray-500" /> : 
                    <ChevronDown className="w-2.5 h-2.5 ml-1 text-gray-500" />
                  }
                </div>
                
                {showLlmDropdown && (
                  <div className="absolute left-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-60 overflow-y-auto">
                    <div className="p-2">
                      <p className="text-xs text-gray-500 mb-2">选择新的LLM模型</p>
                      {modelsList.filter(model => model.is_active).map(model => (
                        <div
                          key={model.model_id}
                          className={`p-2 rounded cursor-pointer hover:bg-gray-100 flex justify-between items-center ${
                            selectedLlmModelId === model.model_id ? 'bg-blue-100' : ''
                          }`}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleLlmModelChange(model.model_id)
                          }}
                        >
                          <div>
                            <div className="text-sm font-medium">{model.model_name}</div>
                            <div className="text-xs text-gray-500">{model.model_provider}</div>
                          </div>
                          {selectedLlmModelId === model.model_id && (
                            <Check className="w-4 h-4 text-blue-600" />
                          )}
                        </div>
                      ))}
                      {modelsList.filter(model => model.is_active).length === 0 && (
                        <div className="p-2 text-sm text-gray-500">没有可用的模型</div>
                      )}
                    </div>
                    <div className="p-2 border-t border-gray-200 flex justify-end space-x-2">
                      <button
                        className="px-2 py-1 text-xs bg-gray-200 rounded hover:bg-gray-300"
                        onClick={(e) => {
                          e.stopPropagation()
                          setShowLlmDropdown(false)
                          setSelectedLlmModelId(memoryBase.llm_model_config_id || 0)
                        }}
                      >
                        取消
                      </button>
                      <button
                        className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSaveLlmModel()
                          setShowLlmDropdown(false)
                        }}
                        disabled={isUpdatingLlmModel || selectedLlmModelId === memoryBase.llm_model_config_id}
                      >
                        {isUpdatingLlmModel ? '保存中...' : '保存'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                memoryBase.status === 'active' 
                  ? 'bg-green-100 text-green-800' 
                  : memoryBase.status === 'processing'
                  ? 'bg-yellow-100 text-yellow-800'
                  : memoryBase.status === 'error'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {t(`memoryBases.status.active`)}
              </span>
            </div>
          </div>
        </div>
        
        {/* 底部信息 */}
        <div className="p-3 border-t border-gray-100 text-xs text-gray-500">
          <div className="flex justify-between">
            <span>{new Date(memoryBase.updated_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
      
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default MemoryBaseCard
