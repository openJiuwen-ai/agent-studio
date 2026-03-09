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

interface FlatOption {
  key: string
  label: string
  depth: number
}

interface TreeNodeData {
  key: string | number
  label: ReactNode
  value: string | number
  children?: TreeNodeData[]
}

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

function getMentionInfo(state: EditorState, triggerCharacters: string[]) {
  if (!state || !state.selection) {
    return null
  }

  const selection = state.selection.main || state.selection
  if (!selection || selection.head === undefined) {
    return null
  }

  const pos = selection.head

  if (!state.doc || typeof state.doc.toString !== 'function') {
    return null
  }

  const text = state.doc.toString()

  if (!text || pos < 0 || pos > text.length) {
    return null
  }

  // 从光标位置向前搜索触发符
  let triggerPos = -1
  let foundTrigger: string | null = null

  // 优先检查较长触发符
  for (const trigger of triggerCharacters.sort((a, b) => b.length - a.length)) {
    const idx = text.lastIndexOf(trigger, pos - trigger.length)
    if (idx !== -1 && idx + trigger.length <= pos) {
      // 检查触发符后到光标之间是否有结束符
      const textAfterTrigger = text.slice(idx + trigger.length, pos)
      if (!/[}\s]/.test(textAfterTrigger)) {
        triggerPos = idx
        foundTrigger = trigger
        break
      }
    }
  }

  if (!foundTrigger || triggerPos === -1) {
    return null
  }

  let from = triggerPos
  let to = pos
  const filterText = text.slice(triggerPos + foundTrigger.length, pos)

  // 检查光标后是否有自动补全的 }
  const charAfterCursor = text.slice(pos, pos + 1)
  if (charAfterCursor === '}' && foundTrigger === '{') {
    to = pos + 1
  }

  return { from, to, triggerLength: foundTrigger.length, filterText, trigger: foundTrigger }
}

type VariableField = BaseVariableField<{ icon?: string | JSX.Element; title?: string }>

function flattenTreeData(node: TreeNodeData, depth = 0): FlatOption[] {
  const result: FlatOption[] = []
  const key = node.key as string
  const label = node.label as string

  result.push({ key, label, depth })

  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      result.push(...flattenTreeData(child, depth + 1))
    }
  }

  return result
}

interface InputsPickerProps {
  inputsValues: IInputsValues
  onSelect: (v: string) => void
  filterText: string
  selectedIndex: number
  onSelectedIndexChange: (index: number) => void
  onFilteredOptionsChange?: (options: FlatOption[]) => void
}

