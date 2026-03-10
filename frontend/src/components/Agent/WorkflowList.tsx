import Typography from '@mui/material/Typography'
import Tooltip from '@mui/material/Tooltip'
import { WorkflowDetail } from '../../types/agentTypes'
import { AlertCircle, LoaderCircle, Settings, Trash2, Workflow } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { useAgentStore } from '@/stores/useAgentStore'
import { useWorkflowVersions } from '@/hooks/useWorkflowVersions'
import { isVersionValid } from '@/utils/versionMenu'
import { VersionField } from '@/components/Agent/VersionField'
import type { WorkflowValidationResult } from '@/hooks/useWorkflowValidation'
import { useScopedTranslation } from '@/i18n'

const WorkflowList = ({
  workflowObjects,
  onClick,
  disabled = false,
  refreshToken,
  validationResults,
  onVersionChange,
}: {
  workflowObjects: WorkflowDetail[]
  onClick: (operate: 'delete' | 'setting', workflowId: string, version?: string) => void
  disabled?: boolean
  refreshToken?: number
  validationResults?: Record<string, WorkflowValidationResult>
  onVersionChange?: (workflowId: string, version: string) => void
}) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration.workflowSetting.workflowList')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null)

  const [selectedVersions, setSelectedVersions] = useState<Record<string, string>>({})
  const updateWorkflowDetail = useAgentStore(s => s.updateWorkflowDetail)

  const initializedIdsRef = useRef<Set<string>>(new Set())

  const spaceId = useMemo(() => getDefaultSpaceId() || '', [])
  const { versionsMap, loadingMap, refresh } = useWorkflowVersions(workflowObjects, spaceId)

  // 刷新按钮触发版本列表刷新
  const prevRefreshTokenRef = useRef(refreshToken)
  useEffect(() => {
    if (refreshToken !== undefined && refreshToken !== prevRefreshTokenRef.current) {
      prevRefreshTokenRef.current = refreshToken
      refresh()
    }
  }, [refreshToken, refresh])

  // 版本初始化：只为新增的工作流设置版本，刷新时不覆盖用户选择
  useEffect(() => {
    const currentIds = new Set(workflowObjects.map(w => w.workflow_id))
    const newIds = [...currentIds].filter(id => !initializedIdsRef.current.has(id))

    if (newIds.length === 0) return

    newIds.forEach(id => initializedIdsRef.current.add(id))

    setSelectedVersions(prev => {
      const next = { ...prev }
      newIds.forEach(id => {
        const workflow = workflowObjects.find(w => w.workflow_id === id)
        if (workflow) {
          next[id] = workflow.workflow_version || 'draft'
        }
      })
      Object.keys(next).forEach(id => {
        if (!currentIds.has(id)) {
          delete next[id]
          initializedIdsRef.current.delete(id)
        }
      })
      return next
    })
  }, [workflowObjects])

  // 版本有效性检查：如果版本被删除，重置为 draft
  useEffect(() => {
    if (Object.values(loadingMap).some(v => v)) return

    const invalidWorkflows = workflowObjects.filter(w => {
      if (!initializedIdsRef.current.has(w.workflow_id)) return false
      const version = selectedVersions[w.workflow_id]
      if (!version || version === 'draft') return false
      return !isVersionValid(w.workflow_id, versionsMap, version)
    })

    if (invalidWorkflows.length > 0) {
      setSelectedVersions(prev => {
        const next = { ...prev }
        invalidWorkflows.forEach(w => {
          next[w.workflow_id] = 'draft'
        })
        return next
      })
      updateWorkflowDetail(
        workflowObjects.map(w =>
          invalidWorkflows.find(i => i.workflow_id === w.workflow_id)
            ? { ...w, workflow_version: 'draft' }
            : w
        )
      )
    }
  }, [workflowObjects, versionsMap, loadingMap, selectedVersions])

  const handleVersionChange = (workflowId: string, ver: string) => {
    setSelectedVersions(prev => ({ ...prev, [workflowId]: ver }))
    const updated = workflowObjects.map(w => (w.workflow_id === workflowId ? { ...w, workflow_version: ver } : w))
    updateWorkflowDetail(updated)
    onVersionChange?.(workflowId, ver)
  }

  return (
    <div className="space-y-4">
      {workflowObjects.map(workflow => (
        <div
          key={workflow.workflow_id}
          className="flex items-start justify-between py-4 px-5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm hover:shadow-sm transition-all duration-200"
        >
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-lg flex items-center justify-center border border-blue-200 dark:border-blue-800 mt-1">
              <Workflow className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1 min-w-0 max-w-[320px]">
              <div className="flex items-center gap-1 min-w-0 mb-2">
                <Typography
                  sx={{
                    fontWeight: 'bold',
                    fontSize: '1rem',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  className="min-w-0 text-gray-900 dark:text-gray-100"
                  title={workflow.workflow_name}
                >
                  {workflow.workflow_name}
                </Typography>
                {validationResults?.[workflow.workflow_id]?.status === 'loading' && (
                  <span className="inline-flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                    <LoaderCircle className="w-4 h-4 animate-spin" />
                    <span>{t('validating')}</span>
                  </span>
                )}
                {validationResults?.[workflow.workflow_id]?.status === 'error' && (
                  <Tooltip title={t('validationFailedTooltip')} arrow>
                    <span className="inline-flex items-center flex-shrink-0 ml-1">
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation()
                          if (disabled) return
                          const currentVersion = selectedVersions[workflow.workflow_id] ?? 'draft'
                          onClick('setting', workflow.workflow_id, currentVersion)
                        }}
                        disabled={disabled}
                        className={`inline-flex items-center text-red-600 dark:text-red-400 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                        aria-label={t('validationFailedAria')}
                      >
                        <AlertCircle className="w-4 h-4" />
                      </button>
                    </span>
                  </Tooltip>
                )}
              </div>
              {workflow.description && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontSize: '0.875rem',
                    lineHeight: 1.5,
                    marginTop: 0,
                    marginBottom: '4px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    maxWidth: '400px',
                  }}
                  className="text-gray-500 dark:text-gray-400"
                  title={workflow.description}
                >
                  {workflow.description}
                </Typography>
              )}
              <div className="flex items-center space-x-3 mt-1">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('versionLabel')}</span>
                <VersionField
                  workflowId={workflow.workflow_id}
                  value={selectedVersions[workflow.workflow_id] ?? 'draft'}
                  onChange={ver => handleVersionChange(workflow.workflow_id, ver)}
                  spaceId={spaceId}
                  readonly={disabled}
                  versionsMap={versionsMap}
                  loadingMap={loadingMap}
                />
              </div>
            </div>
          </div>
          <div className="flex space-x-5 pt-2">
            <button
              title={t('settingsTitle')}
              onClick={e => {
                e.stopPropagation()
                const currentVersion = selectedVersions[workflow.workflow_id] ?? 'draft'
                onClick('setting', workflow.workflow_id, currentVersion)
              }}
            >
              <Settings className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button
              title={t('deleteTitle')}
              onClick={e => {
                e.stopPropagation()
                if (!disabled) {
                  setPendingDelete({ id: workflow.workflow_id, name: workflow.workflow_name })
                  setConfirmOpen(true)
                }
              }}
              disabled={disabled}
              className={`${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Trash2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>
      ))}
      {workflowObjects.length === 0 && <div className="text-center py-6 text-gray-500 dark:text-gray-400">{t('emptyText')}</div>}
      <DeleteConfirmationDialog
        isOpen={confirmOpen}
        onClose={() => {
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        onConfirm={() => {
          if (pendingDelete) onClick('delete', pendingDelete.id)
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        itemType="workflow"
        itemName={pendingDelete?.name || ''}
      />
    </div>
  )
}

export default WorkflowList
