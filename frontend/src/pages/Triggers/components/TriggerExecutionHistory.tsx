import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, IconButton, Tooltip, CircularProgress, Typography,
  Pagination, Box, Collapse, Alert,
} from '@mui/material'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { useTriggerExecutionLogs } from '@test-agentstudio/api-client'
import dayjs from 'dayjs'
import type { TriggerExecutionLog, ExecutionStatus } from '@/types/triggerTypes'

interface TriggerExecutionHistoryProps {
  spaceId: string
  triggerId: string
}

const STATUS_COLORS: Record<ExecutionStatus, 'success' | 'error' | 'default' | 'warning'> = {
  success: 'success',
  error: 'error',
  skipped: 'default',
  running: 'warning',
}

const TriggerExecutionHistory: React.FC<TriggerExecutionHistoryProps> = ({ spaceId, triggerId }) => {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const PAGE_SIZE = 10

  const { data, isLoading, refetch } = useTriggerExecutionLogs(spaceId, triggerId, page, PAGE_SIZE)

  const logs: TriggerExecutionLog[] = (data?.data as any)?.items || []
  const total: number = (data?.data as any)?.total || 0

  // Auto-expand rows that have an error message so failures are immediately visible
  useEffect(() => {
    const errorIds = logs
      .filter(l => l.error_message)
      .map(l => l.id)
    if (errorIds.length > 0) {
      setExpandedRows(prev => new Set([...prev, ...errorIds]))
    }
  }, [data])

  const formatDuration = (ms?: number | null) => {
    if (ms == null) return '—'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const formatTime = (ts?: number | null) => {
    if (!ts) return '—'
    return dayjs(ts).format('MM-DD HH:mm:ss')
  }

  const hasDetails = (log: TriggerExecutionLog) =>
    !!(log.error_message || (log.outputs && Object.keys(log.outputs).length > 0))

  const toggleRow = (id: number) =>
    setExpandedRows(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Typography variant="subtitle1" fontWeight="medium">
          {t('triggers.executionHistory.title', 'Execution History')}
        </Typography>
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </IconButton>
        </Tooltip>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <CircularProgress size={24} />
        </div>
      ) : logs.length === 0 ? (
        <Typography variant="body2" color="text.secondary" className="py-8 text-center">
          {t('triggers.executionHistory.noLogs', 'No executions yet')}
        </Typography>
      ) : (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('triggers.executionHistory.startedAt', 'Started')}</TableCell>
                  <TableCell>{t('triggers.executionHistory.duration', 'Duration')}</TableCell>
                  <TableCell>{t('triggers.executionHistory.status', 'Status')}</TableCell>
                  <TableCell>{t('triggers.executionHistory.firedBy', 'Fired By')}</TableCell>
                  <TableCell align="center" sx={{ width: 48 }} />
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map(log => {
                  const expanded = expandedRows.has(log.id)
                  const showDetails = hasDetails(log)
                  return (
                    <React.Fragment key={log.id}>
                      <TableRow
                        hover
                        sx={showDetails ? { cursor: 'pointer' } : undefined}
                        onClick={showDetails ? () => toggleRow(log.id) : undefined}
                      >
                        <TableCell>
                          <Typography variant="caption">{formatTime(log.started_at)}</Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">{formatDuration(log.duration_ms)}</Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={t(`triggers.executionStatus.${log.status}`, log.status)}
                            color={STATUS_COLORS[log.status] || 'default'}
                            size="small"
                            sx={log.status === 'running' ? { animation: 'pulse 2s infinite' } : {}}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {log.fired_by ? t(`triggers.firedBy.${log.fired_by}`, log.fired_by) : '—'}
                          </Typography>
                        </TableCell>
                        {/* Expand/collapse toggle — spans the unlabelled last column */}
                        <TableCell align="center" sx={{ width: 48, p: 0 }}>
                          {showDetails ? (
                            <IconButton
                              size="small"
                              onClick={e => { e.stopPropagation(); toggleRow(log.id) }}
                              color={log.error_message ? 'error' : 'default'}
                            >
                              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </IconButton>
                          ) : null}
                        </TableCell>
                      </TableRow>

                      {/* Expandable detail row */}
                      {showDetails && (
                        <TableRow>
                          <TableCell
                            colSpan={5}
                            sx={{
                              py: 0,
                              borderBottom: expanded ? undefined : 'none',
                              // Subtle red tint behind error details
                              bgcolor: log.error_message ? 'error.50' : 'transparent',
                            }}
                          >
                            <Collapse in={expanded} unmountOnExit>
                              <Box sx={{ py: 1.5, px: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                                {log.error_message && (
                                  <Alert
                                    severity="error"
                                    sx={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                                  >
                                    {log.error_message}
                                  </Alert>
                                )}
                                {log.outputs && Object.keys(log.outputs).length > 0 && (
                                  <Box>
                                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                      {t('triggers.executionHistory.outputs', 'Outputs')}
                                    </Typography>
                                    <Box
                                      component="pre"
                                      sx={{
                                        mt: 0.5, p: 1, borderRadius: 1,
                                        bgcolor: 'action.hover',
                                        fontSize: '0.7rem',
                                        overflowX: 'auto',
                                        whiteSpace: 'pre-wrap',
                                        wordBreak: 'break-word',
                                        m: 0,
                                      }}
                                    >
                                      {JSON.stringify(log.outputs, null, 2)}
                                    </Box>
                                  </Box>
                                )}
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
          {total > PAGE_SIZE && (
            <Box className="flex justify-center">
              <Pagination
                count={Math.ceil(total / PAGE_SIZE)}
                page={page}
                onChange={(_, v) => setPage(v)}
                size="small"
              />
            </Box>
          )}
        </>
      )}
    </div>
  )
}

export default TriggerExecutionHistory
