import React from 'react';
import { useTranslation } from 'react-i18next';
import { Message, TaskStatus } from '../../../stores/useConversationStore';
import { Hand, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface InterruptMessageProps {
  message: Message;
}

/**
 * 中断等待用户输入消息组件
 *
 * 用于显示：
 * feedback_handler - 中断消息，提醒用户反馈
 *
 * 不同状态的主题：
 * - PENDING/IN_PROGRESS: 黄色主题，等待用户输入
 * - COMPLETED: 绿色主题，用户已回复
 * - FAILED: 红色主题，发生错误
 * - CANCELLED: 黄色主题，对话已取消（使用感叹号图标）
 * - UNKNOWN: 橙色主题，未知状态
 */
export const InterruptMessage: React.FC<InterruptMessageProps> = ({ message }) => {
  const { t } = useTranslation();

  // 根据状态获取样式配置
  const getStatusTheme = () => {
    switch (message.status) {
      case TaskStatus.PENDING:
      case TaskStatus.IN_PROGRESS:
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          icon: Hand,
          iconColor: 'text-yellow-600',
          titleColor: 'text-yellow-800',
          tipColor: 'text-yellow-600',
          title: t('apps.interrupt.title'),
          tip: t('apps.interrupt.pendingTip'),
          padding: 'p-3',
        };
      case TaskStatus.COMPLETED:
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          icon: CheckCircle,
          iconColor: 'text-green-600',
          titleColor: 'text-green-800',
          tipColor: 'text-green-600',
          title: t('apps.interrupt.title'),
          tip: t('apps.interrupt.completedTip'),
          padding: 'p-2',  // 减少卡片高度
        };
      case TaskStatus.FAILED:
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          icon: XCircle,
          iconColor: 'text-red-600',
          titleColor: 'text-red-800',
          tipColor: 'text-red-600',
          title: t('apps.interrupt.title'),
          tip: t('apps.interrupt.failedTip'),
          padding: 'p-3',
        };
      case TaskStatus.CANCELLED:
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          icon: AlertCircle,
          iconColor: 'text-yellow-600',
          titleColor: 'text-yellow-800',
          tipColor: 'text-yellow-700',
          title: t('apps.deepSearch.conversationCancelled'),
          tip: t('apps.deepSearch.conversationCancelledTip'),
          padding: 'p-3',
        };
      case TaskStatus.UNKNOWN:
        return {
          bg: 'bg-orange-50',
          border: 'border-orange-200',
          icon: AlertCircle,
          iconColor: 'text-orange-500',
          titleColor: 'text-orange-700',
          tipColor: 'text-orange-500',
          title: t('apps.interrupt.title'),
          tip: t('apps.interrupt.unknownTip'),
          padding: 'p-3',
        };
      default:
        return {
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          icon: Hand,
          iconColor: 'text-yellow-600',
          titleColor: 'text-yellow-800',
          tipColor: 'text-yellow-600',
          title: t('apps.interrupt.title'),
          tip: t('apps.interrupt.pendingTip'),
          padding: 'p-3',
        };
    }
  };

  const theme = getStatusTheme();
  const Icon = theme.icon;

  // 所有状态使用统一的简单样式
  return (
    <div className={`interrupt-message ${theme.bg} border ${theme.border} rounded-lg ${theme.padding}`}>
      <div className="flex items-start gap-2">
        <Icon size={18} className={`${theme.iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <h4 className={`text-sm font-semibold ${theme.titleColor} mb-1`}>{theme.title}</h4>
          <div className={`mt-2 text-sm ${theme.tipColor}`}>
            {theme.tip}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterruptMessage;
