import React, { useEffect } from 'react'
import { Select, CircularProgress } from '@mui/material'
import { AlertCircle } from 'lucide-react'
import type { VersionsMap, LoadingMap } from '@/hooks/useWorkflowVersions'
import { renderVersionMenuItems } from '@/utils/versionMenu'
import { useScopedTranslation } from '@/i18n'

export const VersionField: React.FC<{
  workflowId?: string
  value?: string
  onChange?: (v: string) => void
  spaceId: string
  readonly?: boolean
  versionsMap: VersionsMap
  loadingMap?: LoadingMap
}> = ({ workflowId, value, onChange, readonly = false, versionsMap, loadingMap = {} }) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration.workflowSetting.versionField')
  const latest = workflowId ? versionsMap[workflowId]?.latestPublished || 'draft' : 'draft'
  const normalized = !value || value === '' ? 'draft' : value
  const isLoading = workflowId ? loadingMap[workflowId] : false

  useEffect(() => {
    if ((value === undefined || value === null) && workflowId) {
      onChange?.(latest)
    } else if (value === '' && workflowId) {
      onChange?.('draft')
    }
  }, [latest, workflowId])
  const ready = !!workflowId && !isLoading && !!versionsMap[workflowId]
  if (!workflowId) return null
  if (!ready) {
    return (
      <div className="inline-flex items-center gap-2 text-xs text-gray-500">
        <CircularProgress size={16} />
        <span>{t('loading')}</span>
      </div>
    )
  }
  const hint =
    normalized === 'draft' ? (
      <span className="inline-flex items-center text-xs text-gray-500 leading-[18px]">
        <AlertCircle className="w-4 h-4 mr-1" />
        {t('followLatest')}
      </span>
    ) : latest && normalized !== latest ? (
      <span className="inline-flex items-center text-xs text-amber-600 leading-[18px]">
        <AlertCircle className="w-4 h-4 mr-1" />
        {t('hasNewVersion')}
      </span>
    ) : (
      <span className="inline-flex items-center text-xs text-gray-500 leading-[18px]">{t('latestPublished')}</span>
    )
  if (readonly || !onChange) {
    return (
      <span className="inline-flex items-center gap-2 text-xs">
        <span className="leading-[18px]">{normalized === 'draft' ? t('draftLabel') : normalized}</span>
        {hint}
      </span>
    )
  }
  return (
    <div className="flex flex-row items-center gap-2">
      <Select
        size="small"
        value={normalized}
        onChange={e => onChange(e.target.value as string)}
        displayEmpty
        disabled={!workflowId || isLoading}
        sx={{ minWidth: 120, width: 'fit-content', fontSize: '0.8rem', '& .MuiSelect-select': { py: 0.25, px: 1.25, lineHeight: '18px', fontSize: '0.8rem' } }}
        MenuProps={{ PaperProps: { sx: { maxHeight: 180 } } }}
      >
        {workflowId
          ? renderVersionMenuItems(workflowId, versionsMap, {
              includeDraft: true,
              itemSx: { fontSize: '0.8rem', py: 0.25 },
              draftLabel: t('draftLabel'),
            })
          : null}
      </Select>
      {hint}
    </div>
  )
}
