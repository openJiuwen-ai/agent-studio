/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeEntity, getNodeScope } from '@flowgram.ai/free-layout-editor'
import { JsonSchemaUtils } from '@flowgram.ai/json-schema'

import { FlowValueUtils, type AssignValueType, type IFlowRefValue } from '../../form-materials'
import { t } from '../../i18n'

interface VariableValidationContext {
  value?: any
  context: {
    node: FlowNodeEntity
  }
  name?: string
  formValues?: any
}

/**
 * Check if right schema can be assigned to left schema
 */
const isTypeCompatible = (leftSchema: any, rightSchema: any): boolean => {
  if (!leftSchema || !rightSchema) {
    return true // If we can't determine the type, allow it
  }

  const leftType = leftSchema.type
  const rightType = rightSchema.type

  // If either is any/undefined, allow
  if (!leftType || !rightType || leftType === 'any' || rightType === 'any') {
    return true
  }

  // Same type
  if (leftType === rightType) {
    return true
  }

  // Number and integer are compatible
  if (
    (leftType === 'number' && rightType === 'integer') ||
    (leftType === 'integer' && rightType === 'number')
  ) {
    return true
  }

  return false
}

/**
 * Validate that left and right side types are compatible
 */
export const validateAssignTypeCompatibility = ({ value, context }: VariableValidationContext) => {
  const assignItem = value as AssignValueType

  if (!assignItem || assignItem.operator !== 'assign') {
    return undefined
  }

  const left = assignItem.left as IFlowRefValue | undefined
  const right = assignItem.right

  // Skip if left or right is not configured
  if (!left?.content || !right) {
    return undefined
  }

  const scope = getNodeScope(context.node)

  // Get left variable schema
  const leftVariable = scope.available.getByKeyPath(left.content)
  const leftSchema = leftVariable?.type
    ? JsonSchemaUtils.astToSchema(leftVariable.type)
    : undefined

  // Get right value schema using existing utility
  const rightSchema = FlowValueUtils.inferJsonSchema(right, scope)

  if (!leftSchema || !rightSchema) {
    return undefined
  }

  if (!isTypeCompatible(leftSchema, rightSchema)) {
    return t('workflowCanvas.nodes.variable.typeMismatch', {
      leftType: leftSchema.type || 'unknown',
      rightType: rightSchema.type || 'unknown',
    })
  }

  return undefined
}

/**
 * Validate assign array
 */
export const validateAssign = ({ value }: VariableValidationContext) => {
  if (!value || !Array.isArray(value)) {
    return t('workflowCanvas.nodes.variable.assignmentConfigEmpty')
  }
  if (value.length === 0) {
    return t('workflowCanvas.nodes.variable.atLeastOneAssignment')
  }
  return undefined
}

/**
 * Validate operator field
 */
export const validateOperator = ({ value }: VariableValidationContext) => {
  if (!value) {
    return t('workflowCanvas.nodes.variable.operatorEmpty')
  }
  if (value !== 'assign') {
    return t('workflowCanvas.nodes.variable.onlyAssignSupported')
  }
  return undefined
}

/**
 * Validate left variable
 */
export const validateLeft = ({ value }: VariableValidationContext) => {
  if (!value) {
    return t('workflowCanvas.nodes.variable.leftVariableEmpty')
  }
  return undefined
}

/**
 * Validate left variable type
 */
export const validateLeftType = ({ value }: VariableValidationContext) => {
  if (!value) {
    return t('workflowCanvas.nodes.variable.leftVariableTypeEmpty')
  }
  if (value !== 'ref') {
    return t('workflowCanvas.nodes.variable.leftVariableMustBeRef')
  }
  return undefined
}

/**
 * Validate left content
 */
export const validateLeftContent = ({ value }: VariableValidationContext) => {
  if (!value || !Array.isArray(value)) {
    return t('workflowCanvas.nodes.variable.leftRefPathEmpty')
  }
  if (value.length < 2) {
    return t('workflowCanvas.nodes.variable.leftRefPathMustContain')
  }
  if (value.some((item: any) => !item || typeof item !== 'string')) {
    return t('workflowCanvas.nodes.variable.leftRefPathNoEmpty')
  }
  return undefined
}

/**
 * Validate right value
 */
export const validateRight = ({ value }: VariableValidationContext) => {
  if (!value) {
    return t('workflowCanvas.nodes.variable.rightValueEmpty')
  }
  return undefined
}

/**
 * Validate right value type
 */
export const validateRightType = ({ value }: VariableValidationContext) => {
  if (!value) {
    return t('workflowCanvas.nodes.variable.rightValueTypeEmpty')
  }
  const validTypes = ['constant', 'ref', 'expression', 'template']
  if (!validTypes.includes(value)) {
    return t('workflowCanvas.nodes.variable.rightValueTypeInvalid')
  }
  return undefined
}

export const validation = {
  assign: validateAssign,
  'assign.*.operator': validateOperator,
  'assign.*.left': validateLeft,
  'assign.*.left.type': validateLeftType,
  'assign.*.left.content': validateLeftContent,
  'assign.*.right': validateRight,
  'assign.*.right.type': validateRightType,
  'assign.*': validateAssignTypeCompatibility,
}
