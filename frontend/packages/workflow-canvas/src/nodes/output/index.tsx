/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'
import { FlowNodeRegistry } from '../../typings'
import { Download } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const OutputNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Output,
  meta: {
    defaultPorts: [{ type: 'input' }, { type: 'output' }],
    size: {
      width: 360,
      height: 211,
    },
    // 确保节点在面板中可见
    nodePanelVisible: true,
  },
  info: () => ({
    icon: <Download size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.output.description'),
  }),
  formMeta,
  onAdd(context?) {
    const titlePrefix = t('workflowCanvas.nodes.output.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Output, context, titlePrefix)

    return {
      id: `output_${customNanoid(5)}`,
      type: WorkflowNodeType.Output,
      data: {
        title: title,
        inputs: {
          inputParameters: {
            output: {
              type: 'constant',
              content: '',
              schema: {
                type: 'string',
              },
              extra: {
                index: 0,
              },
            },
          },
          content: {
            type: 'template',
            content: '{{output}}',
          },
          streaming: false,
        },
      },
    }
  },
}
