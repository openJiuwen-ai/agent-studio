/**
 * AI 改写状态指示器组件
 */

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Brain, PenLine, AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { RewriteStatus } from '@/pages/Apps/types'
import {
  getStatusIndicatorDismissPlan,
  STATUS_INDICATOR_EXIT_MS,
} from './statusIndicatorPolicy'

const STATUS_CONFIG = {
  thinking: {
    icon: Brain,
    textKey: 'apps.report.thinking',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    textColor: 'text-blue-700',
    dot: 'bg-blue-500',
    iconColor: 'text-blue-500',
    animate: true,
  },
  writing: {
    icon: PenLine,
    textKey: 'apps.report.writing',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    textColor: 'text-emerald-700',
    dot: 'bg-emerald-500',
    iconColor: 'text-emerald-500',
    animate: false,
  },
  error: {
    icon: AlertCircle,
    textKey: '',
    bg: 'bg-red-50',
    border: 'border-red-200',
    textColor: 'text-red-700',
    dot: 'bg-red-500',
    iconColor: 'text-red-500',
    animate: false,
  },
} as const

export interface AIRewriteStatusIndicatorProps {
  status: RewriteStatus
  visible: boolean
  errorMessage?: string
  onAutoHide?: () => void
}

export const AIRewriteStatusIndicator: React.FC<AIRewriteStatusIndicatorProps> = ({
  status,
  visible,
  errorMessage,
  onAutoHide,
}) => {
  const { t } = useTranslation()
  const [isExiting, setIsExiting] = useState(false)
  const [shouldRender, setShouldRender] = useState(false)
  const [displayStatus, setDisplayStatus] = useState<RewriteStatus>('idle')
  const [displayErrorMessage, setDisplayErrorMessage] = useState<string | undefined>()

  useEffect(() => {
    if (visible && status !== 'idle') {
      setIsExiting(false)
      setShouldRender(true)
      setDisplayStatus(status)
      setDisplayErrorMessage(errorMessage)
      return
    }

    if (!visible || status === 'idle') {
      setIsExiting(true)
      const timer = setTimeout(() => {
        setShouldRender(false)
        setIsExiting(false)
        setDisplayStatus('idle')
        setDisplayErrorMessage(undefined)
      }, STATUS_INDICATOR_EXIT_MS)
      return () => clearTimeout(timer)
    }
  }, [visible, status, errorMessage])

  useEffect(() => {
    const dismissPlan = visible ? getStatusIndicatorDismissPlan(status) : null
    if (!dismissPlan || !onAutoHide) {
      return
    }

    const timer = setTimeout(() => {
      onAutoHide()
    }, dismissPlan.lingerMs)

    return () => clearTimeout(timer)
  }, [visible, status, onAutoHide])

  if (!shouldRender || displayStatus === 'idle') {
    return null
  }

  const config = STATUS_CONFIG[displayStatus as keyof typeof STATUS_CONFIG]
  if (!config) {
    return null
  }

  const Icon = config.icon
  const displayText =
    displayStatus === 'error' ? (displayErrorMessage || t('apps.report.rewriteFailed')) : t(config.textKey)

  return createPortal(
    <div
      className="fixed top-4 left-1/2 -translate-x-1/2 z-[9999]"
      style={{
        animation: isExiting
          ? `status-slide-up ${STATUS_INDICATOR_EXIT_MS}ms ease-out forwards`
          : 'status-slide-down 0.3s ease-out forwards',
      }}
    >
      <div
        className={`flex items-center gap-2 px-4 py-2 rounded-full shadow-lg border ${config.bg} ${config.border} ${config.textColor}`}
      >
        <span
          className="flex items-center justify-center"
          style={{
            animation: config.animate ? 'thinking-pulse 1.5s ease-in-out infinite' : undefined,
          }}
        >
          <Icon className={`w-4 h-4 ${config.iconColor}`} />
        </span>
        <span className="font-medium text-sm whitespace-nowrap">{displayText}</span>
        {displayStatus !== 'error' && (
          <div className="flex items-center gap-0.5 ml-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className={`w-1 h-1 rounded-full ${config.dot}`}
                style={{
                  animation: 'writing-wave 1s ease-in-out infinite',
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
