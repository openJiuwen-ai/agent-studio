import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Tooltip } from '@mui/material'
import { Edit, Trash2, Info } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import { type TableColumn } from '@/components/Common/common-table'
import { Empty } from '@/components/Common/Empty'
import { Database } from 'lucide-react'
import dayjs from 'dayjs'
import type { KnowledgeBase } from '@/types/knowledgeBase'

export interface KnowledgeBaseTableViewProps {
  knowledgeBases: KnowledgeBase[]
  loading?: boolean
  searchTerm?: string
  onCreateClick?: () => void
  onEdit: (kb: KnowledgeBase) => void
  onDelete: (kb: KnowledgeBase) => void
  /**
   * 用于表格「Embedding 模型」列：id -> { name, isActive }
   * 参考智能体列表，在模型被禁用时给出错误态标签和提示。
   */
  embeddingModelMap?: Record<string, { name: string; isActive: boolean }>
  embeddingModelsLoading?: boolean
}

const getTypeLabel = (type: string, t: (k: string) => string): string => {
  if (!type || type === 'unknown') return t('knowledgeBases.card.documentType')
  const key = `knowledgeBases.types.${type}` as const
  const fallback = t('knowledgeBases.card.documentType')
  try {
    const out = t(key)
    return out === key ? fallback : out
  } catch {
    return fallback
  }
}

export const KnowledgeBaseTableView: React.FC<KnowledgeBaseTableViewProps> = ({
  knowledgeBases,
  loading = false,
  searchTerm = '',
  onCreateClick,
  onEdit,
  onDelete,
  embeddingModelMap = {},
  embeddingModelsLoading = false,
}) => {
  const { t } = useTranslation()

  const formatDateValue = (value: unknown): string => {
    if (!value) return ''
    return dayjs(value as string | number | Date).format('YYYY-MM-DD HH:mm:ss')
  }

  const columns: TableColumn<KnowledgeBase>[] = useMemo(
    () => [
      {
        key: 'name',
        title: t('knowledgeBases.list.name'),
        dataIndex: 'name',
        width: 500,
        render: ({ row }) => (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-blue-50 text-blue-600">
              <Database className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex-1">
              <div
                className="font-semibold text-gray-900 cursor-pointer truncate"
                onClick={() => onEdit(row)}
              >
                {row.name}
              </div>
              <div className="mt-1 text-xs text-gray-500 truncate">
                {row.desc || row.description || '-'}
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'type',
        title: t('knowledgeBases.form.type'),
        dataIndex: 'type',
        width: 200,
        render: ({ row }) => getTypeLabel(row.type || 'document', t),
      },
      {
        key: 'embedding_model',
        title: t('knowledgeBases.form.embeddingModelRequired'),
        dataIndex: 'embedding_model_config_id',
        width: 200,
        render: ({ row }) => {
          const configId = row.embedding_model_config_id?.toString()
          if (!configId) {
            return <span className="text-gray-400">-</span>
          }
          if (embeddingModelsLoading && !Object.keys(embeddingModelMap).length) {
            return <span className="text-gray-500">{t('knowledgeBases.form.loadingModels')}</span>
          }
          const meta = embeddingModelMap[configId]
          if (!meta?.name) {
            return <span className="text-gray-400">-</span>
          }
          if (meta.isActive === false) {
            return (
              <Tooltip title={t('knowledgeBases.form.modelUnavailable')} disableInteractive placement="top">
                <div className="text-red-600 flex items-center gap-1 min-w-0">
                  <span className="truncate">{meta.name}</span>
                  <Info className="w-3 h-3 flex-shrink-0" />
                </div>
              </Tooltip>
            )
          }
          return <span className="truncate block">{meta.name}</span>
        },
      },
      {
        key: 'updated_at',
        title: t('knowledgeBases.list.updatedAt'),
        dataIndex: 'updated_at',
        type: 'date',
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'created_at',
        title: t('knowledgeBases.list.createdAt'),
        dataIndex: 'created_at',
        type: 'date',
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'actions',
        title: t('knowledgeBases.list.actions'),
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
    [onEdit, onDelete, embeddingModelMap, embeddingModelsLoading, t],
  )

  const tableData = useMemo(() => ({ columns, rows: knowledgeBases }), [columns, knowledgeBases])

  return (
    <ConfigTable
      tableData={tableData}
      loading={loading}
      size="small"
      stickyHeader
      emptyState={
        <Empty searchTerm={searchTerm} type="knowledgeBases" onCreateClick={onCreateClick} />
      }
    />
  )
}

export default KnowledgeBaseTableView
