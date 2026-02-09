import React, { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Message, TaskStatus, MessageType, isFinalReportMessage } from '../../../stores/useConversationStore';
import { useConversationStore } from '../../../stores/useConversationStore';
import {
  ChevronDown,
  ChevronRight,
  Circle,
  XCircle,
  Ban,
  FileText,
  Clock,
} from 'lucide-react';
import DeepSearchReportCard from './DeepSearchReportCard';
import { TextContentCard } from './TextContentCard';
import { formatDuration } from '../utils/formatDuration';
import { IosSpinnerSmallStyles, LoadingDotStyles, SpinnerDots } from '../utils/spinnerStyles';
import { formatReportTitleForDisplay } from '@/utils/reportUtils';

interface ReportMessageProps {
  message: Message;
  depth?: number; // 嵌套深度，用于缩进
  onTaskClick?: (task: Message) => void; // 点击报告时的回调
}

// ===== 组件 =====

/**
 * Report类型子消息卡片组件（用于REPORT类型）
 * 根据状态显示不同的字样、标志，并控制点击行为
 * 支持耗时显示（非最终报告）
 */
const ReportCard: React.FC<{
  message: Message;
  onClick: () => void;
  duration: string | null;
  t: (key: string, params?: any) => string;
}> = ({ message, onClick, duration, t }) => {
  // 根据状态获取配置
  const getStatusConfig = () => {
    switch (message.status) {
      case TaskStatus.PENDING:
        return {
          // 待开始：灰色主题，不可点击
          statusText: t('apps.deepSearch.status.pending'),
          statusIcon: <Circle size={14} className="text-gray-400" />,
          bgGradient: 'from-gray-50 via-gray-50 to-gray-100',
          borderColor: 'border-gray-200/50',
          iconBg: 'bg-gradient-to-br from-gray-300 to-gray-400',
          iconColor: 'text-white',
          hoverClass: '',
          cursorClass: 'cursor-not-allowed',
          textColor: 'text-gray-500',
          showArrow: false,
        };
      case TaskStatus.IN_PROGRESS:
        return {
          // 进行中：灰色主题，旋转小菊花，不可点击
          statusText: (
            <span className="flex items-center gap-0.5">
              {t('apps.deepSearch.status.inProgress')}
              <span className="flex gap-0.5 ml-0.5">
                <LoadingDotStyles />
                <span className="loading-dot inline-block w-1 h-1 bg-gray-600 rounded-full"></span>
                <span className="loading-dot inline-block w-1 h-1 bg-gray-600 rounded-full"></span>
                <span className="loading-dot inline-block w-1 h-1 bg-gray-600 rounded-full"></span>
              </span>
            </span>
          ),
          statusIcon: (
            <div className="flex-shrink-0 w-3.5 h-3.5 relative">
              <IosSpinnerSmallStyles />
              <div className="ios-spinner-small">
                <SpinnerDots size="small" />
              </div>
            </div>
          ),
          bgGradient: 'from-gray-50 via-gray-50 to-gray-100',
          borderColor: 'border-gray-200/50',
          iconBg: 'bg-gradient-to-br from-gray-300 to-gray-400',
          iconColor: 'text-white',
          hoverClass: '',
          cursorClass: 'cursor-not-allowed',
          textColor: 'text-gray-600',
          showArrow: false,
        };
      case TaskStatus.COMPLETED:
        return {
          // 已完成：蓝色主题，可点击打开右面板
          statusText: t('apps.deepSearch.status.completed'),
          statusIcon: (
            <div className="flex-shrink-0 w-3.5 h-3.5 rounded-full bg-blue-500 flex items-center justify-center">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          ),
          bgGradient: 'from-blue-50 via-indigo-50 to-cyan-50',
          borderColor: 'border-blue-200/50 hover:border-blue-300/60',
          iconBg: 'bg-gradient-to-br from-blue-400 to-indigo-500',
          iconColor: 'text-white',
          hoverClass: 'hover:scale-[1.01] hover:shadow-md hover:shadow-blue-500/10',
          cursorClass: 'cursor-pointer',
          textColor: 'text-blue-700',
          titleColor: 'text-gray-900',
          showArrow: true,
        };
      case TaskStatus.FAILED:
        return {
          // 失败：红色主题，不可点击
          statusText: t('apps.deepSearch.status.failed'),
          statusIcon: <XCircle size={14} className="text-red-500" />,
          bgGradient: 'from-red-50 via-red-50 to-pink-50',
          borderColor: 'border-red-200/50',
          iconBg: 'bg-gradient-to-br from-red-400 to-red-500',
          iconColor: 'text-white',
          hoverClass: '',
          cursorClass: 'cursor-not-allowed',
          textColor: 'text-red-600',
          showArrow: false,
        };
      case TaskStatus.CANCELLED:
        return {
          // 手动结束：黄色主题，不可点击
          statusText: t('apps.deepSearch.status.cancelled'),
          statusIcon: <Ban size={14} className="text-yellow-500" />,
          bgGradient: 'from-yellow-50 via-yellow-50 to-amber-50',
          borderColor: 'border-yellow-200/50',
          iconBg: 'bg-gradient-to-br from-yellow-400 to-amber-500',
          iconColor: 'text-white',
          hoverClass: '',
          cursorClass: 'cursor-not-allowed',
          textColor: 'text-yellow-600',
          showArrow: false,
        };
      case TaskStatus.UNKNOWN:
        return {
          // 未知状态：浅橙色主题，可点击打开右面板（轻微提示）
          statusText: t('apps.deepSearch.status.unknown'),
          statusIcon: (
            <div className="flex-shrink-0 w-3.5 h-3.5 rounded-full bg-orange-400 flex items-center justify-center" title={t('apps.deepSearch.status.unknown')}>
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          ),
          bgGradient: 'from-orange-50 via-amber-50 to-yellow-50',
          borderColor: 'border-orange-200/50 hover:border-orange-300/60',
          iconBg: 'bg-gradient-to-br from-orange-300 to-amber-400',
          iconColor: 'text-white',
          hoverClass: 'hover:scale-[1.01] hover:shadow-md hover:shadow-orange-500/10',
          cursorClass: 'cursor-pointer',
          textColor: 'text-orange-700',
          titleColor: 'text-gray-900',
          showArrow: true,
        };
      default:
        return {
          statusText: t('apps.deepSearch.status.default'),
          statusIcon: <Circle size={14} className="text-gray-400" />,
          bgGradient: 'from-gray-50 via-gray-50 to-gray-100',
          borderColor: 'border-gray-200/50',
          iconBg: 'bg-gradient-to-br from-gray-300 to-gray-400',
          iconColor: 'text-white',
          hoverClass: '',
          cursorClass: 'cursor-not-allowed',
          textColor: 'text-gray-500',
          showArrow: false,
        };
    }
  };

  const config = getStatusConfig();
  const canClick = message.status === TaskStatus.COMPLETED;

  return (
    <div
      onClick={() => canClick && onClick()}
      className={`mt-2 mb-1 ml-2 mr-2 p-2.5 rounded-lg transition-all duration-200 ease-out flex items-center gap-2.5 group relative overflow-hidden ${config.hoverClass} ${config.cursorClass}`}
    >
      {/* 背景渐变 */}
      <div className={`absolute inset-0 bg-gradient-to-br ${config.bgGradient} border ${config.borderColor} rounded-lg transition-all duration-200`} />

      {/* 装饰性背景图案 - 仅进行中和完成状态显示 */}
      {(message.status === TaskStatus.IN_PROGRESS || message.status === TaskStatus.COMPLETED) && (
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <div className={`absolute -top-4 -right-4 w-16 h-16 rounded-full blur-xl ${message.status === TaskStatus.IN_PROGRESS ? 'bg-gray-400/20 group-hover:bg-gray-500/30' : 'bg-blue-400/20 group-hover:bg-blue-500/30'} transition-colors duration-200`} />
          <div className={`absolute -bottom-3 -left-3 w-12 h-12 rounded-full blur-lg ${message.status === TaskStatus.IN_PROGRESS ? 'bg-gray-300/20 group-hover:bg-gray-400/30' : 'bg-indigo-400/20 group-hover:bg-indigo-500/30'} transition-colors duration-200`} />
        </div>
      )}

      {/* 图标容器 */}
      <div className={`relative flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${config.iconBg} shadow-sm group-hover:shadow-md group-hover:scale-105 transition-all duration-200`}>
        <FileText className={`w-4 h-4 ${config.iconColor}`} />
      </div>

      {/* 内容 - 显示标题、状态文字和耗时 */}
      <div className="relative flex-1 min-w-0">
        <div className={`text-xs font-semibold truncate ${config.titleColor || config.textColor}`}>
          {formatReportTitleForDisplay(message.title, t)}
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`text-[10px] truncate ${config.textColor} opacity-80`}>
            {config.statusText}
          </div>
          {/* 用时显示 */}
          {duration && (
            <div className="flex items-center gap-0.5 text-[10px] text-gray-500 bg-white/60 backdrop-blur-sm px-1.5 py-0.5 rounded-full border border-gray-200/50">
              <Clock size={8} />
              <span>{duration}</span>
            </div>
          )}
        </div>
      </div>

      {/* 状态图标 */}
      <div className="relative flex-shrink-0">
        {config.statusIcon}
      </div>

      {/* 右侧箭头 - 仅完成状态显示 */}
      {config.showArrow && (
        <div className="relative flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center bg-white/60 backdrop-blur-sm group-hover:bg-white group-hover:rotate-90 transition-all duration-200 shadow-sm">
          <ChevronRight className="w-3.5 h-3.5 text-blue-500 group-hover:text-blue-600" />
        </div>
      )}
    </div>
  );
};

