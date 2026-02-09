/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FC, useState, useEffect, useMemo, useCallback } from 'react'

import classnames from 'classnames'
import { type PanelFactory, usePanelManager } from '@flowgram.ai/panel-manager-plugin'
import { Button } from '@douyinfe/semi-ui'
import { X, Loader2, MessageSquare } from 'lucide-react'

import { NodeInputPanel } from '../node-input-panel'
import { testRunRuntimeService } from '../runtime/testrun-runtime-service'
import { StreamResponse } from '../runtime/types'
import { useExecutionContext } from '../../../context'
import { useFormMeta } from '../hooks/use-form-meta'
import { useService } from '@flowgram.ai/free-layout-core'
import { WorkflowDocument } from '@flowgram.ai/free-layout-editor'
import { findNodeRecursively } from '../../../utils'
import { parseInteractionMsgToFormMeta } from '../utils/parseInteractionMsg'
import { useStreamMessages, useInputInterruption, useFormValidation } from '../shared'
import { useTranslation } from '../../../i18n'

import styles from './index.module.less'

let lastTestRunValues: Record<string, unknown> | undefined

export const clearLastTestRunValues = () => {
  lastTestRunValues = undefined
}

interface TestRunSidePanelProps {
  workflowId?: string
  spaceId?: string
  version?: string
}

