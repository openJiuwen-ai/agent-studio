import React, { useState, useMemo, useEffect } from 'react';
import cronstrue from 'cronstrue';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Chip,
  CircularProgress,
  IconButton,
  MenuItem,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  FormControl,
  InputLabel,
  Snackbar,
  Alert,
} from '@mui/material';
import { Plus, Pencil, Trash2, Play, Clock, Webhook, Radio, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/stores/useAuthStore';
import {
  useTriggers,
  useActivateTrigger,
  useDeactivateTrigger,
  useDeleteTrigger,
  useRunTrigger,
  useAgents,
  useWorkflows,
  TriggerService,
} from '@test-agentstudio/api-client';
import { useTranslation as useT } from 'react-i18next';
import type { Trigger, TriggerType, TriggerExecutionLog, ExecutionStatus } from '@/types/triggerTypes';
import dayjs from 'dayjs';

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

const EXEC_STATUS_COLORS: Record<ExecutionStatus, 'success' | 'error' | 'default' | 'warning'> = {
  success: 'success',
  error: 'error',
  skipped: 'default',
  running: 'warning',
};

function formatDuration(ms?: number | null): string {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

const TYPE_COLORS: Record<TriggerType, 'primary' | 'secondary' | 'warning'> = {
  cron: 'primary',
  webhook: 'secondary',
  polling: 'warning',
};

const TYPE_ICONS: Record<TriggerType, React.ReactNode> = {
  cron: <Clock size={14} />,
  webhook: <Webhook size={14} />,
  polling: <Radio size={14} />,
};

const TriggersPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const spaceId = user?.spaceId || '';

  const [typeFilter, setTypeFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; trigger: Trigger | null }>({
    open: false,
    trigger: null,
  });

  const filters = {
    space_id: spaceId,
    ...(typeFilter ? { trigger_type: typeFilter } : {}),
    ...(activeFilter !== '' ? { is_active: activeFilter === 'true' } : {}),
    page,
    page_size: 20,
  };

  const { data, isLoading, refetch } = useTriggers(filters);
  const triggers: Trigger[] = (data?.data as any)?.items || [];
  const total: number = (data?.data as any)?.total || 0;

  const { data: agentsData } = useAgents({ space_id: spaceId, page: 1, page_size: 200 });
  const { data: workflowsData } = useWorkflows({ space_id: spaceId });

  const agentMap = useMemo(() => {
    const m: Record<string, string> = {};
    const raw = agentsData?.data as any;
    for (const a of (raw?.agent_items || raw?.data?.agent_items || [])) m[a.agent_id] = a.agent_name;
    return m;
  }, [agentsData]);

const workflowMap = useMemo(() => {
  const m: Record<string, string> = {};
  const raw = workflowsData?.data as any;

  const list =
    raw?.workflow_list ||
    raw?.workflow_items ||
    raw?.data?.workflow_list ||
    raw?.data?.workflow_items ||
    [];

  for (const w of list) {
    m[w.workflow_id] = w.name;
  }

  return m;
}, [workflowsData]);

  // ── Last execution per trigger ──────────────────────────────────────────────
  // undefined  = not yet fetched  |  null = trigger has no executions yet
  const [lastExecutions, setLastExecutions] = useState<Record<string, TriggerExecutionLog | null | undefined>>({});

  useEffect(() => {
    if (!spaceId || triggers.length === 0) return;
    let cancelled = false;

    Promise.all(
      triggers.map(trigger =>
        TriggerService.getExecutionLogs({
          space_id: spaceId,
          trigger_id: trigger.trigger_id,
          page: 1,
          page_size: 1,
        })
          .then(res => ({
            id: trigger.trigger_id,
            log: ((res?.data as any)?.items?.[0] as TriggerExecutionLog) ?? null,
          }))
          .catch(() => ({ id: trigger.trigger_id, log: null })),
      ),
    ).then(results => {
      if (cancelled) return;
      const map: Record<string, TriggerExecutionLog | null> = {};
      for (const r of results) map[r.id] = r.log;
      setLastExecutions(map);
    });

    return () => { cancelled = true; };
  }, [data, spaceId]); // re-fetch whenever the trigger list refreshes

  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false, message: '', severity: 'success',
  });
  const closeSnackbar = () => setSnackbar(s => ({ ...s, open: false }));

  // Refresh the last execution entry for a single trigger (used after a manual run)
  const refreshOneExecution = (triggerId: string) => {
    TriggerService.getExecutionLogs({ space_id: spaceId, trigger_id: triggerId, page: 1, page_size: 1 })
      .then(res => {
        const log = ((res?.data as any)?.items?.[0] as TriggerExecutionLog) ?? null;
        setLastExecutions(prev => ({ ...prev, [triggerId]: log }));
      })
      .catch(() => {});
  };

  const { mutate: activate, isLoading: isActivating } = useActivateTrigger();
  const { mutate: deactivate, isLoading: isDeactivating } = useDeactivateTrigger();
  const { mutate: deleteTrigger, isLoading: isDeleting } = useDeleteTrigger();
  const { mutate: run } = useRunTrigger();

  const handleToggleActive = (trigger: Trigger) => {
    if (trigger.is_active) {
      deactivate({ space_id: spaceId, trigger_id: trigger.trigger_id });
    } else {
      activate({ space_id: spaceId, trigger_id: trigger.trigger_id });
    }
  };

  const handleDelete = () => {
    if (!deleteDialog.trigger) return;
    deleteTrigger(
      { space_id: spaceId, trigger_id: deleteDialog.trigger.trigger_id },
      {
        onSuccess: () => {
          setDeleteDialog({ open: false, trigger: null });
          refetch();
        },
      },
    );
  };

  const handleRun = (trigger: Trigger) => {
    run(
      { space_id: spaceId, trigger_id: trigger.trigger_id },
      {
        onSuccess: () => {
          setSnackbar({ open: true, message: t('triggers.runStarted', 'Run started'), severity: 'success' });
          // First refresh after ~1 s to pick up the "running" status
          setTimeout(() => refreshOneExecution(trigger.trigger_id), 1000);
          // Second refresh after ~5 s to pick up the final result for quick executions
          setTimeout(() => refreshOneExecution(trigger.trigger_id), 5000);
        },
        onError: (err: any) => {
          setSnackbar({
            open: true,
            message: err?.message || t('triggers.runFailed', 'Failed to start run'),
            severity: 'error',
          });
        },
      },
    );
  };

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Typography variant="h5" fontWeight="bold">
          {t('triggers.title', 'Triggers')}
        </Typography>
        <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => navigate('/dashboard/triggers/new')}>
          {t('triggers.create', 'New Trigger')}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>{t('triggers.form.triggerType', 'Type')}</InputLabel>
          <Select
            value={typeFilter}
            onChange={e => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            label={t('triggers.form.triggerType', 'Type')}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="cron">{t('triggers.types.cron', 'Cron')}</MenuItem>
            <MenuItem value="webhook">{t('triggers.types.webhook', 'Webhook')}</MenuItem>
            <MenuItem value="polling">{t('triggers.types.polling', 'Polling')}</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>{t('triggers.filter.enabled', 'Enabled')}</InputLabel>
          <Select
            value={activeFilter}
            onChange={e => {
              setActiveFilter(e.target.value);
              setPage(1);
            }}
            label={t('triggers.filter.enabled', 'Enabled')}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="true">{t('triggers.status.active', 'Enabled')}</MenuItem>
            <MenuItem value="false">{t('triggers.status.inactive', 'Disabled')}</MenuItem>
          </Select>
        </FormControl>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <CircularProgress />
        </div>
      ) : triggers.length === 0 ? (
        <div className="flex flex-col items-center py-16 gap-4">
          <Typography variant="body1" color="text.secondary">
            {t('triggers.empty', 'No triggers yet. Create one to start automating.')}
          </Typography>
          <Button variant="outlined" startIcon={<Plus size={16} />} onClick={() => navigate('/dashboard/triggers/new')}>
            {t('triggers.create', 'New Trigger')}
          </Button>
        </div>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 56, pr: 0 }}>{t('triggers.filter.enabled', 'Enabled')}</TableCell>
                <TableCell>{t('triggers.form.name', 'Name')}</TableCell>
                <TableCell>{t('triggers.form.triggerType', 'Type')}</TableCell>
                <TableCell>{t('triggers.form.targetType', 'Target')}</TableCell>
                <TableCell>{t('triggers.executionHistory.lastExecution', 'Last Execution')}</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {triggers.map(trigger => (
                <TableRow key={trigger.trigger_id} hover>
                  {/* Enabled/disabled toggle — Switch makes interactivity obvious */}
                  <TableCell sx={{ width: 56, pr: 0 }}>
                    <Tooltip
                      title={trigger.is_active
                        ? t('triggers.status.deactivate', 'Click to disable')
                        : t('triggers.status.activate', 'Click to enable')}
                    >
                      <Switch
                        size="small"
                        checked={trigger.is_active}
                        onChange={() => handleToggleActive(trigger)}
                        color="success"
                      />
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <div>
                      <Typography variant="body2" fontWeight="medium">
                        {trigger.name}
                      </Typography>
                      {trigger.description && (
                        <Typography variant="caption" color="text.secondary">
                          {trigger.description}
                        </Typography>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <Chip
                        icon={TYPE_ICONS[trigger.trigger_type] as any}
                        label={t(`triggers.types.${trigger.trigger_type}`, trigger.trigger_type)}
                        color={TYPE_COLORS[trigger.trigger_type]}
                        size="small"
                        variant="outlined"
                      />
                      {trigger.trigger_type === 'cron' && trigger.config?.cron_expr && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                          {(() => { try { return cronstrue.toString(trigger.config.cron_expr as string, { verbose: false }).replace(/, only(?= )/g, ''); } catch { return trigger.config.cron_expr as string; } })()} (UTC)
                        </Typography>
                      )}
                      {trigger.trigger_type === 'webhook' && trigger.webhook_token && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                          {trigger.webhook_token.slice(0, 29)}…
                        </Typography>
                      )}
                      {trigger.trigger_type === 'polling' && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                          {trigger.config?.poll_url as string} · Every {formatInterval(trigger.config?.poll_interval_seconds as number || 300)}
                        </Typography>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <Typography variant="body2">
                        {trigger.target_type === 'agent'
                          ? (agentMap[trigger.target_id] || trigger.target_id)
                          : (workflowMap[trigger.target_id] || trigger.target_id)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {trigger.target_type} · {trigger.target_version}
                      </Typography>
                    </div>
                  </TableCell>
                  <TableCell>
                    {(() => {
                      const log = lastExecutions[trigger.trigger_id];
                      // undefined → still loading; show nothing yet
                      if (log === undefined) return null;
                      // null → no executions yet
                      if (log === null) {
                        return (
                          <Typography variant="caption" color="text.disabled">—</Typography>
                        );
                      }
                      const chip = (
                        <Chip
                          label={t(`triggers.executionStatus.${log.status}`, log.status)}
                          color={EXEC_STATUS_COLORS[log.status] || 'default'}
                          size="small"
                        />
                      );
                      return (
                        <div>
                          {log.error_message ? (
                            <Tooltip
                              title={
                                <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                                  {log.error_message}
                                </Typography>
                              }
                              arrow
                            >
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'help' }}>
                                {chip}
                                <AlertCircle size={13} color="var(--mui-palette-error-main, #d32f2f)" />
                              </span>
                            </Tooltip>
                          ) : chip}
                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
                            {log.started_at ? dayjs(log.started_at).format('MM-DD HH:mm') : '—'}
                            {log.duration_ms != null ? ` · ${formatDuration(log.duration_ms)}` : ''}
                          </Typography>
                        </div>
                      );
                    })()}
                  </TableCell>
                  <TableCell align="right">
                    <div className="flex items-center justify-end gap-1">
                      <Tooltip title="Run Now">
                        <IconButton size="small" onClick={() => handleRun(trigger)}>
                          <Play size={14} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => navigate(`/dashboard/triggers/${trigger.trigger_id}`)}>
                          <Pencil size={14} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => setDeleteDialog({ open: true, trigger })}>
                          <Trash2 size={14} />
                        </IconButton>
                      </Tooltip>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Delete Confirmation */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, trigger: null })}>
        <DialogTitle>{t('triggers.deleteConfirm.title', 'Delete Trigger')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('triggers.deleteConfirm.message', {
              name: deleteDialog.trigger?.name || '',
              defaultValue: `Are you sure you want to delete "${deleteDialog.trigger?.name}"? This will also delete all execution history.`,
            })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, trigger: null })}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDelete} disabled={isDeleting}>
            {isDeleting ? <CircularProgress size={16} /> : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Run feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} onClose={closeSnackbar} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
};

export default TriggersPage;
