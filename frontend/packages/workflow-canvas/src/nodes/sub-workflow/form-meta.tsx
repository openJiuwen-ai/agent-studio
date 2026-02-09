/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field, FieldRenderProps, FormMeta, ValidateTrigger, FlowNodeJSON } from '@flowgram.ai/free-layout-editor'

import {
  provideJsonSchemaOutputs,
  syncVariableTitle,
  autoRenameRefEffect,
  validateWhenVariableSync,
  listenRefSchemaChange,
  InputsValuesTree,
  DisplayInputsValues,
  IFlowValue,
  JsonSchemaEditor,
} from '../../form-materials'
import { validation } from './validation'
import { JsonSchema } from '../../typings'
import { useIsSidebar } from '../../hooks'
import { FormHeader, FormContent, FormItem, FormDisplay, FormInput, FormOutput } from '../../form-components'
import { VersionField } from '@/components/Agent/VersionField'
import React, { useMemo } from 'react'
import { useTranslation } from '../../i18n'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import WorkflowService from '../../../../api-client/src/services/workflowService'
import { DataEvent, type Effect } from '@flowgram.ai/editor'
import { isContentConfigured } from './utils'
import { canvasDetailCache, buildOutputsSchemaFromNodes } from './index'

const renderForm = () => {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()
  const spaceId = useMemo(() => getDefaultSpaceId() || '', [])

  if (isSidebar) {
    return (
      <>
        <FormHeader />
        <FormContent>
          <FormItem name={t('workflowCanvas.formVersion.version')} vertical>
            <Field<string> name="configs.subWorkflow.workflowId">
              {({ field: { value: workflowId } }) => (
                <Field<string | undefined> name="configs.subWorkflow.workflowVersion">
                  {({ field: { value, onChange } }) => <VersionField workflowId={workflowId} value={value} onChange={onChange} spaceId={spaceId} />}
                </Field>
              )}
            </Field>
          </FormItem>

          <FormItem name={t('workflowCanvas.formInput.input')} vertical>
            <Field<Record<string, IFlowValue | undefined> | undefined> name="inputs.inputParameters">
              {({ field: { value, onChange } }) => (
                <Field<JsonSchema | undefined> name="configs.subWorkflow.startSchema">
                  {({ field: { value: startSchema } }) => (
                    <InputsValuesTree
                      value={value as any}
                      onChange={v => onChange(v as any)}
                      readonly={false}
                      deleteable={false}
                      nameEditable={false}
                      constantProps={{}}
                      schema={startSchema as any}
                      showAddButton={false}
                      allowAddChildren={false}
                    />
                  )}
                </Field>
              )}
            </Field>
          </FormItem>
          <FormItem name={t('workflowCanvas.formOutput.output')} vertical>
            <Field
              name="outputs"
              render={({ field: { value, onChange } }: FieldRenderProps<JsonSchema>) => (
                <JsonSchemaEditor
                  value={value}
                  onChange={(v: JsonSchema) => onChange(v)}
                  showAddButton={false}
                  minProperties={Number.MAX_SAFE_INTEGER}
                  defaultFields={Object.keys(value?.properties || {})}
                  readonly={true}
                  expandable={true}
                />
              )}
            />
          </FormItem>
        </FormContent>
      </>
    )
  }
  return (
    <>
      <FormHeader />
      <FormContent>
        <FormDisplay
          label={t('workflowCanvas.formVersion.version')}
          content={
            <Field<string> name="configs.subWorkflow.workflowId">
              {({ field: { value: wfId } }) => (
                <Field<string> name="configs.subWorkflow.workflowVersion">
                  {({ field: { value } }) => <VersionField workflowId={wfId} value={value || 'draft'} spaceId={spaceId} readonly />}
                </Field>
              )}
            </Field>
          }
        />

        <FormDisplay
          label={t('workflowCanvas.formInput.input')}
          content={
            <Field<Record<string, IFlowValue | undefined> | undefined> name="inputs.inputParameters">
              {({ field: { value } }) => (
                <Field<JsonSchema | undefined> name="configs.subWorkflow.startSchema">
                  {({ field: { value: startSchema } }) => <DisplayInputsValues value={value} schema={startSchema as any} />}
                </Field>
              )}
            </Field>
          }
        />
        <FormOutput />
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta<FlowNodeJSON> = {
  render: renderForm,
  validateTrigger: ValidateTrigger.onChange,
  validate: validation,
  effect: {
    title: syncVariableTitle,
    outputs: provideJsonSchemaOutputs,
    inputsValues: [...autoRenameRefEffect, ...validateWhenVariableSync({ scope: 'public' })],
    'inputsValues.*': listenRefSchemaChange(() => {
      // Schema reference updated
    }),
    'configs.subWorkflow.workflowVersion': [
      {
        event: DataEvent.onValueInitOrChange,
        effect: (params => {
          const run = async () => {
            const { value, form } = params
            const workflowId = form?.getValueIn?.('configs.subWorkflow.workflowId')
            const spaceId = getDefaultSpaceId() || ''
            if (!workflowId) return

            const cacheKey = `${workflowId}-${spaceId}-${value === 'draft' ? 'draft' : value}`

            // Clear cache to ensure we get the latest data
            canvasDetailCache.delete(cacheKey)

            let wfDetail: any
            let nodesList: any[]

            const requestParams: any = { workflow_id: workflowId, space_id: spaceId }
            if (value && value !== 'draft') {
              requestParams.version = value
            }

            const response = await WorkflowService.getWorkflowCanvas(requestParams)
            wfDetail = response?.data?.workflow || {}
            const fullSchema = wfDetail?.schema ? JSON.parse(wfDetail.schema) : {}
            nodesList = Array.isArray(fullSchema?.nodes) ? fullSchema.nodes : []

            const result = { wfDetail, fullSchema, nodesList }
            canvasDetailCache.set(cacheKey, result)

            const startNode = nodesList.find((n: any) => String(n?.type) === '1')
            const startSchema = startNode?.data?.outputs

            const buildInputsFromStart = (schema: any): Record<string, any> => {
              const properties = schema?.properties || {}
              const keys = Object.keys(properties)
              const result: Record<string, any> = {}
              keys.forEach((name, index) => {
                const propSchema = properties[name] || { type: 'string' }
                if (propSchema?.type === 'object' && propSchema?.properties) {
                  result[name] = buildInputsFromStart(propSchema)
                } else {
                  result[name] = { type: 'constant', content: '', schema: propSchema, extra: { index: index + 1 } }
                }
              })
              return result
            }

            const builtInputParameters = startSchema ? buildInputsFromStart(startSchema) : {}
            const prevInputParameters = form?.getValueIn?.('inputs.inputParameters') || {}
            const mergeInputs = (built: any, prev: any): any => {
              if (!built || typeof built !== 'object') return prev || built
              const result: Record<string, any> = {}
              const keys = Object.keys(built || {})
              keys.forEach(k => {
                const builtVal = built[k]
                const prevVal = prev ? prev[k] : undefined
                // 若之前已有赋值（常量/引用/表达式/模板），优先保留之前的值
                const isFlowVal =
                  prevVal &&
                  typeof prevVal === 'object' &&
                  (prevVal.type === 'constant' || prevVal.type === 'ref' || prevVal.type === 'expression' || prevVal.type === 'template')
                if (isFlowVal) {
                  // 更新 schema 以匹配最新 startSchema，但保留 content
                  if (prevVal.type === 'constant') {
                    result[k] = { ...prevVal, schema: builtVal?.schema || builtVal?.schema === undefined ? builtVal?.schema : prevVal.schema }
                  } else {
                    result[k] = prevVal
                  }
                } else if (builtVal && typeof builtVal === 'object' && !builtVal.type) {
                  // 子对象，递归合并
                  result[k] = mergeInputs(builtVal, prevVal || {})
                } else {
                  result[k] = builtVal
                }
              })
              return result
            }
            const inputParameters = mergeInputs(builtInputParameters, prevInputParameters)

            const outputsSchema = buildOutputsSchemaFromNodes(nodesList)

            form?.setValueIn?.('configs.subWorkflow.startSchema', startSchema)
            form?.setValueIn?.('inputs.inputParameters', inputParameters)
            form?.setValueIn?.('outputs', outputsSchema)
          }

          run()
          return () => null
        }) as Effect,
      },
    ],
  },
}
