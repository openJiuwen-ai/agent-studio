import React from 'react';
import { Message } from '../../../stores/useConversationStore';
import { AlertCircle } from 'lucide-react';

interface ErrorMessageProps {
  message: Message;
}

/**
 * 错误消息组件
 *
 * 用于显示错误信息
 */
export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message }) => {
  // 安全地获取错误文本
  let errorText: string;

  if (typeof message.content === 'string') {
    errorText = message.content;
  } else if (typeof message.content === 'object' && message.content !== null) {
    // 如果是对象，尝试提取 text 字段
    const contentObj = message.content as Record<string, unknown>;
    errorText = (typeof contentObj.text === 'string' ? contentObj.text : null) || JSON.stringify(message.content);
  } else {
    errorText = String(message.content ?? '未知错误');
  }

  return (
    <div className="error-message bg-red-50 border border-red-200 rounded-lg p-3">
      <div className="flex items-start gap-2">
        <AlertCircle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          {message.title && (
            <h4 className="text-sm font-semibold text-red-800 mb-1">{message.title}</h4>
          )}
          <p className="text-sm text-red-700">{errorText}</p>
        </div>
      </div>
    </div>
  );
};

export default ErrorMessage;