// 动态导入 TaskMessage（避免循环依赖）
const LazyTaskMessage = React.lazy(() => import('./TaskMessage'));

/**
 * 子消息渲染组件
 * 根据子消息类型渲染不同的组件
 */
const ChildTaskRenderer: React.FC<{
  childTask: Message;
  depth: number;
  onTaskClick?: (task: Message) => void;
  t: (key: string, params?: any) => string;
}> = ({ childTask, depth, onTaskClick, t }) => {
  switch (childTask.type) {
    case MessageType.TASK: {
      return (
        <React.Suspense fallback={
          <div className="ml-2 mr-2 py-2 text-xs text-gray-500">
            {t('apps.deepSearch.loading')}
          </div>
        }>
          <LazyTaskMessage
            key={childTask.id}
            message={childTask}
            depth={depth}
            onTaskClick={onTaskClick}
          />
        </React.Suspense>
      );
    }

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
      // REPORT类型：递归使用ReportMessage组件
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
 * 报告消息组件（递归渲染）
 *
 * 显示规则：
 * 1. 非最终报告：使用ReportCard组件显示，包含耗时
 * 2. 最终报告：使用DeepSearchReportCard组件显示
 * 3. 支持子消息的递归渲染（task/text/report类型）
 */
const ReportMessage: React.FC<ReportMessageProps> = ({
  message,
  depth = 0,
  onTaskClick
}) => {
  const { t } = useTranslation();
  const getChildMessages = useConversationStore((state) => state.getChildMessages);

  const [currentTime, setCurrentTime] = useState(Date.now());
  const isRootNode = !message.parentMessageId;
  const [isExpanded, setIsExpanded] = useState(isRootNode);

  useEffect(() => {
    if (message.status !== TaskStatus.IN_PROGRESS) {
      return;
    }
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, [message.status]);

  const calculatedDuration = useMemo(() => {
    switch (message.status) {
      case TaskStatus.PENDING:
        return undefined;
      case TaskStatus.IN_PROGRESS:
        return Math.max(0, currentTime - message.createdAt);
      case TaskStatus.COMPLETED:
      case TaskStatus.FAILED:
      case TaskStatus.CANCELLED:
        return Math.max(0, message.updatedAt - message.createdAt);
      default:
        return undefined;
    }
  }, [message.status, message.createdAt, message.updatedAt, currentTime]);

  const formattedDuration = useMemo(() => formatDuration(calculatedDuration), [calculatedDuration]);

  const childMessages = getChildMessages(message.id);
  const hasChildren = childMessages && childMessages.length > 0;

  const { taskMessages, textMessages, reportMessages } = useMemo(() => {
    const tasks: Message[] = [];
    const texts: Message[] = [];
    const reports: Message[] = [];

    childMessages?.forEach((child) => {
      if (child.type === MessageType.TASK) {
        tasks.push(child);
      } else if (child.type === MessageType.TEXT) {
        texts.push(child);
      } else if (child.type === MessageType.REPORT) {
        reports.push(child);
      }
    });

    return {
      taskMessages: tasks,
      textMessages: texts,
      reportMessages: reports
    };
  }, [childMessages]);

  // 判断是否为最终报告（必须在所有 hooks 之后，避免 early return 导致 hook 数量变化）
  const isFinalReport = isFinalReportMessage(message.title);
  if (isFinalReport) {
    return (
      <DeepSearchReportCard
        message={message}
        depth={depth}
        onTaskClick={onTaskClick}
      />
    );
  }

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

  return (
    <div className={`report-message py-1 ${getDepthStyle()}`}>
      {/* 报告卡片 */}
      <ReportCard
        message={message}
        onClick={() => onTaskClick?.(message)}
        duration={formattedDuration}
        t={t}
      />

      {/* 展开/折叠子消息 */}
      {hasChildren && (
        <>
          {/* 折叠标志 */}
          <div
            className="flex items-center justify-center ml-8 mr-2 mt-1 mb-1 cursor-pointer hover:bg-black/10 rounded transition-colors w-fit"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-600" />
            ) : (
              <ChevronRight size={14} className="text-gray-600" />
            )}
          </div>

          {/* 展开时的子消息 */}
          {isExpanded && (
            <div className="border-l-2 border-gray-400 ml-2 mr-2 pl-2 pb-2">
              {/* Task类型子消息 */}
              {taskMessages.map((childTask, index) => (
                <div key={childTask.id} className={index < taskMessages.length - 1 ? 'border-b border-gray-300/50' : ''}>
                  <ChildTaskRenderer
                    childTask={childTask}
                    depth={depth + 1}
                    onTaskClick={onTaskClick}
                    t={t}
                  />
                </div>
              ))}

              {/* TEXT类型子消息 */}
              {textMessages.map((childTask) => (
                <ChildTaskRenderer
                  key={childTask.id}
                  childTask={childTask}
                  depth={depth}
                  onTaskClick={onTaskClick}
                  t={t}
                />
              ))}

              {/* REPORT类型子消息 */}
              {reportMessages.map((childTask) => (
                <ChildTaskRenderer
                  key={childTask.id}
                  childTask={childTask}
                  depth={depth}
                  onTaskClick={onTaskClick}
                  t={t}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ReportMessage;
