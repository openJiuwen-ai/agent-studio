/**
 * Empty Template State Component
 * 空模板状态组件
 * 用于展示无模板时的提示
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { FileX, Upload } from 'lucide-react'
import { RADIUS_BUTTON } from '../../../constants/styles'

export interface EmptyTemplateStateProps {
  /** 上传按钮点击回调 */
  onUpload: () => void
}

/**
 * 空模板状态组件
 */
export const EmptyTemplateState: React.FC<EmptyTemplateStateProps> = ({
  onUpload
}) => {
  const { t } = useTranslation()
  return (
    <div className="text-center py-8 px-4">
      <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <FileX className="w-8 h-8 text-gray-400" />
      </div>
      <h4 className="text-sm font-semibold text-gray-900 mb-2">{t('apps.config.template.emptyTitle')}</h4>
      <p className="text-xs text-gray-500 mb-4">{t('apps.config.template.emptyDescription')}</p>
      <button
        onClick={onUpload}
        className={`
          inline-flex items-center justify-center gap-2 px-4 py-2
          ${RADIUS_BUTTON} text-sm font-medium
          bg-blue-600 text-white hover:bg-blue-700
          shadow-sm hover:shadow transition-all duration-200
        `}
      >
        <Upload className="w-4 h-4" />
        {t('apps.config.template.uploadButton')}
      </button>
    </div>
  )
}

export default EmptyTemplateState
