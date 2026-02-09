import { Field, type FieldRenderProps } from '@flowgram.ai/free-layout-editor'
import { useState, useRef, useEffect } from 'react'

import { FormItem, FormSelect } from '../../../form-components'
import { useIsSidebar } from '../../../hooks'
import { Button, Input } from '@douyinfe/semi-ui'
import { useTranslation } from '../../../i18n'

interface DelimiterOption {
  label: string
  value: string[]
}

export function SplittingSelector() {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [customInputValue, setCustomInputValue] = useState('')
  const inputRef = useRef<any>(null)

  const delimiterOptions: DelimiterOption[] = [
    { label: t('workflowCanvas.splittingSelector.comma'), value: [',', '，'] },
    { label: t('workflowCanvas.splittingSelector.semicolon'), value: [';', '；'] },
    { label: t('workflowCanvas.splittingSelector.period'), value: ['.', '。'] },
  ]

  if (!isSidebar) {
    return null
  }

  return (
    <Field name="inputs.textEditorParam.editType">
      {({ field }: FieldRenderProps<string>) => {
        if (field.value === 'StringSplitting') {
          return (
            <FormItem name={t('workflowCanvas.textEditor.delimiter')} vertical>
              <Field name="inputs.textEditorParam.delimiters" defaultValue={[]}>
                {({ field: delimiterField }: FieldRenderProps<any>) => {
                  // 获取自定义分隔符（除了 'custom' 标识和预设分隔符之外的实际值）
                  const getCustomDelimiters = () => {
                    if (!Array.isArray(delimiterField.value)) return []
                    const presetValues = delimiterOptions.flatMap(opt => opt.value)
                    return delimiterField.value.filter(d => !presetValues.includes(d) && d !== 'custom')
                  }

                  const customDelimiters = getCustomDelimiters()

                  const getSelectValues = () => {
                    if (!Array.isArray(delimiterField.value)) return []

                    const values: string[] = []
                    delimiterField.value.forEach(delimiter => {
                      // 查找对应的预设选项
                      const option = delimiterOptions.find(opt => opt.value.includes(delimiter))
                      if (option) {
                        // 添加预设选项的第一个值作为标识
                        if (!values.includes(option.value[0])) {
                          values.push(option.value[0])
                        }
                      } else if (delimiter !== 'custom') {
                        // 添加自定义分隔符
                        values.push(delimiter)
                      }
                    })

                    return values
                  }

                  // 处理选择变化
                  const handleSelectChange = (selectedValues: string[]) => {
                    const newDelimiters: string[] = []

                    selectedValues.forEach(value => {
                      // 查找对应的预设选项
                      const option = delimiterOptions.find(opt => opt.value[0] === value)
                      if (option) {
                        newDelimiters.push(...option.value)
                      } else {
                        // 添加自定义分隔符
                        newDelimiters.push(value)
                      }
                    })

                    // 去重并更新
                    delimiterField.onChange([...new Set(newDelimiters)])
                  }

                  // 添加自定义分隔符
                  const addCustomDelimiter = (newDelimiter: string) => {
                    if (!newDelimiter.trim()) return

                    const currentDelimiters = Array.isArray(delimiterField.value) ? delimiterField.value : []
                    const updatedDelimiters = [...new Set([...currentDelimiters, newDelimiter.trim()])]
                    delimiterField.onChange(updatedDelimiters)
                  }

                  // 构建选项列表（预设选项 + 自定义分隔符）
                  const optionList = [
                    ...delimiterOptions.map(option => ({
                      label: option.label,
                      value: option.value[0],
                    })),
                    ...customDelimiters.map(custom => ({
                      label: custom,
                      value: custom,
                    })),
                  ]

                  // 处理添加自定义分隔符
                  const handleAddCustom = () => {
                    if (customInputValue.trim()) {
                      addCustomDelimiter(customInputValue.trim())
                      setCustomInputValue('')
                      setShowCustomInput(false)
                    }
                  }

                  // 处理回车键
                  const handleKeyPress = (e: any) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddCustom()
                    }
                  }

                  // 自动聚焦输入框
                  useEffect(() => {
                    if (showCustomInput && inputRef.current) {
                      setTimeout(() => {
                        inputRef.current?.focus()
                      }, 100)
                    }
                  }, [showCustomInput])

                  // 自定义底部插槽
                  const innerSlotNode = showCustomInput ? (
                    <div
                      style={{
                        padding: '8px 12px',
                        borderTop: '1px solid var(--semi-color-border)',
                        backgroundColor: 'var(--semi-color-fill-0)',
                      }}
                    >
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <Input
                          ref={inputRef}
                          size="small"
                          value={customInputValue}
                          onChange={setCustomInputValue}
                          onKeyPress={handleKeyPress}
                          placeholder={t('workflowCanvas.textEditor.enterDelimiterToAdd')}
                          style={{ flex: 1, fontSize: '12px' }}
                        />
                        <Button size="small" type="primary" onClick={handleAddCustom} style={{ fontSize: '12px', padding: '0 12px' }}>
                          {t('workflowCanvas.textEditor.add')}
                        </Button>
                        <Button
                          size="small"
                          onClick={() => {
                            setShowCustomInput(false)
                            setCustomInputValue('')
                          }}
                          style={{ fontSize: '12px', padding: '0 12px' }}
                        >
                          {t('workflowCanvas.splittingSelector.cancel')}
                        </Button>
                      </div>

                      {customDelimiters.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          <div style={{ fontSize: '12px', marginBottom: '4px', color: 'var(--semi-color-text-2)' }}>{t('workflowCanvas.splittingSelector.added')}:</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {customDelimiters.map((custom, index) => (
                              <span
                                key={index}
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  padding: '2px 6px',
                                  backgroundColor: 'var(--semi-color-fill-1)',
                                  border: '1px solid var(--semi-color-border)',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  color: 'var(--semi-color-text-2)',
                                }}
                              >
                                {custom}
                                <Button
                                  size="small"
                                  theme="borderless"
                                  style={{
                                    padding: '0',
                                    height: '14px',
                                    minWidth: '14px',
                                    fontSize: '10px',
                                    lineHeight: '1',
                                  }}
                                  onClick={() => {
                                    const currentDelimiters = Array.isArray(delimiterField.value) ? delimiterField.value : []
                                    const updatedDelimiters = currentDelimiters.filter(d => d !== custom)
                                    delimiterField.onChange(updatedDelimiters)
                                  }}
                                >
                                  ×
                                </Button>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="gedit-m-form-select-custom-option" onClick={() => setShowCustomInput(true)}>
                      {t('workflowCanvas.textEditor.addCustomDelimiter')}
                    </div>
                  )

                  return (
                    <FormSelect
                      multiple
                      value={getSelectValues()}
                      onChange={(value: string | string[]) => handleSelectChange(Array.isArray(value) ? value : [value])}
                      options={optionList}
                      placeholder={t('workflowCanvas.textEditor.selectDelimiter')}
                      innerBottomSlot={innerSlotNode}
                    />
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
