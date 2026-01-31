/**
 * Enhanced JSON Code Editor with built-in parsing logic
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'

import { BaseEditor } from '../base-editor'
import type { BaseEditorProps } from '../base-editor'

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

// Enhanced type for ref
export interface JsonCodeEditorRef {
  formatJson: () => void
  getValue: () => Record<string, unknown> | unknown
  getEditorValue: () => string
  isValid: boolean
  error?: string
}

/**
 * Enhanced JSON Editor Component
 *
 * Features:
 * - Automatic JSON.stringify/parse handling
 * - Debounced parsing to avoid errors during typing
 * - Built-in error handling and validation
 * - Clean separation between display and data states
 * - Consistent behavior across all usage
 */
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
  const stringifyValue = useCallback((val: unknown) => {
    return compact ? JSON.stringify(val) : JSON.stringify(val, null, 2)
  }, [compact])

  const [editorValue, setEditorValue] = useState<string>(() => {
    try {
      if (value !== undefined && value !== null) {
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

  // Validation state
  const [validationState, setValidationState] = useState<{
    isValid: boolean
    error?: string
    lastValidValue?: Record<string, unknown> | unknown
    isInternalUpdate?: boolean
  }>(() => ({
    isValid: true,
    lastValidValue: value !== undefined && value !== null ? value : defaultFormat ? undefined : {},
    isInternalUpdate: false,
  }))

  // Sync external value changes to editor using ref to avoid unnecessary updates
  const lastValueRef = useRef(value)

  // Use ref to track internal update state to avoid useEffect dependency cycles
  const isInternalUpdateRef = useRef(false)

  useEffect(() => {
    if (value !== lastValueRef.current && !isInternalUpdateRef.current) {
      try {
        let newEditorValue: string
        if (value !== undefined && value !== null) {
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
          lastValidValue: value !== undefined && value !== null ? value : defaultFormat ? undefined : {},
          isInternalUpdate: false,
        }))
        lastValueRef.current = value
      } catch (error) {
        console.warn('Failed to stringify value for JSON editor:', error)
      }
    }
  }, [value, defaultFormat, stringifyValue])

  // Validate array element types
  const validateArrayElementTypes = useCallback(
    (data: unknown): { isValid: boolean; error?: string } => {
      if (!validateArrayElements || !arrayElementType) {
        return { isValid: true }
      }

      // Only validate if data is an array
      if (!Array.isArray(data)) {
        return { isValid: true }
      }

      // Validate each element in the array
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
            // For unknown types, allow any value
            isValid = true
            break
        }

        if (!isValid) {
          const typeName =
            arrayElementType === 'boolean'
              ? '布尔值'
              : arrayElementType === 'integer'
                ? '整数'
                : arrayElementType === 'number'
                  ? '数字'
                  : arrayElementType === 'string'
                    ? '字符串'
                    : arrayElementType === 'object'
                      ? '对象'
                      : arrayElementType === 'array'
                        ? '数组'
                        : arrayElementType

          return {
            isValid: false,
            error: `数组第${i + 1}个元素类型不匹配，期望${typeName}类型，实际为${typeof element}类型`,
          }
        }
      }

      return { isValid: true }
    },
    [validateArrayElements, arrayElementType],
  )

  // Parse JSON with error handling
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

        // Validate array element types if enabled
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

  // Debounced parsing function
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

          // Notify parent about validation changes
          onValidationChange?.(newState.isValid, newState.error)

          // Trigger onChange only on successful parse (deferred to next tick)
          // For failed validation, do NOT call onChange to preserve other form field values
          if (result.success && onChange) {
            // Set the internal update flag BEFORE calling onChange to prevent race conditions
            isInternalUpdateRef.current = true
            setTimeout(() => {
              onChange(result.data)
              // Reset the flag after the change has been processed
              setTimeout(() => {
                isInternalUpdateRef.current = false
              }, 50)
            }, 0)
          } else {
            // Reset the flag immediately for failed validation
            isInternalUpdateRef.current = false
          }

          return newState
        })
      }, parseDelay)

      // Cleanup function
      return () => clearTimeout(timeoutId)
    },
    [parseJsonSafely, parseDelay],
  )

  // Store cleanup function ref
  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
    }
  }, [])

  // Handle editor value changes
  const handleEditorChange = useCallback(
    (newValue: string) => {
      setEditorValue(newValue)

      // Clear previous timeout
      if (cleanupRef.current) {
        cleanupRef.current()
      }

      if (!validateOnBlur) {
        cleanupRef.current = debouncedParse(newValue)
      } else {
        // When validateOnBlur is true, hide errors during typing
        setValidationState(prev => ({
          ...prev,
          isValid: true,
          error: undefined,
        }))
      }
    },
    [debouncedParse, validateOnBlur],
  )

  // Handle blur event for validation
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
          // Set the internal update flag BEFORE calling onChange to prevent race conditions
          isInternalUpdateRef.current = true
          setTimeout(() => {
            onChange(result.data)
            // Reset the flag after the change has been processed
            setTimeout(() => {
              isInternalUpdateRef.current = false
            }, 50)
          }, 0)
        } else {
          // Reset the flag immediately for failed validation
          isInternalUpdateRef.current = false
        }

        return newState
      })
    }
  }, [validateOnBlur, editorValue, parseJsonSafely, onChange, onValidationChange])

  // Format JSON on demand (optional utility)
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

  // Expose methods via ref
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

  // Default error renderer
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
        JSON格式错误: {error}
      </div>
    ),
    [],
  )

  // Create stable options object to prevent BaseEditor recreation
  const stableOptions = useMemo(
    () => ({
      // JSON-specific options
      tabSize: 2,
      indentUnit: 2,
      jsonValidation: true,
      autoFormat: true,
      ...options,
    }),
    [options],
  )

  // Create stable extensions object to prevent BaseEditor recreation
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

// Export both enhanced version with ref and legacy version
export const JsonCodeEditor = React.forwardRef(JsonCodeEditorWithEnhancedLogic)

// Legacy export for compatibility
export const loadJsonLanguage = () => Promise.resolve()

JsonCodeEditor.displayName = 'JsonCodeEditor'
