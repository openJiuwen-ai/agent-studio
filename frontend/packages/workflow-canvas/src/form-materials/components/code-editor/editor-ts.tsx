/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo } from 'react'

import { BaseEditor } from '../base-editor'
import type { BaseEditorProps } from '../base-editor'

export interface EditorTsProps extends Omit<BaseEditorProps, 'language'> {}

/**
 * TypeScript-specific code editor component
 * Maintains 1:1 API compatibility with the original TypeScriptCodeEditor
 */
export const TypeScriptCodeEditor: React.FC<EditorTsProps> = ({
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
  const stableOptions = useMemo(
    () => ({
      // TypeScript-specific compiler options (equivalent to original worker setup)
      compilerOptions: {
        lib: ['es2015', 'dom'],
        noImplicitAny: false,
      },
      ...options,
    }),
    [options],
  )

  // Create stable extensions object to prevent BaseEditor recreation
  const stableExtensions = useMemo(() => extensions || {}, [extensions])

  // 提取props中的maxHeight，如果未提供则使用默认值
  const { maxHeight: propsMaxHeight, ...restProps } = props
  const maxHeight = propsMaxHeight ?? (mini ? 200 : undefined)

  return (
    <BaseEditor
      value={value}
      onChange={onChange}
      language="typescript"
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
export const loadTypescriptLanguage = () => Promise.resolve()

TypeScriptCodeEditor.displayName = 'TypeScriptCodeEditor'
