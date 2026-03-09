import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Copy, Edit, Trash2 } from 'lucide-react'
import { ConfigTable } from '@/components/Common/common-table'
import { type SortState, type TableColumn, type RemoteQueryParams } from '@/components/Common/common-table'
import { Empty } from '@/components/Common/Empty'
import WorkflowIcon from '@/assets/icons/workflow.svg?react'
import dayjs from 'dayjs'
import { Workflow } from '../../../utils/workflowUtils'
import { isWorkflowNewlyImported, clearNewlyImportedFlag } from '../../../utils/newlyImportedWorkflows'

interface WorkflowTableViewProps {
  workflows: Workflow[]
  loading?: boolean
  searchTerm?: string
  onCopy: (workflowId: string, spaceId: string, workflowName: string) => void
  onDelete: (workflowId: string, workflowName: string, workflowVersion?: string) => void
  onFetchData?: (params: RemoteQueryParams) => void
  onSortChange?: (sort: SortState) => void
  defaultSort?: SortState
}

export const WorkflowTableView: React.FC<WorkflowTableViewProps> = ({
  workflows,
  loading = false,
  searchTerm = '',
  onCopy,
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

  const columns: TableColumn<Workflow>[] = useMemo(
    () => [
      {
        key: 'name',
        title: t('workflows.workflowList.name'),
        dataIndex: 'name',
        minWidth: 260,
        width: 600,
        sortable: true,
        sortField: 'name',
        render: ({ row }) => {
          const isNewlyImported = isWorkflowNewlyImported(row.workflow_id)

          return (
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${
                isNewlyImported ? 'bg-green-100 text-green-600' : 'bg-blue-50 text-blue-600'
              }`}>
                <WorkflowIcon className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <div
                    className="font-semibold text-gray-900 cursor-pointer truncate"
                    onClick={() => {
                      // Clear newly imported flag when user opens workflow
                      if (isNewlyImported) {
                        clearNewlyImportedFlag(row.workflow_id)
                      }
                      navigate(`/dashboard/workflows/editor/${row.workflow_id}?spaceId=${row.space_id}`)
                    }}
                  >
                    {row.name}
                  </div>
                  {isNewlyImported && (
                    <span className="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold rounded-full bg-green-100 text-green-700">
                      IMPORTED
                    </span>
                  )}
                </div>
                <div className="mt-1 text-xs text-gray-500 truncate">{row.desc || '-'}</div>
              </div>
            </div>
          )
        },
      },
      {
        key: 'update_time',
        title: t('workflows.workflowList.updatedAt'),
        dataIndex: 'update_time',
        type: 'date',
        sortable: true,
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'create_time',
        title: t('workflows.workflowList.createdAt'),
        dataIndex: 'create_time',
        type: 'date',
        sortable: true,
        width: 170,
        dateFormatter: formatDateValue,
      },
      {
        key: 'actions',
        title: t('workflows.workflowList.actions'),
        type: 'operate',
        align: 'right',
        width: 180,
        minWidth: 180,
        operations: [
          {
            key: 'edit',
            icon: <Edit className="w-4 h-4" />,
            label: t('workflows.workflowList.editWorkflow'),
            tooltip: t('workflows.workflowList.editWorkflow'),
            onClick: row => {
              // Clear newly imported flag when user edits workflow
              if (isWorkflowNewlyImported(row.workflow_id)) {
                clearNewlyImportedFlag(row.workflow_id)
              }
              navigate(`/dashboard/workflows/editor/${row.workflow_id}?spaceId=${row.space_id}`)
            },
          },
          {
            key: 'copy',
            icon: <Copy className="w-4 h-4" />,
            label: t('workflows.workflowList.copyWorkflow'),
            tooltip: t('common.tooltips.copyWorkflow'),
            onClick: row => onCopy(row.workflow_id, row.space_id, row.name),
          },
          {
            key: 'delete',
            icon: <Trash2 className="w-4 h-4" />,
            label: t('workflows.workflowList.deleteWorkflow'),
            tooltip: t('common.tooltips.deleteWorkflow'),
            onClick: row => onDelete(row.workflow_id, row.name, row.workflow_version),
          },
        ],
      },
    ],
    [navigate, onCopy, onDelete, t],
  )

  const tableData = useMemo(() => ({ columns, rows: workflows }), [columns, workflows])

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
      emptyState={<Empty searchTerm={searchTerm} type="workflows" />}
    />
  )
}

export default WorkflowTableView
