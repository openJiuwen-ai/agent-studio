/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FC, useState, useEffect, useMemo } from 'react'
import { Button } from '@douyinfe/semi-ui'
import { usePanelManager } from '@flowgram.ai/panel-manager-plugin'
import { X, MessageSquare, Loader2 } from 'lucide-react'

import { NodeInputPanel } from '../node-input-panel'
import { useNodeInputMeta } from '../hooks/use-node-input-meta'
import { useService } from '@flowgram.ai/free-layout-core'
import { WorkflowDocument } from '@flowgram.ai/free-layout-editor'
import { useExecutionContext } from '../../../context'
import { findNodeRecursively } from '../../../utils'
import { useTestExecution } from '../shared/use-test-execution'
import { useTranslation } from '../../../i18n'

import styles from './index.module.less'

const lastNodeTestValuesByNodeId = new Map<string, Record<string, unknown>>()

export const clearLastNodeTestValues = () => {
  lastNodeTestValuesByNodeId.clear()
}

export interface NodeTestData {
  id: string
  inputs?: Record<string, any>
  space_id?: string
  version?: string
  loop_id?: string
  data?: {
    outputs?: {
      type: string
      properties: Record<string, any>
      required?: string[]
    }
  }
  [key: string]: any
}

export interface TestDebugPanelProps {
  nodeData: NodeTestData
  workflowId?: string
  spaceId?: string
}

export const TestDebugPanel: FC<TestDebugPanelProps> = ({ nodeData, workflowId, spaceId }) => {
  const { t } = useTranslation()
  const panelManager = usePanelManager()
  const executionContext = useExecutionContext()
  const document = useService(WorkflowDocument)

  const nodeId = nodeData?.id || ''
  const finalSpaceId = nodeData?.space_id || spaceId || ''
  const finalVersion = nodeData?.version || ''

  // Extract output_format from node data for Markdown rendering
  const outputFormat = nodeData?.data?.output_format

  const [inputJSONMode, setInputJSONMode] = useState(() => {
    const savedMode = localStorage.getItem('testdebug-input-json-mode')
    return savedMode ? JSON.parse(savedMode) : false
  })

  const handleSetInputJSONMode = (checked: boolean) => {
    setInputJSONMode(checked)
    localStorage.setItem('testdebug-input-json-mode', JSON.stringify(checked))
  }

  const inputFormMeta = useNodeInputMeta(nodeId)

  const { isExecuting, errors, result, execute, cancel, resetErrors } = useTestExecution({
    workflowId: workflowId || '',
    spaceId: finalSpaceId,
    nodeId,
    conversationId: '',
    version: finalVersion,
    loopId: nodeData?.loop_id,
  })

  const [values, setValues] = useState<Record<string, unknown>>({})

  useEffect(() => {
    if (!nodeId) return
    lastNodeTestValuesByNodeId.set(nodeId, values)
  }, [nodeId, values])

  const nodeIcon = useMemo(() => {
    if (!nodeId) return null

    const node = findNodeRecursively(document.root.blocks, nodeId)
    if (!node) return null

    const registry = node.getNodeRegistry()
    const icon = registry?.info?.icon
    if (!icon) return <MessageSquare size={16} className={styles['interruption-icon']} />

    if (typeof icon === 'string') {
      return <img src={icon} alt="node icon" width={16} height={16} />
    } else {
      return <span>{icon}</span>
    }
  }, [nodeId, document.root.blocks])

  useEffect(() => {
    if (nodeId && lastNodeTestValuesByNodeId.has(nodeId)) {
      const lastValues = lastNodeTestValuesByNodeId.get(nodeId)
      setValues(lastValues || {})
    } else {
      const preservedValues: Record<string, unknown> = {}
      inputFormMeta.forEach(meta => {
        if (meta.defaultValue !== undefined) {
          preservedValues[meta.name] = meta.defaultValue
        }
      })
      setValues(preservedValues)
    }
    resetErrors()
  }, [nodeId])

  const handleTestRun = async (currentValues: Record<string, unknown>) => {
    const valuesWithDefaults: Record<string, unknown> = {}
    inputFormMeta.forEach(meta => {
      if (meta.defaultValue !== undefined) {
        valuesWithDefaults[meta.name] = currentValues[meta.name] ?? meta.defaultValue
      } else if (currentValues[meta.name] !== undefined) {
        valuesWithDefaults[meta.name] = currentValues[meta.name]
      }
    })
    await execute(valuesWithDefaults)
  }

  const handleCancel = () => {
    cancel()
  }

  const handleClose = () => {
    if (isExecuting) {
      handleCancel()
    }
    if (nodeId) {
      lastNodeTestValuesByNodeId.set(nodeId, values)
    }
    panelManager.close(testDebugPanelFactory.key)
  }

  const renderRunning = (
    <div className={styles['testrun-panel-running']}>
      <div className={styles['running-header']}>
        <Loader2 className="animate-spin" size={20} />
        <div className={styles.text}>运行中...</div>
      </div>
    </div>
  )

  const renderForm = (
    <div className={styles['testrun-panel-form']}>
      <NodeInputPanel
        nodeIcon={nodeIcon}
        nodeIconFallback={<MessageSquare size={16} className={styles['interruption-icon']} />}
        values={values}
        setValues={setValues}
        inputFormMeta={inputFormMeta}
        inputJSONMode={inputJSONMode}
        setInputJSONMode={handleSetInputJSONMode}
        isInterruptionMode={false} // 修改为非中断模式，确保能显示输出结果
        interruptionMessage={t('workflowCanvas.testDebugPanel.completeInputToContinue')}
        result={
          result
            ? {
                inputs: result.inputs,
                outputs: result.output,
              }
            : undefined
        }
        outputFormat={outputFormat}
        errors={errors}
        workflowId={workflowId}
        spaceId={finalSpaceId}
      />
    </div>
  )

  const renderButton = isExecuting ? (
    <Button onClick={handleCancel} className={`${styles.button} ${styles.running}`}>
      {t('workflowCanvas.testDebugPanel.cancel')}
    </Button>
  ) : (
    <Button onClick={() => handleTestRun(values)} className={`${styles.button} ${styles.save}`}>
      {t('workflowCanvas.testDebugPanel.run')}
    </Button>
  )

  const renderHeader = (
    <div className={styles['testrun-panel-header']}>
      <div className={styles['testrun-panel-title']}>{t('workflowCanvas.testDebugPanel.testRun')}</div>
      <Button className={styles['testrun-panel-title']} type="tertiary" size="small" theme="borderless" onClick={handleClose}>
        <X size={16} className={styles['text-gray-600']} />
      </Button>
    </div>
  )

  return (
    <div className={styles['testrun-panel-container']}>
      {renderHeader}
      <div className={styles['testrun-panel-content']}>{isExecuting ? renderRunning : renderForm}</div>
      <div className={styles['testrun-panel-footer']}>{renderButton}</div>
    </div>
  )
}

export const testDebugPanelFactory: PanelFactory<TestDebugPanelProps> = {
  key: 'test-debug-panel',
  defaultSize: 400,
  render: props => <TestDebugPanel {...props} />,
}
