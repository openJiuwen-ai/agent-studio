/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../../utils/nanoid-custom'
import { t } from '../../../i18n'

export interface ConditionValue {
  left?: { type: 'ref'; content: string[] }
  operator?: string | number
  right?: { type: 'constant'; content: unknown; schema: { type: string; extra?: { weak?: boolean } } }
}

export interface BranchValue {
  conditions: ConditionValue[]
  logic: 1 | 2
  branchId: string
}

export type BranchType = 'if' | 'elseIf' | 'else'

export const generateBranchId = (): string => {
  return `branch_${customNanoid(8)}`
}

export const generateBranchPortId = (branch: BranchValue): string => {
  return branch.branchId || 'default'
}

export const normalizeBranches = (value: unknown): BranchValue[] => {
  if (!Array.isArray(value)) return []

  return value.map(branch => {
    if (!branch || typeof branch !== 'object') {
      return {
        conditions: [],
        logic: 2,
        branchId: generateBranchId(),
      }
    }

    return {
      conditions: Array.isArray(branch.conditions) ? branch.conditions : [],
      logic: branch.logic || 2,
      branchId: branch.branchId || generateBranchId(),
    }
  })
}

export const determineBranchType = (branch: BranchValue, index: number, branches: BranchValue[]): BranchType => {
  if (branch && branch.conditions.length === 0) {
    return 'else'
  }
  if (index === 0) {
    return 'if'
  }

  const isLast = index === branches.length - 1
  const hasElseBranch = branches.some(b => b && b.conditions.length === 0)

  if (isLast && !hasElseBranch) {
    return 'else'
  }

  return 'elseIf'
}

export const getBranchTitle = (type: BranchType): string => {
  switch (type) {
    case 'if':
      return t('workflowCanvas.nodes.condition.branchType.if')
    case 'elseIf':
      return t('workflowCanvas.nodes.condition.branchType.elseIf')
    case 'else':
      return t('workflowCanvas.nodes.condition.branchType.else')
    default:
      return t('workflowCanvas.nodes.condition.branchType.if')
  }
}
