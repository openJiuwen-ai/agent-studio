/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */
import React from 'react'
import { Button, IconButton } from '@douyinfe/semi-ui'
import { IconPlus, IconDelete, IconSetting } from '@douyinfe/semi-icons'

import { FlowNodeJSON, Field, FormMeta } from '@flowgram.ai/free-layout-editor'
import { SubCanvasRender } from '@flowgram.ai/free-container-plugin'
import { PrivateScopeProvider, ValidateTrigger } from '@flowgram.ai/editor'
import {
  BatchOutputs,
  createBatchOutputsFormPlugin,
  IFlowValue,
  IFlowConstantRefValue,
  IFlowConstantValue,
  DisplayOutputs,
  InputsValues,
  InjectVariableSelector,
  DisplayInputsValues,
  IFlowRefValue,
  BlurInput,
  ConstantInput,
  InjectDynamicValueInput,
} from '../../form-materials'
import { useTranslation } from '../../i18n'
import { provideLoopEffect, exportIntermediateVarsEffect } from './effects'

import { FormHeader, FormContent, FormItem, Feedback, FormSelect, FormDisplay } from '../../form-components'
import { useIsSidebar, useNodeRenderContext } from '../../hooks'
import { useObjectList } from '../../form-materials'
import { validation } from './validation'
import { TypeSelector } from '../../form-materials/components/type-selector'

export enum LoopType {
  ARRAY_LOOP = 'arrayLoop',
  NUM_LOOP = 'numLoop',
}

interface LoopNodeJSON extends FlowNodeJSON {
  data: {
    title?: string
    inputs?: {
      loopParam?: {
        type?: LoopType
        loopNum?: IFlowValue
        loopArray?: Record<string, IFlowValue | undefined>
        intermediateVar?: {
          result?: IFlowRefValue
          item?: IFlowRefValue
        }
      }
    }
    outputs?: {
      type: 'object'
      properties?: Record<string, unknown>
    }
  }
}

const ArrayInputsValues = ({
  value,
  onChange,
}: {
  value?: Record<string, IFlowValue | undefined>
  onChange: (value?: Record<string, IFlowValue | undefined>) => void
}) => {
  const { t } = useTranslation()
  const { list, updateKey, updateValue, remove, add } = useObjectList<IFlowValue | undefined>({
    value,
    onChange,
    sortIndexKey: 'extra.index',
  })

  React.useEffect(() => {
    const isEmpty = !value || Object.keys(value).length === 0
    if (isEmpty && list.length === 0) {
      add({
        type: 'constant',
        content: [],
        schema: { type: 'array', items: { type: 'string' } },
      })
    }
  }, [value, list.length, add])

  return (
    <div>
      {list.map(item => {
        const itemSchema = (item.value as IFlowConstantValue)?.schema
        const itemsType = itemSchema?.items?.type || 'string'
        const fullSchema = { type: 'array', items: { type: itemsType } }

        const handleTypeChange = (_v?: { type: string }) => {
          if (!_v) return
          updateValue(item.id, {
            ...item.value,
            schema: { type: 'array', items: { type: _v.type } },
          } as IFlowValue)
        }

        const handleContentChange = (content: unknown) => {
          updateValue(item.id, {
            ...item.value,
            content,
          } as IFlowValue)
        }

        const handleRefChange = (ref: string[] | undefined) => {
          if (ref) {
            updateValue(item.id, { type: 'ref', content: ref, schema: itemSchema } as IFlowValue)
          } else {
            updateValue(item.id, {
              type: 'constant',
              content: [],
              schema: itemSchema || fullSchema,
            } as IFlowValue)
          }
        }

        return (
          <div key={item.id} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
            <BlurInput
              style={{ width: 100, minWidth: 100, maxWidth: 100 }}
              size="small"
              value={item.key}
              onChange={v => updateKey(item.id, v)}
              placeholder={t('workflowCanvas.formMaterials.common.inputKey')}
            />
            <div className="gedit-m-dynamic-value-input-container" style={{ flexGrow: 1 }}>
              {item.value?.type === 'ref' ? (
                <>
                  <div className="gedit-m-dynamic-value-input-type">
                    <TypeSelector value={fullSchema} readonly={true} />
                  </div>
                  <div className="gedit-m-dynamic-value-input-main">
                    <InjectVariableSelector
                      style={{ width: '100%' }}
                      value={item.value.content}
                      onChange={handleRefChange}
                      includeSchema={{ type: 'array', extra: { weak: true } }}
                    />
                  </div>
                  <div className="gedit-m-dynamic-value-input-trigger">
                    <IconButton theme="borderless" icon={<IconDelete size="small" />} size="small" onClick={() => handleRefChange(undefined)} />
                  </div>
                </>
              ) : (
                <>
                  <div className="gedit-m-dynamic-value-input-type">
                    <TypeSelector value={{ type: itemsType }} onChange={handleTypeChange} excludeTypes={['array', 'object']} />
                  </div>
                  <div className="gedit-m-dynamic-value-input-main">
                    <ConstantInput
                      value={item.value?.content}
                      onChange={handleContentChange}
                      schema={fullSchema}
                      fallbackRenderer={() => (
                        <InjectVariableSelector style={{ width: '100%' }} onChange={handleRefChange} includeSchema={{ type: 'array', extra: { weak: true } }} />
                      )}
                    />
                  </div>
                  <div className="gedit-m-dynamic-value-input-trigger">
                    <InjectVariableSelector
                      value={undefined}
                      onChange={handleRefChange}
                      includeSchema={{ type: 'array', extra: { weak: true } }}
                      triggerRender={() => <IconButton theme="borderless" icon={<IconSetting size="small" />} size="small" />}
                    />
                  </div>
                </>
              )}
            </div>
            <IconButton theme="borderless" icon={<IconDelete size="small" />} size="small" onClick={() => remove(item.id)} />
          </div>
        )
      })}
      <Button
        icon={<IconPlus />}
        size="small"
        onClick={() =>
          add({
            type: 'constant',
            content: [],
            schema: { type: 'array', items: { type: 'string' } },
          })
        }
      />
    </div>
  )
}

