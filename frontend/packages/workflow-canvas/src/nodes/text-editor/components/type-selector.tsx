import { Field, type FieldRenderProps } from '@flowgram.ai/free-layout-editor'

import { FormItem, FormSelect } from '../../../form-components'
import { useIsSidebar } from '../../../hooks'
import { useTranslation } from '../../../i18n'

interface TextEditTypeOption {
  label: string
  value: string
}

export function TypeSelector() {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()

  const editTypeOptions: TextEditTypeOption[] = [
    { label: t('workflowCanvas.textEditor.stringConcatenation'), value: 'StringConcatenation' },
    { label: t('workflowCanvas.textEditor.stringSplitting'), value: 'StringSplitting' },
  ]

  if (!isSidebar) {
    return null
  }

  return (
    <FormItem name={t('workflowCanvas.textEditor.textProcessingMethod')} vertical>
      <Field name="inputs.textEditorParam.editType" defaultValue="StringConcatenation">
        {({ field }: FieldRenderProps<string>) => {
          return <FormSelect value={field.value} onChange={field.onChange} options={editTypeOptions} />
        }}
      </Field>
    </FormItem>
  )
}
