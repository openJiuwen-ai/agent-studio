/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useLayoutEffect } from 'react'
import { Field, WorkflowNodePortsData } from '@flowgram.ai/free-layout-editor'
import { Select as SemiSelect } from '@douyinfe/semi-ui'
import { useTranslation } from '../../../i18n'

import { JsonCodeEditor } from '../../../form-materials'
import { FormItem, FormDisplay } from '../../../form-components'
import { useIsSidebar, useNodeRenderContext } from '../../../hooks'
import {
  CompactSelect,
  CompactInput,
  ErrorHandlerContainer,
  DescriptionRow,
  ConfigurationRow,
  FlexItem,
  MarginLeftItem,
  SmallText,
  ReturnContentContainer,
  ReturnContentLabel,
  CodeEditorContainer,
  CodeEditorText,
} from './styles'

export function ErrorHandler() {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const { node } = useNodeRenderContext()

  const retryOptions = [
    { label: t('workflowCanvas.errorHandler.noRetry'), value: 0 },
    { label: t('workflowCanvas.errorHandler.retry1'), value: 1 },
    { label: t('workflowCanvas.errorHandler.retry2'), value: 2 },
    { label: t('workflowCanvas.errorHandler.retry3'), value: 3 },
  ]

  const errorHandlingOptions = [
    { label: t('workflowCanvas.errorHandler.breakWorkflow'), value: 'break' },
    { label: t('workflowCanvas.errorHandler.returnContent'), value: 'return_content' },
    { label: t('workflowCanvas.errorHandler.executeExceptionStep'), value: 'execute_exception_step' },
  ]

  useLayoutEffect(() => {
    window.requestAnimationFrame(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    })
  }, [node])

  // 监听 processType 变化的组件
  const ProcessTypeField = ({ field }) => {
    const processType = field.value

    return (
      <>
        <CompactSelect
          value={processType || 'break'}
          onChange={value => field.onChange(value as string)}
          style={{
            width: '100%',
          }}
          size="small"
        >
          {errorHandlingOptions.map(option => (
            <SemiSelect.Option key={option.value} value={option.value}>
              {option.label}
            </SemiSelect.Option>
          ))}
        </CompactSelect>
      </>
    )
  }

  // 端口现在通过 updateAllPorts 方法管理，不需要在DOM中渲染端口标记
  return (
    <>
      <div className="absolute -right-0 top-1/2" data-port-id={0} data-port-type="output" />

      {/* 只在侧边栏模式下显示配置表单 */}
      {isSidebar && (
        <FormItem name={t('workflowCanvas.errorHandler.exceptionHandling')} vertical defaultCollapsed={false}>
          <ErrorHandlerContainer>
            {/* 描述行 */}
            <DescriptionRow>
              <FlexItem>
                <SmallText>{t('workflowCanvas.errorHandler.timeout')}</SmallText>
              </FlexItem>
              <FlexItem>
                <SmallText>{t('workflowCanvas.errorHandler.retryTimes')}</SmallText>
              </FlexItem>
              <FlexItem>
                <SmallText>{t('workflowCanvas.errorHandler.processType')}</SmallText>
              </FlexItem>
            </DescriptionRow>

            {/* 配置行 */}
            <ConfigurationRow>
              {/* 超时时间 */}
              <FlexItem>
                <Field<number> name="exceptionConfig.timeoutSeconds">
                  {({ field }) => (
                    <CompactInput
                      value={field.value}
                      onChange={(value: string) => {
                        if (value === '') {
                          field.onChange(0)
                          return
                        }
                        const numValue = parseInt(value)
                        if (!isNaN(numValue) && numValue >= 1 && numValue <= 300) {
                          field.onChange(numValue)
                        }
                      }}
                      style={{
                        width: '100%',
                      }}
                      size="small"
                      suffix="s"
                    />
                  )}
                </Field>
              </FlexItem>

              {/* 重试次数 */}
              <MarginLeftItem>
                <Field<number> name="exceptionConfig.retryTimes">
                  {({ field }) => (
                    <CompactSelect
                      value={field.value?.toString() || '3'}
                      onChange={(value: string) => field.onChange(parseInt(value))}
                      style={{
                        width: '100%',
                      }}
                      size="small"
                    >
                      {retryOptions.map(option => (
                        <SemiSelect.Option key={option.value} value={option.value.toString()}>
                          {option.label}
                        </SemiSelect.Option>
                      ))}
                    </CompactSelect>
                  )}
                </Field>
              </MarginLeftItem>

              {/* 异常处理方式 */}
              <MarginLeftItem>
                <Field<string> name="exceptionConfig.processType">{({ field }) => <ProcessTypeField field={field} />}</Field>
              </MarginLeftItem>
            </ConfigurationRow>

            {/* 返回内容配置 - 仅在选择"返回设定内容"时显示 */}
            <Field<string> name="exceptionConfig.processType">
              {({ field }) => {
                const showReturnContent = field.value === 'return_content'
                return showReturnContent ? (
                  <ReturnContentContainer>
                    <ReturnContentLabel>{t('workflowCanvas.errorHandler.returnContentConfig')}</ReturnContentLabel>
                    <Field<Record<string, any>> name="exceptionConfig.returnContent">
                      {({ field: returnContentField }) => (
                        <Field<Record<string, any> | undefined> name="outputs">
                          {({ field: outputsField }) => {
                            const outputsValues = outputsField.value || {}
                            return (
                              <CodeEditorContainer>
                                <CodeEditorText>
                                  <JsonCodeEditor
                                    value={returnContentField.value || {}}
                                    onChange={parsedValue => {
                                      returnContentField.onChange(parsedValue)
                                    }}
                                    minHeight={100}
                                    mini
                                  />
                                </CodeEditorText>
                              </CodeEditorContainer>
                            )
                          }}
                        </Field>
                      )}
                    </Field>
                  </ReturnContentContainer>
                ) : (
                  <div />
                )
              }}
            </Field>
          </ErrorHandlerContainer>
        </FormItem>
      )}

      {/* 非侧边栏模式下显示异常处理信息 */}
      {!isSidebar && (
        <Field<string> name="exceptionConfig.processType">
          {({ field }) => {
            const processType = field.value
            return processType === 'execute_exception_step' ? (
              <FormDisplay label={t('workflowCanvas.errorHandler.exceptionHandling')} content={errorHandlingOptions.find(option => option.value === processType)?.label || t('workflowCanvas.errorHandler.executeExceptionStep')} />
            ) : (
              <></>
            )
          }}
        </Field>
      )}

      {
        <Field<string> name="exceptionConfig.processType">
          {({ field }) => {
            const processType = field.value
            return processType === 'execute_exception_step' ? <div className="absolute -right-0 top-2/3" data-port-id={1} data-port-type="output" /> : <></>
          }}
        </Field>
      }
    </>
  )
}
