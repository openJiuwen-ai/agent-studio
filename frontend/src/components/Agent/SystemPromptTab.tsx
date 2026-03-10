import React, { useMemo, useState, useRef, useEffect } from 'react'
import { Paper } from '@mui/material'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'

import { useAgentStore } from '@/stores/useAgentStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { ActionSlotMount } from '@/components/Common/ActionSlot'
import AgentAssociatePromptDialog from '@/components/Agent/AgentAssociatePromptDialog'
import {
  RelatedMemberService,
  MemberType,
  type RelatedMemberInfo,
  PromptService,
  type AgentDetailResponse,
  FeedbackOptService,
} from '@test-agentstudio/api-client'
import { buildModelInfoFromAgent } from '@/utils/prompts/modelInfoBuilder'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { ENV_CONFIG } from '@/config/environment'
import SavePromptDialog from '@/components/Agent/SavePromptDialog'
import OverridePromptTemplateDialog from '@/components/Agent/OverridePromptTemplateDialog'
import { getVersionOptions, mergeCurrentVersionOption, fetchPromptText, compareVersions, incrementVersion } from './helper/promptHelpers'
import { isVersionFormatValid } from './helper/promptHelpers'
import UnifiedSnackbar, { SnackbarMessage } from '@/Common/UnifiedSnackbar'
import { PromptTitleActions } from '@/components/Agent/PromptTitleActions'
import { PromptGenerationBanner } from '@/components/Agent/PromptGenerationBanner'
import { PromptRelationInfoBar } from '@/components/Agent/PromptRelationInfoBar'
import { useScopedTranslation } from '@/i18n'

