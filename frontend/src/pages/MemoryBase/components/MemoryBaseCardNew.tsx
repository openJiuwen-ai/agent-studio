import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Edit, Trash2, Clock } from 'lucide-react';
import { ConfigCard, ConfigCardAction, EditingState } from '@/components/Common/common-grid';
import { CardFooterRow } from '@/components/Common/common-grid';
import { useEmbeddingModel, useModels, MemoryBaseService } from '@test-agentstudio/api-client';
import { useAuthStore } from '@/stores/useAuthStore';
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore';
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar';
import { validateMemoryBaseName } from '../utils/validation';
import type { MemoryBase } from '@/types/memoryBase';

interface ModelDetail {
  model_id: number;
  model_name: string;
  model_type: string;
  model_provider: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  timeout: number;
  retry_count: number;
  enable_streaming: boolean;
  enable_function_calling: boolean;
  is_active: boolean;
  api_key: string;
  api_base: string;
  streaming: boolean;
}

const EMPTY_EDITING_STATE: EditingState = {
  id: null,
  field: null,
  value: '',
  isEditing: false,
};

function formatRelativeTime(
  value: string | number | undefined,
  t: (k: string, opts?: Record<string, unknown>) => string
): string {
  if (!value) return '';
  const date = new Date(typeof value === 'number' ? value * 1000 : value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return t('common.messages.relativeTime.justNow');
  if (diffMins < 60) return t('common.messages.relativeTime.minutesAgo', { count: diffMins });
  if (diffHours < 24) return t('common.messages.relativeTime.hoursAgo', { count: diffHours });
  if (diffDays < 7) return t('common.messages.relativeTime.daysAgo', { count: diffDays });
  return date.toLocaleDateString();
}

export interface MemoryBaseCardNewProps {
  memoryBase: MemoryBase;
  onEdit: (mb: MemoryBase) => void;
  onDelete: (mb: MemoryBase) => void;
}

/**
 * 基于 ConfigCard 的记忆库网格卡片，支持卡片内联编辑名称与描述（双击编辑）。
 */
export const MemoryBaseCardNew: React.FC<MemoryBaseCardNewProps> = ({
  memoryBase,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const { updateMemoryBase } = useMemoryBaseStore();
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar();

  const { data: embeddingModel, isLoading: embeddingLoading } = useEmbeddingModel(
    memoryBase.embedding_model_config_id?.toString() || '',
    memoryBase.space_id || user?.spaceId || '',
  );

  const { data: modelsData } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  });

  const [modelsList, setModelsList] = React.useState<ModelDetail[]>([]);

  // 转换LLM模型数据格式
  React.useEffect(() => {
    if (modelsData?.items) {
      const convertedModels: ModelDetail[] = modelsData.items.map(model => ({
        model_id: parseInt(model.id),
        model_name: model.name || '',
        model_type: model.modelId || '',
        model_provider: model.provider || '',
        max_tokens: model.maxTokens || 0,
        temperature: model.temperature || 0,
        top_p: model.topp || 0,
        timeout: model.timeout || 0,
        retry_count: model.retryCount || 0,
        enable_streaming: model.enableStreaming || false,
        enable_function_calling: model.enableFunctionCalling || false,
        is_active: model.isActive || false,
        api_key: model.apiKey || '',
        api_base: model.baseUrl || '',
        streaming: model.enableStreaming || false,
      }));

      setModelsList(convertedModels);
    }
  }, [modelsData]);

  const [editingState, setEditingState] = useState<EditingState>(EMPTY_EDITING_STATE);
  const [existingNames, setExistingNames] = useState<string[]>([]);
  const [nameError, setNameError] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (editingState.id === memoryBase.mdb_id && editingState.field === 'name' && user?.spaceId) {
      const fetchNames = async () => {
        try {
          const allNames: string[] = [];
          let page = 1;
          const pageSize = 100;
          let hasMore = true;
          while (hasMore) {
            const response = await MemoryBaseService.getMemoryBases({
              space_id: user.spaceId,
              page,
              page_size: pageSize,
            });
            if (response?.data?.items) {
              const names = response.data.items
                .map((item: { name?: string }) => item.name)
                .filter((n): n is string => Boolean(n) && n !== memoryBase.name);
              allNames.push(...names);
              const total = response.data.total || 0;
              hasMore = page * pageSize < total;
              page += 1;
            } else {
              hasMore = false;
            }
          }
          setExistingNames(allNames);
        } catch (err) {
          console.error('Failed to fetch memory base names:', err);
        }
      };
      fetchNames();
    }
  }, [editingState.id, editingState.field, user?.spaceId, memoryBase.name]);

  const handleStartEdit = useCallback(
    (field: 'name' | 'description') => {
      setEditingState({
        id: memoryBase.mdb_id,
        field,
        value: field === 'name' ? memoryBase.name : memoryBase.description || '',
        isEditing: true,
      });
      setNameError('');
    },
    [memoryBase.mdb_id, memoryBase.name, memoryBase.description],
  );

  const handleUpdateValue = useCallback((value: string) => {
    setEditingState(prev => (prev.isEditing ? { ...prev, value } : prev));
    setNameError('');
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!editingState.isEditing || editingState.id !== memoryBase.mdb_id || !user?.spaceId) return;
    const { field, value } = editingState;
    const trimmed = value.trim();

    if (field === 'name') {
      const err = validateMemoryBaseName(trimmed, t, 'memoryBases.edit.nameRequired');
      if (err) {
        setNameError(err);
        return;
      }
      if (existingNames.some(n => n === trimmed)) {
        setNameError(t('memoryBases.form.nameExists'));
        return;
      }
    }

    try {
      setIsSaving(true);
      await updateMemoryBase({
        space_id: user.spaceId,
        mdb_id: memoryBase.mdb_id,
        name: field === 'name' ? trimmed : memoryBase.name,
        description: field === 'description' ? trimmed : memoryBase.description ?? '',
      });
      showSuccess(t('memoryBases.update.success'));
      setEditingState(EMPTY_EDITING_STATE);
      setNameError('');
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || t('memoryBases.update.error');
      showError(msg);
    } finally {
      setIsSaving(false);
    }
  }, [
    editingState,
    memoryBase.mdb_id,
    memoryBase.name,
    memoryBase.description,
    user?.spaceId,
    existingNames,
    t,
    updateMemoryBase,
    showSuccess,
    showError,
  ]);

  const handleCancelEdit = useCallback(() => {
    setEditingState(EMPTY_EDITING_STATE);
    setNameError('');
  }, []);

  const llmModel = modelsList.find(model => model.model_id === memoryBase.llm_model_config_id);

  const actions: ConfigCardAction[] = [
    {
      key: 'edit',
      label: t('common.buttons.edit'),
      icon: <Edit className="w-4 h-4" />,
      onClick: () => onEdit(memoryBase),
    },
    {
      key: 'delete',
      label: t('common.buttons.delete'),
      icon: <Trash2 className="w-4 h-4" />,
      onClick: () => onDelete(memoryBase),
    },
  ];

  const icon = <Brain className="w-6 h-6" />;
  const timeDisplay = formatRelativeTime(
    memoryBase.updated_at || memoryBase.created_at,
    t,
  );

  // 参考知识库卡片：Embedding 模型 + LLM 模型标签
  const tags: Array<{
    label: string;
    color?: string;
    variant?: 'default' | 'error' | 'loading';
    tooltip?: React.ReactNode;
  }> = [
  ];

  if (embeddingLoading) {
    tags.push({ label: t('memoryBases.form.loadingModels'), variant: 'loading' });
  } else if (embeddingModel?.name) {
    if (embeddingModel.isActive === false) {
      // 模型已被禁用：错误态 + 提示，参考知识库卡片
      tags.push({
        label: embeddingModel.name,
        variant: 'error',
        tooltip: t('memoryBases.form.modelUnavailable'),
      });
    } else {
      tags.push({ label: embeddingModel.name });
    }
  } else {
    tags.push({label : t('memoryBases.form.modelDeleted')})
  }

  if (llmModel) {
    if (!llmModel.is_active) {
      tags.push({
        label: llmModel.model_name,
        variant: 'error',
        tooltip: t('memoryBases.form.modelUnavailable'),
      });
    } else {
      tags.push({ label: llmModel.model_name });
    }
  } else {
    tags.push({label : t('memoryBases.form.modelDeleted')})
  }

  return (
    <>
      <ConfigCard
        id={memoryBase.mdb_id}
        icon={icon}
        iconBgColor="bg-gradient-to-br from-purple-50 to-indigo-50"
        iconTextColor="text-purple-600"
        title={memoryBase.name}
        description={memoryBase.description}
        tags={tags}
        editingState={editingState}
        isUpdating={isSaving}
        actions={actions}
        onClick={() => onEdit(memoryBase)}
        onEdit={handleStartEdit}
        onUpdateValue={handleUpdateValue}
        onSaveEdit={handleSaveEdit}
        onCancelEdit={handleCancelEdit}
        nameMaxLength={100}
        descriptionMaxLength={2000}
        inlineError={
          editingState.id === memoryBase.mdb_id && editingState.isEditing
            ? editingState.field === 'name'
              ? nameError
              : undefined
            : undefined
        }
        footer={
          <CardFooterRow className="flex flex-col gap-1">
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
  );
};

export default MemoryBaseCardNew;
