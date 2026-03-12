/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormData } from './type'

export const validation = async (values: FormData) => {
  const errors: any = {}
  const warnings: any[] = []

  // Validate model is selected
  if (!values.inputs?.llmParam?.model?.id) {
    errors['inputs.llmParam.model'] = 'Model is required'
  }

  // Validate max_iterations is within valid range
  if (values.max_iterations < 1 || values.max_iterations > 20) {
    warnings.push({
      field: 'max_iterations',
      message: 'Max iterations should be between 1 and 20',
    })
  }

  return { errors, warnings }
}
