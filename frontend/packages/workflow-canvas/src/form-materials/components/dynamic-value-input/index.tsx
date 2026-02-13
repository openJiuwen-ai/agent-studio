/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'

import { JsonSchemaUtils, IJsonSchema, useTypeManager, type JsonSchemaTypeManager } from '@flowgram.ai/json-schema'
import { IconButton } from '@douyinfe/semi-ui'
import { IconSetting } from '@douyinfe/semi-icons'

import { IFlowConstantRefValue, IFlowConstantValue } from '../../'
import { createInjectMaterial } from '../../'
import { InjectVariableSelector } from '../../'
import { TypeSelector } from '../../'
import { ConstantInput, ConstantInputStrategy } from '../../'

import './styles.css'
import { useIncludeSchema, useRefVariable, useSelectSchema } from './hooks'

interface PropsType {
  value?: IFlowConstantRefValue
  onChange: (value?: IFlowConstantRefValue) => void
  readonly?: boolean
  hasError?: boolean
  style?: React.CSSProperties
  schema?: IJsonSchema
  constantProps?: {
    strategies?: ConstantInputStrategy[]
    schema?: IJsonSchema // set schema of constant input only
    [key: string]: any
  }
}

const buildDefaultConstant = (schema?: IJsonSchema): IFlowConstantValue => ({
  type: 'constant',
  content: '',
  schema: schema || { type: 'string' },
})

export function DynamicValueInput({ value, onChange, readonly, style, schema: schemaFromProps, constantProps }: PropsType) {
  const refVariable = useRefVariable(value)
  const [selectSchema, setSelectSchema] = useSelectSchema(schemaFromProps, constantProps, value)
  const includeSchema = useIncludeSchema(schemaFromProps)

  const typeManager = useTypeManager() as JsonSchemaTypeManager

  const renderTypeSelector = () => {
    if (schemaFromProps) {
      return <TypeSelector value={schemaFromProps} readonly={true} />
    }

    if (value?.type === 'ref') {
      const schema = refVariable?.type ? JsonSchemaUtils.astToSchema(refVariable?.type) : undefined

      return <TypeSelector value={schema} readonly={true} />
    }

    return (
      <TypeSelector
        value={selectSchema}
        onChange={_v => {
          setSelectSchema(_v || { type: 'string' })

          const schema = _v || { type: 'string' }
          const content: any = undefined

          onChange({
            type: 'constant',
            content,
            schema,
          })
        }}
        readonly={readonly}
      />
    )
  }

  const handleRefChange = (_v?: string[]) => {
    const constantSchema = schemaFromProps || selectSchema || { type: 'string' }
    if (_v) {
      onChange({ type: 'ref', content: _v })
    } else {
      onChange(buildDefaultConstant(constantSchema))
    }
  }

  const renderMain = () => {
    if (value?.type === 'ref') {
      // Display Variable Or Delete
      return (
        <InjectVariableSelector
          style={{ width: '100%' }}
          value={value?.content}
          onChange={_v => handleRefChange(_v)}
          includeSchema={includeSchema}
          readonly={readonly}
        />
      )
    }

    const constantSchema = schemaFromProps || selectSchema || { type: 'string' }

    return (
      <ConstantInput
        value={value?.content}
        onChange={_v => onChange({ type: 'constant', content: _v, schema: constantSchema })}
        schema={constantSchema || { type: 'string' }}
        readonly={readonly}
        fallbackRenderer={() => (
          <InjectVariableSelector style={{ width: '100%' }} onChange={_v => handleRefChange(_v)} includeSchema={includeSchema} readonly={readonly} />
        )}
        {...constantProps}
        strategies={[...(constantProps?.strategies || [])]}
      />
    )
  }

  const renderTrigger = () => (
    <InjectVariableSelector
      style={{ width: '100%' }}
      value={value?.type === 'ref' ? value?.content : undefined}
      onChange={_v => handleRefChange(_v)}
      includeSchema={includeSchema}
      readonly={readonly}
      triggerRender={() => <IconButton disabled={readonly} size="small" icon={<IconSetting size="small" />} />}
    />
  )

  return (
    <div className="gedit-m-dynamic-value-input-container" style={style}>
      <div className="gedit-m-dynamic-value-input-type">{renderTypeSelector()}</div>
      <div className="gedit-m-dynamic-value-input-main">{renderMain()}</div>
      <div className="gedit-m-dynamic-value-input-trigger">{renderTrigger()}</div>
    </div>
  )
}

DynamicValueInput.renderKey = 'dynamic-value-input-render-key'
export const InjectDynamicValueInput = createInjectMaterial(DynamicValueInput)
