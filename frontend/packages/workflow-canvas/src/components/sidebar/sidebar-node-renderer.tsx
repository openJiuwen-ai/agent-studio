/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useNodeRender, FlowNodeEntity } from '@flowgram.ai/free-layout-editor'

import { NodeRenderContext } from '../../context'
import './sidebar.css'

export function SidebarNodeRenderer(props: { node: FlowNodeEntity }) {
  const { node } = props
  const nodeRender = useNodeRender(node)

  return (
    <NodeRenderContext.Provider value={nodeRender}>
      <div className="sidebar-node-container">
        {nodeRender.form?.render()}
      </div>
    </NodeRenderContext.Provider>
  )
}
