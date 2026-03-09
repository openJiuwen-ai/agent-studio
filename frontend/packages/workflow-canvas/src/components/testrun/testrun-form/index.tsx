/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FC } from 'react'

import classNames from 'classnames'
import { Tooltip } from '@douyinfe/semi-ui'
import { HelpCircle } from 'lucide-react'
import { Input, Select, InputNumber, DatePicker } from '@douyinfe/semi-ui'
import dayjs from 'dayjs'
import { useTranslation } from '../../../i18n'

import { DisplaySchemaTag, JsonCodeEditor } from '../../../form-materials'
import { useFormMeta } from '../hooks/use-form-meta'
import { useFields } from '../hooks/use-fields'
import { useSyncDefault } from '../hooks'
import { FileInput } from '../../../form-materials/plugins/json-schema-preset/type-definition/file'

import styles from './index.module.less'

import { TestRunFormMetaItem } from './type'

interface TestRunFormProps {
  values: Record<string, unknown>
  setValues: (values: Record<string, unknown>) => void
  inputFormMeta?: TestRunFormMetaItem[] // 可选的输入节点表单定义
  workflowId?: string
  spaceId?: string
}

export const TestRunForm: FC<TestRunFormProps> = ({ values, setValues, inputFormMeta, workflowId, spaceId }) => {
  const { t } = useTranslation()
  const formMeta = useFormMeta()

  // 如果有inputFormMeta（输入中断时），使用它；否则使用工作流的formMeta
  const effectiveFormMeta = inputFormMeta || formMeta

  const fields = useFields({
    formMeta: effectiveFormMeta,
    values,
    setValues,
  })

  useSyncDefault({
    formMeta: effectiveFormMeta,
    values,
    setValues,
  })

  const renderField = (field: any) => {
    const hasError = field.error && !field.isValid

    switch (field.type) {
      case 'boolean':
        return (
          <div className={styles.fieldInput}>
            <Select
              size="small"
              placeholder={t('workflowCanvas.formMaterials.input.pleaseSelectBoolean')}
              optionList={[
                { label: t('workflowCanvas.formMaterials.input.true'), value: 1 },
                { label: t('workflowCanvas.formMaterials.input.false'), value: 0 },
              ]}
              value={field.value !== undefined && field.value !== null ? (field.value ? 1 : 0) : undefined}
              onChange={value => field.onChange(value !== undefined ? !!value : undefined)}
            />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
      case 'integer':
        return (
          <div className={styles.fieldInput}>
            <InputNumber
              precision={0}
              max={Number.MAX_SAFE_INTEGER}
              min={Number.MIN_SAFE_INTEGER}
              value={field.value}
              onChange={value => field.onChange(value)}
              type={hasError ? 'error' : 'default'}
            />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
      case 'number':
        return (
          <div className={styles.fieldInput}>
            <InputNumber
              hideButtons
              max={Number.MAX_VALUE}
              value={field.value}
              onChange={value => field.onChange(value)}
              type={hasError ? 'error' : 'default'}
            />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
      case 'object':
        return (
          <div className={classNames(styles.fieldInput, styles.codeEditorWrapper)}>
            <JsonCodeEditor
              value={field.value}
              onChange={value => field.onChange(value)}
              showErrors={hasError}
              renderError={error => <div className={styles.errorMessage}>{field.error || error}</div>}
              expectedFieldType="object"
            />
          </div>
        )
      case 'array':
        return (
          <div className={classNames(styles.fieldInput, styles.codeEditorWrapper)}>
            <JsonCodeEditor
              value={field.value}
              onChange={value => field.onChange(value)}
              defaultFormat="[]"
              showErrors={hasError}
              renderError={error => <div className={styles.errorMessage}>{field.error || error}</div>}
              validateArrayElements={!!field.itemsType}
              arrayElementType={field.itemsType}
              expectedFieldType="array"
            />
          </div>
        )
      case 'file':
        return (
          <div className={styles.fieldInput}>
            <FileInput
              value={field.value}
              onChange={value => field.onChange(value)}
              readonly={false}
              context="testrun"
              fileType={field.fileType || 'default'}
            />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
      case 'date-time':
        return (
          <div className={styles.fieldInput}>
            <DatePicker
              size="small"
              type="dateTime"
              density="compact"
              style={{ width: '100%' }}
              value={field.value ? dayjs(field.value).toDate() : undefined}
              onChange={date => field.onChange(date ? dayjs(date).format('YYYY-MM-DDTHH:mm:ss.SSSZ') : undefined)}
            />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
      default:
        return (
          <div className={styles.fieldInput}>
            <Input value={field.value} onChange={value => field.onChange(value)} type={hasError ? 'error' : 'default'} />
            {hasError && <div className={styles.errorMessage}>{field.error}</div>}
          </div>
        )
    }
  }

  // Show empty state if no fields
  if (fields.length === 0) {
    return (
      <div className={styles.formContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyText}>{t('workflowCanvas.testrunForm.noInputNeeded')}</div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.formContainer}>
      {fields.map(field => (
        <div key={field.name} className={styles.fieldGroup}>
          <label htmlFor={field.name} className={styles.fieldLabel}>
            {field.name}
            {field.description && (
              <Tooltip content={field.description} spacing={5}>
                <HelpCircle size={14} className={styles.helpIcon} />
              </Tooltip>
            )}
            {field.required && <span className={styles.requiredIndicator}>*</span>}
            <span className={styles.fieldTypeIndicator}>
              <DisplaySchemaTag
                value={{
                  type: field.type,
                  items: field.itemsType
                    ? {
                        type: field.itemsType,
                      }
                    : undefined,
                  fileType: field.fileType,
                }}
              />
            </span>
          </label>
          {renderField(field)}
        </div>
      ))}
    </div>
  )
}
