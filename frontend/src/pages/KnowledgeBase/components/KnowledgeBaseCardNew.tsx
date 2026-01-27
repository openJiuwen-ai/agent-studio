import React from 'react'
import { useTranslation } from 'react-i18next'
import { Database, Edit, Trash2, Clock } from 'lucide-react'
import { ConfigCard, ConfigCardAction, EditingState } from '@/components/Common/common-grid'
import { CardFooterRow } from '@/components/Common/common-grid'
import { useEmbeddingModel } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import type { KnowledgeBase } from '@/types/knowledgeBase'

const EMPTY_EDITING_STATE: EditingState = {
  id: null,
  field: null,
  value: '',
  isEditing: false,
}

function getTypeLabel(type: string, t: (k: string) => string): string {
  if (!type || type === 'unknown') return t('knowledgeBases.card.documentType')
  const key = `knowledgeBases.types.${type}` as const
  try {
    const out = t(key)
    return out === key ? t('knowledgeBases.card.documentType') : out
  } catch {
    return t('knowledgeBases.card.documentType')
  }
}

function formatRelativeTime(value: string | number | undefined, t: (k: string, opts?: Record<string, unknown>) => string): string {
  if (!value) return ''
  const date = new Date(typeof value === 'number' ? value * 1000 : value)
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

export interface KnowledgeBaseCardNewProps {
  knowledgeBase: KnowledgeBase
  onEdit: (kb: KnowledgeBase) => void
  onDelete: (kb: KnowledgeBase) => void
}

/**
 * 基于 ConfigCard 的知识库网格卡片，用于 CommonPageLayout 下的网格视图。
 * 本迭代不做卡片内联编辑，编辑即跳转编辑页。
 */
export const KnowledgeBaseCardNew: React.FC<KnowledgeBaseCardNewProps> = ({
  knowledgeBase,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { data: embeddingModel, isLoading: embeddingLoading } = useEmbeddingModel(
    knowledgeBase.embedding_model_config_id?.toString() || '',
    knowledgeBase.space_id || user?.spaceId || '',
  )

  const actions: ConfigCardAction[] = [
    {
      key: 'edit',
      label: t('common.buttons.edit'),
      icon: <Edit className="w-4 h-4" />,
      onClick: () => onEdit(knowledgeBase),
    },
    {
      key: 'delete',
      label: t('common.buttons.delete'),
      icon: <Trash2 className="w-4 h-4" />,
      onClick: () => onDelete(knowledgeBase),
    },
  ]
  const icon = <Database className="w-6 h-6" />
  const typeLabel = getTypeLabel(knowledgeBase.type || 'document', t)
  const timeDisplay = formatRelativeTime(
    knowledgeBase.updated_at || knowledgeBase.created_at,
    t,
  )

  // 参考智能体卡片：类型 + Embedding 模型标签
  const tags: Array<{ label: string; color?: string; variant?: 'default' | 'error' | 'loading'; tooltip?: React.ReactNode }> = [
    { label: typeLabel, color: '#3B82F6' },
  ]
  if (embeddingLoading) {
    tags.push({ label: t('knowledgeBases.form.loadingModels'), variant: 'loading' })
  } else if (embeddingModel?.name) {
    if (embeddingModel.isActive === false) {
      // 模型已被禁用：错误态 + 提示，参考智能体卡片
      tags.push({
        label: embeddingModel.name,
        variant: 'error',
        tooltip: t('knowledgeBases.form.modelUnavailable'),
      })
    } else {
      tags.push({ label: embeddingModel.name })
    }
  }

  return (
    <ConfigCard
      id={knowledgeBase.id}
      icon={icon}
      iconBgColor="bg-gradient-to-br from-blue-50 to-indigo-50"
      iconTextColor="text-blue-600"
      title={knowledgeBase.name}
      description={knowledgeBase.desc || knowledgeBase.description}
      tags={tags}
      editingState={EMPTY_EDITING_STATE}
      actions={actions}
      onClick={() => onEdit(knowledgeBase)}
      footer={
        <CardFooterRow>
          <div className="flex items-center text-[11px] text-[#9CA3AF]">
            <Clock className="w-3 h-3 mr-1" />
            <span>
              {t('common.card.editedAgo')} {timeDisplay}
            </span>
          </div>
        </CardFooterRow>
      }
    />
  )
}

export default KnowledgeBaseCardNew
