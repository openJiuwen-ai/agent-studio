// MemoryBaseTableView Component
import { useTranslation } from 'react-i18next';
import { Tooltip } from '@mui/material';
import { Edit, Trash2, Info, Brain } from 'lucide-react';
import { ConfigTable } from '@/components/Common/common-table';
import { type TableColumn } from '@/components/Common/common-table';
import { Empty } from '@/components/Common/Empty';
import dayjs from 'dayjs';
import type { MemoryBase } from '@/types/memoryBase';
import React from 'react';

export interface MemoryBaseTableViewProps {
  memoryBases: MemoryBase[];
  loading?: boolean;
  searchTerm?: string;
  onCreateClick?: () => void;
  onEdit: (mb: MemoryBase) => void;
  onDelete: (mb: MemoryBase) => void;
  /**
   * 用于表格「Embedding 模型」列：id -> { name, isActive }
   */
  embeddingModelMap?: Record<string, { name: string; isActive: boolean }>;
  embeddingModelsLoading?: boolean;
  llmModels?: { model_id: number; model_name: string; is_active: boolean }[];
}

export const MemoryBaseTableView: React.FC<MemoryBaseTableViewProps> = ({
  memoryBases,
  loading = false,
  searchTerm = '',
  onCreateClick,
  onEdit,
  onDelete,
  embeddingModelMap = {},
  embeddingModelsLoading = false,
  llmModels = [],
}) => {
  const { t } = useTranslation();

  const formatDateValue = (value: unknown): string => {
    if (!value) return '';
    return dayjs(value as string | number | Date).format('YYYY-MM-DD HH:mm:ss');
  };

  const columns: TableColumn<MemoryBase>[] = React.useMemo(
    () => [
      {
        key: 'name',
        title: t('memoryBases.list.name'),
        dataIndex: 'name',
        width: 400,
        render: ({ row }) => (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gradient-to-br from-purple-100 to-indigo-100 text-purple-600">
              <Brain className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex-1">
              <div
                className="font-semibold text-gray-900 cursor-pointer truncate"
                onClick={() => onEdit(row)}
              >
                {row.name}
              </div>
              <div className="mt-1 text-xs text-gray-500 truncate">
                {row.description || '-'}
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'embedding_model',
        title: t('memoryBases.form.embeddingModelRequired'),
        dataIndex: 'embedding_model_config_id',
        width: 200,
        render: ({ row }) => {
          const configId = row.embedding_model_config_id?.toString();
          if (!configId) {
            return <span className="text-gray-400">-</span>;
          }
          if (embeddingModelsLoading && !Object.keys(embeddingModelMap).length) {
            return <span className="text-gray-500">{t('memoryBases.form.loadingModels')}</span>;
          }
          const meta = embeddingModelMap[configId];
          if (!meta?.name) {
            return <span className="text-gray-400">-</span>;
          }
          if (meta.isActive === false) {
            return (
              <Tooltip title={t('memoryBases.form.modelUnavailable')} disableInteractive placement="top">
                <div className="text-red-600 flex items-center gap-1 min-w-0">
                  <span className="truncate">{meta.name}</span>
                  <Info className="w-3 h-3 flex-shrink-0" />
                </div>
              </Tooltip>
            );
          }
          return <span className="truncate block">{meta.name}</span>;
        },
      },
      {
        key: 'llm_model',
        title: t('memoryBases.form.llmModelRequired'),
        dataIndex: 'llm_model_config_id',
        width: 200,
        render: ({ row }) => {
          const llmId = row.llm_model_config_id;
          if (!llmId) {
            return <span className="text-gray-400">-</span>;
          }
          
          const llmMeta = llmModels.find(model => model.model_id === llmId);
          if (!llmMeta) {
            return <span className="text-gray-400">-</span>;
          }
          
          if (!llmMeta.is_active) {
            return (
              <Tooltip title={t('memoryBases.form.llmModelUnavailable')} disableInteractive placement="top">
                <div className="text-red-600 flex items-center gap-1 min-w-0">
                  <span className="truncate">{llmMeta.model_name}</span>
                  <Info className="w-3 h-3 flex-shrink-0" />
                </div>
              </Tooltip>
            );
          }
          return <span className="truncate block">{llmMeta.model_name}</span>;
        },
      },
      {
        key: 'updated_at',
        title: t('memoryBases.list.updatedAt'),
        dataIndex: 'updated_at',
        type: 'date',
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'created_at',
        title: t('memoryBases.list.createdAt'),
        dataIndex: 'created_at',
        type: 'date',
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'actions',
        title: t('memoryBases.list.actions'),
        type: 'operate',
        align: 'right',
        width: 140,
        minWidth: 140,
        operations: [
          {
            key: 'edit',
            icon: <Edit className="w-4 h-4" />,
            label: t('common.buttons.edit'),
            tooltip: t('common.buttons.edit'),
            onClick: row => onEdit(row),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('common.buttons.delete'),
            tooltip: t('common.buttons.delete'),
            onClick: row => onDelete(row),
          },
        ],
      },
    ],
    [onEdit, onDelete, embeddingModelMap, embeddingModelsLoading, llmModels, t],
  );

  const tableData = React.useMemo(() => ({ columns, rows: memoryBases }), [columns, memoryBases]);

  return (
    <ConfigTable
      tableData={tableData}
      loading={loading}
      size="small"
      stickyHeader
      emptyState={
        <Empty searchTerm={searchTerm} type="memoryBases" onCreateClick={onCreateClick} />
      }
    />
  );
};

export default MemoryBaseTableView;