import { Field, type FieldRenderProps } from '@flowgram.ai/free-layout-editor'

import { IFlowTemplateValue, PromptEditorWithInputs } from '../../../form-materials'
import { FormItem } from '../../../form-components'
import { useIsSidebar } from '../../../hooks'
import { useTranslation } from '../../../i18n'

export function ConcatenationTemplate() {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()

  if (!isSidebar) {
    return null
  }

  return (
    <Field name="inputs.textEditorParam.editType">
      {({ field }: FieldRenderProps<string>) => {
        if (field.value === 'StringConcatenation') {
          return (
            <FormItem name={t('workflowCanvas.textEditor.concatenateTemplate')} vertical>
              <Field<Record<string, any> | undefined> name="inputs.inputParameters">
                {({ field: inputParametersField }) => {
                  const inputsValues = inputParametersField.value || {}
                  return (
                    <>
                      <Field<IFlowTemplateValue> name="inputs.textEditorParam.concatenateFormat">
                        {({ field }) => (
                          <PromptEditorWithInputs
                            {...({ disableMarkdownHighlight: false } as any)}
                            style={{ flexGrow: 4 }}
                            onChange={value => field.onChange(value as any)}
                            value={field.value}
                            inputsValues={inputsValues}
                          />
                        )}
                      </Field>
                    </>
                  )
                }}
              </Field>
            </FormItem>
          )
        }
        return <div />
      }}
    </Field>
  )
}