export const LoopFormRender = () => {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const { node } = useNodeRenderContext()
  const formHeight = 110

  const loopSettings = (
    <>
      <FormItem name={t('workflowCanvas.loop.loopType')} vertical>
        <Field<LoopType> name={`inputs.loopParam.type`}>
          {({ field }) => (
            <FormSelect
              style={{ width: '100%' }}
              value={field.value || LoopType.NUM_LOOP}
              onChange={(value: string | string[]) => {
                if (typeof value === 'string') {
                  field.onChange(value as LoopType)
                }
              }}
              options={[
                { label: t('workflowCanvas.loop.specifyCount'), value: LoopType.NUM_LOOP },
                { label: t('workflowCanvas.loop.arrayLoop'), value: LoopType.ARRAY_LOOP },
              ]}
            />
          )}
        </Field>
      </FormItem>

      <Field<LoopType> name={`inputs.loopParam.type`}>
        {({ field }) => {
          if (field.value === LoopType.NUM_LOOP) {
            return (
              <FormItem name={t('workflowCanvas.loop.loopCount')} vertical>
                <Field<IFlowValue> name={`inputs.loopParam.loopNum`}>
                  {({ field: numField }) => (
                    <PrivateScopeProvider>
                      <InjectDynamicValueInput
                        style={{ width: '100%' }}
                        value={numField.value as IFlowConstantRefValue}
                        onChange={value => {
                          if (value?.type === 'constant' && typeof value.content === 'number') {
                            const safeValue = Math.max(1, Math.min(1000, value.content))
                            numField.onChange({
                              ...value,
                              content: safeValue,
                            } as IFlowValue)
                          } else {
                            numField.onChange(value as IFlowValue)
                          }
                        }}
                        schema={{ type: 'integer' }}
                      />
                    </PrivateScopeProvider>
                  )}
                </Field>
              </FormItem>
            )
          }
          return <div />
        }}
      </Field>

      <Field<LoopType> name={`inputs.loopParam.type`}>
        {({ field }) => {
          if (field.value === LoopType.ARRAY_LOOP) {
            return (
              <FormItem name={t('workflowCanvas.loop.loopArray')} vertical>
                <Field<Record<string, IFlowValue | undefined> | undefined> name={`inputs.loopParam.loopArray`}>
                  {({ field: arrayField }) => {
                    const validKeys = Object.keys(arrayField.value || {}).filter(key => key && key.trim() !== '')
                    const showHint = validKeys.length >= 2
                    return (
                      <PrivateScopeProvider>
                        <ArrayInputsValues value={arrayField.value} onChange={value => arrayField.onChange(value)} />
                        {showHint && (
                          <div style={{ color: 'var(--semi-color-text-2)', fontSize: 12, marginTop: 4 }}>
                            {t('workflowCanvas.loop.arrayTruncateHint')}
                          </div>
                        )}
                      </PrivateScopeProvider>
                    )
                  }}
                </Field>
              </FormItem>
            )
          }
          return <div />
        }}
      </Field>

      <FormItem name={t('workflowCanvas.loop.intermediateVar')} vertical>
        <Field<Record<string, IFlowValue | undefined> | undefined> name="inputs.loopParam.intermediateVar">
          {({ field }) => (
            <Field<Record<string, IFlowValue | undefined> | undefined> name="inputs.loopParam.loopArray">
              {({ field: arrayField }) => {
                const arrayKeys = Object.keys(arrayField.value || {}).filter(k => k && k.trim() !== '')
                return (
                  <PrivateScopeProvider>
                    <InputsValues
                      value={field.value}
                      onChange={value => field.onChange(value)}
                      onValidateKey={(key, itemId, allItems) => {
                        if (key === 'index') {
                          return t('workflowCanvas.loop.indexReserved')
                        }
                        const isDuplicate = allItems.some(item => item.id !== itemId && item.key === key)
                        if (isDuplicate && key) {
                          return t('workflowCanvas.loop.variableExists', { key })
                        }
                        if (arrayKeys.includes(key)) {
                          return t('workflowCanvas.loop.variableNameDuplicate')
                        }
                        return undefined
                      }}
                    />
                  </PrivateScopeProvider>
                )
              }}
            </Field>
          )}
        </Field>
      </FormItem>

      <Field<Record<string, IFlowRefValue | undefined> | undefined> name={`outputs.properties`}>
        {({ field, fieldState }) => (
          <Field<Record<string, IFlowValue | undefined> | undefined> name={`inputs.loopParam.loopArray`}>
            {({ field: arrayField }) => {
              const loopArrayKeys = Object.keys(arrayField.value || {}).filter(key => key && key.trim() !== '')
              const skipKeys = ['index', ...loopArrayKeys]

              return (
                <FormItem name={t('workflowCanvas.loop.loopOutput')} vertical>
                  <BatchOutputs
                    style={{ width: '100%' }}
                    value={field.value}
                    onChange={val => field.onChange(val)}
                    hasError={Object.keys(fieldState?.errors || {}).length > 0}
                    skipKeys={skipKeys}
                  />
                  <Feedback errors={fieldState?.errors} />
                </FormItem>
              )
            }}
          </Field>
        )}
      </Field>
    </>
  )

  const loopSummary = (
    <Field<LoopType> name={`inputs.loopParam.type`}>
      {({ field }) => {
        const loopType = field.value || LoopType.NUM_LOOP

        if (loopType === LoopType.NUM_LOOP) {
          return <></>
        } else if (loopType === LoopType.ARRAY_LOOP) {
          return (
            <Field<Record<string, IFlowValue | undefined> | undefined> name={`inputs.loopParam.loopArray`}>
              {({ field: arrayField }) => (
                <FormDisplay
                  label={t('workflowCanvas.loop.input')}
                  content={<DisplayInputsValues value={arrayField.value} node={node} includePrivateScope={true} />}
                />
              )}
            </Field>
          )
        } else {
          return <></>
        }
      }}
    </Field>
  )

  const intermediateVarDisplay = (
    <Field<Record<string, IFlowValue | undefined> | undefined> name="inputs.loopParam.intermediateVar">
      {({ field }) => (
        <FormDisplay
          label={t('workflowCanvas.loop.intermediateVar')}
          content={<DisplayInputsValues value={field.value} node={node} includePrivateScope={true} />}
        />
      )}
    </Field>
  )

  const outputVarDisplay = (
    <Field<Record<string, IFlowRefValue | undefined> | undefined> name={`outputs.properties`}>
      {() => <FormDisplay label={t('workflowCanvas.loop.loopOutput')} content={<DisplayOutputs displayFromScope />} />}
    </Field>
  )

  if (isSidebar) {
    return (
      <>
        <FormHeader />
        <FormContent>{loopSettings}</FormContent>
      </>
    )
  }

  return (
    <>
      <FormHeader />
      <FormContent>
        {loopSummary}
        {intermediateVarDisplay}
        {outputVarDisplay}
        <SubCanvasRender offsetY={-formHeight} />
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta = {
  render: LoopFormRender,
  validateTrigger: ValidateTrigger.onChange,
  validate: validation,
  effect: {
    'inputs.loopParam': [...provideLoopEffect, ...exportIntermediateVarsEffect],
  },
  plugins: [createBatchOutputsFormPlugin({ outputKey: 'outputs.properties' })],
} as FormMeta<LoopNodeJSON>
