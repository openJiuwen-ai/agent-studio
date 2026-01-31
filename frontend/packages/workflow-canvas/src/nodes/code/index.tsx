/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'

import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { Code } from 'lucide-react'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const CodeNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Code,
  info: {
    icon: <Code size={16} className="text-emerald-600" />,
    description: t('workflowCanvas.nodes.code.description'),
  },
  meta: {
    defaultPorts: [{ type: 'input' }],
    useDynamicPort: true,
    size: {
      width: 360,
      height: 211,
    },
    nodePanelVisible: true,
    singleComponentDebug: true,
  },
  formMeta,
  onAdd(context?) {
    const nodeId = `code_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.code.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Code, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.Code,
      data: {
        title: title,
        inputs: {
          inputParameters: {
            input: {
              type: 'constant',
              content: 'hello',
              schema: {
                type: 'string',
              },
              extra: {
                index: 0,
              },
            },
          },
          language: 'python',
          code: "def main(args: Args):\n  import time\n  time.sleep(3)\n  return {'result': args.params['input']}",
        },
        outputs: {
          type: 'object',
          properties: {
            result: {
              type: 'string',
              description: t('workflowCanvas.nodes.code.outputDescription'),
            },
          },
          required: ['result'],
        },
        exceptionConfig: {
          retryTimes: 3,
          timeoutSeconds: 30,
          processType: 'break',
          executeStep: {
            defaultStep: '0',
            errorStep: '1',
          },
        },
      },
    }
  },
}
