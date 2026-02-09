import React from 'react'
import { cn } from '../../lib/utils'
import { Tooltip } from './tooltip'

/**
 * IconButton 变体类型
 */
export type IconButtonVariant = 'default' | 'primary' | 'danger'

/**
 * IconButton 组件属性
 */
export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** 图标 */
  icon: React.ReactNode
  /** 提示文字 */
  tooltip?: string
  /** 按钮变体 */
  variant?: IconButtonVariant
  /** 是否禁用 */
  disabled?: boolean
}

/**
 * 图标按钮组件
 *
 * @example
 * ```tsx
 * <IconButton icon={<Copy />} tooltip="复制" onClick={handleCopy} />
 * <IconButton icon={<Download />} tooltip="下载" variant="primary" onClick={handleDownload} />
 * ```
 */
export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, tooltip, variant = 'default', disabled = false, className = '', ...props }, ref) => {
    const baseStyles =
      'h-11 w-11 rounded-xl flex items-center justify-center transition-all duration-200 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed'

    const variantStyles: Record<IconButtonVariant, string> = {
      primary:
        'bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-blue-500/30 hover:shadow-lg hover:shadow-blue-500/40 hover:scale-105 active:scale-95',
      danger: 'bg-gradient-to-br from-red-500 to-red-600 text-white shadow-red-500/30 hover:shadow-lg hover:shadow-red-500/40 hover:scale-105 active:scale-95',
      default: 'bg-white text-gray-700 shadow-gray-200/50 hover:text-gray-900 hover:shadow-md hover:scale-105 active:scale-95',
    }

    const button = (
      <button ref={ref} disabled={disabled} aria-label={tooltip} className={cn(baseStyles, variantStyles[variant], className)} {...props}>
        {icon}
      </button>
    )

    // 如果有tooltip且未禁用，用Tooltip包裹
    if (tooltip && !disabled) {
      return (
        <Tooltip content={tooltip} delayDuration={500}>
          {button}
        </Tooltip>
      )
    }

    return button
  },
)

IconButton.displayName = 'IconButton'
