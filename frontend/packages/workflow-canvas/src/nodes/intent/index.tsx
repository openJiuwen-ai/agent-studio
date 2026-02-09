/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { nanoid } from 'nanoid'
import { Target } from 'lucide-react'

import { FlowNodeRegistry } from '../../typings'
import { WorkflowNodeType } from '../constants'
import { formMeta } from './form-meta'
import { generateIntentId } from './components/utils'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const IntentNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Intent,
  meta: {
    defaultPorts: [{ type: 'input' }],
    useDynamicPort: true,
    size: {
      width: 360,
      height: 280,
    },
  },
  info: () => ({
    icon: <Target size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.intent.description'),
  }),
  /**
   * 通过 formMeta 渲染节点
   */
  formMeta,
  /**
   * 意图识别节点可以添加
   */
  canAdd() {
    return true
  },
  /**
   * 添加意图识别节点时的默认配置
   */
  onAdd(context?) {
    const defaultIntents = [
      {
        name: '',
        id: generateIntentId(),
      },
    ]

    const nodeId = `intent_${nanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.intent.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Intent, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.Intent,
      data: {
        title: title,
        inputs: {
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
          intents: defaultIntents,
          default_intent: '0',
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
        },
        outputs: {
          type: 'object',
          properties: {
            classification_id: {
              type: 'integer',
              extra: {
                index: 1,
              },
            },
          },
          required: ['classification_id'],
        },
      },
    }
  },
}
