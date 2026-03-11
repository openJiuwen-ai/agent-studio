/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Save, Upload, Download, FileCode2, ArrowLeft, Tag, History } from 'lucide-react'
import { Tooltip, Divider, IconButton, Toast, Typography } from '@douyinfe/semi-ui'
import { WorkflowOperationContainer, WorkflowControlSection } from './styles'
import { HistoryVersionTag } from '../../styles/styles'
import PublishDialog from '../history-panel/publish-dialog'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { t } from '../../i18n'

interface WorkflowControlProps {
  onSave: () => void
  onImport: () => void
  onExport: () => void
  onExportPy: () => void
  workflowId?: string
  spaceId?: string
  asyncSaveRef?: React.RefObject<(() => Promise<void>) | null>
  canvasData?: any
}

export const WorkflowControl = ({ onSave, onImport, onExport, onExportPy, workflowId, spaceId, asyncSaveRef, canvasData }: WorkflowControlProps) => {
  const navigate = useNavigate()
  const [showPublishDialog, setShowPublishDialog] = useState(false)
  const selectedVersion = useWorkflowStore(s => s.selectedVersion)

  // 获取工作流名称 - 改进逻辑，支持多种数据结构
  const workflowName =
    canvasData?.name ||
    canvasData?.workflow?.name ||
    canvasData?.data?.workflow?.name ||
    (workflowId ? `${t('workflowCanvas.workflow.name')}-${workflowId}` : t('workflowCanvas.workflow.unnamed'))

  // 调试日志 - 临时注释，需要时可以启用
  // React.useEffect(() => {
  //   console.log('WorkflowControl debug:')
  //   console.log('- canvasData:', canvasData)
  //   console.log('- workflowName:', workflowName)
  //   console.log('- workflowId:', workflowId)
  //   console.log('- spaceId:', spaceId)
  // }, [canvasData, workflowName, workflowId, spaceId])

  // 调试日志 - 临时禁用以避免过多日志
  // React.useEffect(() => {
  //   console.log('WorkflowControl canvasData:', canvasData)
  //   console.log('WorkflowControl workflow name:', canvasData?.name)
  //   console.log('WorkflowControl final workflowName:', workflowName)
  // }, [canvasData, workflowName])

  const handleBack = () => {
    try {
      const reset = useWorkflowStore.getState().resetStore
      reset()
    } catch {}
    navigate('/dashboard/workflows')
  }

  const handlePublishClick = () => {
    setShowPublishDialog(true)
  }

  const handleVersionHistoryClick = async () => {
    if (!workflowId || !spaceId) {
      Toast.error(t('workflowCanvas.workflow.notFound'))
      return
    }
    // 使用 store 打开右侧版本历史面板，并传递上下文
    const openHistoryPanel = useWorkflowStore.getState().openHistoryPanel
    openHistoryPanel({ workflowId, spaceId })
  }

  return (
    <>
      <WorkflowOperationContainer>
        <WorkflowControlSection>
          {/* 工作流名称显示 */}
          <div
            className="workflow-name-label"
            style={{
              display: 'flex',
              alignItems: 'center',
              marginRight: '12px',
              padding: '4px 12px',
              backgroundColor: 'var(--workflow-bg-surface)',
              borderRadius: '6px',
              border: '1px solid var(--workflow-border-toolbar)',
              height: '32px',
            }}
          >
            <Typography.Text
              type="secondary"
              style={{
                fontWeight: 'bold',
                fontSize: '13px',
                maxWidth: '200px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                lineHeight: '24px',
                color: 'var(--workflow-text-secondary)'
              }}
              title={workflowName || t('workflowCanvas.workflow.nameLabel')}
            >
              {workflowName || t('workflowCanvas.workflow.unnamed')}
            </Typography.Text>
          </div>

          {/* 新增的发布和版本历史按钮 */}
          <Tooltip content={t('workflowCanvas.workflow.publish')}>
            <IconButton 
              type="tertiary" 
              theme="borderless" 
              icon={<Tag size={16} />} 
              onClick={handlePublishClick} 
              disabled={!workflowId || !spaceId}
              style={{ color: 'var(--workflow-text-secondary)' }}
            />
          </Tooltip>

          <Tooltip content={t('workflowCanvas.workflow.versionHistory')}>
            <IconButton
              type="tertiary"
              theme="borderless"
              icon={<History size={16} />}
              onClick={handleVersionHistoryClick}
              disabled={!workflowId || !spaceId}
              style={{ color: 'var(--workflow-text-secondary)' }}
            />
          </Tooltip>

          {/* 当前展示版本：仅当为历史版本时显示 */}
          {selectedVersion && selectedVersion !== 'draft' && (
            <HistoryVersionTag>
              {t('workflowCanvas.workflow.historyVersion')} {selectedVersion}
            </HistoryVersionTag>
          )}

          <Divider layout="vertical" style={{ height: '20px' }} margin={3} />

          {/* 原有的保存、导入、导出按钮 */}
          <Tooltip content={t('workflowCanvas.workflow.save')}>
            <IconButton 
              type="tertiary" 
              theme="borderless" 
              icon={<Save size={16} />} 
              onClick={onSave}
              style={{ color: 'var(--workflow-text-secondary)' }}
            />
          </Tooltip>

          <Tooltip content={t('workflowCanvas.workflow.import')}>
            <IconButton 
              type="tertiary" 
              theme="borderless" 
              icon={<Upload size={16} />} 
              onClick={onImport}
              style={{ color: 'var(--workflow-text-secondary)' }}
            />
          </Tooltip>

          <Tooltip content={t('workflowCanvas.workflow.export')}>
            <IconButton 
              type="tertiary" 
              theme="borderless" 
              icon={<Download size={16} />} 
              onClick={onExport}
              style={{ color: 'var(--workflow-text-secondary)' }}
            />
          </Tooltip>

          <Tooltip content={t('workflowCanvas.workflow.exportPy')}>
            <IconButton
              type="tertiary"
              theme="borderless"
              icon={<FileCode2 size={16} />}
              onClick={onExportPy}
              disabled={!workflowId || !spaceId}
            />
          </Tooltip>

          <Divider layout="vertical" style={{ height: '16px' }} margin={3} />

          <Tooltip content={t('workflowCanvas.workflow.backToList')}>
            <IconButton type="danger" theme="borderless" icon={<ArrowLeft size={16} />} onClick={handleBack} />
          </Tooltip>
        </WorkflowControlSection>
      </WorkflowOperationContainer>

      {/* 发布对话框 */}
      {showPublishDialog && (
        <PublishDialog
          open={showPublishDialog}
          workflowId={workflowId}
          spaceId={spaceId}
          onSave={onSave}
          asyncSaveRef={asyncSaveRef}
          onClose={() => setShowPublishDialog(false)}
          defaultVersion="v0.0.1"
        />
      )}
    </>
  )
}
