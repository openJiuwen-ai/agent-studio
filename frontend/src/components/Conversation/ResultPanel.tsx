import React from 'react';
import { useConversationStore, isFinalReportMessage } from '@/stores/useConversationStore';
import { MessageType } from '@/stores/useConversationStore';
import { ReportMarkdown } from '@/pages/Apps/components/Markdown';
import { X } from 'lucide-react';
import { ReportPanel } from '@/pages/Apps/components/ReportPanel';
import { buildReportFromDeepSearch, cleanReportContent } from '@/utils/reportUtils';

interface ResultPanelProps {
  className?: string;
}

/**
 * 右侧结果面板组件
 *
 * 显示规则（按照task_design.md要求）：
 * 1. 显示 title 作为一级标题
 * 2. 显示 content（Markdown格式）
 * 3. 支持实时更新（isStreaming 状态）
 * 4. 支持关闭面板
 */
const ResultPanel: React.FC<ResultPanelProps> = ({ className = '' }) => {
  // 从store获取选中的消息ID
  const selectedResultMessageId = useConversationStore(
    (state) => state.selectedResultMessageId
  );
  const setSelectedResultMessageId = useConversationStore(
    (state) => state.setSelectedResultMessageId
  );

  // 获取messagesMap以监听message内容变化（用于流式更新）
  const messagesMap = useConversationStore((state) => state.messagesMap);

  // 从messagesMap获取选中的消息（依赖messagesMap以实现流式更新）
  const selectedMessage = React.useMemo(() => {
    if (!selectedResultMessageId) return null;
    return messagesMap.get(selectedResultMessageId);
  }, [selectedResultMessageId, messagesMap]);

  // 解析 DeepSearch 结果（从 selectedMessage.content）
  const deepSearchResult = React.useMemo(() => {
    if (!selectedMessage || !isFinalReportMessage(selectedMessage.title)) {
      return null;
    }

    // 从 message.content 解析 DeepSearchResult
    const content = selectedMessage.content;

    if (typeof content === 'string') {
      if (!content.trim()) {
        return null;
      }
      try {
        return JSON.parse(content);
      } catch (e) {
        console.error('[ResultPanel] Failed to parse message.content as JSON:', e);
        return null;
      }
    } else if (typeof content === 'object' && content !== null) {
      return content;
    }

    return null;
  }, [selectedMessage]);

  // 处理关闭面板
  const handleClose = () => {
    setSelectedResultMessageId(null);
  };

  // 如果没有选中消息，显示空状态
  if (!selectedMessage) {
    return (
      <div className={`w-full h-full flex items-center justify-center ${className}`}>
        <p className="text-gray-500 text-sm">点击左侧任务查看详情</p>
      </div>
    );
  }

  // 检查是否为REPORT类型的消息
  const isReportType = selectedMessage.type === MessageType.REPORT;

  // 使用useMemo构造report对象，确保content更新时report也会更新
  const report = React.useMemo(() => {
    // 如果不是REPORT类型，返回null
    if (!isReportType) {
      return null;
    }

    // 检查是否为最终报告
    const isFinalReport = isFinalReportMessage(selectedMessage.title);

    if (isFinalReport) {
      // 最终报告：从DeepSearchResult获取完整数据
      if (!deepSearchResult) {
        return null;
      }

      return buildReportFromDeepSearch(
        selectedMessage.id,
        selectedMessage.createdAt || Date.now(),
        deepSearchResult
      );
    } else {
      // 其他REPORT类型：直接从message构造简单的Report对象
      let contentString = typeof selectedMessage.content === 'string'
        ? selectedMessage.content
        : String(selectedMessage.content || '');

      // 清理citation引用标记
      contentString = cleanReportContent(contentString);

      return {
        id: selectedMessage.id,
        title: selectedMessage.title || '报告',
        response_content: contentString,
        citation_messages: null, // 非最终报告没有citations
        infer_messages: [], // 非最终报告没有推理图谱
        createdAt: new Date(selectedMessage.createdAt || Date.now()).toISOString(),
      };
    }
  }, [
    isReportType,
    selectedMessage?.id,
    selectedMessage?.title,
    selectedMessage?.content,
    selectedMessage?.createdAt,
    selectedMessage?.isStreaming,
    deepSearchResult
  ]);

  // 如果是REPORT类型且有report对象，使用ReportPanel组件渲染
  if (isReportType) {
    // 对于最终报告但缺少DeepSearchResult的情况
    if (isFinalReportMessage(selectedMessage.title) && !report) {
      return (
        <div className={`w-full h-full flex items-center justify-center ${className}`}>
          <p className="text-gray-500 text-sm">正在加载报告数据...</p>
        </div>
      );
    }

    // 使用ReportPanel渲染REPORT类型
    if (report) {
      return (
        <ReportPanel
          report={report}
          onClose={handleClose}
          className={className}
        />
      );
    }
  }

  // 其他类型（LINK等）使用原有逻辑
  const content = selectedMessage.content;
  const isStreaming = selectedMessage.isStreaming || false;

  // 生成显示内容
  const renderContent = () => {
    // 处理content，生成markdown字符串
    let markdownContent = '';

    // 添加 title 作为一级标题
    if (selectedMessage.title) {
      markdownContent += `# ${selectedMessage.title}\n\n`;
    }

    // 2. 根据content类型添加内容
    if (typeof content === 'string') {
      // TEXT类型：直接添加内容
      markdownContent += content;
    } else if (selectedMessage.type === MessageType.LINK && typeof content === 'object' && content) {
      // LINK类型：生成链接详情
      const linkData = content as any;
      const url = linkData.url || '';

      // 检查是否为本地知识库链接
      const isLocalDataset = url.startsWith('localdataset://result//');

      if (isLocalDataset) {
        // 本地知识库链接：显示详细信息
        markdownContent += `**文档标题**: ${linkData.title || '未知'}\n\n`;
        markdownContent += `**文档ID**: ${url}\n\n`;
        if (linkData.query) {
          markdownContent += `**搜索词**: ${linkData.query}\n\n`;
        }
      } else {
        // 网页链接：显示可点击的链接
        if (linkData.url) {
          markdownContent += `**链接**: [${linkData.title || '查看链接'}](${linkData.url})\n\n`;
        }
        if (linkData.query) {
          markdownContent += `**搜索词**: ${linkData.query}\n\n`;
        }
        if (linkData.snippet) {
          markdownContent += `**摘要**: ${linkData.snippet}\n\n`;
        }
      }
    } else if (content) {
      // 其他类型：转为JSON显示
      markdownContent += '```json\n' + JSON.stringify(content, null, 2) + '\n```\n';
    }

    return markdownContent;
  };

  return (
    <div className={`w-full h-full flex flex-col ${className}`}>
      {/* 顶部标题栏 */}
      <div className="flex-shrink-0 flex items-center justify-between border-b pb-3 mb-4">
        {/* 任务标题 */}
        <div className="flex-1 min-w-0">
          {selectedMessage.title && (
            <h2 className="text-lg font-semibold text-gray-800 truncate">
              {selectedMessage.title}
            </h2>
          )}
        </div>

        {/* 关闭按钮 */}
        <button
          onClick={handleClose}
          className="flex-shrink-0 ml-2 p-1 hover:bg-gray-100 rounded transition-colors"
          title="关闭"
        >
          <X size={18} className="text-gray-500" />
        </button>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto">
        <div className="prose prose-sm max-w-none">
          <ReportMarkdown content={renderContent()} instanceId={`result-${selectedResultMessageId}`} />
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse align-middle"></span>
          )}
        </div>
      </div>

      {/* 流式状态指示 */}
      {isStreaming && (
        <div className="flex-shrink-0 flex items-center gap-2 text-xs text-gray-500 mt-2 pt-2 border-t">
          <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
          <span>正在更新中...</span>
        </div>
      )}
    </div>
  );
};

export default ResultPanel;
