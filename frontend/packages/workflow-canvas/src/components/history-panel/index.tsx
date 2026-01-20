/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect } from 'react'
import dayjs from 'dayjs'
import { History as HistoryIcon, X, FileText, Tag, Loader2, Trash2 } from 'lucide-react'
import { Toast } from '@douyinfe/semi-ui'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import { WorkflowService, getErrorMessage } from '@test-agentstudio/api-client'
import { useWorkflowStore } from '../../stores/useWorkflowStore'
import { useTranslation } from '../../i18n'
import { usePanelManager } from '@flowgram.ai/panel-manager-plugin'

export interface HistoryPanelProps {
  title?: string
  width?: number
  onClose: () => void
  workflowId?: string
  spaceId?: string
  selectedVersion?: string | null
  onSelectVersion?: (_versionId: string) => void
  refreshKey?: number
}

export interface VersionListItem {
  id: string
  version: string
  description?: string
  createdAt?: string
  createdTs?: number
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  title,
  width = 360,
  onClose,
  workflowId,
  spaceId,
  selectedVersion,
  onSelectVersion,
  refreshKey,
}) => {
  const { t } = useTranslation()
  const panelManager = usePanelManager()

  // 打开历史面板时，关闭试运行面板和节点详情面板
  useEffect(() => {
    panelManager.close('test-run-panel')
    panelManager.close('node-form-panel')
  }, [panelManager])

  const [versions, setVersions] = React.useState<VersionListItem[]>([])
  const [loading, setLoading] = React.useState<boolean>(false)
  const [switchingVersion, setSwitchingVersion] = React.useState<string | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [restoreConfirmOpen, setRestoreConfirmOpen] = React.useState(false)
  const [restoreTargetVersion, setRestoreTargetVersion] = React.useState<string | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = React.useState(false)
  const [deleteTargetVersion, setDeleteTargetVersion] = React.useState<string | null>(null)
  const [deletingVersion, setDeletingVersion] = React.useState<string | null>(null)
  const contentRef = React.useRef<HTMLDivElement>(null)

  const handleCreateCopy = async (version?: string) => {
    if (!workflowId || !spaceId) return
    try {
      const resp = await WorkflowService.copyWorkflow({ workflow_id: workflowId, space_id: spaceId, version: version === 'draft' ? undefined : version })
      const newId = resp?.data?.workflow?.workflow_id
      if (newId) {
        window.open(`/dashboard/workflows/editor/${newId}?spaceId=${spaceId}`, '_blank')
      }
    } catch (e) {
      console.error(t('workflowCanvas.historyPanel.createCopyFailed'), e)
      Toast.error({ content: getErrorMessage(e) || t('workflowCanvas.historyPanel.createCopyFailed'), showClose: false })
    } finally {
      setSwitchingVersion(null)
    }
  }

  const openRestoreDialog = (version: string) => {
    setRestoreTargetVersion(version)
    setRestoreConfirmOpen(true)
  }

  const openRestoreConfirm = async () => {
    if (!workflowId || !spaceId || !restoreTargetVersion) return
    try {
      const canvasResp = await WorkflowService.getWorkflowCanvas({ workflow_id: workflowId, space_id: spaceId, version: restoreTargetVersion })
      const schema = canvasResp?.data?.workflow?.schema || ''
      if (!schema) throw new Error(t('workflowCanvas.historyPanel.versionContentNotFound'))
      await WorkflowService.saveWorkflow({ workflow_id: workflowId, workflow_version: 'draft', space_id: spaceId, schema })
      onSelectVersion && onSelectVersion('draft')
    } catch (e) {
      console.error(t('workflowCanvas.historyPanel.restoreVersionFailed'), e)
      Toast.error({ content: getErrorMessage(e) || t('workflowCanvas.historyPanel.restoreVersionFailed'), showClose: false })
    } finally {
      setRestoreConfirmOpen(false)
      setRestoreTargetVersion(null)
    }
  }

  const openDeleteDialog = (version: string) => {
    setDeleteTargetVersion(version)
    setDeleteConfirmOpen(true)
  }

  const handleDeleteVersion = async () => {
    if (!workflowId || !spaceId || !deleteTargetVersion) return
    try {
      setDeletingVersion(deleteTargetVersion)
      await WorkflowService.deleteWorkflowVersion({
        workflow_id: workflowId,
        space_id: spaceId,
        workflow_version: deleteTargetVersion,
      })

      // If deleting selected version, switch to draft
      if (selectedVersion === deleteTargetVersion) {
        onSelectVersion && onSelectVersion('draft')
      }

      // Refresh version list
      const { notifyPublished } = useWorkflowStore.getState()
      notifyPublished({ workflowId, spaceId })

      setDeleteConfirmOpen(false)
      setDeleteTargetVersion(null)
    } catch (e) {
      console.error(t('workflowCanvas.historyPanel.deleteVersionFailed'), e)
      Toast.error({ content: getErrorMessage(e) || t('workflowCanvas.historyPanel.deleteVersionFailed'), showClose: false })
    } finally {
      setDeletingVersion(null)
    }
  }

  React.useEffect(() => {
    const formatTimestamp = (ts: number | string): string => {
      try {
        if (typeof ts === 'number') {
          const ms = ts > 1e12 ? ts : ts > 1e10 ? ts : ts > 0 ? ts * 1000 : NaN
          if (!ms || isNaN(ms)) return t('workflowCanvas.historyPanel.invalidTime')
          const d = dayjs(ms)
          return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : t('workflowCanvas.historyPanel.invalidTime')
        }
        const d = dayjs(ts)
        return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : t('workflowCanvas.historyPanel.invalidTime')
      } catch {
        return t('workflowCanvas.historyPanel.timeFormatError')
      }
    }

    const toMs = (ts: number | string): number | null => {
      try {
        if (typeof ts === 'number') {
          const ms = ts > 1e12 ? ts : ts > 1e10 ? ts : ts > 0 ? ts * 1000 : NaN
          return !ms || isNaN(ms) ? null : ms
        }
        const d = dayjs(ts)
        return d.isValid() ? d.valueOf() : null
      } catch {
        return null
      }
    }

    const fetchVersions = async () => {
      if (!workflowId || !spaceId) return
      try {
        setLoading(true)
        setError(null)
        const resp = await WorkflowService.getWorkflowVersionList({ workflow_id: workflowId, space_id: spaceId })
        if (resp.code === 200 && resp.data?.versions) {
          const items: VersionListItem[] = resp.data.versions.map(
            (v: { workflow_version?: string; create_time?: number; version_description?: string }, idx: number) => {
              const ver = v.workflow_version?.startsWith('v') ? v.workflow_version : `v${v.workflow_version}`
              const createdTs = toMs(v.create_time)
              return {
                id: v.workflow_version || String(idx),
                version: ver,
                description: v.version_description || t('workflowCanvas.historyPanel.noVersionDescription'),
                createdAt: formatTimestamp(v.create_time),
                createdTs: createdTs ?? undefined,
              }
            },
          )
          const sortedItems = [...items].sort((a, b) => (b.createdTs ?? 0) - (a.createdTs ?? 0))
          // Always add draft version to list, will use latest data when switching to draft
          const draftItem: VersionListItem = {
            id: 'draft',
            version: 'draft',
          }
          setVersions([draftItem, ...sortedItems])
        } else {
          throw new Error(resp.message || t('workflowCanvas.historyPanel.fetchVersionHistoryFailed'))
        }
      } catch (err: { message?: string }) {
        setError(err?.message || t('workflowCanvas.historyPanel.fetchVersionHistoryFailed'))
      } finally {
        setLoading(false)
      }
    }

    fetchVersions()
  }, [workflowId, spaceId, refreshKey])

  // 当选中版本变化时，关闭切换中的提示
  React.useEffect(() => {
    if (switchingVersion && selectedVersion) {
      setSwitchingVersion(null)
      setLoading(false)
    }
  }, [selectedVersion])

  React.useEffect(() => {
    if (selectedVersion === 'draft') {
      const el = contentRef.current
      if (el) {
        el.scrollTo({ top: 0, behavior: 'smooth' })
      }
    }
  }, [selectedVersion])

  return (
    <div className="h-full bg-white border-l border-gray-200 shadow-sm flex flex-col flex-none" style={{ width }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
        <div className="flex items-center">
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 p-2 rounded-lg mr-2">
            <HistoryIcon className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-800">{title || t('workflowCanvas.historyPanel.title')}</div>
            <div className="text-xs text-gray-500">{t('workflowCanvas.historyPanel.subtitle')}</div>
          </div>
        </div>
        <button
          className="text-gray-500 hover:text-gray-700 p-2 rounded"
          aria-label="close"
          onClick={() => {
            // Restore to draft version before closing panel
            onSelectVersion && onSelectVersion('draft')
            onClose()
          }}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-3 pl-5 py-2" ref={contentRef}>
        {!workflowId || !spaceId ? (
          <div className="p-4 text-sm text-gray-500">{t('workflowCanvas.historyPanel.selectWorkflowPrompt')}</div>
        ) : error ? (
          <div className="p-4 text-sm text-red-600">{t('workflowCanvas.historyPanel.loadFailed')}: {error}</div>
        ) : loading ? (
          <div className="p-4 text-sm text-gray-500">{t('workflowCanvas.historyPanel.loading')}</div>
        ) : versions && versions.length > 0 ? (
          <ul className="space-y-3">
            {versions.map(item => {
              const isActive = selectedVersion ? item.version === selectedVersion : item.version === 'draft'
              return (
                <li key={item.id}>
                  <VersionCard
                    item={item}
                    isActive={isActive}
                    onSelectVersion={onSelectVersion}
                    switchingVersion={switchingVersion}
                    setSwitchingVersion={setSwitchingVersion}
                    onCreateCopy={() => handleCreateCopy(item.version)}
                    onRestoreVersion={() => openRestoreDialog(item.version)}
                    onDeleteVersion={() => openDeleteDialog(item.version)}
                    deletingVersion={deletingVersion}
                  />
                </li>
              )
            })}
          </ul>
        ) : (
          <div className="p-4 text-sm text-gray-500">{t('workflowCanvas.historyPanel.noVersionData')}</div>
        )}
      </div>
      <DeleteConfirmationDialog
        isOpen={restoreConfirmOpen}
        onClose={() => {
          setRestoreConfirmOpen(false)
          setRestoreTargetVersion(null)
        }}
        onConfirm={openRestoreConfirm}
        title={t('workflowCanvas.historyPanel.restoreToThisVersion')}
        message={t('workflowCanvas.historyPanel.restoreConfirmMessage')}
        confirmButtonText={t('workflowCanvas.historyPanel.confirm')}
        iconType="warning"
      />
      <DeleteConfirmationDialog
        isOpen={deleteConfirmOpen}
        onClose={() => {
          setDeleteConfirmOpen(false)
          setDeleteTargetVersion(null)
        }}
        onConfirm={handleDeleteVersion}
        title={t('workflowCanvas.historyPanel.deleteVersion')}
        message={t('workflowCanvas.historyPanel.deleteConfirmMessage', { version: deleteTargetVersion })}
        confirmButtonText={t('workflowCanvas.historyPanel.delete')}
        iconType="danger"
      />
    </div>
  )
}

const VersionCard: React.FC<{
  item: VersionListItem
  isActive: boolean
  onSelectVersion?: (_versionId: string) => void
  switchingVersion?: string | null
  setSwitchingVersion?: (v: string | null) => void
  onCreateCopy?: () => void
  onRestoreVersion?: () => void
  onDeleteVersion?: () => void
  deletingVersion?: string | null
}> = ({ item, isActive, onSelectVersion, switchingVersion, setSwitchingVersion, onCreateCopy, onRestoreVersion, onDeleteVersion, deletingVersion }) => {
  const { t } = useTranslation()
  return (
    <div
      className={`group cursor-pointer rounded-2xl border px-4 py-3 transition-all ${
        isActive ? 'border-green-300 bg-white shadow-sm ring-1 ring-green-200' : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
      } ${switchingVersion === item.version ? 'opacity-75' : ''}`}
      onClick={() => {
        if (isActive) return
        setSwitchingVersion && setSwitchingVersion(item.version)
        onSelectVersion && onSelectVersion(item.version)
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${isActive ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span className="font-semibold text-gray-900 tracking-tight overflow-hidden text-ellipsis whitespace-nowrap max-w-[100px]" title={item.version}>
            {item.version}
          </span>
        </div>
        {item.createdAt && (
          <span
            className={`inline-flex items-center gap-1 px-3 py-1 text-xs rounded-md border leading-4 ${
              isActive ? 'border-green-200 bg-green-50/70 text-green-700' : 'border-gray-200 bg-gray-50/70 text-gray-700'
            }`}
          >
            {switchingVersion === item.version ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Tag className="w-3.5 h-3.5" />}
            {switchingVersion === item.version ? t('workflowCanvas.historyPanel.switching') : item.createdAt}
          </span>
        )}
      </div>
      {item.version !== 'draft' && (
        <div className="mt-2 grid grid-cols-[20px_1fr] items-start text-sm">
          <FileText className="w-4 h-4 text-gray-500 mt-0.5" />
          <div>
            <span className="text-gray-600">{t('workflowCanvas.historyPanel.versionDescription')}:</span>
            <span
              className="whitespace-pre-line break-words text-gray-800 overflow-hidden text-ellipsis whitespace-nowrap max-w-[180px] inline-block"
              title={item.description || t('workflowCanvas.historyPanel.noVersionDescription')}
            >
              {item.description || t('workflowCanvas.historyPanel.noVersionDescription')}
            </span>
          </div>
        </div>
      )}
      {isActive && (
        <div className="mt-2 flex justify-end gap-2 flex-wrap">
          <button
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 bg-white border border-green-300 rounded-md transition-colors hover:bg-green-50 focus:outline-none disabled:opacity-60"
            onClick={e => {
              e.stopPropagation()
              onCreateCopy && onCreateCopy()
            }}
          >
            {t('workflowCanvas.historyPanel.createCopy')}
          </button>
          {item.version !== 'draft' && (
            <button
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 bg-white border border-green-300 rounded-md transition-colors hover:bg-green-50 focus:outline-none disabled:opacity-60"
              onClick={e => {
                e.stopPropagation()
                onRestoreVersion && onRestoreVersion()
              }}
            >
              {t('workflowCanvas.historyPanel.restoreToThisVersion')}
            </button>
          )}
          {item.version !== 'draft' && (
            <button
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-white border border-red-300 rounded-md transition-colors hover:bg-red-50 focus:outline-none disabled:opacity-60"
              onClick={e => {
                e.stopPropagation()
                onDeleteVersion && onDeleteVersion()
              }}
              disabled={deletingVersion === item.version}
            >
              {deletingVersion === item.version ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {t('workflowCanvas.historyPanel.deleting')}
                </>
              ) : (
                <>
                  <Trash2 className="w-3 h-3" />
                  {t('workflowCanvas.historyPanel.delete')}
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default HistoryPanel
