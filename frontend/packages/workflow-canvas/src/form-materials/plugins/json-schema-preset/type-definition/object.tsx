/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable react/prop-types */
import React from 'react'

import { t } from '../../../../i18n'

import { ConditionPresetOp, JsonCodeEditor } from '../../..'

import { type JsonSchemaTypeRegistry } from '../types'

export const objectRegistry: Partial<JsonSchemaTypeRegistry> = {
  type: 'object',
  ConstantRenderer: props => {
    const schemaKey = JSON.stringify(props.schema)
    return (
      <JsonCodeEditor
        key={schemaKey}
        mini
        compact
        value={props.value}
        onChange={v => props.onChange?.(v)}
        placeholder={t('workflowCanvas.formMaterials.input.pleaseInputObject')}
        readonly={props.readonly}
        defaultFormat="{}"
        expectedFieldType="object"
      />
    )
  },
  conditionRule: {
    [ConditionPresetOp.IS_EMPTY]: null,
    [ConditionPresetOp.IS_NOT_EMPTY]: null,
  },
}
