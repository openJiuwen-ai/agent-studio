import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Database } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import AgentIcon from '@/assets/icons/agent.svg?react'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import ModelIcon from '@/assets/icons/modelManagement.svg?react'
import PluginIcon from '@/assets/icons/plugin.svg?react'
import PromptTemplateIcon from '@/assets/icons/promptTemplate.svg?react'

const resourceConfig = {
  agents: {
    icon: <AgentIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: '/dashboard/agents/new',
    i18nKeys: {
      noDataTitle: 'agents.agentList.noAgents',
      noResultsTitle: 'agents.tableView.noMatchingAgents',
      noDataDescription: 'agents.agentList.createFirstAgent',
      noResultsDescription: 'agents.tableView.noMatchingAgentsDesc',
      createButton: 'agents.createAgent',
    },
  },
  workflows: {
    icon: <WorkflowIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: '/dashboard/workflows/new',
    i18nKeys: {
      noDataTitle: 'workflows.workflowList.noWorkflows',
      noResultsTitle: 'workflows.workflowList.noWorkflowsFound',
      noDataDescription: 'workflows.workflowList.createFirstWorkflow',
      noResultsDescription: 'workflows.workflowList.tryAdjustFilters',
      createButton: 'workflows.createWorkflow',
    },
  },
  models: {
    icon: <ModelIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: null, // 模型通过对话框创建，不需要跳转
    i18nKeys: {
      noDataTitle: 'models.modelList.emptyModelList',
      noResultsTitle: 'models.modelList.filterEmpty',
      noDataDescription: 'models.modelList.emptyModelListDesc',
      noResultsDescription: 'models.modelList.filterEmptyDesc',
      createButton: 'models.addModel',
    },
  },
  plugins: {
    icon: <PluginIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: null, // 插件通过对话框安装
    i18nKeys: {
      noDataTitle: 'plugins.noMatching',
      noResultsTitle: 'plugins.noMatching',
      noDataDescription: 'plugins.noMatchingDescription',
      noResultsDescription: 'plugins.noMatchingDescription',
      createButton: 'plugins.installPlugin',
    },
  },
  prompts: {
    icon: <PromptTemplateIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: null, // 提示词通过对话框创建
    i18nKeys: {
      noDataTitle: 'prompts.promptList.noPrompts',
      noResultsTitle: 'apps.empty.noTemplates',
      noDataDescription: 'prompts.promptList.createFirstPrompt',
      noResultsDescription: 'prompts.promptList.tryAdjustSearch',
      createButton: 'prompts.createPrompt',
    },
  },
  promptOptimize: {
    icon: <PromptTemplateIcon className="w-12 h-12 text-[#6b7280]" />,
    createPath: null, // 提示词自优化任务通过对话框 / 页面创建
    i18nKeys: {
      noDataTitle: 'prompts.optimizePage.emptyStates.noTasks.title',
      noResultsTitle: 'prompts.optimizePage.emptyStates.noMatch.title',
      noDataDescription: 'prompts.optimizePage.emptyStates.noTasks.description',
      noResultsDescription: 'prompts.optimizePage.emptyStates.noMatch.description',
      createButton: 'prompts.optimizePage.createTask',
    },
  },
  knowledgeBases: {
    icon: <Database className="w-12 h-12 text-[#6b7280]" />,
    createPath: null, // 知识库通过对话框创建
    i18nKeys: {
      noDataTitle: 'knowledgeBases.empty.title',
      noResultsTitle: 'knowledgeBases.search.noResults',
      noDataDescription: 'knowledgeBases.empty.description',
      noResultsDescription: 'knowledgeBases.search.tryOtherKeywords',
      createButton: 'knowledgeBases.createButton',
    },
  },
} as const

interface EmptyProps {
  searchTerm?: string
  type: 'agents' | 'workflows' | 'models' | 'plugins' | 'prompts' | 'promptOptimize' | 'knowledgeBases'
  hasFilters?: boolean // 是否有筛选条件（用于 models、promptOptimize）
  onCreateClick?: () => void // 创建按钮点击回调（用于 models、prompts、promptOptimize、knowledgeBases）
  customTitle?: string // 自定义标题（覆盖默认 i18n 文案）
  customDescription?: string // 自定义描述（覆盖默认 i18n 文案）
}

export const Empty: React.FC<EmptyProps> = ({ searchTerm = '', type, hasFilters = false, onCreateClick, customTitle, customDescription }) => {
  const { t } = useTranslation()
  const hasSearch = searchTerm.trim().length > 0
  const config = resourceConfig[type]
  const showNoResults =
    hasSearch ||
    (type === 'models' && hasFilters) ||
    (type === 'promptOptimize' && hasFilters) ||
    (type === 'prompts' && hasSearch) ||
    (type === 'knowledgeBases' && hasSearch)

  const createButton = useMemo(() => {
    if ((type === 'models' || type === 'plugins' || type === 'prompts' || type === 'promptOptimize' || type === 'knowledgeBases') && onCreateClick) {
      // 模型、插件、提示词、自优化任务和知识库类型使用回调函数
      return (
        <button
          onClick={onCreateClick}
          className="px-4 py-2 bg-[#3b82f6] text-white rounded-[4px] text-sm font-medium hover:bg-[#2563eb] transition-colors flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>{t(config.i18nKeys.createButton)}</span>
        </button>
      )
    } else if (config.createPath) {
      // 其他类型使用 Link
      return (
        <Link
          to={config.createPath}
          className="px-4 py-2 bg-[#3b82f6] text-white rounded-[4px] text-sm font-medium hover:bg-[#2563eb] transition-colors flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>{t(config.i18nKeys.createButton)}</span>
        </Link>
      )
    }
    return null
  }, [config, t, type, onCreateClick])

  // 确定显示的标题和描述（优先使用自定义文案）
  const title = customTitle ?? (showNoResults ? t(config.i18nKeys.noResultsTitle) : t(config.i18nKeys.noDataTitle))
  const description = customDescription ?? (showNoResults ? t(config.i18nKeys.noResultsDescription) : t(config.i18nKeys.noDataDescription))

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-24 h-24 rounded-full bg-[#f3f4f6] flex items-center justify-center mb-6">
        {config.icon}
      </div>
      <div className="text-lg font-semibold text-[#1f2937] mb-2">{title}</div>
      <p className="text-[#6b7280] text-sm mb-6">{description}</p>
      {!showNoResults && createButton}
    </div>
  )
}

export default Empty
