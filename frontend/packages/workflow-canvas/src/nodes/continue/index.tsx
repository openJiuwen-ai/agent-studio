/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'

import { FlowNodeRegistry } from '../../typings'
import { SkipForward } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { generateNodeTitle } from '../../utils/workflow-node-utils'
import { t } from '../../i18n'

export const ContinueNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Continue,
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
    icon: <SkipForward size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.continue.description'),
  }),
  /**
   * Render node via formMeta
   */
  formMeta,
  onAdd(context?) {
    const titlePrefix = t('workflowCanvas.nodes.continue.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Continue, context, titlePrefix)

    return {
      id: `continue_${customNanoid(5)}`,
      type: WorkflowNodeType.Continue,
      data: {
        title: title,
      },
    }
  },
}
