/**
 * 复制按钮组件
 *
 * @description
 * 带状态反馈的复制按钮组件
 * - 复制前：Copy 图标 + 提示文本
 * - 复制后：Check 图标 + 视觉反馈 + 自动重置
 */

import React from 'react'
import { Copy, Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { IconButton } from '@test-agentstudio/base-ui'
import { useClipboard } from '../hooks'

/**
 * 复制按钮组件属性
 */
export interface ClipboardButtonProps {
  /** 要复制的内容 */
  content: string
  /** 成功提示消息 */
  successMessage?: string
  /** 自定义样式类名 */
  className?: string
  /** 按钮变体（默认根据状态自动切换） */
  variant?: 'default' | 'primary' | 'auto'
}

/**
 * 复制按钮组件
 *
 * @example
 * ```tsx
 * <ClipboardButton content={text} successMessage="已复制" />
 * ```
 */
export const ClipboardButton: React.FC<ClipboardButtonProps> = ({
  content,
  successMessage,
  className = '',
  variant = 'auto',
}) => {
  const { t } = useTranslation()
  const clipboard = useClipboard()

  // Use translated success message if not provided
  const finalSuccessMessage = successMessage || t('apps.clipboard.copiedToClipboard')

  // 根据状态确定按钮变体
  const buttonVariant = variant === 'auto'
    ? (clipboard.copied ? 'primary' : 'default')
    : variant

  // 图标容器（用于过渡动画）
  const icon = (
    <span className="relative inline-block">
      {/* Copy 图标 - 淡出 */}
      <span
        className={`absolute inset-0 flex items-center justify-center transition-all duration-200 ${
          clipboard.copied
            ? 'opacity-0 scale-50 rotate-90'
            : 'opacity-100 scale-100 rotate-0'
        }`}
      >
        <Copy className="w-5 h-5" aria-hidden="true" />
      </span>

      {/* Check 图标 - 淡入 */}
      <span
        className={`transition-all duration-200 ${
          clipboard.copied
            ? 'opacity-100 scale-100 rotate-0'
            : 'opacity-0 scale-50 -rotate-90'
        }`}
      >
        <Check className="w-5 h-5" aria-hidden="true" />
      </span>
    </span>
  )

  return (
    <IconButton
      icon={icon}
      tooltip={clipboard.copied ? t('apps.clipboard.copied') : t('apps.clipboard.copy')}
      onClick={() => clipboard.copy(content, finalSuccessMessage)}
      variant={buttonVariant}
      aria-label={clipboard.copied ? t('apps.clipboard.copiedToClipboard') : t('apps.clipboard.copyReport')}
      className={className}
    />
  )
}