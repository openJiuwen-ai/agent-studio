/**
 * Chat Input Area Component
 * 统一的聊天输入区域组件
 */

import React from 'react'
import { useTranslation } from 'react-i18next'
import { Send, Loader2, Plus, Square } from 'lucide-react'
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
  onStopClick?: () => void  // 停止按钮点击事件（DeepSearch 运行中）
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

  // DeepSearch 服务状态
  deepsearchUnavailable?: boolean
  checkingDeepsearch?: boolean
  disableEnterKey?: boolean

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
  onStopClick,
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
  deepsearchUnavailable = false,
  checkingDeepsearch = false,
  className = '',
  inputStyle,
}) => {
  const { t } = useTranslation()

  // 判断是否可以发送消息
  const canSendMessage = selectedAgent && selectedModel && inputValue.trim() && !deepsearchUnavailable && !checkingDeepsearch

  // 判断是否显示停止按钮（streaming 状态且有 onStopClick 回调）
  const isStopMode = isStreaming && !!onStopClick

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
          isDisabled={isStreaming || !canSendMessage}
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
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              title={isStreaming ? t('apps.chat.conversationInProgress') : t('apps.chat.startNewConversation')}
            >
              <Plus className="w-5 h-5" />
            </button>
          )}

          {/* 发送/停止按钮 - 根据 streaming 状态切换 */}
          <button
            onClick={() => isStopMode ? onStopClick() : onPressEnter()}
            disabled={isStopMode ? false : !canSendMessage}
            className={`
              w-10 h-10 ${RADIUS_BUTTON} flex items-center justify-center
              transition-all duration-200 shrink-0
              ${
                isStopMode
                  ? 'bg-red-500 hover:bg-red-600 text-white cursor-pointer'  // 停止状态：红色
                  : checkingDeepsearch || deepsearchUnavailable
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : canSendMessage
                      ? 'bg-blue-500 hover:bg-blue-600 active:scale-95 text-white shadow-sm hover:shadow'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
              }
            `}
            title={
              checkingDeepsearch
                ? t('apps.chat.checkingDeepsearch')
                : isStreaming
                  ? t('apps.chat.stopDeepSearch')
                  : deepsearchUnavailable
                    ? t('apps.chat.deepsearchServiceDown')
                    : !selectedModel
                      ? t('apps.chat.selectModel')
                      : !selectedAgent
                        ? t('apps.chat.selectAgent')
                        : t('apps.chat.sendMessage')
            }
          >
            {checkingDeepsearch ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isStreaming ? (
              <Square className="w-5 h-5" />
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
