/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useRef, createContext, useContext, useMemo, useCallback, useState } from 'react'

import { BaseEditor, type BaseEditorRef } from '../code-editor'
import { ExtensionManager } from '../base-editor'
import { EditorState } from '@codemirror/state'

import { PropsType } from './types'
import { createCustomLanguageExtension } from './custom-language-support'
import { mentionExtension } from './extensions/mention'
import { useTranslation } from '../../../i18n'

import './styles.css'

const envValue = import.meta.env.VITE_API_PROMPT_LENGTH
const MAX_PROMPT_LENGTH = parseInt(envValue || '8000', 10)

if (typeof window !== 'undefined') {
  console.log('📝 Prompt length limit DEBUG:', {
    rawEnvValue: envValue,
    typeofEnvValue: typeof envValue,
    envValueString: `"${envValue}"`,
    parsedLength: MAX_PROMPT_LENGTH,
    allEnvKeys: Object.keys(import.meta.env).filter(key => key.startsWith('VITE_')),
  })
}

const EditorContext = createContext<EditorAPI | null>(null)

const EditorEventContext = createContext<{
  listeners: Set<(update: any) => void>
}>({ listeners: new Set() })

function useEditor(): EditorAPI | null {
  return useContext(EditorContext)
}

function useEditorEvent(callback: (update: any) => void) {
  const { listeners } = useContext(EditorEventContext)

  useEffect(() => {
    listeners.add(callback)
    return () => {
      listeners.delete(callback)
    }
  }, [listeners])
}

export interface EditorAPI {
  getValue: () => string
  setValue: (value: string) => void
  replaceText: (options: { from: number; to: number; text: string }) => void
  insertVariable: (variable: string, trigger: string, position?: number) => void
  $view: {
    dispatch: (transaction: any) => void
    state: {
      doc: {
        sliceString: (from: number, to: number) => string
        toString(): string
      }
      selection: {
        main: {
          head: number
        }
      }
    }
  }
  getView: () => any
}

export interface MentionInfo {
  trigger: string
  from: number
  to: number
  view: any
  position: number
  insertVariable?: (variable: string) => void
}

export type PromptEditorPropsType = PropsType & {
  options?: Record<string, any>
  onVariableSelect?: (trigger: string, info: MentionInfo) => void
}

export { useEditor, useEditorEvent }

