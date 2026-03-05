/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'
import { Toast } from '@douyinfe/semi-ui'
import { WorkflowService } from '@test-agentstudio/api-client'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { useTranslation } from '../../i18n'

export interface PublishModalProps {
  open: boolean
  workflowId?: string
  spaceId?: string
  onSave: () => void
  asyncSaveRef?: React.RefObject<(() => Promise<void>) | null>
  onClose: () => void
  defaultVersion?: string
}

// 版本号递增工具（vX.Y.Z -> vX.Y.(Z+1)）
const VERSION_PATTERN = /^v(\d+)\.(\d+)\.(\d+)$/
function computeNextVersion(latest?: string): string {
  const match = latest?.match(VERSION_PATTERN)
  if (!match) return 'v0.0.1'
  const major = Number(match[1])
  const minor = Number(match[2])
  const patch = Number(match[3]) + 1
  return `v${major}.${minor}.${patch}`
}

// 拉取版本列表并设置默认版本（命名函数，避免闭包/IIFE）
async function refreshDefaultVersion(workflowId: string, spaceId: string, defaultVersion: string, setVersion: (v: string) => void, t: (key: string) => string): Promise<void> {
  try {
    const res = await WorkflowService.getWorkflowVersionList({ workflow_id: workflowId, space_id: spaceId })
    const versions = res?.data?.versions || []
    const latest = versions.slice().sort((a, b) => (b.create_time || 0) - (a.create_time || 0))[0]?.workflow_version
    const next = computeNextVersion(latest)
    setVersion(next)
  } catch (err) {
    console.error(t('workflowCanvas.publishDialog.fetchVersionListFailed'), err)
    setVersion(defaultVersion)
  }
}

