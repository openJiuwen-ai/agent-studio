import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Chip, Typography, Tooltip, Switch } from '@mui/material'
import { Play, Pencil, Trash2 } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import { type TableColumn, type RemoteQueryParams, type CellRenderParams } from '@/components/Common/common-table'
import type { FrontendModelConfig } from '@test-agentstudio/api-client'
import { ModelProvider } from '@test-agentstudio/api-client'
import { Empty } from '@/components/Common/Empty'

export interface LLMModelsTableProps {
  models: FrontendModelConfig[]
  loading?: boolean
  onFetchData?: (params: RemoteQueryParams) => void
  onEdit?: (model: FrontendModelConfig) => void
  onDelete?: (model: FrontendModelConfig) => void
  onToggleStatus?: (model: FrontendModelConfig) => void
  onTest?: (model: FrontendModelConfig) => void
  searchTerm?: string
  hasFilters?: boolean
  onCreateClick?: () => void
}

export const LLMModelsTable: React.FC<LLMModelsTableProps> = ({
  models,
  loading = false,
  onFetchData,
  onEdit,
  onDelete,
  onToggleStatus,
  onTest,
  searchTerm = '',
  hasFilters = false,
  onCreateClick,
}) => {
  const { t } = useTranslation()

  const columns: TableColumn<FrontendModelConfig>[] = useMemo(
    () => [
      {
        key: 'name',
        title: t('models.modelList.name'),
        dataIndex: 'name',
        type: 'text',
        width: 200,
        render: params => {
          const model = params.row as FrontendModelConfig
          return (
            <div>
              <Typography
                variant="subtitle2"
                className="font-bold text-gray-900 overflow-hidden text-ellipsis whitespace-nowrap"
                title={model.name}
              >
                {model.name}
              </Typography>
              {model.description && (
                <Typography variant="caption" className="text-gray-600 block max-w-[250px] truncate mt-1" title={model.description}>
                  {model.description}
                </Typography>
              )}
            </div>
          )
        },
      },
      {
        key: 'provider',
        title: t('models.modelList.provider'),
        dataIndex: 'provider',
        width: 120,
        render: (params: CellRenderParams<FrontendModelConfig>) => {
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
          const row = params.row as FrontendModelConfig
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
        key: 'tags',
        title: t('models.modelList.tags'),
        dataIndex: 'tags',
        width: 180,
        render: params => {
          const tags = params.value as string[]
          if (!tags || tags.length === 0) return '-'
          return (
            <div className="flex flex-wrap gap-1 items-center">
              {tags.slice(0, 3).map((tag, index) => (
                <Tooltip key={index} title={tag} arrow>
                  <Chip
                    label={tag}
                    size="small"
                    className="bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 border border-blue-200 hover:from-blue-200 hover:to-indigo-200 transition-all duration-200"
                    sx={{
                      maxWidth: '120px',
                      '& .MuiChip-label': {
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      },
                    }}
                  />
                </Tooltip>
              ))}
              {tags.length > 3 && (
                <Tooltip
                  title={
                    <div className="p-2 max-w-md bg-white">
                      <div className="text-sm font-semibold mb-2 text-gray-800">{t('models.modelConfig.basicInfo.moreTags')}: </div>
                      <div className="space-y-1">
                        {tags.slice(3).map((tag, index) => (
                          <div key={index} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded break-all">
                            {tag}
                          </div>
                        ))}
                      </div>
                    </div>
                  }
                  arrow
                >
                  <Chip
                    label={`+${tags.length - 3}`}
                    size="small"
                    className="bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-800 border border-blue-100 cursor-pointer"
                  />
                </Tooltip>
              )}
            </div>
          )
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
            icon: <Play className="w-4 h-4" />,
            label: t('models.testModel'),
            tooltip: t('models.testModel'),
            onClick: (row) => onTest?.(row),
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
    [t, onEdit, onDelete, onToggleStatus, onTest],
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

export default LLMModelsTable
