import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ExternalLink, X } from 'lucide-react';
import { MemoryBase, CreateMemoryBaseRequest, UpdateMemoryBaseRequest } from '@/types/memoryBase';
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { ENV_CONFIG } from '@/config/environment';
import { useEmbeddingModels, useTestEmbeddingModel, useToggleEmbeddingModelStatus, useModels, useTestModel, useToggleModelStatus } from '@test-agentstudio/api-client';
import { MemoryBaseService } from '@test-agentstudio/api-client';
import { validateMemoryBaseName } from '../utils/validation';
import { IconButton, Tooltip } from '@mui/material';

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
  label: string;
  type?: string;
  value: string | number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  required?: boolean;
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
);

const CustomTextarea = ({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
  ...props
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  rows?: number;
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
);

const CustomSelect = ({
  label,
  value,
  onChange,
  options,
  ...props
}: {
  label: string;
  value: string | number;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: { value: string | number; label: string }[];
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
);

interface ModelDetail {
  model_id: number;
  model_name: string;
  model_type: string;
  model_provider: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  timeout: number;
  retry_count: number;
  enable_streaming: boolean;
  enable_function_calling: boolean;
  is_active: boolean;
  api_key: string;
  api_base: string;
  streaming: boolean;
}

interface MemoryBaseFormDialogProps {
  open: boolean;
  memoryBase: MemoryBase | null;
  onClose: () => void;
  onSuccess: () => void;
  onCreateAndContinue?: (memoryBaseId: string) => void;
}

const MemoryBaseFormDialog: React.FC<MemoryBaseFormDialogProps> = ({ open, memoryBase, onClose, onSuccess, onCreateAndContinue }) => {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; embedding_model_config_id?: string; llm_model_config_id?: string }>({});

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'memory',
    embedding_model_config_id: 0, // Embedding 模型配置ID
    llm_model_config_id: 0, // LLM 模型ID
  });

  const { createMemoryBase, updateMemoryBase, total } = useMemoryBaseStore();
  const [existingNames, setExistingNames] = useState<string[]>([]);
  const MAX_MEMORY_BASES = 100;
  const isAtLimit = !memoryBase && total >= MAX_MEMORY_BASES;

  // 获取 Embedding 模型列表
  const { data: embeddingModelsResponse, isLoading: isLoadingEmbeddingModels } = useEmbeddingModels({
    spaceId: user?.spaceId,
    page: 1,
    size: 100,
    is_active: true, // 只获取激活的模型
  });

  // 获取 LLM 模型列表
  const { data: modelsData, isLoading: isLoadingLlmModels } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  });

  const [modelsList, setModelsList] = useState<ModelDetail[]>([]);
  const embeddingModels = embeddingModelsResponse?.items || [];

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
      }));

      setModelsList(convertedModels);
    }
  }, [modelsData]);

  // 测试和禁用 embedding 模型的 hooks
  const testEmbeddingModelMutation = useTestEmbeddingModel();
  const toggleEmbeddingModelStatusMutation = useToggleEmbeddingModelStatus();
  const testLLMModelMutation = useTestModel();
  const toggleLLMModelStatusMutation = useToggleModelStatus();
  // 获取所有记忆库名称用于重复检查
  useEffect(() => {
    if (open && user?.spaceId) {
      const fetchAllMemoryBaseNames = async () => {
        try {
          const allNames: string[] = [];
          let page = 1;
          const pageSize = 100;
          let hasMore = true;

          while (hasMore) {
            const response = await MemoryBaseService.getMemoryBases({
              space_id: user.spaceId,
              page: page,
              page_size: pageSize,
            });
            if (response.code === 200 && response.data?.items) {
              const names = response.data.items.map((item: any) => item.name).filter((name: string) => name && (!memoryBase || name !== memoryBase.name)); // 更新模式时排除当前记忆库
              allNames.push(...names);

              // 检查是否还有更多数据
              const total = response.data.total || 0;
              const fetched = page * pageSize;
              hasMore = fetched < total;
              page++;
            } else {
              hasMore = false;
            }
          }

          setExistingNames(allNames);
        } catch (error) {
          console.error('Failed to fetch memory base names:', error);
        }
      };
      fetchAllMemoryBaseNames();
    }
  }, [open, user?.spaceId, memoryBase]);

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value;
    setFormData(prev => ({ ...prev, name: newName }));

    let nameError: string | null = null;

    // 先检查基本验证（特殊字符、长度等）
    nameError = validateMemoryBaseName(newName, t, 'memoryBases.form.nameRequired');

    // 如果基本验证通过，检查重复名称
    if (!nameError && newName.trim()) {
      const isDuplicate = existingNames.some(existingName => existingName === newName);
      if (isDuplicate) {
        nameError = t('memoryBases.form.nameExists');
      }
    }

    setErrors(prev => ({
      ...prev,
      name: nameError || undefined,
    }));
  };

  useEffect(() => {
    if (memoryBase) {
      setFormData({
        name: memoryBase.name || '',
        description: memoryBase.description || '',
        type: 'memory',
        embedding_model_config_id: memoryBase.embedding_model_config_id || 0,
        llm_model_config_id: memoryBase.llm_model_config_id || 0,
      });
    } else {
      // 创建模式：重置表单，不自动选择模型，让用户手动选择
      setFormData({
        name: '',
        description: '',
        type: 'memory',
        embedding_model_config_id: 0,
        llm_model_config_id: 0,
      });
    }
    setErrors({}); // 清除错误
  }, [memoryBase, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: { name?: string; embedding_model_config_id?: string; llm_model_config_id?: string } = {};

    // 验证名称
    const nameError = validateMemoryBaseName(formData.name, t, 'memoryBases.form.nameRequired');
    if (nameError) {
      newErrors.name = nameError;
    } else if (formData.name.trim()) {
      // 如果基本验证通过，检查重复名称
      const isDuplicate = existingNames.some(existingName => existingName === formData.name);
      if (isDuplicate) {
        newErrors.name = t('memoryBases.form.nameExists');
      }
    }

    // 检查是否有可用的 embedding 模型（仅在创建时检查）
    if (!memoryBase) {
      // 验证Embedding模型
      if (embeddingModels.length === 0) {
        newErrors.embedding_model_config_id = t('memoryBases.form.noEmbeddingModels');
      } else if (!formData.embedding_model_config_id || formData.embedding_model_config_id === 0) {
        newErrors.embedding_model_config_id = t('memoryBases.form.selectEmbeddingModel');
      } else {
        const selectedEmbeddingModel = embeddingModels.find(
          model => parseInt(model.id) === formData.embedding_model_config_id
        );
        if (!selectedEmbeddingModel) {
          newErrors.embedding_model_config_id = t('memoryBases.form.embeddingModelUnavailable');
        }
      }

      // 验证LLM模型
      if (modelsList.length === 0) {
        newErrors.llm_model_config_id = t('memoryBases.form.noLlmModels');
      } else if (!formData.llm_model_config_id || formData.llm_model_config_id === 0) {
        newErrors.llm_model_config_id = t('memoryBases.form.selectLlmModelError');
      } else {
        const selectedLlmModel = modelsList.find(
          model => model.model_id === formData.llm_model_config_id
        );
        if (!selectedLlmModel || !selectedLlmModel.is_active) {
          newErrors.llm_model_config_id = t('memoryBases.form.modelUnavailable');
        }
      }
    } else {
      // 更新模式下，如果修改了LLM模型，验证是否有效
      if (formData.llm_model_config_id && formData.llm_model_config_id !== 0) {
        const selectedLlmModel = modelsList.find(
          model => model.model_id === formData.llm_model_config_id
        );
        if (!selectedLlmModel || !selectedLlmModel.is_active) {
          newErrors.llm_model_config_id = t('memoryBases.form.modelUnavailable');
        }
      }
    }

    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      return;
    }

    setIsLoading(true);

    try {
      if (memoryBase) {
        // 更新记忆库
        const updateData: UpdateMemoryBaseRequest = {
          space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
          mdb_id: memoryBase.mdb_id,
          name: formData.name,
          description: formData.description || '',
        };
        
        // 如果修改了LLM模型，添加到更新数据中
        if (formData.llm_model_config_id && formData.llm_model_config_id !== 0) {
          updateData.llm_model_config_id = formData.llm_model_config_id;
        }
        
        await updateMemoryBase(updateData);
      } else {
        // 创建记忆库前，先测试 embedding 模型是否可用
        const selectedEmbeddingModelId = formData.embedding_model_config_id.toString();
        try {
          // 测试 embedding 模型
          await testEmbeddingModelMutation.mutateAsync({
            id: selectedEmbeddingModelId,
            testRequest: { text: t('memoryBases.form.testText') },
          });
        } catch (testError: any) {
          // 测试失败，禁用该模型
          console.error('Embedding 模型测试失败，正在禁用模型:', testError);
          try {
            await toggleEmbeddingModelStatusMutation.mutateAsync({
              id: selectedEmbeddingModelId,
              spaceId: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
            });
          } catch (toggleError) {
            console.error('禁用Embedding模型失败:', toggleError);
          }
          
          // 在测试失败后清除相关的表单字段和错误
          setFormData(prev => ({ 
            ...prev, 
            embedding_model_config_id: 0 // 将embedding模型选择置为空
          }));
          
          // 更新错误状态，移除embedding模型相关的错误
          setErrors(prev => ({ 
            ...prev, 
            embedding_model_config_id: undefined 
          }));
          
          // 重新抛出错误以便上层处理
          throw new Error(t('memoryBases.form.embeddingModelTestFailed') + ': ' + (testError.message || testError));
        }

        const selectedModelId = formData.llm_model_config_id.toString();
        try {
          // 测试 embedding 模型
          await testLLMModelMutation.mutateAsync({
            id: selectedModelId,
            prompt: t('memoryBases.form.testText'),
            spaceId: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
          });
        } catch (testError: any) {
          // 测试失败，禁用该模型
          console.error('LLM 模型测试失败，正在禁用模型:', testError);
          try {
            await toggleLLMModelStatusMutation.mutateAsync({
              id: selectedModelId,
              spaceId: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
            });
          } catch (toggleError) {
            console.error('禁用LLM模型失败:', toggleError);
          }
          
          // 在测试失败后清除相关的表单字段和错误
          setFormData(prev => ({ 
            ...prev, 
            llm_model_config_id: 0 // 将embedding模型选择置为空
          }));
          
          // 更新错误状态，移除embedding模型相关的错误
          setErrors(prev => ({ 
            ...prev, 
            llm_model_config_id: undefined 
          }));
          
          // 重新抛出错误以便上层处理
          throw new Error(t('memoryBases.form.modelTestError') + ': ' + (testError.message || testError));
        }

        // 创建记忆库
        const createData: CreateMemoryBaseRequest = {
          space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
          name: formData.name,
          description: formData.description || '',
          embedding_model_config_id: formData.embedding_model_config_id,
          llm_model_config_id: formData.llm_model_config_id,
        };

        const result = await createMemoryBase(createData);
        
        // 如果有继续创建的回调，执行它
        if (onCreateAndContinue && result?.mdb_id) {
          onCreateAndContinue(result.mdb_id);
        }
      }

      onSuccess();
    } catch (error: any) {
      console.error('Failed to save memory base:', error);
      
      // 处理错误消息
      if (error.message?.includes('name exists')) {
        setErrors(prev => ({ ...prev, name: t('memoryBases.form.nameExists') }));
      } else if (error.message?.includes('embedding model')) {
        setErrors(prev => ({ ...prev, embedding_model_config_id: error.message }));
      } else if (error.message?.includes('llm model')) {
        setErrors(prev => ({ ...prev, llm_model_config_id: error.message }));
      } else {
        setErrors(prev => ({ 
          ...prev, 
          name: t('memoryBases.form.saveError', { message: error.message || 'Unknown error' }) 
        }));
      }
    } finally {
      setIsLoading(false);
      setErrors({});
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={onClose}></div>

        <div className="relative bg-white rounded-lg max-w-2xl w-full">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900">
              {memoryBase ? t('memoryBases.settings.title') : t('memoryBases.create.title')}
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6">
            <p className="text-gray-600 mb-6">
              {memoryBase ? t('memoryBases.edit.description') : t('memoryBases.create.description')}
            </p>

            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                {/* 基本信息 */}
                <div>
                  <CustomInput
                    label={t('memoryBases.form.name')}
                    value={formData.name}
                    onChange={handleNameChange}
                    placeholder={t('memoryBases.form.namePlaceholder')}
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
                    label={t('memoryBases.form.description')}
                    value={formData.description}
                    onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder={t('memoryBases.form.descriptionPlaceholder')}
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
                {!memoryBase && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {t('memoryBases.form.embeddingModelRequired')} <span className="text-red-500">
                        *
                        <Tooltip title={t('memoryBases.form.embeddingModelDesc')} placement="top" arrow>
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
                        </span>
                    </label>
                    {isLoadingEmbeddingModels ? (
                      <div className="text-sm text-gray-500">{t('memoryBases.form.loadingModels')}</div>
                    ) : embeddingModels.length === 0 ? (
                      <div className="flex flex-col gap-2">
                        <p className="text-sm text-red-500">
                          {t('memoryBases.form.noModels')}{' '}
                        </p>
                        <Link
                          to="/dashboard/models"
                          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                          {t('memoryBases.form.createEmbeddingModelLink')}
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </div>
                    ) : (
                      <select
                        value={formData.embedding_model_config_id || ''}
                        onChange={e => {
                          const selectedValue = e.target.value;
                          if (selectedValue === '') {
                            setFormData(prev => ({ ...prev, embedding_model_config_id: 0 }));
                          } else {
                            const selectedId = parseInt(selectedValue);
                            setFormData(prev => ({ ...prev, embedding_model_config_id: selectedId }));
                            // 清除错误（如果用户选择了有效的模型）
                            if (embeddingModels.find(model => parseInt(model.id) === selectedId)) {
                              setErrors(prev => ({ ...prev, embedding_model_config_id: undefined }));
                            }
                          }
                        }}
                        className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          !formData.embedding_model_config_id ? 'text-gray-400' : ''
                        }`}
                        style={!formData.embedding_model_config_id ? { color: '#9ca3af' } : {}}
                      >
                        <option value="" disabled hidden style={{ color: '#9ca3af' }}>
                          {t('memoryBases.form.selectModel')}
                        </option>
                        {embeddingModels.map(model => (
                          <option key={model.id} value={parseInt(model.id)} style={{ color: '#111827' }}>
                            {model.name} ({model.modelId})
                          </option>
                        ))}
                      </select>
                    )}
                    {errors.embedding_model_config_id && (
                      <p className="text-red-500 text-sm mt-1">{errors.embedding_model_config_id}</p>
                    )}
                  </div>
                )}

                {/* LLM 模型选择器 - 仅在创建时显示 */}
                {!memoryBase && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {t('memoryBases.form.llmModelRequired')} <span className="text-red-500">
                        *
                        <Tooltip title={t('memoryBases.form.llmModelDesc')} placement="top" arrow>
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
                        </span>
                    </label>
                    {isLoadingLlmModels ? (
                      <div className="text-sm text-gray-500">{t('memoryBases.form.loadingModels')}</div>
                    ) : modelsList.length === 0 ? (
                      <div className="flex flex-col gap-2">
                        <p className="text-sm text-red-500">
                          {t('memoryBases.form.noLlmModels')}{' '}
                        </p>
                        <Link
                          to="/dashboard/models"
                          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                          {t('memoryBases.form.createLLMModelLink')}
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </div>
                    ) : (
                      <select
                        value={formData.llm_model_config_id || ''}
                        onChange={e => {
                          const selectedValue = e.target.value;
                          if (selectedValue === '') {
                            setFormData(prev => ({ ...prev, llm_model_config_id: 0 }));
                          } else {
                            const selectedId = parseInt(selectedValue);
                            setFormData(prev => ({ ...prev, llm_model_config_id: selectedId }));
                            // 清除错误（如果用户选择了有效的模型）
                            if (modelsList.find(model => model.model_id === selectedId && model.is_active)) {
                              setErrors(prev => ({ ...prev, llm_model_config_id: undefined }));
                            }
                          }
                        }}
                        className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                          !formData.llm_model_config_id ? 'text-gray-400' : ''
                        }`}
                        style={!formData.llm_model_config_id ? { color: '#9ca3af' } : {}}
                      >
                        <option value="" disabled hidden style={{ color: '#9ca3af' }}>
                          {t('memoryBases.form.selectLlmModel')}
                        </option>
                        {modelsList.filter(model => model.is_active).map(model => (
                          <option key={model.model_id} value={model.model_id} style={{ color: '#111827' }}>
                            {model.model_name} ({model.model_provider})
                          </option>
                        ))}
                      </select>
                    )}
                    {errors.llm_model_config_id && (
                      <p className="text-red-500 text-sm mt-1">{errors.llm_model_config_id}</p>
                    )}
                  </div>
                )}
              </div>

              {/* 对话框底部按钮 */}
              <div className="mt-6 pt-6 border-t">
                {isAtLimit && (
                  <p className="text-sm text-red-500 mb-3">{t('memoryBases.form.limitReached')}</p>
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
                      !!errors.llm_model_config_id ||
                      isAtLimit ||
                      (!memoryBase && embeddingModels.length === 0) ||
                      (!memoryBase && modelsList.length === 0)
                    }
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading ? t('common.saving') : memoryBase ? t('common.buttons.update') : t('common.buttons.create')}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemoryBaseFormDialog;
