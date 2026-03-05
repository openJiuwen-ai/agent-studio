/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'

import { IconButton } from '@douyinfe/semi-ui'
import { IconMinus } from '@douyinfe/semi-icons'

import { IFlowConstantRefValue } from '../../'
import { InjectVariableSelector } from '../../'
import { InjectDynamicValueInput } from '../../'
import { BlurInput } from '../../'
import { VariableSelectorProvider } from '../variable-selector'

import { AssignRowProps } from './types'

export function AssignRow(props: AssignRowProps) {
  const {
    value = {
      operator: 'assign',
    },
    onChange,
    onDelete,
    readonly,
    skipVariable,
  } = props

  const leftSelector = value?.operator === 'assign' ? (
    <InjectVariableSelector
      style={{ width: '100%', height: 26 }}
      value={value?.left?.content}
      config={{ placeholder: 'Select Left' }}
      onChange={v =>
        onChange?.({
          ...value,
          left: { type: 'ref', content: v },
        })
      }
    />
  ) : (
    <BlurInput
      style={{ height: 26 }}
      size="small"
      placeholder="Input Name"
      value={value?.left}
      onChange={v =>
        onChange?.({
          ...value,
          left: v,
        })
      }
    />
  )

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <div style={{ width: 150, minWidth: 150, maxWidth: 150 }}>
        {skipVariable ? (
          <VariableSelectorProvider skipVariable={skipVariable}>
            {leftSelector}
          </VariableSelectorProvider>
        ) : (
          leftSelector
        )}
      </div>
      <div style={{ flexGrow: 1 }}>
        <InjectDynamicValueInput
          readonly={readonly}
          value={value?.right as IFlowConstantRefValue | undefined}
          onChange={v =>
            onChange?.({
              ...value,
              right: v,
            })
          }
        />
      </div>
      {onDelete && (
        <div>
          <IconButton size="small" theme="borderless" icon={<IconMinus />} onClick={() => onDelete?.()} />
        </div>
      )}
    </div>
  )
}

export { type AssignValueType } from './types'
