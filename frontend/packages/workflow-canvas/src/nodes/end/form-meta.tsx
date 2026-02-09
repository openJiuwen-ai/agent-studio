/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormMeta, ValidateTrigger } from '@flowgram.ai/free-layout-editor'

import { autoRenameRefEffect, listenRefSchemaChange, provideJsonSchemaOutputs, syncVariableTitle, validateWhenVariableSync } from '../../form-materials'
import { validation } from './validation'
import { FormHeader, FormContent, FormInput, FormContentEditor } from '../../form-components'
import { FormData } from './type'
import { Field } from '@flowgram.ai/free-layout-editor'
import { Typography } from '@douyinfe/semi-ui'
import { IFlowTemplateValue } from '../../form-materials'
import { useIsSidebar } from '../../hooks'
import { useTranslation } from '../../i18n'

export const renderForm = () => {
  const { t } = useTranslation()

  const SidebarNote: React.FC<{ show: boolean }> = ({ show }) => {
    const isSidebar = useIsSidebar()
    if (!isSidebar || !show) return null
    return (
      <div>
        <Typography.Text type="tertiary" size="small">
          {t('workflowCanvas.nodes.end.outputConfiguredNote')}
        </Typography.Text>
      </div>
    )
  }

  return (
    <>
      <FormHeader titleEditable={false} menuVisible={false} />
      <FormContent>
        <FormInput name={'workflowCanvas.formOutput.output'} />
        <Field<boolean> name="inputs.streaming">
          {({ field: streamingField }) => (
            <Field<IFlowTemplateValue> name="inputs.content">
              {({ field: contentField }) => {
                const hasContent = typeof contentField?.value?.content === 'string' && (contentField.value?.content as string).length > 0
                const defaultCollapsed = !(hasContent || streamingField.value === true)

                return (
                  <>
                    <FormContentEditor defaultCollapsed={defaultCollapsed} />
                    <SidebarNote show={hasContent} />
                  </>
                )
              }}
            </Field>
          )}
        </Field>
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta<FormData> = {
  validateTrigger: ValidateTrigger.onChange,
  validate: validation,
  render: renderForm,
  effect: {
    title: syncVariableTitle,
    outputs: provideJsonSchemaOutputs,
    inputsValues: [...autoRenameRefEffect, ...validateWhenVariableSync({ scope: 'public' })],
    'inputs.inputsParams.*': listenRefSchemaChange(params => {
      console.log(`[${params.context.node.id}][${params.name}] Schema Of Ref Updated`)
    }),
  },
}
