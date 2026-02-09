import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MoreVertical, Info, Check, X } from 'lucide-react'
import { Tooltip, CircularProgress, Popover } from '@mui/material'
import { Card, CardHeader, CardHeaderIcon, CardHeaderContent, CardBody, CardFooter, CardFooterRow } from './CommonCard'

export interface ConfigCardTag {
  label: string
  color?: string
  bgColor?: string
  variant?: 'default' | 'error' | 'loading' | 'warning'
  tooltip?: React.ReactNode
}

export interface ConfigCardAction {
  key: string
  label: string
  icon?: React.ReactNode
  onClick: () => void
  disabled?: boolean
  danger?: boolean
}

export interface EditingState {
  id: string | number | null
  field: 'name' | 'description' | null
  value: string
  isEditing: boolean
}

export interface ConfigCardProps {
  id: string | number
  icon?: string | React.ReactNode
  iconBgColor?: string
  iconTextColor?: string
  title: string
  titleExtra?: React.ReactNode
  description?: string
  tags?: ConfigCardTag[]
  editingState: EditingState
  actions?: ConfigCardAction[]
  isUpdating?: boolean
  onClick?: () => void
  onEdit?: (field: 'name' | 'description') => void
  onUpdateValue?: (value: string) => void
  onSaveEdit?: () => void
  onCancelEdit?: () => void
  footer?: React.ReactNode
  className?: string
  nameMaxLength?: number
  descriptionMaxLength?: number
  inlineError?: string
}

const GAP = 8
const MIN_TAG_WIDTH = 60
const MAX_VISIBLE_TAGS = 3

interface TagDisplayInfo {
  visibleTags: ConfigCardTag[]
  overflowCount: number
  showOverflow: boolean
}

const calculateTagDisplay = (tags: ConfigCardTag[], containerWidth: number): TagDisplayInfo => {
  if (tags.length === 0) {
    return { visibleTags: [], overflowCount: 0, showOverflow: false }
  }

  let maxItems = Math.floor((containerWidth + GAP) / (MIN_TAG_WIDTH + GAP))
  maxItems = Math.max(1, Math.min(maxItems, MAX_VISIBLE_TAGS))

  const showOverflow = tags.length > maxItems
  const visibleCount = showOverflow ? Math.max(1, maxItems - 1) : tags.length
  const overflowCount = tags.length - visibleCount

  return {
    visibleTags: tags.slice(0, visibleCount),
    overflowCount: showOverflow && overflowCount > 0 ? overflowCount : 0,
    showOverflow: showOverflow && overflowCount > 0,
  }
}

