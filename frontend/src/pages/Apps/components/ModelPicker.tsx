/**
 * Model Picker Component
 * 模型选择器
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Info } from 'lucide-react'
import ModelIcon from '@/assets/icons/modelManagement.svg?react'
import { BasePickerContainer, usePickerKeyboard } from './BasePicker'
import { RADIUS_SMALL } from '../constants/styles'

export interface ModelItem {
  name: string
  provider?: string
}

export interface ModelPickerProps {
  models: string[]
  selectedModel: string
  onSelect: (model: string) => void
  onClose: () => void
  position: { x: number; y: number }
  isLoading?: boolean
}

const ModelPicker: React.FC<ModelPickerProps> = ({
  models,
  selectedModel,
  onSelect,
  onClose,
  position,
  isLoading = false,
}) => {
  const { t } = useTranslation()
  const [selectedIndex, setSelectedIndex] = useState(0)

  // 找到当前选中的索引
  useEffect(() => {
    const currentIndex = models.indexOf(selectedModel)
    if (currentIndex >= 0) {
      setSelectedIndex(currentIndex)
    }
  }, [selectedModel, models])

  // 处理选择
  const handleSelect = useCallback(() => {
    if (models[selectedIndex]) {
      onSelect(models[selectedIndex])
      onClose()
    }
  }, [models, selectedIndex, onSelect, onClose])

  // 使用通用键盘导航
  usePickerKeyboard({
    itemCount: models.length,
    selectedIndex,
    setSelectedIndex,
    onSelect: handleSelect,
  })

  // 无模型时不显示
  if (isLoading) {
    return null
  }

  if (models.length === 0) {
    return null
  }

  return (
    <BasePickerContainer onClose={onClose} position={position}>
      {/* 标题 */}
      <div className="px-3 py-2 border-b border-gray-100">
        <span className="text-xs font-medium text-gray-500">{t('apps.model.selectModel')}</span>
      </div>

      {/* 温馨提示 */}
      <div className="mx-3 mt-2 mb-1 px-2.5 py-1.5 rounded-md border border-amber-200 bg-amber-50 flex items-start gap-2">
        <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
        <span className="text-xs text-amber-800">
          {t('apps.model.contextLengthWarning')}
        </span>
      </div>

      {/* 列表 */}
      <div className="py-1">
        {models.map((model, index) => {
          const isSelected = index === selectedIndex || model === selectedModel

          return (
            <div
              key={model}
              className={`
                flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors
                ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'}
              `}
              onClick={() => {
                onSelect(model)
                onClose()
              }}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              {/* 图标 */}
              <div className={`flex-shrink-0 p-1 ${RADIUS_SMALL} text-blue-600 bg-blue-50`}>
                <ModelIcon className="w-4 h-4" />
              </div>

              {/* 内容 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                    {model}
                  </span>
                  {(isSelected || model === selectedModel) && <Check className="w-3 h-3 text-blue-600" />}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </BasePickerContainer>
  )
}

export default ModelPicker
