import React from 'react';
import { MessageItems, useConversationStore } from '../../stores/useConversationStore';
import ReactMarkdown from 'react-markdown';

interface UserMessageItemProps {
  messageItems: MessageItems;
}

/**
 * 用户消息组件
 *
 * 显示规则：
 * 1. 显示在MessageBox右侧
 * 2. 蓝色背景（bg-blue-50）
 * 3. messagesIds长度==1，messagesIds[0]对应的消息content就是提问内容
 * 4. 以markdown方式显示
 */
export const UserMessageItem: React.FC<UserMessageItemProps> = ({ messageItems }) => {
  const getMessageById = useConversationStore(state => state.getMessageById);

  // 用户消息只有一个message
  const messageId = messageItems.messagesIds[0];
  const message = messageId ? getMessageById(messageId) : undefined;

  if (!message) {
    return null;
  }

  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[80%] bg-blue-50 rounded-lg px-4 py-2 shadow-sm">
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{message.content as string}</ReactMarkdown>
        </div>
        {/* 可选：显示时间 */}
        <div className="text-xs text-gray-400 mt-1 text-right">
          {new Date(messageItems.createdAt).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};

export default UserMessageItem;
