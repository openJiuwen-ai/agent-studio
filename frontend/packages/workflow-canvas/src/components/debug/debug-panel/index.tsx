/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */
import { FC, useState, useEffect } from 'react'
import { SideSheet, Button, Toast, Select, Switch } from '@douyinfe/semi-ui'
import { Bug, Terminal, AlertCircle, XCircle, Code, Database, ArrowRight, Clock, RefreshCw } from 'lucide-react'
import { useExecutionLogsList, useExecutionDebug, useFetchExecutionLogDetail } from '@test-agentstudio/api-client'
import { LogSummaryTree } from '../log-summary-tree'
import { ErrorBoundary } from './ErrorBoundary'
import { useTranslation } from '../../../i18n'

interface DebugSidePanelProps {
  visible: boolean
  onCancel: () => void
  workflowId?: string
  spaceId?: string
}

// Component Detail Panel for Sidebar
const ComponentDetailPanel: FC<{ component: any }> = ({ component }) => {
  const { t } = useTranslation()
  const hasInputs = component.inputs && Object.keys(component.inputs).length > 0
  const hasOutputs = component.outputs && Object.keys(component.outputs).length > 0
  const formatJSON = (obj: any) => {
    try {
      return JSON.stringify(obj, null, 2)
    } catch {
      return String(obj || 'null')
    }
  }
  if (!hasInputs && !hasOutputs) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-blue-600">
          <Database size={16} />
          <span className="text-sm font-medium">{t('workflowCanvas.debugPanel.noInputOutputData')}</span>
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-6">
      {/* Component Info */}
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-3">{t('workflowCanvas.debugPanel.componentInfo')}</h3>
        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
          {component.invokeId && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">ID:</span>
              <span className="text-gray-900 font-mono text-xs">{component.invokeId}</span>
            </div>
          )}
          {component.status && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{t('workflowCanvas.debugPanel.status')}:</span>
              <span
                className={`px-2 py-1 rounded text-xs ${
                  component.status === 'success' || component.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : component.status === 'failed' || component.status === 'error'
                      ? 'bg-red-100 text-red-800'
                      : component.status === 'running' || component.status === 'processing'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                }`}
              >
                {component.status}
              </span>
            </div>
          )}
          {component.duration && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{t('workflowCanvas.debugPanel.executionTime')}:</span>
              <span className="text-gray-900">{component.duration}ms</span>
            </div>
          )}
          {component.llmModel && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">{t('workflowCanvas.debugPanel.model')}:</span>
              <span className="text-gray-900">{component.llmModel}</span>
            </div>
          )}
        </div>
      </div>
      {/* Inputs */}
      {hasInputs && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ArrowRight size={14} className="text-green-500" />
            <h3 className="text-sm font-medium text-gray-900">Inputs</h3>
            <span className="text-xs text-gray-500">({Object.keys(component.inputs).length} {t('workflowCanvas.debugPanel.items')})</span>
          </div>
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
            <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono overflow-x-auto max-h-64 overflow-y-auto">{formatJSON(component.inputs)}</pre>
          </div>
        </div>
      )}
      {/* Outputs */}
      {hasOutputs && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ArrowRight size={14} className="text-blue-500" />
            <h3 className="text-sm font-medium text-gray-900">Outputs</h3>
            <span className="text-xs text-gray-500">({Object.keys(component.outputs).length} {t('workflowCanvas.debugPanel.items')})</span>
          </div>
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
            <pre className="text-xs text-gray-800 whitespace-pre-wrap font-mono overflow-x-auto max-h-64 overflow-y-auto">{formatJSON(component.outputs)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

// Debug function: Deep check API response structure
const debugApiResponse = (response: any, context: string) => {
  console.log(`🔍 [${context}] API响应调试:`)
  console.log('  - 响应类型:', typeof response)
  console.log('  - 是否为null/undefined:', response == null)
  console.log('  - 响应键:', response ? Object.keys(response) : 'N/A')
  if (response && typeof response === 'object') {
    console.log('  - data字段:', response.data)
    console.log('  - data类型:', typeof response.data)
    if (response.data) {
      console.log('  - data键:', Object.keys(response.data))
      const logSummaryFields = ['logSummary', 'log_summary', 'LogSummary', 'Log_summary']
      logSummaryFields.forEach(field => {
        if (response.data[field] !== undefined) {
          console.log(`  - 找到 ${field}:`, typeof response.data[field], response.data[field])
        }
      })
      const logDetailsFields = ['logDetails', 'log_details', 'LogDetails', 'Log_details']
      logDetailsFields.forEach(field => {
        if (response.data[field] !== undefined) {
          console.log(
            `  - 找到 ${field}:`,
            typeof response.data[field],
            Array.isArray(response.data[field]) ? `array(${response.data[field].length})` : 'not array',
          )
        }
      })
    }
  }
}

export const DebugSidePanel: FC<DebugSidePanelProps> = ({ visible, onCancel, workflowId, spaceId }) => {
  const { t } = useTranslation()
  const [selectedComponent, setSelectedComponent] = useState<any>(null)
  const [debugData, setDebugData] = useState<{
    log_summary?: any
    log_details?: any[]
    logs_create_list?: any[]
  } | null>(null)

  const [selectedExecutionTime, setSelectedExecutionTime] = useState<string>('')
  const [selectedLogIdForTime, setSelectedLogIdForTime] = useState<string>('')
  const [executionLogs, setExecutionLogs] = useState<any[]>([])

  // 存储执行日志选择后的调试数据
  const [executionLogDebugData, setExecutionLogDebugData] = useState<any>(null)

  // 调试数据加载状态
  const [isDebugDataLoading, setIsDebugDataLoading] = useState(false)

  // 初始加载调试树（基于工作流ID）
  const { initialDebugData, refetch: refetchDebug } = useExecutionDebug(
    {
      workflow_id: workflowId,
      space_id: spaceId,
    },
    {
      enabled: visible && !!workflowId && !!spaceId,
      onSuccess: (data: any) => {
        debugApiResponse(data, '初始调试数据加载')
        if (data.data) {
          const logSummary = data.data.log_summary || data.data.data?.log_summary || data.data.logSummary || data.data.data?.logSummary
          const logDetails = data.data.log_details || data.data.data?.log_details || data.data.logDetails || data.data.data?.logDetails || []
          const logsCreateList =
            data.data.logs_create_list || data.data.data?.logs_create_list || data.data.logsCreateList || data.data.data?.logsCreateList || []

          const parsedData = { log_summary: logSummary, log_details: logDetails, logs_create_list: logsCreateList }

          const hasAnyData =
            parsedData.log_summary ||
            (parsedData.log_details && parsedData.log_details.length > 0) ||
            (parsedData.logs_create_list && parsedData.logs_create_list.length > 0)

          if (hasAnyData) {
            setDebugData(parsedData)

            // 设置默认执行时间
            let defaultTime = ''
            if (parsedData.log_summary?.createTime) {
              defaultTime = formatExecutionTime(parsedData.log_summary.createTime)
            } else if (parsedData.logs_create_list && parsedData.logs_create_list.length > 0) {
              defaultTime = formatExecutionTime(parsedData.logs_create_list[0].createTime)
              setSelectedLogIdForTime(parsedData.logs_create_list[0].trace_id || parsedData.logs_create_list[0].traceId)
            }
            setSelectedExecutionTime(defaultTime)

            // 同时更新executionLogs状态
            if (parsedData.logs_create_list && parsedData.logs_create_list.length > 0) {
              setExecutionLogs(parsedData.logs_create_list)
            }
          } else {
            console.warn('⚠️ 未获取到任何有效的初始调试数据')
            setDebugData(parsedData)
          }
        }
      },
      onError: (error: any) => {
        console.error('❌ 初始调试数据加载失败:', error)
      },
    },
  )

  // 获取执行日志列表（用于时间选择器）
  const {
    logsData,
    isLoading: logsLoading,
    error: logsError,
  } = useExecutionLogsList(
    {
      workflow_id: workflowId,
      space_id: spaceId,
      page: 1,
      page_size: 20,
    },
    {
      enabled: visible && !!workflowId && !!spaceId,
    },
  )

  // Mutation 用于加载带 trace_id 的执行日志详情
  const fetchExecutionLogDetailMutation = useFetchExecutionLogDetail()

  // 加载执行日志列表后更新执行日志数据
  useEffect(() => {
    if (logsData) {
      let logsCreateList = []

      // 优先使用logs_create_list字段
      if (logsData?.data?.logs_create_list && Array.isArray(logsData.data.logs_create_list)) {
        logsCreateList = logsData.data.logs_create_list
      } else if (logsData?.data?.logsCreateList && Array.isArray(logsData.data.logsCreateList)) {
        logsCreateList = logsData.data.logsCreateList
      } else if (logsData?.data?.logs && Array.isArray(logsData.data.logs)) {
        logsCreateList = logsData.data.logs
      } else if (logsData?.logs_create_list && Array.isArray(logsData.logs_create_list)) {
        logsCreateList = logsData.logs_create_list
      } else if (logsData?.logs && Array.isArray(logsData.logs)) {
        logsCreateList = logsData.logs
      }

      if (logsCreateList.length > 0) {
        setExecutionLogs(logsCreateList)

        // 如果还没有选择执行时间，自动选择第一个
        if (!selectedExecutionTime && !selectedLogIdForTime && logsCreateList.length > 0) {
          const firstLog = logsCreateList[0]
          const createTime = firstLog.createTime || firstLog.create_time || Date.now()
          const logId = firstLog.trace_id || firstLog.id || firstLog.traceId || firstLog.traceId
          const formattedTime = formatExecutionTime(createTime)

          setSelectedExecutionTime(formattedTime)
          setSelectedLogIdForTime(logId)

          console.log('✅ 自动选择第一个执行日志:', {
            createTime,
            formattedTime,
            logId,
            log: firstLog,
          })
        }
      } else {
        console.log('⚠️ 未找到有效的执行日志数据:', logsData)
      }
    }
  }, [logsData, selectedExecutionTime, selectedLogIdForTime])

  // 辅助函数：格式化执行时间
  const formatExecutionTime = (timestamp: string | number) => {
    try {
      let date: Date
      if (typeof timestamp === 'string') {
        if (timestamp.includes('T') && timestamp.includes(':')) {
          date = new Date(timestamp)
        } else if (timestamp.includes('-') && timestamp.includes(' ')) {
          date = new Date(timestamp.replace(' ', 'T'))
        } else {
          date = new Date(timestamp)
        }
      } else {
        date = new Date(timestamp)
      }
      if (isNaN(date.getTime())) return t('workflowCanvas.debugPanel.invalidDate')
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    } catch (error) {
      return t('workflowCanvas.debugPanel.timeFormatError')
    }
  }

  // ✅ handleTimeSelection - 执行日志选择处理函数
  const handleTimeSelection = async (log: any, index: number) => {
    try {
      const createTime = log.createTime || log.create_time || Date.now()
      const formattedTime = formatExecutionTime(createTime)
      const logId = log.trace_id || log.id || log.traceId || log.log_id

      console.log('🎯 用户选择了执行日志:', { log, index, createTime, formattedTime, logId })

      setSelectedExecutionTime(formattedTime)
      setSelectedLogIdForTime(logId)
      setDebugData(null) // 清空之前的调试数据
      setExecutionLogDebugData(null) // 清空执行日志调试数据
      setSelectedComponent(null) // 清空选中的组件
      setIsDebugDataLoading(true) // 设置加载状态
      Toast.info(t('workflowCanvas.debugPanel.loadingDebugData', { nodeName: formattedTime }))

      if (!workflowId || !spaceId) {
        Toast.error(t('workflowCanvas.debugPanel.missingWorkflowOrSpaceId'))
        setIsDebugDataLoading(false)
        return
      }

      console.log('🚀 调用getExecutionLogDetail API:', { workflowId, spaceId, trace_id: logId })

      const result = await fetchExecutionLogDetailMutation.mutateAsync({
        trace_id: logId,
        workflow_id: workflowId,
        space_id: spaceId,
      })

      console.log('✅ API调用成功，响应数据:', result)

      if (result && result.data) {
        // 获取执行日志详情数据
        const executionLogDetail = result.data

        console.log('📋 原始API响应数据:', executionLogDetail)

        // 检查API响应中是否包含logSummary和logDetails字段
        let logSummary = null
        let logDetails = []

        // 优先使用API响应中的logSummary和logDetails字段
        if (executionLogDetail.logSummary) {
          logSummary = executionLogDetail.logSummary
          console.log('✅ 找到logSummary字段:', logSummary)
        } else {
          // 如果没有logSummary，基于ExecutionLogDetail基础信息创建一个
          logSummary = {
            traceId: executionLogDetail.id,
            createTime: executionLogDetail.start_time,
            duration: executionLogDetail.duration,
            status:
              executionLogDetail.status === 'completed'
                ? 0
                : executionLogDetail.status === 'failed'
                  ? 1
                  : executionLogDetail.status === 'running'
                    ? 2
                    : executionLogDetail.status === 'cancelled'
                      ? 3
                      : 1,
            inputs: executionLogDetail.input_data || {},
            outputs: executionLogDetail.output_data || {},
            execute_info_list: [],
          }
          console.log('🔧 基于基础信息创建logSummary:', logSummary)
        }

        if (executionLogDetail.logDetails) {
          logDetails = executionLogDetail.logDetails
          console.log('✅ 找到logDetails字段:', logDetails)
        } else if (executionLogDetail.nodes) {
          // 如果没有logDetails但有nodes，使用nodes作为logDetails
          logDetails = executionLogDetail.nodes
          console.log('🔧 使用nodes字段作为logDetails:', logDetails)
        }

        // 将数据转换为调试树可以使用的格式
        const adaptedDebugData = {
          log_summary: logSummary,
          log_details: logDetails,
          logs_create_list: [], // 保持空数组，因为这是详情API
        }

        console.log('📊 最终适配后的调试数据:', adaptedDebugData)

        // 设置调试数据，用于调测树展示
        setDebugData(adaptedDebugData)

        // 同时设置执行日志调试数据（原始响应），用于调试信息显示
        setExecutionLogDebugData(result.data)

        setIsDebugDataLoading(false) // 重置加载状态
        Toast.success(t('workflowCanvas.debugPanel.loadedExecutionLogDetails', { nodeName: executionLogDetail.workflow_name || formattedTime }))
      } else {
        console.warn('⚠️ API响应数据为空或格式错误')
        Toast.warning(t('workflowCanvas.debugPanel.executionLogDetailsEmpty'))
        setIsDebugDataLoading(false) // 重置加载状态

        // 提供降级数据，防止页面空白
        setDebugData({
          log_summary: null,
          log_details: [],
          logs_create_list: [],
        })
      }
    } catch (error) {
      console.error('❌ 加载时间选择的调试数据失败:', error)
      setIsDebugDataLoading(false) // 重置加载状态

      // 设置降级数据，防止页面空白
      setDebugData({
        log_summary: null,
        log_details: [],
        logs_create_list: [],
      })
      setExecutionLogDebugData(null)

      const errorMessage = error instanceof Error ? error.message : t('workflowCanvas.debugPanel.unknownError')
      Toast.error(`${t('workflowCanvas.debugPanel.loadDebugDataFailed')}: ${errorMessage}`)
    }
  }

  // 执行日志下拉选择器渲染
  const renderExecutionLogsDropdown = () => {
    // 直接使用从API获取的数据
    const logsCreateList = logsData?.data?.logs_create_list || logsData?.data?.logsCreateList || executionLogs

    if (logsCreateList.length === 0) {
      const loadingText = logsError ? t('workflowCanvas.debugPanel.loadFailed') : logsLoading ? t('workflowCanvas.debugPanel.fetchingData') : t('workflowCanvas.debugPanel.noExecutionLogs')
      return (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-700 font-medium">{t('workflowCanvas.debugPanel.executionLogs')}:</span>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <Clock size={12} />
            <span>{loadingText}</span>
          </div>
          <Button
            icon={<Clock size={12} />}
            size="small"
            type="tertiary"
            onClick={() => {
              Toast.info(t('workflowCanvas.debugPanel.reloadingExecutionLogs'))
            }}
            className="text-orange-600 hover:text-orange-700 hover:bg-orange-50"
          >
            {t('workflowCanvas.debugPanel.retry')}
          </Button>
        </div>
      )
    }

    // 将logs_create_list转换为下拉选项
    const selectOptions = logsCreateList.map((log: any, index: number) => {
      const createTime = log.createTime || log.create_time || Date.now()
      const formattedTime = formatExecutionTime(createTime)

      // 使用完整的格式化时间作为显示值
      let displayTime = formattedTime
      if (formattedTime && [t('workflowCanvas.debugPanel.invalidDate'), t('workflowCanvas.debugPanel.timeFormatError')].includes(formattedTime)) {
        displayTime = `${t('workflowCanvas.debugPanel.executionTime')} ${index + 1}`
      }

      return {
        value: formattedTime,
        label: displayTime,
        log,
        index,
        render: () => (
          <div className="flex items-center gap-2 py-1">
            <Clock size={14} className="text-gray-400" />
            <span className="text-sm">{displayTime}</span>
            <span className="text-xs text-gray-500">#{index + 1}</span>
          </div>
        ),
      }
    })

    const handleSelectChange = (value: string) => {
      const selectedOption = selectOptions.find(option => option.value === value)
      if (selectedOption) {
        handleTimeSelection(selectedOption.log, selectedOption.index)
      }
    }

    const handleSelectClear = () => {
      setSelectedExecutionTime('')
      setSelectedLogIdForTime('')
      setDebugData(null)
      setExecutionLogDebugData(null) // 同时清空执行日志调试数据
      setSelectedComponent(null)
      Toast.info(t('workflowCanvas.debugPanel.clearedSelection'))
    }

    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-700 font-medium">{t('workflowCanvas.debugPanel.executionLogs')}:</span>
        <Select
          value={selectedExecutionTime && ![t('workflowCanvas.debugPanel.invalidDate'), t('workflowCanvas.debugPanel.timeFormatError')].includes(selectedExecutionTime) ? selectedExecutionTime : ''}
          onChange={handleSelectChange}
          onClear={handleSelectClear}
          placeholder={t('workflowCanvas.debugPanel.selectExecutionLog')}
          size="small"
          style={{ width: '280px' }}
          className="w-full max-w-xs"
          disabled={logsLoading}
          loading={logsLoading}
          showClear
          allowCreate={false}
          maxTagCount={1}
        >
          {selectOptions.map(option => (
            <Select.Option
              key={option.value || `option-${option.index}`}
              value={option.value}
              render={option.render}
              disabled={!option.value || [t('workflowCanvas.debugPanel.invalidDate'), t('workflowCanvas.debugPanel.timeFormatError')].includes(option.value)}
            >
              {option.label}
            </Select.Option>
          ))}
        </Select>
      </div>
    )
  }

  return (
    <SideSheet
      title={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Bug size={20} className="text-orange-500" />
            <span>{t('workflowCanvas.debugPanel.debug')}</span>
          </div>
          <div className="flex items-center gap-2">
            {renderExecutionLogsDropdown()}
            <Button
              icon={<RefreshCw size={14} />}
              size="small"
              type="tertiary"
              onClick={() => {
                Toast.info(t('workflowCanvas.debugPanel.fetchingLatestLogs'))
                // 只重新获取执行日志列表，不影响当前选中的执行时间和调试数据
                refetchDebug()
              }}
              className="text-gray-600 hover:text-gray-700 hover:bg-gray-50"
              title={t('workflowCanvas.debugPanel.refreshExecutionLogs')}
            />
          </div>
        </div>
      }
      visible={visible}
      onCancel={onCancel}
      width={1000}
      bodyStyle={{ padding: 0 }}
      headerStyle={{
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#fafafa',
        padding: '16px 20px',
      }}
    >
      <div className="h-full bg-gray-50 flex">
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          <div className="p-4 space-y-4">
            {/* LogSummary 调测树 */}
            {debugData?.log_summary && (
              <div>
                {selectedExecutionTime && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2">
                      <Clock size={16} className="text-blue-500" />
                      <span className="text-sm font-medium text-blue-900">{t('workflowCanvas.debugPanel.currentExecutionTime')}: {selectedExecutionTime}</span>
                    </div>
                  </div>
                )}
                <ErrorBoundary>
                  <LogSummaryTree
                    logSummary={debugData.log_summary}
                    onNodeClick={node => {
                      console.log('[DebugPanel] LogSummary node clicked:', node)
                      setSelectedComponent(node)
                    }}
                  />
                </ErrorBoundary>
              </div>
            )}

            {!debugData?.log_summary && debugData && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle size={16} className="text-orange-600" />
                  <span className="font-medium text-gray-900">{t('workflowCanvas.debugPanel.missingLogSummaryData')}</span>
                </div>
                <div className="text-sm text-gray-600 mt-2">{t('workflowCanvas.debugPanel.missingLogSummaryDescription')}</div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        {selectedComponent && (
          <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code size={16} className="text-blue-500" />
                  <span className="font-medium text-gray-900">{selectedComponent.invokeType || t('workflowCanvas.debugPanel.unknownComponent')}</span>
                </div>
                <button onClick={() => setSelectedComponent(null)} className="text-gray-400 hover:text-gray-600 transition-colors">
                  <XCircle size={16} />
                </button>
              </div>
              <div className="text-xs text-gray-500 mt-1">{selectedComponent.invokeName && `${t('workflowCanvas.debugPanel.name')}: ${selectedComponent.invokeName}`}</div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <ComponentDetailPanel component={selectedComponent} />
            </div>
          </div>
        )}
      </div>
    </SideSheet>
  )
}
