import React from 'react';
import { Message } from '../../../stores/useConversationStore';
import { ReportMarkdown } from '@/pages/Apps/components/Markdown';

interface TextMessageProps {
  message: Message;
  isStreaming?: boolean;
}

/**
 * 普通文本消息组件
 *
 * 用于显示：
 * 1. entry - 简单问题的回答
 * 2. generate_questions - 生成的问题列表
 * 3. sub_reporter - 章节子报告内容
 * 4. collector_summary - 研究步骤总结
 * 5. end - 最终报告内容
 */
export const TextMessage: React.FC<TextMessageProps> = ({ message, isStreaming = false }) => {
  // 安全地获取 content 字符串
  let content: string;

  if (typeof message.content === 'string') {
    content = message.content;
  } else if (typeof message.content === 'object' && message.content !== null) {
    // 如果是对象，转换为 JSON 字符串
    content = JSON.stringify(message.content, null, 2);
    console.warn('[TextMessage] Received object content, converted to JSON:', message.id);
  } else {
    // 其他类型（number, boolean, null, undefined）转为字符串
    content = String(message.content ?? '');
    console.warn('[TextMessage] Converted non-string content:', typeof message.content, message.id);
  }

  return (
    <div className="text-message">
      {/* 如果有标题，显示标题 */}
      {message.title && (
        <h3 className="text-lg font-semibold mb-2 text-gray-800">{message.title}</h3>
      )}

      {/* Markdown内容 */}
      <ReportMarkdown content={content} instanceId={`message-${message.id}`} />

      {/* 流式状态指示 */}
      {isStreaming && (
        <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse align-middle"></span>
      )}
    </div>
  );
};

export default TextMessage;
