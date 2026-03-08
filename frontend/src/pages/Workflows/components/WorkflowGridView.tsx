import React from 'react'
import { WorkflowCard } from './WorkflowCard'
import { Empty } from '@/components/Common/Empty'
import { EditingState } from '../../../components/Common/common-grid'
import { Workflow } from '../../../utils/workflowUtils'

interface WorkflowGridViewProps {
  workflows: Workflow[]
  editingState: EditingState
  searchTerm?: string
  onEdit: (workflowId: string, field: 'name' | 'description', value: string) => void
  onUpdateValue: (value: string) => void
  onSaveEdit: (workflowId: string) => void
  onCancelEdit: () => void
  onCopy: (workflowId: string, spaceId: string, workflowName: string) => void
  onDelete: (workflowId: string, workflowName: string, workflowVersion?: string) => void
  savingWorkflowId?: string | null
}

export const WorkflowGridView: React.FC<WorkflowGridViewProps> = ({
  workflows,
  editingState,
  searchTerm = '',
  onEdit,
  onUpdateValue,
  onSaveEdit,
  onCancelEdit,
  onCopy,
  onDelete,
  savingWorkflowId = null,
}) => {
  if (workflows.length === 0) {
    return <Empty searchTerm={searchTerm} type="workflows" />
  }

  return (
    <div className="grid grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {workflows.map(workflow => {
        const isEditingThis = editingState.id === workflow.workflow_id && editingState.isEditing
        const isUpdatingThis = savingWorkflowId === workflow.workflow_id
        return (
          <WorkflowCard
            key={workflow.workflow_id}
            workflow={workflow}
            editingState={isEditingThis ? editingState : { id: null, field: null, value: '', isEditing: false }}
            onEdit={(field) => onEdit(workflow.workflow_id, field, field === 'name' ? workflow.name : workflow.desc)}
            onUpdateValue={onUpdateValue}
            onSaveEdit={() => onSaveEdit(workflow.workflow_id)}
            onCancelEdit={onCancelEdit}
            onCopy={() => onCopy(workflow.workflow_id, workflow.space_id, workflow.name)}
            onDelete={() => onDelete(workflow.workflow_id, workflow.name, workflow.workflow_version)}
            isUpdating={isUpdatingThis}
          />
        )
      })}
    </div>
  )
}

export default WorkflowGridView
