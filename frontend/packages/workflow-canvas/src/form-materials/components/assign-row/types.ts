/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { BaseVariableField } from '@flowgram.ai/editor'

import { IFlowRefValue, IFlowValue } from '../../'

export type AssignValueType =
  | {
      operator: 'assign'
      left?: IFlowRefValue
      right?: IFlowValue
    }
  | {
      operator: 'declare'
      left?: string
      right?: IFlowValue
    }

export interface AssignRowProps {
  value?: AssignValueType
  onChange?: (value?: AssignValueType) => void
  onDelete?: () => void
  readonly?: boolean
  skipVariable?: (variable?: BaseVariableField) => boolean
}
