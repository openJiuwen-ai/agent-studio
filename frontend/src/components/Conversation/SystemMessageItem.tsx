import React from 'react';
import { useTranslation } from 'react-i18next';
import { MessageItems, Message, MessageType, TaskStatus } from '../../stores/useConversationStore';
import { useConversationStore } from '../../stores/useConversationStore';
import { TextMessage } from './messageTypes/TextMessage';
import { LinkMessage } from './messageTypes/LinkMessage';
import { DetailLinkMessage } from './messageTypes/DetailLinkMessage';
import { TaskMessage } from './messageTypes/TaskMessage';
import ReportMessage from './messageTypes/ReportMessage';
import { ErrorMessage } from './messageTypes/ErrorMessage';
import { InterruptMessage } from './messageTypes/InterruptMessage';

interface SystemMessageItemProps {
  messageItems: MessageItems;
}

/**
 * 系统消息组件
 *
 * 显示规则：
 * 1. 显示在MessageBox左侧
 * 2. messages会依次往下显示，都在同一个消息框内
 * 3. 如果MessageItems还在进行中，最后的message会跟着数据更新显示
 * 4. 之前的message不会变化
 */
export const SystemMessageItem: React.FC<SystemMessageItemProps> = ({ messageItems }) => {
  const { t } = useTranslation();
  const getMessageById = useConversationStore(state => state.getMessageById);
  const getMessageItemsIsUser = useConversationStore(state => state.getMessageItemsIsUser);
  const { messagesIds, status } = messageItems;

  // 判断是否正在进行中
  const isInProgress = status === TaskStatus.IN_PROGRESS;

  // 判断是否是用户消息（兼容历史数据）
  const isUserMessage = getMessageItemsIsUser(messageItems);

  // 通过 messagesIds 获取实际的 Message 对象
  const messages = messagesIds
    .map(msgId => getMessageById(msgId))
    .filter((msg): msg is Message => msg !== undefined);

  if (!messagesIds || !Array.isArray(messagesIds)) {
    console.error('[SystemMessageItem] Invalid messagesIds:', messagesIds);
    return <div className="text-red-500">{t('apps.deepSearch.messageDataError')}</div>;
  }

  try {
    // ===== 用户消息：简单显示，和默认模式一样 =====
    if (isUserMessage) {
      if (messages.length === 0) {
        console.warn('[SystemMessageItem] User message has no content!');
        return null;
      }

      const userContent = messages[0].content;
      // 确保content是字符串
      const displayContent = typeof userContent === 'string' ? userContent : String(userContent || '');

      return (
        <div className="flex justify-end mb-4">
          <div className="flex flex-col items-end max-w-[100%]">
            <div className="w-fit rounded-2xl px-5 py-3 text-gray-900 bg-gray-100 overflow-hidden">
              <p className="text-base leading-relaxed m-0">{displayContent}</p>
            </div>
          </div>
        </div>
      );
    }

    // ===== AI消息：显示系统任务消息 =====
    // 过滤掉作为子任务的消息（有 parentMessageId 的消息）
    // 这些消息会在其父任务的TaskMessage组件中递归渲染
    const topLevelMessages = messages.filter(message => {
      if (message.parentMessageId) {
        return false;
      }
      return true;
    });

    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[90%] bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200 overflow-x-hidden">
          {/* 消息列表 */}
          {topLevelMessages.map((message, index) => {
            
            // 判断是否是最后一个进行中的消息
            const isLastStreaming = isInProgress && index === topLevelMessages.length - 1 && message.isStreaming;

            return (
              <div key={message.id} className="mb-3 last:mb-0">
                {/* 根据消息类型渲染不同的组件 */}
                <MessageRenderer message={message} isStreaming={isLastStreaming} t={t} />

                {/* 消息分隔线（除了最后一个消息） */}
                {index < topLevelMessages.length - 1 && (
                  <div className="border-t border-gray-100 my-2"></div>
                )}
              </div>
            );
          })}

        {/* 状态指示器 */}
        <div className="flex items-center justify-between mt-2">
          {isInProgress && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-75"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse delay-150"></div>
              </div>
              <span>{t('apps.chat.generating')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
    );
  } catch (error) {
    console.error('[SystemMessageItem] Render error:', error, 'messages:', messages);
    return <div className="text-red-500 p-4 border border-red-500">{t('apps.deepSearch.renderError')}: {error instanceof Error ? error.message : String(error)}</div>;
  }
};

interface MessageRendererProps {
  message: Message;
  isStreaming?: boolean;
  t: (key: string, params?: any) => string;
}

const MessageRenderer: React.FC<MessageRendererProps> = ({ message, isStreaming = false, t }) => {
  const setSelectedResultMessageId = useConversationStore(state => state.setSelectedResultMessageId);
  const selectedResultMessageId = useConversationStore(state => state.selectedResultMessageId);

  // 处理任务点击 - 如果点击的是当前已选中的消息，则关闭面板
  const handleTaskClick = (task: Message) => {
    if (selectedResultMessageId === task.id) {
      // 点击同一个消息，关闭面板
      setSelectedResultMessageId(null);
    } else {
      // 点击不同消息，打开面板
      setSelectedResultMessageId(task.id);
    }
  };

  try {
    switch (message.type) {
      case MessageType.REPORT:
        return <ReportMessage message={message} onTaskClick={handleTaskClick} />;

      case MessageType.LINK:
        return <LinkMessage message={message} />;

      case MessageType.DETAIL_LINK:
        return <DetailLinkMessage message={message} />;

      case MessageType.TASK:
        return <TaskMessage message={message} onTaskClick={handleTaskClick} />;

    case MessageType.ERROR:
      return <ErrorMessage message={message} />;

    case MessageType.INTERRUPT:
      return <InterruptMessage message={message} />;

    default:
      // 默认渲染为文本消息
      return <TextMessage message={message} isStreaming={isStreaming} />;
  }
  } catch (error) {
    console.error('MessageRenderer error:', error, message);
    return (
      <div style={{ padding: '16px', border: '1px solid red', borderRadius: '8px', marginBottom: '8px' }}>
        <div style={{ color: 'red', fontWeight: 'bold' }}>{t('apps.deepSearch.renderError')}</div>
        <div style={{ fontSize: '12px' }}>
          type: {message.type}, id: {message.id}
        </div>
      </div>
    );
  }
};

export default SystemMessageItem;
