/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'
import { Select } from '@douyinfe/semi-ui'

import { useIsSidebar } from '../../../hooks'
import { FormItem } from '../../../form-components'
import { useTranslation } from '../../../i18n'

export function MethodSelector() {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()

  if (!isSidebar) {
    return null
  }

  const methodOptions = [
    { label: 'GET', value: 'GET' },
    { label: 'POST', value: 'POST' },
    { label: 'PUT', value: 'PUT' },
    { label: 'DELETE', value: 'DELETE' },
    { label: 'PATCH', value: 'PATCH' },
    { label: 'HEAD', value: 'HEAD' },
    { label: 'OPTIONS', value: 'OPTIONS' },
  ]

  return (
    <Field<{ type: string; content: string }> name="inputs.inputParameters.method">
      {({ field }) => {
        const currentMethod = field.value?.content || 'GET'

        return (
          <FormItem name={t('workflowCanvas.formInput.method') || 'method'}>
            <Select
              value={currentMethod}
              onChange={(value) => {
                field.onChange({
                  ...field.value,
                  type: 'constant',
                  content: value as string,
                })
              }}
              style={{ width: '100%' }}
            >
              {methodOptions.map((methodOption) => (
                <Select.Option 
                  key={methodOption.value} 
                  value={methodOption.value}>
                  {methodOption.label}
                </Select.Option>
              ))}
            </Select>
          </FormItem>
        )
      }}
    </Field>
  )
}
