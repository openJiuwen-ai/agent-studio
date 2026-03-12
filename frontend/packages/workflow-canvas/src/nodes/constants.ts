/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

export enum WorkflowNodeType {
  Start = '1',
  End = '2',
  LLM = '3',
  Condition = '4',
  Loop = '5',
  Intent = '6',
  Questioner = '7',
  Input = '8',
  Output = '9',
  Code = '10',
  TextEditor = '11',
  Continue = '12',
  Break = '13',
  Workflow = '14',
  BlockStart = '15',
  BlockEnd = '16',
  Variable = '17',
  VariableMerge = '18',
  Plugin = '19',
  HttpRequest = '20',
  ReactAgent = '21',
  Comment = '99',
}
