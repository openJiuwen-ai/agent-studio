/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */
import { useMemo, useEffect, useRef } from 'react'

import { Field } from '@flowgram.ai/free-layout-editor'
import { Select as SemiSelect, Modal } from '@douyinfe/semi-ui'

import { useIsSidebar } from '../../../hooks'
import { useTranslation } from '../../../i18n'
import { PythonCodeEditor, TypeScriptCodeEditor } from '../../../form-materials'
import { FormItem } from '../../../form-components'
import { CompactSelect, LanguageSelectContainer } from './styles'
import { getCodeTemplate, shouldUpdateTemplate, isTemplateForLanguage } from './templates'

export function Code() {
  const isSidebar = useIsSidebar()
  const { t } = useTranslation()

  if (!isSidebar) {
    return null
  }

  const languageOptions = [
    { label: 'JavaScript', value: 'javascript' },
    { label: 'Python', value: 'python' },
  ]

  const prevLanguageRef = useRef('javascript')
  const templateUpdatedRef = useRef(false)

  return (
    <Field<string> name="inputs.language" defaultValue="javascript">
      {({ field: languageField }) => {
        const language = languageField.value || 'javascript'

        const editorLanguageId = useMemo(() => {
          return language === 'python' ? 'python' : 'typescript'
        }, [language])

        return (
          <Field<string> name="inputs.code">
            {({ field: codeField }) => {
              const handleLanguageChange = (prevLang?: string) => {
                const prevLanguage = prevLang || prevLanguageRef.current
                const currentCode = codeField.value || ''
                const template = getCodeTemplate(language)

                if (shouldUpdateTemplate(currentCode)) {
                  codeField.onChange(template.template)
                } else if (prevLanguage !== language) {
                  if (isTemplateForLanguage(currentCode, prevLanguage)) {
                    codeField.onChange(template.template)
                  }
                }
              }

              useEffect(() => {
                if (templateUpdatedRef.current) {
                  templateUpdatedRef.current = false
                  prevLanguageRef.current = language
                  return
                }

                handleLanguageChange()
                prevLanguageRef.current = language
              }, [language])

              const handleLanguageSelect = (value: string | number | any[] | Record<string, any> | undefined) => {
                const newLanguage = value as string

                if (newLanguage === language) {
                  return
                }

                const currentCode = codeField.value || ''
                const isOldTemplate = isTemplateForLanguage(currentCode, language)
                const isEdited = !shouldUpdateTemplate(currentCode) && !isOldTemplate

                if (isEdited) {
                  Modal.confirm({
                    title: t('workflowCanvas.formCode.switchLanguageTitle'),
                    content: t('workflowCanvas.formCode.switchLanguageMessage', {
                      language: newLanguage === 'python' ? 'Python' : 'JavaScript',
                    }),
                    okText: t('workflowCanvas.formCode.confirmSwitch'),
                    cancelText: t('workflowCanvas.formCode.cancel'),
                    onOk: () => {
                      languageField.onChange(newLanguage)
                      const newTemplate = getCodeTemplate(newLanguage)
                      codeField.onChange(newTemplate.template)
                      templateUpdatedRef.current = true
                    },
                    onCancel: () => {},
                  })
                } else {
                  languageField.onChange(newLanguage)
                }
              }

              return (
                <FormItem name={t('workflowCanvas.formCode.code')}>
                  <LanguageSelectContainer>
                    <CompactSelect
                      value={languageField.value}
                      onChange={handleLanguageSelect}
                      style={{
                        width: 96,
                      }}
                      size="small"
                    >
                      {languageOptions.map(option => (
                        <SemiSelect.Option key={option.value} value={option.value}>
                          {option.label}
                        </SemiSelect.Option>
                      ))}
                    </CompactSelect>
                  </LanguageSelectContainer>
                  {editorLanguageId === 'python' ? (
                    <PythonCodeEditor
                      value={codeField.value}
                      onChange={value => {
                        codeField.onChange(value)
                      }}
                    />
                  ) : (
                    <TypeScriptCodeEditor
                      value={codeField.value}
                      onChange={value => {
                        codeField.onChange(value)
                      }}
                    />
                  )}
                </FormItem>
              )
            }}
          </Field>
        )
      }}
    </Field>
  )
}
