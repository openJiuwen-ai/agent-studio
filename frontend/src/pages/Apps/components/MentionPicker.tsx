/**
 * Mention Picker Component
 * 用于选择智能体 (@) 和资源 (#)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Bot, Database, FileText, Globe, Upload } from 'lucide-react'
import { BasePickerContainer, usePickerKeyboard } from './BasePicker'
import { RADIUS_SMALL } from '../constants/styles'

// ==================== 类型定义 ====================

export type MentionType = 'agent' | 'knowledge' | 'document' | 'websearch'

export interface MentionItem {
  id: string
  name: string
  type: MentionType
  description?: string
  icon?: React.ReactNode
}

export interface MentionPickerProps {
  // 触发字符 (@ 或 #)
  trigger: string
  // 当前输入的查询文本
  query: string
  // 候选项列表
  items: MentionItem[]
  // 选择回调
  onSelect: (item: MentionItem) => void
  // 关闭回调
  onClose: () => void
  // 位置
  position: { x: number; y: number }
  // 文件上传回调 (仅 # 触发器)
  onFileUpload?: (files: FileList) => void
}

// ==================== 辅助函数 ====================

/**
 * 根据类型获取图标
 */
const getTypeIcon = (type: MentionType): React.ReactNode => {
  const iconClassName = 'w-4 h-4'
  switch (type) {
    case 'agent':
      return <Bot className={iconClassName} />
    case 'knowledge':
      return <Database className={iconClassName} />
    case 'document':
      return <FileText className={iconClassName} />
    case 'websearch':
      return <Globe className={iconClassName} />
    default:
      return null
  }
}

/**
 * 根据类型获取颜色
 */
const getTypeColor = (type: MentionType): string => {
  switch (type) {
    case 'agent':
      return 'text-blue-600 bg-blue-50'
    case 'knowledge':
      return 'text-purple-600 bg-purple-50'
    case 'document':
      return 'text-green-600 bg-green-50'
    case 'websearch':
      return 'text-orange-600 bg-orange-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}

// ==================== 主组件 ====================

export const MentionPicker: React.FC<MentionPickerProps> = ({
  trigger,
  query,
  items,
  onSelect,
  onClose,
  position,
  onFileUpload,
}) => {
  const { t } = useTranslation()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [filteredItems, setFilteredItems] = useState<MentionItem[]>(items)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 处理文件上传按钮点击
  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0 && onFileUpload) {
      onFileUpload(files)
      onClose()
    }
  }

  // 根据查询文本过滤项
  useEffect(() => {
    if (!query) {
      setFilteredItems(items)
    } else {
      const lowerQuery = query.toLowerCase()
      setFilteredItems(items.filter(item => item.name.toLowerCase().includes(lowerQuery)))
    }
    setSelectedIndex(0)
  }, [query, items])

  // 处理选择
  const handleSelect = useCallback(() => {
    if (filteredItems[selectedIndex]) {
      onSelect(filteredItems[selectedIndex])
    }
  }, [filteredItems, selectedIndex, onSelect])

  // 计算总项数（包括上传选项）
  const totalItems = filteredItems.length + (trigger === '#' && onFileUpload ? 1 : 0)

  // 使用通用键盘导航
  usePickerKeyboard({
    itemCount: totalItems,
    selectedIndex,
    setSelectedIndex,
    onSelect: handleSelect,
  })

  return (
    <BasePickerContainer onClose={onClose} position={position}>
      {/* 标题 */}
      <div className="px-3 py-2 border-b border-gray-100">
        <span className="text-xs font-medium text-gray-500">
          {trigger === '@' ? t('apps.picker.selectAgent') : t('apps.picker.selectResource')}
        </span>
      </div>

      {/* 列表 */}
      <div className="py-1">
        {filteredItems.map((item, index) => {
          const isSelected = index === selectedIndex
          const typeColor = getTypeColor(item.type)

          return (
            <div
              key={item.id}
              className={`
                flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors
                ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'}
              `}
              onClick={() => onSelect(item)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              {/* 图标 */}
              <div className={`flex-shrink-0 p-1 ${RADIUS_SMALL} ${typeColor}`}>
                {item.icon || getTypeIcon(item.type)}
              </div>

              {/* 内容 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                    {item.name}
                  </span>
                  {isSelected && <Check className="w-3 h-3 text-blue-600" />}
                </div>
                {item.description && (
                  <p className="text-xs text-gray-500 truncate">
                    {item.description.startsWith('apps.') ? t(item.description) : item.description}
                  </p>
                )}
              </div>
            </div>
          )
        })}

        {/* 仅 # 触发器：显示知识库和上传文件选项 */}
        {trigger === '#' && (
          <>
            {/* 分隔线 - 仅在有知识库时显示 */}
            {filteredItems.length > 0 && <div className="my-1 border-t border-gray-100" />}

            {/* 暂无知识库选项 (禁用状态) */}
            {filteredItems.length === 0 && (
              <div
                className="flex items-center gap-2 px-3 py-2 cursor-not-allowed opacity-50"
                onMouseEnter={() => setSelectedIndex(filteredItems.length)}
              >
                {/* 图标 */}
                <div className={`flex-shrink-0 p-1 ${RADIUS_SMALL} text-gray-400 bg-gray-50`}>
                  <Database className="w-4 h-4" />
                </div>

                {/* 内容 */}
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-400">{t('apps.picker.noKnowledgeBase')}</span>
                  <p className="text-xs text-gray-400">{t('apps.picker.noKnowledgeBaseConnected')}</p>
                </div>
              </div>
            )}

            {/* 文件上传选项 */}
            {onFileUpload && (
              <div
                className="flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors hover:bg-gray-50"
                onClick={handleUploadClick}
                onMouseEnter={() => setSelectedIndex(filteredItems.length + (filteredItems.length === 0 ? 1 : 0))}
              >
                {/* 图标 */}
                <div className={`flex-shrink-0 p-1 ${RADIUS_SMALL} text-green-600 bg-green-50`}>
                  <Upload className="w-4 h-4" />
                </div>

                {/* 内容 */}
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-900">{t('apps.picker.uploadLocalFiles')}</span>
                  <p className="text-xs text-gray-500">{t('apps.picker.uploadFileDescription')}</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.doc,.docx,.txt,.md,.json,.csv"
        className="hidden"
        onChange={handleFileChange}
      />
    </BasePickerContainer>
  )
}

// ==================== 默认数据 ====================

/**
 * 默认智能体列表
 */
export const DEFAULT_AGENTS: MentionItem[] = [
  {
    id: 'deepsearch',
    name: 'DeepSearch',
    type: 'agent',
    description: 'apps.picker.deepSearchAgent',
  },
]

/**
 * 默认资源列表
 */
export const DEFAULT_RESOURCES: MentionItem[] = []

export default MentionPicker
