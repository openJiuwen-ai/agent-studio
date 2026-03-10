/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormMeta, ValidateTrigger } from '@flowgram.ai/free-layout-editor'

import {
  provideJsonSchemaOutputs,
  syncVariableTitle,
  autoRenameRefEffect,
  validateWhenVariableSync,
} from '../../form-materials'
import { FormHeader, FormContent, FormInput, FormOutput } from '../../form-components'
import { HttpRequestNodeData } from './types'
import { MethodSelector } from './components'

export const FormRender = () => {
  return (
    <>
      <FormHeader />
      <FormContent>
        <MethodSelector />
        <FormInput
          showAddButton={false}
          deleteable={false}
          nameEditable={false}
          useFieldSchema={true}
        />
        <FormOutput showAddButton={false} readonly={true} />
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta<HttpRequestNodeData> = {
  render: () => <FormRender />,
  validateTrigger: ValidateTrigger.onChange,
  validate: async () => ({ errors: [], warnings: [] }),
  plugins: [],
  effect: {
    title: syncVariableTitle,
    outputs: provideJsonSchemaOutputs,
    'inputs.inputParameters.*': [...autoRenameRefEffect, ...validateWhenVariableSync({ scope: 'public' })],
    // Conditionally show/hide body field based on method
    'inputs.method.content': [
      (value, { setFieldState }) => {
        const methodValue = value as string
        const shouldShowBody = ['POST', 'PUT', 'PATCH'].includes(methodValue)

        setFieldState('inputs.inputParameters.body', (state) => ({
          ...state,
          hidden: !shouldShowBody,
          disabled: !shouldShowBody,
        }))
      },
    ],
  },
}
