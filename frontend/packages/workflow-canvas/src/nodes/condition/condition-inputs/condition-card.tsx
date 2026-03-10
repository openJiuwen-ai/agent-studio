/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable @typescript-eslint/no-unused-vars */

import React, { useCallback } from 'react'

import { Field, FieldArray } from '@flowgram.ai/free-layout-editor'
import { Button } from '@douyinfe/semi-ui'
import { Plus, XCircle, GripVertical } from 'lucide-react'
import styled from 'styled-components'
import { useTranslation } from '../../../i18n'

import { ConditionRow, ConditionRowValueType, ConditionPresetOp } from '../../../form-materials'
import { generateBranchPortId } from './utils'

// 自定义样式的原生Select组件
const StyledSelect = styled.select`
  font-size: 12px;
  padding: 4px 6px;
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 6px;
  background-color: white;
  min-height: 28px;
  cursor: pointer;
  width: 100%;
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M6 0L12 4L6 8Z' fill='%23333'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 8px 6px;
  padding-right: 20px;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--accent-primary);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  &:focus {
    outline: none;
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }

  option {
    padding: 4px 6px;
    font-size: 12px;
    background-color: white;
    color: #1f2329;
  }

  option:hover {
    background-color: #f8f9fa;
  }
`

interface ConditionValue {
  left?: { type: 'ref'; content: string[] }
  operator?: string | number // 同时支持string和number类型
  right?: { type: 'constant'; content: unknown; schema: { type: string; extra?: { weak?: boolean } } }
}

interface BranchValue {
  conditions: ConditionValue[]
  logic: 1 | 2 // 1: OR (||), 2: AND (&&)
  branchId: string
}

type BranchType = 'if' | 'elseIf' | 'else'

