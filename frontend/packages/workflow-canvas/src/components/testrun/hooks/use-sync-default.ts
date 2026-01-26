/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useEffect } from 'react'

import { TestRunFormMeta, TestRunFormMetaItem } from '../testrun-form/type'

const getDefaultValue = (meta: TestRunFormMetaItem) => {
  const defaultValue = meta.defaultValue

  if (['object', 'array', 'map'].includes(meta.type)) {
    if (typeof defaultValue === 'string') {
      if (defaultValue === '') {
        return meta.type === 'array' ? [] : null
      }
      try {
        return JSON.parse(defaultValue)
      } catch {
        return defaultValue
      }
    }
  }

  return defaultValue
}

export const useSyncDefault = (params: {
  formMeta: TestRunFormMeta
  values: Record<string, unknown>
  setValues: (values: Record<string, unknown>) => void
}) => {
  const { formMeta, values, setValues } = params

  // 添加对 formMeta 长度的依赖，确保数组内容变化时也能触发
  const formMetaKey = JSON.stringify(formMeta.map(m => ({ name: m.name, defaultValue: m.defaultValue })))

  useEffect(() => {
    // 如果没有 formMeta，跳过
    if (!formMeta || formMeta.length === 0) {
      return
    }

    // 构建包含所有默认值的完整对象和字段名集合
    const defaultValues: Record<string, unknown> = {}
    const fieldNames = new Set<string>()
    formMeta.forEach(meta => {
      fieldNames.add(meta.name)
      if (meta.defaultValue !== undefined) {
        defaultValues[meta.name] = getDefaultValue(meta)
      }
    })

    setValues(prevValues => {
      const mergedValues = { ...defaultValues }

      Object.keys(prevValues).forEach(key => {
        if (fieldNames.has(key) && prevValues[key] !== undefined && prevValues[key] !== null) {
          const meta = formMeta.find(m => m.name === key)
          if (meta?.type === 'array') {
            mergedValues[key] = prevValues[key]
          } else if (meta?.type === 'object') {
            if (typeof prevValues[key] === 'object' && Object.keys(prevValues[key] || {}).length > 0) {
              mergedValues[key] = prevValues[key]
            }
          } else if (prevValues[key] !== '') {
            mergedValues[key] = prevValues[key]
          }
        }
      })

      return mergedValues
    })
  }, [formMetaKey])
}