export const TestRunSidePanel: FC<TestRunSidePanelProps> = ({ workflowId, spaceId, version }) => {
  const { t } = useTranslation()
  const panelManager = usePanelManager()
  const executionContext = useExecutionContext()
  const document = useService(WorkflowDocument)

  const [values, setValues] = useState<Record<string, unknown>>(() => lastTestRunValues || {})
  const [errors, setErrors] = useState<string[]>()
  const [result, setResult] = useState<
    | {
        inputs: Record<string, any>
        outputs: Record<string, any>
      }
    | undefined
  >()
  const [isStreamExecuting, setIsStreamExecuting] = useState(false)

  const { messages, handleStreamEvent: handleStreamMessageEvent, clearMessages, setRef } = useStreamMessages()
  const { interruption, inputValues, setInputValues, handleInputRequired, resume: resumeInput, clear: clearInterruption } = useInputInterruption()
  const { validate: validateForm } = useFormValidation()

  const formMeta = useFormMeta()

  const [inputJSONMode, _setInputJSONMode] = useState(() => {
    const savedMode = localStorage.getItem('testrun-input-json-mode')
    return savedMode ? JSON.parse(savedMode) : false
  })

  const setInputJSONMode = (checked: boolean) => {
    _setInputJSONMode(checked)
    localStorage.setItem('testrun-input-json-mode', JSON.stringify(checked))
  }

  useEffect(() => {
    testRunRuntimeService.clearAllNodeStatuses()

    const resultDisposer = testRunRuntimeService.onResultChanged(event => {
      if (event.result) {
        setResult(event.result)
        setIsStreamExecuting(false)
        setErrors(undefined)
        clearInterruption()
      } else if (event.errors) {
        const isUserCanceled = event.errors.length > 0 && event.errors[0] === 'canceled by user'

        if (isUserCanceled) {
          setErrors(event.errors)
          setIsStreamExecuting(false)
          setResult(undefined)
        } else {
          setErrors(event.errors)
          setIsStreamExecuting(false)
          setResult(undefined)
          testRunRuntimeService.clearAllNodeStatuses()
        }
      }
    })

    return () => {
      resultDisposer?.dispose()
    }
  }, [clearInterruption])

  const interruptionNodeIcon = useMemo(() => {
    const nodeId = interruption?.nodeId
    if (!nodeId) return null

    const node = findNodeRecursively(document.root.blocks, nodeId)
    if (!node) return null

    const registry = node.getNodeRegistry()
    const info = typeof registry?.info === 'function' ? registry.info() : registry?.info
    const icon = info?.icon
    if (!icon) return <MessageSquare size={16} className={styles['interruption-icon']} />

    if (typeof icon === 'string') {
      return <img src={icon} alt="node icon" width={16} height={16} className={styles['interruption-icon']} />
    } else {
      return <span className={styles['interruption-icon']}>{icon}</span>
    }
  }, [interruption?.nodeId, document.root.blocks])

  const interruptionFormMeta = useMemo(() => {
    if (!interruption) return undefined

    // 从 workflow document 中提取 input 节点的默认值
    const inputDefaults: Record<string, unknown> = {}
    try {
      const allNodes = document.getAllNodes()
      for (const node of allNodes) {
        try {
          // 安全地获取节点数据
          let nodeData: any = null
          if (typeof node.getData === 'function') {
            nodeData = node.getData()
          } else if (node.data) {
            nodeData = node.data
          }

          if (!nodeData) continue

          // 检查是否是 input 节点
          const nodeType = nodeData.type ?? nodeData.componentType
          const nodeId = node.id ?? nodeData.id

          if (nodeType === 8 || nodeType === '8' || nodeId?.startsWith('input_')) {
            const outputs = nodeData?.outputs ?? nodeData?.data?.outputs
            if (outputs && outputs.properties) {
              for (const [fieldName, fieldDef] of Object.entries<any>(outputs.properties)) {
                if (fieldDef?.default !== undefined && fieldDef?.default !== '') {
                  inputDefaults[fieldName] = fieldDef.default
                }
              }
            }
          }
        } catch (nodeError) {
          // 忽略单个节点的错误，继续处理其他节点
          continue
        }
      }
    } catch (error) {
      // 提取失败时使用空对象
    }

    return parseInteractionMsgToFormMeta(interruption.message, inputDefaults)
  }, [interruption?.message, document])

  const getNodeDisplayName = useCallback(
    (nodeId: string): string => {
      const streamData = messages.get(nodeId)
      if (streamData?.nodeName) return streamData.nodeName

      const node = findNodeRecursively(document.root.blocks, nodeId)
      if (!node) return nodeId

      const registry = node.getNodeRegistry()
      const info = typeof registry?.info === 'function' ? registry.info() : registry?.info
      return info?.title || info?.name || nodeId
    },
    [document.root.blocks, messages],
  )

  const handleStreamEvent = useCallback(
    (event: StreamResponse) => {
      handleStreamMessageEvent(event)

      switch (event.type) {
        case 'input_required':
          handleInputRequired(event.data)
          setIsStreamExecuting(false)
          break
        case 'completed':
          setIsStreamExecuting(false)
          setResult({
            inputs: event.data.inputs,
            outputs: event.data.outputs,
          })
          break
        case 'error':
          setIsStreamExecuting(false)
          {
            const errorMessage = event.data.message || 'Execution error'
            const isUserCanceled = event.data.isUserCanceled || errorMessage === 'canceled by user'
            const nodeId = event.data.nodeId

            if (!isUserCanceled) {
              setErrors([errorMessage])

              const isWorkflowLevelError = nodeId && nodeId.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)

              if (isWorkflowLevelError) {
                const runningNodes = testRunRuntimeService.getRunningNodes()

                if (runningNodes.length > 0) {
                  const lastRunningNode = runningNodes[runningNodes.length - 1]
                  testRunRuntimeService.setNodeFailedStatus(lastRunningNode, errorMessage)
                }
              } else if (nodeId) {
                testRunRuntimeService.setNodeFailedStatus(nodeId, errorMessage)
              }
            }
          }
          break
      }
    },
    [handleStreamMessageEvent, handleInputRequired],
  )

  const onTestRun = async () => {
    if (isStreamExecuting) {
      testRunRuntimeService.stopStreamExecution()
      setIsStreamExecuting(false)
      clearMessages()
      return
    }

    if (!workflowId || !spaceId) {
      setErrors(['Missing workflowId or spaceId for execution'])
      return
    }

    const validationErrors = validateForm(values, formMeta)
    if (validationErrors) {
      setErrors(validationErrors)
      return
    }

    lastTestRunValues = values

    setResult(undefined)
    setErrors(undefined)
    clearInterruption()
    clearMessages()

    setIsStreamExecuting(true)
    executionContext.clearExecution()
    testRunRuntimeService.clearAllNodeStatuses()

    try {
      const params = {
        id: workflowId,
        version: version || '',
        space_id: spaceId,
        inputs: values,
        options: {
          statusManagement: {
            clearBeforeStart: false,
            triggerNodeStatus: true,
            triggerGlobalReset: false,
          },
          eventHandling: {
            enableNodeReport: true,
            enableProgressTracking: true,
            enableResultBroadcast: true,
          },
          mode: 'workflow' as const,
        },
      }

      await testRunRuntimeService.execute(params, handleStreamEvent)
    } catch (error) {
      setErrors([error instanceof Error ? error.message : 'Execution failed'])
      setIsStreamExecuting(false)
      testRunRuntimeService.clearAllNodeStatuses()
    }
  }

  const handleInputResume = async () => {
    const metaForValidation = interruptionFormMeta || []

    // 构建包含默认值的输入对象
    const valuesWithDefaults: Record<string, unknown> = {}
    metaForValidation.forEach(meta => {
      const userValue = inputValues[meta.name]
      // 如果用户未输入（undefined、null 或空字符串），使用默认值
      if (userValue === undefined || userValue === null || userValue === '') {
        valuesWithDefaults[meta.name] = meta.defaultValue
      } else {
        valuesWithDefaults[meta.name] = userValue
      }
    })

    const validationErrors = validateForm(valuesWithDefaults, metaForValidation)

    if (validationErrors) {
      setErrors(validationErrors)
      return
    }

    setIsStreamExecuting(true)
    setErrors(undefined)

    const success = await resumeInput(valuesWithDefaults)
    if (!success) {
      setIsStreamExecuting(false)
    }
  }

  const onClose = async () => {
    testRunRuntimeService.stopStreamExecution()
    setValues({})
    setInputValues({})
    setIsStreamExecuting(false)
    clearInterruption()
    clearMessages()
    panelManager.close(testRunPanelFactory.key)
  }

  const renderRunning = (
    <div className={styles['testrun-panel-running']}>
      <div className={styles['running-header']}>
        <Loader2 className="animate-spin" size={20} />
        <div className={styles.text}>{t('workflowCanvas.testrunPanel.running')}</div>
      </div>
      {messages.size > 0 && (
        <div className={styles['stream-messages-container']}>
          {Array.from(messages.entries()).map(([nodeId, data]) => (
            <div key={nodeId} className={styles['node-message-container']}>
              <div className={styles['node-message-header']}>{getNodeDisplayName(nodeId)}</div>
              <div ref={el => setRef(nodeId, el)} className={styles['node-message-textarea']}>
                {data.message}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderForm = (
    <div className={styles['testrun-panel-form']}>
      <NodeInputPanel
        title={interruption ? undefined : t('workflowCanvas.testrunPanel.testRunInput')}
        nodeIcon={interruption ? interruptionNodeIcon : undefined}
        nodeIconFallback={<MessageSquare size={16} className={styles['interruption-icon']} />}
        values={interruption ? inputValues : values}
        setValues={interruption ? setInputValues : setValues}
        inputFormMeta={interruptionFormMeta}
        inputJSONMode={interruption ? false : inputJSONMode}
        setInputJSONMode={interruption ? () => {} : setInputJSONMode}
        isInterruptionMode={!!interruption}
        interruptionMessage={t('workflowCanvas.testrunPanel.completeInputToContinue')}
        result={result}
        errors={errors}
        workflowId={workflowId}
        spaceId={spaceId}
      />
    </div>
  )

  const renderButton = interruption ? (
    <Button onClick={handleInputResume} className={classnames(styles.button, styles.save)}>
      {t('workflowCanvas.testrunPanel.continueRunning')}
    </Button>
  ) : (
    <Button
      onClick={onTestRun}
      className={classnames(styles.button, {
        [styles.running]: isStreamExecuting,
        [styles.default]: !isStreamExecuting,
      })}
    >
      {isStreamExecuting ? <>{t('workflowCanvas.testrunPanel.cancel')}</> : <>{t('workflowCanvas.testrunPanel.run')}</>}
    </Button>
  )

  const renderHeader = (
    <div className={styles['testrun-panel-header']}>
      <div className={styles['testrun-panel-title']}>{t('workflowCanvas.testrunPanel.testRun')}</div>
      <Button className={styles['testrun-panel-title']} type="tertiary" size="small" theme="borderless" onClick={onClose}>
        <X size={16} className={`${styles['text-gray-600']} ${styles['hover:text-red-6']}`} />
      </Button>
    </div>
  )

  return (
    <div className={styles['testrun-panel-container']}>
      {renderHeader}
      <div className={styles['testrun-panel-content']}>{isStreamExecuting ? renderRunning : renderForm}</div>
      <div className={styles['testrun-panel-footer']}>{renderButton}</div>
    </div>
  )
}

export const testRunPanelFactory: PanelFactory<TestRunSidePanelProps> = {
  key: 'test-run-panel',
  defaultSize: 400,
  render: props => <TestRunSidePanel {...props} />,
}
