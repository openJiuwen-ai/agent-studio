/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'

import { useIsSidebar } from '../../hooks'
import { FormItem, FormDisplay } from '../../form-components'
import { JsonSchemaEditor, DisplayOutputs, IJsonSchema } from '../../form-materials'
import { useTranslation } from '../../i18n'

export interface FormOutputProps {
  name?: string
  outputName?: string
  showAddButton?: boolean
  defaultFields?: string[]
  minProperties?: number
  expandable?: boolean
  readonly?: boolean
  labelExtra?: React.ReactNode
  excludeTypes?: string[]
  maxNameBytes?: number
  excludeNestedArray?: boolean
  showDefaultValue?: boolean
  maxDescBytes?: number
}

export function FormOutput({
  name,
  outputName = 'outputs',
  showAddButton,
  defaultFields,
  minProperties,
  expandable = false,
  readonly = false,
  labelExtra,
  excludeTypes,
  maxNameBytes,
  excludeNestedArray,
  showDefaultValue,
  maxDescBytes,
}: FormOutputProps) {
  const { t } = useTranslation()
  var displayName = t('workflowCanvas.formOutput.output')
  if (name) {
    displayName = t(name)
  }
  const isSidebar = useIsSidebar()

  if (!isSidebar) {
    return (
      <Field<IJsonSchema> name={outputName}>
        {({ field }) => <FormDisplay label={displayName} labelExtra={labelExtra} content={<DisplayOutputs value={field.value} />} />}
      </Field>
    )
  }

  return (
    <>
      <FormItem name={displayName} vertical customComponent={labelExtra}>
        <Field<IJsonSchema> name={outputName}>
          {({ field }) => (
            <JsonSchemaEditor
              value={field.value}
              onChange={value => field.onChange(value)}
              showAddButton={showAddButton}
              defaultFields={defaultFields}
              minProperties={minProperties}
              config={{ addButtonText: '', excludeTypes, excludeNestedArray, showDefaultValue, maxDescBytes }}
              expandable={expandable}
              readonly={readonly}
              maxNameBytes={maxNameBytes}
            />
          )}
        </Field>
      </FormItem>
    </>
  )
}
