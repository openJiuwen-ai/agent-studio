import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Database, Edit, Trash2, Clock } from 'lucide-react'
import { ConfigCard, ConfigCardAction, EditingState } from '@/components/Common/common-grid'
import { CardFooterRow } from '@/components/Common/common-grid'
import { useEmbeddingModel, KnowledgeBaseService } from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { useKnowledgeBaseStore } from '@/stores/useKnowledgeBaseStore'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { validateKnowledgeBaseName } from '../utils/validation'
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
 * 基于 ConfigCard 的知识库网格卡片，支持卡片内联编辑名称与描述（双击编辑）。
 */
export const KnowledgeBaseCardNew: React.FC<KnowledgeBaseCardNewProps> = ({ knowledgeBase, onEdit, onDelete }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { updateKnowledgeBase } = useKnowledgeBaseStore()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()
  const { data: embeddingModel, isLoading: embeddingLoading } = useEmbeddingModel(
    knowledgeBase.embedding_model_config_id?.toString() || '',
    knowledgeBase.space_id || user?.spaceId || '',
  )

  const [editingState, setEditingState] = useState<EditingState>(EMPTY_EDITING_STATE)
  const [existingNames, setExistingNames] = useState<string[]>([])
  const [nameError, setNameError] = useState<string>('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (editingState.id === knowledgeBase.id && editingState.field === 'name' && user?.spaceId) {
      const fetchNames = async () => {
        try {
          const allNames: string[] = []
          let page = 1
          const pageSize = 100
          let hasMore = true
          while (hasMore) {
            const response = await KnowledgeBaseService.getKnowledgeBases({
              space_id: user.spaceId,
              page,
              size: pageSize,
            })
            if (response.code === 200 && response.data?.items) {
              const names = response.data.items.map((item: { name?: string }) => item.name).filter((n): n is string => Boolean(n) && n !== knowledgeBase.name)
              allNames.push(...names)
              const total = response.data.total || 0
              hasMore = page * pageSize < total
              page++
            } else {
              hasMore = false
            }
          }
          setExistingNames(allNames)
        } catch (err) {
          console.error('Failed to fetch knowledge base names:', err)
        }
      }
      fetchNames()
    }
  }, [editingState.id, editingState.field, user?.spaceId, knowledgeBase.name])

  const handleStartEdit = useCallback(
    (field: 'name' | 'description') => {
      setEditingState({
        id: knowledgeBase.id,
        field,
        value: field === 'name' ? knowledgeBase.name : knowledgeBase.desc || knowledgeBase.description || '',
        isEditing: true,
      })
      setNameError('')
    },
    [knowledgeBase.id, knowledgeBase.name, knowledgeBase.desc, knowledgeBase.description],
  )

  const handleUpdateValue = useCallback((value: string) => {
    setEditingState(prev => (prev.isEditing ? { ...prev, value } : prev))
    setNameError('')
  }, [])

  const handleSaveEdit = useCallback(async () => {
    if (!editingState.isEditing || editingState.id !== knowledgeBase.id || !user?.spaceId) return
    const { field, value } = editingState
    const trimmed = value.trim()

    if (field === 'name') {
      const err = validateKnowledgeBaseName(trimmed, t, 'knowledgeBases.edit.nameRequired')
      if (err) {
        setNameError(err)
        return
      }
      if (existingNames.some(n => n === trimmed)) {
        setNameError(t('knowledgeBases.form.nameExists'))
        return
      }
    }

    try {
      setIsSaving(true)
      await updateKnowledgeBase({
        kb_id: knowledgeBase.id,
        space_id: user.spaceId,
        name: field === 'name' ? trimmed : knowledgeBase.name,
        desc: field === 'description' ? trimmed : knowledgeBase.desc || knowledgeBase.description || '',
      })
      showSuccess(t('knowledgeBases.update.success'))
      setEditingState(EMPTY_EDITING_STATE)
      setNameError('')
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || t('knowledgeBases.update.error')
      showError(msg)
    } finally {
      setIsSaving(false)
    }
  }, [
    editingState,
    knowledgeBase.id,
    knowledgeBase.name,
    knowledgeBase.desc,
    knowledgeBase.description,
    user?.spaceId,
    existingNames,
    t,
    updateKnowledgeBase,
    showSuccess,
    showError,
  ])

  const handleCancelEdit = useCallback(() => {
    setEditingState(EMPTY_EDITING_STATE)
    setNameError('')
  }, [])

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
  const timeDisplay = formatRelativeTime(knowledgeBase.updated_at || knowledgeBase.created_at, t)

  const tags: Array<{ label: string; color?: string; variant?: 'default' | 'error' | 'loading'; tooltip?: React.ReactNode }> = [
    { label: typeLabel, color: '#3B82F6' },
  ]
  if (embeddingLoading) {
    tags.push({ label: t('knowledgeBases.form.loadingModels'), variant: 'loading' })
  } else if (embeddingModel?.name) {
    if (embeddingModel.isActive === false) {
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
    <>
      <ConfigCard
        id={knowledgeBase.id}
        icon={icon}
        iconBgColor="bg-gradient-to-br from-blue-50 to-indigo-50"
        iconTextColor="text-blue-600"
        title={knowledgeBase.name}
        description={knowledgeBase.desc || knowledgeBase.description}
        tags={tags}
        editingState={editingState}
        isUpdating={isSaving}
        actions={actions}
        onClick={() => onEdit(knowledgeBase)}
        onEdit={handleStartEdit}
        onUpdateValue={handleUpdateValue}
        onSaveEdit={handleSaveEdit}
        onCancelEdit={handleCancelEdit}
        nameMaxLength={100}
        descriptionMaxLength={2000}
        inlineError={editingState.id === knowledgeBase.id && editingState.field === 'name' ? nameError : undefined}
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
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default KnowledgeBaseCardNew
