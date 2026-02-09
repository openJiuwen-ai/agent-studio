/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'

import { FlowNodeRegistry } from '../../typings'
import { XCircle } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { generateNodeTitle } from '../../utils/workflow-node-utils'
import { t } from '../../i18n'

export const BreakNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Break,
  meta: {
    defaultPorts: [{ type: 'input' }],
    sidebarDisabled: true,
    size: {
      width: 360,
      height: 54,
    },
    onlyInContainer: WorkflowNodeType.Loop,
  },
  info: () => ({
    icon: <XCircle size={16} className="text-red-600" />,
    description: t('workflowCanvas.nodes.break.description'),
  }),
  /**
   * Render node via formMeta
   */
  formMeta,
  onAdd(context?) {
    const titlePrefix = t('workflowCanvas.nodes.break.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Break, context, titlePrefix)

    return {
      id: `break_${customNanoid(5)}`,
      type: WorkflowNodeType.Break,
      data: {
        title: title,
      },
    }
  },
}
