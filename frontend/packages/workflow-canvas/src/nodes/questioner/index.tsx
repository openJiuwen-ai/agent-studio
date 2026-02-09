/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'
import { HelpCircle } from 'lucide-react'

import { FlowNodeRegistry } from '../../typings'
import { WorkflowNodeType } from '../constants'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const QuestionerNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Questioner,
  info: () => ({
    icon: <HelpCircle size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.questioner.description'),
  }),
  meta: {
    defaultPorts: [{ type: 'input' }, { type: 'output' }],
    size: {
      width: 360,
      height: 240,
    },
    nodePanelVisible: true,
  },
  formMeta,
  onAdd(context?) {
    const nodeId = `questioner_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.questioner.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Questioner, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.Questioner,
      data: {
        title: title,
        inputs: {
          max_response: 3,
          inputParameters: {
            query: {
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
          llmParam: {
            systemPrompt: {
              type: 'template',
              content: '',
            },
            prompt: {
              type: 'template',
              content: '',
            },
          },
        },
        outputs: {
          type: 'object',
          properties: {
            user_response: {
              type: 'string',
              description: '用户响应输出变量',
            },
            output: {
              type: 'string',
            },
          },
          required: ['user_response'],
        },
      },
    }
  },
}
