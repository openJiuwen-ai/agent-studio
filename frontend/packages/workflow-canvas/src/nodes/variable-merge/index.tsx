/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Merge } from 'lucide-react'

import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { formMeta } from './form-meta'
import { customNanoid } from '../../utils/nanoid-custom'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const VariableMergeNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.VariableMerge,
  info: () => ({
    icon: <Merge size={16} className="text-purple-600" />,
    description: t('workflowCanvas.nodes.variableMerge.description'),
  }),
  meta: {
    size: {
      width: 360,
      height: 211,
    },
  },
  onAdd(context?) {
    const nodeId = `variable_merge_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.variableMerge.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.VariableMerge, context, titlePrefix)

    return {
      id: nodeId,
      type: 'variable_merge',
      data: {
        title: title,
        inputs: {
          variableMerge: [
            {
              name: 'Group1',
              type: 'string',
              items: ['input1'],
            },
          ],
          mergeStrategy: 'firstNonNull',
          inputParameters: {
            input1: {
              type: 'ref',
              content: [''],
              extra: {
                index: 0,
              },
            },
          },
        },
        outputs: {
          type: 'object',
          properties: {
            Group1: {
              type: 'string',
              extra: { index: 0 },
            },
          },
        },
      },
    }
  },
  formMeta: formMeta,
}
