import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Tooltip, Box, Typography, LinearProgress } from '@mui/material'
import { Trash2, Eye } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import type { TableColumn } from '@/components/Common/common-table'
import dayjs from 'dayjs'

export interface PromptOptimizationRow {
  id: string
  name: string
  status: 'pending' | 'optimizing' | 'completed' | 'failed' | 'stopping' | 'draft'
  optimizationRounds: number
  progress: number
  createdAt: string
  duration: string
  description: string
  errorMsg?: string
  jobType?: 'formal' | 'draft'
}

export interface PromptOptimizeTableViewProps {
  prompts: PromptOptimizationRow[]
  loading?: boolean
  emptyState?: React.ReactNode
  onView: (prompt: PromptOptimizationRow) => void
  onDelete: (prompt: PromptOptimizationRow) => void
  getStatusLabel: (status: PromptOptimizationRow['status']) => string
}

const formatDateValue = (value: unknown): string => {
  if (!value) return ''
  return dayjs(value as string | number | Date).format('YYYY-MM-DD HH:mm:ss')
}

export const PromptOptimizeTableView: React.FC<PromptOptimizeTableViewProps> = ({
  prompts,
  loading = false,
  emptyState,
  onView,
  onDelete,
  getStatusLabel,
}) => {
  const { t } = useTranslation()

  const renderStatusWithProgress = (prompt: PromptOptimizationRow) => {
    const { status, errorMsg } = prompt
    const statusLabel = getStatusLabel(status)

    let color = '#6b7280' // 默认灰色
    switch (status) {
      case 'completed':
        color = '#16a34a'
        break
      case 'optimizing':
        color = '#2563eb'
        break
      case 'failed':
        color = '#dc2626'
        break
      case 'stopping':
        color = '#f97316'
        break
      case 'draft':
        color = '#0ea5e9'
        break
      default:
        color = '#6b7280'
    }

    const statusDotAndText = (
      <div className="flex items-center gap-1.5">
        <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-xs font-medium" style={{ color: '#777777' }}>
          {statusLabel}
        </span>
      </div>
    )

    const statusContent =
      status === 'failed' && errorMsg?.trim() ? (
        <Tooltip
          title={
            <Box>
              <Typography variant="body2" fontWeight="bold" sx={{ mb: 1 }}>
                {t('prompts.optimizePage.messages.failureReason')}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', maxWidth: 400 }}>
                {errorMsg}
              </Typography>
            </Box>
          }
          placement="top"
          arrow
        >
          {statusDotAndText}
        </Tooltip>
      ) : (
        statusDotAndText
      )

    const progressValue = Math.max(0, Math.min(100, Number.isFinite(prompt.progress) ? prompt.progress : 0))
    const showProgress = prompt.status === 'optimizing' || prompt.status === 'completed'
    const percentText = `${showProgress ? progressValue : 0}%`

    return (
      <div className="flex items-center gap-3 min-w-0">
        <div className="shrink-0">{statusContent}</div>
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div className="flex-1 min-w-[96px]">
            <LinearProgress
              variant="determinate"
              value={showProgress ? progressValue : 0}
              sx={{
                height: 6,
                borderRadius: 999,
                backgroundColor: '#e5e7eb',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 999,
                  backgroundColor: prompt.status === 'completed' ? '#16a34a' : '#22c55e',
                },
              }}
            />
          </div>
          <div className="text-xs text-gray-600 w-10 text-right tabular-nums">{percentText}</div>
        </div>
      </div>
    )
  }

  const columns: TableColumn<PromptOptimizationRow>[] = useMemo(
    () => [
      {
        key: 'name',
        title: t('prompts.optimizePage.table.taskName'),
        dataIndex: 'name',
        minWidth: 260,
        width: 400,
        render: ({ row }) => (
          <div className="flex flex-col min-w-0">
            <div
              className="font-semibold text-gray-900 cursor-pointer truncate hover:text-blue-600"
              onClick={() => onView(row)}
            >
              {row.name}
            </div>
            {row.description && (
              <div className="mt-1 text-xs text-gray-500 truncate">{row.description}</div>
            )}
          </div>
        ),
      },
      {
        key: 'status',
        title: t('prompts.optimizePage.table.status'),
        dataIndex: 'status',
        width: 260,
        minWidth: 240,
        render: ({ row }) => renderStatusWithProgress(row),
      },
      {
        key: 'rounds',
        title: t('prompts.optimizePage.table.rounds'),
        dataIndex: 'optimizationRounds',
        width: 120,
        render: ({ row }) => (
          <span>
            {row.optimizationRounds} {t('prompts.optimizePage.table.round')}
          </span>
        ),
      },
      {
        key: 'duration',
        title: t('prompts.optimizePage.table.duration'),
        dataIndex: 'duration',
        width: 120,
        render: ({ row }) => <span>{row.duration}</span>,
      },
      {
        key: 'createdAt',
        title: t('prompts.optimizePage.table.createdAt'),
        dataIndex: 'createdAt',
        type: 'date',
        width: 170,
        dateFormatter: (value) => formatDateValue(value),
      },
      {
        key: 'actions',
        title: t('prompts.optimizePage.table.actions'),
        type: 'operate',
        align: 'right',
        width: 140,
        minWidth: 140,
        operations: [
          {
            key: 'view',
            icon: <Eye className="w-4 h-4" />,
            label: t('prompts.optimizePage.actions.view'),
            tooltip: t('prompts.optimizePage.actions.view'),
            onClick: row => onView(row),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('prompts.optimizePage.actions.delete'),
            tooltip: t('prompts.optimizePage.actions.delete'),
            onClick: row => onDelete(row),
          },
        ],
      },
    ],
    [t, onView, onDelete, getStatusLabel],
  )

  const tableData = useMemo(() => ({ columns, rows: prompts }), [columns, prompts])

  return (
    <ConfigTable
      tableData={tableData}
      loading={loading}
      size="small"
      stickyHeader
      emptyState={emptyState}
    />
  )
}

export default PromptOptimizeTableView
