/**
 * General Config Tab Component
 * 通用配置标签内容组件
 * 包含交互设置和规划设置
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'

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
}

export const GeneralConfigTab: React.FC<GeneralConfigTabProps> = ({
  config,
  updateConfig,
  ToggleSwitch,
  RangeSlider
}) => {
  const { t } = useTranslation()
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
