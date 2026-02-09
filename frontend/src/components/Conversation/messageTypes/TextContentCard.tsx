import React, { useMemo, useEffect, useRef, useState } from 'react';
import { Message, TaskStatus } from '../../../stores/useConversationStore';
import { ReportMarkdown } from '@/pages/Apps/components/Markdown';
import { Minimize2, Maximize2 } from 'lucide-react';

interface TextContentCardProps {
  message: Message;
  depth: number;
}

/**
 * TextContentCard组件：显示类型为TEXT的Task message
 * 包含title和content两部分
 */
export const TextContentCard: React.FC<TextContentCardProps> = ({ message, depth }) => {
  // 获取title字体大小
  const getTitleSize = () => {
    if (depth === 0) return 'text-lg'; // 18px
    if (depth === 1) return 'text-base'; // 16px
    return 'text-sm'; // 14px
  };

  // 获取title样式
  const getTitleStyle = () => {
    switch (message.status) {
      case TaskStatus.PENDING:
        return 'text-gray-400';
      case TaskStatus.IN_PROGRESS:
        return 'text-gray-800';
      case TaskStatus.COMPLETED:
      case TaskStatus.UNKNOWN:
        return 'text-gray-900 font-semibold';
      case TaskStatus.FAILED:
        return 'text-red-600 font-semibold';
      case TaskStatus.CANCELLED:
        return 'text-gray-800';
      default:
        return 'text-gray-400';
    }
  };

  // 转换content为字符串
  const contentString = useMemo(() => {
    if (typeof message.content === 'string') {
      return message.content;
    }
    return String(message.content || '');
  }, [message.content]);

  // Content 展开/折叠功能
  const contentRef = useRef<HTMLDivElement>(null);
  const [isContentExpanded, setIsContentExpanded] = useState(false);
  const [hasContentOverflow, setHasContentOverflow] = useState(false);
  const [hasEverOverflowed, setHasEverOverflowed] = useState(false);

  // 检测内容是否溢出（只在折叠状态下检测，展开后保持状态）
  useEffect(() => {
    const checkOverflow = () => {
      if (contentRef.current && !isContentExpanded) {
        const hasOverflow = contentRef.current.scrollHeight > contentRef.current.clientHeight;
        setHasContentOverflow(hasOverflow);
        if (hasOverflow) {
          setHasEverOverflowed(true);
        }
      }
    };

    // 多次检测，确保内容渲染完成
    const timers = [
      setTimeout(checkOverflow, 0),
      setTimeout(checkOverflow, 100),
      setTimeout(checkOverflow, 300),
      setTimeout(checkOverflow, 500),
      setTimeout(checkOverflow, 1000),
    ];

    // 使用 ResizeObserver 监听内容变化
    let resizeObserver: ResizeObserver | null = null;
    // 延迟创建 ResizeObserver，确保 DOM 已渲染
    const observerTimer = setTimeout(() => {
      if (contentRef.current && typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => {
          // 只在折叠状态下检测
          if (!isContentExpanded) {
            checkOverflow();
          }
        });
        resizeObserver.observe(contentRef.current);
        // 创建后立即检测一次
        checkOverflow();
      }
    }, 0);

    // 监听窗口大小变化
    window.addEventListener('resize', checkOverflow);

    return () => {
      clearTimeout(observerTimer);
      timers.forEach(timer => clearTimeout(timer));
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      window.removeEventListener('resize', checkOverflow);
    };
  }, [contentString]); // 只在内容变化时重新设置监听

  // 切换内容展开状态
  const toggleContentExpand = () => {
    setIsContentExpanded(!isContentExpanded);
    // 收起时重新检测溢出状态
    if (isContentExpanded) {
      setTimeout(() => {
        if (contentRef.current) {
          const hasOverflow = contentRef.current.scrollHeight > contentRef.current.clientHeight;
          setHasContentOverflow(hasOverflow);
        }
      }, 50);
    }
  };

  return (
    <div className="mt-2">
      {/* Title部分 */}
      {message.title && (
        <div className={`font-bold ${getTitleSize()} ${getTitleStyle()} ml-2 mr-2 mb-1`}>
          {message.title}
        </div>
      )}

      {/* Content部分 - 与task的content模块一样 */}
      {contentString && (
        <div className="relative ml-2 mr-2">
          <div
            ref={contentRef}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-200 overflow-y-auto shadow-sm"
            style={{
              maxHeight: isContentExpanded ? 'none' : '120px', // 约5行的高度
              lineHeight: '1.5'
            }}
          >
            <ReportMarkdown
              content={contentString}
              className="prose prose-xs max-w-none prose-p:text-gray-600 prose-headings:text-gray-900 prose-p:my-1 prose-headings:mt-2 prose-headings:mb-1 prose-pre:overflow-x-auto prose-pre:max-w-full"
              instanceId={`text-${message.id}`}
            />
          </div>

          {/* 折叠/展开按钮 - 只在曾经溢出或当前溢出时显示 */}
          {(hasEverOverflowed || hasContentOverflow) && (
            <button
              onClick={toggleContentExpand}
              className="absolute bottom-2 right-2 flex-shrink-0 flex items-center justify-center w-7 h-7 opacity-70 hover:opacity-100 bg-white/90 backdrop-blur-sm rounded-full border border-gray-300 shadow-sm hover:bg-white hover:border-gray-400 transition-all"
              title={isContentExpanded ? '折叠内容' : '展开内容'}
            >
              {isContentExpanded ? (
                <Minimize2 size={14} className="text-gray-600" />
              ) : (
                <Maximize2 size={14} className="text-gray-600" />
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default TextContentCard;
