/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { type FlowNodeEntity } from '@flowgram.ai/free-layout-editor'

import { FlowNodeRegistry } from '../../typings'
import { Icon } from './styles'

export const getIcon = (node: FlowNodeEntity) => {
  const info = node.getNodeRegistry<FlowNodeRegistry>().info
  const icon = typeof info === 'function' ? info().icon : info?.icon
  if (!icon) return null

  if (typeof icon === 'string') {
    return <Icon src={icon} />
  } else {
    return icon
  }
}
