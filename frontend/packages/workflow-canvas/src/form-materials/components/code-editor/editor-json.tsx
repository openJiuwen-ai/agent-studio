/**
 * Enhanced JSON Code Editor with built-in parsing logic
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'

import { BaseEditor } from '../base-editor'
import type { BaseEditorProps } from '../base-editor'
import { useTranslation } from '../../../i18n'

export interface EditorJsonProps extends Omit<BaseEditorProps, 'language'> {
  value?: Record<string, unknown> | unknown
  onChange?: (value: Record<string, unknown> | unknown) => void
  parseDelay?: number
  showErrors?: boolean
  renderError?: (error: string) => React.ReactNode
  validateOnBlur?: boolean
  onValidationChange?: (isValid: boolean, error?: string) => void
  mini?: boolean
  defaultFormat?: string
  arrayElementType?: string
  validateArrayElements?: boolean
  compact?: boolean
}

export interface JsonCodeEditorRef {
  formatJson: () => void
  getValue: () => Record<string, unknown> | unknown
  getEditorValue: () => string
  isValid: boolean
  error?: string
}

const JsonCodeEditorWithEnhancedLogic: React.ForwardRefRenderFunction<JsonCodeEditorRef, EditorJsonProps> = (
  {
    value,
    onChange,
    parseDelay = 800,
    showErrors = true,
    renderError,
    validateOnBlur = false,
    onValidationChange,
    theme = 'light',
    placeholder,
    readonly = false,
    options,
    mini,
    children,
    extensions,
    defaultFormat,
    arrayElementType,
    validateArrayElements = false,
    compact = false,
    ...props
  },
  ref,
) => {
  const { t } = useTranslation()

  const stringifyValue = useCallback((val: unknown) => {
    return compact ? JSON.stringify(val) : JSON.stringify(val, null, 2)
  }, [compact])

  const hasValue = value !== undefined && value !== null && value !== ''

  const [editorValue, setEditorValue] = useState<string>(() => {
    try {
      if (hasValue) {
        return stringifyValue(value)
      } else if (defaultFormat) {
        return defaultFormat
      } else {
        return stringifyValue({})
      }
    } catch (error) {
      console.warn('Failed to format initial JSON value:', error)
      return defaultFormat || '{}'
    }
  })

  const [validationState, setValidationState] = useState<{
    isValid: boolean
    error?: string
    lastValidValue?: Record<string, unknown> | unknown
    isInternalUpdate?: boolean
  }>(() => ({
    isValid: true,
    lastValidValue: hasValue ? value : defaultFormat ? undefined : {},
    isInternalUpdate: false,
  }))

  const lastValueRef = useRef(value)
  const isInternalUpdateRef = useRef(false)

  useEffect(() => {
    if (value !== lastValueRef.current && !isInternalUpdateRef.current) {
      try {
        const newHasValue = value !== undefined && value !== null && value !== ''
        let newEditorValue: string
        if (newHasValue) {
          newEditorValue = stringifyValue(value)
        } else if (defaultFormat) {
          newEditorValue = defaultFormat
        } else {
          newEditorValue = stringifyValue({})
        }

        setEditorValue(newEditorValue)
        setValidationState(prev => ({
          ...prev,
          isValid: true,
          lastValidValue: newHasValue ? value : defaultFormat ? undefined : {},
          isInternalUpdate: false,
        }))
        lastValueRef.current = value
      } catch (error) {
        console.warn('Failed to stringify value for JSON editor:', error)
      }
    }
  }, [value, defaultFormat, stringifyValue])

  const validateArrayElementTypes = useCallback(
    (data: unknown): { isValid: boolean; error?: string } => {
      if (!validateArrayElements || !arrayElementType) {
        return { isValid: true }
      }

      if (!Array.isArray(data)) {
        return { isValid: true }
      }

      for (let i = 0; i < data.length; i++) {
        const element = data[i]
        let isValid = false

        switch (arrayElementType) {
          case 'boolean':
            isValid = typeof element === 'boolean'
            break
          case 'integer':
            isValid = typeof element === 'number' && Number.isInteger(element)
            break
          case 'number':
            isValid = typeof element === 'number' && !isNaN(element)
            break
          case 'string':
            isValid = typeof element === 'string'
            break
          case 'object':
            isValid = typeof element === 'object' && element !== null && !Array.isArray(element)
            break
          case 'array':
            isValid = Array.isArray(element)
            break
          default:
            isValid = true
            break
        }

        if (!isValid) {
          const typeName = t(`workflowCanvas.jsonEditor.type.${arrayElementType}`)
          return {
            isValid: false,
            error: t('workflowCanvas.jsonEditor.arrayElementTypeMismatch', {
              index: i + 1,
              expectedType: typeName,
              actualType: t(`workflowCanvas.jsonEditor.type.${typeof element}`)
            }),
          }
        }
      }

      return { isValid: true }
    },
    [validateArrayElements, arrayElementType],
  )

  const parseJsonSafely = useCallback(
    (
      jsonString: string,
    ): {
      success: boolean
      data?: Record<string, unknown> | unknown
      error?: string
    } => {
      if (!jsonString.trim()) {
        return { success: true, data: defaultFormat ? undefined : {} }
      }

      try {
        const parsed = JSON.parse(jsonString)

        const arrayValidation = validateArrayElementTypes(parsed)
        if (!arrayValidation.isValid) {
          return { success: false, error: arrayValidation.error }
        }

        return { success: true, data: parsed }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Invalid JSON'
        return { success: false, error: errorMessage }
      }
    },
    [defaultFormat, validateArrayElementTypes],
  )

  const debouncedParse = useCallback(
    (jsonString: string) => {
      const timeoutId = setTimeout(() => {
        const result = parseJsonSafely(jsonString)

        setValidationState(prev => {
          const newState = {
            isValid: result.success,
            error: result.error,
            lastValidValue: result.success ? result.data : prev.lastValidValue,
            isInternalUpdate: result.success,
          }

          onValidationChange?.(newState.isValid, newState.error)

          if (result.success && onChange) {
            isInternalUpdateRef.current = true
            setTimeout(() => {
              onChange(result.data)
              setTimeout(() => {
                isInternalUpdateRef.current = false
              }, 50)
            }, 0)
          } else {
            isInternalUpdateRef.current = false
          }

          return newState
        })
      }, parseDelay)

      return () => clearTimeout(timeoutId)
    },
    [parseJsonSafely, parseDelay, onValidationChange, onChange],
  )

  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
    }
  }, [])

  const handleEditorChange = useCallback(
    (newValue: string) => {
      setEditorValue(newValue)

      if (cleanupRef.current) {
        cleanupRef.current()
      }

      if (!validateOnBlur) {
        cleanupRef.current = debouncedParse(newValue)
      } else {
        setValidationState(prev => ({
          ...prev,
          isValid: true,
          error: undefined,
        }))
      }
    },
    [debouncedParse, validateOnBlur],
  )

  const handleBlur = useCallback(() => {
    if (validateOnBlur) {
      const result = parseJsonSafely(editorValue)

      setValidationState(prev => {
        const newState = {
          isValid: result.success,
          error: result.error,
          lastValidValue: result.success ? result.data : prev.lastValidValue,
          isInternalUpdate: result.success,
        }

        onValidationChange?.(newState.isValid, newState.error)

        if (result.success && onChange) {
          isInternalUpdateRef.current = true
          setTimeout(() => {
            onChange(result.data)
            setTimeout(() => {
              isInternalUpdateRef.current = false
            }, 50)
          }, 0)
        } else {
          isInternalUpdateRef.current = false
        }

        return newState
      })
    }
  }, [validateOnBlur, editorValue, parseJsonSafely, onChange, onValidationChange])

  const formatJson = useCallback(() => {
    const result = parseJsonSafely(editorValue)
    if (result.success && result.data) {
      try {
        const formatted = JSON.stringify(result.data, null, 2)
        setEditorValue(formatted)
      } catch (error) {
        console.warn('Failed to format JSON:', error)
      }
    }
  }, [editorValue, parseJsonSafely])

  React.useImperativeHandle(
    ref,
    () => ({
      formatJson,
      getValue: () => validationState.lastValidValue,
      getEditorValue: () => editorValue,
      isValid: validationState.isValid,
      error: validationState.error,
    }),
    [formatJson, validationState, editorValue],
  )

  const defaultErrorRenderer = useCallback(
    (error: string) => (
      <div
        style={{
          fontSize: '12px',
          color: '#ff4d4f',
          marginTop: '4px',
          padding: '4px 8px',
          backgroundColor: '#fff2f0',
          border: '1px solid #ffccc7',
          borderRadius: '4px',
        }}
      >
        {t('workflowCanvas.jsonEditor.formatError')}: {error}
      </div>
    ),
    [],
  )

  const stableOptions = useMemo(
    () => ({
      tabSize: 2,
      indentUnit: 2,
      jsonValidation: true,
      autoFormat: true,
      ...options,
    }),
    [options],
  )

  const stableExtensions = useMemo(() => extensions || {}, [extensions])

  return (
    <div className="json-editor">
      <BaseEditor
        value={editorValue}
        onChange={handleEditorChange}
        onBlur={handleBlur}
        language="json"
        theme={theme}
        placeholder={placeholder || '{\n  "key": "value"\n}'}
        readonly={readonly}
        options={stableOptions}
        extensions={stableExtensions}
        className={mini ? 'mini-editor' : ''}
        minHeight={mini ? 24 : 200}
        lineNumbers={!mini}
        foldGutter={!mini}
        {...props}
      >
        {children}
      </BaseEditor>

      {showErrors &&
        !validationState.isValid &&
        validationState.error &&
        (renderError ? renderError(validationState.error) : defaultErrorRenderer(validationState.error))}
    </div>
  )
}

export const JsonCodeEditor = React.forwardRef(JsonCodeEditorWithEnhancedLogic)

export const loadJsonLanguage = () => Promise.resolve()

JsonCodeEditor.displayName = 'JsonCodeEditor'
