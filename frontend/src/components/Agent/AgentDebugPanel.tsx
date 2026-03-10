import { Select, Typography, MenuItem, SelectChangeEvent, FormControl, Tooltip, IconButton } from '@mui/material'
import React, { useEffect, useState } from 'react'
import {
  AgentExecutionDebugDetailResponse,
  AgentExecutionDebugListResponse,
  AgentExecutionLogSummary,
  AgentService,
  ExecutionLogCreateInfo,
  InvokeExecuteInfo,
} from '@test-agentstudio/api-client'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import dayjs from 'dayjs'
import { Copy, Check, RefreshCcw } from 'lucide-react'
import CallTree from './CallTree'
import FlameGraph from './FlameGraph'
import NodeDetail from './NodeDetail'
import { getStatusMeta } from './helper/statusUtils'
import { useScopedTranslation } from '@/i18n'

interface AgentDebugPanelProps {
  title?: string
  children?: React.ReactNode
  agentId: string
  agentVersion?: string
  agentName?: string
}

const AgentDebugPanel = ({ agentId, agentVersion, agentName }: AgentDebugPanelProps) => {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugPanel')
  const [logsCreateList, setLogsCreateList] = useState<ExecutionLogCreateInfo[]>([])
  const [selectedLogId, setSelectedLogId] = useState<string>('')
  const [selectedLogInfo, setSelectedLogInfo] = useState<AgentExecutionLogSummary>()
  const [loadingSelected, setLoadingSelected] = useState<boolean>(false)
  const [loadingList, setLoadingList] = useState<boolean>(false)
  const [viewMode, setViewMode] = useState<'tree' | 'flame'>('tree')
  const [selectedNode, setSelectedNode] = useState<InvokeExecuteInfo | null>(null)

  const getEnterExecutionLogsDebug = (space_id: string, agent_id: string, agent_version?: string): Promise<AgentExecutionDebugListResponse> => {
    return AgentService.enterExecutionLogsDebug({
      space_id,
      business_id: agent_id,
      business_version: agent_version || undefined,
      business_type: 'AGENT',
    })
  }

  const loadLogs = async () => {
    setLoadingList(true)
    try {
      const info = await getEnterExecutionLogsDebug(getDefaultSpaceId(), agentId, agentVersion || undefined)
      const list = info?.data || []
      const sorted = [...list].sort((a, b) => dayjs(b.create_time).valueOf() - dayjs(a.create_time).valueOf())
      const firstId = sorted?.[0]?.trace_id || ''
      setLogsCreateList(sorted)
      setSelectedLogId(firstId)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    loadLogs().catch((err: unknown) => {
      console.error('进入智能体执行日志调试失败:', err)
    })
  }, [agentId, agentVersion])

  const handleRefresh = () => {
    loadLogs().catch((err: unknown) => {
      console.error('刷新执行日志列表失败:', err)
    })
  }

  useEffect(() => {
    if (!selectedLogId) return
    setLoadingSelected(true)
    AgentService.getExecutionLogDetail({
      space_id: getDefaultSpaceId(),
      business_id: agentId,
      business_version: agentVersion || undefined,
      business_type: 'AGENT',
      trace_id: selectedLogId,
    })
      .then((info: AgentExecutionDebugDetailResponse) => {
        console.log('info', info)
        const log = info?.data || {}
        setSelectedLogInfo(log)
      })
      .catch((err: unknown) => {
        console.error('获取执行日志详情失败:', err)
      })
      .finally(() => setLoadingSelected(false))
  }, [selectedLogId, agentId, agentVersion])

  useEffect(() => {
    const arr = (selectedLogInfo?.execute_info_list || []) as InvokeExecuteInfo[]
    if (Array.isArray(arr) && arr.length > 0) {
      setSelectedNode(arr[0])
    } else {
      setSelectedNode(null)
    }
  }, [selectedLogInfo])

  const renderDebugContent = () => {
    const execList = (selectedLogInfo?.execute_info_list || []) as InvokeExecuteInfo[]
    const rootId = execList?.[0]?.invoke_id as string | undefined
    return (
      <div className="mt-2">
        {selectedLogInfo && <SummaryDetail logInfo={selectedLogInfo} />}
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <Typography variant="body2" className="text-gray-700 dark:text-gray-300">
              {viewMode === 'tree' ? t('viewMode.tree') : t('viewMode.flame')}
            </Typography>
            <div className="flex items-center gap-2">
              <button
                className={`text-xs px-2 py-1 rounded ${viewMode === 'tree' ? 'bg-gray-800 text-white dark:bg-gray-600' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}`}
                onClick={() => setViewMode('tree')}
              >
                {t('viewMode.tree')}
              </button>
              <button
                className={`text-xs px-2 py-1 rounded ${viewMode === 'flame' ? 'bg-gray-800 text-white dark:bg-gray-600' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'}`}
                onClick={() => setViewMode('flame')}
              >
                {t('viewMode.flame')}
              </button>
            </div>
          </div>
          <div className="rounded-md border border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-900 p-2">
            {execList.length === 0 ? (
              <div className="text-xs text-gray-500 dark:text-gray-400">{t('empty.noExecData')}</div>
            ) : viewMode === 'tree' ? (
              <CallTree execList={execList} onSelect={setSelectedNode} selectedId={selectedNode?.invokeId as string | undefined} rootLabel={agentName} />
            ) : (
              <FlameGraph execList={execList} onSelect={setSelectedNode} rootLabel={agentName} />
            )}
          </div>
        </div>
        <div className="mt-3">
          <Typography variant="body2" className="text-gray-700 dark:text-gray-300 mb-1">
            {t('sections.nodeDetail')}
          </Typography>
          <div className="mt-2 rounded-md border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-2">
            <NodeDetail node={selectedNode} rootName={agentName} rootId={rootId} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
      <div className="flex-1 bg-white dark:bg-gray-800 p-4 overflow-y-auto overflow-x-hidden shadow-inner border border-gray-100 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <Typography variant="body2" className="text-gray-700 dark:text-gray-300 flex-shrink-0">
            {t('filters.executionLog')}
          </Typography>
          <FormControl size="small" className="w-full">
            <Select
              value={selectedLogId}
              onChange={(e: SelectChangeEvent<string>) => setSelectedLogId(e.target.value)}
              renderValue={value => {
                if (loadingSelected || loadingList) return t('select.loading')
                if (!value) return t('select.placeholder')
                const current = logsCreateList.find(i => i.trace_id === value)
                return current ? dayjs(current.create_time).format('YYYY/MM/DD HH:mm:ss') : value
              }}
              MenuProps={{
                PaperProps: {
                  className: 'dark:bg-gray-800 dark:border-gray-700',
                  style: { maxHeight: 280 },
                },
              }}
              className="dark:text-gray-300"
              sx={{
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#E5E7EB',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#3B82F6',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#3B82F6',
                },
                '& .MuiSvgIcon-root': {
                  color: '#6B7280',
                },
                '.dark & .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#4B5563',
                },
                '.dark &:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#5B8CFF',
                },
                '.dark &.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#5B8CFF',
                },
                '.dark & .MuiSvgIcon-root': {
                  color: '#9CA3AF',
                },
              }}
            >
              {logsCreateList.map(item => (
                <MenuItem key={item.trace_id} value={item.trace_id} className="dark:text-gray-300 dark:hover:bg-gray-700">
                  {dayjs(item.create_time).format('YYYY/MM/DD HH:mm:ss')}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title={loadingList ? t('refresh.loading') : t('refresh.label')} placement="top">
            <span>
              <IconButton size="small" onClick={handleRefresh} disabled={loadingList} aria-label={t('refresh.ariaLabel')} className="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
                <RefreshCcw className={`w-4 h-4 ${loadingList ? 'animate-spin' : ''}`} />
              </IconButton>
            </span>
          </Tooltip>
        </div>

        {renderDebugContent()}
      </div>
    </div>
  )
}

const SummaryDetail = ({ logInfo }: { logInfo?: AgentExecutionDebugDetailResponse['data'] }) => {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugPanel.summary')
  return (
    <div className="summary border border-gray-100 dark:border-gray-700 p-2 rounded-md bg-gray-50 dark:bg-gray-900 gap-2 flex flex-col">
      <span className="text-gray-700 dark:text-gray-300 text-xs">
        {t('traceId')}：{logInfo?.trace_id}
        <CopyButton text={logInfo?.trace_id} />
      </span>
      <span className="text-gray-700 dark:text-gray-300 text-xs">
        {t('duration')}：{logInfo?.duration || 0} ms
        <span className={`text-xs py-0.5 ml-2 px-2 rounded-full ${getStatusMeta(logInfo?.status as string).className}`}>
          {getStatusMeta(logInfo?.status as string).label}
        </span>
      </span>
    </div>
  )
}

/**
 * 复制按钮组件：点击后复制文本到剪贴板，并在短时间内显示“已复制”反馈
 */
const CopyButton = ({ text }: { text?: string }) => {
  const [copied, setCopied] = useState(false)
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugPanel.copy')

  useEffect(() => {
    // traceId 变化时重置状态
    setCopied(false)
  }, [text])

  const handleCopy = async () => {
    if (!text) return
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        // 兼容旧环境的回退方案
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch (e) {
      console.error('复制 traceId 失败:', e)
    }
  }

  return (
    <Tooltip title={copied ? t('copied') : t('tooltip')} placement="top">
      <span>
        <IconButton size="small" onClick={handleCopy} disabled={!text} className="ml-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" aria-label={t('ariaLabel')}>
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        </IconButton>
      </span>
    </Tooltip>
  )
}

export default AgentDebugPanel
