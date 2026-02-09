import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Message, TaskStatus, MessageType, LinkContent } from '../../../stores/useConversationStore';
import { useConversationStore } from '../../../stores/useConversationStore';
import {
  ChevronDown,
  ChevronRight,
  Circle,
  XCircle,
  Ban,
  Clock,
  ExternalLink,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { ReportMarkdown } from '@/pages/Apps/components/Markdown';
import ReportMessage from './ReportMessage';
import { TextContentCard } from './TextContentCard';
import { formatDuration } from '../utils/formatDuration';
import { IosSpinnerStyles, SpinnerDots } from '../utils/spinnerStyles';

interface TaskMessageProps {
  message: Message;
  depth?: number; // 嵌套深度，用于缩进
  onTaskClick?: (task: Message) => void; // 点击任务时的回调
}

// ===== 工具函数 =====

/**
 * 获取网站的favicon URL
 */
const getFaviconUrl = (url: string): string => {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return '';
  }
};

/**
 * 将连续的link类型消息分组为LinkSet
 */
const groupLinksIntoSets = (messages: Message[]): Message[][] => {
  const sets: Message[][] = [];
  let currentSet: Message[] = [];

  messages.forEach((msg) => {
    if (msg.type === MessageType.LINK) {
      currentSet.push(msg);
    } else {
      if (currentSet.length > 0) {
        sets.push(currentSet);
        currentSet = [];
      }
    }
  });

  if (currentSet.length > 0) {
    sets.push(currentSet);
  }

  return sets;
};

/**
 * 截断文本到指定长度
 */
const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 2) + '...';
};

// ===== 组件 =====

/**
 * LinkSet组件：渲染连续的link卡片组
 */
const LinkSet: React.FC<{
  links: Message[];
  onLinkClick: (link: Message) => void;
  t: (key: string, params?: any) => string;
}> = ({ links, onLinkClick, t }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const maxVisible = 6;
  const showExpandButton = links.length > maxVisible;
  const visibleLinks = isExpanded ? links : links.slice(0, maxVisible);

  return (
    <div className="flex flex-wrap gap-2 mt-2 mb-1 ml-2 mr-2">
      {visibleLinks.map((link) => {
        const linkData = link.content as LinkContent;
        const url = linkData?.url || '';
        const title = linkData?.title || link.title || t('apps.deepSearch.link');
        const isLocalDataset = url.startsWith('localdataset://result//');
        const faviconUrl = getFaviconUrl(url);

        return (
          <div
            key={link.id}
            className={`
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full flex-shrink-0
              bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200
              hover:from-blue-50 hover:to-indigo-50 hover:border-blue-200
              transition-all duration-200 group max-w-full
            `}
            onClick={(e) => {
              e.stopPropagation();
              if (isLocalDataset) {
                onLinkClick(link);
              } else {
                window.open(url, '_blank');
              }
            }}
          >
            {/* 图标 */}
            {faviconUrl ? (
              <img
                src={faviconUrl}
                alt=""
                className="w-4 h-4 flex-shrink-0"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            ) : (
              <span className="text-sm flex-shrink-0">{isLocalDataset ? '📚' : '📎'}</span>
            )}

            {/* 标题 */}
            <span className="text-xs text-gray-700 group-hover:text-blue-700 truncate max-w-[100px]">
              {truncateText(title, 15)}
            </span>

            {/* 外部链接图标 */}
            {!isLocalDataset && (
              <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-blue-500 flex-shrink-0" />
            )}
          </div>
        );
      })}

      {/* 展开/收起按钮 */}
      {showExpandButton && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-blue-50 hover:bg-blue-100 border border-blue-200 text-xs text-blue-700 font-medium transition-colors flex-shrink-0"
        >
          {isExpanded ? t('apps.deepSearch.collapse') : t('apps.deepSearch.expand', { count: links.length - maxVisible })}
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
      )}
    </div>
  );
};

