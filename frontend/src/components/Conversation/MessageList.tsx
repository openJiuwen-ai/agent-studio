import React, { useEffect, useRef } from 'react';
import { useConversationStore } from '../../stores/useConversationStore';
import { UserMessageItem } from './UserMessageItem';
import { SystemMessageItem } from './SystemMessageItem';
import { ErrorBoundary } from './ErrorBoundary';

/**
 * 消息列表组件
 *
 * 功能：
 * 1. 获取当前对话的 MessageItems 列表
 * 2. 根据isUser判断渲染UserMessageItem还是SystemMessageItem（兼容历史数据）
 * 3. 监听父容器滚动，自动滚动到底部
 */
export const MessageList: React.FC = () => {
  const messageItemsList = useConversationStore(state => state.getCurrentMessageItems());
  const getMessageItemsIsUser = useConversationStore(state => state.getMessageItemsIsUser);
  const containerRef = useRef<HTMLDivElement>(null);

  // 监听messageItemsList变化，滚动到最新消息
  useEffect(() => {
    // 延迟一帧，确保DOM已更新
    const timer = setTimeout(() => {
      if (containerRef.current) {
        containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [messageItemsList.length]);

  return (
    <div className="px-6 py-4">
      <div ref={containerRef}>
        {messageItemsList.length === 0 ? (
          // 空状态
          <div className="flex items-center justify-center h-full">
            <p>开始对话吧...</p>
          </div>
        ) : (
          // 消息列表 - 使用 Error Boundary 包裹每个消息项
          <div className="space-y-4">
            {messageItemsList.map((messageItems) => (
              <ErrorBoundary key={messageItems.id}>
                <div>
                  {getMessageItemsIsUser(messageItems) ? (
                    <UserMessageItem messageItems={messageItems} />
                  ) : (
                    <SystemMessageItem messageItems={messageItems} />
                  )}
                </div>
              </ErrorBoundary>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageList;
