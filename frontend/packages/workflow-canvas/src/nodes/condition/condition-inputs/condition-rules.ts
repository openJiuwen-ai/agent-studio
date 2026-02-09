/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { IConditionRule, ConditionOpConfigs, ConditionPresetOp } from '../../../form-materials'
import { t } from '../../../i18n'

// 自定义操作符配置，支持国际化标签（使用 getter 延迟翻译）
export const conditionOps: ConditionOpConfigs = {
  [ConditionPresetOp.EQ]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.eq') },
    abbreviation: '=',
  },
  [ConditionPresetOp.NEQ]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.neq') },
    abbreviation: '≠',
  },
  [ConditionPresetOp.GT]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.gt') },
    abbreviation: '>',
  },
  [ConditionPresetOp.GTE]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.gte') },
    abbreviation: '>=',
  },
  [ConditionPresetOp.LT]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.lt') },
    abbreviation: '<',
  },
  [ConditionPresetOp.LTE]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.lte') },
    abbreviation: '<=',
  },
  [ConditionPresetOp.CONTAINS]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.contains') },
    abbreviation: '⊇',
  },
  [ConditionPresetOp.NOT_CONTAINS]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.notContains') },
    abbreviation: '⊉',
  },
  [ConditionPresetOp.IS_EMPTY]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.isEmpty') },
    abbreviation: '=',
    rightDisplay: 'Empty',
  },
  [ConditionPresetOp.IS_NOT_EMPTY]: {
    get label() { return t('workflowCanvas.nodes.condition.operators.isNotEmpty') },
    abbreviation: '≠',
    rightDisplay: 'Empty',
  },
}

// 字符串条件规则
export const stringConditionRules: IConditionRule = {
  [ConditionPresetOp.EQ]: 'string',
  [ConditionPresetOp.NEQ]: 'string',
  [ConditionPresetOp.CONTAINS]: 'string',
  [ConditionPresetOp.NOT_CONTAINS]: 'string',
  [ConditionPresetOp.IS_EMPTY]: null,
  [ConditionPresetOp.IS_NOT_EMPTY]: null,
  [ConditionPresetOp.GT]: 'number', // 长度大于
  [ConditionPresetOp.GTE]: 'number', // 长度大于等于
  [ConditionPresetOp.LT]: 'number', // 长度小于
  [ConditionPresetOp.LTE]: 'number', // 长度小于等于
}

// 整数条件规则
export const integerConditionRules: IConditionRule = {
  [ConditionPresetOp.EQ]: 'number',
  [ConditionPresetOp.NEQ]: 'number',
  [ConditionPresetOp.GT]: 'number',
  [ConditionPresetOp.GTE]: 'number',
  [ConditionPresetOp.LT]: 'number',
  [ConditionPresetOp.LTE]: 'number',
}

// 统一的规则配置，提供给 ConditionProvider
export const conditionRules = {
  string: stringConditionRules,
  integer: integerConditionRules,
}
