/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeRegistry } from '../../typings'
import { FileText } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { customNanoid } from '../../utils/nanoid-custom'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const TextEditorNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.TextEditor,
  meta: {
    defaultPorts: [{ type: 'input' }, { type: 'output' }],
    size: {
      width: 360,
      height: 211,
    },
    singleComponentDebug: true,
  },
  info: {
    icon: <FileText size={16} className="text-green-600" />,
    description: t('workflowCanvas.nodes.textEditor.description'),
  },
  /**
   * Render node via formMeta
   */
  formMeta,
  /**
   * Text Editor Node can be added
   */
  canAdd() {
    return true
  },
  /**
   * 添加文本编辑节点时的默认配置
   */
  onAdd(context?) {
    const nodeId = `text_editor_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.textEditor.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.TextEditor, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.TextEditor,
      data: {
        title: title,
        inputs: {
          textEditorParam: {
            editType: 'StringConcatenation',
            delimiters: [],
            concatenateFormat: {
              type: 'template',
              content: '{{input}}',
            },
            customDelimiters: [],
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
