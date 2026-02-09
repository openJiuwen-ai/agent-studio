import React from 'react';
import { Message, LinkContent } from '../../../stores/useConversationStore';
import { ExternalLink, FileText, Globe } from 'lucide-react';

interface LinkMessageProps {
  message: Message;
}

/**
 * 外部链接消息组件
 *
 * 用于显示：
 * collector_info_retrieval - 搜索结果
 *
 * 支持两种展示样式：
 * 1. text - 文字样式链接
 * 2. card - 小卡片样式链接
 */
export const LinkMessage: React.FC<LinkMessageProps> = ({ message }) => {
  const linkContent = message.content as LinkContent;

  if (!linkContent) {
    return null;
  }

  const { url, title, query, description, source, publishTime, cardStyle = 'card' } = linkContent;

  // 如果没有URL，显示为普通文本
  if (!url) {
    return (
      <div className="text-sm text-gray-700">
        {title || query || '未知链接'}
      </div>
    );
  }

  // 判断是web还是local
  const isWeb = !url.startsWith('localdataset://');
  const displaySource = source || (isWeb ? 'web' : 'local');

  // 文字样式链接
  if (cardStyle === 'text') {
    return (
      <div className="link-message">
        <a
          href={isWeb ? url : undefined}
          target={isWeb ? '_blank' : undefined}
          rel={isWeb ? 'noopener noreferrer' : undefined}
          className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 text-sm"
        >
          {title}
          {isWeb && <ExternalLink size={14} />}
        </a>
        {query && (
          <div className="text-xs text-gray-500 mt-1">搜索词: {query}</div>
        )}
        {description && (
          <div className="text-xs text-gray-500 mt-1">{description}</div>
        )}
      </div>
    );
  }

  // 卡片样式链接（默认）
  return (
    <div className="link-message">
      <a
        href={isWeb ? url : undefined}
        target={isWeb ? '_blank' : undefined}
        rel={isWeb ? 'noopener noreferrer' : undefined}
        className="block border border-gray-200 rounded-lg p-3 hover:border-blue-300 hover:shadow-md transition-all"
      >
        {/* 标题和图标 */}
        <div className="flex items-start gap-2">
          <div className="flex-shrink-0 mt-1">
            {displaySource === 'web' ? (
              <Globe size={16} className="text-blue-500" />
            ) : (
              <FileText size={16} className="text-green-500" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-gray-800 hover:text-blue-600 line-clamp-2">
              {title}
            </h4>
          </div>
          {isWeb && <ExternalLink size={14} className="flex-shrink-0 text-gray-400" />}
        </div>

        {/* 搜索词 */}
        {query && (
          <p className="text-xs text-blue-600 mt-2 line-clamp-1">
            搜索: {query}
          </p>
        )}

        {/* 描述 */}
        {description && (
          <p className="text-xs text-gray-600 mt-2 line-clamp-2">{description}</p>
        )}

        {/* 元数据 */}
        <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
          <span className="capitalize">
            {displaySource === 'web' ? '网页' : '知识库'}
          </span>
          {publishTime && (
            <span>{new Date(publishTime).toLocaleDateString()}</span>
          )}
          <span className="text-gray-300 truncate max-w-[200px]">{url}</span>
        </div>
      </a>
    </div>
  );
};

export default LinkMessage;
