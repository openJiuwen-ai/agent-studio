/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useLayoutEffect } from 'react'
import { FormMeta, ValidateTrigger, FlowNodeJSON, WorkflowNodePortsData, Field, FieldRenderProps } from '@flowgram.ai/free-layout-editor'

import { provideJsonSchemaOutputs, syncVariableTitle, autoRenameRefEffect, validateWhenVariableSync, listenRefSchemaChange } from '../../form-materials'
import { validation } from './validation'
import { useNodeRenderContext } from '../../hooks'
import { FormHeader, FormContent, FormDisplay } from '../../form-components'
import { FormInput, FormOutput } from '../../form-components'

function PluginInputs() {
  return <FormInput name="输入" showAddButton={false} deleteable={false} nameEditable={false} useFieldSchema={true} />
}

function PluginOutputs() {
  const { node } = useNodeRenderContext()

  useLayoutEffect(() => {
    window.requestAnimationFrame(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    })
  }, [node])

  return <FormOutput name="输出" outputName="outputs" showAddButton={false} readonly={true} />
}

const renderForm = () => {
  return (
    <>
      <FormHeader />
      <FormContent>
        <Field<string> name="pluginName">
          {({ field: { value } }: FieldRenderProps<string>) => (
            <FormDisplay label="Plugin" content={value || ''} />
          )}
        </Field>
        <div className="flex flex-col gap-4">
          <PluginInputs />
          <PluginOutputs />
        </div>
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
  },
}
