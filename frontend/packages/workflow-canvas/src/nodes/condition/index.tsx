/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { GitBranch } from 'lucide-react'

import { FlowNodeRegistry } from '../../typings'
import { customNanoid } from '../../utils/nanoid-custom'
import { WorkflowNodeType } from '../constants'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const ConditionNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Condition,
  info: () => ({
    icon: <GitBranch size={16} className="text-orange-600" />,
    description: t('workflowCanvas.nodes.condition.description'),
  }),
  meta: {
    defaultPorts: [{ type: 'input' }],
    useDynamicPort: true,
    size: {
      width: 360,
      height: 210,
    },
  },
  formMeta,
  onAdd(context?) {
    const nodeId = `condition_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.condition.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Condition, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.Condition,
      data: {
        title: title,
        branches: [
          {
            conditions: [
              {
                left: {
                  type: 'ref',
                  content: [],
                },
                operator: 'eq',
                right: {
                  type: 'constant',
                  content: '',
                  schema: {
                    type: 'string',
                    extra: {
                      weak: true,
                    },
                  },
                },
              },
            ],
            logic: 2,
            branchId: `branch_${customNanoid(5)}`,
          },
          {
            conditions: [],
            logic: 2,
            branchId: `branch_${customNanoid(5)}`,
          },
        ],
      },
    }
  },
}