export function InputsPicker({ inputsValues, onSelect, filterText, selectedIndex, onSelectedIndexChange, onFilteredOptionsChange }: InputsPickerProps) {
  const scope = useCurrentScope()
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

  const allOptions: FlatOption[] = useMemo(() => treeData.flatMap(node => flattenTreeData(node)), [treeData])

  // 根据输入过滤选项（前缀匹配）
  const filteredOptions: FlatOption[] = useMemo(() => {
    if (!filterText) {
      return allOptions
    }
    const lowerFilter = filterText.toLowerCase()
    return allOptions.filter(option => {
      const lowerKey = option.key.toLowerCase()
      const lowerLabel = option.label.toLowerCase()
      return lowerKey.startsWith(lowerFilter) || lowerLabel.startsWith(lowerFilter)
    })
  }, [allOptions, filterText])

  useEffect(() => {
    if (selectedIndex >= filteredOptions.length) {
      onSelectedIndexChange(0)
    }
    onFilteredOptionsChange?.(filteredOptions)
  }, [filteredOptions, selectedIndex, onSelectedIndexChange, onFilteredOptionsChange])

  useEffect(() => {
    if (containerRef.current) {
      const selectedElement = containerRef.current.children[selectedIndex] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [selectedIndex])

  if (filteredOptions.length === 0) {
    return (
      <div style={{ padding: 8, color: 'var(--semi-color-text-2)' }}>
        无匹配变量
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ width: '100%', outline: 'none' }}>
      {filteredOptions.map((option, index) => (
        <div
          key={option.key}
          onClick={() => onSelect(option.key)}
          onMouseEnter={() => onSelectedIndexChange(index)}
          style={{
            padding: `8px ${8 + option.depth * 16}px`,
            cursor: 'pointer',
            backgroundColor: index === selectedIndex ? 'var(--semi-color-fill-1)' : 'transparent',
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

const DEFAULT_TRIGGER_CHARACTERS = ['{', '{}', '@']

export function InputsTree({ inputsValues, triggerCharacters = DEFAULT_TRIGGER_CHARACTERS }: { inputsValues: IInputsValues; triggerCharacters?: string[] }) {
  const [posKey, setPosKey] = useState('')
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState(-1)
  const [savedRange, setSavedRange] = useState<{ from: number; to: number } | null>(null)
  const [filterText, setFilterText] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [filteredOptions, setFilteredOptions] = useState<FlatOption[]>([])
  const editor = useEditor() as EditorAPI | undefined

  const insert = useCallback((variablePath: string) => {
    if (!editor || !savedRange) {
      return
    }

    const { from, to } = savedRange
    const insertText = '{{' + variablePath + '}}'

    const view = editor.getView?.()
    if (!view) {
      return
    }

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
    setFilterText('')
    setSelectedIndex(0)
  }, [editor, savedRange])

  const handleEditorChange = useCallback(
    (update: { docChanged: boolean; selectionSet?: boolean; state: EditorState }) => {
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

      const mentionInfo = getMentionInfo(state, triggerCharacters)

      if (mentionInfo) {
        setPosition(pos)
        setPosKey(String(Math.random()))
        setSavedRange({ from: mentionInfo.from, to: mentionInfo.to })
        setFilterText(mentionInfo.filterText)
        setVisible(true)
      } else {
        setVisible(false)
        setSavedRange(null)
        setFilterText('')
        setSelectedIndex(0)
      }
    },
    [editor, triggerCharacters],
  )

  useEditorEvent(handleEditorChange)

  useEffect(() => {
    if (!visible) return

    const view = editor?.getView?.()
    if (!view?.dom) return

    const handleKeyDown = (e: KeyboardEvent) => {
      const count = Math.max(filteredOptions.length, 1)

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        e.stopPropagation()
        setSelectedIndex(prev => (prev + 1) % count)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        e.stopPropagation()
        setSelectedIndex(prev => (prev - 1 + count) % count)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        e.stopPropagation()
        if (filteredOptions[selectedIndex]) {
          insert(filteredOptions[selectedIndex].key)
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        setVisible(false)
        setSavedRange(null)
        setFilterText('')
        setSelectedIndex(0)
      }
    }

    const editorDom = view.dom as HTMLElement
    editorDom.addEventListener('keydown', handleKeyDown, true)

    return () => {
      editorDom.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [visible, editor, selectedIndex, filteredOptions, insert])

  return (
    <>
      <Popover
        visible={visible}
        trigger="custom"
        position="bottomLeft"
        rePosKey={posKey}
        clickToHide={false}
        autoAdjustOverflow={false}
        spacing={4}
        content={
          <div
            data-inputs-picker-content
            style={{ width: 300, maxHeight: 300, overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}
            onMouseDown={e => e.stopPropagation()}
          >
            <InputsPicker
              inputsValues={inputsValues}
              onSelect={insert}
              filterText={filterText}
              selectedIndex={selectedIndex}
              onSelectedIndexChange={setSelectedIndex}
              onFilteredOptionsChange={setFilteredOptions}
            />
          </div>
        }
      >
        <PositionMirror position={position} onChange={() => setPosKey(String(Math.random()))} />
      </Popover>
    </>
  )
}
