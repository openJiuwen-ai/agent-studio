/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable react/prop-types */
import React from 'react'

import { InputNumber } from '@douyinfe/semi-ui'
import { t } from '../../../../i18n'

import { ConditionPresetOp } from '../../..'

import { type JsonSchemaTypeRegistry } from '../types'

export const numberRegistry: Partial<JsonSchemaTypeRegistry> = {
  type: 'number',
  ConstantRenderer: props => (
    <InputNumber
      placeholder={t('workflowCanvas.formMaterials.input.pleaseInputNumber')}
      size="small"
      disabled={props.readonly}
      hideButtons
      max={Number.MAX_VALUE}
      min={Number.MIN_VALUE}
      {...props}
    />
  ),
  conditionRule: {
    [ConditionPresetOp.EQ]: { type: 'number' },
    [ConditionPresetOp.NEQ]: { type: 'number' },
    [ConditionPresetOp.GT]: { type: 'number' },
    [ConditionPresetOp.GTE]: { type: 'number' },
    [ConditionPresetOp.LT]: { type: 'number' },
    [ConditionPresetOp.LTE]: { type: 'number' },
    [ConditionPresetOp.IN]: {
      type: 'array',
      extra: { weak: true },
    },
    [ConditionPresetOp.NIN]: {
      type: 'array',
      extra: { weak: true },
    },
  },
}
