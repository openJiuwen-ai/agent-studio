import React, { useCallback, useMemo, useRef } from 'react'
import { Box, InputLabel } from '@mui/material'
import { styled } from '@mui/material/styles'
import CodeMirror from '@uiw/react-codemirror'
import { EditorView } from '@codemirror/view'
import { Extension, EditorState } from '@codemirror/state'
import { StreamLanguage, HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'
import { isValidVariableName } from '@/utils/prompts/promptEditPageUtils'
import { ViewPlugin, Decoration, DecorationSet, ViewUpdate } from '@codemirror/view'
import type { Range } from '@codemirror/state'
import { createMaxLengthExtension } from '@/utils/codemirror/maxLengthExtension'

// 样式化的容器
const EditorContainer = styled(Box)({
  position: 'relative',
  width: '100%',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',

  // CodeMirror 样式覆盖
  '& .cm-editor': {
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: '"SF Mono", Monaco, Inconsolata, "Roboto Mono", "Source Code Pro", monospace',
    height: '100%',
    flex: 1,

    '&:hover': {
      borderColor: '#9ca3af',
    },

    '&.cm-focused': {
      borderColor: '#1976d2',
      boxShadow: '0 0 0 2px rgba(25, 118, 210, 0.2)',
      outline: 'none',
    },
  },

  '& .cm-content': {
    padding: '16px',
    minHeight: '120px',
    maxHeight: '100%',
    lineHeight: '1.6',
    caretColor: '#374151',
    color: '#374151',
    overflow: 'auto',
  },

  '& .cm-scroller': {
    maxHeight: '100%',
    overflow: 'auto',
    fontFamily: 'inherit',
  },

  '& .cm-line': {
    padding: '0',
  },

  // 语法高亮样式 - 直接针对 CodeMirror 的类
  '& .tok-heading': {
    color: '#0891b2 !important',
    fontWeight: 'bold !important',
  },

  '& .tok-list': {
    color: '#2563eb !important',
    fontWeight: '500 !important',
  },

  '& .tok-variable': {
    color: '#16a34a !important',
    fontWeight: '500 !important',
    backgroundColor: 'rgba(22, 163, 74, 0.1) !important',
    borderRadius: '2px !important',
    padding: '0 2px !important',
  },

  // 有效变量的样式（整个变量包括 {{}} 和内容都是绿色，无背景）
  '& .cm-variable-valid': {
    color: '#16a34a !important',
    fontWeight: '500 !important',
  },

  // 无效变量的括号样式（只有 {{ 和 }} 是绿色）
  '& .cm-variable-bracket': {
    color: '#16a34a !important',
    fontWeight: '500 !important',
  },

  // Jinja2 控制结构样式（粉色）
  '& .cm-jinja2-control': {
    color: '#e91e63 !important',
    fontWeight: '500 !important',
  },

  // 禁用当前行高亮背景
  '& .cm-activeLine': {
    backgroundColor: 'transparent !important',
  },

  '& .cm-activeLineGutter': {
    backgroundColor: 'transparent !important',
  },

  // 占位符样式
  '& .cm-placeholder': {
    color: '#9ca3af',
    opacity: 0.8,
  },
})

// 创建自定义语言定义
const promptLanguage = StreamLanguage.define({
  name: 'prompt',
  startState: () => ({
    inVariable: false,
    variableStart: false,
    variableContent: '', // 用于累积变量内容
    isValidVariable: false, // 标记当前变量是否有效
    isVariableChecked: false, // 标记是否已经检查过变量有效性
  }),
  token: (stream, state) => {
    // 处理标题 # 开头 - 必须在行首
    if (stream.sol() && stream.match(/^#+/)) {
      stream.skipToEnd()
      return 'heading'
    }

    // 处理列表项 1. 2. 3. a. b. c. - 必须在行首或前面有空格
    if (stream.sol() || (stream.column() > 0 && stream.string.substring(0, stream.pos).match(/^\s+$/))) {
      if (stream.match(/(\d+\.|[a-zA-Z]\.)/)) {
        return 'strong' // 使用 strong 标签来应用蓝色样式
      }
    }

    // 处理变量 {{...}} - 现在由 variableHighlightPlugin 处理高亮，这里只标记为普通字符串
    // 这样 StreamLanguage 不会干扰 variableHighlightPlugin 的装饰
    if (stream.match(/\{\{/)) {
      state.inVariable = true
      state.variableStart = true
      state.variableContent = ''
      // 不返回任何 token，让 variableHighlightPlugin 处理高亮
      return null
    }

    if (state.inVariable) {
      if (stream.match(/\}\}/)) {
        state.inVariable = false
        state.variableStart = false
        // 不返回任何 token，让 variableHighlightPlugin 处理高亮
        return null
      }
      stream.next()
      // 变量内容也不返回 token，让 variableHighlightPlugin 处理高亮
      return null
    }

    stream.next()
    return null
  },
  languageData: {
    commentTokens: { line: '//' },
  },
})

// 创建语法高亮样式
const promptHighlightStyle = HighlightStyle.define([
  { tag: tags.heading, color: '#0891b2', fontWeight: 'bold' },
  { tag: tags.strong, color: '#2563eb', fontWeight: '500' },
])

// 创建变量高亮装饰插件（用于区分有效和无效变量）
const createVariableHighlightPlugin = (templateEngine: 'normal' | 'jinja2' = 'normal') => {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet
      allowSpaces: boolean

      constructor(view: EditorView) {
        this.allowSpaces = templateEngine === 'jinja2'
        this.decorations = this.buildDecorations(view)
      }

      update(update: ViewUpdate) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = this.buildDecorations(update.view)
        }
      }

      buildDecorations(view: EditorView): DecorationSet {
        const decorations: Range<Decoration>[] = []
        const text = view.state.doc.toString()

        // 匹配所有 {{...}} 格式的变量
        const variableRegex = /\{\{([^}]+)\}\}/g
        let match

        while ((match = variableRegex.exec(text)) !== null) {
          const from = match.index
          const to = match.index + match[0].length
          const rawVariableName = match[1]

          // 检查变量是否有效（根据模板引擎模式决定是否允许前后空格）
          const isValid = isValidVariableName(rawVariableName, this.allowSpaces)

          if (isValid) {
            // 有效变量：整个变量（包括 {{}} 和内容）都是绿色
            decorations.push(
              Decoration.mark({
                class: 'cm-variable-valid',
              }).range(from, to),
            )
          } else {
            // 无效变量：只有 {{ 和 }} 是绿色，中间内容是普通颜色
            const openBraceEnd = from + 2 // {{ 结束位置
            const closeBraceStart = to - 2 // }} 开始位置

            // 装饰开头的 {{
            decorations.push(
              Decoration.mark({
                class: 'cm-variable-bracket',
              }).range(from, openBraceEnd) as any,
            )

            // 装饰结尾的 }}
            decorations.push(
              Decoration.mark({
                class: 'cm-variable-bracket',
              }).range(closeBraceStart, to) as any,
            )

            // 中间的内容不添加装饰，保持普通颜色
          }
        }

        return Decoration.set(decorations)
      }
    },
    {
      decorations: v => v.decorations,
    },
  )
}

