import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ArrowDown } from 'lucide-react'
import {
  AgentService,
  AgentDetailResponse,
  useRuntimeDetail,
  useRemoveRuntime,
  getToken,
  API_CONFIG,
  API_ENDPOINTS,
} from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, IconButton } from '@mui/material'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { AssistantUiChat } from '@/components/Common/Chat/AssistantUiChat'
import TabSwitch from '@/components/Common/TabSwitch'
import PublishApiPanel, { type CodeExampleItem } from './components/PublishApiPanel'
import type { JsonSchema } from '@/types/jsonSchema'

type PublishType = 'chat' | 'api'

/** API 发布 demo（与接口返回结构一致，后续由接口返回替换） */
const DEMO_API_PUBLISH = {
  api_name: '发送查询请求',
  api_desc: '发送查询请求',
  method: 'POST',
  url: 'http://localhost:8090/query',
  code_example: [
  {
    example_name: ['Example'],
    examples: [
      `curl -X POST '{{#if data.url}}{{data.url}}{{else}}https://localhost:8090/query{{/if}}{{#if data.query.conversation_id}}?conversation_id={{data.query.conversation_id}}{{/if}}' \\
-H "Authorization: Bearer {{#if data.token}}{{data.token}}{{else}}{token}{{/if}}" \\
-H "Content-Type: application/json"{{#if data.raw_body}} \\
-d '{{{data.raw_body}}}'{{else}}{{/if}}`,
    ],
    language: 'Shell',
    title: 'Curl Request',
  },
  {
    example_name: ['例1 流式响应', '例2 非流式响应', '例3 结合端插件聊天'],
    examples: [
      `"""
This example is about how to use the streaming interface to start a chat request
and handle chat events
"""
import os
from cozepy import COZE_CN_BASE_URL
coze_api_token = '{{#if data.token}}{{data.token}}{{else}}{token}{{/if}}'
coze_api_base = COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType, ChatEventType
coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
bot_id = '{{#if data.body.bot_id}}{{data.body.bot_id}}{{else}}{bot_id}{{/if}}'
user_id = '{{#if data.body.user_id}}{{data.body.user_id}}{{else}}{user_id}{{/if}}'
for event in coze.chat.stream(
    bot_id=bot_id,
    user_id=user_id,
    additional_messages=[Message.build_user_question_text("Tell a 500-word story.")],
):
    if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
        print(event.message.content, end="", flush=True)
    if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
        print()
        print("token usage:", event.chat.usage.token_count)`,
      `"""
This example describes how to use the chat interface to initiate conversations,
poll the status of the conversation, and obtain the messages after the conversation is completed.
"""
import os
import time
from cozepy import COZE_CN_BASE_URL
coze_api_token = '{{#if data.token}}{{data.token}}{{else}}{token}{{/if}}'
coze_api_base = COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType
coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
bot_id = '{{#if data.body.bot_id}}{{data.body.bot_id}}{{else}}{bot_id}{{/if}}'
user_id = '{{#if data.body.user_id}}{{data.body.user_id}}{{else}}{user_id}{{/if}}'
chat_poll = coze.chat.create_and_poll(
    bot_id=bot_id,
    user_id=user_id,
    additional_messages=[
        Message.build_user_question_text("Who are you?"),
        Message.build_assistant_answer("I am Bot by Coze."),
        Message.build_user_question_text("What about you?"),
    ],
)
for message in chat_poll.messages:
    print(message.content, end="", flush=True)
if chat_poll.chat.status == ChatStatus.COMPLETED:
    print()
    print("token usage:", chat_poll.chat.usage.token_count)`,
      `"""
This use case teaches you how to use local plugin.
"""
import json
from typing import List
from cozepy import COZE_CN_BASE_URL, ChatEvent, Stream, ToolOutput
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType, ChatEventType
coze_api_token = '{{#if data.token}}{{data.token}}{{else}}{token}{{/if}}'
coze_api_base = COZE_CN_BASE_URL
coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
bot_id = '{{#if data.body.bot_id}}{{data.body.bot_id}}{{else}}{bot_id}{{/if}}'
user_id = '{{#if data.body.user_id}}{{data.body.user_id}}{{else}}{user_id}{{/if}}'
def handle_stream(stream: Stream[ChatEvent]):
    for event in stream:
        if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
            print(event.message.content, end="", flush=True)
        if event.event == ChatEventType.CONVERSATION_CHAT_REQUIRES_ACTION:
            # ... submit_tool_outputs and continue
            pass
        if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
            print()
            print("token usage:", event.chat.usage.token_count)
handle_stream(coze.chat.stream(bot_id=bot_id, user_id=user_id, additional_messages=[
    Message.build_user_question_text("What do I have to do in the afternoon?"),
]))`,
    ],
    language: 'Python',
    title: 'Request',
  },
  {
    example_name: ['例1 流式响应', '例2 非流式响应'],
    examples: [
      `// Our official coze sdk for JavaScript [coze-js]
import { CozeAPI } from '@coze/api';
const apiClient = new CozeAPI({
  token: {{#if data.token}}'{{data.token}}'{{else}}{token}{{/if}},
  baseURL: '{{data.baseUrl}}'
});
const res = await apiClient.chat.stream({
  bot_id: {{#if data.body.bot_id}}'{{data.body.bot_id}}'{{else}}{bot_id}{{/if}},
  user_id: {{#if data.body.user_id}}'{{data.body.user_id}}'{{else}}{user_id}{{/if}},
});`,
      `// Our official coze sdk for JavaScript [coze-js]
import { CozeAPI } from '@coze/api';
const apiClient = new CozeAPI({
  token: {{#if data.token}}'{{data.token}}'{{else}}{token}{{/if}},
  baseURL: '{{data.baseUrl}}'
});
const res = await apiClient.chat.create({
  bot_id: {{#if data.body.bot_id}}'{{data.body.bot_id}}'{{else}}{bot_id}{{/if}},
  user_id: {{#if data.body.user_id}}'{{data.body.user_id}}'{{else}}{user_id}{{/if}},
});`,
    ],
    language: 'JavaScript',
    title: 'Fetch Request',
  },
] as CodeExampleItem[],
}

