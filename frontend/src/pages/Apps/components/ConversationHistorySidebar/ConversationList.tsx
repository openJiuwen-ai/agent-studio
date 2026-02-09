import React, { useState, useEffect, useRef } from 'react'
import { MessageSquare } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useConversationStore } from '../../../../stores/useConversationStore'
import ConversationItem from './ConversationItem'
import type { ConversationListProps } from './types'
import type { Conversation } from '../../../../stores/useConversationStore'

/**
 * Custom scrollbar styles for the conversation list
 */
const SCROLLBAR_STYLES = `
  .conversation-scroll::-webkit-scrollbar {
    width: 6px;
  }
  .conversation-scroll::-webkit-scrollbar-track {
    background: transparent;
  }
  .conversation-scroll::-webkit-scrollbar-thumb {
    background-color: rgba(156, 163, 175, 0.3);
    border-radius: 3px;
  }
  .conversation-scroll::-webkit-scrollbar-thumb:hover {
    background-color: rgba(156, 163, 175, 0.5);
  }
`

const ConversationList: React.FC<ConversationListProps> = ({
  currentConversationId,
  onConversationSelect,
  onDeleteConversation,
  isStreaming,
}) => {
  const { t } = useTranslation()

  // 使用 useState 来缓存计算结果，避免无限循环
  const [conversations, setConversations] = useState<Conversation[]>([])
  const conversationsRef = useRef<Conversation[]>([])

  // 订阅 store 变化，手动比较后更新
  useEffect(() => {
    // 初始化：从 store 获取当前数据
    const initConversations = () => {
      const state = useConversationStore.getState()
      const { conversationsList, conversationsMap } = state

      const newConversations = conversationsList
        .map(id => conversationsMap.get(id))
        .filter((conv): conv is Conversation => conv !== undefined)
        .sort((a, b) => b.updatedAt - a.updatedAt)

      conversationsRef.current = newConversations
      setConversations(newConversations)
    }

    // 立即初始化
    initConversations()

    const unsub = useConversationStore.subscribe((state) => {
      const { conversationsList, conversationsMap } = state

      // 计算新的 conversations 数组
      const newConversations = conversationsList
        .map(id => conversationsMap.get(id))
        .filter((conv): conv is Conversation => conv !== undefined)
        .sort((a, b) => b.updatedAt - a.updatedAt)

      // 深度比较：只在数据真正变化时才更新
      if (newConversations.length !== conversationsRef.current.length) {
        conversationsRef.current = newConversations
        setConversations(newConversations)
        return
      }

      // 检查每个 conversation 是否有变化
      let hasChanged = false
      for (let i = 0; i < newConversations.length; i++) {
        const newConv = newConversations[i]
        const oldConv = conversationsRef.current[i]
        if (!oldConv || newConv.updatedAt !== oldConv.updatedAt || newConv.title !== oldConv.title) {
          hasChanged = true
          break
        }
      }

      if (hasChanged) {
        conversationsRef.current = newConversations
        setConversations(newConversations)
      }
    })

    return unsub
  }, [])

  return (
    <>
      <style>{SCROLLBAR_STYLES}</style>
      <div className="flex-1 overflow-y-auto conversation-scroll px-2 py-3 min-h-0">
        {conversations.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full">
            <MessageSquare className="w-12 h-12 opacity-30 mb-3" />
            <p className="text-sm">{t('apps.chat.noConversationHistory')}</p>
          </div>
        ) : (
          // Conversation list
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === currentConversationId}
                onClick={() => onConversationSelect(conversation.id)}
                onDelete={onDeleteConversation}
                isStreaming={isStreaming}
              />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

export default ConversationList
