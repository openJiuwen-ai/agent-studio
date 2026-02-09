/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeRegistry } from '../../typings'
import { PlayCircle } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { t } from '../../i18n'

export const BlockStartNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.BlockStart,
  meta: {
    isStart: true,
    deleteDisable: true,
    copyDisable: true,
    sidebarDisabled: true,
    nodePanelVisible: false,
    defaultPorts: [{ type: 'output' }],
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
        <PlayCircle size={20} className="text-green-600" />
        <span style={{ fontSize: '12px', fontWeight: 'bold', marginTop: '2px' }}>{t('workflowCanvas.block.start')}</span>
      </div>
    ),
    description: t('workflowCanvas.nodes.blockStart.description'),
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
