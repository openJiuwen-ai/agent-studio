/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo } from 'react'

import { BaseEditor } from '../base-editor'
import type { BaseEditorProps } from '../base-editor'

export interface EditorPythonProps extends Omit<BaseEditorProps, 'language'> {}

/**
 * Python-specific code editor component
 * Maintains 1:1 API compatibility with the original PythonCodeEditor
 */
export const PythonCodeEditor: React.FC<EditorPythonProps> = ({
  value,
  onChange,
  theme = 'light',
  placeholder,
  readonly = false,
  options,
  mini,
  children,
  extensions,
  ...props
}) => {
  // Create stable options object to prevent BaseEditor recreation
  const stableOptions = useMemo(() => options || {}, [options])

  // Create stable extensions object to prevent BaseEditor recreation
  const stableExtensions = useMemo(() => extensions || {}, [extensions])

  // 提取props中的maxHeight，如果未提供则使用默认值
  const { maxHeight: propsMaxHeight, ...restProps } = props
  const maxHeight = propsMaxHeight ?? (mini ? 200 : undefined)

  return (
    <BaseEditor
      value={value}
      onChange={onChange}
      language="python"
      theme={theme}
      placeholder={placeholder}
      readonly={readonly}
      options={stableOptions}
      extensions={stableExtensions}
      className={mini ? 'mini-editor' : ''}
      minHeight={mini ? 24 : 200}
      maxHeight={maxHeight}
      lineNumbers={!mini}
      foldGutter={!mini}
      {...restProps}
    >
      {children}
    </BaseEditor>
  )
}

// Legacy export for compatibility
export const loadPythonLanguage = () => Promise.resolve()

PythonCodeEditor.displayName = 'PythonCodeEditor'