// 拖拽手柄样式
const DragHandle = styled.div<{ disabled?: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: #999999;
  cursor: ${props => (props.disabled ? 'not-allowed' : 'grab')};
  flex-shrink: 0;
  padding: 0;
  border-radius: 4px;
  transition: all 0.2s ease;

  &:hover {
    color: ${props => (props.disabled ? '#cccccc' : '#666666')};
    background-color: ${props => (props.disabled ? 'transparent' : '#f5f5f5')};
  }

  &:active {
    cursor: ${props => (props.disabled ? 'not-allowed' : 'grabbing')};
  }
`

interface ConditionCardProps {
  branch: BranchValue
  branchIndex: number
  branchType: BranchType
  totalBranches: number
  onUpdate: (index: number, branch: BranchValue) => void
  onDelete: (index: number) => void
  onCardDelete?: (index: number) => void
  enableDrag?: boolean
  dragHandleProps?: unknown
  isDragging?: boolean
}

/* eslint-disable @typescript-eslint/no-unused-vars */
export const ConditionCard: React.FC<ConditionCardProps> = React.memo(
  ({ branch, branchIndex, branchType, totalBranches, onUpdate, onDelete, onCardDelete, enableDrag = false, dragHandleProps, isDragging = false }) => {
    const { t } = useTranslation()

    const getBranchTitle = useCallback(() => {
      switch (branchType) {
        case 'if':
          return t('workflowCanvas.condition.if')
        case 'elseIf':
          return t('workflowCanvas.condition.elseIf')
        case 'else':
          return t('workflowCanvas.condition.else')
      }
    }, [branchType])

    const isElseBranch = branchType === 'else'
    const hasOnlyIfBranch = branchIndex === 0 && totalBranches <= 2
    const isDragDisabled = totalBranches <= 1 || isDragging

    return (
      <div className={`mb-2 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden ${isDragging ? 'opacity-75' : ''}`}>
        <div className="flex items-center justify-between px-3 py-2">
          <div className="flex items-center gap-2">
            {enableDrag && (
              <DragHandle
                disabled={isDragDisabled}
                {...dragHandleProps}
                title={isDragDisabled ? t('workflowCanvas.condition.onlyOneBranch') : t('workflowCanvas.condition.dragSort')}
              >
                <GripVertical size={14} />
              </DragHandle>
            )}
            <span className="text-sm font-medium text-gray-900">{getBranchTitle()}</span>
          </div>

          <div className="flex items-center gap-1">
            {!isElseBranch && (
              <Button
                theme="borderless"
                icon={<XCircle size={14} />}
                size="small"
                disabled={hasOnlyIfBranch}
                onClick={() => onDelete(branchIndex)}
                className={hasOnlyIfBranch ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-red-600 hover:bg-red-50'}
              />
            )}
          </div>
        </div>

        {!isElseBranch && (
          <div className="px-3 pb-3">
            <ConditionContent branch={branch} branchIndex={branchIndex} branchType={branchType} onUpdate={onUpdate} onCardDelete={onCardDelete} />
          </div>
        )}

        <div className="absolute -right-3 top-1/2 -translate-y-1/2" data-port-id={generateBranchPortId(branch)} data-port-type="output" />
      </div>
    )
  },
)

ConditionCard.displayName = 'ConditionCard'

// 条件内容组件
const ConditionContent: React.FC<{
  branch: BranchValue
  branchIndex: number
  branchType: BranchType
  onUpdate: (index: number, branch: BranchValue) => void
  onCardDelete?: (index: number) => void
}> = React.memo(({ branch, branchIndex, branchType, onUpdate, onCardDelete }) => {
  const { t } = useTranslation()

  return (
    <FieldArray name={`branches.${branchIndex}.conditions`}>
      {({ field: conditionsField }) => {
        const conditions = Array.isArray(conditionsField.value) ? (conditionsField.value as ConditionValue[]) : []

        const handleAddCondition = useCallback(() => {
          const newCondition: ConditionValue = {
            left: { type: 'ref', content: [] },
            operator: ConditionPresetOp.CONTAINS,
            right: {
              type: 'constant',
              content: '',
              schema: { type: 'string', extra: { weak: true } },
            },
          }
          const updatedConditions = [...conditions, newCondition]
          onUpdate(branchIndex, { ...branch, conditions: updatedConditions })
        }, [branch, branchIndex, conditions, onUpdate])

        const handleDeleteCondition = useCallback(
          (conditionIndex: number) => {
            const updatedConditions = conditions.filter((_, index) => index !== conditionIndex)

            if (updatedConditions.length === 0 && branchType === 'elseIf' && onCardDelete) {
              onCardDelete(branchIndex)
            } else {
              onUpdate(branchIndex, { ...branch, conditions: updatedConditions })
            }
          },
          [branch, branchIndex, branchType, conditions, onUpdate, onCardDelete],
        )

        const handleLogicChange = useCallback(
          (value: string | number | unknown[] | Record<string, unknown> | undefined) => {
            if (value !== undefined && (typeof value === 'string' || typeof value === 'number')) {
              const logic = typeof value === 'number' ? value : (parseInt(value as string, 10) as 1 | 2)
              onUpdate(branchIndex, { ...branch, logic })
            }
          },
          [branch, branchIndex, onUpdate],
        )

        return (
          <div className="flex">
            {conditions.length > 1 && (
              <div className="flex-none w-[40px] mt-2 mb-8 mr-2">
                <div className="flex flex-col h-full">
                  <div className="flex-1 relative">
                    <div className="absolute left-1/2 right-0 top-2.5 bottom-0 rounded-tl-lg border-solid border-0 border-t border-l border-gray-300" />
                  </div>
                  <div className="relative">
                    <StyledSelect
                      value={branch.logic}
                      onChange={e => {
                        const value = e.target.value as 1 | 2
                        handleLogicChange(value)
                      }}
                    >
                      <option value={2}>{t('workflowCanvas.condition.and')}</option>
                      <option value={1}>{t('workflowCanvas.condition.or')}</option>
                    </StyledSelect>
                  </div>
                  <div className="flex-1 relative">
                    <div className="absolute left-1/2 right-0 top-0 bottom-2.5 rounded-bl-lg border-solid border-0 border-b border-l border-gray-300" />
                  </div>
                </div>
              </div>
            )}

            <div className="flex-1">
              <div className="space-y-1 mb-2">
                {conditions.map((condition: ConditionValue, conditionIndex: number) => (
                  <div key={`condition-${conditionIndex}`} className="flex items-center gap-1">
                    <div className="flex-1">
                      <Field<ConditionValue> name={`branches.${branchIndex}.conditions.${conditionIndex}`}>
                        {({ field: conditionField }) => {
                          return (
                            <div className="flex-1">
                              <ConditionRow
                                value={conditionField.value as unknown as ConditionRowValueType}
                                onChange={v => {
                                  const newValue = v as ConditionValue
                                  const currentValue = conditionField.value as ConditionValue

                                  const updatedValue: ConditionValue = {
                                    left: newValue.left ?? currentValue.left,
                                    operator: newValue.operator,
                                    right: 'right' in (newValue as object) ? newValue.right : currentValue.right,
                                  }

                                  conditionField.onChange(updatedValue)
                                }}
                              />
                            </div>
                          )
                        }}
                      </Field>
                    </div>

                    {branchType !== 'else' && (
                      <div style={{ flex: '0 0 24px' }}>
                        <Button
                          theme="borderless"
                          icon={<XCircle size={14} />}
                          onClick={() => handleDeleteCondition(conditionIndex)}
                          className="text-gray-400 hover:text-red-500"
                          size="small"
                          disabled={branchType === 'if' && conditions.length === 1 && conditionIndex === 0}
                          style={{
                            cursor: branchType === 'if' && conditions.length === 1 && conditionIndex === 0 ? 'not-allowed' : undefined,
                            opacity: branchType === 'if' && conditions.length === 1 && conditionIndex === 0 ? 0.5 : 1,
                          }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center">
                <Button
                  theme="light"
                  icon={<Plus size={14} />}
                  onClick={handleAddCondition}
                  className="text-blue-500 border border-blue-500 hover:bg-blue-50"
                  size="small"
                >
                  {t('workflowCanvas.condition.add')}
                </Button>
              </div>
            </div>
          </div>
        )
      }}
    </FieldArray>
  )
})

ConditionContent.displayName = 'ConditionContent'

export type { ConditionCardProps }