/**
 * 子任务渲染组件
 * 根据子任务类型渲染不同的组件
 */
const ChildTaskRenderer: React.FC<{
  childTask: Message;
  depth: number;
  onTaskClick?: (task: Message) => void;
}> = ({ childTask, depth, onTaskClick }) => {
  switch (childTask.type) {
    case MessageType.TASK:
      return (
        <TaskMessage
          key={childTask.id}
          message={childTask}
          depth={depth}
          onTaskClick={onTaskClick}
        />
      );

    case MessageType.LINK:
      // LINK类型在LinkSet中统一处理，这里不单独渲染
      return null;

    case MessageType.TEXT: {
      // TEXT类型：使用TextContentCard显示title和content
      return (
        <TextContentCard
          key={childTask.id}
          message={childTask}
          depth={depth}
        />
      );
    }

    case MessageType.REPORT: {
      // REPORT类型：使用ReportMessage组件
      return (
        <ReportMessage
          key={childTask.id}
          message={childTask}
          depth={depth}
          onTaskClick={onTaskClick}
        />
      );
    }

    default:
      return null;
  }
};

/**
 * 任务消息组件（递归渲染）
 *
 * 显示规则：
 * 1. 顶部行：[进度标志] [title] [用时] [折叠标志]
 * 2. content模块：显示markdown格式的content
 * 3. 子Message模块：task/link/text类型分别处理
 * 4. 点击title或折叠标志切换折叠状态
 * 5. 点击text卡片打开右侧面板
 */
