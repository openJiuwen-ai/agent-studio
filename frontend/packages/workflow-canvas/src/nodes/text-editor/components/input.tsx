import { Field, FieldRenderProps } from '@flowgram.ai/free-layout-editor'

import { useIsSidebar } from '../../../hooks'
import { FormItem, FormDisplay } from '../../../form-components'
import { InputsValues, IFlowValue, DisplayInputsValues } from '../../../form-materials'
import { useTranslation } from '../../../i18n'

interface InputProps {
  name?: string
  inputParametersName?: string
  showAddButton?: boolean
  defaultFields?: string[]
}

export function Input({ name, inputParametersName = 'inputs.inputParameters' }: InputProps) {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()
  const displayName = name || t('workflowCanvas.textEditor.input')

  if (!isSidebar) {
    return (
      <Field<Record<string, IFlowValue | undefined> | undefined> name={inputParametersName}>
        {({ field }) => <FormDisplay label={displayName} content={<DisplayInputsValues value={field.value} />} />}
      </Field>
    )
  }

  const validateSingleInputParameter = (value: Record<string, IFlowValue | undefined> | undefined) => {
    if (!value) return true

    const keys = Object.keys(value)

    // 如果没有元素，是有效的
    if (keys.length === 0) return true

    // 如果只有一个元素，是有效的
    if (keys.length === 1) return true

    // 如果有多个元素，只保留第一个元素
    if (keys.length > 1) {
      const firstKey = keys[0]
      const newValue: Record<string, IFlowValue | undefined> = {}
      newValue[firstKey] = value[firstKey]
      return newValue
    }

    return true
  }

  return (
    <>
      <Field name="inputs.textEditorParam.editType">
        {({ field }: FieldRenderProps<string>) => {
          if (field.value === 'StringSplitting') {
            return (
              <>
                <FormItem name={displayName} vertical>
                  <Field<Record<string, IFlowValue | undefined> | undefined> name={inputParametersName}>
                    {({ field }) => {
                      const handleChange = (value: Record<string, IFlowValue | undefined> | undefined) => {
                        const validationResult = validateSingleInputParameter(value)

                        if (typeof validationResult === 'object' && validationResult !== null) {
                          field.onChange(validationResult)
                        } else {
                          field.onChange(value)
                        }
                      }

                      return (
                        <div>
                          <InputsValues value={field.value} onChange={handleChange} showAddButton={false} />
                        </div>
                      )
                    }}
                  </Field>
                </FormItem>
              </>
            )
          }

          return (
            <FormItem name={displayName} vertical>
              <Field<Record<string, IFlowValue | undefined> | undefined> name={inputParametersName}>
                {({ field }) => <InputsValues value={field.value} onChange={value => field.onChange(value)} />}
              </Field>
            </FormItem>
          )
        }}
      </Field>
    </>
  )
}
