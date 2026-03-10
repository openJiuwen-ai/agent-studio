/**
 * Message Input Component
 * 使用 textarea + 弹窗实现 @ 和 # 功能
 */

import React, { useState, useRef, useImperativeHandle, forwardRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MentionItem, MentionPicker } from './MentionPicker'
import { RADIUS_CONTAINER } from '../constants/styles'

export interface MessageInputRef {
  getValue: () => string
  setValue: (value: string) => void
  focus: () => void
  clear: () => void
  triggerPicker: (trigger: '@' | '#') => void
}

export interface MessageInputProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  disabled?: boolean
  isDisabled?: boolean
  agents?: MentionItem[]
  resources?: MentionItem[]
  onAgentSelect?: (agent: MentionItem) => void
  onResourceSelect?: (resource: MentionItem) => void
  onFileUpload?: (files: FileList) => void
  onPressEnter?: () => void
  className?: string
  style?: React.CSSProperties
}

const MessageInput = forwardRef<MessageInputRef, MessageInputProps>(
  (
    {
      value = '',
      onChange,
      placeholder,
      disabled = false,
      isDisabled = false,
      agents = [],
      resources = [],
      onAgentSelect,
      onResourceSelect,
      onFileUpload,
      onPressEnter,
      className = '',
      style,
    },
    ref,
  ) => {
    const { t } = useTranslation()
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    // Use translated placeholder if not provided
    const finalPlaceholder = placeholder || t('apps.input.placeholder')
    const [showPicker, setShowPicker] = useState(false)
    const [pickerState, setPickerState] = useState({
      trigger: '',
      query: '',
      position: { x: 0, y: 0 } as { x: number; y: number } | null,
      triggerType: null as 'agent' | 'resource' | null,
      cursorPos: 0,
    })

    // 获取光标坐标 - 简化版本，使用更可靠的计算方法
    const getCaretCoordinates = useCallback((element: HTMLTextAreaElement, position: number) => {
      const rect = element.getBoundingClientRect()
      const style = window.getComputedStyle(element)

      const paddingLeft = parseFloat(style.paddingLeft)
      const paddingTop = parseFloat(style.paddingTop)
      const fontSize = parseFloat(style.fontSize)
      const lineHeight = parseFloat(style.lineHeight)

      const textBeforeCursor = element.value.substring(0, position)
      const lines = textBeforeCursor.split('\n')
      const currentLineIndex = lines.length - 1

      const y = paddingTop + (currentLineIndex * lineHeight)
      const currentLineText = lines[currentLineIndex] || ''
      const x = paddingLeft + (currentLineText.length * fontSize * 0.6)

      return {
        left: rect.left + x,
        top: rect.top + y,
        bottom: rect.top + y + lineHeight,
      }
    }, [])

    // 检测触发字符
    const checkTrigger = useCallback((text: string, cursorPos: number) => {
      const beforeCursor = text.slice(0, cursorPos)

      const atMatch = beforeCursor.match(/@([\u4e00-\u9fa5\w]*)$/)
      const hashMatch = beforeCursor.match(/#([\u4e00-\u9fa5\w]*)$/)

      if (atMatch) {
        const query = atMatch[1]
        const triggerIndex = beforeCursor.lastIndexOf('@')
        const position = getCaretCoordinates(textareaRef.current!, triggerIndex)
        setPickerState({
          trigger: '@',
          query,
          position: { x: position.left, y: position.bottom + 5 },
          triggerType: 'agent',
          cursorPos: triggerIndex,
        })
        setShowPicker(true)
        return
      }

      if (hashMatch) {
        const query = hashMatch[1]
        const triggerIndex = beforeCursor.lastIndexOf('#')
        const position = getCaretCoordinates(textareaRef.current!, triggerIndex)

        setPickerState({
          trigger: '#',
          query,
          position: { x: position.left, y: position.bottom + 5 },
          triggerType: 'resource',
          cursorPos: triggerIndex,
        })
        setShowPicker(true)
        return
      }

      setShowPicker(false)
    }, [getCaretCoordinates])

    // 暴露 API
    useImperativeHandle(
      ref,
      () => ({
        getValue: () => textareaRef.current?.value || '',
        setValue: (newValue: string) => {
          if (textareaRef.current) {
            textareaRef.current.value = newValue
            onChange?.(newValue)
          }
        },
        focus: () => {
          textareaRef.current?.focus()
        },
        clear: () => {
          if (textareaRef.current) {
            textareaRef.current.value = ''
            onChange?.('')
          }
        },
        triggerPicker: (trigger: '@' | '#') => {
          const textarea = textareaRef.current
          if (!textarea) return

          const currentValue = textarea.value
          const newValue = currentValue + trigger
          textarea.value = newValue
          onChange?.(newValue)

          const cursorPos = newValue.length
          textarea.setSelectionRange(cursorPos, cursorPos)
          textarea.focus()

          setTimeout(() => {
            checkTrigger(newValue, cursorPos)
          }, 10)
        },
      }),
      [onChange, checkTrigger],
    )

    // 处理输入变化
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value
      const cursorPos = e.target.selectionStart || 0

      onChange?.(newValue)
      checkTrigger(newValue, cursorPos)
    }

    // 处理键盘事件
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        // 如果选择器打开，不处理 Enter
        if (showPicker) {
          e.preventDefault()
          return
        }
        // 检查是否禁用发送
        if (isDisabled) {
          e.preventDefault()
          return
        }
        // 否则发送消息
        e.preventDefault()
        onPressEnter?.()
      }
    }

    // 处理选择
    const handleSelect = (item: MentionItem) => {
      const textarea = textareaRef.current
      if (!textarea || !pickerState.position) return

      const { cursorPos, trigger, triggerType } = pickerState
      const currentValue = textarea.value

      // 智能体选择：只移除触发字符和查询文本，不添加智能体名称
      // 资源选择：保留原有的格式（如 #资源名称）
      const before = currentValue.slice(0, cursorPos)
      const after = currentValue.slice(cursorPos + pickerState.query.length + 1)

      let newValue: string
      let newCursorPos: number

      if (triggerType === 'agent') {
        // 智能体：移除 @agent，光标回到原位置
        newValue = before.slice(0, -1) + after
        newCursorPos = cursorPos - 1
      } else {
        // 资源：保留 #资源名称 格式
        newValue = before + `${trigger}${item.name}` + after
        newCursorPos = cursorPos + trigger.length + item.name.length
      }

      textarea.value = newValue
      onChange?.(newValue)

      // 设置光标位置
      textarea.setSelectionRange(newCursorPos, newCursorPos)
      textarea.focus()

      setShowPicker(false)

      // 触发回调
      if (triggerType === 'agent') {
        onAgentSelect?.(item)
      } else if (triggerType === 'resource') {
        onResourceSelect?.(item)
      }
    }

    // 确定选项列表
    const items = pickerState.triggerType === 'agent' ? agents : resources

    return (
      <div className={`relative ${className}`} style={style}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={finalPlaceholder}
          disabled={disabled}
          rows={4}
          className={`
            w-full px-5 py-4
            bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 ${RADIUS_CONTAINER}
            text-[15px] text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500
            focus:outline-none focus:border-blue-400 dark:focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:focus:ring-blue-900/30
            transition-all duration-200
            resize-none
          `}
        />

        {/* Mention Picker */}
        {showPicker && pickerState.position && (
          <MentionPicker
            trigger={pickerState.trigger}
            query={pickerState.query}
            items={items}
            onSelect={handleSelect}
            onClose={() => setShowPicker(false)}
            position={pickerState.position}
            onFileUpload={onFileUpload}
          />
        )}
      </div>
    )
  },
)

MessageInput.displayName = 'MessageInput'

export default MessageInput