export const TaskMessage: React.FC<TaskMessageProps> = ({
  message,
  depth = 0,
  onTaskClick
}) => {
  const { t } = useTranslation();
  const getChildMessages = useConversationStore((state) => state.getChildMessages);

  /**
   * 翻译任务标题
   * 检测 "信息收集{number}" 模式并翻译，其他标题保持原样
   */
  const translateTaskTitle = (title: string | undefined): string => {
    if (!title) return '';

    // 检测 "信息收集1", "信息收集2" 等模式
    const match = title.match(/^信息收集(\d+)$/);
    if (match) {
      const index = match[1];
      return t('apps.deepSearch.informationCollection', { index });
    }

    // 其他标题保持原样
    return title;
  };

  // 判断是否为根节点
  const isRootNode = !message.parentMessageId;

  // 默认展开逻辑：根节点展开，子节点折叠
  const [isExpanded, setIsExpanded] = useState(isRootNode);

  // 获取子消息
  const childMessages = getChildMessages(message.id);
  const hasChildren = childMessages && childMessages.length > 0;

  // 将content转换为字符串（提前计算，用于判断是否显示折叠按钮）
  const contentString = useMemo(() => {
    if (typeof message.content === 'string') {
      return message.content;
    }
    return String(message.content || '');
  }, [message.content]);

  // 用于触发实时更新的状态（每秒更新）
  const [currentTime, setCurrentTime] = useState(Date.now());

  // 对于进行中的任务，每秒更新当前时间（未开始的任务不需要更新，因为不显示耗时）
  useEffect(() => {
    if (message.status !== TaskStatus.IN_PROGRESS) {
      // 非进行中的任务不需要定时器
      return;
    }

    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, [message.status]);

  // 计算耗时：根据状态动态计算
  const calculatedDuration = useMemo(() => {
    switch (message.status) {
      case TaskStatus.PENDING:
        // 未开始：不显示耗时
        return undefined;
      case TaskStatus.IN_PROGRESS:
        // 进行中：当前时间 - 创建时间，确保不为负数
        return Math.max(0, currentTime - message.createdAt);
      case TaskStatus.COMPLETED:
      case TaskStatus.FAILED:
      case TaskStatus.CANCELLED:
      case TaskStatus.UNKNOWN:
        // 已完成、失败、手动结束、未知：更新时间 - 创建时间，确保不为负数
        return Math.max(0, message.updatedAt - message.createdAt);
      default:
        return undefined;
    }
  }, [message.status, message.createdAt, message.updatedAt, currentTime]);

  // 格式化duration
  const formattedDuration = useMemo(() => formatDuration(calculatedDuration), [calculatedDuration]);

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
  }, [contentString, isExpanded]); // 监听内容变化和展开状态变化

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

  // 判断是否显示折叠标志（根节点不显示）
  // 只要有子消息或有content，就显示折叠按钮
  const showCollapseIcon = (hasChildren || contentString) && !isRootNode;

  // 获取状态图标
  const getStatusIcon = () => {
    switch (message.status) {
      case TaskStatus.PENDING:
        return <Circle size={16} className="text-gray-400 flex-shrink-0" />;
      case TaskStatus.IN_PROGRESS:
        // iOS风格小菊花：长椭圆形点组成的旋转圆圈
        return (
          <div className="flex-shrink-0 w-4 h-4 relative">
            <IosSpinnerStyles />
            <div className="ios-spinner">
              <SpinnerDots />
            </div>
          </div>
        );
      case TaskStatus.COMPLETED:
        // 绿底白勾（简单勾号，圆形）
        return (
          <div className="flex-shrink-0 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        );
      case TaskStatus.FAILED:
        return <XCircle size={16} className="text-red-500 flex-shrink-0" />;
      case TaskStatus.CANCELLED:
        return <Ban size={16} className="text-yellow-500 flex-shrink-0" />;
      case TaskStatus.UNKNOWN:
        // 橙色对勾（轻微提示）
        return (
          <div className="flex-shrink-0 w-4 h-4 rounded-full bg-orange-400 flex items-center justify-center" title={t('apps.deepSearch.statusUnknown')}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        );
      default:
        return <Circle size={16} className="text-gray-400 flex-shrink-0" />;
    }
  };

  // 获取title的样式
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

  // 处理折叠/展开切换
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isRootNode) {
      setIsExpanded(!isExpanded);
    }
  };

  // 处理title点击
  const handleTitleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!isRootNode) {
      setIsExpanded(!isExpanded);
    }
  };

  // 将子消息分组：task、link set、text(TEXT)、report(REPORT)
  const { taskMessages, linkSets, textMessages, reportMessages } = useMemo(() => {
    const tasks: Message[] = [];
    const links: Message[] = [];
    const texts: Message[] = [];
    const reports: Message[] = [];

    childMessages?.forEach((child) => {
      if (child.type === MessageType.TASK) {
        tasks.push(child);
      } else if (child.type === MessageType.LINK) {
        links.push(child);
      } else if (child.type === MessageType.TEXT) {
        texts.push(child);
      } else if (child.type === MessageType.REPORT) {
        reports.push(child);
      }
    });

    return {
      taskMessages: tasks,
      linkSets: groupLinksIntoSets(links),
      textMessages: texts,
      reportMessages: reports
    };
  }, [childMessages]);

  // 根据深度获取背景色和边框样式（灰色系，层级区分）
  const getDepthStyle = () => {
    const depthMod = depth % 4;
    switch (depthMod) {
      case 0:
        return 'bg-gray-50/50'; // 最浅
      case 1:
        return 'bg-gray-100/50'; // 浅灰
      case 2:
        return 'bg-gray-200/40'; // 中灰
      case 3:
        return 'bg-gray-300/30'; // 深灰
      default:
        return 'bg-gray-50/50';
    }
  };

  // 根据深度获取title字体大小（所有层级都比content大）
  const getTitleSize = () => {
    if (depth === 0) return 'text-lg'; // 18px
    if (depth === 1) return 'text-base'; // 16px
    return 'text-sm'; // 14px，所有底层都是14px，比content的12px大
  };

  return (
    <div className={`task-message py-1 ${getDepthStyle()}`}>
      {/* 任务行：[进度标志] [title + 用时] [折叠标志] */}
      <div className="flex items-center gap-2 py-2 pr-2 rounded transition-colors">
        {/* 进度标志 */}
        <div className="flex-shrink-0">{getStatusIcon()}</div>

        {/* 标题和用时容器 */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* 标题 - 可点击切换折叠 */}
          <span
            className={`font-bold truncate ${getTitleSize()} ${getTitleStyle()} ${
              !isRootNode && hasChildren ? 'cursor-pointer hover:bg-black/5 rounded px-1 -mx-1' : ''
            }`}
            onClick={handleTitleClick}
          >
            {translateTaskTitle(message.title) || t('apps.deepSearch.researchOutline')}
          </span>

          {/* 用时模块 */}
          {formattedDuration && (
            <div className="flex-shrink-0 flex items-center gap-1 text-xs text-gray-500 bg-white/60 backdrop-blur-sm px-2 py-0.5 rounded-full border border-gray-200/50">
              <Clock size={12} />
              <span>{formattedDuration}</span>
            </div>
          )}
        </div>

        {/* 流式指示器 */}
        {message.isStreaming && (
          <span className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        )}

        {/* 折叠标志 - 根节点不显示 */}
        {showCollapseIcon && (
          <div
            className="flex-shrink-0 w-5 h-5 flex items-center justify-center cursor-pointer hover:bg-black/10 rounded transition-colors"
            onClick={handleToggle}
          >
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-600" />
            ) : (
              <ChevronRight size={14} className="text-gray-600" />
            )}
          </div>
        )}
      </div>

      {/* 展开时的内容 */}
      {isExpanded && (
        <div className="pb-2">
          {/* content和子Message的容器 - 左侧灰色竖线，与进展标志居中对齐 */}
          <div className="border-l-2 border-gray-400 ml-2 mr-2 pl-2">
            {/* content模块 - Markdown渲染，统一白色背景 */}
            {contentString && (
              <div className="relative mt-1">
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
                    instanceId={`task-${message.id}`}
                  />
                </div>

                {/* 折叠/展开按钮 - 只在曾经溢出或当前溢出时显示 */}
                {(hasEverOverflowed || hasContentOverflow) && (
                  <button
                    onClick={toggleContentExpand}
                    className="absolute bottom-2 right-2 flex-shrink-0 flex items-center justify-center w-7 h-7 opacity-70 hover:opacity-100 bg-white/90 backdrop-blur-sm rounded-full border border-gray-300 shadow-sm hover:bg-white hover:border-gray-400 transition-all"
                    title={isContentExpanded ? t('apps.deepSearch.collapseContent') : t('apps.deepSearch.expandContent')}
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

            {/* 子Message模块 */}
            {(taskMessages.length > 0 || linkSets.length > 0 || textMessages.length > 0 || reportMessages.length > 0) && (
              <div className="mt-2">
              {/* Task类型子消息 */}
              {taskMessages.map((childTask, index) => (
                <div key={childTask.id} className={index < taskMessages.length - 1 ? 'border-b border-gray-300/50' : ''}>
                  <ChildTaskRenderer
                    childTask={childTask}
                    depth={depth + 1}
                    onTaskClick={onTaskClick}
                  />
                </div>
              ))}

              {/* Link类型子消息 - LinkSet */}
              {linkSets.map((linkSet, index) => (
                <LinkSet
                  key={`linkset-${index}`}
                  links={linkSet}
                  onLinkClick={(link) => onTaskClick?.(link)}
                  t={t}
                />
              ))}

              {/* TEXT类型子消息 */}
              {textMessages.map((childTask) => (
                <ChildTaskRenderer
                  key={childTask.id}
                  childTask={childTask}
                  depth={depth}
                  onTaskClick={onTaskClick}
                />
              ))}

              {/* REPORT类型子消息 */}
              {reportMessages.map((childTask) => (
                <ChildTaskRenderer
                  key={childTask.id}
                  childTask={childTask}
                  depth={depth}
                  onTaskClick={onTaskClick}
                />
              ))}
            </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskMessage;
