/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useCallback } from 'react'

import { validateRequiredFields, validateBasicTypes } from '../utils/validation'
import { TestRunFormMetaItem } from '../testrun-form/type'
import { t } from '../../../i18n'

export function useFormValidation() {
  const validate = useCallback((
    values: Record<string, unknown>,
    formMeta: TestRunFormMetaItem[],
  ): string[] | null => {
    const missingRequired = validateRequiredFields(values, formMeta)
    if (missingRequired.length > 0) {
      return [t('workflowCanvas.testrunForm.missingRequiredFields', { fields: missingRequired.join(', ') })]
    }

    const typeValidationErrors = validateBasicTypes(values, formMeta)
    if (typeValidationErrors.length > 0) {
      return typeValidationErrors
    }

    return null
  }, [])

  return { validate }
}