/** 请求配置 demo：Header / Query / Body（JSON Schema，与接口返回结构一致时可替换） */
const DEMO_HEADER_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    token: {
      type: 'string',
      description: 'API 通过访问令牌进行 API 请求的鉴权。生成方式可以参考鉴权方式',
    },
  },
  required: ['token'],
}

const DEMO_QUERY_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    conversation_id: {
      type: 'string',
      description:
        '标识对话发生在哪一次会话中。会话是 Bot 和用户之间的一段问答交互。一个会话包含一条或多条消息。对话是会话中对 Bot 的一次调用，Bot 会将对话中产生的消息添加到会话中。',
    },
  },
}

const DEMO_BODY_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    bot_id: {
      type: 'string',
      description: '要进行会话聊天的智能体 ID。进入智能体的开发页面，开发页面 URL 中 bot 参数后的数字就是智能体 ID。',
      example: '73428668*****',
    },
    user_id: {
      type: 'string',
      description:
        '标识当前与智能体对话的用户，由使用方自行定义、生成与维护。user_id 用于标识对话中的不同用户，不同的 user_id，其对话的上下文消息、数据库等对话记忆数据互相隔离。',
      example: '123',
    },
  },
  required: ['bot_id', 'user_id'],
}

/** 返回参数说明 demo（JSON Schema object，支持嵌套，与接口返回结构一致时可替换） */
const DEMO_RETURN_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    code: {
      type: 'integer',
      description: '调用状态码。0 表示调用成功，其他值表示调用失败，你可以通过 msg 字段判断详细的错误原因。',
      example: 0,
    },
    data: {
      type: 'object',
      description: '对话详情。',
      properties: {
        bot_id: { type: 'string', description: '该会话所属的智能体的 ID。', example: '737946218936519****' },
        completed_at: {
          type: 'integer',
          description: '对话结束的时间。格式为 10 位的 Unixtime 时间戳，单位为秒。',
          example: 1.718609575e9,
        },
        conversation_id: { type: 'string', description: '会话 ID，即会话的唯一标识。', example: '738136585609548****' },
        created_at: {
          type: 'integer',
          description: '对话创建的时间。格式为 10 位的 Unixtime 时间戳，单位为秒。',
          example: 1.718609571e9,
        },
        failed_at: {
          type: 'integer',
          description: '对话失败的时间。格式为 10 位的 Unixtime 时间戳，单位为秒。',
          example: 1.718609571e9,
        },
        id: { type: 'string', description: '对话 ID，即对话的唯一标识。', example: '738137187639794****' },
        last_error: {
          type: 'object',
          description: '最近一次错误信息。',
          properties: {
            code: { type: 'integer', description: '状态码。0 代表调用成功。', example: 0 },
            msg: {
              type: 'string',
              description: '状态信息。API 调用失败时可通过此字段查看详细错误信息。',
              example: '详见响应示例',
            },
          },
        },
      },
    },
  },
}

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

  useEffect(() => {
    fetchAgentDetail()
  }, [agentId])

  useEffect(() => {
    const deployUrl = runtimeDetailQuery.data?.data?.deploy_details?.[0]?.url
    if (deployUrl) {
      setRuntimeApiUrl(appendQueryPath(String(deployUrl)))
    }
  }, [runtimeDetailQuery.data])

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
      console.error('获取智能体详情失败:', error)
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

  const handleBack = () => {
    navigate('/dashboard/agents')
  }

  const handleOpenOfflineConfirm = () => {
    setOfflineConfirmOpen(true)
  }

  const handleCloseOfflineConfirm = () => {
    if (removeRuntimeMutation.isPending) return
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
      console.error('下架智能体失败:', error)
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
                <h1 className="text-lg font-semibold text-gray-900 truncate">{agent.agent_name}</h1>
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
            onChange={v => setPublishType(v as PublishType)}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          />

          <div className="flex flex-1 items-center justify-end space-x-2 min-w-0">
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<ArrowDown className="w-4 h-4" />}
              className="btn-secondary"
              onClick={handleOpenOfflineConfirm}
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
          <Button onClick={handleCloseOfflineConfirm} disabled={removeRuntimeMutation.isPending}>
            {t('runtime.publish.offlineConfirm.cancel')}
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleOffline}
            disabled={removeRuntimeMutation.isPending}
          >
            {t('runtime.publish.offlineConfirm.confirm')}
          </Button>
        </DialogActions>
      </Dialog>

      <div className="flex-1 overflow-auto">
        {publishType === 'chat' ? (
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
              userName={user?.username || user?.email || '用户'}
              className="flex-1 min-h-0"
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
                return_section_title: '非流式响应',
                return_params: DEMO_RETURN_PARAMS,
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default AgentPublishPage
