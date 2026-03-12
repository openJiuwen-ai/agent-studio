/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FlowNodeRegistry } from '../typings'
import { StartNodeRegistry } from './start'
import { LoopNodeRegistry } from './loop'
import { LLMNodeRegistry } from './llm'
import { IntentNodeRegistry } from './intent'

import { EndNodeRegistry } from './end'
import { ContinueNodeRegistry } from './continue'
import { ConditionNodeRegistry } from './condition'
import { CommentNodeRegistry } from './comment'
import { CodeNodeRegistry } from './code'
import { BreakNodeRegistry } from './break'
import { BlockStartNodeRegistry } from './block-start'
import { BlockEndNodeRegistry } from './block-end'
import { InputNodeRegistry } from './input'
import { OutputNodeRegistry } from './output'
import { QuestionerNodeRegistry } from './questioner'
import { TextEditorNodeRegistry } from './text-editor'
import { WorkflowNodeRegistry } from './sub-workflow'
import { VariableNodeRegistry } from './variable'
import { VariableMergeNodeRegistry } from './variable-merge'
import { PluginNodeRegistry } from './plugin'
import { HttpRequestNodeRegistry } from './http-request'
import { ReactAgentNodeRegistry } from './react-agent'
export { WorkflowNodeType } from './constants'

export const nodeRegistries: FlowNodeRegistry[] = [
  ConditionNodeRegistry,
  StartNodeRegistry,
  EndNodeRegistry,
  LLMNodeRegistry,
  IntentNodeRegistry,
  LoopNodeRegistry,
  CommentNodeRegistry,
  BlockStartNodeRegistry,
  BlockEndNodeRegistry,
  CodeNodeRegistry,
  ContinueNodeRegistry,
  BreakNodeRegistry,
  InputNodeRegistry,
  QuestionerNodeRegistry,
  OutputNodeRegistry,
  TextEditorNodeRegistry,
  WorkflowNodeRegistry,
  VariableNodeRegistry,
  VariableMergeNodeRegistry,
  PluginNodeRegistry,
  HttpRequestNodeRegistry,
  ReactAgentNodeRegistry,
]
