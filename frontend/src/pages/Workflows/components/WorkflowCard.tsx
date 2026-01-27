import React from 'react'
import { useTranslation } from 'react-i18next'
import { Clock, Copy, Edit, Trash2 } from 'lucide-react'
import { ConfigCard, ConfigCardAction, EditingState } from '../../../components/Common/common-grid'
import { CardFooterRow } from '../../../components/Common/common-grid'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import { ENV_CONFIG } from '../../../config/environment'


export interface Workflow {
  workflow_id: string
  name: string
  desc: string
  space_id: string
  workflow_version?: string
  create_time?: number
  update_time?: number
  status?: string
  tags: any[]
}

interface WorkflowCardProps {
  workflow: Workflow
  editingState: EditingState
  onEdit: (field: 'name' | 'description') => void
  onUpdateValue: (value: string) => void
  onSaveEdit: () => void
  onCancelEdit: () => void
  onCopy: () => void
  onDelete: () => void
  isUpdating?: boolean
}

// 格式化时间辅助函数
const formatTime = (time?: string | Date | number): string => {
  if (!time) return ''
  const date = typeof time === 'number' ? new Date(time) : (typeof time === 'string' ? new Date(time) : time)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`

  return date.toLocaleDateString()
}

/**
 * WorkflowCard - 工作流卡片组件
 *
 * 基于 ConfigCard 的业务封装，处理工作流特定的逻辑（如时间格式化）
 */
export const WorkflowCard: React.FC<WorkflowCardProps> = ({
  workflow,
  editingState,
  onEdit,
  onUpdateValue,
  onSaveEdit,
  onCancelEdit,
  onCopy,
  onDelete,
  isUpdating = false,
}) => {
  const { t } = useTranslation()
  // 构建操作按钮
  const actions: ConfigCardAction[] = [
    {
      key: 'edit',
      label: '编辑',
      icon: <Edit className="w-4 h-4" />,
      onClick: () => {
        window.location.href = `/dashboard/workflows/editor/${workflow.workflow_id}?spaceId=${workflow.space_id || ENV_CONFIG.DEFAULT_SPACE_ID}`
      },
    },
    {
      key: 'copy',
      label: '复制',
      icon: <Copy className="w-4 h-4" />,
      onClick: onCopy,
    },
    {
      key: 'delete',
      label: '删除',
      icon: <Trash2 className="w-4 h-4" />,
      onClick: onDelete,
    },
  ]

  // 工作流图标
  const workflowIcon = <WorkflowIcon className="w-6 h-6" />

  // 格式化时间
  const timeDisplay = formatTime(workflow.update_time || workflow.create_time)

  return (
    <ConfigCard
      id={workflow.workflow_id}
      icon={workflowIcon}
      iconBgColor="bg-gradient-to-br from-blue-50 to-indigo-50"
      iconTextColor="text-blue-600"
      title={workflow.name}
      description={workflow.desc}
      editingState={editingState}
      actions={actions}
      isUpdating={isUpdating}
      onClick={() => {
        window.location.href = `/dashboard/workflows/editor/${workflow.workflow_id}?spaceId=${workflow.space_id || ENV_CONFIG.DEFAULT_SPACE_ID}`
      }}
      onEdit={onEdit}
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

export default WorkflowCard
