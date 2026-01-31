/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeRegistry } from '../../typings'
import { MousePointerClick } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { customNanoid } from '../../utils/nanoid-custom'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const InputNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Input,
  meta: {
    defaultPorts: [{ type: 'input' }, { type: 'output' }],
    size: {
      width: 360,
      height: 211,
    },
  },
  info: {
    icon: <MousePointerClick size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.input.description'),
  },
  /**
   * Render node via formMeta
   */
  formMeta,
  /**
   * Input Node can be added
   */
  canAdd() {
    return true
  },
  /**
   * 添加输入节点时的默认配置
   */
  onAdd: (context?) => {
    const titlePrefix = t('workflowCanvas.nodes.input.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Input, context, titlePrefix)

    return {
      id: `input_${customNanoid(5)}`,
      type: WorkflowNodeType.Input,
      data: {
        title: title,
        outputs: {
          type: 'object',
          properties: {
            userInput: {
              type: 'string',
              extra: {
                index: 1,
              },
            },
          },
          required: ['userInput'],
        },
      },
    }
  },
}
