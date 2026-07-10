import React, { useEffect, useState } from 'react'
import { Plus, ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { RADIUS_BUTTON, BUTTON_HOVER_EFFECTS, BUTTON_TRANSITION, RADIUS_CIRCLE } from '../../constants/styles'
import ConversationList from './ConversationList'
import type { ConversationHistorySidebarProps } from './types'

// Local storage key for sidebar collapsed state
const SIDEBAR_COLLAPSED_KEY = 'deepsearch_sidebar_collapsed'

const ConversationHistorySidebar: React.FC<ConversationHistorySidebarProps> = ({
  currentConversationId,
  onConversationSelect,
  onDeleteConversation,
  onNewConversation,
  isStreaming,
  forceCollapsed = false,
}) => {
  const { t, i18n } = useTranslation()

  const [isCollapsed, setIsCollapsed] = useState(false)

  // Load collapsed state from localStorage on mount
  useEffect(() => {
    const savedCollapsed = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    if (savedCollapsed !== null) {
      setIsCollapsed(savedCollapsed === 'true')
    }
  }, [])

  // 自动收起：当 forceCollapsed 为 true 时，自动收起侧边栏
  useEffect(() => {
    if (forceCollapsed) {
      setIsCollapsed(true)
    }
  }, [forceCollapsed])

  // Save collapsed state to localStorage when it changes
  useEffect(() => {
    if (!forceCollapsed) {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed))
    }
  }, [isCollapsed, forceCollapsed])

  // 统一的图标按钮样式
  const iconButtonClass = `
    flex items-center justify-center
    text-gray-500 hover:text-gray-700
    ${BUTTON_HOVER_EFFECTS}
    ${RADIUS_BUTTON}
    ${BUTTON_TRANSITION}
  `

  // 收起状态的展开按钮样式（圆形）
  const collapsedExpandButtonClass = `
    w-10 h-10 flex items-center justify-center
    bg-white ${RADIUS_CIRCLE}
    border border-gray-200 shadow-sm
    text-gray-400 hover:text-gray-600 hover:border-gray-300 hover:bg-gray-50
    ${BUTTON_TRANSITION}
    hover:scale-110 active:scale-95
  `

  if (isCollapsed) {
    return (
      <div className="relative w-0 h-full">
        <button
          onClick={() => setIsCollapsed(false)}
          className={`${collapsedExpandButtonClass} absolute top-1/2 -translate-y-1/2 left-2 z-20`}
          title={t('apps.chat.expandHistory')}
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    )
  }

  // Expanded state - full sidebar
  return (
    <div className="flex flex-col border-r border-gray-200 w-[260px] h-full min-h-0">
      {/* Header */}
      <div className={`flex items-center justify-between ${i18n.language === 'en-US' ? 'px-1.5 py-4' : 'px-4 py-4'}`}>
        <div className="flex items-center gap-1.5 min-w-0">
          <Clock className="w-5 h-5 text-gray-500 flex-shrink-0" />
          <h2 className={`font-bold text-gray-700 truncate ${
            i18n.language === 'en-US' ? 'text-base' : 'text-lg'
          }`}>
            {t('apps.chat.allConversations')}
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {/* New conversation button */}
          <button
            onClick={onNewConversation}
            disabled={isStreaming}
            className={`${iconButtonClass} w-10 h-10 ${
              isStreaming ? 'cursor-not-allowed opacity-50' : ''
            }`}
            title={isStreaming ? t('apps.chat.conversationInProgress') : t('apps.chat.newConversation')}
          >
            <Plus className="w-5 h-5" />
          </button>

          {/* Collapse button */}
          <button
            onClick={() => setIsCollapsed(true)}
            className={`${iconButtonClass} w-10 h-10`}
            title={t('apps.chat.collapseHistory')}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Conversation List */}
      <ConversationList
        currentConversationId={currentConversationId}
        onConversationSelect={onConversationSelect}
        onDeleteConversation={onDeleteConversation}
        isStreaming={isStreaming}
      />
    </div>
  )
}

export default ConversationHistorySidebar
