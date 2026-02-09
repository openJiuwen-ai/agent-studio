/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useMemo, useEffect, useState, useCallback, forwardRef, useRef } from 'react'
import type { ReactNode } from 'react'
import { isPlainObject, last } from 'lodash-es'
import { type ArrayType, ASTMatch, type BaseType, type BaseVariableField, useCurrentScope } from '@flowgram.ai/editor'
import { Popover } from '@douyinfe/semi-ui'

import { IInputsValues } from '../../../'
import { FlowValueUtils } from '../../../'
import { useEditor, useEditorEvent } from '../../prompt-editor'

// 扁平化的可选项
interface FlatOption {
  key: string
  label: string
  depth: number
}

// 树节点数据
interface TreeNodeData {
  key: string | number
  label: ReactNode
  value: string | number
  children?: TreeNodeData[]
}

// EditorAPI interface from prompt-editor
interface EditorAPI {
  replaceText?: (_options: { from: number; to: number; text: string }) => void
  $view: {
    state?: {
      doc?: {
        sliceString: (_from: number, _to: number) => string
        toString?: () => string
      }
      selection?: {
        main?: {
          head: number
        }
        head?: number
      }
    }
    dispatch?: (transaction: { changes: { from: number; to: number; insert: string }; selection: { anchor: number; head: number } }) => void
    dom?: {
      parentElement?: HTMLElement
    }
  }
  getView?: () => {
    coordsAtPos?: (pos: number) => { left: number; top: number; right: number; bottom: number } | null
    dom?: { parentElement?: HTMLElement }
    state?: {
      doc?: {
        sliceString: (_from: number, _to: number) => string
      }
    }
    focus?: () => void
    dispatch?: (transaction: { changes: { from: number; to: number; insert: string }; selection?: { anchor: number; head: number } }) => void
  }
}

// Simple Mention component
interface MentionProps {
  triggerCharacters: string[]
  onOpenChange: (e: { value: boolean; state: EditorState }) => void
}

function Mention({ triggerCharacters, onOpenChange }: MentionProps) {
  const editor = useEditor() as EditorAPI | undefined

  // 使用 React Context 的事件系统
  const handleEditorChange = useCallback(
    (update: { docChanged: boolean; selectionSet?: boolean; state: EditorState }) => {
      // 检查文档变化或选择变化，都应该触发变量选择检查
      if (!update.docChanged && !update.selectionSet) return

      const view = editor?.$view
      const state: EditorState = update.state || (view?.state as EditorState | undefined)

      if (!state || !state.selection) {
        return
      }

      const selection = state.selection.main || state.selection
      const pos = selection && selection.head

      if (pos === undefined || pos === null) {
        return
      }

      let triggerFound = false

      for (const trigger of triggerCharacters) {
        const startPos = pos - trigger.length
        if (startPos >= 0 && state?.doc) {
          const charsBefore = state.doc.sliceString(startPos, pos)

          if (charsBefore === trigger) {
            triggerFound = true
            onOpenChange({ value: true, state })
            break
          }
        }
      }

      if (!triggerFound) {
        onOpenChange({ value: false, state })
      }
    },
    [editor, triggerCharacters, onOpenChange],
  )

  // 使用 React Context 的事件监听
  useEditorEvent(handleEditorChange)

  // Mention组件不渲染任何内容，只处理逻辑
  return null
}

// Simple PositionMirror component
interface PositionMirrorProps {
  position: number
  onChange?: () => void
}

const PositionMirror = forwardRef<HTMLDivElement, PositionMirrorProps>(function PositionMirror({ position, onChange: _onChange }, ref) {
  const editor = useEditor() as EditorAPI | undefined
  const [coords, setCoords] = useState({ left: 0, top: 0 })

  useEffect(() => {
    if (editor && position >= 0) {
      const view = editor.getView?.()
      if (view) {
        try {
          // CodeMirror 6 standard API: get coordinates for cursor position
          const rect = view.coordsAtPos?.(position)

          if (rect) {
            const editorElement = view.dom?.parentElement
            if (editorElement) {
              const editorRect = editorElement.getBoundingClientRect()
              const newCoords = {
                left: rect.left - editorRect.left,
                top: rect.bottom - editorRect.top,
              }
              setCoords(newCoords)
            }
          }
        } catch (error) {
          console.warn('Failed to get cursor coordinates:', error)
        }
      }
    }
  }, [editor, position])

  return <div ref={ref} style={{ position: 'absolute', left: coords.left, top: coords.top, width: 1, height: 1 }} />
})

// Helper function to get mention replace range
interface EditorState {
  doc: {
    toString(): string
    sliceString: (_from: number, _to: number) => string
  }
  selection: {
    main?: {
      head: number
    }
    head?: number
  }
}

