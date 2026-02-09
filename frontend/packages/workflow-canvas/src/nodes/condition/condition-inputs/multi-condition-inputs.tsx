/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useLayoutEffect, useCallback } from 'react'

import { Field, FieldArray, WorkflowNodePortsData } from '@flowgram.ai/free-layout-editor'
import { Button } from '@douyinfe/semi-ui'
import { Plus } from 'lucide-react'
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core'
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable'

import { useIsSidebar, useNodeRenderContext } from '../../../hooks'
import { useTranslation } from '../../../i18n'
import { ConditionProvider, ConditionPresetOp } from '../../../form-materials'
import { Feedback, FormItem } from '../../../form-components'
import { conditionRules, conditionOps } from './condition-rules'
import { ConditionCard } from './condition-card'
import { DraggableConditionCard } from './draggable-condition-card'
import { ConditionDisplay } from './condition-display'
import { normalizeBranches, generateBranchId, determineBranchType, BranchValue } from './utils'

export function MultiConditionInputs() {
  const { node } = useNodeRenderContext()
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()

  const updatePorts = useCallback(() => {
    setTimeout(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    }, 0)
  }, [node])

  useLayoutEffect(() => {
    window.requestAnimationFrame(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    })
  }, [node, isSidebar])

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  return (
    <ConditionProvider ops={conditionOps} rules={conditionRules}>
      {!isSidebar && <ConditionDisplay />}

      {isSidebar && (
        <FieldArray name="branches">
          {({ field }) => {
            const branches = normalizeBranches(field.value)

            React.useEffect(() => {
              if (branches.length === 0) {
                const initialValue = [
                  {
                    conditions: [
                      {
                        left: { type: 'ref', content: [] },
                        operator: ConditionPresetOp.CONTAINS,
                        right: {
                          type: 'constant',
                          content: '',
                          schema: { type: 'string', extra: { weak: true } },
                        },
                      },
                    ],
                    logic: 2 as const,
                    branchId: generateBranchId(),
                  },
                  {
                    conditions: [],
                    logic: 2 as const,
                    branchId: generateBranchId(),
                  },
                ]
                field.onChange(initialValue)
              }
            }, [])

            // 确保始终有一个else分支
            React.useEffect(() => {
              const hasElseBranch = branches.some((branch: BranchValue) => branch && branch.conditions.length === 0)
              if (branches.length > 0 && !hasElseBranch) {
                const elseBranch = {
                  conditions: [],
                  logic: 2 as const,
                  branchId: generateBranchId(),
                }
                field.onChange([...branches, elseBranch])
              }
            }, [branches.length])

            const handleAddBranch = useCallback(() => {
              const newBranch = {
                conditions: [
                  {
                    left: { type: 'ref', content: [] },
                    operator: ConditionPresetOp.EQ,
                    right: {
                      type: 'constant',
                      content: '',
                      schema: { type: 'string', extra: { weak: true } },
                    },
                  },
                ],
                logic: 2 as const,
                branchId: generateBranchId(),
              }

              const updatedBranches = [...branches]
              const elseBranchIndex = updatedBranches.findIndex((branch: BranchValue) => branch.conditions.length === 0)

              if (elseBranchIndex > 0) {
                updatedBranches.splice(elseBranchIndex, 0, newBranch)
              } else {
                updatedBranches.push(newBranch)
              }

              field.onChange(updatedBranches)
              updatePorts()
            }, [branches, field, updatePorts])

            const handleDragEnd = useCallback(
              (event: DragEndEvent) => {
                const { active, over } = event

                if (over && active.id !== over.id) {
                  const oldIndex = branches.findIndex((branch: BranchValue) => branch.branchId === active.id)
                  const newIndex = branches.findIndex((branch: BranchValue) => branch.branchId === over.id)

                  if (oldIndex !== -1 && newIndex !== -1) {
                    const newBranches = arrayMove(branches, oldIndex, newIndex)
                    field.onChange(newBranches)

                    setTimeout(() => {
                      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
                      if (portsData) {
                        portsData.updateDynamicPorts()
                      }
                    }, 0)
                  }
                }
              },
              [branches, field, node],
            )

            const addButton = (
              <Button
                theme="borderless"
                icon={<Plus size={16} />}
                onClick={handleAddBranch}
                className="text-gray-500 hover:text-blue-600 hover:bg-blue-50"
                size="small"
              />
            )

            // 为拖拽准备的数据：只包含非else分支
            const sortableItems = branches
              .filter((branch: BranchValue, index: number) => {
                const branchType = determineBranchType(branch, index, branches)
                return branchType !== 'else'
              })
              .map((branch: BranchValue) => ({
                id: branch.branchId,
                branch,
              }))

            return (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={sortableItems.map(item => item.id)} strategy={verticalListSortingStrategy}>
                  <FormItem name={t('workflowCanvas.nodes.condition.branchLabel')} customComponent={addButton}>
                    <div className="space-y-0">
                      {branches.map((branch: BranchValue, branchIndex: number) => (
                        <Field<BranchValue> key={`branch-${branchIndex}`} name={`branches.${branchIndex}`}>
                          {({ field: branchField, fieldState: branchState }) => {
                            const currentBranchType = determineBranchType(branchField.value, branchIndex, branches)

                            return (
                              <div className="relative">
                                {currentBranchType === 'else' ? (
                                  // 否则卡片：使用普通卡片，无拖拽能力
                                  <ConditionCard
                                    branch={branchField.value}
                                    branchIndex={branchIndex}
                                    branchType={currentBranchType}
                                    totalBranches={branches.length}
                                    onUpdate={(index, updatedBranch) => {
                                      const updatedBranches = [...branches]
                                      updatedBranches[index] = updatedBranch
                                      field.onChange(updatedBranches)
                                    }}
                                    onDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                    onCardDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                  />
                                ) : branches.length === 1 ? (
                                  // 只有一个分支（只有如果）：使用普通卡片，无拖拽能力
                                  <ConditionCard
                                    branch={branchField.value}
                                    branchIndex={branchIndex}
                                    branchType={currentBranchType}
                                    totalBranches={branches.length}
                                    onUpdate={(index, updatedBranch) => {
                                      const updatedBranches = [...branches]
                                      updatedBranches[index] = updatedBranch
                                      field.onChange(updatedBranches)
                                    }}
                                    onDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                    onCardDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                  />
                                ) : currentBranchType === 'if' && branches.length === 2 ? (
                                  // 只有如果和否则两个分支：如果卡片使用普通卡片，无拖拽能力
                                  <ConditionCard
                                    branch={branchField.value}
                                    branchIndex={branchIndex}
                                    branchType={currentBranchType}
                                    totalBranches={branches.length}
                                    onUpdate={(index, updatedBranch) => {
                                      const updatedBranches = [...branches]
                                      updatedBranches[index] = updatedBranch
                                      field.onChange(updatedBranches)
                                    }}
                                    onDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                    onCardDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                  />
                                ) : (
                                  // 其他情况：如果和否则如果卡片使用可拖拽卡片
                                  <DraggableConditionCard
                                    id={branch.branchId}
                                    branch={branchField.value}
                                    branchIndex={branchIndex}
                                    branchType={currentBranchType}
                                    totalBranches={branches.length}
                                    onUpdate={(index, updatedBranch) => {
                                      const updatedBranches = [...branches]
                                      updatedBranches[index] = updatedBranch
                                      field.onChange(updatedBranches)
                                    }}
                                    onDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                    onCardDelete={index => {
                                      const updatedBranches = branches.filter((_, i) => i !== index)
                                      // 删除后分支索引会自动重新排序，第一个分支将变为新的[如果]分支
                                      field.onChange(updatedBranches)
                                    }}
                                  />
                                )}

                                <Feedback errors={branchState?.errors} invalid={branchState?.invalid} />
                              </div>
                            )
                          }}
                        </Field>
                      ))}
                    </div>
                  </FormItem>
                </SortableContext>
              </DndContext>
            )
          }}
        </FieldArray>
      )}
    </ConditionProvider>
  )
}
