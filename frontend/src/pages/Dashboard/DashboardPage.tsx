import React from 'react'
import { Link } from 'react-router-dom'
import AgentIcon from '@/assets/icons/agent.svg?react'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import ModelIcon from '@/assets/icons/modelManagement.svg?react'
import PluginIcon from '@/assets/icons/plugin.svg?react'
import { useAgents } from '@test-agentstudio/api-client'
import { useWorkflows } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { useTranslation } from 'react-i18next'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { Plus } from 'lucide-react'

// 配置dayjs使用相对时间插件
dayjs.extend(relativeTime)

// 时间戳处理工具函数
const normalizeTimestamp = (timestamp: number | string): number => {
  // 将字符串转换为数字
  const numTimestamp = typeof timestamp === 'string' ? parseInt(timestamp) : timestamp

  // 判断是秒级还是毫秒级时间戳
  return numTimestamp > 1000000000000 ? numTimestamp : numTimestamp * 1000
}

// 创建dayjs对象的工具函数
const createDayjsDate = (timestamp: number | string | Date): dayjs.Dayjs => {
  if (timestamp instanceof Date) {
    return dayjs(timestamp)
  } else if (typeof timestamp === 'string') {
    const numTimestamp = parseInt(timestamp)
    if (!isNaN(numTimestamp)) {
      return dayjs(normalizeTimestamp(numTimestamp))
    }
    return dayjs(timestamp) // 如果是日期字符串，直接解析
  }

  // 数字类型时间戳
  return dayjs(normalizeTimestamp(timestamp))
}

