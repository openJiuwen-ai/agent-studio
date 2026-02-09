/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { validateFlowValue } from '../../form-materials'
import { t } from '../../i18n'

/**
 * Validator configuration options
 */
export interface ValidatorOptions {
  /** Error message */
  message?: string
  /** Whether required */
  required?: boolean
  /** Include private scope */
  includePrivateScope?: boolean
  /** Custom error messages */
  errorMessages?: {
    required?: string
    unknownVariable?: string
  }
  /** Empty message (for return content validation) */
  emptyMessage?: string
  /** Result message (for return content validation) */
  resultMessage?: string
}

/**
 * Input parameters validator configuration
 */
export interface InputParametersValidatorOptions extends ValidatorOptions {
  /** Required parameters list */
  requiredParams?: string[]
  /** Parameter name extraction regex */
  namePattern?: RegExp
  /** Whether to check empty content */
  checkEmptyContent?: boolean
}

/**
 * Create title validator
 * @param options - Validator configuration
 * @returns Title validator function
 */
export const createTitleValidator = (options: ValidatorOptions = {}) => {
  return ({ value }: { value: string }) => {
    if (value) return undefined
    return options.message || t('workflowCanvas.validation.titleRequired')
  }
}

/**
 * Create input parameters validator
 * @param options - Validator configuration
 * @returns Input parameters validator function
 */
export const createInputParametersValidator = (options: InputParametersValidatorOptions = {}) => {
  const {
    requiredParams = [],
    namePattern = /^inputs\.inputParameters\./,
    checkEmptyContent = true,
    required = false,
    includePrivateScope = false,
    errorMessages = {},
  } = options

  return ({ value, context, name, formValues }: any) => {
    // Extract property name
    const valuePropertyKey = name.replace(namePattern, '')

    // Check if it's a required parameter
    const isRequired = required || requiredParams.includes(valuePropertyKey)

    // If parameter exists, check if its value is empty
    if (value && checkEmptyContent) {
      if (value?.type === 'constant' && (value?.content === undefined || value?.content === null || value?.content === '')) {
        return t('workflowCanvas.validation.paramEmpty', { param: valuePropertyKey })
      }
    }

    // Use validateFlowValue for variable reference validation
    return validateFlowValue(value, {
      node: context.node,
      required: isRequired,
      includePrivateScope,
      errorMessages: {
        required: errorMessages.required || t('workflowCanvas.validation.paramRequired', { param: valuePropertyKey }),
        unknownVariable: errorMessages.unknownVariable || t('workflowCanvas.validation.variableUnknown'),
      },
    })
  }
}

/**
 * Create prompt validator
 * @param options - Validator configuration
 * @returns Prompt validator function
 */
export const createPromptValidator = (options: ValidatorOptions = {}) => {
  return ({ value }: any) => {
    const content = value?.content ?? ''
    if (!content || content.trim().length === 0) {
      return options.message || t('workflowCanvas.validation.promptRequired')
    }
    return undefined
  }
}

/**
 * Create output count validator
 * @param minCount - Minimum output count
 * @param options - Validator configuration
 * @returns Output count validator function
 */
export const createOutputCountValidator = (minCount: number, options: ValidatorOptions = {}) => {
  return ({ value }: any) => {
    if (!value?.properties) {
      return options.message || t('workflowCanvas.validation.outputCountMin', { count: minCount })
    }
    const outputCount = Object.keys(value.properties).length
    if (outputCount >= minCount) return undefined
    return options.message || t('workflowCanvas.validation.outputCountMin', { count: minCount })
  }
}

/**
 * Create condition validator
 * @param options - Validator configuration
 * @returns Condition validator function
 */
export const createConditionValidator = (options: ValidatorOptions = {}) => {
  return ({ value }: any) => {
    // Handle is_empty and is_not_empty operators
    if (value?.operator === 'is_empty' || value?.operator === 'is_not_empty') {
      if (!value?.left) {
        return options.message || t('workflowCanvas.validation.conditionIncomplete')
      }
      return undefined
    }

    // Handle other operators that require left and right values
    if (!value?.left || !value?.right) {
      return options.message || t('workflowCanvas.validation.conditionIncomplete')
    }
    return undefined
  }
}

/**
 * Create return content validator
 * @param options - Validator configuration
 * @returns Return content validator function
 */
export const createReturnContentValidator = (options: ValidatorOptions = {}) => {
  return ({ value, formValues }: any) => {
    if (formValues?.exceptionConfig?.processType === 'return_content') {
      if (!value || Object.keys(value).length === 0) {
        return options.emptyMessage || t('workflowCanvas.validation.returnContentEmpty')
      }
      if (!value.result) {
        return options.resultMessage || t('workflowCanvas.validation.resultRequired')
      }
    }
    return undefined
  }
}

/**
 * Create model validator
 * @param options - Validator configuration
 * @returns Model validator function
 */
export const createModelValidator = (options: ValidatorOptions = {}) => {
  return ({ value }: any) => {
    // Check if model is configured
    if (!value || !value.id || value.id === '') {
      return options.message || t('workflowCanvas.validation.modelRequired')
    }
    return undefined
  }
}

/**
 * Create streaming template validator
 * @param options - Validator configuration
 * @returns Streaming template validator function
 */
export const createStreamingTemplateValidator = (options: ValidatorOptions = {}) => {
  return ({ value, formValues }: any) => {
    // If streaming is enabled, check if output template is empty
    if (formValues?.inputs?.streaming === true) {
      const content = formValues?.inputs?.content?.content ?? ''
      if (!content || content.trim().length === 0) {
        return options.message || t('workflowCanvas.validation.streamingTemplateEmpty')
      }
    }
    return undefined
  }
}

/**
 * Predefined common validators
 */
export const commonValidators = {
  /** Default title validator */
  title: createTitleValidator(),

  /** Default input parameters validator */
  inputParameters: createInputParametersValidator(),

  /** Optional input parameters validator */
  optionalInputParameters: createInputParametersValidator({ required: false }),

  /** Dual output validator */
  dualOutput: createOutputCountValidator(2),

  /** Condition validator */
  condition: createConditionValidator(),

  /** Return content validator */
  returnContent: createReturnContentValidator(),

  /** Model validator */
  model: createModelValidator(),

  /** Streaming template validator */
  streamingTemplate: createStreamingTemplateValidator(),
}
