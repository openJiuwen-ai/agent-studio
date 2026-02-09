/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'
import { IJsonSchema } from '@flowgram.ai/json-schema'

import { useIsSidebar } from '../../hooks'
import { FormItem, FormDisplay } from '../../form-components'
import { DisplayInputsValues, IFlowValue, InputsValues } from '../../form-materials'
import { useTranslation } from '../../i18n'

export interface FormInputProps {
  name?: string
  inputParametersName?: string
  showAddButton?: boolean
  defaultFields?: string[]
  schema?: IJsonSchema
  deleteable?: boolean
  nameEditable?: boolean
  /** 是否使用字段自身的 schema 限制（优先于全局 schema） */
  useFieldSchema?: boolean
}

export function FormInput({
  name,
  inputParametersName = 'inputs.inputParameters',
  showAddButton,
  defaultFields,
  schema,
  deleteable = true,
  nameEditable = true,
  useFieldSchema = false,
}: FormInputProps) {
  const { t } = useTranslation()
  var displayName = t('workflowCanvas.formInput.input')
  if (name) {
    displayName = t(name)
  }
  const isSidebar = useIsSidebar()

  if (!isSidebar) {
    return (
      <Field<Record<string, IFlowValue | undefined> | undefined> name={inputParametersName}>
        {({ field }) => <FormDisplay label={displayName} content={<DisplayInputsValues value={field.value} schema={schema} />} />}
      </Field>
    )
  }

  return (
    <FormItem name={displayName} vertical>
      <Field<Record<string, IFlowValue | undefined> | undefined> name={inputParametersName}>
        {({ field }) => {
          return (
            <InputsValues
              value={field.value}
              onChange={value => field.onChange(value)}
              showAddButton={showAddButton}
              defaultFields={defaultFields}
              schema={schema}
              deleteable={deleteable}
              nameEditable={nameEditable}
              useFieldSchema={useFieldSchema}
            />
          )
        }}
      </Field>
    </FormItem>
  )
}
