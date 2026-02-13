/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable react/prop-types */
import React from 'react'

import { ConditionPresetOp, JsonCodeEditor } from '../../..'
import { t } from '../../../../i18n'

import { type JsonSchemaTypeRegistry } from '../types'

export const arrayRegistry: Partial<JsonSchemaTypeRegistry> = {
  type: 'array',
  ConstantRenderer: props => {
    const schemaKey = JSON.stringify(props.schema)
    return (
      <JsonCodeEditor
        key={schemaKey}
        mini
        compact
        value={props.value}
        onChange={v => props.onChange?.(v)}
        placeholder={t('workflowCanvas.formMaterials.input.pleaseInputArray')}
        readonly={props.readonly}
        defaultFormat="[]"
        validateArrayElements={!!props.schema?.items?.type}
        arrayElementType={props.schema?.items?.type}
      />
    )
  },
  conditionRule: {
    [ConditionPresetOp.IS_EMPTY]: null,
    [ConditionPresetOp.IS_NOT_EMPTY]: null,
    [ConditionPresetOp.CONTAINS]: { type: 'array', extra: { weak: true } },
    [ConditionPresetOp.NOT_CONTAINS]: { type: 'array', extra: { weak: true } },
    [ConditionPresetOp.EQ]: { type: 'array', extra: { weak: true } },
    [ConditionPresetOp.NEQ]: { type: 'array', extra: { weak: true } },
  },
}
