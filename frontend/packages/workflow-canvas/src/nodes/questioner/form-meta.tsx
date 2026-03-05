/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormMeta, ValidateTrigger, Field } from '@flowgram.ai/free-layout-editor'
import { InputNumber } from '@douyinfe/semi-ui'

import { provideJsonSchemaOutputs, syncVariableTitle } from '../../form-materials'
import { validation } from './validation'
import { FlowNodeJSON } from '../../typings'
import { FormHeader, FormContent, FormModel, FormPrompt, FormInput, FormOutput, FormItem, FormDisplay } from '../../form-components'
import { useIsSidebar } from '../../hooks'
import { useTranslation } from '../../i18n'

const FormMaxResponse = () => {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()

  return (
    <Field<number> name="inputs.max_response">
      {({ field, meta }: any) => {
        if (!isSidebar) {
          return <FormDisplay label={t('workflowCanvas.nodes.questioner.maxQuestions')} content={field.value} />
        }
        return (
          <FormItem name={t('workflowCanvas.nodes.questioner.maxQuestions')} description={t('workflowCanvas.nodes.questioner.maxQuestionsDescription')}>
            <InputNumber
              value={field.value}
              onChange={v => field.onChange(v as number)}
              min={1}
              max={10}
              style={{ width: '100%' }}
              validateStatus={meta?.error ? 'error' : 'default'}
            />
            {meta?.error && <div style={{ color: 'var(--semi-color-danger)', fontSize: 12, marginTop: 4 }}>{meta.error}</div>}
          </FormItem>
        )
      }}
    </Field>
  )
}

export const renderForm = () => {
  return (
    <>
      <FormHeader />
      <FormContent>
        <FormInput showAddButton={false} defaultFields={['query']} schema={{ type: 'string' }} />
        <FormModel showHistoryEnable={true} />
        <FormMaxResponse />
        <FormOutput defaultFields={['user_response']} minProperties={2} expandable={true} excludeTypes={['object', 'date-time', 'array', 'file']} />
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
  },
}
