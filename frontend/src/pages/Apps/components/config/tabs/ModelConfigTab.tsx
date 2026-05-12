/**
 * Model Config Tab Component
 * 模型配置标签页组件
 * Research mode: 基础配置（通用模型）和高级配置（生成大纲、信息选择、报告撰写）
 * Search mode: 通过平台模型选择器选择 Planning Model + Search Model
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

export interface ModelConfigTabProps extends ConfigTabProps {
  /** 可用模型列表 */
  availableModels: Model[]
  /** 模型加载状态 */
  modelsLoading: boolean
  /** 空间 ID，用于模型测试 */
  spaceId?: string
  availableVLMModels?: Model[]
  vlmModelsLoading?: boolean
  /** 配置模式 */
  mode?: 'research' | 'search'
}

// 模型配置项类型
interface ModelConfigItemDef {
  id: string
  labelKey: string
  descKey: string
  recommendationKey: string
  configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId'
}

/**
 * 模型配置项组件（用于 Research mode 的 platform model picker）
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
  isCurrentTesting?: boolean
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
  const isLocked = isOtherTesting
  const isTesting = isCurrentTesting
  const displayPlaceholder = isTesting ? t('components.prompts.modelSelector.validating') : placeholder
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
  mode = 'research',
}) => {
  const { t } = useTranslation()
  const [testingModelId, setTestingModelId] = useState<string | null>(null)
  const [testingConfigKey, setTestingConfigKey] = useState<
    'generalModelId' | 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId' | null
  >(null)
  const testModelMutation = useTestModel()
  const { showSuccess, showError } = useUnifiedSnackbar()

  // ==================== Search mode: platform model picker for Planning + Search models ====================
  if (mode === 'search') {
    const getModelById = (modelId: string | undefined): Model | null => {
      if (!modelId) return null
      return availableModels.find(m => m.openModel.model_id === modelId) || null
    }

    const handlePlanningModelChange = (model: Model | null) => {
      updateConfig('planningModelId', model?.openModel.model_id ?? undefined)
    }

    const handleSearchModelChange = (model: Model | null) => {
      updateConfig('searchModelId', model?.openModel.model_id ?? undefined)
    }

    return (
      <div className="space-y-6">
        <ModelConfigItem
          label={t('apps.config.model.planningModel.label')}
          description={t('apps.config.model.planningModel.description')}
          availableModels={availableModels}
          selectedModel={getModelById(config.planningModelId)}
          modelsLoading={modelsLoading}
          onModelChange={handlePlanningModelChange}
          placeholder={t('apps.config.model.selectModel')}
          required
        />

        <ModelConfigItem
          label={t('apps.config.model.searchModel.label')}
          description={t('apps.config.model.searchModel.description')}
          availableModels={availableModels}
          selectedModel={getModelById(config.searchModelId)}
          modelsLoading={modelsLoading}
          onModelChange={handleSearchModelChange}
          placeholder={t('apps.config.model.selectModel')}
          required
        />
      </div>
    )
  }

  // ==================== Research mode (original platform model picker) ====================
  const advancedModelConfigs: ModelConfigItemDef[] = [
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
      if (!model) {
        updateConfig(configKey, undefined)
        return
      }
      if (!spaceId) {
        showError('缺少 spaceId，无法测试模型')
        return
      }
      const currentModelId = config[configKey]
      if (model.openModel.model_id === currentModelId) return
      if (testingModelId === model.openModel.model_id) return

      updateConfig(configKey, undefined)
      setTestingModelId(model.openModel.model_id)
      setTestingConfigKey(configKey)

      try {
        const result = await testModelMutation.mutateAsync({
          id: model.openModel.model_id,
          prompt: '你好',
          spaceId: spaceId,
          parameters: { temperature: 0.7, max_tokens: 100 },
        })
        if (result.success) {
          updateConfig(configKey, model.openModel.model_id)
          showSuccess('模型可用性验证通过')
        } else {
          showError(`模型不可用：${result.error || '未知错误'}`)
        }
      } catch (error: any) {
        const errorMessage = error?.response?.data?.message || error?.message || '模型测试失败'
        showError(`模型不可用：${errorMessage}`)
      } finally {
        setTestingModelId(null)
        setTestingConfigKey(null)
      }
    },
    [testModelMutation, spaceId, config, updateConfig, testingModelId, showSuccess, showError],
  )

  const handleGeneralModelChange = (model: Model | null) => {
    handleModelSelectWithTest(model, 'generalModelId')
  }

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
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">{t('apps.config.model.advanced.info')}</p>
          </div>

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
