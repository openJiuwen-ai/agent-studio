import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Button, CircularProgress, Divider, FormControl, FormLabel,
  IconButton, InputLabel, MenuItem, Paper, Radio, RadioGroup,
  Select, Tab, Tabs, TextField, Typography, FormControlLabel,
  Alert, Chip,
} from '@mui/material'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  useTriggerDetail, useCreateTrigger, useUpdateTrigger, useActivateTrigger,
  useAgents, useWorkflows,
} from '@test-agentstudio/api-client'
import { TriggerService, AgentService, WorkflowService } from '@test-agentstudio/api-client'
import CronConfigForm from './components/CronConfigForm'
import WebhookConfigForm from './components/WebhookConfigForm'
import PollingConfigForm from './components/PollingConfigForm'
import TriggerExecutionHistory from './components/TriggerExecutionHistory'
import type { CreateTriggerRequest, TriggerType, TargetType } from '@/types/triggerTypes'

type InputPayloadRow = { key: string; value: string }

const TriggerFormPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEditMode = !!id
  const { user } = useAuthStore()
  const spaceId = user?.spaceId || ''

  // ── Form state ──────────────────────────────────────────────────────────────
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerType, setTriggerType] = useState<TriggerType>('cron')
  const [targetType, setTargetType] = useState<TargetType>('agent')
  const [targetId, setTargetId] = useState('')
  const [targetVersion, setTargetVersion] = useState('draft')
  const [inputPayloadRows, setInputPayloadRows] = useState<InputPayloadRow[]>([])

  // Type-specific state
  const [cronExpr, setCronExpr] = useState('0 9 * * 1')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [pollUrl, setPollUrl] = useState('')
  const [pollIntervalSeconds, setPollIntervalSeconds] = useState(300)

  const [availableVersions, setAvailableVersions] = useState<string[]>(['draft'])
  const [isLoadingVersions, setIsLoadingVersions] = useState(false)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Tracks whether the form has been initialised from server data (edit mode).
  // Prevents a background refetch from resetting user edits.
  const formInitialised = useRef(false)

  // ── Data fetching ──────────────────────────────────────────────────────────
  const { data: detailData, isLoading: isLoadingDetail } = useTriggerDetail(spaceId, id || '')

  const { data: agentsData } = useAgents({ space_id: spaceId, page: 1, page_size: 100 })
  const { data: workflowsData } = useWorkflows({ space_id: spaceId, page: 1, page_size: 100 })

  const agents = (agentsData?.data as any)?.agent_items || []
  const workflows = (workflowsData?.data as any)?.workflow_list || []
  const targetList = targetType === 'agent' ? agents : workflows
  const targetIdField = targetType === 'agent' ? 'agent_id' : 'workflow_id'
  const targetNameField = targetType === 'agent' ? 'agent_name' : 'name'

  const { mutateAsync: createTrigger } = useCreateTrigger()
  const { mutateAsync: updateTrigger } = useUpdateTrigger()
  const { mutateAsync: activate } = useActivateTrigger()

  // ── Populate form for edit mode ─────────────────────────────────────────────
  const trigger = (detailData?.data as any)

  // Populate form once when detail data arrives for edit mode.
  // Using a ref guard so that subsequent background refetches do NOT overwrite
  // changes the user has already made in the form.
  useEffect(() => {
    if (!trigger || formInitialised.current) return
    formInitialised.current = true

    setName(trigger.name || '')
    setDescription(trigger.description || '')
    setTriggerType(trigger.trigger_type || 'cron')
    setTargetType(trigger.target_type || 'agent')
    setTargetId(trigger.target_id || '')
    setTargetVersion(trigger.target_version || 'draft')

    const payload = trigger.input_payload || {}
    setInputPayloadRows(Object.entries(payload).map(([key, value]) => ({ key, value: String(value) })))

    const config = trigger.config || {}
    if (trigger.trigger_type === 'cron') {
      setCronExpr(config.cron_expr || '0 9 * * 1')
    } else if (trigger.trigger_type === 'webhook') {
      setWebhookSecret(config.webhook_secret || '')
    } else if (trigger.trigger_type === 'polling') {
      setPollUrl(config.poll_url || '')
      setPollIntervalSeconds(config.poll_interval_seconds || 300)
    }
  }, [trigger])

  // Fetch available versions whenever the selected target changes.
  // 'draft' is always the first option; published versions follow.
  useEffect(() => {
    if (!targetId || !spaceId) {
      setAvailableVersions(['draft'])
      return
    }

    let cancelled = false
    setIsLoadingVersions(true)

    const fetchVersions = async () => {
      try {
        let versions: string[] = ['draft']
        if (targetType === 'agent') {
          const res = await AgentService.getAgentVersionList({ agent_id: targetId, space_id: spaceId })
          if (!cancelled && res.code === 200) {
            const agentVersions = (res.data as any)?.versions || []
            const published = agentVersions
              .filter((v: any) => v.published_flag && v.published_flag !== 'false')
              .map((v: any) => v.agent_version as string)
            versions = ['draft', ...published]
          }
        } else {
          const res = await WorkflowService.getWorkflowVersionList({ workflow_id: targetId, space_id: spaceId })
          if (!cancelled && res.code === 200) {
            const wfVersions = (res.data as any)?.versions || []
            const published = wfVersions.map((v: any) => v.workflow_version as string)
            versions = ['draft', ...published]
          }
        }
        if (!cancelled) setAvailableVersions(versions)
      } catch {
        if (!cancelled) setAvailableVersions(['draft'])
      } finally {
        if (!cancelled) setIsLoadingVersions(false)
      }
    }

    fetchVersions()
    return () => { cancelled = true }
  }, [targetId, targetType, spaceId])

  // ── Save logic ─────────────────────────────────────────────────────────────
  const buildRequest = (): CreateTriggerRequest => {
    const input_payload = inputPayloadRows.reduce(
      (acc, row) => {
        if (row.key.trim()) acc[row.key.trim()] = row.value
        return acc
      },
      {} as Record<string, unknown>,
    )

    const req: CreateTriggerRequest = {
      space_id: spaceId,
      name: name.trim(),
      description: description.trim() || undefined,
      trigger_type: triggerType,
      target_type: targetType,
      target_id: targetId,
      target_version: targetVersion || 'draft',
        // In edit mode always send the dict (even if empty {}) so the backend
      // "is not None" guard fires and clears the stored payload.
      // In create mode undefined is fine — the backend defaults to null.
      input_payload: Object.keys(input_payload).length > 0 ? input_payload : (isEditMode ? {} : undefined),
    }

    if (triggerType === 'cron') {
      req.cron_config = { cron_expr: cronExpr }
    } else if (triggerType === 'webhook') {
      req.webhook_config = { webhook_secret: webhookSecret || undefined }
    } else if (triggerType === 'polling') {
      req.polling_config = { poll_url: pollUrl, poll_interval_seconds: pollIntervalSeconds }
    }

    return req
  }

  const handleSave = async (andActivate = false) => {
    setError(null)
    if (!name.trim()) { setError(t('triggers.messages.saveFailed', 'Name is required')); return }
    if (!targetId) { setError(t('triggers.messages.saveFailed', 'Target is required')); return }

    setSaving(true)
    try {
      let savedId = id
      if (isEditMode) {
        const res = await updateTrigger({ ...buildRequest(), trigger_id: id } as any)
        if (res.code !== 200) throw new Error(res.message)
      } else {
        const res = await createTrigger(buildRequest() as any)
        if (res.code !== 200) throw new Error(res.message)
        savedId = (res.data as any)?.trigger_id
      }

      if (andActivate && savedId) {
        await TriggerService.activateTrigger({ space_id: spaceId, trigger_id: savedId })
      }

      navigate('/dashboard/triggers')
    } catch (err: any) {
      setError(err.message || t('triggers.messages.saveFailed', 'Failed to save trigger'))
    } finally {
      setSaving(false)
    }
  }

  // ── Input payload rows ─────────────────────────────────────────────────────
  const addPayloadRow = () => setInputPayloadRows(prev => [...prev, { key: '', value: '' }])
  const removePayloadRow = (idx: number) =>
    setInputPayloadRows(prev => prev.filter((_, i) => i !== idx))
  const updatePayloadRow = (idx: number, field: 'key' | 'value', value: string) =>
    setInputPayloadRows(prev => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)))

  if (isEditMode && isLoadingDetail) {
    return (
      <div className="flex justify-center py-16">
        <CircularProgress />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <IconButton onClick={() => navigate('/dashboard/triggers')} size="small">
          <ArrowLeft size={18} />
        </IconButton>
        <Typography variant="h5" fontWeight="bold">
          {isEditMode ? trigger?.name || 'Edit Trigger' : t('triggers.create', 'New Trigger')}
        </Typography>
      </div>

      {error && <Alert severity="error">{error}</Alert>}

      {/* Section 1: General */}
      <Paper variant="outlined" className="p-5 space-y-4">
        <Typography variant="subtitle1" fontWeight="medium">General</Typography>
        <TextField
          fullWidth
          label={t('triggers.form.name', 'Name')}
          value={name}
          onChange={e => setName(e.target.value)}
          required
          size="small"
        />
        <TextField
          fullWidth
          label={t('triggers.form.description', 'Description')}
          value={description}
          onChange={e => setDescription(e.target.value)}
          multiline
          rows={2}
          size="small"
        />

        <Divider />

        {/* Target Type */}
        <FormControl>
          <FormLabel>{t('triggers.form.targetType', 'Target Type')}</FormLabel>
          <RadioGroup
            row
            value={targetType}
            onChange={e => { setTargetType(e.target.value as TargetType); setTargetId(''); setTargetVersion('draft') }}
          >
            <FormControlLabel value="agent" control={<Radio />} label="Agent" />
            <FormControlLabel value="workflow" control={<Radio />} label="Workflow" />
          </RadioGroup>
        </FormControl>

        {/* Target */}
        <FormControl fullWidth size="small">
          <InputLabel>{t('triggers.form.target', 'Target')}</InputLabel>
          <Select
            value={targetId}
            onChange={e => { setTargetId(e.target.value); setTargetVersion('draft') }}
            label={t('triggers.form.target', 'Target')}
          >
            {targetList.map((item: any) => (
              <MenuItem key={item[targetIdField]} value={item[targetIdField]}>
                {item[targetNameField] || item[targetIdField]}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl fullWidth size="small" disabled={!targetId || isLoadingVersions}>
          <InputLabel>{t('triggers.form.targetVersion', 'Version')}</InputLabel>
          <Select
            value={availableVersions.includes(targetVersion) ? targetVersion : (targetVersion || 'draft')}
            onChange={e => setTargetVersion(e.target.value)}
            label={t('triggers.form.targetVersion', 'Version')}
          >
            {/* Ensure the currently-saved version always appears even if not in the fetched list */}
            {targetVersion && !availableVersions.includes(targetVersion) && (
              <MenuItem value={targetVersion}>{targetVersion}</MenuItem>
            )}
            {availableVersions.map(v => (
              <MenuItem key={v} value={v}>{v}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Input Payload */}
        <div>
          <Typography variant="subtitle2" className="mb-2">
            {t('triggers.form.inputPayload', 'Input Payload')}
          </Typography>
          <div className="space-y-2">
            {inputPayloadRows.map((row, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <TextField
                  size="small"
                  placeholder="Key"
                  value={row.key}
                  onChange={e => updatePayloadRow(idx, 'key', e.target.value)}
                  sx={{ flex: 1 }}
                />
                <TextField
                  size="small"
                  placeholder="Value"
                  value={row.value}
                  onChange={e => updatePayloadRow(idx, 'value', e.target.value)}
                  sx={{ flex: 1 }}
                />
                <IconButton size="small" onClick={() => removePayloadRow(idx)}>
                  <Trash2 size={14} />
                </IconButton>
              </div>
            ))}
            <Button
              size="small"
              startIcon={<Plus size={14} />}
              onClick={addPayloadRow}
              variant="outlined"
            >
              {t('triggers.form.addInputRow', 'Add Input')}
            </Button>
          </div>
        </div>
      </Paper>

      {/* Section 2: Trigger Configuration */}
      <Paper variant="outlined" className="p-5 space-y-4">
        <Typography variant="subtitle1" fontWeight="medium">
          {t('triggers.form.triggerType', 'Trigger Configuration')}
        </Typography>

        {/* Type selector — only changeable on create */}
        {!isEditMode && (
          <Tabs
            value={triggerType}
            onChange={(_, v) => setTriggerType(v as TriggerType)}
            variant="scrollable"
          >
            <Tab value="cron" label={t('triggers.types.cron', 'Cron')} />
            <Tab value="webhook" label={t('triggers.types.webhook', 'Webhook')} />
            <Tab value="polling" label={t('triggers.types.polling', 'Polling')} />
          </Tabs>
        )}

        {isEditMode && (
          <Chip label={t(`triggers.types.${triggerType}`, triggerType)} variant="outlined" />
        )}

        <div className="mt-2">
          {triggerType === 'cron' && (
            <CronConfigForm value={cronExpr} onChange={setCronExpr} />
          )}
          {triggerType === 'webhook' && (
            <WebhookConfigForm
              webhookToken={trigger?.webhook_token || null}
              webhookSecret={webhookSecret}
              onSecretChange={setWebhookSecret}
            />
          )}
          {triggerType === 'polling' && (
            <PollingConfigForm
              pollUrl={pollUrl}
              pollIntervalSeconds={pollIntervalSeconds}
              lastCheckedAt={(trigger?.config as any)?.last_checked_at}
              lastSeenHash={(trigger?.config as any)?.last_seen_hash}
              onUrlChange={setPollUrl}
              onIntervalChange={setPollIntervalSeconds}
            />
          )}
        </div>
      </Paper>

      {/* Section 3: Execution History (edit mode only) */}
      {isEditMode && id && (
        <Paper variant="outlined" className="p-5">
          <TriggerExecutionHistory spaceId={spaceId} triggerId={id} />
        </Paper>
      )}

      {/* Save buttons */}
      <div className="flex gap-3 justify-end">
        <Button variant="outlined" onClick={() => navigate('/dashboard/triggers')} disabled={saving}>
          Cancel
        </Button>
        <Button variant="outlined" onClick={() => handleSave(false)} disabled={saving}>
          {saving ? <CircularProgress size={16} /> : t('triggers.form.save', 'Save')}
        </Button>
        <Button variant="contained" onClick={() => handleSave(true)} disabled={saving}>
          {saving ? <CircularProgress size={16} /> : t('triggers.form.saveAndActivate', 'Save & Activate')}
        </Button>
      </div>
    </div>
  )
}

export default TriggerFormPage
