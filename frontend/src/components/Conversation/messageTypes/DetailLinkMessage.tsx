import React from 'react';
import { Message, LinkContent } from '../../../stores/useConversationStore';
import { ChevronRight, Eye } from 'lucide-react';

interface DetailLinkMessageProps {
  message: Message;
}

/**
 * 详情链接消息组件
 *
 * 用于显示：
 * 可点击打开右侧面板的详情链接
 */
export const DetailLinkMessage: React.FC<DetailLinkMessageProps> = ({ message }) => {
  const linkContent = message.content as LinkContent;

  if (!linkContent) {
    return null;
  }

  const { title, description, cardStyle = 'card' } = linkContent;

  const handleClick = () => {
    // TODO: 打开右侧面板显示详情
  };

  // 文字样式
  if (cardStyle === 'text') {
    return (
      <button
        onClick={handleClick}
        className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 text-sm"
      >
        {title || '查看详情'}
        <ChevronRight size={14} />
      </button>
    );
  }

  // 卡片样式（默认）
  return (
    <button
      onClick={handleClick}
      className="w-full text-left border border-blue-200 bg-blue-50 rounded-lg p-3 hover:bg-blue-100 hover:shadow-md transition-all flex items-center gap-3"
    >
      <div className="flex-shrink-0">
        <Eye size={18} className="text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-800">{title || '查看详细信息'}</h4>
        {description && (
          <p className="text-xs text-gray-600 mt-1 line-clamp-2">{description}</p>
        )}
      </div>
      <ChevronRight size={16} className="flex-shrink-0 text-gray-400" />
    </button>
  );
};

export default DetailLinkMessage;