const PublishDialog: React.FC<PublishModalProps> = ({ open, workflowId, spaceId, onSave, asyncSaveRef, onClose, defaultVersion = 'v1.0.0' }) => {
  const { t } = useTranslation()
  const [version, setVersion] = React.useState<string>('')
  const [description, setDescription] = React.useState<string>('')
  const [loading, setLoading] = React.useState<boolean>(false)

  // 仅用于控制错误展示时机，不用于控制提交有效性
  const [versionTouched, setVersionTouched] = React.useState<boolean>(false)
  const [descriptionTouched, setDescriptionTouched] = React.useState<boolean>(false)
  const [hasSubmitted, setHasSubmitted] = React.useState<boolean>(false)

  // 校验函数：版本号与描述
  const validateVersionInput = React.useCallback((val: string): string => {
    const trimmed = (val || '').trim()
    if (!trimmed) return t('workflowCanvas.publishDialog.enterPublishVersion')
    const pattern = /^v\d+\.\d+\.\d+$/
    if (!pattern.test(trimmed)) return t('workflowCanvas.publishDialog.versionFormatIncorrect')
    return ''
  }, [t])

  const validateDescriptionInput = React.useCallback((val: string): string => {
    const trimmed = (val || '').trim()
    if (!trimmed) return t('workflowCanvas.publishDialog.enterPublishDescription')
    if (trimmed.length < 5) return t('workflowCanvas.publishDialog.descriptionMinLength')
    if (trimmed.length > 200) return t('workflowCanvas.publishDialog.descriptionMaxLength')
    return ''
  }, [t])

  const versionValidationError = validateVersionInput(version)
  const descriptionValidationError = validateDescriptionInput(description)
  const showVersionError = (versionTouched || hasSubmitted) && !!versionValidationError
  const showDescriptionError = (descriptionTouched || hasSubmitted) && !!descriptionValidationError
  // 允许用户在输入不合法时也能点击提交，由 handleConfirm 统一拦截并给出错误提示
  const isSubmitDisabled = loading

  React.useEffect(() => {
    if (!open) return
    // 打开时初始化描述
    setDescription('')
    setVersionTouched(false)
    setDescriptionTouched(false)
    setHasSubmitted(false)

    // 若缺少必要参数，则使用默认版本
    if (!workflowId || !spaceId) {
      setVersion(defaultVersion)
      return
    }

    refreshDefaultVersion(workflowId, spaceId, defaultVersion, setVersion, t)
  }, [open, workflowId, spaceId, defaultVersion, t])

  const handleConfirm = async () => {
    if (!workflowId || !spaceId) {
      Toast.error(t('workflowCanvas.publishDialog.workflowInfoNotFound'))
      return
    }

    // 提交时静默校验，阻止无效提交（不弹 Toast）
    if (versionValidationError || descriptionValidationError) {
      setHasSubmitted(true)
      return
    }

    setLoading(true)
    try {
      const asyncSaveFunction = asyncSaveRef?.current
      if (asyncSaveFunction) {
        await asyncSaveFunction()
      } else {
        onSave()
      }

      const response = await WorkflowService.publishWorkflow({
        workflow_id: workflowId,
        space_id: spaceId,
        force: false,
        version: version.trim(),
        version_description: description.trim(),
      })

      if (response.code === 200) {
        Toast.success(t('workflowCanvas.publishDialog.publishSuccess'))
        // 通知 store 发布成功：刷新历史列表并重置选中为草稿
        const notifyPublished = useWorkflowStore.getState().notifyPublished
        notifyPublished({ workflowId, spaceId })
        onClose()
        setVersion('')
        setDescription('')
        setVersionTouched(false)
        setDescriptionTouched(false)
        setHasSubmitted(false)
      } else {
        Toast.error(response.message || t('workflowCanvas.publishDialog.publishFailed'))
      }
    } catch (error: any) {
      console.error(t('workflowCanvas.publishDialog.publishWorkflowFailed'), error)
      Toast.error(error?.message || t('workflowCanvas.publishDialog.publishFailedRetry'))
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    onClose()
    setVersion('')
    setDescription('')
    setVersionTouched(false)
    setDescriptionTouched(false)
    setHasSubmitted(false)
  }

  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          width: '480px',
          maxWidth: '90vw',
        }}
      >
        <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', fontWeight: 'bold' }}>{t('workflowCanvas.publishDialog.publishWorkflow')}</h3>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px', fontWeight: 500 }}>
            {t('workflowCanvas.publishDialog.publishVersion')} <span style={{ color: '#ff4d4f' }}>*</span>
          </div>
          <input
            type="text"
            value={version}
            onChange={e => {
              const v = e.target.value
              if (v.length <= 80) setVersion(v)
            }}
            placeholder={t('workflowCanvas.publishDialog.versionPlaceholder')}
            style={{
              width: '100%',
              padding: '12px 16px',
              border: `1.5px solid ${showVersionError ? '#ff4d4f' : '#d9d9d9'}`,
              borderRadius: '6px',
              fontSize: '14px',
              outline: 'none',
              transition: 'border-color 0.2s ease',
            }}
            onBlur={() => {
              setVersionTouched(true)
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
            {showVersionError ? (
              <div style={{ fontSize: '12px', color: '#ff4d4f' }}>{versionValidationError}</div>
            ) : (
              <div />
            )}
            <div style={{ fontSize: '12px', color: '#999' }}>{version.length}/80</div>
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '14px', color: '#333', marginBottom: '8px', fontWeight: 500 }}>
            {t('workflowCanvas.publishDialog.publishDescription')} <span style={{ color: '#ff4d4f' }}>*</span>
          </div>
          <textarea
            value={description}
            onChange={e => {
              const v = e.target.value
              if (v.length <= 200) setDescription(v)
            }}
            placeholder={t('workflowCanvas.publishDialog.descriptionPlaceholder')}
            style={{
              width: '100%',
              minHeight: '120px',
              padding: '12px 16px',
              border: `1.5px solid ${showDescriptionError ? '#ff4d4f' : '#d9d9d9'}`,
              borderRadius: '6px',
              fontSize: '14px',
              lineHeight: '1.5',
              resize: 'vertical',
              fontFamily: 'inherit',
              outline: 'none',
              transition: 'border-color 0.2s ease',
            }}
            onBlur={() => {
              setDescriptionTouched(true)
            }}
            maxLength={200}
          />
          {showDescriptionError && <div style={{ fontSize: '12px', color: '#ff4d4f', marginTop: '4px' }}>{descriptionValidationError}</div>}
          <div style={{ fontSize: '12px', color: '#999', textAlign: 'right', marginTop: '4px' }}>{description.length}/200</div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
          <button
            onClick={handleCancel}
            disabled={loading}
            style={{
              padding: '8px 16px',
              border: '1px solid #d9d9d9',
              borderRadius: '6px',
              backgroundColor: 'white',
              color: '#333',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
            }}
          >
            {t('workflowCanvas.publishDialog.cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitDisabled}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: '#1890ff',
              color: 'white',
              cursor: isSubmitDisabled ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              opacity: isSubmitDisabled ? 0.6 : 1,
            }}
          >
            {loading ? t('workflowCanvas.publishDialog.publishing') : t('workflowCanvas.publishDialog.confirmPublish')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default PublishDialog