const PromptEditor: React.FC<{
  textAreaRef: React.RefObject<HTMLTextAreaElement> | React.MutableRefObject<HTMLTextAreaElement | null>
  effectiveText: string
  readonly: boolean
  isLockedForCandidate: boolean
  onChange: (value: string) => void
  placeholder?: string
}> = ({ textAreaRef, effectiveText, readonly, isLockedForCandidate, onChange, placeholder }) => (
  <Paper elevation={0} className="relative flex-1 min-h-0 flex flex-col bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-xl">
    <textarea
      ref={textAreaRef}
      value={effectiveText}
      onChange={e => {
        const newPrompt = e.target.value
        if (readonly || isLockedForCandidate) return
        onChange(newPrompt)
      }}
      placeholder={placeholder}
      className={`h-full w-full p-2 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-600 dark:text-gray-300 border-0 rounded-xl resize-y min-h-[240px] max-h-[80vh] overflow-auto bg-transparent dark:bg-gray-800${readonly || isLockedForCandidate ? ' cursor-not-allowed' : ''}`}
      readOnly={readonly || isLockedForCandidate}
    />
  </Paper>
)
const SystemPromptTab: React.FC<{ agentDetailResponse?: AgentDetailResponse | null }> = ({ agentDetailResponse }) => {
  const { t } = useScopedTranslation('agents.agentEditor.systemPrompt')
  const { saveAgentRequest, updateSaveAgentRequest } = useAgentStore()
  const readonly = useAgentStore(s => s.readonly)
  const { user } = useAuthStore()

  // Dialog open state for associating prompts
  const [associateDialogOpen, setAssociateDialogOpen] = useState(false)

  const handleOpenAssociateDialog = () => setAssociateDialogOpen(true)
  const handleCloseAssociateDialog = () => setAssociateDialogOpen(false)

  const textAreaRef = useRef<HTMLTextAreaElement>(null)

  // Currently associated prompt and version info
  const [currentRelation, setCurrentRelation] = useState<{ promptId: string; promptVersion: string; promptName: string } | null>(null)
  // Version dropdown related state
  const [versionLoading, setVersionLoading] = useState(false)
  const [versionOptions, setVersionOptions] = useState<{ id: string; version: string }[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  // Fallback to empty when selected version is not in options to avoid MUI Select warnings
  const safeSelectedVersion = useMemo(() => (versionOptions.some(v => v.version === selectedVersion) ? selectedVersion : ''), [selectedVersion, versionOptions])

  // Compute latest version using helper compareVersions
  const latestVersion = useMemo<string | undefined>(() => {
    if (!versionOptions || versionOptions.length === 0) return undefined
    return versionOptions.map(v => v.version).reduce((acc, cur) => (compareVersions(acc, cur) >= 0 ? acc : cur))
  }, [versionOptions])

  // Save prompt related state
  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [overrideDraftDialogOpen, setOverrideDraftDialogOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveForm, setSaveForm] = useState<{ promptKey: string; promptName: string; promptVersion: string; promptDesc: string }>({
    promptKey: '',
    promptName: '',
    promptVersion: ENV_CONFIG.DEFAULT_PROMPT_VERSION,
    promptDesc: '',
  })
  const [existingPromptInfo, setExistingPromptInfo] = useState<{ id: string; latestVersion: string } | null>(null)
  const [snackbar, setSnackbar] = useState<SnackbarMessage>({ open: false, severity: 'success', message: '', duration: 3000 })

  const [isGenerating, setIsGenerating] = useState(false)
  const quickOptimizeStreamingRef = useRef<string>('')
  const [candidatePrompt, setCandidatePrompt] = useState<string>('')
  const [displayOverride, setDisplayOverride] = useState<string | null>(null)
  const quickOptimizeAbortRef = useRef<AbortController | null>(null)

  const [unlinkConfirmOpen, setUnlinkConfirmOpen] = useState(false)

  const agentId = useMemo(() => saveAgentRequest?.agent_id || '', [saveAgentRequest])
  const agentName = useMemo(() => saveAgentRequest?.name || '', [saveAgentRequest])
  const agentVersion = useMemo(() => saveAgentRequest?.agent_version || 'draft', [saveAgentRequest])

  const workspaceId = useMemo(() => user?.spaceId || getDefaultSpaceId(), [user])
  const userId = useMemo(() => user?.id || ENV_CONFIG.DEFAULT_USER_ID, [user])

  const agentInfoMemo = {
    id: agentId,
    version: agentVersion,
    name: agentName,
    type: MemberType.AGENT,
  }

  const makePromptInfo = (id: string, version: string, name: string) => ({
    id,
    version,
    name,
    type: MemberType.PROMPT,
  })

  const setSystemPrompt = (text: string) => {
    const currentConfigs = saveAgentRequest?.configs || {}
    updateSaveAgentRequest({ configs: { ...currentConfigs, system_prompt: text } })
  }

  const fetchCurrentRelation = async () => {
    const spaceId = workspaceId
    if (!agentId) return
    const agentInfo: RelatedMemberInfo = {
      id: agentId,
      version: agentVersion,
      name: agentName,
      type: MemberType.AGENT,
    }
    try {
      const resp = await RelatedMemberService.getPromptRelations(spaceId, agentInfo, true)
      const list = resp?.data || []
      if (Array.isArray(list) && list.length > 0) {
        const r = list[0]
        setCurrentRelation({ promptId: String(r.prompt_id), promptVersion: String(r.prompt_version || 'draft'), promptName: r.prompt_name || '' })
      } else {
        setCurrentRelation(null)
      }
    } catch (e) {
      // Fetch failure does not block main flow
      setCurrentRelation(null)
    }
  }

  // Load version list for the currently associated prompt
  const loadVersionListForCurrentRelation = async () => {
    const pid = currentRelation?.promptId
    if (!pid) {
      setVersionOptions([])
      return
    }
    setVersionLoading(true)
    try {
      const options = await getVersionOptions(pid, workspaceId)
      const merged = mergeCurrentVersionOption(options, pid, currentRelation?.promptVersion)
      setVersionOptions(merged)
    } catch (e) {
      setVersionOptions([])
    } finally {
      setVersionLoading(false)
    }
  }

  // Load prompt content by selected version and update editor
  const loadPromptContentByVersion = async (promptId: string, commitVersion: string) => {
    const spaceId = workspaceId
    try {
      const text = await fetchPromptText(promptId, commitVersion, spaceId, { includeDraft: true, withDefaultConfig: false })
      if (text) {
        setSystemPrompt(text)
      }
    } catch (e) {
      // Fetch failure does not block
    }
  }

  useEffect(() => {
    fetchCurrentRelation()
  }, [agentId, agentVersion])

  useEffect(() => {
    if (!associateDialogOpen) {
      // After dialog closes, reload to get latest relation info (replacement registers relation)
      fetchCurrentRelation()
    }
  }, [associateDialogOpen])

  // When relation changes, sync selected version and reload version list
  useEffect(() => {
    setSelectedVersion(currentRelation?.promptVersion || '')
    loadVersionListForCurrentRelation()
  }, [currentRelation?.promptId])

  const handleUnlinkRelation = async () => {
    const spaceId = workspaceId
    const agentInfo = agentInfoMemo
    try {
      await RelatedMemberService.deletePromptRelation(spaceId, agentInfo)
      setCurrentRelation(null)
    } catch (e) {
      // Unlink failure does not block
    }
  }

  // When selecting a different version, update relation version
  const handleVersionSelectChange = async (nextVersion: string) => {
    setSelectedVersion(nextVersion)
    if (!currentRelation) return
    try {
      const spaceId = workspaceId
      const promptInfo = makePromptInfo(currentRelation.promptId, nextVersion, currentRelation.promptName || '')
      const relatedMemberInfo = agentInfoMemo
      await RelatedMemberService.registerPromptRelation(spaceId, promptInfo, relatedMemberInfo)
      setCurrentRelation(prev => (prev ? { ...prev, promptVersion: nextVersion } : prev))
      // After switching version, load corresponding content into editor
      await loadPromptContentByVersion(currentRelation.promptId, nextVersion)
    } catch (e) {
      // Update failure does not block main flow
    }
  }

  // Handle association updates from dialog (optimistic refresh)
  const handleRelationUpdated = (info: { promptId: string; promptName: string; promptVersion: string; promptContent: string }) => {
    setCurrentRelation({ promptId: info.promptId, promptName: info.promptName, promptVersion: info.promptVersion })
    setSelectedVersion(info.promptVersion)
    // Sync editor content so version and content are updated together
    setSystemPrompt(info.promptContent)
  }

  // Replace system prompt text with selected template content
  const handleReplacePromptText = (text: string) => {
    setSystemPrompt(text)
    setAssociateDialogOpen(false)
  }

  // Insert system prompt text at current cursor position (separated by a blank line if needed)
  const handleInsertPromptText = (text: string) => {
    if (readonly) return
    const existing = typeof saveAgentRequest?.configs?.system_prompt === 'string' ? saveAgentRequest?.configs?.system_prompt : ''

    const ta = textAreaRef.current
    const start = ta?.selectionStart ?? existing.length
    const end = ta?.selectionEnd ?? start

    const before = existing.slice(0, start)
    const after = existing.slice(end)
    // If there is existing content and no newline before, prepend a line break to avoid sticking
    const needsLeadingBreak = before && !/\n$/.test(before)
    const insertText = needsLeadingBreak ? `\n${text}` : text
    const combined = `${before}${insertText}${after}`

    setSystemPrompt(combined)
    setAssociateDialogOpen(false)

    // Restore caret to the end of inserted text
    requestAnimationFrame(() => {
      const ref = textAreaRef.current
      if (ref) {
        const pos = before.length + insertText.length
        ref.focus()
        ref.setSelectionRange(pos, pos)
      }
    })
  }

  // Derive system prompt from store
  const systemPrompt = useMemo<string>(() => {
    const sp = saveAgentRequest?.configs?.system_prompt
    return typeof sp === 'string' ? sp : ''
  }, [saveAgentRequest])

  const displayedSystemPrompt = useMemo<string>(() => {
    if (readonly) {
      const hist = agentDetailResponse?.data?.agent_info?.configs?.['system_prompt']
      return typeof hist === 'string' ? hist : ''
    }
    return systemPrompt
  }, [readonly, agentDetailResponse, systemPrompt])

  const effectiveText = useMemo(() => displayOverride ?? displayedSystemPrompt, [displayOverride, displayedSystemPrompt])

  const isLockedForCandidate = useMemo(() => isGenerating || !!candidatePrompt, [isGenerating, candidatePrompt])

  const handleQuickOptimizeGenerate = async () => {
    if (readonly) return
    const content = (systemPrompt || '').trim()
    if (!content) {
      setSnackbar({ open: true, severity: 'error', message: t('messages.emptySystemPrompt') })
      return
    }

    quickOptimizeAbortRef.current?.abort()
    quickOptimizeAbortRef.current = null
    setIsGenerating(true)
    quickOptimizeStreamingRef.current = ''
    setCandidatePrompt('')
    setDisplayOverride('')

    // 优先从 store 中读取当前模型的 model_id（由 AgentModelSelector 维护）
    const storeModelId = saveAgentRequest?.model?.model_info?.model_id

    // 如果 store 中没有，则从 agentDetail 的 model_list 中按名称匹配一次作为兜底
    let modelId = storeModelId
    if (modelId === undefined || modelId === null) {
      const modelList = agentDetailResponse?.data?.agent_option_info?.model_list || []
      const currentModelName = saveAgentRequest.model?.model_info?.model_name || ''
      const matchedModel = modelList.find((model: any) => model.model_name === currentModelName)
      modelId = matchedModel?.model_id

      if (modelId === undefined || modelId === null) {
        console.warn(
          '⚠️ [SystemPromptTab] No matching model ID found for quick optimize.',
          'Current model name:',
          currentModelName,
          'storeModelId:',
          storeModelId,
          'model list:',
          modelList,
        )
        setSnackbar({ open: true, severity: 'warning', message: t('messages.modelIdNotFound') })
      } else {
        console.log('✅ [SystemPromptTab] Found matching model ID from detail:', modelId, 'model name:', currentModelName)
      }
    } else {
      console.log('✅ [SystemPromptTab] Using model_id from store for quick optimize:', storeModelId)
    }

    // Convert AgentModelInfo to QuickOptimizeModelInfo format（始终传入最终的 modelId，避免为 0）
    const modelInfo = buildModelInfoFromAgent(saveAgentRequest.model, modelId ?? undefined)

    const quickOptimizeRequest = {
      modelInfo,
      instruct: content,
      stream: true,
    }

    try {
      quickOptimizeAbortRef.current = new AbortController()
      await FeedbackOptService.quickOptimize(
        quickOptimizeRequest,
        workspaceId,
        (data: string) => {
          quickOptimizeStreamingRef.current += data
          setDisplayOverride(quickOptimizeStreamingRef.current)
        },
        (error: string) => {
          setSnackbar({ open: true, severity: 'error', message: t('messages.generateFailedWithError', { error }) })
          setIsGenerating(false)
          setDisplayOverride(null)
          quickOptimizeAbortRef.current = null
        },
        () => {
          setIsGenerating(false)
          setCandidatePrompt(quickOptimizeStreamingRef.current)
          setSnackbar({ open: true, severity: 'success', message: t('messages.generateComplete') })
          setDisplayOverride(quickOptimizeStreamingRef.current)
          quickOptimizeAbortRef.current = null
        },
        quickOptimizeAbortRef.current,
      )
    } catch (e: unknown) {
      const fallbackMsg = t('messages.generateRequestFailed')
      const msgFromError = (e as any)?.message
      const msg = typeof msgFromError === 'string' ? msgFromError : fallbackMsg
      setSnackbar({ open: true, severity: 'error', message: msg })
      setIsGenerating(false)
      setDisplayOverride(null)
      quickOptimizeAbortRef.current = null
    }
  }

  const handleAdoptCandidate = () => {
    if (readonly) return
    const text = candidatePrompt || quickOptimizeStreamingRef.current || ''
    if (!text.trim()) {
      setSnackbar({ open: true, severity: 'error', message: t('messages.noAdoptableContent') })
      return
    }
    setSystemPrompt(text)
    setCandidatePrompt('')
    quickOptimizeStreamingRef.current = ''
    setDisplayOverride(null)
    setSnackbar({ open: true, severity: 'success', message: t('messages.adopted') })
  }

  const handleCancelCandidate = () => {
    quickOptimizeAbortRef.current?.abort()
    quickOptimizeAbortRef.current = null
    setIsGenerating(false)
    setCandidatePrompt('')
    quickOptimizeStreamingRef.current = ''
    setDisplayOverride(null)
    setSnackbar({ open: true, severity: 'success', message: t('messages.cancelled') })
  }

  // Open save prompt dialog and prefill information
  const handleOpenSaveDialog = async () => {
    const content = (systemPrompt || '').trim()
    if (!content) {
      setSnackbar({ open: true, severity: 'error', message: t('messages.emptySystemPromptCannotSave') })
      return
    }

    try {
      // Check if there is already an associated prompt
      const agentInfo: RelatedMemberInfo = {
        id: agentId,
        version: agentVersion,
        name: agentName,
        type: MemberType.AGENT,
      }
      const resp = await RelatedMemberService.getPromptRelations(workspaceId, agentInfo, true)
      const list = resp?.data || []
      if (Array.isArray(list) && list.length > 0) {
        const r = list[0]
        const pid = String(r.prompt_id)
        const detail = await PromptService.getPromptDetail(pid, {
          workspaceId,
          withCommit: false,
          withDraft: false,
          withDefaultConfig: false,
        })
        const promptBasic = detail?.prompt?.[0]?.prompt_basic
        const latest = promptBasic?.latest_version || ENV_CONFIG.DEFAULT_PROMPT_VERSION
        const key = detail?.prompt?.[0]?.prompt_key || ''
        const name = promptBasic?.display_name || r.prompt_name || ''
        setExistingPromptInfo({ id: pid, latestVersion: latest })
        setSaveForm({
          promptKey: key,
          promptName: name,
          promptVersion: incrementVersion(latest, ENV_CONFIG.DEFAULT_PROMPT_VERSION),
          promptDesc: '',
        })
      } else {
        // Default values based on agent info
        const defaultKey = `agent_${Date.now()}`
        const defaultName = agentName || t('defaults.unnamedPrompt')
        setExistingPromptInfo(null)
        setSaveForm({
          promptKey: defaultKey,
          promptName: defaultName,
          promptVersion: ENV_CONFIG.DEFAULT_PROMPT_VERSION,
          promptDesc: '',
        })
      }
      setSaveDialogOpen(true)
    } catch (e: unknown) {
      // If 404, treat as no relation and go through create flow
      const status = e?.status ?? e?.response?.status
      if (status === 404) {
        setExistingPromptInfo(null)
        setSaveForm({
          promptKey: '',
          promptName: '',
          promptVersion: ENV_CONFIG.DEFAULT_PROMPT_VERSION,
          promptDesc: '',
        })
        setSaveDialogOpen(true)
      } else {
        setSnackbar({ open: true, severity: 'error', message: t('messages.prefillFailed') })
      }
    }
  }

  const handleConfirmSave = async () => {
    const { promptKey, promptName, promptVersion, promptDesc } = saveForm
    if (!promptKey.trim() || !promptName.trim() || !promptVersion.trim()) {
      setSnackbar({ open: true, severity: 'error', message: t('messages.fillKeyNameVersion') })
      return
    }
    setSaving(true)
    try {
      let targetPromptId = existingPromptInfo?.id || ''

      // 1) If no relation, create prompt first
      if (!targetPromptId) {
        const createResp = await PromptService.createPrompt({
          updated_by: userId,
          prompt_key: promptKey,
          prompt_name: promptName,
          prompt_description: promptDesc || '',
          workspace_id: workspaceId,
        })
        if (createResp.code !== 0 || !createResp.prompt_id) {
          throw new Error(t('messages.createPromptFailed'))
        }
        targetPromptId = String(createResp.prompt_id)
      } else {
        // Existing prompt: optional basic info update
        // Intentionally keep name/description unchanged; enable this if needed:
        // await PromptService.editPromptBasicInfo(targetPromptId, { prompt_name: promptName, prompt_description: promptDesc || '' })
      }

      // 2) Save draft (system prompt)
      await PromptService.saveDraft(targetPromptId, workspaceId, {
        promptMessages: [
          {
            id: 'system-msg-1',
            role: 'system',
            content: systemPrompt,
            placeholderName: undefined,
          },
        ],
        parameters: [],
        modelConfig: {
          model: '1',
          temperature: 0.7,
          maxTokens: 2048,
          top_p: 0.7,
        },
        selectedModel: null,
        templateEngine: 'normal',
        toolsEnabled: false,
        debugMode: false,
        tools: [],
      })

      // 3) Commit version
      // Before commit: version must be x.x.x and greater than current latest
      if (
        !isVersionFormatValid(promptVersion) ||
        (existingPromptInfo?.latestVersion && compareVersions(promptVersion, existingPromptInfo.latestVersion) <= 0)
      ) {
        setSnackbar({
          open: true,
          severity: 'error',
          message: t('messages.versionFormatAndGreaterError'),
        })
        setSaving(false)
        return
      }
      await PromptService.commitVersion(targetPromptId, workspaceId, {
        commit_version: promptVersion,
        commit_description: promptDesc || t('messages.commitDescriptionFallback', { agentName: agentName || agentId }),
      })

      // 4) Register relation (Prompt -> Agent) so the relation points to newest version
      const promptInfo: RelatedMemberInfo = {
        id: targetPromptId,
        version: promptVersion,
        name: promptName,
        type: MemberType.PROMPT,
      }
      const relatedMemberInfo: RelatedMemberInfo = {
        id: agentId,
        version: agentVersion,
        name: agentName,
        type: MemberType.AGENT,
      }
      await RelatedMemberService.registerPromptRelation(workspaceId, promptInfo, relatedMemberInfo)

      // 5) Refresh local relation and version list, and update editor content
      setCurrentRelation({ promptId: targetPromptId, promptVersion, promptName })
      setSelectedVersion(promptVersion)
      await loadVersionListForCurrentRelation()
      await loadPromptContentByVersion(targetPromptId, promptVersion)

      setSnackbar({ open: true, severity: 'success', message: t('messages.savedAndCommitted') })
      setSaveDialogOpen(false)
    } catch (e: unknown) {
      const msgFromError = (e as any)?.message
      const msg = typeof msgFromError === 'string' ? msgFromError : t('messages.savePromptFailed')
      setSnackbar({ open: true, severity: 'error', message: msg })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-3">
      <ActionSlotMount name="system-title-actions">
        <PromptTitleActions
          readonly={readonly}
          isGenerating={isGenerating}
          candidatePrompt={candidatePrompt}
          saving={saving}
          systemPrompt={systemPrompt}
          onOptimize={handleQuickOptimizeGenerate}
          onAssociate={handleOpenAssociateDialog}
          onSave={handleOpenSaveDialog}
        />
      </ActionSlotMount>

      <PromptGenerationBanner
        isGenerating={isGenerating}
        candidatePrompt={candidatePrompt}
        readonly={readonly}
        onCancel={handleCancelCandidate}
        onAdopt={handleAdoptCandidate}
      />

      {/* Current associated prompt info and unlink actions (info bar) */}
      <PromptRelationInfoBar
        currentRelation={currentRelation}
        readonly={readonly}
        safeSelectedVersion={safeSelectedVersion}
        selectedVersion={selectedVersion}
        latestVersion={latestVersion}
        versionOptions={versionOptions}
        versionLoading={versionLoading}
        onVersionChange={handleVersionSelectChange}
        onOpenOverrideDialog={() => setOverrideDraftDialogOpen(true)}
        onOpenUnlinkConfirm={() => setUnlinkConfirmOpen(true)}
      />

      {/* Prompt association dialog (standalone component) */}
      <AgentAssociatePromptDialog
        open={associateDialogOpen}
        onClose={handleCloseAssociateDialog}
        onReplace={handleReplacePromptText}
        onInsert={handleInsertPromptText}
        agentInfo={{ agentId, agentName, agentVersion }}
        onRelationUpdated={handleRelationUpdated}
      />

      {/* Save prompt dialog (standalone component) */}
      <SavePromptDialog
        open={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        onConfirm={handleConfirmSave}
        saving={saving}
        existingPromptInfo={existingPromptInfo ?? undefined}
        saveForm={saveForm}
        setSaveForm={setSaveForm}
      />

      <OverridePromptTemplateDialog
        open={overrideDraftDialogOpen}
        onClose={() => setOverrideDraftDialogOpen(false)}
        onJump={() => {
          setOverrideDraftDialogOpen(false)
          const pid = currentRelation?.promptId
          if (pid) {
            const versionParam = selectedVersion || versionOptions[0]?.version || ENV_CONFIG.DEFAULT_PROMPT_VERSION
            window.open(`/dashboard/prompts/${pid}?version=${versionParam}&from=agent`, '_blank')
          }
        }}
        onOverwrite={() => {
          setOverrideDraftDialogOpen(false)
          const overrideData = {
            systemPrompt: systemPrompt || '',
            type: 'System',
            fromAgent: true,
            timestamp: Date.now(),
          }
          try {
            sessionStorage.setItem('promptOverrideData', JSON.stringify(overrideData))
          } catch (err) {
            // noop
          }
          const pid = currentRelation?.promptId
          if (pid) {
            window.open(`/dashboard/prompts/${pid}`, '_blank')
          }
        }}
      />

      <DeleteConfirmationDialog
        isOpen={unlinkConfirmOpen}
        onClose={() => setUnlinkConfirmOpen(false)}
        onConfirm={async () => {
          await handleUnlinkRelation()
          setUnlinkConfirmOpen(false)
        }}
        itemType="agent"
        itemName={agentName || agentId}
        title={t('unlinkDialog.title')}
        message={t('unlinkDialog.message', {
          promptName: currentRelation?.promptName || '',
          version: selectedVersion || currentRelation?.promptVersion || '',
        })}
        confirmButtonText={t('unlinkDialog.confirmButtonText')}
      />

      <PromptEditor
        textAreaRef={textAreaRef}
        effectiveText={effectiveText}
        readonly={readonly}
        isLockedForCandidate={isLockedForCandidate}
        onChange={setSystemPrompt}
        placeholder={t('defineAgentPlaceholder')}
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={() => setSnackbar(s => ({ ...s, open: false }))} />
    </div>
  )
}

export default SystemPromptTab
