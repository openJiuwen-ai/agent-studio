import React from 'react'
import { Clock, Copy, Download, Trash2, Edit } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { ConfigCard, ConfigCardAction, EditingState } from '../../../components/Common/common-grid'
import { CardFooterRow } from '../../../components/Common/common-grid'
import AgentIcon from '@/assets/icons/agent.svg?react'
import { getAgentIconColor, getAgentIconTextColor } from './utils'
import { Agent } from './types'

interface AgentCardProps {
  agent: Agent
  onEdit: (agent: Agent, field: 'name' | 'description') => void
  onCopy: (agent: Agent) => void
  onDelete: (agent: Agent) => void
  onExport?: (agent: Agent) => void
  editingState: EditingState
  onUpdateValue: (value: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  isUpdating?: boolean
  isModelAvailable?: boolean
  modelsLoading?: boolean
}

export const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  onEdit,
  onCopy,
  onDelete,
  onExport,
  editingState,
  onUpdateValue,
  onSaveEdit,
  onCancelEdit,
  isUpdating = false,
  isModelAvailable = true,
  modelsLoading = false,
}) => {
  const { t } = useTranslation()

  const formatRelativeTime = (timestamp: number): string => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return t('common.messages.relativeTime.justNow')
    if (diffMins < 60) return t('common.messages.relativeTime.minutesAgo', { count: diffMins })
    if (diffHours < 24) return t('common.messages.relativeTime.hoursAgo', { count: diffHours })
    if (diffDays < 7) return t('common.messages.relativeTime.daysAgo', { count: diffDays })

    return date.toLocaleDateString()
  }

  const actions: ConfigCardAction[] = [
    {
      key: 'edit',
      label: t('agents.agentCard.actions.edit'),
      icon: <Edit className="w-4 h-4" />,
      onClick: () => {
        window.location.href = `/dashboard/agents/${agent.agent_id}`
      },
    },
    {
      key: 'copy',
      label: t('agents.agentCard.actions.copy'),
      icon: <Copy className="w-4 h-4" />,
      onClick: () => onCopy(agent),
    },
    ...(onExport
      ? [
          {
            key: 'export',
            label: t('agents.agentCard.actions.export'),
            icon: <Download className="w-4 h-4" />,
            onClick: () => onExport(agent),
          } as ConfigCardAction,
        ]
      : []),
    {
      key: 'delete',
      label: t('agents.agentCard.actions.delete'),
      icon: <Trash2 className="w-4 h-4" />,
      onClick: () => onDelete(agent),
    },
  ]

  const agentIcon = <AgentIcon className="w-6 h-6" />

  const iconBgColor = getAgentIconColor(agent)
  const iconTextColor = getAgentIconTextColor(agent)

  const modelName = agent.model?.model_info.model_name || agent.model_name

  const getAgentTypeLabel = () => {
    if (agent.agent_type === 'workflow') return t('agents.agentCard.types.workflow')
    if (agent.agent_type === 'react') return t('agents.agentCard.types.react')
    return t('agents.agentCard.types.default')
  }

  const tags: Array<{ label: string; color?: string; variant?: 'default' | 'error' | 'loading'; tooltip?: React.ReactNode }> = [
    { label: getAgentTypeLabel(), color: '#3B82F6' },
  ]

  if (modelName && modelName !== 'no model') {
    if (modelsLoading) {
      tags.push({ label: t('agents.agentCard.loadingModel'), variant: 'loading' })
    } else if (!isModelAvailable) {
      tags.push({ label: modelName, variant: 'error', tooltip: t('agents.agentList.modelDisabledTooltip') })
    } else {
      tags.push({ label: modelName })
    }
  }
  
  const timeDisplay = formatRelativeTime(agent.update_time || agent.create_time)

  const handleEdit = (field: 'name' | 'description') => {
    onEdit(agent, field)
  }

  return (
    <ConfigCard
      id={agent.agent_id}
      icon={agent.icon || agentIcon}
      iconBgColor={iconBgColor}
      iconTextColor={iconTextColor}
      title={agent.agent_name}
      description={agent.description}
      tags={tags}
      editingState={editingState}
      actions={actions}
      isUpdating={isUpdating}
      onClick={() => {
        window.location.href = `/dashboard/agents/${agent.agent_id}`
      }}
      onEdit={handleEdit}
      onUpdateValue={onUpdateValue}
      onSaveEdit={onSaveEdit}
      onCancelEdit={onCancelEdit}
      nameMaxLength={100}
      descriptionMaxLength={500}
      footer={
        <CardFooterRow>
          <div className="flex items-center text-[11px] text-[#9CA3AF]">
            <Clock className="w-3 h-3 mr-1" />
            <span>{t('common.card.editedAgo')} {timeDisplay}</span>
          </div>
        </CardFooterRow>
      }
    />
  )
}

export default AgentCard
