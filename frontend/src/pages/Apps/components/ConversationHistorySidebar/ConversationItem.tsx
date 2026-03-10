import React from 'react'
import { useTranslation } from 'react-i18next'
import { Trash2 } from 'lucide-react'
import { RADIUS_MEDIUM, BUTTON_HOVER_EFFECTS, BUTTON_TRANSITION } from '../../constants/styles'
import type { ConversationItemProps } from './types'

/**
 * Format timestamp to human-readable string
 * - Today: "14:30"
 * - Yesterday: "昨天" / "Yesterday"
 * - Older: "1月15日" / "Jan 15"
 */
function formatTimestamp(timestamp: number, t: (key: string) => string, locale: string): string {
  const now = new Date()
  const date = new Date(timestamp)
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    // Today - show time
    return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', hour12: false })
  } else if (diffDays === 1) {
    // Yesterday
    return t('apps.chat.yesterday')
  } else {
    // Older - show date
    return date.toLocaleDateString(locale, { month: 'numeric', day: 'numeric' })
  }
}

/**
 * Truncate title to 50 characters with "..." suffix
 */
function truncateTitle(title: string, maxLength: number = 50): string {
  if (title.length <= maxLength) return title
  return title.slice(0, maxLength) + '...'
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onClick,
  onDelete,
  isStreaming,
}) => {
  const { t, i18n } = useTranslation()

  const handleClick = () => {
    if (!isStreaming) {
      onClick()
    }
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation() // 阻止事件冒泡，避免触发对话选择
    if (!isStreaming) {
      // 二次确认
      const confirmed = window.confirm(t('apps.chat.deleteConfirm', { title: conversation.title }))
      if (confirmed) {
        await onDelete(conversation.id)
      }
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`
        flex items-center justify-between px-3 py-2 ${RADIUS_MEDIUM}
        ${BUTTON_TRANSITION} group
        ${isActive
          ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
          : `bg-transparent ${BUTTON_HOVER_EFFECTS} text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700`
        }
        ${isStreaming ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
      `}
      title={isStreaming ? t('apps.chat.conversationInProgress') : conversation.title}
    >
      <div className="flex-1 min-w-0">
        {/* Title */}
        <div className={`text-sm font-medium truncate ${isActive ? 'text-gray-900 dark:text-gray-100' : 'text-gray-700 dark:text-gray-300'}`}>
          {truncateTitle(conversation.title)}
        </div>
        {/* Timestamp */}
        <div className={`text-xs mt-0.5 ${isActive ? 'text-gray-500 dark:text-gray-400' : 'text-gray-400 dark:text-gray-500'}`}>
          {formatTimestamp(conversation.updatedAt, t, i18n.language)}
        </div>
      </div>

      {/* Delete button - show on hover */}
      <button
        onClick={handleDelete}
        disabled={isStreaming}
        className={`
          opacity-0 group-hover:opacity-100
          flex items-center justify-center w-7 h-7 ml-2
          rounded-md
          text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
          transition-all duration-200
          ${isStreaming ? 'cursor-not-allowed' : 'cursor-pointer'}
        `}
        title={t('apps.chat.deleteConversation')}
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}

export default ConversationItem
