import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ReportCard from '@/pages/Apps/components/ReportCard';
import { buildReportFromDeepSearch } from '@/utils/reportUtils';
import type { DeepSearchResult } from '@/pages/Apps/types';
import type { Message } from '@/stores/useConversationStore';
import { TaskStatus } from '@/stores/useConversationStore';
import { AlertCircle, FileText, Loader2 } from 'lucide-react';

interface DeepSearchReportCardProps {
  message: Message;
  depth: number;
  onTaskClick?: (task: any) => void;
}

/**
 * DeepSearch 最终报告加载中卡片组件
 * 当报告正在生成中时显示灰色主题
 * 注意：加载中卡片不支持点击打开右侧面板
 */
const LoadingReportCard: React.FC<{
  depth: number;
}> = ({ depth }) => {
  const { t } = useTranslation();

  return (
    <div
      style={{ marginLeft: `${depth * 16}px`, marginTop: '12px', marginRight: '16px' }}
    >
      <div
        className="mt-3 p-4 rounded-xl cursor-not-allowed transition-all duration-300 ease-out
          flex items-center justify-between gap-4 group relative overflow-hidden
          bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 border-2 border-gray-200/60"
      >
        {/* 装饰性背景图案 */}
        <div className="absolute inset-0 opacity-30 pointer-events-none">
          <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full blur-2xl bg-gray-400/20" />
          <div className="absolute -bottom-6 -left-6 w-24 h-24 rounded-full blur-xl bg-gray-300/20" />
        </div>

        {/* 左侧：图标和内容 */}
        <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
          {/* 图标容器 - 旋转动画 */}
          <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
            bg-gradient-to-br from-gray-300 to-gray-400 shadow-gray-500/30
            transition-all duration-300 shadow-md">
            <Loader2 className="w-6 h-6 text-white animate-spin" />
          </div>

          {/* 文本内容 */}
          <div className="flex-1 min-w-0">
            {/* 标题 */}
            <div className="text-sm font-semibold truncate text-gray-800">
              {t('apps.deepSearch.finalReportStatus.generating')}
            </div>

            {/* 提示信息 */}
            <div className="mt-1.5 text-xs text-gray-600">
              {t('apps.deepSearch.finalReportStatus.summarizing')}
            </div>
          </div>
        </div>

        {/* 右侧：箭头图标 */}
        <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
          bg-white/80 backdrop-blur-sm
          transition-all duration-300 relative z-10 shadow-sm">
          <FileText className="w-4 h-4 text-gray-400" />
        </div>
      </div>
    </div>
  );
};

/**
 * DeepSearch 最终报告错误卡片组件
 * 当 response_content 为空或异常时显示红色报错主题
 * 注意：错误卡片不支持点击打开右侧面板
 */
const ErrorReportCard: React.FC<{
  errorType: 'exception_only' | 'both_empty';
  exceptionInfo?: string;
  depth: number;
}> = ({ errorType, exceptionInfo, depth }) => {
  const { t } = useTranslation();

  // 判断是否为开发模式，开发模式显示详细异常信息
  const isDevMode = import.meta.env.DEV;

  const getErrorMessage = () => {
    if (errorType === 'exception_only') {
      // 开发模式：显示详细异常信息；生产模式：显示通用错误提示
      if (isDevMode && exceptionInfo) {
        return exceptionInfo;
      }
      return t('apps.deepSearch.finalReportStatus.unknownError');
    }
    return t('apps.deepSearch.finalReportStatus.bothEmpty');
  };

  return (
    <div
      style={{ marginLeft: `${depth * 16}px`, marginTop: '12px', marginRight: '16px' }}
    >
      <div
        className="mt-3 p-4 rounded-xl cursor-not-allowed transition-all duration-300 ease-out
          flex items-center justify-between gap-4 group relative overflow-hidden
          bg-gradient-to-br from-red-50 via-red-50 to-pink-50 border-2 border-red-200/60
          hover:from-red-100 hover:via-red-100 hover:to-pink-100 hover:border-red-400
          hover:shadow-xl hover:shadow-red-500/20 hover:scale-[1.01]"
      >
        {/* 装饰性背景图案 */}
        <div className="absolute inset-0 opacity-30 pointer-events-none">
          <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full blur-2xl transition-colors duration-300 bg-red-400/20 group-hover:bg-red-500/30" />
          <div className="absolute -bottom-6 -left-6 w-24 h-24 rounded-full blur-xl transition-colors duration-300 bg-pink-400/20 group-hover:bg-pink-500/30" />
        </div>

        {/* 左侧：图标和内容 */}
        <div className="flex items-center gap-3 flex-1 min-w-0 relative z-10">
          {/* 图标容器 */}
          <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
            bg-gradient-to-br from-red-400 to-red-500 shadow-red-500/30
            transition-all duration-300 shadow-md group-hover:shadow-lg group-hover:scale-110">
            <AlertCircle className="w-6 h-6 text-white" />
          </div>

          {/* 文本内容 */}
          <div className="flex-1 min-w-0">
            {/* 标题 */}
            <div className="text-sm font-semibold truncate text-red-800">
              {t('apps.deepSearch.finalReportStatus.failed')}
            </div>

            {/* 错误信息 */}
            <div className="mt-1.5 text-xs font-bold text-red-900 line-clamp-2">
              {getErrorMessage()}
            </div>
          </div>
        </div>

        {/* 右侧：箭头图标 */}
        <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center
          bg-white/80 backdrop-blur-sm group-hover:bg-white
          transition-all duration-300 relative z-10 shadow-sm">
          <FileText className="w-4 h-4 text-red-500 group-hover:text-red-600" />
        </div>
      </div>
    </div>
  );
};

