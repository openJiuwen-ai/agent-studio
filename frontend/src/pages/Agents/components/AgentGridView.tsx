import React from 'react'
import { AgentCard } from './AgentCard'
import { Empty } from '@/components/Common/Empty'
import { Agent } from './types'
import { EditingState } from '../../../components/Common/common-grid'

interface AgentGridViewProps {
  agents: Agent[]
  searchTerm?: string
  editingState: EditingState
  savingAgentId?: string | null
  onEdit: (agent: Agent, field: 'name' | 'description') => void
  onUpdateValue: (value: string) => void
  onSaveEdit: (agent: Agent) => void
  onCancelEdit: () => void
  onCopy: (agent: Agent) => void
  onDelete: (agent: Agent) => void
  onExport?: (agent: Agent) => void
  availableModelNames: Set<string>
  modelsLoading?: boolean
}

export const AgentGridView: React.FC<AgentGridViewProps> = ({
  agents,
  searchTerm = '',
  editingState,
  savingAgentId = null,
  onEdit,
  onUpdateValue,
  onSaveEdit,
  onCancelEdit,
  onCopy,
  onDelete,
  onExport,
  availableModelNames,
  modelsLoading = false,
}) => {
  // 检查模型是否可用
  const isModelAvailable = (agent: Agent): boolean => {
    const modelName = agent.model?.model_info.model_name || agent.model_name
    return modelName ? availableModelNames.has(modelName) : true
  }

  // 空状态
  if (agents.length === 0) {
    return <Empty searchTerm={searchTerm} type="agents" />
  }

  return (
    <div className="grid grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {agents.map(agent => {
        const isEditingThis = editingState.id === agent.agent_id && editingState.isEditing
        const isUpdatingThis = savingAgentId === agent.agent_id
        return (
          <AgentCard
            key={agent.agent_id}
            agent={agent}
            editingState={isEditingThis ? editingState : { id: null, field: null, value: '', isEditing: false }}
            onEdit={(cardAgent, field) => onEdit(cardAgent, field)}
            onUpdateValue={onUpdateValue}
            onSaveEdit={() => onSaveEdit(agent)}
            onCancelEdit={onCancelEdit}
            onCopy={() => onCopy(agent)}
            onDelete={() => onDelete(agent)}
            onExport={onExport ? () => onExport(agent) : undefined}
            isUpdating={isUpdatingThis}
            isModelAvailable={isModelAvailable(agent)}
            modelsLoading={modelsLoading}
          />
        )
      })}
    </div>
  )
}

export default AgentGridView
