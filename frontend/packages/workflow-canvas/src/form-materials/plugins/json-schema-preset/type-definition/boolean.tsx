/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable react/prop-types */
import React from 'react'

import { Select } from '@douyinfe/semi-ui'
import { t } from '../../../../i18n'

import { ConditionPresetOp } from '../../..'

import { type JsonSchemaTypeRegistry } from '../types'

export const booleanRegistry: Partial<JsonSchemaTypeRegistry> = {
  type: 'boolean',
  ConstantRenderer: props => {
    const { value, onChange, ...rest } = props
    return (
      <Select
        placeholder={t('workflowCanvas.formMaterials.input.pleaseSelectBoolean')}
        size="small"
        disabled={props.readonly}
        optionList={[
          { label: t('workflowCanvas.formMaterials.input.true'), value: 1 },
          { label: t('workflowCanvas.formMaterials.input.false'), value: 0 },
        ]}
        value={typeof value === 'boolean' ? (value ? 1 : 0) : undefined}
        onChange={value => onChange?.(value !== undefined ? !!value : undefined)}
        {...rest}
      />
    )
  },
  conditionRule: {
    [ConditionPresetOp.EQ]: { type: 'boolean' },
    [ConditionPresetOp.NEQ]: { type: 'boolean' },
    [ConditionPresetOp.IS_TRUE]: null,
    [ConditionPresetOp.IS_FALSE]: null,
    [ConditionPresetOp.IN]: {
      type: 'array',
      items: { type: 'boolean' },
    },
    [ConditionPresetOp.NIN]: {
      type: 'array',
      items: { type: 'boolean' },
    },
  },
}
