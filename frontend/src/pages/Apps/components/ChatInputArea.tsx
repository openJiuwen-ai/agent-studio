/**
 * Chat Input Area Component
 * 统一的聊天输入区域组件
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { Send, Loader2, Plus } from 'lucide-react'
import MessageInput, { MessageInputRef } from './MessageInput'
import { MentionItem } from './MentionPicker'
import AgentSelectionPill from './AgentSelectionPill'
import { ModelSelectButton, TriggerButtons } from './InputButtons'
import { RADIUS_BUTTON } from '../constants/styles'

export interface ChatInputAreaProps {
  // 输入相关
  inputValue: string
  onInputChange: (value: string) => void
  onPressEnter: () => void
  inputRef: React.RefObject<MessageInputRef | null>
  isStreaming?: boolean

  // 智能体相关
  selectedAgent: MentionItem | null
  onAgentSelect: (agent: MentionItem) => void
  onAgentConfig: () => void
  onAgentDeselect: () => void
  agents: MentionItem[]

  // 资源相关
  onResourceSelect: (resource: MentionItem) => void
  resources: MentionItem[]
  onFileUpload: (files: FileList) => void

  // 模型相关
  selectedModel: string
  modelsLoading: boolean
  models: string[]
  onModelClick: () => void
  modelButtonRef: React.RefObject<HTMLButtonElement | null>

  // 新对话
  onNewConversation?: () => void

  // 样式
  className?: string
  inputStyle?: React.CSSProperties
}

const ChatInputArea: React.FC<ChatInputAreaProps> = ({
  inputValue,
  onInputChange,
  onPressEnter,
  inputRef,
  isStreaming = false,
  selectedAgent,
  onAgentSelect,
  onAgentConfig,
  onAgentDeselect,
  agents,
  onResourceSelect,
  resources,
  onFileUpload,
  selectedModel,
  modelsLoading,
  models,
  onModelClick,
  modelButtonRef,
  onNewConversation,
  className = '',
  inputStyle,
}) => {
  const { t } = useTranslation()
  return (
    <div className={className}>
      {/* 智能体选择悬浮框 */}
      {selectedAgent && (
        <div className="mb-3">
          <AgentSelectionPill
            agent={selectedAgent}
            onConfig={onAgentConfig}
            onDeselect={onAgentDeselect}
          />
        </div>
      )}

      <div className="relative">
        <MessageInput
          ref={inputRef}
          value={inputValue}
          onChange={onInputChange}
          placeholder={selectedAgent ? t('apps.chat.sendToAgent', { name: selectedAgent.name }) : t('apps.chat.typeAtSelectAgent')}
          agents={agents}
          resources={resources}
          onAgentSelect={onAgentSelect}
          onResourceSelect={onResourceSelect}
          onFileUpload={onFileUpload}
          onPressEnter={onPressEnter}
          className="w-full"
          style={inputStyle}
        />

        {/* 左侧 @ 和 # 按钮 */}
        <div className="absolute left-2 bottom-3">
          <TriggerButtons
            onAtClick={() => inputRef.current?.triggerPicker('@')}
            onHashClick={() => inputRef.current?.triggerPicker('#')}
          />
        </div>

        {/* 右侧模型选择、新对话和发送按钮 */}
        <div className="absolute right-2 bottom-3 flex items-center gap-2">
          <ModelSelectButton
            selectedModel={selectedModel}
            isLoading={modelsLoading}
            models={models}
            onClick={onModelClick}
            buttonRef={modelButtonRef}
          />

          {/* 新对话按钮 */}
          {onNewConversation && (
            <button
              onClick={onNewConversation}
              disabled={isStreaming}
              className={`w-10 h-10 flex items-center justify-center rounded-full transition-all duration-200 shrink-0 ${
                isStreaming
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
              title={isStreaming ? t('apps.chat.conversationInProgress') : t('apps.chat.startNewConversation')}
            >
              <Plus className="w-5 h-5" />
            </button>
          )}

          {/* 发送按钮 - 在发送中时显示灰色禁用状态 */}
          <button
            onClick={onPressEnter}
            disabled={!selectedAgent || !selectedModel || !inputValue.trim() || isStreaming}
            className={`
              w-10 h-10 ${RADIUS_BUTTON} flex items-center justify-center
              transition-all duration-200 shrink-0
              ${
                isStreaming
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : selectedAgent && selectedModel && inputValue.trim()
                    ? 'bg-blue-500 hover:bg-blue-600 active:scale-95 text-white shadow-sm hover:shadow'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }
            `}
            title={
              isStreaming
                ? t('apps.chat.conversationInProgress')
                : !selectedModel
                  ? t('apps.chat.selectModel')
                  : !selectedAgent
                    ? t('apps.chat.selectAgent')
                    : t('apps.chat.sendMessage')
            }
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatInputArea
