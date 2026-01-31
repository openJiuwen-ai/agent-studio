/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FunctionComponent } from 'react'

import { SelectorBoxPopoverProps } from '@flowgram.ai/free-layout-editor'
import { Button, ButtonGroup, Tooltip } from '@douyinfe/semi-ui'
import { Copy, Trash2, Maximize2, Minimize2 } from 'lucide-react'

import { FlowCommandId } from '../../shortcuts/constants'

const BUTTON_HEIGHT = 24

export const SelectorBoxPopover: FunctionComponent<SelectorBoxPopoverProps> = ({ bounds, children, commandRegistry }) => {
  return (
    <>
      <div
        style={{
          position: 'absolute',
          left: bounds.right,
          top: bounds.top,
          transform: 'translate(-100%, -100%)',
        }}
        onMouseDown={e => {
          e.stopPropagation()
        }}
      >
        <ButtonGroup size="small" style={{ display: 'flex', flexWrap: 'nowrap', height: BUTTON_HEIGHT }}>
          <Tooltip content={'复制'}>
            <Button
              icon={<Copy size={18} className="text-white" />}
              style={{ height: BUTTON_HEIGHT }}
              type="primary"
              theme="solid"
              onClick={() => {
                commandRegistry.executeCommand(FlowCommandId.COPY)
              }}
            />
          </Tooltip>

          <Tooltip content={'删除'}>
            <Button
              type="primary"
              theme="solid"
              icon={<Trash2 size={18} className="text-white" />}
              style={{ height: BUTTON_HEIGHT }}
              onClick={() => {
                commandRegistry.executeCommand(FlowCommandId.DELETE)
              }}
            />
          </Tooltip>
        </ButtonGroup>
      </div>
      <div>{children}</div>
    </>
  )
}