export function PromptEditor(props: PromptEditorPropsType) {
  const { value, onChange, readonly, placeholder, style, hasError, children, disableMarkdownHighlight, options, onVariableSelect } = props || {}
  const { t } = useTranslation()

  const defaultPlaceholder = t('workflowCanvas.formMaterials.promptEditor.placeholder')
  const finalPlaceholder = placeholder ?? defaultPlaceholder

  const editorRef = useRef<BaseEditorRef | null>(null)
  const extensionManagerRef = useRef<ExtensionManager | null>(null)
  const lastContentRef = useRef<string>('')
  const editorAPIRef = useRef<EditorAPI | null>(null)
  const editorValue = String(value?.content || '')
  const listenersRef = useRef<Set<(update: any) => void>>(new Set())
  const [characterCount, setCharacterCount] = useState(0)

  useEffect(() => {
    setCharacterCount(editorValue.length)
  }, [value?.content])

  const stableCustomExtensions = useMemo(() => {
    const extensions = [createCustomLanguageExtension()]

    extensions.push(
      EditorState.transactionFilter.of((transaction) => {
        if (transaction.docChanged && transaction.newDoc.length > MAX_PROMPT_LENGTH) {
          return false
        }
        return transaction
      }),
    )

    extensions.push(
      mentionExtension({
        triggerCharacters: ['{', '@', '{{'],
        onTrigger: (view, from, to, trigger) => {
          if (onVariableSelect) {
            onVariableSelect(trigger, {
              trigger,
              from,
              to,
              view,
              position: from,
              insertVariable: (variable: string) => {
                editorAPIRef.current?.insertVariable(variable, trigger, from)
              },
            })
          }
        },
      }),
    )

    return extensions
  }, [onVariableSelect])

  const stableExtensions = useMemo(
    () => ({
      jinja: stableCustomExtensions,
    }),
    [stableCustomExtensions],
  )
  const stableOptions = useMemo(
    () => ({
      ...options,
      readOnly: readonly,
      editable: !readonly,
    }),
    [options, readonly],
  )

  const enableExtensionsValue = !disableMarkdownHighlight

  const hasContentChanged = lastContentRef.current !== editorValue
  if (hasContentChanged) {
    lastContentRef.current = editorValue
  }

  const editorAPI = React.useMemo(() => {
    const editor = {
      getValue: () => editorRef.current?.getValue() || '',
      setValue: (val: string) => editorRef.current?.setValue(val),
      replaceText: (options: { from: number; to: number; text: string }) => {
        const currentView = editorRef.current?.getView()
        if (currentView) {
          currentView.dispatch({
            changes: {
              from: options.from,
              to: options.to,
              insert: options.text,
            },
            selection: { anchor: options.from + options.text.length, head: options.from + options.text.length },
          })
        }
      },
      insertVariable: (variable: string, trigger: string, position?: number) => {
        const currentView = editorRef.current?.getView()
        if (!currentView) return

        const state = currentView.state
        const currentPos = position ?? state.selection.main.head
        const text = state.doc.toString()

        let triggerStart = -1
        let triggerEnd = -1

        if (trigger === '{{') {
          const beforePos = text.slice(0, currentPos)
          const match = beforePos.lastIndexOf('{{')
          if (match !== -1) {
            triggerStart = match
            triggerEnd = match + 2
          }
        } else if (trigger === '{' || trigger === '@') {
          const beforePos = text.slice(0, currentPos)
          const match = beforePos.lastIndexOf(trigger)
          if (match !== -1) {
            triggerStart = match
            triggerEnd = match + 1
          }
        }

        if (triggerStart === -1) return

        const textAfterTrigger = text.slice(triggerEnd)

        let replacementEnd = triggerEnd
        let needClosingBracket = true

        if (textAfterTrigger.startsWith('}}') && trigger === '{{') {
          replacementEnd = triggerEnd + 2
          needClosingBracket = false
        } else if (textAfterTrigger.startsWith('}') && (trigger === '{' || trigger === '@')) {
          replacementEnd = triggerEnd + 1
          needClosingBracket = false
        }

        let finalText = variable
        if (needClosingBracket) {
          finalText = variable + '}'
        }

        currentView.dispatch({
          changes: {
            from: triggerStart,
            to: replacementEnd,
            insert: `${trigger}${finalText}`,
          },
          selection: {
            anchor: triggerStart + trigger.length + finalText.length,
            head: triggerStart + trigger.length + finalText.length,
          },
        })
      },
      $view: {
        dispatch: (transaction: any) => {
          const currentView = editorRef.current?.getView()
          if (currentView && transaction.changes) {
            currentView.dispatch({
              changes: transaction.changes,
            })
          }
        },
        state: null as any,
      },
      getView: () => editorRef.current?.getView() || null,
    }

    const updateViewState = () => {
      const view = editorRef.current?.getView()
      if (view && editor.$view) {
        editor.$view.state = view.state
        editor.$view.state.doc = {
          sliceString: (from: number, to: number) => {
            const state = view.state
            if (!state) return ''
            try {
              return state.doc.sliceString ? state.doc.sliceString(from, to) : state.doc.toString().slice(from, to)
            } catch (e) {
              return state.doc.toString().slice(from, to)
            }
          },
          toString: () => view.state?.doc?.toString?.() || '',
        }
        editor.$view.state.selection = view.state?.selection || {
          main: { head: 0 },
        }
      }
    }

    // Store reference and set up update mechanism
    editorAPIRef.current = editor
    return editor
  }, [])

  useEffect(() => {
    if (editorAPIRef.current && editorRef.current) {
      const view = editorRef.current.getView()
      if (view && editorAPIRef.current.$view) {
        editorAPIRef.current.$view.state = view.state
      }
    }
  }, [editorAPI])

  const handleEditorChange = (newValue: string) => {
    // 避免重复内容变化导致的重新渲染
    if (newValue === lastContentRef.current) {
      return
    }

    let finalValue = newValue
    if (newValue.length > MAX_PROMPT_LENGTH) {
      finalValue = newValue.slice(0, MAX_PROMPT_LENGTH)
    }

    lastContentRef.current = finalValue
    setCharacterCount(finalValue.length)

    listenersRef.current.forEach(listener => {
      listener({
        docChanged: true,
        state: editorAPIRef.current?.$view?.state,
      })
    })

    onChange?.({ type: 'template', content: finalValue })
  }

  const handleEditorUpdate = useCallback((update: any) => {
    if (editorAPIRef.current && editorAPIRef.current.$view) {
      editorAPIRef.current.$view.state = update.state
    }

    listenersRef.current.forEach(listener => {
      listener({
        docChanged: update.docChanged,
        state: update.state,
      })
    })
  }, [])

  useEffect(() => {
    return () => {
      if (editorRef.current) {
        editorRef.current.off('update', handleEditorUpdate)
      }
    }
  }, [handleEditorUpdate])

  const handleEditorMount = async (editorRefInstance: BaseEditorRef) => {
    editorRef.current = editorRefInstance
    extensionManagerRef.current = editorRefInstance.getExtensionManager() || null

    editorRefInstance.on('update', handleEditorUpdate)
  }

  return (
    <EditorContext.Provider value={editorAPI}>
      <EditorEventContext.Provider value={{ listeners: listenersRef.current }}>
        <div className={`gedit-m-prompt-editor-container ${hasError ? 'has-error' : ''}`} style={style}>
          <BaseEditor
            value={editorValue}
            onChange={handleEditorChange}
            language="markdown"
            theme="light"
            placeholder={finalPlaceholder}
            readonly={readonly}
            options={stableOptions}
            extensions={stableExtensions}
            enableExtensions={enableExtensionsValue}
            enableCloseBrackets={true}
            enableBracketMatching={true}
            enableAutocompletion={false}
            enableWordWrap={false}
            ref={ref => {
              if (ref) {
                handleEditorMount(ref)
              }
            }}
          />
          {!readonly && (
            <div
              style={{
                fontSize: '12px',
                color: characterCount > MAX_PROMPT_LENGTH * 0.9 ? '#f44336' : '#666',
                textAlign: 'right',
                marginTop: '4px',
                userSelect: 'none',
              }}
            >
              {characterCount} / {MAX_PROMPT_LENGTH}
            </div>
          )}
          {children}
        </div>
      </EditorEventContext.Provider>
    </EditorContext.Provider>
  )
}
