import React from 'react'
import { Tooltip } from '@mui/material'
import { useTranslation } from 'react-i18next'

export type PublishStatus = 'false' | 'pending' | 'running' | 'stopped' | 'failed'

export interface PublishStatusConfig {
  label: string
  className: string
  color: string
}

export const normalizePublishStatus = (status?: string | null): PublishStatus => {
  if (!status) return 'false'
  const normalized = String(status).toLowerCase().trim()
  if (normalized === 'pending' || normalized === 'running' || normalized === 'stopped' || normalized === 'failed') {
    return normalized
  }
  return 'false'
}

export const getPublishStatusConfig = (t: (key: string) => string, status?: string | null): PublishStatusConfig => {
  const key = normalizePublishStatus(status)
  const map: Record<PublishStatus, PublishStatusConfig> = {
    false: {
      label: t('agents.tableView.publishStatus.unpublished'),
      className: 'bg-gray-100 text-gray-700',
      color: '#6B7280',
    },
    pending: {
      label: t('agents.tableView.publishStatus.pending'),
      className: 'bg-amber-100 text-amber-700',
      color: '#F59E0B',
    },
    running: {
      label: t('agents.tableView.publishStatus.running'),
      className: 'bg-green-100 text-green-700',
      color: '#22C55E',
    },
    stopped: {
      label: t('agents.tableView.publishStatus.stopped'),
      className: 'bg-gray-100 text-gray-700',
      color: '#6B7280',
    },
    failed: {
      label: t('agents.tableView.publishStatus.failed'),
      className: 'bg-red-100 text-red-700',
      color: '#EF4444',
    },
  }
  return map[key]
}

interface PublishStatusTagProps {
  status?: string | null
  withTooltip?: boolean
  className?: string
}

const PublishStatusTag: React.FC<PublishStatusTagProps> = ({ status, withTooltip = false, className = '' }) => {
  const { t } = useTranslation()
  const config = getPublishStatusConfig(t, status)

  const tagNode = (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.className} ${className}`.trim()}>
      {config.label}
    </span>
  )

  if (!withTooltip) {
    return tagNode
  }

  return (
    <Tooltip title={config.label} disableInteractive placement="top">
      {tagNode}
    </Tooltip>
  )
}

export default PublishStatusTag
