import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import dayjs from 'dayjs'
import { Chip, Typography, Tooltip, Switch } from '@mui/material'
import { Play, Pencil, Trash2, Loader2 } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import { type TableColumn, type RemoteQueryParams, type CellRenderParams } from '@/components/Common/common-table'
import type { FrontendEmbeddingModelConfig } from '@test-agentstudio/api-client'
import { ModelProvider } from '@test-agentstudio/api-client'
import { Empty } from '@/components/Common/Empty'

export interface EmbeddingModelsTableProps {
  models: FrontendEmbeddingModelConfig[]
  loading?: boolean
  onFetchData?: (params: RemoteQueryParams) => void
  onEdit?: (model: FrontendEmbeddingModelConfig) => void
  onDelete?: (model: FrontendEmbeddingModelConfig) => void
  onToggleStatus?: (model: FrontendEmbeddingModelConfig) => void
  onTest?: (model: FrontendEmbeddingModelConfig) => void
  testingModelId?: string | null // 正在测试的模型 ID
  searchTerm?: string
  hasFilters?: boolean
  onCreateClick?: () => void
}

export const EmbeddingModelsTable: React.FC<EmbeddingModelsTableProps> = ({
  models,
  loading = false,
  onFetchData,
  onEdit,
  onDelete,
  onToggleStatus,
  onTest,
  testingModelId = null,
  searchTerm = '',
  hasFilters = false,
  onCreateClick,
}) => {
  const { t } = useTranslation()

  // 检查是否有任何模型正在测试
  const isAnyTesting = testingModelId !== null

  const columns: TableColumn<FrontendEmbeddingModelConfig>[] = useMemo(
    () => [
      {
        key: 'name',
        title: t('models.modelList.name'),
        dataIndex: 'name',
        type: 'text',
        width: 200,
        render: params => {
          const model = params.row as FrontendEmbeddingModelConfig
          return (
            <div>
              <Typography
                variant="subtitle2"
                className="font-bold text-gray-900 overflow-hidden text-ellipsis whitespace-nowrap"
                title={model.name}
              >
                {model.name}
              </Typography>
              <Typography variant="caption" className="text-gray-600 block max-w-[250px] truncate mt-1" title={model.modelId}>
                {model.modelId}
              </Typography>
            </div>
          )
        },
      },
      {
        key: 'provider',
        title: t('models.modelList.provider'),
        dataIndex: 'provider',
        width: 120,
        render: (params: CellRenderParams<FrontendEmbeddingModelConfig>) => {
          const provider = params.value as ModelProvider
          const providerLabels: Partial<Record<ModelProvider, string>> = {
            [ModelProvider.OPENAI]: 'OpenAI',
            [ModelProvider.SILICONFLOW]: 'SiliconFlow',
          }
          return (
            <Chip
              label={providerLabels[provider] || provider}
              size="small"
            />
          )
        },
      },
      {
        key: 'modelId',
        title: t('models.modelList.type'),
        dataIndex: 'modelId',
        type: 'text',
        width: 180,
        render: params => (
          <Typography variant="body2" className="text-gray-700">
            {params.value as string}
          </Typography>
        ),
      },
      {
        key: 'isActive',
        title: t('models.modelList.status'),
        dataIndex: 'isActive',
        width: 100,
        render: params => {
          const row = params.row as FrontendEmbeddingModelConfig
          const isActive = params.value as boolean
          return (
            <Switch
              checked={isActive}
              onChange={() => onToggleStatus?.(row)}
              size="small"
            />
          )
        },
      },
      {
        key: 'updatedAt',
        title: t('agents.tableView.columns.updateAt'),
        dataIndex: 'updatedAt',
        type: 'date',
        width: 170,
        dateFormatter: (value: unknown) => {
          if (!value) return ''
          return dayjs(value as string | number | Date).format('YYYY-MM-DD HH:mm:ss')
        },
      },
      {
        key: 'actions',
        title: t('models.modelList.actions'),
        type: 'operate',
        align: 'right',
        width: 160,
        minWidth: 160,
        operations: [
          {
            key: 'edit',
            icon: <Pencil className="w-4 h-4" />,
            label: t('models.editModel'),
            tooltip: (row) => row.isSystemModel ? t('models.messages.systemModelNoEdit') : t('models.editModel'),
            onClick: (row) => onEdit?.(row),
            disabled: (row) => row.isSystemModel,
          },
          {
            key: 'test',
            icon: (row) => {
              const isTesting = testingModelId === row.id
              return isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />
            },
            label: t('models.testModel'),
            tooltip: (row) => !row.isActive ? t('models.messages.embeddingModel.modelDisabled') : t('models.testModel'),
            onClick: (row) => row.isActive && !isAnyTesting && onTest?.(row),
            disabled: (row) => !row.isActive || isAnyTesting,
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('models.modelList.deleteModel'),
            tooltip: (row) => row.isSystemModel ? t('models.messages.systemModelNoDelete') : t('models.modelList.deleteModel'),
            onClick: (row) => onDelete?.(row),
            disabled: (row) => row.isSystemModel,
          },
        ],
      },
    ],
    [t, onEdit, onDelete, onToggleStatus, onTest, testingModelId, isAnyTesting],
  )

  const tableData = useMemo(
    () => ({
      columns,
      rows: models,
    }),
    [columns, models],
  )

  return (
    <ConfigTable
      tableData={tableData}
      loading={loading}
      onFetchData={onFetchData}
      stickyHeader
      emptyState={<Empty searchTerm={searchTerm} type="models" hasFilters={hasFilters} onCreateClick={onCreateClick} />}
    />
  )
}

export default EmbeddingModelsTable