function getCurrentMentionReplaceRange(state: EditorState) {
  if (!state || !state.selection) {
    return null
  }

  const selection = state.selection.main || state.selection
  if (!selection || selection.head === undefined) {
    return null
  }

  const pos = selection.head

  // Check if state.doc is available and has the expected methods
  if (!state.doc || typeof state.doc.toString !== 'function') {
    return null
  }

  const text = state.doc.toString()

  // Check if text is valid
  if (!text || pos < 0 || pos > text.length) {
    return null
  }

  // 从当前位置向前查找触发字符，同时检查是否有自动补全的 }
  let from = pos
  let to = pos
  let triggerLength = 0

  // 检查 {{ 和 { 触发符
  // 获取各个位置的字符片段
  const sliceMinus2 = text.slice(pos - 2, pos)
  const sliceMinus1 = text.slice(pos - 1, pos)
  const sliceCurrent = text.slice(pos, pos + 1)

  if (pos >= 2 && text.slice(pos - 2, pos) === '{{') {
    from = pos - 2
    triggerLength = 2
  } else if (pos >= 1 && text.slice(pos - 1, pos) === '{') {
    from = pos - 1
    triggerLength = 1

    // 检查是否后面有自动补全的 }
    if (text.length > pos && text.slice(pos, pos + 1) === '}') {
      // 如果有自动补全的 }，将其也包含在替换范围内
      to = pos + 1
    }
  } else if (pos >= 1 && text.slice(pos - 1, pos) === '@') {
    from = pos - 1
    triggerLength = 1
  } else if (pos >= 1 && sliceMinus1 === '{' && sliceCurrent === '}') {
    // 新增支持：输入法输入{}后光标在{和}中间的情况
    from = pos - 1
    to = pos + 1
    triggerLength = 1
  } else if (pos >= 2 && sliceMinus2 === '{}' && sliceCurrent !== '}') {
    // 新增支持：输入法输入{}后光标在}后面的情况
    from = pos - 2
    to = pos
    triggerLength = 2
  } else {
    return null
  }

  return { from, to, triggerLength }
}

type VariableField = BaseVariableField<{ icon?: string | JSX.Element; title?: string }>

interface InputsPickerProps {
  inputsValues: IInputsValues
  onSelect: (v: string) => void
}

// 将树结构扁平化为可选项列表
function flattenTreeData(node: TreeNodeData, depth = 0): FlatOption[] {
  const result: FlatOption[] = []
  const key = node.key as string
  const label = node.label as string

  // 添加当前节点
  result.push({ key, label, depth })

  // 递归处理子节点
  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      result.push(...flattenTreeData(child, depth + 1))
    }
  }

  return result
}

export function InputsPicker({ inputsValues, onSelect }: InputsPickerProps) {
  const scope = useCurrentScope()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const getArrayDrilldown = (type: ArrayType, depth = 1): { type: BaseType; depth: number } => {
    if (ASTMatch.isArray(type.items)) {
      return getArrayDrilldown(type.items, depth + 1)
    }
    return { type: type.items, depth: depth }
  }

  const renderVariable = (variable: VariableField, keyPath: string[]): TreeNodeData => {
    const type = variable?.type
    let children: TreeNodeData[] | undefined

    if (ASTMatch.isObject(type)) {
      children = (type.properties || [])
        .map(_property => renderVariable(_property as VariableField, [...keyPath, _property.key]))
        .filter(Boolean) as TreeNodeData[]
    }

    if (ASTMatch.isArray(type)) {
      const drilldown = getArrayDrilldown(type)
      if (ASTMatch.isObject(drilldown.type)) {
        children = (drilldown.type.properties || [])
          .map(_property => renderVariable(_property as VariableField, [...keyPath, ...new Array(drilldown.depth).fill('[0]'), _property.key]))
          .filter(Boolean) as TreeNodeData[]
      }
    }

    const key = keyPath.map((_key, idx) => (_key === '[0]' || idx === 0 ? _key : `.${_key}`)).join('')

    return {
      key: key,
      label: last(keyPath),
      value: key,
      children,
    }
  }

  const getTreeData = (value: unknown, keyPath: string[]): TreeNodeData | undefined => {
    const currKey = keyPath.join('.')

    if (FlowValueUtils.isFlowValue(value)) {
      if (FlowValueUtils.isRef(value)) {
        const variable = scope?.available?.getByKeyPath(value.content || [])
        if (variable) {
          return renderVariable(variable, keyPath)
        }
      }
      return {
        key: currKey,
        value: currKey,
        label: last(keyPath),
      }
    }

    if (isPlainObject(value)) {
      return {
        key: currKey,
        value: currKey,
        label: (last(keyPath) ?? currKey) as ReactNode,
        children: Object.entries(value as Record<string, unknown>)
          .map(([key, value]) => getTreeData(value, [...keyPath, key])!)
          .filter(Boolean) as TreeNodeData[],
      }
    }
    return undefined
  }

  const treeData: TreeNodeData[] = useMemo(
    () =>
      Object.entries(inputsValues)
        .map(([key, value]) => getTreeData(value, [key])!)
        .filter(Boolean),
    [],
  )

  // 扁平化选项
  const flatOptions: FlatOption[] = useMemo(() => treeData.flatMap(node => flattenTreeData(node)), [treeData])

  // 重置选中索引当选项变化时
  useEffect(() => {
    setSelectedIndex(0)
  }, [flatOptions])

  // 滚动到选中项
  useEffect(() => {
    if (containerRef.current) {
      const selectedElement = containerRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

  // 键盘事件处理
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => (prev + 1) % flatOptions.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => (prev - 1 + flatOptions.length) % flatOptions.length)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (flatOptions[selectedIndex]) {
          onSelect(flatOptions[selectedIndex].key)
        }
      }
    },
    [flatOptions, selectedIndex, onSelect],
  )

  // 暴露键盘处理方法给父组件
  useEffect(() => {
    if (containerRef.current) {
      const element = containerRef.current
      element.focus()
    }
  }, [])

  return (
    <div ref={containerRef} tabIndex={0} style={{ width: '100%', outline: 'none' }} onKeyDown={handleKeyDown}>
      {flatOptions.map((option, index) => (
        <div
          key={option.key}
          onClick={() => onSelect(option.key)}
          onMouseEnter={() => setSelectedIndex(index)}
          style={{
            padding: `8px ${8 + option.depth * 16}px`,
            cursor: 'pointer',
            backgroundColor: index === selectedIndex ? 'var(--semi-color-fill-0)' : 'transparent',
            borderRadius: 4,
            margin: '2px 0',
          }}
        >
          {option.label}
        </div>
      ))}
    </div>
  )
}

