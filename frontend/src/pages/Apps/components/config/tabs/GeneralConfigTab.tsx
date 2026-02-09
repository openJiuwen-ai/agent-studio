/**
 * General Config Tab Component
 * 通用配置标签内容组件
 * 包含交互设置和规划设置
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'

// 临时定义控件类型，实际应从 AgentConfigDialog 导出
// 为了避免循环依赖，这里重新定义
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
}

// 从父组件传入的控件组件
export interface GeneralConfigTabProps extends ConfigTabProps {
  /** 开关组件 */
  ToggleSwitch: React.FC<ToggleSwitchProps>
  /** 滑块组件 */
  RangeSlider: React.FC<RangeSliderProps>
}

/**
 * 通用配置标签组件
 */
export const GeneralConfigTab: React.FC<GeneralConfigTabProps> = ({
  config,
  updateConfig,
  ToggleSwitch,
  RangeSlider
}) => {
  const { t } = useTranslation()
  return (
    <div className="space-y-8">
      {/* 交互设置 */}
      <ConfigSection title={t('apps.config.general.interactionSettings')}>
        <div className="space-y-4">
          {/* 启用人机交互 */}
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

          {/* 启用溯源 */}
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
        </div>
      </ConfigSection>

      {/* 规划章节数量 */}
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
