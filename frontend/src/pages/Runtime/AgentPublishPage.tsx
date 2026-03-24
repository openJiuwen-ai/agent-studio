import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronLeft } from 'lucide-react'
import {
  AgentService,
  AgentDetailResponse,
  useRuntimeDetail,
  useRemoveRuntime,
  useResetConversation,
  getToken,
  API_CONFIG,
  API_ENDPOINTS,
} from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, IconButton } from '@mui/material'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { AssistantUiChat } from '@/components/Common/Chat/AssistantUiChat'
import PublishStatusTag from '@/components/Runtime/PublishStatusTag'
import TabSwitch from '@/components/Common/TabSwitch'
import PublishApiPanel from './components/PublishApiPanel'
import offShelfIcon from '@/assets/icons/runtime-dp-off-shelf-lined.svg'
import runtimePublishStatusIcon from '@/assets/icons/runtime-publish-success.svg'
import {
  DEMO_API_PUBLISH,
  DEMO_HEADER_PARAMS,
  DEMO_QUERY_PARAMS,
  DEMO_BODY_PARAMS,
  DEMO_RETURN_PARAMS,
  DEMO_RETURN_OVERALL_DESC,
} from './runtimeDemoData'

type PublishType = 'chat' | 'api'
type RuntimeDeployStatus = 'running' | 'pending' | 'stopped' | 'failed' | 'unknown'

/** 模拟 AI 回复（固定文案，用于对话体验演示） */
// Mock 已切换为真实执行接口（8001）

const AgentPublishPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const params = useParams()
  const agentId = params.id || ''
  const { user } = useAuthStore()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()

  const [loading, setLoading] = useState(true)
  const [agentDetail, setAgentDetail] = useState<AgentDetailResponse | null>(null)
  const [publishType, setPublishType] = useState<PublishType>('chat')
  const [runtimeApiUrl, setRuntimeApiUrl] = useState<string>(DEMO_API_PUBLISH.url)
  const [isRuntimeDetailEnabled, setIsRuntimeDetailEnabled] = useState(true)
  const [offlineConfirmOpen, setOfflineConfirmOpen] = useState(false)
  const [conversationId] = useState(() => {
    try {
      return crypto.randomUUID()
    } catch {
      return `${Date.now()}-${Math.random().toString(16).slice(2)}`
    }
  })

  const spaceId = user?.spaceId || getDefaultSpaceId()
  const runtimeDetailQuery = useRuntimeDetail(
    {
      agent_id: agentId,
      space_id: spaceId,
    },
    { enabled: !!agentId && isRuntimeDetailEnabled }
  )
  const removeRuntimeMutation = useRemoveRuntime()
  const resetConversationMutation = useResetConversation()
  const deployDetails = runtimeDetailQuery.data?.data?.deploy_details
  const primaryDeployDetail = Array.isArray(deployDetails) ? deployDetails[0] : (deployDetails as any)

  const normalizedDeployStatus = String(primaryDeployDetail?.status || '')
    .toLowerCase()
    .trim()
  const deployStatus: RuntimeDeployStatus =
    normalizedDeployStatus === 'running'
      ? 'running'
      : normalizedDeployStatus === 'pending'
        ? 'pending'
        : normalizedDeployStatus === 'stopped'
          ? 'stopped'
          : normalizedDeployStatus === 'failed'
            ? 'failed'
            : 'unknown'

  const hasDeploymentDetail = Array.isArray(deployDetails)
    ? deployDetails.length > 0
    : !!primaryDeployDetail
  const isRuntimeReady = hasDeploymentDetail && deployStatus === 'running'
  const shouldDisableRuntimeActions = !isRuntimeReady
  const isNotPublishedState = !hasDeploymentDetail || deployStatus === 'unknown'

  const runtimeStatusMessage = !hasDeploymentDetail
    ? t('runtime.publish.messages.notPublished')
    : deployStatus === 'pending'
      ? t('runtime.publish.messages.pending')
      : deployStatus === 'stopped'
        ? t('runtime.publish.messages.stopped')
        : deployStatus === 'failed'
          ? t('runtime.publish.messages.failed')
          : deployStatus === 'running'
            ? ''
            : t('runtime.publish.messages.notPublished')

  const publishStatusKey: 'false' | 'pending' | 'running' | 'stopped' | 'failed' =
    !hasDeploymentDetail
      ? 'false'
      : deployStatus === 'pending' || deployStatus === 'running' || deployStatus === 'stopped' || deployStatus === 'failed'
        ? deployStatus
        : 'false'

  const handleGoPublish = () => {
    if (!agentId) return
    navigate(`/dashboard/agents/${agentId}`, {
      state: { openPublishDialog: true },
    })
  }

  useEffect(() => {
    fetchAgentDetail()
  }, [agentId])

  useEffect(() => {
    const deployUrl = primaryDeployDetail?.url
    if (deployUrl) {
      setRuntimeApiUrl(appendQueryPath(String(deployUrl)))
    }
  }, [primaryDeployDetail?.url])

  useEffect(() => {
    if (!isRuntimeReady && publishType !== 'chat') {
      setPublishType('chat')
    }
  }, [isRuntimeReady, publishType])

  const fetchAgentDetail = async () => {
    if (!agentId) return

    try {
      setLoading(true)
      const response = await AgentService.getAgentDetail({
        space_id: user?.spaceId || getDefaultSpaceId(),
        agent_id: agentId,
      })

      if (response.code === 200) {
        setAgentDetail(response)
      } else {
        showError(`${t('common.messages.error')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error) {
      console.error('Failed to fetch agent detail:', error)
      showError(
        `${t('common.messages.error')}: ${
          error instanceof Error ? error.message : t('common.messages.unknownError')
        }`,
      )
    } finally {
      setLoading(false)
    }
  }

  const appendQueryPath = (url: string): string => {
    const trimmed = (url || '').trim()
    if (!trimmed) return DEMO_API_PUBLISH.url
    const normalized = trimmed.replace(/\/+$/, '')
    if (normalized.endsWith('/query')) return normalized
    return `${normalized}/query`
  }

  const appendResetConversationPath = (url: string): string => {
    const trimmed = (url || '').trim()
    if (!trimmed) return ''
    const normalized = trimmed.replace(/\/+$/, '')
    if (normalized.endsWith('/reset_conversation')) return normalized
    if (normalized.endsWith('/query')) return normalized.replace(/\/query$/, '/reset_conversation')
    return `${normalized}/reset_conversation`
  }

  const handleBack = () => {
    navigate('/dashboard/agents')
  }

  const handleOpenOfflineConfirm = () => {
    setOfflineConfirmOpen(true)
  }

  const handleCloseOfflineConfirm = () => {
    if (removeRuntimeMutation.isLoading) return
    setOfflineConfirmOpen(false)
  }

  const handleOffline = async () => {
    if (!agentId) return

    try {
      // 下架后无需再查询部署详情，避免详情接口返回空导致报错
      setIsRuntimeDetailEnabled(false)
      await removeRuntimeMutation.mutateAsync({
        space_id: spaceId,
        agent_id: agentId,
      })

      setOfflineConfirmOpen(false)
      showSuccess(t('runtime.publish.messages.offlineSuccess'))
      // 先展示成功提示，再跳转，避免页面卸载导致 Snackbar 不可见
      setTimeout(() => {
        navigate('/dashboard/agents')
      }, 1000)
    } catch (error) {
      // 下架失败时恢复查询能力
      setIsRuntimeDetailEnabled(true)
      console.error('Failed to offline agent:', error)
    }
  }

  const handleResetConversation = async (): Promise<boolean> => {
    try {
      const data = await resetConversationMutation.mutateAsync({
        target_url: appendResetConversationPath(runtimeApiUrl),
        space_id: String(spaceId),
        conversation_id: conversationId,
      })

      if (data && typeof data === 'object') {
        const wrapped = data as any
        if (typeof wrapped.code === 'number' && wrapped.code !== 200) {
          throw new Error(wrapped.message || 'reset conversation failed')
        }
        if (wrapped.data && typeof wrapped.data === 'object' && 'status' in wrapped.data && wrapped.data.status !== 'ok') {
          throw new Error(wrapped.data.message || 'reset conversation failed')
        }
        if ('status' in wrapped && wrapped.status !== 'ok') {
          throw new Error(wrapped.message || 'reset conversation failed')
        }
      }

      return true
    } catch (error) {
      console.error('Failed to reset conversation:', error)
      showError(t('runtime.publish.messages.resetConversationFailed'))
      return false
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <CircularProgress />
      </div>
    )
  }

  if (!agentDetail) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">{t('runtime.publish.messages.agentNotFound')}</div>
      </div>
    )
  }

  const agent = agentDetail.data.agent_info

  const token = getToken()
  const baseUrl = API_CONFIG.BASE_URL || '/api/v1'
  /** 经中台转发到 Runtime /query，与页面同域，避免直连 localhost:port 触发 CORS */
  const runtimeProxyQueryUrl = `${String(baseUrl).replace(/\/$/, '')}${API_ENDPOINTS.RUNTIME.QUERY}`

  return (
    <div className="h-full flex flex-col bg-white">
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />

      <div className="border-b border-gray-200 px-6 py-4 relative">
        <div className="flex items-center justify-between">
          <div className="flex flex-1 items-center space-x-4 min-w-0">
            <IconButton onClick={handleBack} title={t('common.actions.back')}>
              <ChevronLeft className="w-5 h-5" />
            </IconButton>

            <div className="flex items-center space-x-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-lg flex-shrink-0">
                {agent.icon || '🤖'}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  <h1 className="text-lg font-semibold text-gray-900 truncate">{agent.agent_name}</h1>
                  <PublishStatusTag status={publishStatusKey} />
                </div>
                <p className="text-sm text-gray-500 truncate">
                  {agent.description || t('runtime.publish.noDescription')}
                </p>
              </div>
            </div>
          </div>

          {/* 切换按钮：标题栏水平居中 */}
          <TabSwitch
            options={[
              { value: 'chat', label: t('runtime.publish.types.chat') },
              { value: 'api', label: t('runtime.publish.types.api') },
            ]}
            value={publishType}
            onChange={v => {
              if (shouldDisableRuntimeActions) return
              setPublishType(v as PublishType)
            }}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          />

          <div className="flex flex-1 items-center justify-end space-x-2 min-w-0">
            <Button
              variant="contained"
              startIcon={<img src={offShelfIcon} alt="" className="w-3.5 h-3.5" aria-hidden="true" />}
              className="btn-primary"
              onClick={handleOpenOfflineConfirm}
              disabled={shouldDisableRuntimeActions}
            >
              {t('runtime.publish.actions.offline')}
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={offlineConfirmOpen} onClose={handleCloseOfflineConfirm}>
        <DialogTitle>{t('runtime.publish.offlineConfirm.title')}</DialogTitle>
        <DialogContent>{t('runtime.publish.offlineConfirm.description')}</DialogContent>
        <DialogActions>
          <Button onClick={handleCloseOfflineConfirm} disabled={removeRuntimeMutation.isLoading}>
            {t('runtime.publish.offlineConfirm.cancel')}
          </Button>
          <Button
            variant="contained"
            className="btn-primary"
            onClick={handleOffline}
            disabled={removeRuntimeMutation.isLoading}
          >
            {t('runtime.publish.offlineConfirm.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      <div className="flex-1 overflow-auto">
        {!isRuntimeReady ? (
          <div className="h-full min-h-0 flex items-center justify-center px-6 py-8">
            <div className="w-full max-w-[460px] px-8 py-9 text-center">
              <img
                src={runtimePublishStatusIcon}
                alt=""
                className="mx-auto w-[132px] h-[72px] select-none pointer-events-none"
                aria-hidden="true"
              />
              <div className="mt-4 text-[22px] leading-8 font-semibold text-[#1F2A44]">
                {isNotPublishedState ? (
                  <>
                    {t('runtime.publish.messages.notPublished')}
                    <button
                      type="button"
                      onClick={handleGoPublish}
                      className="ml-1 text-[22px] leading-8 font-semibold text-[#1A56F8] cursor-pointer"
                    >
                      {t('runtime.publish.actions.goPublish')}
                    </button>
                  </>
                ) : (
                  runtimeStatusMessage
                )}
              </div>
            </div>
          </div>
        ) : publishType === 'chat' ? (
          <div className="h-full min-h-0 flex flex-col w-full max-w-full overflow-hidden">
            <AssistantUiChat
              agUi={{
                url: runtimeProxyQueryUrl,
                headers: {
                  ...(API_CONFIG.HEADERS || {}),
                  ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                buildBody: (input: any) => {
                  const messages = Array.isArray(input?.messages) ? input.messages : []
                  return {
                    agent_id: String(agent.agent_id || agentId),
                    target_url: runtimeApiUrl,
                    space_id: String(spaceId),
                    messages,
                    conversation_id: conversationId,
                    user_id: user?.id ?? 'anonymous',
                    stream: true,
                  }
                },
              }}
              assistantIcon={agent.icon}
              assistantName={agent.agent_name}
              emptyStateText={t('runtime.publish.chat.defaultGreeting')}
              userName={user?.username || user?.email || t('runtime.publish.chat.defaultUserName')}
              className="flex-1 min-h-0"
              onNewChat={handleResetConversation}
            />
          </div>
        ) : (
          <div className="h-full min-h-0 overflow-auto">
            <PublishApiPanel
              data={{
                ...DEMO_API_PUBLISH,
                url: runtimeApiUrl,
                api_desc: DEMO_API_PUBLISH.api_desc || t('runtime.publish.noDescription'),
                header_params: DEMO_HEADER_PARAMS,
                query_params: DEMO_QUERY_PARAMS,
                body_params: DEMO_BODY_PARAMS,
                return_section_title: t('runtime.publish.api.streamResponseSectionTitle'),
                return_params: DEMO_RETURN_PARAMS,
                return_overall_desc: DEMO_RETURN_OVERALL_DESC,
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default AgentPublishPage