const DEFAULT_TRIGGER_CHARACTERS = ['{', '{}', '@']

export function InputsTree({ inputsValues, triggerCharacters = DEFAULT_TRIGGER_CHARACTERS }: { inputsValues: IInputsValues; triggerCharacters?: string[] }) {
  const [posKey, setPosKey] = useState('')
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState(-1)
  const [savedRange, setSavedRange] = useState<{ from: number; to: number } | null>(null)
  const editor = useEditor() as EditorAPI | undefined
  const pickerRef = useRef<HTMLDivElement>(null)

  function insert(variablePath: string) {
    if (!editor || !savedRange) {
      return
    }

    const { from, to } = savedRange
    const insertText = '{{' + variablePath + '}}'

    // 先将焦点返回到编辑器
    const view = editor.getView?.()
    if (!view) {
      return
    }

    view.focus?.()

    // 直接使用 view.dispatch 执行插入操作
    view.dispatch?.({
      changes: {
        from,
        to,
        insert: insertText,
      },
      selection: {
        anchor: from + insertText.length,
        head: from + insertText.length,
      },
    })

    setVisible(false)
    setSavedRange(null)
  }

  function handleOpenChange(e: { value: boolean; state: EditorState }) {
    if (e.state && e.state.selection) {
      const selection = e.state.selection.main || e.state.selection
      if (selection && selection.head !== undefined) {
        setPosition(selection.head)
        setPosKey(String(Math.random()))

        if (e.value && editor) {
          const range = getCurrentMentionReplaceRange(e.state)
          if (range) {
            setSavedRange({ from: range.from, to: range.to })
          }
        }
      }
    }
    setVisible(e.value)
  }

  // 弹窗打开时聚焦到选择器
  useEffect(() => {
    if (visible && pickerRef.current) {
      const timer = setTimeout(() => {
        pickerRef.current?.focus()
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [visible])

  // 全局键盘事件处理 - Escape 关闭弹窗
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setVisible(false)
        setSavedRange(null)
        const view = editor?.getView?.()
        if (view?.focus) {
          view.focus()
        }
      }
    },
    [editor],
  )

  return (
    <>
      <Mention triggerCharacters={triggerCharacters} onOpenChange={handleOpenChange} />

      <Popover
        visible={visible}
        trigger="custom"
        position="bottomLeft"
        rePosKey={posKey}
        clickToHide={false}
        content={
          <div
            ref={pickerRef}
            style={{ width: 300, maxHeight: 300, overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}
            onMouseDown={e => e.stopPropagation()}
            onKeyDown={handleKeyDown}
            tabIndex={-1}
          >
            <InputsPicker inputsValues={inputsValues} onSelect={insert} />
          </div>
        }
      >
        <PositionMirror position={position} onChange={() => setPosKey(String(Math.random()))} />
      </Popover>
    </>
  )
}
