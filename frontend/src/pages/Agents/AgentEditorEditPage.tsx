import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { Button, IconButton, Paper, CircularProgress, Divider, Select, MenuItem, SelectChangeEvent } from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { AgentDetailResponse, AgentService, ExecutionService, SaveAgentRequest, useModels } from '@test-agentstudio/api-client'
import i18n, { useScopedTranslation } from '@/i18n'
import { ChevronLeft, Save, History, Brain, Settings, Eye, Clock, Tag } from 'lucide-react'
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import AgentModelSelector from '@/components/Agent/AgentModelSelector'
import MultiWorkflowSelector from '@/components/Agent/MultiWorkflowSelector'
import AgentDebugChat from '@/components/Agent/AgentDebugChat'
import AgentPublishDialog from '@/components/Agent/AgentPublishDialog'
import { useAgentStore } from '@/stores/useAgentStore'
import { useAuthStore } from '@/stores/useAuthStore'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import SystemPromptTab from '@/components/Agent/SystemPromptTab'
import { ActionSlotTarget } from '@/components/Common/ActionSlot'
import AgentVersionListPanel from '@/components/Agent/AgentVersionListPanel'
import AgentSettingsDialog from '@/components/Agent/AgentSettingsDialog'
import type { ModelDetail } from '@/types/agentTypes'

const MIN_LEFT = 15
const MIN_MIDDLE = 20
const MIN_RIGHT = 15

