import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Tooltip } from '@mui/material'
import { Copy, Download, Trash2, Info, Edit } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import { type SortState, type TableColumn, type RemoteQueryParams } from '@/components/Common/common-table'
import { Empty } from '@/components/Common/Empty'
import dayjs from 'dayjs'
import { Agent } from './types'
import { getAgentIconColor, getAgentIconTextColor } from './utils'

interface AgentTableViewProps {
  agents: Agent[]
  loading?: boolean
  searchTerm?: string
  availableModelNames: Set<string>
  modelsData: any
  modelsLoading: boolean
  onCopy: (agent: Agent) => void
  onExport: (agent: Agent) => void
  onDelete: (agent: Agent) => void
  onFetchData?: (params: RemoteQueryParams) => void
  onSortChange?: (sort: SortState) => void
  defaultSort?: SortState
}

export const AgentTableView: React.FC<AgentTableViewProps> = ({
  agents,
  loading = false,
  searchTerm = '',
  availableModelNames,
  modelsData,
  modelsLoading,
  onCopy,
  onExport,
  onDelete,
  onFetchData,
  onSortChange,
  defaultSort,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()

  // Date formatting utility
  const formatDateValue = (value: unknown): string => {
    if (!value) return ''
    return dayjs(value as string | number | Date).format('YYYY-MM-DD HH:mm:ss')
  }

  const columns: TableColumn<Agent>[] = useMemo(
    () => [
      {
        key: 'agent',
        title: t('agents.tableView.columns.agent'),
        dataIndex: 'agent_name',
        minWidth: 260,
        width: 600,
        sortable: true,
        sortField: 'agent_name',
        render: ({ row }) => {
          const typeLabel = row.agent_type === 'workflow' ? t('agents.tableView.types.multiWorkflow') : row.agent_type === 'react' ? t('agents.tableView.types.autonomousPlanning') : row.agent_type || ''
          const description = row.description || ''
          const iconBgColor = getAgentIconColor(row)
          const iconTextColor = getAgentIconTextColor(row)
          return (
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${iconBgColor} ${iconTextColor}`}>
                {row.icon}
              </div>
              <div className="min-w-0 flex-1">
                <div
                  className="font-semibold text-gray-900 cursor-pointer truncate"
                  onClick={() => navigate(`/dashboard/agents/${row.agent_id}`, { state: { botId: row.agent_id } })}
                >
                  {row.agent_name}
                </div>
                <div className="mt-1 text-xs text-gray-500 truncate">
                  {typeLabel && description ? `${typeLabel}｜${description}` : description || typeLabel || '-'}
                </div>
              </div>
            </div>
          )
        },
      },
      {
        key: 'model_name',
        title: t('agents.tableView.columns.model'),
        dataIndex: 'model_name',
        width: 200,
        render: ({ row }) => {
          const modelName = row.model_name === 'no model' ? null : row.model_name || row.model?.model_info.model_name || null
          if (!modelName) {
            return <span className="text-gray-400">{t('agents.agentList.noModel')}</span>
          }
          if (modelsLoading && !modelsData) {
            return <span className="text-gray-500">{t('agents.tableView.loading')}</span>
          }
          const isModelAvailable = availableModelNames.has(modelName)
          if (!isModelAvailable) {
            return (
              <Tooltip title={t('agents.agentList.modelDisabledTooltip')} disableInteractive placement="top">
                <div className="text-red-600 flex items-center gap-1 min-w-0">
                  <span className="truncate">{modelName}</span>
                  <Info className="w-3 h-3 flex-shrink-0" />
                </div>
              </Tooltip>
            )
          }
          return <span className="truncate block">{modelName}</span>
        },
      },
      // {
      //   key: 'relations',
      //   title: t('agents.tableView.columns.resources'),
      //   dataIndex: 'relation_count',
      //   minWidth: 200,
      //   render: ({ row }) => {
      //     const relation = row.relation_count
      //     const workflows = relation?.workflows ?? 0
      //     const knowledge = relation?.knowledge ?? 0
      //     const plugins = relation?.plugins ?? 0
      //     if (!relation) {
      //       return <span className="text-gray-400">-</span>
      //     }
      //     return (
      //       <div className="flex items-center gap-3 text-xs text-gray-700">
      //         <div className="flex items-center gap-1 min-w-[40px]">
      //           <BookOpen className="w-4 h-4 text-gray-500" />
      //           <span className="font-semibold">{knowledge}</span>
      //         </div>
 //         <div className="flex items-center gap-1 min-w-[40px]">
      //           <WorkflowIcon className="w-4 h-4 text-gray-500" />
      //           <span className="font-semibold">{workflows}</span>
      //         </div>
      //         <div className="flex items-center gap-1 min-w-[40px]">
      //           <PluginIcon className="w-4 h-4 text-gray-500" />
      //           <span className="font-semibold">{plugins}</span>
      //         </div>
      //       </div>
      //     )
      //   },
      // },
      // {
      //   key: 'publish_status',
      //   title: t('agents.tableView.columns.publishStatus'),
      //   dataIndex: 'publish_status',
      //   minWidth: 120,
      //   render: ({ row }) => {
      //     const isPublished = row.publish_status === 'published'
      //     return (
      //       <Chip
      //         size="small"
      //         label={isPublished ? t('agents.tableView.published') : t('agents.tableView.draft')}
      //         color={isPublished ? 'success' : 'default'}
      //         variant={isPublished ? 'filled' : 'outlined'}
      //       />
      //     )
      //   },
      // },
      {
        key: 'update_time',
        title: t('agents.tableView.columns.updateAt'),
        dataIndex: 'update_time',
        type: 'date',
        sortable: true,
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'create_time',
        title: t('agents.tableView.columns.createdAt'),
        dataIndex: 'create_time',
        type: 'date',
        sortable: true,
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'actions',
        title: t('agents.tableView.columns.actions'),
        type: 'operate',
        align: 'right',
        width: 180,
        minWidth: 180,
        operations: [
          {
            key: 'edit',
            icon: <Edit className="w-4 h-4" />,
            label: t('agents.agentCard.actions.edit'),
            tooltip: t('agents.agentCard.actions.edit'),
            onClick: row => navigate(`/dashboard/agents/${row.agent_id}`),
          },
          {
            key: 'copy',
            icon: <Copy className="w-4 h-4" />,
            label: t('agents.agentCard.actions.copy'),
            tooltip: t('common.tooltips.copyAgent'),
            onClick: row => onCopy(row),
          },
          {
            key: 'export',
            icon: <Download className="w-4 h-4" />,
            label: t('agents.agentCard.actions.export'),
            tooltip: t('agents.tableView.exportAgent'),
            onClick: row => onExport(row),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('agents.agentCard.actions.delete'),
            tooltip: t('common.tooltips.deleteAgent'),
            onClick: row => onDelete(row),
          },
        ],
      },
    ],
    [availableModelNames, modelsData, modelsLoading, onCopy, onExport, onDelete, navigate, t],
  )

  const tableData = useMemo(() => ({ columns, rows: agents }), [columns, agents])

  return (
    <ConfigTable
      tableData={tableData}
      loading={loading}
      remoteSort={true}
      onFetchData={onFetchData}
      onSortChange={onSortChange}
      defaultSort={defaultSort}
      size="small"
      stickyHeader
      emptyState={<Empty searchTerm={searchTerm} type="agents" />}
    />
  )
}

export default AgentTableView
