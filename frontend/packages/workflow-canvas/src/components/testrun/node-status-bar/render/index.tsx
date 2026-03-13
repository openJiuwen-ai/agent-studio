/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FC, useMemo, useState } from 'react'

import classnames from 'classnames'
import { NodeReport, NodeExecutionStatus, normalizeNodeStatus } from '../../runtime/types'
import { Tag, Button, Select } from '@douyinfe/semi-ui'
import { CheckCircle, Loader2, XCircle, AlertCircle } from 'lucide-react'
import { useTranslation } from '../../../../i18n'

import { NodeStatusHeader } from '../header'
import { NodeStatusGroup } from '../group'

import styles from './index.module.less'

interface NodeStatusRenderProps {
  report: NodeReport
}

const msToSeconds = (ms: number): string => (ms / 1000).toFixed(2) + 's'
const displayCount = 6

export const NodeStatusRender: FC<NodeStatusRenderProps> = ({ report }) => {
  const { t } = useTranslation()
  const { status: nodeStatus } = report
  const [currentSnapshotIndex, setCurrentSnapshotIndex] = useState(0)

  const snapshots = report.snapshots || []
  const currentSnapshot = snapshots[currentSnapshotIndex] || snapshots[0]

  // 使用统一的状态转换
  const normalizedStatus = normalizeNodeStatus(nodeStatus)

  // 简化的状态判断
  const isNodeRunning = normalizedStatus === NodeExecutionStatus.RUNNING
  const isNodeFailed = normalizedStatus === NodeExecutionStatus.FAILED
  const isNodeSucceed = normalizedStatus === NodeExecutionStatus.SUCCESS
  const isNodeCanceled = normalizedStatus === NodeExecutionStatus.CANCELED

  const tagColor = useMemo(() => {
    if (isNodeSucceed) {
      return styles.nodeStatusSucceed
    }
    if (isNodeFailed) {
      return styles.nodeStatusFailed
    }
    if (isNodeRunning) {
      return styles.nodeStatusProcessing
    }
    if (isNodeCanceled) {
      return styles.nodeStatusCanceled
    }
  }, [isNodeSucceed, isNodeFailed, isNodeRunning, isNodeCanceled])

  const renderIcon = () => {
    if (isNodeRunning) {
      return <Loader2 className={classnames(styles.icon, styles.processing, styles.spin)} />
    }
    if (isNodeSucceed) {
      return <CheckCircle className={classnames(styles.icon, styles.success)} />
    }
    if (isNodeFailed) {
      return <AlertCircle className={classnames(styles.icon, styles.failed)} />
    }
    if (isNodeCanceled) {
      return <XCircle className={classnames(styles.icon, styles.canceled)} />
    }
    // 默认情况下显示运行状态
    return <Loader2 className={classnames(styles.icon, styles.processing, styles.spin)} />
  }
  const renderDesc = () => {
    const getDesc = () => {
      if (isNodeRunning) {
        return t('workflowCanvas.nodeStatusBar.running')
      } else if (isNodeSucceed) {
        return t('workflowCanvas.nodeStatusBar.success')
      } else if (isNodeFailed) {
        return t('workflowCanvas.nodeStatusBar.failed')
      } else if (isNodeCanceled) {
        return t('workflowCanvas.nodeStatusBar.cancelled')
      }
    }

    const desc = getDesc()

    return desc ? <p className={styles.desc}>{desc}</p> : null
  }
  const renderCost = () => {
    // 正在执行中的节点显示 "0.00s"
    if (isNodeRunning) {
      return (
        <Tag size="small" className={tagColor}>
          0.00s
        </Tag>
      )
    }

    return (
      <Tag size="small" className={tagColor}>
        {msToSeconds(report.timeCost || 100)}
      </Tag>
    )
  }

  const renderSnapshotNavigation = () => {
    if (snapshots.length <= 1) {
      return null
    }

    const count = <p className={styles.count}>{t('workflowCanvas.nodeStatusBar.total')}: {snapshots.length}</p>

    if (snapshots.length <= displayCount) {
      return (
        <>
          {count}
          <div className={styles.snapshotNavigation}>
            {snapshots.map((_, index) => (
              <Button
                key={index}
                size="small"
                type={currentSnapshotIndex === index ? 'primary' : 'tertiary'}
                onClick={() => setCurrentSnapshotIndex(index)}
                className={classnames(styles.snapshotButton, {
                  [styles.active]: currentSnapshotIndex === index,
                  [styles.inactive]: currentSnapshotIndex !== index,
                })}
              >
                {index + 1}
              </Button>
            ))}
          </div>
        </>
      )
    }

    // 超过5个时，前5个显示为按钮，剩余的放在下拉选择中
    return (
      <>
        {count}
        <div className={styles.snapshotNavigation}>
          {snapshots.slice(0, displayCount).map((_, index) => (
            <Button
              key={index}
              size="small"
              type="tertiary"
              onClick={() => setCurrentSnapshotIndex(index)}
              className={classnames(styles.snapshotButton, {
                [styles.active]: currentSnapshotIndex === index,
                [styles.inactive]: currentSnapshotIndex !== index,
              })}
            >
              {index + 1}
            </Button>
          ))}
          <Select
            value={currentSnapshotIndex >= displayCount ? currentSnapshotIndex : undefined}
            onChange={value => setCurrentSnapshotIndex(value as number)}
            className={classnames(styles.snapshotSelect, {
              [styles.active]: currentSnapshotIndex >= displayCount,
              [styles.inactive]: currentSnapshotIndex < displayCount,
            })}
            size="small"
            placeholder="Select"
          >
            {snapshots.slice(displayCount).map((_, index) => {
              const actualIndex = index + displayCount
              return (
                <Select.Option key={actualIndex} value={actualIndex}>
                  {actualIndex + 1}
                </Select.Option>
              )
            })}
          </Select>
        </div>
      </>
    )
  }

  if (!report) {
    return null
  }

  return (
    <NodeStatusHeader
      header={
        <>
          {renderIcon()}
          {renderDesc()}
          {renderCost()}
        </>
      }
    >
      <div className={styles.container}>
        {renderSnapshotNavigation()}
        <NodeStatusGroup title={t('workflowCanvas.nodeStatusBar.inputParams')} data={currentSnapshot?.inputs} />
        <NodeStatusGroup title={t('workflowCanvas.nodeStatusBar.outputResult')} data={currentSnapshot?.outputs} />
        {isNodeFailed && <NodeStatusGroup title={t('workflowCanvas.nodeStatusBar.errorMessage')} data={currentSnapshot?.error} optional />}
        <NodeStatusGroup title={t('workflowCanvas.nodeStatusBar.branchInfo')} data={currentSnapshot?.branch} optional />
        <NodeStatusGroup title={t('workflowCanvas.nodeStatusBar.otherData')} data={currentSnapshot?.data} optional />
      </div>
    </NodeStatusHeader>
  )
}
