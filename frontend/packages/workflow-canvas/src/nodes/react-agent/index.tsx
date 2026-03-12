/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'
import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { Bot } from 'lucide-react'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const ReactAgentNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.ReactAgent,
  info: () => ({
    icon: <Bot size={16} className="text-purple-600" />,
    description: t('workflowCanvas.nodes.reactAgent.description'),
  }),
  meta: {
    size: {
      width: 400,
      height: 520, // Taller to accommodate Skills section
    },
    defaultPorts: [{ type: 'output' }, { type: 'input' }],
    nodePanelVisible: true,
    singleComponentDebug: true,
  },
  formMeta,
  onAdd: (context?) => {
    const nodeId = `react_agent_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.reactAgent.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.ReactAgent, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.ReactAgent,
      data: {
        title: title,
        max_iterations: 5,
        inputs: {
          llmParam: {
            systemPrompt: {
              type: 'template',
              content: 'You are a helpful ReAct agent that can reason and use tools to solve problems.',
            },
            prompt: {
              type: 'template',
              content: '{{query}}',
            },
          },
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
          skillsParam: {
            plugins: [],
            workflows: [],
          },
        },
        outputs: {
          type: 'object',
          properties: {
            output: {
              type: 'string',
              extra: {
                index: 1,
              },
            },
          },
          required: ['output'],
        },
      },
    }
  },
}
