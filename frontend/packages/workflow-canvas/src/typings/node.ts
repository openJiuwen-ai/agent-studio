/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import {
  WorkflowNodeJSON as FlowNodeJSONDefault,
  WorkflowNodeRegistry as FlowNodeRegistryDefault,
  FreeLayoutPluginContext,
  FlowNodeEntity,
  type WorkflowEdgeJSON,
  WorkflowNodeMeta,
} from '@flowgram.ai/free-layout-editor'
import { ReactElement } from 'react'

import { type JsonSchema } from './json-schema'
import { WorkflowNodeType } from '../nodes'

/**
 * You can customize the data of the node, and here you can use JsonSchema to define the input and output of the node
 * 你可以自定义节点的 data 业务数据, 这里演示 通过 JsonSchema 来定义节点的输入/输出
 */
export interface FlowNodeJSON extends FlowNodeJSONDefault {
  data: {
    /**
     * Node title
     */
    title?: string
    /**
     * Define the inputs data of the node by JsonSchema
     */
    inputs?: JsonSchema
    /**
     * Define the outputs data of the node by JsonSchema
     */
    outputs?: JsonSchema
    /**
     * Rest properties
     */
    [key: string]: any
  }
}

/**
 * You can customize your own node meta
 * 你可以自定义节点的meta
 */
export interface FlowNodeMeta extends WorkflowNodeMeta {
  sidebarDisabled?: boolean
  nodePanelHidden?: boolean
  wrapperStyle?: React.CSSProperties
  onlyInContainer?: WorkflowNodeType
  singleComponentDebug?: boolean // 是否显示单节点调试
}

/**
 * You can customize your own node registry
 * 你可以自定义节点的注册器
 */
export type FlowNodeRegistryInfo = {
  icon: string | ReactElement
  description: string
}

export interface FlowNodeRegistry extends FlowNodeRegistryDefault {
  meta: FlowNodeMeta
  info?: FlowNodeRegistryInfo | (() => FlowNodeRegistryInfo)
  canAdd?: (ctx: FreeLayoutPluginContext) => boolean
  canDelete?: (ctx: FreeLayoutPluginContext, from: FlowNodeEntity) => boolean
  onAdd?: (ctx: FreeLayoutPluginContext) => FlowNodeJSON
}

export interface FlowDocumentJSON {
  nodes: FlowNodeJSON[]
  edges: WorkflowEdgeJSON[]
}
