/**
 * Model Config Tab Component
 * 模型配置标签页组件
 * 包含基础配置（通用模型）和高级配置（生成大纲、信息选择、报告撰写）
 */

import React, { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Info } from 'lucide-react'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'
import { ModelSelector } from '@/components/Prompts'
import type { Model } from '@/types/promptType'
import { useTestModel } from '@test-agentstudio/api-client'
import { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'

// 从父组件传入的控件组件
export interface ModelConfigTabProps extends ConfigTabProps {
  /** 可用模型列表 */
  availableModels: Model[]
  /** 模型加载状态 */
  modelsLoading: boolean
  /** 空间 ID，用于模型测试 */
  spaceId?: string
  availableVLMModels?: Model[]
  vlmModelsLoading?: boolean
}

// 模型配置项类型
interface ModelConfigItem {
  id: string
  labelKey: string
  descKey: string
  recommendationKey: string
  configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId'
}

/**
 * 模型配置项组件
 */
const ModelConfigItem: React.FC<{
  label: string
  description: string
  recommendation?: string
  availableModels: Model[]
  selectedModel: Model | null
  modelsLoading: boolean
  onModelChange: (model: Model | null) => void
  placeholder?: string
  required?: boolean
  // 测试中状态 - 当前选项是否正在测试
  isCurrentTesting?: boolean
  // 其他选项是否正在测试（用于锁定）
  isOtherTesting?: boolean
}> = ({
  label,
  description,
  recommendation,
  availableModels,
  selectedModel,
  modelsLoading,
  onModelChange,
  placeholder,
  required = false,
  isCurrentTesting,
  isOtherTesting,
}) => {
  const { t } = useTranslation()

  // 当前选项正在测试：显示验证中 placeholder 和灰色，清除选中状态
  // 其他选项正在测试：显示灰色锁定，但保留选中状态和 placeholder
  const isLocked = isOtherTesting
  const isTesting = isCurrentTesting

  // 测试期间显示验证中的 placeholder（仅当前测试的选项）
  const displayPlaceholder = isTesting ? t('components.prompts.modelSelector.validating') : placeholder

  // 仅当前测试的选项清除选中状态，其他选项保持原有选中状态
  const displaySelectedModel = isTesting ? null : selectedModel

  return (
    <div className="flex items-center gap-4 py-1">
      <div className="flex-shrink-0 w-[300px]">
        <span className="text-sm text-gray-900 font-medium">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </span>
        {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
        {recommendation && <p className="text-xs text-gray-500 mt-1">{recommendation}</p>}
      </div>
      <div className="flex-1 min-w-[240px]">
        <ModelSelector
          availableModels={availableModels}
          selectedModel={displaySelectedModel}
          onModelChange={onModelChange}
          modelsLoading={modelsLoading || !!isTesting || !!isLocked}
          placeholder={displayPlaceholder}
          className={`bg-white rounded-lg ${isLocked || isTesting ? 'opacity-75' : ''}`}
          disabled={isLocked || isTesting}
        />
      </div>
    </div>
  )
}

/**
 * 模型配置标签组件
 */
export const ModelConfigTab: React.FC<ModelConfigTabProps> = ({
  config,
  updateConfig,
  availableModels,
  modelsLoading,
  spaceId,
  availableVLMModels = [],
  vlmModelsLoading = false,
}) => {
  const { t } = useTranslation()

  // 模型测试状态
  const [testingModelId, setTestingModelId] = useState<string | null>(null)
  // 正在测试的配置项 key
  const [testingConfigKey, setTestingConfigKey] = useState<
    'generalModelId' | 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId' | null
  >(null)

  // 模型测试 hook
  const testModelMutation = useTestModel()

  // Snackbar hook
  const { showSuccess, showError } = useUnifiedSnackbar()

  // 高级模型配置项
  const advancedModelConfigs: ModelConfigItem[] = [
    {
      id: 'outline',
      labelKey: 'apps.config.model.outline.label',
      descKey: 'apps.config.model.outline.description',
      recommendationKey: 'apps.config.model.outline.recommendation',
      configKey: 'planUnderstandingModelId',
    },
    {
      id: 'infoCollecting',
      labelKey: 'apps.config.model.infoCollecting.label',
      descKey: 'apps.config.model.infoCollecting.description',
      recommendationKey: 'apps.config.model.infoCollecting.recommendation',
      configKey: 'infoCollectingModelId',
    },
    {
      id: 'reportWriting',
      labelKey: 'apps.config.model.reportWriting.label',
      descKey: 'apps.config.model.reportWriting.description',
      recommendationKey: 'apps.config.model.reportWriting.recommendation',
      configKey: 'writingCheckingModelId',
    },
  ]

  // 根据模型 ID 获取模型对象
  const getModelById = (modelId: string | undefined): Model | null => {
    if (!modelId) return null
    return availableModels.find(m => m.openModel.model_id === modelId) || null
  }

  const getVLMModelById = (modelId: string | undefined): Model | null => {
    if (!modelId) return null
    return availableVLMModels.find(m => m.openModel.model_id === modelId) || null
  }

  // 带验证的模型选择处理函数
  const handleModelSelectWithTest = useCallback(
    async (model: Model | null, configKey: 'generalModelId' | 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId') => {
      // 用户选择空值，直接清除
      if (!model) {
        updateConfig(configKey, undefined)
        return
      }

      // 检查是否已经有 spaceId
      if (!spaceId) {
        showError(t('apps.config.model.test.missingSpaceId'))
        return
      }

      // 如果已经是当前选中的模型，不做任何操作
      const currentModelId = config[configKey]
      if (model.openModel.model_id === currentModelId) {
        return
      }

      // 如果已经在测试这个模型，忽略此次请求
      if (testingModelId === model.openModel.model_id) {
        return
      }

      // 先清除当前选中的模型（在 UI 上立即反映）
      updateConfig(configKey, undefined)

      // 记录待测试的模型和配置项，进入"pending"状态
      setTestingModelId(model.openModel.model_id)
      setTestingConfigKey(configKey)

      try {
        // 调用测试接口，发送"你好"作为测试 prompt
        const result = await testModelMutation.mutateAsync({
          id: model.openModel.model_id,
          prompt: t('apps.config.model.test.prompt'),
          spaceId: spaceId,
          parameters: { temperature: 0.7, max_tokens: 100 },
        })

        if (result.success) {
          // 测试通过，正式选中模型
          updateConfig(configKey, model.openModel.model_id)
          showSuccess(t('apps.config.model.test.validationPassed'))
        } else {
          showError(t('apps.config.model.test.unavailable', { error: result.error || t('apps.errors.unknownError') }))
        }
      } catch (error: any) {
        const errorMessage = error?.response?.data?.message || error?.message || t('apps.config.model.test.testFailed')
        showError(t('apps.config.model.test.unavailable', { error: errorMessage }))
      } finally {
        // 清除测试状态
        setTestingModelId(null)
        setTestingConfigKey(null)
      }
    },
    [testModelMutation, spaceId, config, updateConfig, testingModelId, showSuccess, showError],
  )

  // 处理通用模型选择变更（带验证）
  const handleGeneralModelChange = (model: Model | null) => {
    handleModelSelectWithTest(model, 'generalModelId')
  }

  // 处理高级模型选择变更（带验证）
  const handleModelChange = (configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId', model: Model | null) => {
    handleModelSelectWithTest(model, configKey)
  }

  return (
    <>
      <div className="space-y-8">
        {/* 基础配置 */}
        <ConfigSection title={t('apps.config.model.general.title')}>
          <div className="space-y-4">
            <ModelConfigItem
              label={t('apps.config.model.general.label')}
              description={t('apps.config.model.general.description')}
              availableModels={availableModels}
              selectedModel={getModelById(config.generalModelId)}
              modelsLoading={modelsLoading}
              onModelChange={handleGeneralModelChange}
              placeholder={t('apps.config.model.useGeneral')}
              required={true}
              isCurrentTesting={testingConfigKey === 'generalModelId'}
              isOtherTesting={!!testingModelId && testingConfigKey !== 'generalModelId'}
            />
          </div>
        </ConfigSection>

        {/* 高级配置 */}
        <ConfigSection title={t('apps.config.model.advanced.title')}>
          {/* 提示信息横幅 */}
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">{t('apps.config.model.advanced.info')}</p>
          </div>

          {/* 高级配置项 */}
          <div className="space-y-4">
            {advancedModelConfigs.map(modelConfig => (
              <ModelConfigItem
                key={modelConfig.id}
                label={t(modelConfig.labelKey)}
                description={t(modelConfig.descKey)}
                recommendation={t(modelConfig.recommendationKey)}
                availableModels={availableModels}
                selectedModel={getModelById(config[modelConfig.configKey])}
                modelsLoading={modelsLoading}
                onModelChange={model => handleModelChange(modelConfig.configKey, model)}
                placeholder={t('apps.config.model.useGeneral')}
                isCurrentTesting={testingConfigKey === modelConfig.configKey}
                isOtherTesting={!!testingModelId && testingConfigKey !== modelConfig.configKey}
              />
            ))}

            <ModelConfigItem
              label={t('apps.config.model.vlmChart.label', { defaultValue: 'VLM 图表生成模型' })}
              description={t('apps.config.model.vlmChart.description', { defaultValue: '用于 DeepSearch 图表生成后的视觉模型迭代优化' })}
              recommendation={t('apps.config.model.vlmChart.recommendation', { defaultValue: '建议选择支持图像输入的多模态模型' })}
              availableModels={availableVLMModels}
              selectedModel={getVLMModelById(config.vlmChartModelId)}
              modelsLoading={vlmModelsLoading}
              onModelChange={model => updateConfig('vlmChartModelId', model?.openModel.model_id)}
              placeholder={t('apps.config.model.useGeneral')}
              required={config.vlmChartGeneratorEnable && config.vlmChartGeneratorMaxIterations > 0}
              isCurrentTesting={false}
              isOtherTesting={!!testingModelId}
            />
          </div>
        </ConfigSection>
      </div>
    </>
  )
}

export default ModelConfigTab