// 创建 Jinja2 控制结构高亮插件（用于高亮 {% ... %} 语法）
const createJinja2ControlPlugin = () => {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet

      constructor(view: EditorView) {
        this.decorations = this.buildDecorations(view)
      }

      update(update: ViewUpdate) {
        if (update.docChanged || update.viewportChanged) {
          this.decorations = this.buildDecorations(update.view)
        }
      }

      buildDecorations(view: EditorView): DecorationSet {
        const decorations: Range<Decoration>[] = []
        const text = view.state.doc.toString()

        // Jinja2 关键字列表
        const jinja2Keywords = [
          'if',
          'elif',
          'else',
          'endif',
          'for',
          'endfor',
          'while',
          'endwhile',
          'macro',
          'endmacro',
          'set',
          'block',
          'endblock',
          'include',
          'extends',
          'import',
          'with',
          'endwith',
          'filter',
          'endfilter',
          'call',
          'endcall',
          'raw',
          'endraw',
        ]

        // 匹配所有 {% ... %} 格式的 Jinja2 控制结构
        // 包括 {% if %}, {% elif %}, {% else %}, {% endif %}, {% for %}, {% endfor %} 等
        const jinja2ControlRegex = /\{%[\s\S]*?%\}/g
        let match

        while ((match = jinja2ControlRegex.exec(text)) !== null) {
          const from = match.index
          const to = match.index + match[0].length
          const fullMatch = match[0]

          // 提取中间的内容（去掉 {% 和 %}，保留原始空格）
          const innerContent = fullMatch.slice(2, -2)

          // 高亮开头的 {%
          const openBraceEnd = from + 2
          decorations.push(
            Decoration.mark({
              class: 'cm-jinja2-control',
            }).range(from, openBraceEnd) as any,
          )

          // 检查中间内容是否包含 Jinja2 关键字
          // 在 innerContent 中查找关键字（不区分大小写）
          for (const keyword of jinja2Keywords) {
            // 创建关键字匹配的正则表达式
            // 匹配关键字，确保它是独立的词（前后是空格、%} 或字符串开始/结束）
            const keywordRegex = new RegExp(`\\b${keyword}\\b`, 'gi')
            let keywordMatch

            // 使用 exec 循环查找所有匹配的关键字（虽然通常只有一个）
            while ((keywordMatch = keywordRegex.exec(innerContent)) !== null) {
              if (keywordMatch.index !== undefined) {
                // 计算关键字在文档中的位置
                const keywordStartInMatch = keywordMatch.index
                const keywordEndInMatch = keywordStartInMatch + keywordMatch[0].length

                // 关键字在完整匹配中的位置（需要考虑 {% 的2个字符）
                const keywordStartInDoc = from + 2 + keywordStartInMatch
                const keywordEndInDoc = from + 2 + keywordEndInMatch

                // 高亮关键字
                decorations.push(
                  Decoration.mark({
                    class: 'cm-jinja2-control',
                  }).range(keywordStartInDoc, keywordEndInDoc) as any,
                )
              }
            }
          }

          // 高亮结尾的 %}
          const closeBraceStart = to - 2
          decorations.push(
            Decoration.mark({
              class: 'cm-jinja2-control',
            }).range(closeBraceStart, to) as any,
          )
        }

        return Decoration.set(decorations)
      }
    },
    {
      decorations: v => v.decorations,
    },
  )
}