const AgentEditorEditPage = () => {
  const { t } = useScopedTranslation('agents.agentEditor.editPage')
  const [leftPanelWidth, setLeftPanelWidth] = useState(30)
  const [rightPanelWidth, setRightPanelWidth] = useState(30)
  const [isDragging, setIsDragging] = useState(false)
  const [draggingDivider, setDraggingDivider] = useState<null | 'left' | 'right'>(null)
  const dragStartXRef = useRef(0)
  const startLeftRef = useRef(30)
  const startRightRef = useRef(30)
  const draggingDividerRef = useRef<null | 'left' | 'right'>(null)
  const leftPanelWidthRef = useRef(leftPanelWidth)
  const rightPanelWidthRef = useRef(rightPanelWidth)
  // Store original widths for debugging panel toggle
  const prevWidthsRef = useRef<{ left: number; right: number }>({ left: leftPanelWidth, right: rightPanelWidth })
  const containerRef = useRef<HTMLDivElement>(null)
  // Page data processing
  const navigate = useNavigate()
  const { id: agentId } = useParams<{ id: string }>()
  const [agentDetailResponse, setAgentDetailResponse] = useState<AgentDetailResponse>()
  const [loading, setLoading] = useState(true)
  const { saveAgentRequest, setSaveAgentRequest, updateSaveAgentRequest, saveAgent, isSaving, saveError, setReadonly } = useAgentStore()
  const lastAutoSaveTime = useAgentStore(s => s.lastAutoSaveTime)
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()
  const { user } = useAuthStore()
  const [historyAgentDetailResponse, setHistoryAgentDetailResponse] = useState<AgentDetailResponse | null>(null)

  // 获取模型管理API的完整模型列表（最新数据，包含is_active状态）
  const { data: modelsData } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })

  // Publish dialog state
  const [publishDialogOpen, setPublishDialogOpen] = useState(false)

  // History version related state (panel control only, data fetched within component)
  const [versionListPanelOpen, setVersionListPanelOpen] = useState(false)
  const [switchingToVersion, setSwitchingToVersion] = useState<string | null>(null)
  const [selectedHistoryVersion, setSelectedHistoryVersion] = useState<string | null>(null)

  // Settings dialog state and fields
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Format agent save request
  const formatSaveAgentRequest = (response: AgentDetailResponse): SaveAgentRequest => {
    const { agent_name, ...otherProps } = response.data.agent_info
    // Use the actual agent_type from response to avoid race conditions
    const actualAgentType = otherProps.agent_type || 'react'

    // 从模型列表中查找当前模型的 model_id
    const modelList = response.data?.agent_option_info?.model_list || []
    const currentModelName = otherProps.model?.model_info?.model_name || ''
    const matchedModel = modelList.find(model => model.model_name === currentModelName)
    const modelId = matchedModel?.model_id

    // 如果找到匹配的模型，将 model_id 添加到 model.model_info 中
    const model = otherProps.model
      ? {
          ...otherProps.model,
          model_info: {
            ...otherProps.model.model_info,
            ...(modelId !== undefined && { model_id: modelId }),
          },
        }
      : otherProps.model

    return {
      ...otherProps,
      name: agent_name,
      agent_type: actualAgentType,
      model,
      configs: otherProps.configs || {},
      plugins: otherProps.plugins || [],
      workflows: otherProps.workflows || [],
      prompt_template_name: otherProps.prompt_template_name || '',
      prompt_template: otherProps.prompt_template || [],
      prompt_tuning: otherProps.prompt_tuning || {},
      triggers: otherProps.triggers || [],
      knowledge: otherProps.knowledge || [],
      memory: otherProps.memory || {},
    }
  }

  // Fetch agent details
  const fetchAgentDetail = async (agentId: string) => {
    try {
      setLoading(true)
      const response = await AgentService.getAgentDetail({
        agent_id: agentId,
        space_id: getDefaultSpaceId(),
      })
      setAgentDetailResponse(response)
      setSaveAgentRequest(formatSaveAgentRequest(response))
      // Enter page in draft edit mode by default
      setSelectedHistoryVersion(null)
      setHistoryAgentDetailResponse(null)
      useAgentStore.getState().setReadonly(false)
    } catch (error) {
      console.error('Failed to fetch agent detail:', error)
    } finally {
      setLoading(false)
    }
  }

  // Fetch current agent details on page load
  useEffect(() => {
    if (agentId) {
      fetchAgentDetail(agentId)
    } else {
      console.warn('agentId is empty')
    }
  }, [agentId])

  // Reset store data on component unmount
  useEffect(() => {
    // Only return cleanup function, no mount-time logic
    return () => {
      useAgentStore.getState().resetStore()
    }
  }, [])

  const onAgentSave = async () => {
    // 在保存前，确保 model_id 已经设置
    const modelList = agentDetailResponse?.data?.agent_option_info?.model_list || []
    const currentModelName = saveAgentRequest.model?.model_info?.model_name || ''
    const matchedModel = modelList.find(model => model.model_name === currentModelName)
    const modelId = matchedModel?.model_id

    // 如果找到匹配的模型且 model_id 还未设置，则更新 saveAgentRequest
    if (modelId !== undefined && !saveAgentRequest.model?.model_info?.model_id) {
      updateSaveAgentRequest({
        model: {
          ...saveAgentRequest.model,
          model_info: {
            ...saveAgentRequest.model.model_info,
            model_id: modelId,
          },
        },
      })
      // 等待状态更新
      await new Promise(resolve => setTimeout(resolve, 10))
    }

    const success = await saveAgent()
    if (success) {
      showSuccess(t('messages.saveSuccess'))
    } else {
      showError(saveError || t('messages.saveFailed'))
    }
  }

  // Reset layout widths to default values
  const resetLayoutWidths = useCallback(() => {
    const defaultLeft = 30
    const defaultRight = 30
    setLeftPanelWidth(defaultLeft)
    setRightPanelWidth(defaultRight)
    leftPanelWidthRef.current = defaultLeft
    rightPanelWidthRef.current = defaultRight
    prevWidthsRef.current = { left: defaultLeft, right: defaultRight }
  }, [])

  const handleAgentModeChange = async (e: SelectChangeEvent) => {
    const nextMode = e.target.value as 'single-react-agent' | 'multi-workflow'
    const nextType = nextMode === 'multi-workflow' ? 'workflow' : 'react'
    updateSaveAgentRequest({ agent_type: nextType })
    // Reset layout when switching agent mode
    resetLayoutWidths()
    if (agentId && displayedAgentDetailResponse?.data?.agent_info?.agent_version) {
      try {
        await ExecutionService.resetAgentInstance({
          space_id: getDefaultSpaceId(),
          id: agentId,
          version: displayedAgentDetailResponse.data.agent_info.agent_version,
          inputs: {
            query: '',
            conversation_id: agentId,
          },
          conversation_id: agentId,
        })
      } catch (error) {
        console.error('Failed to reset debug instance when switching mode:', error)
      }
    }
  }

  // Open publish dialog
  const handleOpenPublishDialog = () => {
    setPublishDialogOpen(true)
  }

  // Debug info panel toggle: compress other panels moderately
  const handleDebugInfoChange = useCallback((open: boolean) => {
    if (open) {
      // Record current widths for restoration on close
      prevWidthsRef.current = { left: leftPanelWidthRef.current, right: rightPanelWidthRef.current }
      const increaseRight = 20 // Percentage increase for right panel (moderate compression)
      const maxRightAllowed = 100 - MIN_LEFT - MIN_MIDDLE
      const targetRight = Math.min(maxRightAllowed, rightPanelWidthRef.current + increaseRight)
      const delta = targetRight - rightPanelWidthRef.current
      if (delta <= 0) return

      // Prioritize compressing left side, then middle, to ensure minimum widths
      const currentMiddle = Math.max(0, 100 - leftPanelWidthRef.current - rightPanelWidthRef.current)
      const canReduceLeft = Math.max(0, leftPanelWidthRef.current - MIN_LEFT)
      const canReduceMiddle = Math.max(0, currentMiddle - MIN_MIDDLE)

      const reduceLeft = Math.min(Math.ceil(delta / 2), canReduceLeft)
      const remaining = delta - reduceLeft
      const reduceMiddle = Math.min(remaining, canReduceMiddle)
      const extraRemaining = remaining - reduceMiddle

      const finalReduceLeft = Math.min(reduceLeft + Math.max(0, extraRemaining), canReduceLeft)

      const nextLeft = Math.max(MIN_LEFT, leftPanelWidthRef.current - finalReduceLeft)
      const nextRight = rightPanelWidthRef.current + finalReduceLeft + reduceMiddle

      setLeftPanelWidth(nextLeft)
      setRightPanelWidth(nextRight)
    } else {
      // Restore previous widths
      setLeftPanelWidth(prevWidthsRef.current.left)
      setRightPanelWidth(prevWidthsRef.current.right)
    }
  }, [])

  // Close publish dialog
  const handleClosePublishDialog = () => {
    setPublishDialogOpen(false)
  }

  // Open settings dialog (draft mode only)
  const handleOpenSettings = () => {
    setSettingsOpen(true)
  }

  const handleCloseSettings = () => {
    setSettingsOpen(false)
  }

  const handleSaveSettings = async (nextName: string, nextDescription: string, nextIcon: string) => {
    if (!agentId) return
    try {
      const agentType = agentDetailResponse?.data?.agent_info?.agent_type || 'react'
      await AgentService.updateAgent({
        agent_id: agentId,
        space_id: getDefaultSpaceId(),
        agent_name: nextName.trim(),
        description: nextDescription,
        icon: nextIcon,
        agent_type: agentType,
      })
      showSuccess(t('messages.updateAgentSuccess'))
      await fetchAgentDetail(agentId)
      setSettingsOpen(false)
    } catch (error) {
      console.error('Failed to update agent info:', error)
      showError(t('messages.updateAgentFailed'))
    }
  }

  // Open history version dialog
  const handleOpenVersionHistoryDialog = () => {
    setVersionListPanelOpen(true)
  }

  // Close history version dialog
  const handleCloseVersionHistoryDialog = async () => {
    // Prevent closing panel during version switching to avoid state inconsistency
    if (switchingToVersion) return

    // If currently in history version view, refresh to latest draft data on close
    if (selectedHistoryVersion) {
      try {
        if (agentId) {
          await fetchAgentDetail(agentId)
          showSuccess(t('messages.returnToLatestDraft'))
        } else {
          // Fallback: reset readonly and local history state when no agentId
          setSelectedHistoryVersion(null)
          setHistoryAgentDetailResponse(null)
          useAgentStore.getState().setReadonly(false)
        }
      } catch (e) {
        console.error('Failed to close history panel and refresh draft: ', e)
      }
    }

    setVersionListPanelOpen(false)
  }

  // Switch to specified version
  const handleSwitchToVersion = async (versionId: string, restoreTargetVersion?: string) => {
    if (!agentId) {
      showError(t('messages.versionInfoIncomplete'))
      return
    }

    try {
      setSwitchingToVersion(versionId)

      // Draft version: exit readonly mode, restore draft data
      if (versionId.toLowerCase() === 'draft') {
        setTimeout(() => {
          setSelectedHistoryVersion(null)
          setHistoryAgentDetailResponse(null)
          useAgentStore.getState().setReadonly(false)
          // Reset layout when switching to draft
          resetLayoutWidths()
          if (restoreTargetVersion) {
            showSuccess(t('messages.restoredToVersion', { version: restoreTargetVersion }))
          } else {
            showSuccess(t('messages.switchedToLatestContent'))
          }
        }, 200)
        return
      }

      // Re-fetch agent details for specified version
      const response = await AgentService.getAgentDetail({
        agent_id: agentId,
        space_id: getDefaultSpaceId(),
        version: versionId,
      })

      // History version details for display only, not written to saveAgentRequest
      setHistoryAgentDetailResponse(response)
      useAgentStore.getState().setReadonly(true)

      // Reset layout when switching to history version
      resetLayoutWidths()

      showSuccess(t('messages.switchedToVersion', { version: versionId }))
      // Keep version list panel open and record currently selected history version
      setSelectedHistoryVersion(versionId)
    } catch (error) {
      console.error('Failed to switch version:', error)
      const errorMessage = error instanceof Error ? error.message : t('messages.switchVersionFailed')
      showError(errorMessage)
    } finally {
      setSwitchingToVersion(null)
    }
  }

  const beginDragLeft = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    setDraggingDivider('left')
    draggingDividerRef.current = 'left'
    dragStartXRef.current = e.clientX
    startLeftRef.current = leftPanelWidthRef.current
    document.addEventListener('mousemove', onDragMove)
    document.addEventListener('mouseup', endDrag)
  }
  const beginDragRight = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    setDraggingDivider('right')
    draggingDividerRef.current = 'right'
    dragStartXRef.current = e.clientX
    startRightRef.current = rightPanelWidthRef.current
    document.addEventListener('mousemove', onDragMove)
    document.addEventListener('mouseup', endDrag)
  }
  const onDragMove = useCallback((e: MouseEvent) => {
    if (!draggingDividerRef.current) return
    const container = containerRef.current
    if (!container) return
    const rect = container.getBoundingClientRect()
    const deltaPercent = ((e.clientX - dragStartXRef.current) / rect.width) * 100
    if (draggingDividerRef.current === 'left') {
      let newLeft = startLeftRef.current + deltaPercent
      const maxLeftAllowed = 100 - rightPanelWidthRef.current - MIN_MIDDLE
      newLeft = Math.max(MIN_LEFT, Math.min(maxLeftAllowed, newLeft))
      setLeftPanelWidth(newLeft)
    } else if (draggingDividerRef.current === 'right') {
      let newRight = startRightRef.current - deltaPercent
      const maxRightAllowed = 100 - leftPanelWidthRef.current - MIN_MIDDLE
      newRight = Math.max(MIN_RIGHT, Math.min(maxRightAllowed, newRight))
      setRightPanelWidth(newRight)
    }
  }, [])
  const endDrag = useCallback(() => {
    setIsDragging(false)
    setDraggingDivider(null)
    draggingDividerRef.current = null
    document.removeEventListener('mousemove', onDragMove)
    document.removeEventListener('mouseup', endDrag)
  }, [])

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onDragMove)
      document.removeEventListener('mouseup', endDrag)
    }
  }, [onDragMove, endDrag])
  // Sync widths to refs for drag listener use
  useEffect(() => {
    leftPanelWidthRef.current = leftPanelWidth
  }, [leftPanelWidth])
  useEffect(() => {
    rightPanelWidthRef.current = rightPanelWidth
  }, [rightPanelWidth])
  const isReadOnly = !!selectedHistoryVersion
  const displayedAgentDetailResponse = historyAgentDetailResponse || agentDetailResponse

  // displayedSaveAgentRequest: 业务数据的统一来源
  // 历史版本模式：从历史数据转换
  // 草稿模式：返回实时更新的 saveAgentRequest
  const displayedSaveAgentRequest = useMemo<SaveAgentRequest>(() => {
    if (selectedHistoryVersion && historyAgentDetailResponse) {
      return formatSaveAgentRequest(historyAgentDetailResponse)
    }
    return saveAgentRequest
  }, [selectedHistoryVersion, historyAgentDetailResponse, saveAgentRequest])

  // Calculate agent mode from displayedSaveAgentRequest (reflects real-time edits)
  const agentMode = useMemo<'single-react-agent' | 'multi-workflow'>(() => {
    const agentType = displayedSaveAgentRequest?.agent_type
    return agentType === 'workflow' ? 'multi-workflow' : 'single-react-agent'
  }, [displayedSaveAgentRequest?.agent_type])

  // Calculate whether to show left panel based on agent mode
  const shouldShowSystemPrompt = agentMode !== 'multi-workflow'

  // Adjust panel widths based on agent mode
  const { adjustedMiddleWidth, adjustedRightWidth } = useMemo(() => {
    if (!shouldShowSystemPrompt) {
      // Multi-workflow mode: orchestration and debug preview each take half
      return { adjustedMiddleWidth: 50, adjustedRightWidth: 50 }
    }
    // Other modes: maintain original drag widths
    return {
      adjustedMiddleWidth: Math.max(0, 100 - leftPanelWidth - rightPanelWidth),
      adjustedRightWidth: rightPanelWidth,
    }
  }, [shouldShowSystemPrompt, leftPanelWidth, rightPanelWidth])

  /** 把enableLongTerm提到AgentEditorEditPage，控制记忆弹窗显示长期记忆 */
  const [enableLongTerm, setEnableLongTerm] = useState<boolean | undefined>(undefined)

  useEffect(() => {
    const cfg = displayedSaveAgentRequest?.memory?.longterm_memory_config
    if (cfg !== undefined) {
      setEnableLongTerm(cfg)
    }
  }, [displayedSaveAgentRequest?.memory?.longterm_memory_config])

  // 将模型管理API的数据转换为ModelDetail格式（获取最新的is_active状态）
  const modelsList = useMemo<ModelDetail[]>(() => {
    if (!modelsData?.items) return []
    return modelsData.items.map(model => ({
      model_id: parseInt(model.id),
      model_name: model.name,
      model_type: model.modelId,
      model_provider: model.provider,
      max_tokens: model.maxTokens,
      temperature: model.temperature,
      top_p: model.topp,
      timeout: model.timeout,
      retry_count: model.retryCount,
      enable_streaming: model.enableStreaming,
      enable_function_calling: model.enableFunctionCalling,
      is_active: model.isActive,
      api_key: model.apiKey,
      api_base: model.baseUrl,
      streaming: model.enableStreaming,
    }))
  }, [modelsData])

  // 检查当前选择的模型是否可用
  const isModelActive = useMemo(() => {
    const currentModelName = displayedSaveAgentRequest?.model?.model_info?.model_name || ''
    if (!currentModelName) return false // 如果没有选择模型，认为不可用
    const matchedModel = modelsList.find(model => model.model_name === currentModelName)
    // 只有找到模型且is_active为true时才认为可用
    return matchedModel?.is_active === true
  }, [modelsList, displayedSaveAgentRequest?.model?.model_info?.model_name])

  return (
    <div className="agent-editor-enhanced-page flex flex-col h-full w-full overflow-x-hidden px-6 py-6" key={selectedHistoryVersion || 'draft'}>
      {loading ? (
        <div className="flex items-center justify-center h-full w-full">
          <CircularProgress />
        </div>
      ) : (
        <>
          <div className="header flex items-center justify-between p-4">
            <div className="flex items-center">
              <IconButton onClick={() => navigate('/dashboard/agents')}>
                <ChevronLeft className="w-6 h-6" />
              </IconButton>
              <div className="ml-2 flex items-center">
                <div className="mr-3 text-3xl">{displayedAgentDetailResponse?.data?.agent_info?.icon}</div>
                <div className="text-lg text-gray-800 font-bold max-w-[200px] truncate" title={displayedAgentDetailResponse?.data?.agent_info?.agent_name}>
                  {displayedAgentDetailResponse?.data?.agent_info?.agent_name}
                </div>
                {selectedHistoryVersion && (
                  <span className="ml-2 px-2 py-0.5 text-xs rounded border border-yellow-300 bg-yellow-50 text-yellow-800">
                    {t('labels.historyVersionPrefix')} {selectedHistoryVersion}
                  </span>
                )}
                {!selectedHistoryVersion && (
                  <>
                    <IconButton size="small" onClick={handleOpenSettings}>
                      <Settings className="w-4 h-4 text-gray-600" />
                    </IconButton>
                    <Select
                      value={agentMode}
                      onChange={handleAgentModeChange}
                      disabled={isReadOnly}
                      size="small"
                      style={{ minWidth: 180, marginLeft: '8px' }}
                      className="bg-white hover:bg-gray-50"
                    >
                      <MenuItem value="single-react-agent">{t('mode.singleReact')}</MenuItem>
                      <MenuItem value="multi-workflow">{t('mode.multiWorkflow')}</MenuItem>
                      <MenuItem value="multi-agents" disabled>
                        {t('mode.multiAgents')}
                      </MenuItem>
                    </Select>
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {/* 显示自动保存时间 */}
              {lastAutoSaveTime && (
                <>
                  <div className="text-sm text-gray-500 flex items-center">
                    <Clock className="w-4 h-4 mr-1" />
                    <span className="text-gray-700">{t('labels.lastSavedAt')}</span>
                    <span className="font-medium">{lastAutoSaveTime}</span>
                  </div>
                  <Divider orientation="vertical" variant="middle" flexItem />
                </>
              )}

              <Button
                variant="outlined"
                color="secondary"
                startIcon={<Save className="w-4 h-4" />}
                className="hover:bg-gray-50"
                onClick={onAgentSave}
                disabled={isSaving || isReadOnly}
              >
                {isSaving ? t('buttons.saving') : t('buttons.save')}
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                startIcon={<History className="w-4 h-4" />}
                className="hover:bg-gray-50"
                onClick={handleOpenVersionHistoryDialog}
              >
                {t('buttons.versionHistory')}
              </Button>
              <Button
                variant="contained"
                className="btn-primary"
                startIcon={<Tag className="w-4 h-4" />}
                onClick={handleOpenPublishDialog}
                disabled={isReadOnly}
              >
                {t('buttons.submitNewVersion')}
              </Button>
            </div>
          </div>
          <div className="content flex-1 flex overflow-x-hidden overflow-y-hidden min-w-0 relative">
            {/* 三栏容器：在剩余空间中自适应压缩 */}
            <div className="flex flex-row flex-1 min-w-0" ref={containerRef}>
              {/* 左侧面板 */}
              {shouldShowSystemPrompt && (
                <Paper className="h-full overflow-hidden p-4 flex-none relative" style={{ width: `${leftPanelWidth}%` }} elevation={1}>
                  <div className="flex items-center mb-4">
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-2 rounded-lg mr-3">
                      <Brain className="w-5 h-5 text-blue-600" />
                    </div>
                    <span className="text-lg font-semibold text-gray-800">{i18n.t('agents.agentEditor.systemPrompt.title')}</span>
                    <ActionSlotTarget name="system-title-actions" className="ml-auto flex items-center gap-2" />
                  </div>
                  <div className="h-[calc(100%-52px)]">
                    {/* 左侧面板：系统提示词 */}
                    <SystemPromptTab agentDetailResponse={displayedAgentDetailResponse || null} />
                  </div>
                </Paper>
              )}
              {/* 左侧拖拽分隔线（扩大命中区域，视觉仍为细条）*/}
              {shouldShowSystemPrompt && (
                <div className="top-0 h-full w-2 group cursor-col-resize select-none justify-items-center" onMouseDown={beginDragLeft} style={{ zIndex: 10 }}>
                  <div
                    className={`top-0 h-full w-1 transition-colors duration-200 ${isDragging && draggingDivider === 'left' ? 'bg-blue-500' : 'bg-gray-300'} group-hover:bg-blue-500`}
                  />
                </div>
              )}
              {/* 中间面板 */}
              <Paper className="h-full py-4 px-4 relative overflow-x-hidden flex-none" elevation={1} style={{ width: `${adjustedMiddleWidth}%` }}>
                <div className="flex items-center mb-4 h-18">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-2 rounded-lg mr-3">
                    <Settings className="w-5 h-5 text-blue-600" />
                  </div>
                  <span className="text-lg font-semibold text-gray-800">{i18n.t('agents.agentEditor.orchestration.title')}</span>
                </div>
                <div className="h-[calc(100%-52px)] text-gray-600 overflow-auto border rounded-xl p-2">
                  {agentMode === 'multi-workflow' ? (
                    <MultiWorkflowSelector agentDetailResponse={displayedAgentDetailResponse || null} saveAgentRequest={displayedSaveAgentRequest} />
                  ) : (
                    <AgentModelSelector
                      agentDetailResponse={displayedAgentDetailResponse || null}
                      saveAgentRequest={displayedSaveAgentRequest}
                      onLongTermChange={setEnableLongTerm}
                    />
                  )}
                </div>
              </Paper>
              {/* 右侧拖拽分隔线（扩大命中区域，视觉仍为细条）*/}
              {shouldShowSystemPrompt && (
                <div className="top-0 h-full w-2 group cursor-col-resize select-none justify-items-center" onMouseDown={beginDragRight} style={{ zIndex: 10 }}>
                  <div
                    className={`top-0 h-full w-1 transition-colors duration-200 ${isDragging && draggingDivider === 'right' ? 'bg-blue-500' : 'bg-gray-300'} group-hover:bg-blue-500`}
                  />
                </div>
              )}
              {/* 右侧面板 */}
              <Paper className="h-full overflow-y-auto overflow-x-hidden p-4 relative flex-none" style={{ width: `${adjustedRightWidth}%` }} elevation={1}>
                <div className="flex items-center mb-4">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-2 rounded-lg mr-3">
                    <Eye className="w-5 h-5 text-blue-600" />
                  </div>
                  <span className="text-lg font-semibold text-gray-800">{i18n.t('agents.agentEditor.previewDebug.title')}</span>
                  <ActionSlotTarget name="debug-title-actions" className="ml-auto flex items-center gap-2" />
                </div>
                {/* 对话调试面板 - 使用独立组件 */}
                <div className="flex flex-col h-[calc(100%-52px)] border rounded-xl p-2">
                  {agentId && (
                    <AgentDebugChat
                      key={agentMode}
                      agentId={agentId}
                      mdbId={saveAgentRequest.memory.memory_base?.mdb_id}
                      onDebugInfoChange={handleDebugInfoChange}
                      enableLongTerm={enableLongTerm ?? true}
                      hideMemoryButton={agentMode === 'multi-workflow'}
                      saveAgentRequest={displayedSaveAgentRequest}
                      isModelActive={isModelActive}
                    />
                  )}
                </div>
              </Paper>
            </div>
            {/* 版本历史侧边面板（固定宽度，组件内自行获取数据）*/}
            <AgentVersionListPanel
              open={versionListPanelOpen}
              agentId={agentId || null}
              selectedVersion={selectedHistoryVersion || 'draft'}
              onSelectVersion={versionId => {
                handleSwitchToVersion(versionId)
              }}
              onRestoreVersion={async versionId => {
                setReadonly(false)
                if (historyAgentDetailResponse) {
                  updateSaveAgentRequest(formatSaveAgentRequest(historyAgentDetailResponse))
                }
                await handleSwitchToVersion('draft', versionId)
              }}
              onClose={handleCloseVersionHistoryDialog}
              widthPx={360}
            />
          </div>
        </>
      )}

      {/* 设置对话框 */}
      <AgentSettingsDialog
        open={settingsOpen}
        initialName={displayedAgentDetailResponse?.data?.agent_info?.agent_name || ''}
        initialDescription={displayedAgentDetailResponse?.data?.agent_info?.description || ''}
        initialIcon={displayedAgentDetailResponse?.data?.agent_info?.icon || '🤖'}
        onClose={handleCloseSettings}
        onConfirm={(name, description, icon) => handleSaveSettings(name, description, icon)}
      />

      {/* 发布对话框 - 抽成独立组件 */}
      <AgentPublishDialog
        open={publishDialogOpen}
        agentId={agentId}
        onClose={handleClosePublishDialog}
        onPublished={() => {
          if (agentId) {
            fetchAgentDetail(agentId)
          }
          showSuccess(t('messages.publishSuccess'))
        }}
      />
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  )
}

export default AgentEditorEditPage
