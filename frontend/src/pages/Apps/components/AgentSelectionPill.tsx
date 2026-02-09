/**
 * Agent Selection Pill Component
 * 智能体选择悬浮框组件 - 显示已选中的智能体，提供配置和取消选择功能
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { Settings, Bot, X } from 'lucide-react'
import { MentionItem } from './MentionPicker'
import { RADIUS_BUTTON, RADIUS_SMALL, RADIUS_CIRCLE } from '../constants/styles'

export interface AgentSelectionPillProps {
  agent: MentionItem
  onConfig: () => void
  onDeselect: () => void
}

const AgentSelectionPill: React.FC<AgentSelectionPillProps> = ({ agent, onConfig, onDeselect }) => {
  const { t } = useTranslation()
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 ${RADIUS_BUTTON} shadow-sm`}>
      {/* 机器人图标 */}
      <div className={`flex-shrink-0 w-5 h-5 flex items-center justify-center bg-blue-100 ${RADIUS_CIRCLE}`}>
        <Bot className="w-3 h-3 text-blue-600" />
      </div>

      {/* 智能体名称 */}
      <span className="text-sm font-medium text-gray-900">{agent.name}</span>

      {/* 分隔线 */}
      <div className="w-px h-4 bg-gray-200" />

      {/* 配置按钮 */}
      <button
        onClick={onConfig}
        className={`flex-shrink-0 p-1 text-gray-400 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-400 ${RADIUS_SMALL} transition-all duration-200`}
        title={t('apps.agent.configAgent')}
      >
        <Settings className="w-3.5 h-3.5" />
      </button>

      {/* 取消选择按钮 */}
      <button
        onClick={onDeselect}
        className={`flex-shrink-0 p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-400 ${RADIUS_SMALL} transition-all duration-200`}
        title={t('apps.agent.deselectAgent')}
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export default AgentSelectionPill
