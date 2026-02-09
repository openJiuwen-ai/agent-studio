/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { commonValidators } from '../../utils/validation'
import { validateFlowValue, ConditionPresetOp, checkPortConnection } from '../../form-materials'
import { t } from '../../i18n'

const validateConstantValueSchema = (value: any): string | undefined => {
  if (value?.type !== 'constant' || !value?.schema) {
    return undefined
  }

  const { schema, content } = value
  const originalExpectedType = schema.type

  if (!originalExpectedType || originalExpectedType === 'any') {
    return undefined
  }

  const formatToBaseType: Record<string, string> = {
    'date-time': 'string',
  }
  const expectedType = formatToBaseType[originalExpectedType] || originalExpectedType

  let actualType: string
  if (content === null || content === undefined) {
    actualType = 'null'
  } else if (Array.isArray(content)) {
    actualType = 'array'
  } else if (typeof content === 'object') {
    actualType = 'object'
  } else {
    actualType = typeof content
  }

  if (actualType === 'number' && Number.isInteger(content) && expectedType === 'integer') {
    actualType = 'integer'
  }

  if (actualType !== expectedType) {
    return t('workflowCanvas.nodes.condition.typeMismatch', {
      expectedType: t(`workflowCanvas.nodes.condition.type.${expectedType}`),
      actualType: t(`workflowCanvas.nodes.condition.type.${actualType}`),
    })
  }

  if (originalExpectedType === 'date-time') {
    const dateTimeRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/
    if (!dateTimeRegex.test(content)) {
      return t('workflowCanvas.nodes.condition.invalidDateTimeFormat')
    }
  }

  return undefined
}

export const validateBranch = ({ value }: any) => {
  if (value?.conditions && value.conditions.length === 0) {
    return undefined
  }
  return undefined
}

export const validateConditionValue = ({ value, context }: any) => {
  if (!value) {
    return undefined
  }

  if (value?.type === 'constant') {
    if (value?.content === undefined || value?.content === null || value?.content === '') {
      return t('workflowCanvas.nodes.condition.conditionValueCannotBeEmpty')
    }

    const schemaValidationError = validateConstantValueSchema(value)
    if (schemaValidationError) {
      return schemaValidationError
    }
  }

  const validationResult = validateFlowValue(value, {
    node: context.node,
    required: true,
    includePrivateScope: false,
    errorMessages: {
      required: t('workflowCanvas.nodes.condition.conditionValueRequired'),
      unknownVariable: t('workflowCanvas.validation.variableUnknown'),
    },
  })

  return validationResult?.message
}

export const validateCondition = ({ value, context }: any) => {
  if (!value) {
    return undefined
  }

  const { operator, left, right } = value

  if (operator === ConditionPresetOp.IS_EMPTY || operator === ConditionPresetOp.IS_NOT_EMPTY) {
    if (!left) {
      return t('workflowCanvas.nodes.condition.pleaseSelectVariableToCheck')
    }
    return validateConditionValue({ value: left, context })
  }

  if (!left) {
    return t('workflowCanvas.nodes.condition.pleaseSelectLeftValue')
  }
  if (!right) {
    return t('workflowCanvas.nodes.condition.pleaseSelectRightValue')
  }

  const leftError = validateConditionValue({ value: left, context })
  if (leftError) {
    return leftError
  }

  const rightError = validateConditionValue({ value: right, context })
  if (rightError) {
    return rightError
  }

  return undefined
}

export const validateBranchConnections = ({ value, context }: any) => {
  if (!value || !Array.isArray(value) || value.length === 0) {
    return undefined
  }

  const node = context.node
  if (!node) {
    return undefined
  }

  const branchPorts = value.map((branch: any) => branch.branchId).filter(Boolean)

  const connectionStatus = branchPorts.map(branchId => ({
    branchId,
    hasConnection: checkPortConnection(node, branchId, 'output'),
  }))

  const unconnectedBranches = connectionStatus.filter(status => !status.hasConnection)

  if (unconnectedBranches.length > 0) {
    const unconnectedBranchInfo = unconnectedBranches.map(({ branchId }) => {
      const index = value.findIndex((branch: any) => branch.branchId === branchId)
      const isElseBranch = value[index]?.conditions?.length === 0

      if (isElseBranch) {
        return { type: 'else', index }
      } else if (index === 0) {
        return { type: 'if', index }
      } else {
        return { type: 'elseIf', index }
      }
    })

    if (unconnectedBranchInfo.length === 1) {
      const { type } = unconnectedBranchInfo[0]
      switch (type) {
        case 'if':
          return t('workflowCanvas.nodes.condition.ifBranchMustBeConnected')
        case 'else':
          return t('workflowCanvas.nodes.condition.elseBranchMustBeConnected')
        case 'elseIf':
          return t('workflowCanvas.nodes.condition.elseIfBranchMustBeConnected')
      }
    } else {
      const branchTypes = unconnectedBranchInfo.map(({ type }) => {
        switch (type) {
          case 'if':
            return t('workflowCanvas.nodes.condition.branchType.if')
          case 'else':
            return t('workflowCanvas.nodes.condition.branchType.else')
          case 'elseIf':
            return t('workflowCanvas.nodes.condition.branchType.elseIf')
        }
      })

      if (branchTypes.length === unconnectedBranches.length) {
        return t('workflowCanvas.nodes.condition.branchesMustBeConnected', { types: branchTypes.join(', ') })
      }
    }
  }

  return undefined
}

export const validation = {
  'branches.*': validateBranch,
  'branches.*.conditions.*': validateCondition,
  branches: validateBranchConnections,
}
