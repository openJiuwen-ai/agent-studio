/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useState, useEffect, useMemo, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { RelatedMemberService, MemberType, type RelatedMemberInfo, PromptService, FeedbackOptService } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { ENV_CONFIG } from '@/config/environment'
import {
  getVersionOptions,
  mergeCurrentVersionOption,
  fetchPromptText,
  compareVersions,
  incrementVersion,
  isVersionFormatValid,
} from '@/components/Agent/helper/promptHelpers'
import UnifiedSnackbar, { SnackbarMessage } from '@/Common/UnifiedSnackbar'
import { useWorkflowCanvasData } from './use-workflow-data'
import { t } from '../i18n'

export interface UseWorkflowNodePromptOptions {
  nodeId: string
  nodeName?: string
  systemPrompt: string
  onSystemPromptChange: (value: string) => void
  readonly?: boolean
  modelInfo?: any
}

export function useWorkflowNodePrompt({ nodeId, nodeName, systemPrompt, onSystemPromptChange, readonly = false, modelInfo }: UseWorkflowNodePromptOptions) {
  const { user } = useAuthStore()
  const { id: workflowId } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const spaceId = searchParams.get('spaceId') || user?.spaceId || getDefaultSpaceId() || ENV_CONFIG.DEFAULT_SPACE_ID

  const { canvasData, isLoading: canvasDataLoading } = useWorkflowCanvasData(workflowId, spaceId)
  const workflowName = useMemo(() => {
    if (canvasDataLoading) {
      return ''
    }
    if (!canvasData) {
      return ''
    }
    const name = canvasData.name
    if (name && typeof name === 'string' && name.trim()) {
      return name.trim()
    }
    return canvasData.workflow_name || canvasData.display_name || ''
  }, [canvasData, canvasDataLoading])

  const [associateDialogOpen, setAssociateDialogOpen] = useState(false)
  const handleOpenAssociateDialog = () => setAssociateDialogOpen(true)
  const handleCloseAssociateDialog = () => setAssociateDialogOpen(false)

  const [currentRelation, setCurrentRelation] = useState<{ promptId: string; promptVersion: string; promptName: string } | null>(null)
  const [versionLoading, setVersionLoading] = useState(false)
  const [versionOptions, setVersionOptions] = useState<{ id: string; version: string }[]>([])
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  const safeSelectedVersion = useMemo(() => (versionOptions.some(v => v.version === selectedVersion) ? selectedVersion : ''), [selectedVersion, versionOptions])

  const latestVersion = useMemo<string | undefined>(() => {
    if (!versionOptions || versionOptions.length === 0) return undefined
    return versionOptions.map(v => v.version).reduce((acc, cur) => (compareVersions(acc, cur) >= 0 ? acc : cur))
  }, [versionOptions])

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

  const userId = useMemo(() => user?.id || ENV_CONFIG.DEFAULT_USER_ID, [user])

  const nodeInfoMemo = useMemo(() => {
    let finalName = workflowName

    if (!finalName) {
      if (canvasDataLoading) {
        finalName = workflowId || nodeId
      } else if (!canvasData) {
        finalName = workflowId || nodeId
      } else {
        finalName = workflowId || nodeId
      }
    }

    return {
      id: workflowId && nodeId ? `${workflowId}&${nodeId}` : nodeId,
      version: 'draft',
      name: finalName,
      type: MemberType.WORKFLOW,
    }
  }, [workflowId, nodeId, workflowName, canvasDataLoading, canvasData])

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[useWorkflowNodePrompt] Debug info:', {
        workflowId,
        spaceId,
        canvasDataLoading,
        canvasData: canvasData
          ? {
              name: canvasData.name,
              workflow_name: canvasData.workflow_name,
              display_name: canvasData.display_name,
              workflow_id: canvasData.workflow_id,
              keys: Object.keys(canvasData),
            }
          : null,
        workflowName,
        nodeInfoMemo,
      })
    }
  }, [workflowId, spaceId, canvasData, canvasDataLoading, workflowName, nodeInfoMemo])

  const makePromptInfo = (id: string, version: string, name: string) => ({
    id,
    version,
    name,
    type: MemberType.PROMPT,
  })

  const fetchCurrentRelation = async () => {
    if (!nodeId) return
    try {
      const resp: any = await RelatedMemberService.getPromptRelations(spaceId, nodeInfoMemo, true)
      const list = resp?.data || []
      if (Array.isArray(list) && list.length > 0) {
        const r = list[0]
        setCurrentRelation({ promptId: String(r.prompt_id), promptVersion: String(r.prompt_version || 'draft'), promptName: r.prompt_name || '' })
      } else {
        setCurrentRelation(null)
      }
    } catch (e) {
      setCurrentRelation(null)
    }
  }

  const loadVersionListForCurrentRelation = async () => {
    const pid = currentRelation?.promptId
    if (!pid) {
      setVersionOptions([])
      return
    }
    setVersionLoading(true)
    try {
      const options = await getVersionOptions(pid)
      const merged = mergeCurrentVersionOption(options, pid, currentRelation?.promptVersion)
      setVersionOptions(merged)
    } catch (e) {
      setVersionOptions([])
    } finally {
      setVersionLoading(false)
    }
  }

  const loadPromptContentByVersion = async (promptId: string, commitVersion: string) => {
    try {
      const text = await fetchPromptText(promptId, commitVersion, spaceId, { includeDraft: true, withDefaultConfig: false })
      if (text) {
        onSystemPromptChange(text)
      }
    } catch (e) {}
  }

  useEffect(() => {
    fetchCurrentRelation()
  }, [nodeId])

  useEffect(() => {
    if (!associateDialogOpen) {
      fetchCurrentRelation()
    }
  }, [associateDialogOpen])

  useEffect(() => {
    setSelectedVersion(currentRelation?.promptVersion || '')
    loadVersionListForCurrentRelation()
  }, [currentRelation?.promptId])

  const handleUnlinkRelation = async () => {
    try {
      await RelatedMemberService.deletePromptRelation(spaceId, nodeInfoMemo)
      setCurrentRelation(null)
    } catch (e) {}
  }

  const handleVersionSelectChange = async (nextVersion: string) => {
    setSelectedVersion(nextVersion)
    if (!currentRelation) return
    try {
      const promptInfo = makePromptInfo(currentRelation.promptId, nextVersion, currentRelation.promptName || '')
      await RelatedMemberService.registerPromptRelation(spaceId, promptInfo, nodeInfoMemo)
      setCurrentRelation(prev => (prev ? { ...prev, promptVersion: nextVersion } : prev))
      await loadPromptContentByVersion(currentRelation.promptId, nextVersion)
    } catch (e) {}
  }

  const handleRelationUpdated = (info: { promptId: string; promptName: string; promptVersion: string; promptContent: string }) => {
    setCurrentRelation({ promptId: info.promptId, promptName: info.promptName, promptVersion: info.promptVersion })
    setSelectedVersion(info.promptVersion)
    onSystemPromptChange(info.promptContent)
  }

  const handleReplacePromptText = (text: string) => {
    onSystemPromptChange(text)
    setAssociateDialogOpen(false)
  }

  const handleInsertPromptText = (text: string) => {
    if (readonly) return
    const existing = systemPrompt || ''
    const combined = existing ? `${existing}\n${text}` : text
    onSystemPromptChange(combined)
    setAssociateDialogOpen(false)
  }

  const handleQuickOptimizeGenerate = async () => {
    if (readonly) return
    const content = (systemPrompt || '').trim()
    if (!content) {
      setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.systemPromptEmpty') })
      return
    }

    quickOptimizeAbortRef.current?.abort()
    quickOptimizeAbortRef.current = null
    setIsGenerating(true)
    quickOptimizeStreamingRef.current = ''
    setCandidatePrompt('')
    setDisplayOverride('')

    const quickOptimizeRequest = {
      modelInfo: modelInfo || {
        id: 0,
        model: '',
        model_from: 'db',
        headers: {
          temperature: 0.7,
          max_tokens: 4000,
          top_p: 0.9,
        },
      },
      instruct: content,
      stream: true,
    }

    try {
      quickOptimizeAbortRef.current = new AbortController()
      await FeedbackOptService.quickOptimize(
        quickOptimizeRequest,
        (data: string) => {
          quickOptimizeStreamingRef.current += data
          setDisplayOverride(quickOptimizeStreamingRef.current)
        },
        (error: string) => {
          setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.generateFailed', { error }) })
          setIsGenerating(false)
          setDisplayOverride(null)
          quickOptimizeAbortRef.current = null
        },
        () => {
          setIsGenerating(false)
          setCandidatePrompt(quickOptimizeStreamingRef.current)
          setSnackbar({ open: true, severity: 'success', message: t('workflowCanvas.nodePrompt.generateCompleted') })
          setDisplayOverride(quickOptimizeStreamingRef.current)
          quickOptimizeAbortRef.current = null
        },
        quickOptimizeAbortRef.current,
      )
    } catch (e: any) {
      const msg = typeof e?.message === 'string' ? e.message : t('workflowCanvas.nodePrompt.requestFailed')
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
      setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.noContentToAdopt') })
      return
    }
    onSystemPromptChange(text)
    setCandidatePrompt('')
    quickOptimizeStreamingRef.current = ''
    setDisplayOverride(null)
    setSnackbar({ open: true, severity: 'success', message: t('workflowCanvas.nodePrompt.adoptedGenerated') })
  }

  const handleCancelCandidate = () => {
    quickOptimizeAbortRef.current?.abort()
    quickOptimizeAbortRef.current = null
    setIsGenerating(false)
    setCandidatePrompt('')
    quickOptimizeStreamingRef.current = ''
    setDisplayOverride(null)
    setSnackbar({ open: true, severity: 'success', message: t('workflowCanvas.nodePrompt.canceled') })
  }

  const handleOpenSaveDialog = async () => {
    const content = (systemPrompt || '').trim()
    if (!content) {
      setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.systemPromptEmpty') })
      return
    }

    try {
      const resp: any = await RelatedMemberService.getPromptRelations(spaceId, nodeInfoMemo, true)
      const list = resp?.data || []
      if (Array.isArray(list) && list.length > 0) {
        const r = list[0]
        const pid = String(r.prompt_id)
        const detail = await PromptService.getPromptDetail(pid, {
          workspaceId: spaceId,
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
        const defaultKey = nodeId ? `workflow_${nodeId}_${Date.now()}` : `workflow_${Date.now()}`
        const defaultName = nodeName || t('workflowCanvas.nodePrompt.unnamedPrompt')
        setExistingPromptInfo(null)
        setSaveForm({
          promptKey: defaultKey,
          promptName: defaultName,
          promptVersion: ENV_CONFIG.DEFAULT_PROMPT_VERSION,
          promptDesc: '',
        })
      }
      setSaveDialogOpen(true)
    } catch (e: any) {
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
        setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.loadFailed') })
      }
    }
  }

  const handleConfirmSave = async () => {
    const { promptKey, promptName, promptVersion, promptDesc } = saveForm
    if (!promptKey.trim() || !promptName.trim() || !promptVersion.trim()) {
      setSnackbar({ open: true, severity: 'error', message: t('workflowCanvas.nodePrompt.requiredFields') })
      return
    }
    setSaving(true)
    try {
      let targetPromptId = existingPromptInfo?.id || ''

      if (!targetPromptId) {
        const createResp = await PromptService.createPrompt({
          updated_by: userId,
          prompt_key: promptKey,
          prompt_name: promptName,
          prompt_description: promptDesc || '',
          workspace_id: spaceId,
        })
        if (createResp.code !== 0 || !createResp.prompt_id) {
          throw new Error(t('workflowCanvas.nodePrompt.createFailed'))
        }
        targetPromptId = String(createResp.prompt_id)
      }

      await PromptService.saveDraft(targetPromptId, userId, spaceId, {
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
          topP: 0.7,
        },
        selectedModel: null,
        templateEngine: 'normal',
        toolsEnabled: false,
        debugMode: false,
        tools: [],
      })

      if (
        !isVersionFormatValid(promptVersion) ||
        (existingPromptInfo?.latestVersion && compareVersions(promptVersion, existingPromptInfo.latestVersion) <= 0)
      ) {
        setSnackbar({
          open: true,
          severity: 'error',
          message: t('workflowCanvas.nodePrompt.versionFormatError', {
            current: existingPromptInfo?.latestVersion ? t('workflowCanvas.nodePrompt.currentVersion', { version: existingPromptInfo.latestVersion }) : '',
          }),
        })
        setSaving(false)
        return
      }
      await PromptService.commitVersion(targetPromptId, userId, {
        commit_version: promptVersion,
        commit_description: promptDesc || t('workflowCanvas.nodePrompt.commitDescription', { nodeName: nodeName || nodeId }),
      })

      const promptInfo: RelatedMemberInfo = {
        id: targetPromptId,
        version: promptVersion,
        name: promptName,
        type: MemberType.PROMPT,
      }
      await RelatedMemberService.registerPromptRelation(spaceId, promptInfo, nodeInfoMemo)

      setCurrentRelation({ promptId: targetPromptId, promptVersion, promptName })
      setSelectedVersion(promptVersion)
      await loadVersionListForCurrentRelation()
      await loadPromptContentByVersion(targetPromptId, promptVersion)

      setSnackbar({ open: true, severity: 'success', message: t('workflowCanvas.nodePrompt.saved') })
      setSaveDialogOpen(false)
    } catch (e: any) {
      const msg = typeof e?.message === 'string' ? e.message : t('workflowCanvas.nodePrompt.saveFailed')
      setSnackbar({ open: true, severity: 'error', message: msg })
    } finally {
      setSaving(false)
    }
  }

  const effectiveText = useMemo(() => displayOverride ?? systemPrompt, [displayOverride, systemPrompt])
  const isLockedForCandidate = useMemo(() => isGenerating || !!candidatePrompt, [isGenerating, candidatePrompt])

  return {
    isGenerating,
    candidatePrompt,
    saving,
    currentRelation,
    safeSelectedVersion,
    selectedVersion,
    latestVersion,
    versionOptions,
    versionLoading,
    effectiveText,
    isLockedForCandidate,
    associateDialogOpen,
    saveDialogOpen,
    overrideDraftDialogOpen,
    unlinkConfirmOpen,
    saveForm,
    existingPromptInfo,
    snackbar,
    handleOpenAssociateDialog,
    handleCloseAssociateDialog,
    handleReplacePromptText,
    handleInsertPromptText,
    handleRelationUpdated,
    handleQuickOptimizeGenerate,
    handleAdoptCandidate,
    handleCancelCandidate,
    handleOpenSaveDialog,
    handleConfirmSave,
    handleVersionSelectChange,
    handleUnlinkRelation,
    setSaveDialogOpen,
    setOverrideDraftDialogOpen,
    setUnlinkConfirmOpen,
    setSaveForm,
    setSnackbar,
    nodeInfo: nodeInfoMemo,
    workspaceId: spaceId,
  }
}
