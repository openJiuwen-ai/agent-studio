/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, useImperativeHandle, forwardRef, useMemo } from 'react'
import { EditorView, keymap, placeholder as codemirrorPlaceholder, lineNumbers, GutterMarker } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { defaultKeymap, history, indentWithTab } from '@codemirror/commands'
import { foldGutter, syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language'
import { gutter } from '@codemirror/gutter'
import { autocompletion, closeBrackets } from '@codemirror/autocomplete'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { json } from '@codemirror/lang-json'
import { sql } from '@codemirror/lang-sql'
import { markdown } from '@codemirror/lang-markdown'
import { oneDark } from '@codemirror/theme-one-dark'

const STABLE_HIGHLIGHT_STYLE = defaultHighlightStyle

const foldGutterCache = new Map<boolean, any[]>()
const getFoldGutterExtension = (enable: boolean) => {
  if (foldGutterCache.has(enable)) {
    return foldGutterCache.get(enable)
  }
  const extension = enable ? [foldGutter()] : []
  foldGutterCache.set(enable, extension)
  return extension
}

const bracketExtensionsCache = new Map<string, any[]>()
const getBracketExtensions = (enableCloseBrackets: boolean, enableAutocompletion: boolean) => {
  const key = `${enableCloseBrackets}-${enableAutocompletion}`
  if (bracketExtensionsCache.has(key)) {
    return bracketExtensionsCache.get(key)
  }

  const extensions: any[] = []
  if (enableCloseBrackets) {
    extensions.push(closeBrackets())
  }
  if (enableAutocompletion) {
    extensions.push(autocompletion({}))
  }

  bracketExtensionsCache.set(key, extensions)
  return extensions
}

const EMPTY_ARRAY: any[] = []

// 标准化换行符，确保使用\n
const normalizeLineBreaks = (text: string): string => {
  if (!text) return ''
  // 将\r\n和\r都转换为\n
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
}

import { LanguageLoader } from './utils/language-loader'
import { ThemeManager } from './utils/theme-manager'
import { EventHandler } from './utils/event-handler'
import { OptionsManager } from './utils/options-manager'
import { ExtensionManager, type ExtensionConfig } from './extensions'

import './styles.css'

const languageExtensionCache = new Map<string, any>()

const getLanguageExtension = (language: string) => {
  if (languageExtensionCache.has(language)) {
    return languageExtensionCache.get(language)
  }

  let extension
  switch (language) {
    case 'javascript':
    case 'typescript':
      extension = javascript({ typescript: true })
      break
    case 'python':
      extension = python()
      break
    case 'json':
      extension = json()
      break
    case 'sql':
      extension = sql()
      break
    case 'markdown':
      extension = markdown()
      break
    case 'shell':
      extension = []
      break
    default:
      extension = []
  }

  languageExtensionCache.set(language, extension)
  return extension
}

export interface BaseEditorProps {
  value?: string
  onChange?: (value: string) => void
  language?: 'javascript' | 'typescript' | 'python' | 'json' | 'sql' | 'shell' | 'markdown'
  theme?: 'light' | 'dark'
  placeholder?: string
  readonly?: boolean
  options?: Record<string, unknown>
  className?: string
  style?: React.CSSProperties
  minHeight?: number
  maxHeight?: number
  showLineNumbers?: boolean
  showFoldGutter?: boolean
  extensions?: Record<string, ExtensionConfig>
  enableExtensions?: boolean
  enableCloseBrackets?: boolean
  enableBracketMatching?: boolean
  enableAutocompletion?: boolean
  enableWordWrap?: boolean
}

export interface BaseEditorRef {
  getValue: () => string
  setValue: (value: string) => void
  focus: () => void
  blur: () => void
  setOptions: (options: Record<string, any>) => void
  destroy: () => void
  on: (event: string, callback: (...args: unknown[]) => void) => void
  off: (event: string, callback: (...args: unknown[]) => void) => void
  getView: () => EditorView | null
  getState: () => EditorState | null
  // Extension-related methods
  getExtensionManager: () => ExtensionManager | null
  registerExtension: (extensionId: string, extension: any, config?: ExtensionConfig) => Promise<void>
  unregisterExtension: (extensionId: string) => Promise<void>
  mountExtension: (extensionId: string) => Promise<void>
  unmountExtension: (extensionId: string) => Promise<void>
  updateExtensionConfig: (extensionId: string, config: Record<string, any>) => Promise<void>
}

export const BaseEditor = forwardRef<BaseEditorRef, BaseEditorProps>(
  (
    {
      value = '',
      onChange,
      language = 'python',
      theme = 'light',
      placeholder,
      readonly = false,
      options = {},
      className = '',
      style,
      minHeight = 200,
      maxHeight,
      showLineNumbers = true,
      showFoldGutter = true,
      extensions = {},
      enableExtensions = true,
      enableCloseBrackets = true,
      enableBracketMatching = true,
      enableAutocompletion = false,
      enableWordWrap = false,
    },
    ref,
  ) => {
    const editorRef = useRef<HTMLDivElement>(null)
    const viewRef = useRef<EditorView | null>(null)
    const languageLoaderRef = useRef<LanguageLoader | null>(null)
    const themeManagerRef = useRef<ThemeManager | null>(null)
    const eventHandlerRef = useRef<EventHandler | null>(null)
    const optionsManagerRef = useRef<OptionsManager | null>(null)
    const extensionManagerRef = useRef<ExtensionManager | null>(null)
    const isUpdatingFromProps = useRef(false)

    // Initialize extension manager synchronously if needed
    if (enableExtensions && !extensionManagerRef.current) {
      extensionManagerRef.current = new ExtensionManager()
    }

    // Initialize utility managers
    useEffect(() => {
      languageLoaderRef.current = new LanguageLoader()
      themeManagerRef.current = new ThemeManager()
      eventHandlerRef.current = new EventHandler()
      optionsManagerRef.current = new OptionsManager()

      return () => {
        // Cleanup
        if (viewRef.current) {
          viewRef.current.destroy()
          viewRef.current = null
        }

        if (extensionManagerRef.current) {
          extensionManagerRef.current.clear()
        }
      }
    }, [enableExtensions])

    const editorExtensions = useMemo(() => {
      // Get language extension - use the cached extension
      const langSupport = getLanguageExtension(language)
      const languageExtension = langSupport?.extension || []

      // Get bracket completion extensions
      const bracketExtensions = getBracketExtensions(enableCloseBrackets, enableAutocompletion)

      let extensionList: any[] = EMPTY_ARRAY

      // Add extensions from props
      if (enableExtensions && extensions && Object.keys(extensions).length > 0) {
        const propsExtensions: any[] = []
        Object.values(extensions).forEach(extension => {
          if (extension && typeof extension === 'object') {
            propsExtensions.push(extension)
          }
        })
        extensionList = propsExtensions
      }

      // Add extensions from extension manager
      if (enableExtensions && extensionManagerRef.current) {
        const managerExtensions = extensionManagerRef.current.getExtensions()

        if (extensionList === EMPTY_ARRAY) {
          extensionList = managerExtensions
        } else {
          extensionList = [...extensionList, ...managerExtensions]
        }
      }

      // Add fold gutter support for languages that support it
      const shouldEnableFoldGutter =
        (language === 'javascript' || language === 'typescript' || language === 'python' || language === 'json' || language === 'shell') && showLineNumbers
      const foldExtension = getFoldGutterExtension(shouldEnableFoldGutter)

      const finalExtensions = [
        history(),
        keymap.of([indentWithTab, ...defaultKeymap]),
        ...languageExtension, // Language extension must come first
        syntaxHighlighting(STABLE_HIGHLIGHT_STYLE),
        ...(showLineNumbers ? [lineNumbers()] : []),
        ...foldExtension,
        ...(theme === 'dark' ? [oneDark] : []),
        ...extensionList,
        ...bracketExtensions,
        EditorView.theme({
          '&': {
            minHeight: `${minHeight}px`,
            ...(maxHeight && { maxHeight: `${maxHeight}px` }),
          },
          '.cm-scroller': {
            minHeight: `${minHeight}px`,
            overflowX: enableWordWrap ? 'hidden' : 'auto',
            overflowY: 'auto',
            ...(maxHeight && { maxHeight: `${maxHeight}px` }),
          },
          '.cm-gutters': {
            minHeight: `${minHeight - 8}px`, // 与 cm-content 保持一致，减去 padding
            ...(maxHeight && { maxHeight: `${maxHeight - 8}px` }),
            backgroundColor: 'var(--cm-gutters-background, #f5f5f5)',
            borderRight: '1px solid var(--cm-gutters-border, #ddd)',
            color: 'var(--cm-gutters-color, #666)',
            fontSize: '13px',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          },
          '.cm-lineNumbers .cm-gutterElement': {
            minWidth: '3em',
            textAlign: 'right',
            paddingRight: '0.5em',
            lineHeight: '1.5',
            userSelect: 'none',
            fontSize: '13px',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          },
          '.cm-content': {
            padding: '4px',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            minHeight: `${minHeight - 8}px`, // Account for padding
            ...(maxHeight && { maxHeight: `${maxHeight - 8}px` }),
            // Word wrap styles
            whiteSpace: enableWordWrap ? 'pre-wrap' : 'pre',
            wordWrap: enableWordWrap ? 'break-word' : 'normal',
            overflowWrap: enableWordWrap ? 'break-word' : 'normal',
          },
          '.cm-line': {
            whiteSpace: enableWordWrap ? 'pre-wrap' : 'pre',
            wordBreak: enableWordWrap ? 'break-word' : 'normal',
            minHeight: '1.5em', // 确保每行有足够高度
            position: 'relative',
          },
          '.cm-lineNumbers': {
            position: 'sticky',
            left: 0,
          },
          '.cm-lineNumbers-gutter': {
            backgroundColor: 'var(--cm-gutters-background, #f5f5f5)',
            color: 'var(--cm-gutters-color, #666)',
            borderRight: '1px solid var(--cm-gutters-border, #ddd)',
            minWidth: '3em',
          },
        }),
        EditorView.editable.of(!readonly),
        // Update listener - simplified
        EditorView.updateListener.of(update => {
          // Emit events for extension compatibility
          if (eventHandlerRef.current) {
            eventHandlerRef.current.emit('update', update)
          }

          // Handle onChange
          if (update.docChanged && onChange && !isUpdatingFromProps.current) {
            const newValue = update.state.doc.toString()
            onChange(newValue)
          }
        }),
      ]

      return finalExtensions
    }, [
      language,
      theme,
      readonly,
      minHeight,
      maxHeight,
      showLineNumbers,
      enableCloseBrackets,
      enableAutocompletion,
      enableExtensions,
      enableWordWrap,
      extensions,
      STABLE_HIGHLIGHT_STYLE,
    ])

    const placeholderExtension = useMemo(() => {
      return placeholder ? [codemirrorPlaceholder(placeholder)] : []
    }, [placeholder])

    useEffect(() => {
      if (!editorRef.current) return

      // Create editor state with stable extensions
      const startState = EditorState.create({
        doc: normalizeLineBreaks(value || ''),
        extensions: [...editorExtensions, ...placeholderExtension],
      })

      // Create editor view
      const view = new EditorView({
        state: startState,
        parent: editorRef.current,
      })

      viewRef.current = view

      // Setup extensions if enabled
      if (enableExtensions && extensionManagerRef.current) {
        extensionManagerRef.current.setEditorView(view)
      }

      return () => {
        if (viewRef.current) {
          viewRef.current.destroy()
          viewRef.current = null
        }
      }
    }, [editorExtensions, placeholderExtension])

    // Handle external value changes from props (prevent interference with user typing)
    useEffect(() => {
      if (viewRef.current && !isUpdatingFromProps.current) {
        const currentContent = viewRef.current.state.doc.toString()

        // Only update if content is actually different AND editor doesn't have focus
        // This prevents external value updates from interfering with user typing
        if (currentContent !== (value || '') && !viewRef.current.hasFocus) {
          isUpdatingFromProps.current = true

          const currentView = viewRef.current
          const currentState = currentView.state

          // 标准化换行符
          const newText = normalizeLineBreaks(value || '')

          // Replace entire content
          currentView.dispatch({
            changes: {
              from: 0,
              to: currentState.doc.length,
              insert: newText,
            },
          })

          // Reset the flag in next tick
          requestAnimationFrame(() => {
            isUpdatingFromProps.current = false
          })
        }
      }
    }, [value])

    // Setup extensions when configurations change
    useEffect(() => {
      if (enableExtensions && extensionManagerRef.current && viewRef.current) {
        // Re-initialize extension manager with new view if needed
        extensionManagerRef.current.setEditorView(viewRef.current)
      }
    }, [enableExtensions, extensions])

    // API Methods exposed via ref
    useImperativeHandle(
      ref,
      () => ({
        getValue: () => {
          return viewRef.current?.state.doc.toString() || ''
        },

        setValue: (newValue: string) => {
          if (viewRef.current && newValue !== undefined) {
            const currentView = viewRef.current
            const currentState = currentView.state

            // 标准化换行符
            const normalizedValue = normalizeLineBreaks(newValue)

            currentView.dispatch({
              changes: {
                from: 0,
                to: currentState.doc.length,
                insert: normalizedValue,
              },
            })
          }
        },

        focus: () => {
          viewRef.current?.focus()
        },

        blur: () => {
          viewRef.current?.contentDOM.blur()
        },

        setOptions: (newOptions: Record<string, any>) => {
          if (optionsManagerRef.current && viewRef.current) {
            const mergedOptions = { ...options, ...newOptions }
            optionsManagerRef.current.applyOptions(viewRef.current, mergedOptions)

            // Emit options change event
            if (eventHandlerRef.current) {
              eventHandlerRef.current.emit('optionsChange', mergedOptions)
            }
          }
        },

        destroy: () => {
          if (viewRef.current) {
            viewRef.current.destroy()
            viewRef.current = null
          }

          // Clean up extension manager
          if (extensionManagerRef.current) {
            extensionManagerRef.current.clear()
            extensionManagerRef.current = null
          }

          if (eventHandlerRef.current) {
            eventHandlerRef.current.removeAllListeners()
            eventHandlerRef.current = null
          }
        },

        on: (event: string, callback: (...args: unknown[]) => void) => {
          if (eventHandlerRef.current) {
            eventHandlerRef.current.on(event, callback)
          }
        },

        off: (event: string, callback: (...args: unknown[]) => void) => {
          if (eventHandlerRef.current) {
            eventHandlerRef.current.off(event, callback)
          }
        },

        getView: () => viewRef.current,

        getState: () => viewRef.current?.state || null,

        // Extension-related methods
        getExtensionManager: () => extensionManagerRef.current,

        registerExtension: async (extensionId: string, extension: any, config?: ExtensionConfig) => {
          // Ensure extension manager is initialized
          if (!extensionManagerRef.current && enableExtensions) {
            extensionManagerRef.current = new ExtensionManager()
          }

          if (!extensionManagerRef.current) {
            throw new Error('Extension manager not initialized')
          }

          const extensionWithId = { ...extension, id: extensionId }
          await extensionManagerRef.current.register(extensionWithId)
        },

        unregisterExtension: async (extensionId: string) => {
          if (!extensionManagerRef.current) {
            throw new Error('Extension manager not initialized')
          }
          await extensionManagerRef.current.unregister(extensionId)
        },

        mountExtension: async (extensionId: string) => {
          if (!extensionManagerRef.current) {
            throw new Error('Extension manager not initialized')
          }
          await extensionManagerRef.current.mount(extensionId)
        },

        unmountExtension: async (extensionId: string) => {
          if (!extensionManagerRef.current) {
            throw new Error('Extension manager not initialized')
          }
          await extensionManagerRef.current.unmount(extensionId)
        },

        updateExtensionConfig: async (extensionId: string, config: Record<string, any>) => {
          if (!extensionManagerRef.current) {
            throw new Error('Extension manager not initialized')
          }
          await extensionManagerRef.current.update(extensionId, config)
        },
      }),
      [options, enableExtensions],
    )

    // Cleanup on unmount
    useEffect(() => {
      return () => {
        // Call the destroy method which handles all cleanup
        if (viewRef.current) {
          viewRef.current.destroy()
        }
      }
    }, [])

    return (
      <div className={`base-editor-container ${className}`} style={style}>
        <div ref={editorRef} className={`base-editor ${enableWordWrap ? 'word-wrap' : ''}`} />
      </div>
    )
  },
)

BaseEditor.displayName = 'BaseEditor'
