/**
 * General Config Tab Component
 * 通用配置标签内容组件
 * 包含交互设置和规划设置
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'
import { ModelSelector } from '@/components/Prompts'
import type { Model } from '@/types/promptType'

interface ToggleSwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

interface RangeSliderProps {
  label: string
  description: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
  step?: number
}

export interface GeneralConfigTabProps extends ConfigTabProps {
  ToggleSwitch: React.FC<ToggleSwitchProps>
  RangeSlider: React.FC<RangeSliderProps>
  availableVLMModels?: Model[]
  vlmModelsLoading?: boolean
}

export const GeneralConfigTab: React.FC<GeneralConfigTabProps> = ({
  config,
  updateConfig,
  ToggleSwitch,
  RangeSlider,
  availableVLMModels = [],
  vlmModelsLoading = false
}) => {
  const { t } = useTranslation()
  const getVLMModelById = (modelId: string | undefined): Model | null => {
    if (!modelId) return null
    return availableVLMModels.find(model => model.openModel.model_id === modelId) || null
  }

  return (
    <div className="space-y-8">
      <ConfigSection title={t('apps.config.general.interactionSettings')}>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.enableHumanInteraction')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.enableHumanInteractionDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.enableHumanInteraction}
              onChange={checked => updateConfig('enableHumanInteraction', checked)}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.outlineInteractionEnabled')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.outlineInteractionEnabledDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.outlineInteractionEnabled}
              onChange={checked => updateConfig('outlineInteractionEnabled', checked)}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.executionModeEnabled')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.executionModeEnabledDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.execution_method === "dependency_driving"}
              onChange={checked => updateConfig('execution_method', checked ? "dependency_driving" : "parallel")}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.enableTraceability')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.enableTraceabilityDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.enableTraceability}
              onChange={checked => updateConfig('enableTraceability', checked)}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.userFeedbackProcessorEnable')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.userFeedbackProcessorEnableDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.userFeedbackProcessorEnable}
              onChange={checked => updateConfig('userFeedbackProcessorEnable', checked)}
            />
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">
                {t('apps.config.general.vlmChart.enable', { defaultValue: '启用 VLM 图表生成' })}
              </span>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('apps.config.general.vlmChart.enableDesc', { defaultValue: '使用视觉模型对 DeepSearch 生成的图表进行迭代优化' })}
              </p>
            </div>
            <ToggleSwitch
              checked={config.vlmChartGeneratorEnable}
              onChange={checked => updateConfig('vlmChartGeneratorEnable', checked)}
            />
          </div>

          {config.vlmChartGeneratorEnable && (
            <div className="ml-6 space-y-4 border-l border-gray-100 pl-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                <div className="flex-shrink-0 sm:w-[220px]">
                  <span className="text-sm text-gray-900 font-medium">
                    {t('apps.config.general.vlmChart.model', { defaultValue: 'VLM 模型' })}
                  </span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('apps.config.general.vlmChart.modelDesc', { defaultValue: '与模型配置中的VLM模型保持同步' })}
                  </p>
                </div>
                <div className="w-full max-w-[360px]">
                  <ModelSelector
                    availableModels={availableVLMModels}
                    selectedModel={getVLMModelById(config.vlmChartModelId)}
                    onModelChange={model => updateConfig('vlmChartModelId', model?.openModel.model_id)}
                    modelsLoading={vlmModelsLoading}
                    placeholder={t('apps.config.model.useGeneral')}
                    disabled={vlmModelsLoading}
                    className="bg-white rounded-lg"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                <div className="flex-shrink-0 sm:w-[220px]">
                  <span className="text-sm text-gray-900 font-medium">
                    {t('apps.config.general.vlmChart.maxIterations', { defaultValue: '最大迭代次数' })}
                  </span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('apps.config.general.vlmChart.maxIterationsDesc', { defaultValue: '0 表示不进行 VLM 迭代，建议 1-3 次' })}
                  </p>
                </div>
                <div className="w-full max-w-[360px]">
                  <div className="flex justify-end mb-2">
                    <span className="text-sm font-semibold text-blue-600">{config.vlmChartGeneratorMaxIterations}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={3}
                    step={1}
                    value={config.vlmChartGeneratorMaxIterations}
                    onChange={e => updateConfig('vlmChartGeneratorMaxIterations', Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </ConfigSection>

      <ConfigSection title={t('apps.config.general.chapterCount')}>
        <RangeSlider
          label={t('apps.config.general.chapterCount')}
          description={t('apps.config.general.chapterCountDesc')}
          value={config.planChapterCount}
          min={1}
          max={10}
          onChange={value => updateConfig('planChapterCount', value)}
        />
      </ConfigSection>
    </div>
  )
}

export default GeneralConfigTab