// 定义返回类型
type ParsedResult = {
  report: Awaited<ReturnType<typeof buildReportFromDeepSearch>> | null;
  errorType: 'exception_only' | 'both_empty' | null;
  exceptionInfo: string | null;
  isLoading: boolean;
};

/**
 * DeepSearch 最终报告卡片
 * 从 task_1_N 的 content 字段获取 DeepSearchResult 数据并渲染 ReportCard
 *
 * 数据映射：
 * - Message.content (DeepSearchResult).response_content → Report.content
 * - Message.content (DeepSearchResult).citation_messages → Report.citations
 * - Message.content (DeepSearchResult).exception_info → 异常信息（显示在 ReportPanel）
 *
 * 异常处理：
 * - response_content 为空且 exception_info 非空：显示红色错误卡片，显示 exception_info
 * - response_content 和 exception_info 均为空：显示红色错误卡片，提示两者都空
 *
 * 加载状态：
 * - PENDING/IN_PROGRESS 且 content 为空：显示灰色加载中卡片
 */
const DeepSearchReportCard: React.FC<DeepSearchReportCardProps> = ({
  message,
  depth,
  onTaskClick,
}) => {
  // 解析 DeepSearchResult 和确定错误状态
  const { report, errorType, exceptionInfo, isLoading } = useMemo((): ParsedResult => {
    if (!message) {
      console.warn('[DeepSearchReportCard] No message provided');
      return { report: null, errorType: null, exceptionInfo: null, isLoading: false };
    }

    // 从 message.content 解析 DeepSearchResult
    let deepSearchResult: DeepSearchResult;
    const content = message.content;

    // 如果 content 是空字符串
    if (typeof content === 'string' && !content.trim()) {
      // 如果是进行中状态（PENDING、IN_PROGRESS 或 UNKNOWN），显示加载中卡片
      if (message.status === TaskStatus.PENDING || message.status === TaskStatus.IN_PROGRESS || message.status === TaskStatus.UNKNOWN) {
        return { report: null, errorType: null, exceptionInfo: null, isLoading: true };
      }
      // 如果是完成/失败状态，显示错误卡片
      return { report: null, errorType: 'both_empty', exceptionInfo: null, isLoading: false };
    }

    if (typeof content === 'string') {
      // content 是 JSON 字符串，需要解析
      try {
        deepSearchResult = JSON.parse(content);
      } catch (e) {
        console.error('[DeepSearchReportCard] Failed to parse message.content as JSON:', e);
        return { report: null, errorType: 'both_empty', exceptionInfo: null, isLoading: false };
      }
    } else if (typeof content === 'object' && content !== null) {
      // content 已经是对象
      deepSearchResult = content as DeepSearchResult;
    } else {
      console.warn('[DeepSearchReportCard] Invalid message.content type:', typeof content);
      return { report: null, errorType: 'both_empty', exceptionInfo: null, isLoading: false };
    }

    const hasResponseContent = deepSearchResult.response_content && deepSearchResult.response_content.trim() !== '';
    const hasExceptionInfo = deepSearchResult.exception_info && deepSearchResult.exception_info.trim() !== '';

    // 异常情况判断
    if (!hasResponseContent) {
      if (hasExceptionInfo) {
        // response_content 为空，exception_info 非空
        return { report: null, errorType: 'exception_only', exceptionInfo: deepSearchResult.exception_info || null, isLoading: false };
      } else {
        // 两者都为空
        return { report: null, errorType: 'both_empty', exceptionInfo: null, isLoading: false };
      }
    }

    // 正常情况：使用工具函数构造 Report 对象
    return {
      report: buildReportFromDeepSearch(message.id, message.createdAt, deepSearchResult),
      errorType: null,
      exceptionInfo: null,
      isLoading: false
    };
  }, [message]);

  // 如果是加载中状态，显示加载中卡片
  if (isLoading) {
    return <LoadingReportCard depth={depth} />;
  }

  // 如果有错误，渲染错误卡片
  if (errorType) {
    return (
      <ErrorReportCard
        errorType={errorType}
        exceptionInfo={exceptionInfo || undefined}
        depth={depth}
      />
    );
  }

  // 如果没有数据，不渲染
  if (!report) {
    console.warn('[DeepSearchReportCard] Report object is null, not rendering');
    return null;
  }

  return (
    <div style={{ marginLeft: `${depth * 16}px`, marginTop: '12px', marginRight: '16px' }}>
      <ReportCard
        report={report}
        isActive={false}
        onClick={() => onTaskClick?.({
          id: message.id,
          title: report.title,
          content: report.response_content,
        })}
      />
    </div>
  );
};

export default DeepSearchReportCard;