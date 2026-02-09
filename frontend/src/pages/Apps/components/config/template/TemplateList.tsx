/**
 * Template List Component
 * 模板列表组件
 * 用于展示和选择报告模板
 * 优化交互：点击模板卡片即选中并启用，再次点击取消选中
 */

import React from 'react'
import { FileText, Trash2, Check, Eye } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ReportTemplate } from '../../AgentConfigDialog'
import { RADIUS_BUTTON } from '../../../constants/styles'

export interface TemplateListProps {
  /** 模板列表 */
  templates: ReportTemplate[]
  /** 当前选中的模板ID */
  selectedId?: number
  /** 选择模板回调（传入id，如果已选中则传入undefined取消） */
  onSelect: (id: number | undefined) => void
  /** 删除模板回调（可选） */
  onDelete?: (id: number) => void
  /** 查看模板回调（可选） */
  onView?: (id: number) => void
}

/**
 * 模板列表组件
 */
export const TemplateList: React.FC<TemplateListProps> = ({
  templates,
  selectedId,
  onSelect,
  onDelete,
  onView
}) => {
  const { t } = useTranslation()

  if (templates.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-gray-500">{t('apps.config.template.available')}</p>
      </div>
    )
  }

  const handleSelect = (id: number) => {
    // 如果点击已选中的模板，则取消选中
    if (selectedId === id) {
      onSelect(undefined)
    } else {
      onSelect(id)
    }
  }

  return (
    <div className="space-y-2">
      {templates.map(template => {
        const isSelected = selectedId === template.template_id

        return (
          <div
            key={template.template_id}
            className={`
              group relative px-4 py-3 ${RADIUS_BUTTON} text-sm transition-all duration-200 border cursor-pointer flex items-center gap-3
              ${isSelected
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }
            `}
            onClick={() => handleSelect(template.template_id)}
          >
            {/* 左侧小图标 */}
            <FileText className={`w-4 h-4 flex-shrink-0 ${isSelected ? 'text-blue-600' : 'text-gray-400'}`} />

            {/* 模板信息 */}
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">
                {template.template_name}
              </div>
              <div className={`text-xs truncate ${isSelected ? 'text-blue-600/70' : 'text-gray-400'}`}>
                {template.template_desc || t('apps.config.template.noDescription')}
              </div>
            </div>

            {/* 右侧：选中标记或操作按钮 */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {/* 查看按钮 - 选中或未选中都显示 */}
              {onView && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onView(template.template_id)
                  }}
                  className="p-1.5 text-gray-300 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title={t('apps.config.template.viewTemplate')}
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              )}

              {/* 选中标记或删除按钮 */}
              {isSelected ? (
                <div className="w-8 h-8 flex items-center justify-center">
                  <Check className="w-4 h-4 text-blue-600" />
                </div>
              ) : onDelete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(template.template_id)
                  }}
                  className="p-1.5 text-gray-300 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title={t('apps.config.template.deleteTemplate')}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default TemplateList