export const ConfigCard: React.FC<ConfigCardProps> = ({
  id,
  icon = '⚙️',
  iconBgColor = 'bg-[#F3F4F6]',
  iconTextColor = 'text-[#374151]',
  title,
  titleExtra,
  description,
  tags = [],
  editingState,
  actions = [],
  isUpdating = false,
  onClick,
  onEdit,
  onUpdateValue,
  onSaveEdit,
  onCancelEdit,
  footer,
  className = '',
  nameMaxLength,
  descriptionMaxLength,
  inlineError,
}) => {
  const { t } = useTranslation()
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null)
  const tagContainerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [showErrorTooltip, setShowErrorTooltip] = useState(true)
  const [errorTooltipKey, setErrorTooltipKey] = useState(0)
  const errorTooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isEditingThis = editingState.id === id && editingState.isEditing

  useEffect(() => {
    if (inlineError) {
      setShowErrorTooltip(true)
      if (errorTooltipTimerRef.current) clearTimeout(errorTooltipTimerRef.current)
      errorTooltipTimerRef.current = setTimeout(() => setShowErrorTooltip(false), 3000)
    } else {
      setShowErrorTooltip(true)
    }
    return () => {
      if (errorTooltipTimerRef.current) {
        clearTimeout(errorTooltipTimerRef.current)
        errorTooltipTimerRef.current = null
      }
    }
  }, [inlineError])

  const showErrorTooltipAgain = useCallback(() => {
    setErrorTooltipKey(prev => prev + 1)
    setShowErrorTooltip(true)
    if (errorTooltipTimerRef.current) clearTimeout(errorTooltipTimerRef.current)
    errorTooltipTimerRef.current = setTimeout(() => setShowErrorTooltip(false), 3000)
  }, [])

  const tagDisplayInfo = useMemo(() => {
    return calculateTagDisplay(tags, containerWidth)
  }, [tags, containerWidth])

  useEffect(() => {
    if (!tagContainerRef.current) return
    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width)
      }
    })
    resizeObserver.observe(tagContainerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  useEffect(() => {
    return () => {
      if (clickTimeoutRef.current) {
        clearTimeout(clickTimeoutRef.current)
      }
    }
  }, [])

  const handleMenuAction = (action: () => void) => {
    action()
    setMenuAnchorEl(null)
  }

  const handleMenuToggle = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation()
    setMenuAnchorEl(e.currentTarget)
  }

  const handleMenuClose = () => {
    setMenuAnchorEl(null)
  }

  const handleFieldMouseDown = (field: 'name' | 'description') => (e: React.MouseEvent) => {
    if (isEditingThis && editingState.field !== field) {
      e.preventDefault()
    }
  }

  const handleFieldDoubleClick = (field: 'name' | 'description') => (e: React.MouseEvent) => {
    e.stopPropagation()
    if (isUpdating) return
    if (clickTimeoutRef.current) {
      clearTimeout(clickTimeoutRef.current)
      clickTimeoutRef.current = null
    }
    onEdit?.(field)
  }

  const isMenuOpen = Boolean(menuAnchorEl)

  const getTagStyles = (variant?: ConfigCardTag['variant']) => {
    const baseClass = 'inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-[4px] max-w-full'
    const maxWidth = `calc(45% - ${(GAP * 2) / 3}px)`

    const variantStyles = {
      error: 'bg-[#FEE2E2] text-[#DC2626]',
      loading: 'bg-[#F3F4F6] text-[#6B7280]',
      warning: 'bg-[#FEF3C7] text-[#92400E]',
      default: 'bg-[#F3F4F6] text-[#6B7280]',
    } as const

    return {
      className: `${baseClass} ${variantStyles[variant || 'default']}`,
      style: { maxWidth } as React.CSSProperties,
    }
  }

  const renderOverflowTag = (overflowCount: number) => {
    const overflowTags = tags.slice(tags.length - overflowCount)
    return (
      <Tooltip
        key="overflow"
        title={
          <div className="flex flex-col gap-1">
            {overflowTags.map((t, i) => (
              <span key={i}>{t.label}</span>
            ))}
          </div>
        }
        arrow
        placement="top"
      >
        <span className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-[4px] bg-[#F3F4F6] text-[#6B7280] cursor-pointer">
          +{overflowCount}
        </span>
      </Tooltip>
    )
  }

  const renderTag = (tag: ConfigCardTag, index: number) => {
    const { className, style } = getTagStyles(tag.variant)
    const baseStyle = { ...(style as React.CSSProperties) }

    const customStyle: React.CSSProperties = {
      ...baseStyle,
      color: tag.color ?? baseStyle.color,
      backgroundColor: tag.bgColor ?? baseStyle.backgroundColor,
    }

    if (tag.variant === 'error') {
      return (
        <Tooltip key={index} title={tag.tooltip ?? t('common.messages.disabled')} disableInteractive placement="top">
          <span className={className} style={customStyle}>
            <span className="truncate">{tag.label}</span>
            <Info className="w-3 h-3 ml-1 flex-shrink-0" />
          </span>
        </Tooltip>
      )
    }

    if (tag.variant === 'loading') {
      return (
        <span key={index} className={className} style={customStyle}>
          {t('common.messages.loading')}
        </span>
      )
    }

    const TagWithConditionalTooltip: React.FC = () => {
      const [showTooltip, setShowTooltip] = useState(false)
      const textRef = useRef<HTMLSpanElement>(null)

      useEffect(() => {
        const checkOverflow = () => {
          if (textRef.current) {
            setShowTooltip(textRef.current.scrollWidth > textRef.current.clientWidth)
          }
        }
        checkOverflow()
        window.addEventListener('resize', checkOverflow)
        return () => window.removeEventListener('resize', checkOverflow)
      }, [])

      const content = (
        <span className={className} style={customStyle}>
          <span ref={textRef} className="truncate">
            {tag.label}
          </span>
        </span>
      )

      if (!showTooltip) {
        return content
      }

      return (
        <Tooltip title={tag.label} disableInteractive placement="top">
          {content}
        </Tooltip>
      )
    }

    return <TagWithConditionalTooltip key={index} />
  }

  const scrollbarStyles = `
    .config-card-scrollbar {
      scrollbar-width: thin;
      scrollbar-color: #d1d5db transparent;
    }
    .config-card-scrollbar::-webkit-scrollbar {
      width: 4px;
    }
    .config-card-scrollbar::-webkit-scrollbar-track {
      background: transparent;
    }
    .config-card-scrollbar::-webkit-scrollbar-thumb {
      background: #d1d5db;
      border-radius: 2px;
    }
    .config-card-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #9ca3af;
    }
  `

  return (
    <>
      <style>{scrollbarStyles}</style>
      <Card
        className={className}
        onClick={() => {
          if (!isMenuOpen) {
            if (clickTimeoutRef.current) {
              clearTimeout(clickTimeoutRef.current)
            }
            clickTimeoutRef.current = setTimeout(() => {
              if (window.getSelection()?.toString().trim()) return
              onClick?.()
            }, 200)
          }
        }}
      >
        <CardHeader>
          <CardHeaderIcon bgColor={iconBgColor} textColor={`${iconTextColor} text-2xl`}>
            {icon}
          </CardHeaderIcon>
          <CardHeaderContent className={tags.length > 0 ? 'justify-between' : 'justify-center'}>
            {isEditingThis && editingState.field === 'name' ? (
              <div className="flex items-center gap-1 min-w-0 flex-1">
                <Tooltip
                  key={errorTooltipKey}
                  title={inlineError ?? ''}
                  placement="top-end"
                  open={!!inlineError && showErrorTooltip}
                  slotProps={{
                    popper: {
                      modifiers: [{ name: 'offset', options: { offset: [0, -10] } }],
                      sx: {
                        '& .MuiTooltip-tooltip': {
                          bgcolor: '#FEE2E2',
                          color: '#DC2626',
                          fontWeight: 500,
                        },
                      },
                    },
                  }}
                >
                  <div className="flex-1 relative">
                    <input
                      id={`edit-input-${id}-name`}
                      type="text"
                      value={editingState.value}
                      onChange={e => onUpdateValue?.(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          onCancelEdit?.()
                        }
                      }}
                      maxLength={nameMaxLength}
                      className={`w-full px-2 py-1 pr-16 text-[14px] font-bold text-[#1F2937] leading-[24px] h-[24px] border rounded-[4px] focus:outline-none focus:ring-1 ${
                        inlineError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : 'border-[#3B82F6] focus:ring-[#3B82F6] focus:border-[#3B82F6]'
                      }`}
                      disabled={isUpdating}
                      onClick={e => e.stopPropagation()}
                      autoFocus
                    />
                    {nameMaxLength != null && (
                      <div
                        className="absolute right-2 top-1/2 transform -translate-y-1/2 text-xs text-[#9CA3AF] pointer-events-none"
                        style={{ lineHeight: '24px' }}
                      >
                        {editingState.value.length}/{nameMaxLength}
                      </div>
                    )}
                  </div>
                </Tooltip>
                <button
                  onClick={e => {
                    e.stopPropagation()
                    showErrorTooltipAgain()
                    onSaveEdit?.()
                  }}
                  disabled={isUpdating}
                  className="flex items-center justify-center p-0.5 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title={t('common.buttons.save')}
                >
                  {isUpdating ? <CircularProgress size={14} sx={{ color: '#16A34A' }} /> : <Check className="w-3.5 h-3.5" />}
                </button>
                <button
                  onMouseDown={e => {
                    e.preventDefault()
                    e.stopPropagation()
                    onCancelEdit?.()
                  }}
                  disabled={isUpdating}
                  className="flex items-center justify-center p-0.5 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title={t('common.buttons.cancel')}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div
                className={`flex items-center gap-1 h-[24px] min-w-0 flex-1 ${onEdit ? 'cursor-text' : ''}`}
                onMouseDown={onEdit ? handleFieldMouseDown('name') : undefined}
                onDoubleClick={onEdit ? handleFieldDoubleClick('name') : undefined}
                title={onEdit ? `${t('common.messages.doubleClickToEdit')}` : undefined}
              >
                <h3 className="text-[#1F2937] font-bold text-[14px] leading-[24px] truncate min-w-0">{title}</h3>
                {titleExtra}
              </div>
            )}
            {tags.length > 0 && (
              <div ref={tagContainerRef} className="flex items-center gap-2 w-full overflow-hidden">
                {tagDisplayInfo.visibleTags.map((tag, index) => renderTag(tag, index))}
                {tagDisplayInfo.showOverflow && renderOverflowTag(tagDisplayInfo.overflowCount)}
              </div>
            )}
          </CardHeaderContent>
        </CardHeader>

        {description !== undefined && (
          <CardBody>
            {isEditingThis && editingState.field === 'description' ? (
              <div className="flex items-start gap-1">
                <Tooltip
                  key={errorTooltipKey}
                  title={inlineError ?? ''}
                  placement="top-end"
                  open={!!inlineError && showErrorTooltip}
                  slotProps={{
                    popper: {
                      modifiers: [{ name: 'offset', options: { offset: [0, -10] } }],
                      sx: {
                        '& .MuiTooltip-tooltip': {
                          bgcolor: '#FEE2E2',
                          color: '#DC2626',
                          fontWeight: 500,
                        },
                      },
                    },
                  }}
                >
                  <div className="flex-1 relative" style={{ height: '39px' }}>
                    <textarea
                      id={`edit-input-${id}-description`}
                      value={editingState.value}
                      onChange={e => onUpdateValue?.(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Escape') {
                          e.preventDefault()
                          onCancelEdit?.()
                        }
                      }}
                      maxLength={descriptionMaxLength}
                      className={`config-card-scrollbar w-full px-2 py-1 pr-16 text-xs text-[#6B7280] border rounded-[4px] focus:outline-none focus:ring-1 resize-none overflow-y-auto ${
                        inlineError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : 'border-[#3B82F6] focus:ring-[#3B82F6] focus:border-[#3B82F6]'
                      }`}
                      style={{
                        lineHeight: '1.625',
                        height: '39px',
                        minHeight: '39px',
                        maxHeight: '39px',
                      }}
                      disabled={isUpdating}
                      onClick={e => e.stopPropagation()}
                      autoFocus
                    />
                    {descriptionMaxLength != null && (
                      <div className="absolute right-2 bottom-0.5 text-xs text-[#9CA3AF] pointer-events-none" style={{ lineHeight: '1' }}>
                        {editingState.value.length}/{descriptionMaxLength}
                      </div>
                    )}
                  </div>
                </Tooltip>
                <div className="flex flex-col gap-1">
                  <button
                    onClick={e => {
                      e.stopPropagation()
                      showErrorTooltipAgain()
                      onSaveEdit?.()
                    }}
                    disabled={isUpdating}
                    className="flex items-center justify-center p-0.5 text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={t('common.buttons.save')}
                  >
                    {isUpdating ? <CircularProgress size={12} sx={{ color: '#16A34A' }} /> : <Check className="w-3 h-3" />}
                  </button>
                  <button
                    onMouseDown={e => {
                      e.preventDefault()
                      e.stopPropagation()
                      onCancelEdit?.()
                    }}
                    disabled={isUpdating}
                    className="flex items-center justify-center p-0.5 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={t('common.buttons.cancel')}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ) : (
              <p
                className={`text-[#6B7280] text-xs leading-relaxed line-clamp-2 overflow-hidden h-[39px] whitespace-pre-line break-words ${onEdit ? 'cursor-text' : ''}`}
                onMouseDown={onEdit ? handleFieldMouseDown('description') : undefined}
                onDoubleClick={onEdit ? handleFieldDoubleClick('description') : undefined}
                title={onEdit ? `${t('common.messages.doubleClickToEdit')}` : undefined}
              >
                {description || t('common.messages.noDescription')}
              </p>
            )}
          </CardBody>
        )}

        {footer && actions.length > 0 ? (
          <CardFooter>
            <CardFooterRow>
              {footer}
              <>
                <button
                  onClick={handleMenuToggle}
                  className="p-1 text-[#9CA3AF] hover:text-[#4B5563] hover:bg-[#F3F4F6] rounded-[4px] transition-colors"
                  title={t('common.messages.moreActions')}
                >
                  <MoreVertical className="w-4 h-4" />
                </button>

                <Popover
                  open={isMenuOpen}
                  anchorEl={menuAnchorEl}
                  onClose={handleMenuClose}
                  anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                  transformOrigin={{ vertical: 'top', horizontal: 'right' }}
                >
                  {actions.map(action => (
                    <button
                      key={action.key}
                      onClick={() => handleMenuAction(action.onClick)}
                      disabled={action.disabled}
                      className={`w-full px-3 py-2 text-left text-sm transition-colors flex items-center space-x-2 ${
                        action.danger ? 'text-red-600 hover:bg-[#FEF2F2]' : 'text-[#374151] hover:bg-[#F3F4F6]'
                      } ${action.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {action.icon && <span>{action.icon}</span>}
                      <span>{action.label}</span>
                    </button>
                  ))}
                </Popover>
              </>
            </CardFooterRow>
          </CardFooter>
        ) : footer ? (
          <CardFooter>{footer}</CardFooter>
        ) : null}
      </Card>
    </>
  )
}

export default ConfigCard
