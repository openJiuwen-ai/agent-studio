/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'
import styled from 'styled-components'

import { ConditionValue, BranchValue } from './utils'
import { ConditionPresetOp, defaultConditionOpConfigs } from '../../../form-materials'
import { useScopeAvailable } from '@flowgram.ai/editor'
import { useTranslation } from '../../../i18n'
import { last } from 'lodash-es'

// 条件容器 - 参考 HTML 结构
const ConditionContainer = styled.div`
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 4px;
  padding: 4px;
  min-height: 24px;
  max-width: 100%;
  overflow: hidden;
  background-color: white;
`

// 单个条件行容器
const ConditionRowContainer = styled.div`
  display: flex;
  align-items: center;
  padding: 0 2px;
  min-width: 0;

  &:not(:last-child) {
    margin-bottom: 4px;
  }
`

// 条件标签样式 - 模拟 semi-tag
const ConditionTag = styled.div`
  display: flex;
  align-items: center;
  padding: 2px 6px;
  background-color: #f0f0f0;
  border: 1px solid #d9d9d9;
  border-radius: 3px;
  font-size: 12px;
  color: #333;
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`

// 操作符容器
const OperatorContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  flex-grow: 0;
  flex-basis: 0;
  padding: 0 4px;
`

// 操作符图标
const OperatorIcon = styled.div<{ operator: string | number | undefined }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  color: #666;
  font-size: 12px;
  font-family: 'Cambria Math', 'Times New Roman', serif; /* 优化数学符号显示 */
`

// 逻辑操作符容器 - 模拟 HTML 结构
const LogicOperatorContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 1px 0;
  margin: 1px 0;
`

// 分割线
const Divider = styled.div`
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  border-top: 1px solid rgba(0, 0, 0, 0.15);
  transform: translateY(-50%);
`

// 逻辑操作符文本
const LogicOperatorText = styled.span`
  position: relative;
  min-width: 24px;
  background-color: white;
  padding: 1px 3px;
  font-size: 11px;
  color: #333;
  font-weight: 500;
  text-align: center;
`

const formatConditionValue = (value: unknown, available?: { getByKeyPath?: (path: unknown[]) => unknown }, valueType?: string): string => {
  if (value == null) return 'Empty'

  if (typeof value === 'string') {
    return value === '' ? 'Empty' : value
  }

  if (Array.isArray(value)) {
    if (valueType === 'constant') {
      return JSON.stringify(value)
    }

    if (value.length === 0) return 'Empty'

    if (available && value.length > 0) {
      try {
        const variable = available.getByKeyPath(value)

        if (variable) {
          const rootField = last(variable.parentFields) || variable
          const isRoot = variable === rootField
          const rootTitle = rootField.meta?.title || rootField.key || 'Unknown'
          const varName = variable.keyPath.slice(1).join('.')

          if (varName && !isRoot) {
            return `${rootTitle} ${varName}`
          } else {
            return rootTitle
          }
        }
      } catch (error) {
        // ignore
      }
    }

    const componentId = value[0] || 'Unknown'
    const varName = value.slice(1).join('.')

    if (varName) {
      return `${componentId} ${varName}`
    } else {
      return componentId
    }
  }

  if (typeof value === 'object' && value !== null && 'content' in value) {
    return formatConditionValue((value as { content: unknown }).content, available)
  }

  return String(value)
}

const getOperatorIcon = (operator: string | number | undefined): string => {
  const opConfigs = defaultConditionOpConfigs

  if (typeof operator === 'string') {
    const trimmedOperator = operator.trim()
    if (trimmedOperator && opConfigs[trimmedOperator as ConditionPresetOp]) {
      return opConfigs[trimmedOperator as ConditionPresetOp].abbreviation
    }

    const numericOperator = parseInt(trimmedOperator, 10)
    if (!isNaN(numericOperator)) {
      return getNumericOperatorIcon(numericOperator)
    }
  }

  if (typeof operator === 'number') {
    return getNumericOperatorIcon(operator)
  }

  return '='
}

const getNumericOperatorIcon = (operator: number): string => {
  const legacyIconMap: Record<number, string> = {
    1: '=',
    2: '≠',
    3: '⊇',
    4: '⊉',
    5: '◀',
    6: '▶',
    7: '>',
    8: '<',
    9: '≥',
    10: '≤',
  }

  return legacyIconMap[operator] || '='
}

const ConditionRowDisplay: React.FC<{ condition: ConditionValue }> = React.memo(({ condition }) => {
  const available = useScopeAvailable()
  const leftValue = condition.left?.content || []
  const operator = condition.operator

  const isEmptyOperator = operator === ConditionPresetOp.IS_EMPTY || operator === ConditionPresetOp.IS_NOT_EMPTY
  let rightDisplay = 'Empty'

  if (!isEmptyOperator && condition.right) {
    rightDisplay = formatConditionValue(condition.right?.content, available, condition.right?.type)
  }

  return (
    <ConditionRowContainer>
      <ConditionTag title={formatConditionValue(leftValue, available)}>{formatConditionValue(leftValue, available)}</ConditionTag>

      <OperatorContainer>
        <OperatorIcon operator={operator} title={String(operator)}>
          {getOperatorIcon(operator)}
        </OperatorIcon>
      </OperatorContainer>

      <ConditionTag title={rightDisplay}>{rightDisplay}</ConditionTag>
    </ConditionRowContainer>
  )
})

ConditionRowDisplay.displayName = 'ConditionRowDisplay'

interface ConditionContentDisplayProps {
  branch: BranchValue
}

export const ConditionContentDisplay: React.FC<ConditionContentDisplayProps> = React.memo(({ branch }) => {
  const { t } = useTranslation()
  const conditions = branch?.conditions || []

  if (conditions.length === 0) {
    return (
      <ConditionContainer>
        <div style={{ textAlign: 'center', color: '#999', fontSize: '12px' }}>{t('workflowCanvas.nodes.condition.unconditional')}</div>
      </ConditionContainer>
    )
  }

  const logic = typeof branch?.logic === 'number' ? branch.logic : parseInt(branch?.logic as string, 10) || 2
  const logicText = logic === 1 ? t('workflowCanvas.nodes.condition.logic.or') : t('workflowCanvas.nodes.condition.logic.and')

  return (
    <ConditionContainer>
      {conditions.map((condition: ConditionValue, conditionIndex: number) => (
        <div key={conditionIndex}>
          <ConditionRowDisplay condition={condition} />
          {conditionIndex < conditions.length - 1 && (
            <LogicOperatorContainer>
              <Divider />
              <LogicOperatorText>{logicText}</LogicOperatorText>
            </LogicOperatorContainer>
          )}
        </div>
      ))}
    </ConditionContainer>
  )
})

ConditionContentDisplay.displayName = 'ConditionContentDisplay'
