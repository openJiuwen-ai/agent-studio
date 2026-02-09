/**
 * Base Picker Component
 * 选择器组件基类 - 提供通用的键盘导航、点击外部关闭等功能
 */

import React, { useEffect, useRef, useCallback, ReactNode, useState } from 'react'
import { RADIUS_BUTTON } from '../constants/styles'

export interface BasePickerProps {
  onClose: () => void
  position: { x: number; y: number }
  children: ReactNode
}

export interface UsePickerKeyboardParams {
  itemCount: number
  selectedIndex: number
  setSelectedIndex: (index: number) => void
  onSelect: () => void
}

/**
 * 通用的键盘导航 Hook
 */
export const usePickerKeyboard = ({
  itemCount,
  selectedIndex,
  setSelectedIndex,
  onSelect,
}: UsePickerKeyboardParams) => {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault()
          setSelectedIndex((prev) => (prev + 1) % itemCount)
          break
        case 'ArrowUp':
          event.preventDefault()
          setSelectedIndex((prev) => (prev - 1 + itemCount) % itemCount)
          break
        case 'Enter':
          event.preventDefault()
          onSelect()
          break
        case 'Escape':
          event.preventDefault()
          // Escape 由 onClose 处理
          break
      }
    },
    [itemCount, selectedIndex, setSelectedIndex, onSelect],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown])
}

/**
 * 通用的点击外部关闭 Hook
 */
export const useClickOutside = (
  pickerRef: React.RefObject<HTMLDivElement>,
  onClose: () => void,
) => {
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])
}

/**
 * 基础选择器容器组件
 */
export const BasePickerContainer = ({ onClose, position, children }: BasePickerProps) => {
  const pickerRef = useRef<HTMLDivElement>(null)
  const [adjustedPosition, setAdjustedPosition] = useState(position)

  useClickOutside(pickerRef, onClose)

  // 智能调整弹窗位置，确保不被截断
  useEffect(() => {
    if (!pickerRef.current) return

    const picker = pickerRef.current
    const pickerRect = picker.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    const viewportWidth = window.innerWidth

    let { x, y } = position

    // 检查是否会超出底部
    if (y + pickerRect.height > viewportHeight - 10) {
      // 尝试在按钮上方显示
      const spaceAbove = position.y - pickerRect.height - 5
      if (spaceAbove > 10) {
        y = spaceAbove
      } else {
        // 如果上方空间也不够，则贴近顶部显示
        y = 10
      }
    }

    // 检查是否会超出右侧
    if (x + pickerRect.width > viewportWidth - 10) {
      x = viewportWidth - pickerRect.width - 10
    }

    // 确保不超出左侧
    if (x < 10) {
      x = 10
    }

    setAdjustedPosition({ x, y })
  }, [position])

  return (
    <div
      ref={pickerRef}
      className={`fixed z-50 w-72 max-h-64 overflow-y-auto bg-white border border-gray-200 ${RADIUS_BUTTON} shadow-lg`}
      style={{
        left: `${adjustedPosition.x}px`,
        top: `${adjustedPosition.y}px`,
      }}
    >
      {children}
    </div>
  )
}
