/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'

import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { Sparkles } from 'lucide-react'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { OutputFormat } from './type'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const LLMNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.LLM,
  info: {
    icon: <Sparkles size={16} className="text-purple-600" />,
    description: t('workflowCanvas.nodes.llm.description'),
  },
  meta: {
    size: {
      width: 400, // Increased from 360 to accommodate wider labels
      height: 390,
    },
    singleComponentDebug: true,
  },
  formMeta,
  onAdd: (context?) => {
    const nodeId = `llm_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.llm.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.LLM, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.LLM,
      data: {
        title: title,
        output_format: OutputFormat.TEXT,
        inputs: {
          llmParam: {
            systemPrompt: {
              type: 'template',
              content: '',
            },
            prompt: {
              type: 'template',
              content: '{{input}}',
            },
          },
          inputParameters: {
            input: {
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
