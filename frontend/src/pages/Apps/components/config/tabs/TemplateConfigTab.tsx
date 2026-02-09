/**
 * Template Config Tab Component
 * 模板配置标签内容组件
 * 包含模板列表和上传功能
 */

import React from 'react'
import { Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'
import { TemplateList } from '../template/TemplateList'
import { EmptyTemplateState } from '../template/EmptyTemplateState'
import { ReportTemplate } from '../../AgentConfigDialog'
import { RADIUS_BUTTON } from '../../../constants/styles'

export interface TemplateConfigTabProps extends ConfigTabProps {
  /** 模板列表 */
  templates: ReportTemplate[]
  /** 模板加载状态 */
  templatesLoading: boolean
  /** 上传中状态 */
  uploading: boolean
  /** 上传错误信息 */
  uploadError: string | null
  /** 选择模板回调 */
  onSelectTemplate: (templateId: number | undefined) => void
  /** 删除模板回调 */
  onDeleteTemplate: (templateId: number) => void
  /** 显示上传对话框 */
  onShowUploadDialog: () => void
  /** 查看模板回调 */
  onViewTemplate?: (templateId: number) => void
}

/**
 * 模板配置标签组件
 */
export const TemplateConfigTab: React.FC<TemplateConfigTabProps> = ({
  config,
  templates,
  templatesLoading,
  uploading,
  uploadError,
  onSelectTemplate,
  onDeleteTemplate,
  onShowUploadDialog,
  onViewTemplate
}) => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      {/* 可用模板 */}
      <ConfigSection title={t('apps.config.template.available')}>
        {templatesLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : templates.length > 0 ? (
          <TemplateList
            templates={templates}
            selectedId={config.selectedTemplateId}
            onSelect={onSelectTemplate}
            onDelete={onDeleteTemplate}
            onView={onViewTemplate}
          />
        ) : (
          <EmptyTemplateState onUpload={onShowUploadDialog} />
        )}
      </ConfigSection>

      {/* 上传新模板按钮 */}
      {templates.length > 0 && (
        <div className="pt-6 border-t border-gray-100">
          <button
            onClick={onShowUploadDialog}
            disabled={uploading}
            className={`
              w-full px-4 py-3 ${RADIUS_BUTTON} text-sm font-medium
              border border-gray-300 text-gray-700
              hover:bg-gray-50 hover:border-gray-400
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200 flex items-center justify-center gap-2
            `}
          >
            <Plus className="w-4 h-4" />
            {uploading ? t('apps.config.template.uploading') : t('apps.config.template.uploadNew')}
          </button>
        </div>
      )}

      {/* 上传错误提示 */}
      {uploadError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <p className="text-sm text-red-600">{uploadError}</p>
        </div>
      )}
    </div>
  )
}

export default TemplateConfigTab
