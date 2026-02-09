/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeRegistry } from '../../typings'
import { Square } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { t } from '../../i18n'

export const BlockEndNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.BlockEnd,
  meta: {
    isNodeEnd: true,
    deleteDisable: true,
    copyDisable: true,
    sidebarDisabled: true,
    nodePanelVisible: false,
    defaultPorts: [{ type: 'input' }],
    size: {
      width: 100,
      height: 100,
    },
    wrapperStyle: {
      minWidth: 'unset',
      width: '100%',
      borderWidth: 2,
      borderRadius: 12,
      cursor: 'move',
    },
  },
  info: () => ({
    icon: (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', padding: '4px 0', flexDirection: 'column' }}>
        <Square size={20} className="text-red-600" />
        <span style={{ fontSize: '12px', fontWeight: 'bold', marginTop: '2px' }}>{t('workflowCanvas.block.end')}</span>
      </div>
    ),
    description: t('workflowCanvas.nodes.blockEnd.description'),
  }),
  /**
   * Render node via formMeta
   */
  formMeta,
  /**
   * Start Node cannot be added
   */
  canAdd() {
    return false
  },
}