// 创建主题扩展
const createPromptTheme = (): Extension[] => {
  return [
    EditorView.theme({
      '&': {
        fontSize: '14px',
        fontFamily: '"SF Mono", Monaco, Inconsolata, "Roboto Mono", "Source Code Pro", monospace',
      },
      '.cm-content': {
        padding: '16px',
        minHeight: '120px',
        maxHeight: '100%',
        lineHeight: '1.6',
        color: '#374151',
        overflow: 'auto',
      },
      '.cm-scroller': {
        maxHeight: '100%',
        overflow: 'auto',
      },
      '.cm-focused': {
        outline: 'none',
      },
      '.cm-line': {
        padding: '0',
      },
      '.cm-placeholder': {
        color: '#9ca3af',
        opacity: 0.8,
      },
      // 禁用当前行高亮
      '.cm-activeLine': {
        backgroundColor: 'transparent !important',
      },
      '.cm-activeLineGutter': {
        backgroundColor: 'transparent !important',
      },
      // 语法高亮样式
      '.tok-heading': {
        color: '#0891b2 !important',
        fontWeight: 'bold !important',
      },
      '.tok-list': {
        color: '#2563eb !important',
        fontWeight: '500 !important',
      },
      '.tok-variable': {
        color: '#16a34a !important',
        fontWeight: '500 !important',
        backgroundColor: 'rgba(22, 163, 74, 0.1) !important',
        borderRadius: '2px !important',
        padding: '0 2px !important',
      },
      // 有效变量的样式（整个变量包括 {{}} 和内容都是绿色，无背景）
      '.cm-variable-valid': {
        color: '#16a34a !important',
        fontWeight: '500 !important',
      },
      // 无效变量的括号样式（只有 {{ 和 }} 是绿色）
      '.cm-variable-bracket': {
        color: '#16a34a !important',
        fontWeight: '500 !important',
      },
      // 有效变量的样式（整个变量包括 {{}} 和内容都是绿色）
      '.tok-variable-valid': {
        color: '#16a34a !important',
        fontWeight: '500 !important',
        backgroundColor: 'rgba(22, 163, 74, 0.1) !important',
        borderRadius: '2px !important',
        padding: '0 2px !important',
      },
      // 无效变量的括号样式（只有 {{ 和 }} 是绿色）
      '.tok-variable-bracket': {
        color: '#16a34a !important',
        fontWeight: '500 !important',
      },
      // Jinja2 控制结构样式（粉色）
      '.cm-jinja2-control': {
        color: '#e91e63 !important',
        fontWeight: '500 !important',
      },
    }),
    syntaxHighlighting(promptHighlightStyle),
  ]
}

interface AdvancedCodeMirrorEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  label?: string
  minHeight?: number
  maxHeight?: number
  maxLength?: number // 最大字符长度限制
  className?: string
  fullWidth?: boolean
  multiline?: boolean
  minRows?: number
  maxRows?: number
  sx?: any
  InputProps?: any
  inputProps?: any
  // 新增：文本选中和光标位置事件回调
  onTextSelection?: (selectedText: string, position: { x: number; y: number }, messageId?: string) => void
  onCursorPositionChange?: (position: { x: number; y: number }, cursorPos: number) => void
  messageId?: string // 用于标识消息，传递给回调函数
  templateEngine?: 'normal' | 'jinja2' // 模板引擎模式，用于变量验证
  optimizationSourceType?: 'main' | 'base' | 'control' // 优化来源类型，用于调整按钮位置偏移量
}

/**
 * 高级 CodeMirror 提示词编辑器
 * 提供专业的语法高亮和完美的编辑体验
 */
const AdvancedCodeMirrorEditor: React.FC<AdvancedCodeMirrorEditorProps> = ({
  value,
  onChange,
  placeholder = '输入提示词内容...\n\n支持语法：\n# 标题 (蓝绿色加粗)\n1. 列表 (数字蓝色)\n{{变量}} (绿色高亮)',
  disabled = false,
  label,
  minHeight = 120,
  maxHeight,
  maxLength,
  className,
  minRows,
  onTextSelection,
  onCursorPositionChange,
  messageId,
  templateEngine = 'normal',
  optimizationSourceType = 'main',
  sx,
  ...props
}) => {
  const editorRef = useRef<any>(null)
  const cursorTimerRef = useRef<NodeJS.Timeout | null>(null)
  const selectionTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 根据 minRows 计算实际最小高度
  const calculatedMinHeight = minRows ? minRows * 20 + 32 : minHeight // 每行约20px，加上padding等额外空间

  // 创建事件处理扩展
  const eventExtensions = useMemo(() => {
    const extensions: Extension[] = []

    // 添加选择变化监听器
    if (onTextSelection || onCursorPositionChange) {
      extensions.push(
        EditorView.updateListener.of(update => {
          if (update.selectionSet || update.focusChanged) {
            const state = update.state
            const selection = state.selection.main

            // 处理文本选中
            if (!selection.empty && onTextSelection) {
              const selectedText = state.doc.sliceString(selection.from, selection.to)
              if (selectedText.trim()) {
                // 清除之前的选中定时器
                if (selectionTimerRef.current) {
                  clearTimeout(selectionTimerRef.current)
                }

                // 延迟触发选中回调，确保选中操作已完成（鼠标已释放）
                selectionTimerRef.current = setTimeout(() => {
                  // 再次检查选中状态，确保用户没有取消选中
                  const currentState = update.view.state
                  const currentSelection = currentState.selection.main
                  if (!currentSelection.empty) {
                    const currentSelectedText = currentState.doc.sliceString(currentSelection.from, currentSelection.to)
                    if (currentSelectedText.trim()) {
                      // 获取选中区域的DOM位置
                      const view = update.view

                      // 获取选中区域的起始位置坐标
                      const startCoords = view.coordsAtPos(currentSelection.from)
                      const endCoords = view.coordsAtPos(currentSelection.to)

                      // 获取选中文本所在的行信息
                      const selectionLine = view.state.doc.lineAt(currentSelection.from)
                      const lastLine = view.state.doc.lineAt(currentSelection.to)
                      const isMultiLine = selectionLine.number !== lastLine.number

                      // 获取选中文本所在行在输入框中的实际起始位置
                      // 我们需要找到该行第一个可见字符的位置
                      // 如果该行有前导空格，我们需要找到第一个非空白字符的位置

                      // 获取该行在文档中的起始位置
                      const selectionLineStartPos = selectionLine.from
                      const lineStartCoords = view.coordsAtPos(selectionLineStartPos)

                      // 获取该行的文本内容
                      const lineText = view.state.doc.sliceString(selectionLine.from, selectionLine.to)

                      // 找到该行第一个非空白字符的位置
                      // 如果该行全是空白，使用行起始位置
                      const firstNonWhitespaceIndex = lineText.search(/\S/)
                      let selectionLineStartCoords = lineStartCoords

                      if (firstNonWhitespaceIndex >= 0) {
                        // 找到第一个非空白字符在文档中的位置
                        const firstNonWhitespacePos = selectionLine.from + firstNonWhitespaceIndex
                        const firstNonWhitespaceCoords = view.coordsAtPos(firstNonWhitespacePos)

                        // 如果第一个非空白字符和选中起始位置在同一行，使用第一个非空白字符的x坐标，但y坐标使用选中起始位置的y坐标
                        if (firstNonWhitespaceCoords && startCoords && Math.abs(firstNonWhitespaceCoords.top - startCoords.top) < 1) {
                          // 同一行，使用第一个非空白字符的x坐标作为该行的起始位置
                          selectionLineStartCoords = {
                            left: firstNonWhitespaceCoords.left,
                            top: startCoords.top, // 使用选中起始位置的y坐标
                            right: firstNonWhitespaceCoords.right,
                            bottom: firstNonWhitespaceCoords.bottom,
                          }
                        } else {
                          // 如果不在同一行（不应该发生），使用行起始位置
                          selectionLineStartCoords = lineStartCoords
                        }
                      } else {
                        // 该行全是空白，使用行起始位置
                        selectionLineStartCoords = lineStartCoords
                      }

                      if (selectionLineStartCoords && startCoords) {
                        // 计算一行高度（基于行高1.6和字体大小14px，约22.4px）
                        const lineHeight = 22
                        // 按钮和选中文本之间的间距（希望按钮底部距离选中文本1行）
                        const spacing = lineHeight // 1行间距

                        // 使用选中文本的起始位置（水平方向），而不是该行第一个字符的位置
                        // 这样按钮会显示在选中文本的起始位置上方
                        const selectedStartX = startCoords.left
                        // 使用选中起始位置的y坐标（确保按钮和选中文本在同一行高度）
                        const selectedTop = startCoords.top

                        // 按钮应显示在选中文本起始位置上方 1 行（按钮底部与选中区域间距 1 行）
                        const position = {
                          x: selectedStartX, // 使用选中文本的起始位置（相对于视口）
                          y: selectedTop - spacing, // 按钮底部在 selectedTop - 1 行
                        }

                        onTextSelection(currentSelectedText, position, messageId)
                      }
                    }
                  }
                }, 200) // 200ms 延迟，确保选中操作完成
              }
            } else if (selection.empty && selectionTimerRef.current) {
              // 如果选中被清除，取消延迟回调
              clearTimeout(selectionTimerRef.current)
              selectionTimerRef.current = null
            }

            // 处理光标位置变化
            if (selection.empty && onCursorPositionChange) {
              // 清除之前的定时器
              if (cursorTimerRef.current) {
                clearTimeout(cursorTimerRef.current)
              }

              // 设置1秒后触发光标位置回调
              cursorTimerRef.current = setTimeout(() => {
                const view = update.view
                const coords = view.coordsAtPos(selection.from)

                if (coords) {
                  // 计算一行高度（基于行高1.6和字体大小14px，约22.4px）
                  const lineHeight = 22
                  // IconButton size="small" 的实际高度约26px
                  const buttonHeight = 26
                  const spacing = lineHeight // 1行间距，按钮底部距离光标1行

                  // 调整偏移量：让按钮出现在光标上方一行的位置
                  const extraOffset = 0 // 减少偏移量，让按钮更接近光标
                  const targetButtonBottom = coords.top - spacing // 按钮底部应该在光标上方1行
                  const targetButtonTop = targetButtonBottom - buttonHeight // 按钮顶部位置

                  // 水平位置：使用光标的中心位置，让按钮中心对齐到光标中心
                  const cursorCenterX = (coords.left + coords.right) / 2
                  const calculatedPosition = {
                    x: cursorCenterX,
                    y: targetButtonTop - extraOffset, // 减去额外偏移，让实际位置正确
                  }

                  onCursorPositionChange(calculatedPosition, selection.from)
                }
              }, 1000)
            }
          }
        }),
      )
    }

    return extensions
  }, [onTextSelection, onCursorPositionChange])

  // 清理定时器
  React.useEffect(() => {
    return () => {
      if (cursorTimerRef.current) {
        clearTimeout(cursorTimerRef.current)
      }
      if (selectionTimerRef.current) {
        clearTimeout(selectionTimerRef.current)
      }
    }
  }, [])

  // 创建扩展
  const extensions = useMemo(() => {
    const baseExtensions = [
      promptLanguage,
      ...createPromptTheme(),
      createVariableHighlightPlugin(templateEngine), // 添加变量高亮装饰插件（根据模板引擎模式）
      EditorView.lineWrapping,
      ...eventExtensions, // 添加事件处理扩展
      ...createMaxLengthExtension(maxLength, onChange), // 添加最大长度限制扩展
    ]

    // 当模板引擎为 jinja2 时，添加 Jinja2 控制结构高亮插件
    if (templateEngine === 'jinja2') {
      baseExtensions.push(createJinja2ControlPlugin())
    }

    // 添加高度约束
    baseExtensions.push(
      EditorView.theme({
        '&': {
          height: '100%',
          maxHeight: maxHeight ? `${maxHeight}px` : '100%',
        },
        '.cm-scroller': {
          maxHeight: maxHeight ? `${maxHeight}px` : '100%',
          height: '100%',
          overflow: 'auto',
        },
        '.cm-content': {
          maxHeight: '100%',
          overflow: 'auto',
        },
      }),
    )

    return baseExtensions
  }, [maxHeight, eventExtensions, templateEngine, maxLength, onChange])

  // 处理值变化
  const handleChange = useCallback(
    (val: string) => {
      onChange(val)
    },
    [onChange],
  )

  return (
    <EditorContainer
      className={className}
      sx={[
        {
          '& .cm-content': {
            minHeight: `${calculatedMinHeight}px`,
          },
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    >
      {label && (
        <InputLabel shrink sx={{ mb: 1, color: '#374151', fontWeight: 500 }}>
          {label}
        </InputLabel>
      )}

      <Box sx={{ flex: 1, height: '100%', overflow: 'hidden' }}>
        <CodeMirror
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          editable={!disabled}
          extensions={extensions}
          basicSetup={{
            lineNumbers: false,
            foldGutter: false,
            dropCursor: false,
            allowMultipleSelections: false,
            indentOnInput: false,
            bracketMatching: false,
            closeBrackets: false,
            autocompletion: false,
            highlightSelectionMatches: false,
            searchKeymap: false,
            tabSize: 2,
            highlightActiveLine: false, // 禁用当前行高亮
          }}
          theme="light"
          style={{
            height: '100%',
            maxHeight: '100%',
          }}
        />
      </Box>
    </EditorContainer>
  )
}

export default AdvancedCodeMirrorEditor
