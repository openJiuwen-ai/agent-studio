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

/**
 * Integer input box with validation
 */
const IntegerInput: React.FC<{
  label: string
  description: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
}> = ({ label, description, value, min, max, onChange }) => {
  const [inputValue, setInputValue] = React.useState(String(value))
  const [isFocused, setIsFocused] = React.useState(false)

  React.useEffect(() => {
    if (!isFocused) setInputValue(String(value))
  }, [value, isFocused])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value
    setInputValue(v)
    const parsed = parseInt(v, 10)
    if (!isNaN(parsed) && parsed >= min && parsed <= max) {
      onChange(parsed)
    }
  }

  const handleBlur = () => {
    setIsFocused(false)
    const parsed = parseInt(inputValue, 10)
    if (isNaN(parsed) || parsed < min) {
      onChange(min)
      setInputValue(String(min))
    } else if (parsed > max) {
      onChange(max)
      setInputValue(String(max))
    }
  }

  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex-1 min-w-0 mr-4">
        <span className="text-sm text-gray-900 font-medium">{label}</span>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      <input
        type="number"
        value={isFocused ? inputValue : String(value)}
        onChange={handleChange}
        onFocus={() => setIsFocused(true)}
        onBlur={handleBlur}
        min={min}
        max={max}
        step={1}
        className="w-24 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
      />
    </div>
  )
}

export interface GeneralConfigTabProps extends ConfigTabProps {
  ToggleSwitch: React.FC<ToggleSwitchProps>
  RangeSlider: React.FC<RangeSliderProps>
  availableVLMModels?: Model[]
  vlmModelsLoading?: boolean
  mode?: 'research' | 'search'
}

export const GeneralConfigTab: React.FC<GeneralConfigTabProps> = ({
  config,
  updateConfig,
  ToggleSwitch,
  RangeSlider,
  availableVLMModels = [],
  vlmModelsLoading = false,
  mode = 'research',
}) => {
  const { t } = useTranslation()
  const getVLMModelById = (modelId: string | undefined): Model | null => {
    if (!modelId) return null
    return availableVLMModels.find(model => model.openModel.model_id === modelId) || null
  }

  return (
    <div className="space-y-8">
      {mode === 'research' && (
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
          </div>
        </ConfigSection>
      )}

      {mode === 'research' ? (
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
      ) : (
        <ConfigSection title={t('apps.config.general.searchProcessSettings')}>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-1">
              <div>
                <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.enableQuestionRouter')}</span>
                <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.enableQuestionRouterDesc')}</p>
              </div>
              <ToggleSwitch
                checked={config.enableQuestionRouter ?? false}
                onChange={checked => updateConfig('enableQuestionRouter', checked)}
              />
            </div>
            <IntegerInput
              label={t('apps.config.general.actionProposalsLimit')}
              description={t('apps.config.general.actionProposalsLimitDesc')}
              value={config.actionProposalsLimit ?? 5}
              min={1}
              max={10}
              onChange={value => updateConfig('actionProposalsLimit', value)}
            />
            <IntegerInput
              label={t('apps.config.general.actionsExploredLimit')}
              description={t('apps.config.general.actionsExploredLimitDesc')}
              value={config.actionsExploredLimit ?? 200}
              min={1}
              max={200}
              onChange={value => updateConfig('actionsExploredLimit', value)}
            />
            <IntegerInput
              label={t('apps.config.general.maxLlmCallsPerRun')}
              description={t('apps.config.general.maxLlmCallsPerRunDesc')}
              value={config.maxLlmCallsPerRun ?? 10}
              min={1}
              max={20}
              onChange={value => updateConfig('maxLlmCallsPerRun', value)}
            />
            <IntegerInput
              label={t('apps.config.general.timeLimit')}
              description={t('apps.config.general.timeLimitDesc')}
              value={config.timeLimit ?? 3600}
              min={1}
              max={3600}
              onChange={value => updateConfig('timeLimit', value)}
            />
          </div>
        </ConfigSection>
      )}
    </div>
  )
}

export default GeneralConfigTab