const DashboardPage: React.FC = () => {
  const { user } = useAuthStore()
  const { t } = useTranslation()

  // 格式化时间的工具函数
  const formatTimeAgo = (timestamp: number | string | Date): string => {
    const dayjsDate = createDayjsDate(timestamp)

    // 验证日期是否有效
    if (!dayjsDate.isValid()) {
      return t('dashboard.recent.agents.timeUnknown')
    }

    const now = dayjs()
    const diffMinutes = now.diff(dayjsDate, 'minute')
    const diffHours = now.diff(dayjsDate, 'hour')
    const diffDays = now.diff(dayjsDate, 'day')

    if (diffMinutes < 5) {
      return t('dashboard.recent.agents.justNow')
    } else if (diffMinutes < 60) {
      return t('dashboard.recent.agents.minutesAgo', { count: diffMinutes })
    } else if (diffHours < 24) {
      return t('dashboard.recent.agents.hoursAgo', { count: diffHours })
    } else {
      return t('dashboard.recent.agents.daysAgo', { count: diffDays })
    }
  }
  const {
    data: workflowsResponse,
    isLoading: workflowsLoading,
    error: workflowsError,
  } = useWorkflows({
    space_id: user?.spaceId || '',
  })

  // 使用useAgents hook查询智能体数据
  const {
    data: agentsResponse,
    isLoading: agentsLoading,
    error: agentsError,
  } = useAgents({
    space_id: user?.spaceId || '',
  })

  // 通用数据处理函数：按时间戳排序并格式化数据
  const processRecentItems = <T extends Record<string, any>, R extends Record<string, any>>(
    items: T[] | undefined,
    isLoading: boolean,
    options: {
      idField: string
      nameField: string
      descriptionField: string
      timestampFields: string[]
      defaultName: string
      defaultDescription: string
      limit?: number
      mapFunction?: (item: T, index: number, formattedTimestamp: string) => R
    },
  ): R[] => {
    const { idField, nameField, descriptionField, timestampFields, defaultName, defaultDescription, limit = 3, mapFunction } = options

    // 加载中或无数据时返回空数组
    if (isLoading || !items || items.length === 0) {
      return []
    }

    // 按创建时间排序并提取指定数量的项目
    return items
      .sort((a: T, b: T) => {
        // 使用指定的时间戳字段进行排序
        const getTimestamp = (item: T): number => {
          for (const field of timestampFields) {
            if (item[field]) return item[field]
          }
          return 0
        }

        const timestampA = getTimestamp(a)
        const timestampB = getTimestamp(b)

        // 使用通用的时间戳处理函数进行比较
        return normalizeTimestamp(timestampB) - normalizeTimestamp(timestampA) // 降序排序，最新的在前
      })
      .slice(0, limit)
      .map((item: T, index: number) => {
        // 获取时间戳
        let timestamp = Date.now()
        for (const field of timestampFields) {
          if (item[field]) {
            timestamp = item[field]
            break
          }
        }

        const formattedTime = formatTimeAgo(timestamp)

        // 如果提供了自定义映射函数，则使用它
        if (mapFunction) {
          return mapFunction(item, index, formattedTime)
        }

        // 默认映射
        return {
          id: item[idField] || index + 1,
          name: item[nameField] || defaultName,
          description: item[descriptionField] || defaultDescription,
          lastUpdated: formattedTime,
        } as unknown as R
      })
  }

  // 处理工作流数据
  const recentWorkflows = React.useMemo(() => {
    return processRecentItems(workflowsResponse?.data?.workflow_list, workflowsLoading, {
      idField: 'workflow_id',
      nameField: 'name',
      descriptionField: 'desc',
      timestampFields: ['create_time'],
      defaultName: t('dashboard.recent.workflows.unnamed'),
      defaultDescription: t('dashboard.recent.workflows.noDescription'),
    })
  }, [workflowsResponse, workflowsLoading, t])

  // 处理智能体数据
  const recentAgents = React.useMemo(() => {
    return processRecentItems(agentsResponse?.data?.agent_items, agentsLoading, {
      idField: 'agent_id',
      nameField: 'agent_name',
      descriptionField: 'description',
      timestampFields: ['create_time'],
      defaultName: t('dashboard.recent.agents.unnamed'),
      defaultDescription: t('dashboard.recent.agents.noDescription'),
      mapFunction: (agent, index, formattedTime) => ({
        id: agent.agent_id || index + 1,
        name: agent.agent_name || t('dashboard.recent.agents.unnamed'),
        description: agent.description || t('dashboard.recent.agents.noDescription'),
        lastUpdated: formattedTime,
        icon: agent.icon || '🤖',
      }),
    })
  }, [agentsResponse, agentsLoading, t])

  // 通用函数：计算最近一天新增的项目数量
  const calculateDailyCount = <T extends Record<string, any>>(items: T[] | undefined, isLoading: boolean, timestampFields: string[]): number => {
    if (isLoading || !items) {
      return 0
    }

    const now = dayjs()
    const oneDayAgo = now.subtract(24, 'hour')

    return items.filter((item: T) => {
      // 获取时间戳
      let timestamp = 0
      let hasValidTimestamp = false

      for (const field of timestampFields) {
        if (item[field] !== undefined && item[field] !== null && item[field] !== '') {
          timestamp = item[field]
          hasValidTimestamp = true
          break
        }
      }

      // 如果没有找到有效时间戳，跳过该项目
      if (!hasValidTimestamp) {
        return false
      }

      const createDate = createDayjsDate(timestamp)
      return createDate.isValid() && createDate.isAfter(oneDayAgo)
    }).length
  }

  // 计算实际工作流总数
  const workflowCount = workflowsLoading
    ? 0 // 加载中使用0
    : !workflowsResponse?.data
      ? 0 // 无数据时显示0
      : workflowsResponse.data.total || workflowsResponse.data.workflow_list?.length || 0

  // 计算实际智能体总数
  const agentCount = agentsLoading
    ? 0 // 加载中使用0
    : !agentsResponse?.data.pagination?.total || agentsResponse.data.pagination.total === 0
      ? 0 // 无数据时显示0
      : agentsResponse.data.pagination.total

  // 计算最近一天新增的智能体和工作流数量
  const dailyAgentCount = React.useMemo(
    () => calculateDailyCount(agentsResponse?.data?.agent_items, agentsLoading, ['update_time', 'create_time']),
    [agentsResponse, agentsLoading],
  )

  const dailyWorkflowCount = React.useMemo(
    () => calculateDailyCount(workflowsResponse?.data?.workflow_list, workflowsLoading, ['update_time', 'create_time']),
    [workflowsResponse, workflowsLoading],
  )

  const stats = [
    {
      name: t('dashboard.quickStats.agents.total'),
      value: agentCount.toString(),
      change: dailyAgentCount > 0 ? `+${dailyAgentCount}` : undefined,
      changeType: dailyAgentCount > 0 ? 'positive' : 'neutral',
      icon: AgentIcon,
      color: agentCount > 0 ? 'bg-blue-500' : 'bg-gray-500',
    },
    {
      name: t('dashboard.quickStats.workflows.total'),
      value: workflowCount.toString(),
      change: dailyWorkflowCount > 0 ? `+${dailyWorkflowCount}` : undefined,
      changeType: dailyWorkflowCount > 0 ? 'positive' : 'neutral',
      icon: WorkflowIcon,
      color: workflowCount > 0 ? 'bg-green-500' : 'bg-gray-500',
    },
  ]

  const quickActions = [
    {
      name: t('dashboard.quickActions.createAgent.name'),
      description: t('dashboard.quickActions.createAgent.description'),
      icon: AgentIcon,
      href: '/dashboard/agents/new',
      color: 'bg-blue-500 hover:bg-blue-600',
    },
    {
      name: t('dashboard.quickActions.createWorkflow.name'),
      description: t('dashboard.quickActions.createWorkflow.description'),
      icon: WorkflowIcon,
      href: '/dashboard/workflows/new',
      color: 'bg-green-500 hover:bg-green-600',
    },
    {
      name: t('dashboard.quickActions.manageModels.name'),
      description: t('dashboard.quickActions.manageModels.description'),
      icon: ModelIcon,
      href: '/dashboard/models',
      color: 'bg-purple-500 hover:bg-purple-600',
    },
    {
      name: t('dashboard.quickActions.installPlugins.name'),
      description: t('dashboard.quickActions.installPlugins.description'),
      icon: PluginIcon,
      href: '/dashboard/plugins',
      color: 'bg-orange-500 hover:bg-orange-600',
    },
  ]

  return (
    <div className="space-y-8 p-6 min-h-full">
      {/* Page header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2">
          {t('dashboard.title')}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">{t('dashboard.subtitle')}</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {stats.map((stat, index) => (
          <Link
            key={stat.name}
            to={
              stat.name === t('dashboard.quickStats.agents.total')
                ? '/dashboard/agents'
                : stat.name === t('dashboard.quickStats.workflows.total')
                  ? '/dashboard/workflows'
                  : '#'
            }
            className="group relative overflow-hidden bg-white rounded-2xl shadow-sm hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-2 border border-gray-100 cursor-pointer"
            style={{
              animationDelay: `${index * 100}ms`,
              pointerEvents: stat.name === t('dashboard.quickStats.agents.total') || stat.name === t('dashboard.quickStats.workflows.total') ? 'auto' : 'none',
            }}
          >
            {/* Gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-white via-gray-50 to-gray-100 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

            {/* Content */}
            <div className="relative p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-600 mb-1">{stat.name}</p>
                  <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-700 mb-2">{stat.value}</p>
                  {stat.change && (
                    <div className="flex items-center space-x-2">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${
                          stat.changeType === 'positive'
                            ? 'bg-green-100 text-green-700 border border-green-200'
                            : 'bg-red-100 text-red-700 border border-red-200'
                        }`}
                      >
                        {stat.change}
                      </span>
                    </div>
                  )}
                </div>
                <div
                  className={`w-16 h-16 ${stat.color} rounded-2xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300`}
                >
                  <stat.icon className="w-8 h-8 text-white" />
                </div>
              </div>
            </div>

            {/* Bottom accent */}
            <div className={`absolute bottom-0 left-0 right-0 h-1 ${stat.color} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">{t('dashboard.quickActions.title')}</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, index) => (
            <Link
              key={action.name}
              to={action.href}
              className="group relative overflow-hidden bg-gradient-to-br from-gray-50 to-white rounded-xl p-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-gray-200 hover:border-gray-300"
              style={{ animationDelay: `${index * 150}ms` }}
            >
              {/* Hover effect overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-indigo-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

              {/* Content */}
              <div className="relative flex items-center space-x-3">
                <div
                  className={`w-12 h-12 ${action.color} rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300`}
                >
                  <action.icon className="w-6 h-6 text-white flex-shrink-0" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-900 transition-colors duration-300">{action.name}</h3>
                  <p className="text-sm text-gray-600 group-hover:text-gray-700 transition-colors duration-300">{action.description}</p>
                </div>
              </div>

              {/* Arrow indicator */}
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all duration-300">
                <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                  <div className="w-2 h-2 bg-blue-600 rounded-full" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent agents */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 min-w-0">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center mr-3">
                <AgentIcon className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">
                {t('dashboard.recent.agents.title')}
              </h2>
            </div>
            <Link to="/dashboard/agents" className="text-sm text-blue-600 hover:text-blue-700 font-medium hover:underline transition-all duration-200">
              {t('dashboard.recent.agents.viewAll')} →
            </Link>
          </div>
          <div className="space-y-4">
            {recentAgents.length > 0 ? (
              recentAgents.map((agent, index) => (
                <Link
                  key={agent.id}
                  to={`/dashboard/agents/${agent.id}?spaceId=${user?.spaceId || ''}`}
                  className="group flex items-center space-x-4 p-4 rounded-xl hover:bg-gradient-to-r hover:from-blue-50 hover:to-cyan-50 transition-all duration-300 border border-transparent hover:border-blue-200"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="text-4xl group-hover:scale-110 transition-transform duration-300">{agent.icon}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 group-hover:text-blue-900 transition-colors duration-300 truncate w-full">{agent.name}</p>
                    <p className="text-xs text-gray-600 group-hover:text-gray-700 transition-colors duration-300 truncate w-full">{agent.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500 font-medium">{agent.lastUpdated}</p>
                  </div>
                </Link>
              ))
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-blue-100">
                  <AgentIcon className="w-8 h-8 text-blue-400" />
                </div>
                <p className="text-lg text-gray-500 font-medium">{t('dashboard.recent.agents.noData')}</p>
                <p className="text-sm text-gray-400 mt-2 mb-6">{t('dashboard.recent.agents.emptyDescription')}</p>
                <Link
                  to="/dashboard/agents/new"
                  className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-4 py-2 rounded-xl font-medium hover:from-blue-600 hover:to-cyan-600 transition-all duration-300"
                >
                  <Plus className="w-4 h-4" />
                  <span>{t('dashboard.recent.agents.createFirst')}</span>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Recent workflows */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 min-w-0">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl flex items-center justify-center mr-3">
                <WorkflowIcon className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-green-800">
                {t('dashboard.recent.workflows.title')}
              </h2>
            </div>
            <Link to="/dashboard/workflows" className="text-sm text-blue-600 hover:text-blue-700 font-medium hover:underline transition-all duration-200">
              {t('dashboard.recent.workflows.viewAll')} →
            </Link>
          </div>
          <div className="space-y-4">
            {recentWorkflows.length > 0 ? (
              recentWorkflows.map((workflow, index) => (
                <Link
                  key={workflow.id}
                  to={`/dashboard/workflows/editor/${workflow.id}?spaceId=${user?.spaceId || ''}`}
                  className="group flex items-center space-x-4 p-4 rounded-xl hover:bg-gradient-to-r hover:from-green-50 hover:to-emerald-50 transition-all duration-300 border border-transparent hover:border-green-200"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="w-12 h-12 bg-gradient-to-r from-green-100 to-emerald-100 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 border border-green-200">
                    <WorkflowIcon className="w-6 h-6 text-green-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 group-hover:text-green-900 transition-colors duration-300 truncate">{workflow.name}</p>
                    <p className="text-xs text-gray-600 group-hover:text-gray-700 transition-colors duration-300 truncate">{workflow.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500 font-medium">{workflow.lastUpdated}</p>
                  </div>
                </Link>
              ))
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-r from-green-50 to-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-100">
                  <WorkflowIcon className="w-8 h-8 text-green-400" />
                </div>
                <p className="text-lg text-gray-500 font-medium">{t('dashboard.recent.workflows.noData')}</p>
                <p className="text-sm text-gray-400 mt-2 mb-6">{t('dashboard.recent.workflows.emptyDescription')}</p>
                <Link
                  to="/dashboard/workflows/new"
                  className="inline-flex items-center space-x-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-xl font-medium hover:from-green-600 hover:to-emerald-600 transition-all duration-300"
                >
                  <Plus className="w-4 h-4" />
                  <span>{t('dashboard.recent.workflows.createFirst')}</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
