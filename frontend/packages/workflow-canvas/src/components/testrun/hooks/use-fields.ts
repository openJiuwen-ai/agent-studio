/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { TestRunFormField, TestRunFormMeta } from '../testrun-form/type'
import { t } from '../../../i18n'

const validateValue = (type: string, value: unknown): { isValid: boolean; error?: string } => {
  if (value === undefined || value === null || value === '') {
    return { isValid: true }
  }

  switch (type) {
    case 'integer': {
      const num = Number(value)
      if (isNaN(num) || !Number.isInteger(num)) {
        return {
          isValid: false,
          error: t('workflowCanvas.testrunForm.validation.integer'),
        }
      }
      return { isValid: true }
    }
    case 'number': {
      const num = Number(value)
      if (isNaN(num)) {
        return {
          isValid: false,
          error: t('workflowCanvas.testrunForm.validation.number'),
        }
      }
      return { isValid: true }
    }
    case 'boolean': {
      if (typeof value !== 'boolean') {
        return {
          isValid: false,
          error: t('workflowCanvas.testrunForm.validation.boolean'),
        }
      }
      return { isValid: true }
    }
    case 'object': {
      if (typeof value === 'string') {
        try {
          const parsed = JSON.parse(value)
          if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
            return {
              isValid: false,
              error: t('workflowCanvas.testrunForm.validation.object'),
            }
          }
        } catch {
          return {
            isValid: false,
            error: t('workflowCanvas.testrunForm.validation.jsonFormat'),
          }
        }
      }
      return { isValid: true }
    }
    case 'array': {
      if (typeof value === 'string') {
        try {
          const parsed = JSON.parse(value)
          if (!Array.isArray(parsed)) {
            return {
              isValid: false,
              error: t('workflowCanvas.testrunForm.validation.array'),
            }
          }
        } catch {
          return {
            isValid: false,
            error: t('workflowCanvas.testrunForm.validation.arrayFormat'),
          }
        }
      } else if (!Array.isArray(value) && value !== undefined && value !== null) {
        return {
          isValid: false,
          error: t('workflowCanvas.testrunForm.validation.array'),
        }
      }
      return { isValid: true }
    }
    case 'file': {
      if (typeof value === 'object' && value !== null) {
        const fileValue = value as Record<string, unknown>
        const url = fileValue.url
        const objectKey = fileValue.object_key
        if (!url || (typeof url === 'string' && url.trim() === '')) {
          return { isValid: false, error: t('workflowCanvas.formMaterials.input.fileUrlError') }
        }
        if (!objectKey || (typeof objectKey === 'string' && objectKey.trim() === '')) {
          return { isValid: false, error: t('workflowCanvas.formMaterials.input.fileUrlError') }
        }
      } else {
        return { isValid: false, error: t('workflowCanvas.formMaterials.input.fileUrlError') }
      }
      return { isValid: true }
    }
    case 'string':
    default:
      return { isValid: true }
  }
}

export const useFields = (params: {
  formMeta: TestRunFormMeta
  values: Record<string, unknown>
  setValues: (values: Record<string, unknown>) => void
}): TestRunFormField[] => {
  const { formMeta, values, setValues } = params

  const fields: TestRunFormField[] = formMeta.map(meta => {
    const getCurrentValue = (): unknown => {
      const rawValue = values[meta.name] ?? meta.defaultValue
      if (rawValue === null || rawValue === undefined) {
        return rawValue
      }

      if ((meta.type === 'object' || meta.type === 'array') && typeof rawValue === 'string') {
        try {
          return JSON.parse(rawValue)
        } catch {
          return rawValue
        }
      }
      return rawValue
    }

    const currentValue = getCurrentValue()
    const validation = validateValue(meta.type, currentValue)

    const handleChange = (newValue: unknown): void => {
      if (meta.type === 'object' || meta.type === 'array') {
        try {
          if (newValue === '' || newValue === null || newValue === undefined) {
            setValues(prevValues => ({
              ...prevValues,
              [meta.name]: meta.type === 'array' ? [] : null,
            }))
          } else {
            let parsedValue: unknown
            if (typeof newValue === 'string') {
              parsedValue = JSON.parse(newValue)
            } else {
              parsedValue = newValue
            }

            setValues(prevValues => ({
              ...prevValues,
              [meta.name]: parsedValue,
            }))
          }
        } catch (error) {
          console.warn('[use-fields] Failed to parse JSON value:', error instanceof Error ? error.message : String(error))
        }
      } else {
        setValues(prevValues => ({
          ...prevValues,
          [meta.name]: newValue,
        }))
      }
    }

    return {
      ...meta,
      value: currentValue,
      onChange: handleChange,
      error: validation.error,
      isValid: validation.isValid,
    }
  })

  return fields
}
