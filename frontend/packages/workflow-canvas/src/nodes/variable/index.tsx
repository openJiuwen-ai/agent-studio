/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { nanoid } from 'nanoid'

import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { Key } from 'lucide-react'
import { formMeta } from './form-meta'
import { customNanoid } from '../../utils/nanoid-custom'
import { generateNodeTitle } from '../../utils/workflow-node-utils'
import { t } from '../../i18n'

export const VariableNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Variable,
  info: () => ({
    icon: <Key size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.variable.description'),
  }),
  meta: {
    size: {
      width: 360,
      height: 390,
    },
    onlyInContainer: WorkflowNodeType.Loop,
  },
  onAdd(context?) {
    const titlePrefix = t('workflowCanvas.nodes.variable.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Variable, context, titlePrefix)

    return {
      id: `variable__${customNanoid(5)}`,
      type: WorkflowNodeType.Variable,
      data: {
        title: title,
        assign: [
          {
            operator: 'assign',
            left: '',
          },
        ],
      },
    }
  },
  formMeta: formMeta,
}
