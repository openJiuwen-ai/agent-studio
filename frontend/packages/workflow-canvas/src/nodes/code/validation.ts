/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { commonValidators, createInputParametersValidator } from '../../utils/validation'
import { t } from '../../i18n'

/**
 * Code 节点的完整校验配置
 */
export const validation = {
  'inputs.inputParameters.*': ({ value, context, name, formValues }: any) => {
    const valuePropertyKey = name.replace(/^inputs\.inputParameters\./, '')
    const required = formValues.inputs?.inputParameters?.required || []

    // 创建动态验证器
    const validator = createInputParametersValidator({
      requiredParams: required,
      errorMessages: {
        required: t('workflowCanvas.validation.fieldRequired'),
        unknownVariable: t('workflowCanvas.validation.variableReferencedNotFound'),
      },
    })

    return validator({ value, context, name, formValues })
  },
  'exceptionConfig.returnContent': commonValidators.returnContent,
}
