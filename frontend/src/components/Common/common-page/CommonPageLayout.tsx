import React, { useState, useCallback, useEffect } from 'react'
import { AlertCircle } from 'lucide-react'
import { CircularProgress, Tab, Tabs } from '@mui/material'
import { Pagination } from '../common-table'
import { ViewToggle } from './ViewToggle'

export type ViewType = 'grid' | 'table'
import type { PagerState, PagerChangeHandler } from '../common-table/Pagination'

export interface TabConfig {
  key: string
  label: string
}

const LoadingState: React.FC = () => (
  <div className="flex items-center justify-center py-12">
    <CircularProgress className="text-blue-500 dark:text-blue-400" />
  </div>
)

// Internal PageHeader component
interface PageHeaderProps {
  title: string
  tabs?: TabConfig[]
  activeTab?: string
  onTabChange?: (key: string) => void
  viewType?: ViewType
  onViewTypeChange?: (type: ViewType) => void
  showViewToggle?: boolean
  toolbarLeft?: React.ReactNode
  toolbarRight?: React.ReactNode
  className?: string
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  tabs,
  activeTab,
  onTabChange,
  viewType = 'grid',
  onViewTypeChange,
  showViewToggle = false,
  toolbarLeft,
  toolbarRight,
  className = '',
}) => {
  return (
    <div className={`mb-4 ${className}`}>
      <div className="mb-4 mt-6">
        <span className="text-[20px] font-semibold text-[#1F2937] dark:text-gray-100">{title}</span>
      </div>

      {tabs && tabs.length > 0 && (
        <div className="mb-4">
          <Tabs
            value={activeTab}
            onChange={(_event, newValue) => onTabChange?.(newValue)}
            sx={{
              height: '32px !important',
              minHeight: '32px !important',
              '& .MuiTab-root': {
                px: 0,
                height: '28px !important',
                minHeight: '28px !important',
                pb: 2,
                mr: 2,
                minWidth: 'auto',
                fontSize: '0.875rem',
              },
            }}
          >
            {tabs.map(tab => (
              <Tab key={tab.key} value={tab.key} label={tab.label} disableRipple />
            ))}
          </Tabs>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">{toolbarLeft}</div>

        <div className="flex items-center space-x-2">
          {showViewToggle && onViewTypeChange && <ViewToggle viewType={viewType} onChange={onViewTypeChange} />}
          {toolbarRight}
        </div>
      </div>
    </div>
  )
}

export interface CommonPageLayoutProps {
  title: string

  // Tabs
  tabs?: TabConfig[]
  defaultTabKey?: string
  onTabChange?: (key: string) => void

  defaultViewType?: ViewType
  viewType?: ViewType
  onViewTypeChange?: (type: ViewType) => void
  showViewToggle?: boolean

  // 视图渲染
  gridView?: React.ReactNode
  tableView?: React.ReactNode

  // 工具栏
  toolbarLeft?: React.ReactNode
  toolbarRight?: React.ReactNode

  // Pagination
  pager: PagerState
  onPagerChange?: PagerChangeHandler
  showPagination?: boolean

  loading?: boolean
  error?: string | null

  renderContentAbove?: () => React.ReactNode
  renderContentBelow?: () => React.ReactNode

  renderPagination?: () => React.ReactNode

  className?: string
}

function CommonPageLayoutInner(props: CommonPageLayoutProps) {
  const {
    title,
    tabs,
    defaultTabKey,
    onTabChange,
    defaultViewType = 'grid',
    viewType: controlledViewType,
    onViewTypeChange,
    showViewToggle = true,
    gridView,
    tableView,
    toolbarLeft,
    toolbarRight,
    pager,
    onPagerChange,
    showPagination = true,
    loading: externalLoading,
    error,
    renderContentAbove,
    renderContentBelow,
    renderPagination,
    className,
  } = props

  const [internalViewType, setInternalViewType] = useState<ViewType>(defaultViewType)
  const [activeTab, setActiveTab] = useState<string>(defaultTabKey || tabs?.[0]?.key || '')

  const handleTabChange = useCallback(
    (key: string) => {
      setActiveTab(key)
      onTabChange?.(key)
    },
    [onTabChange],
  )

  // 视图切换时的内部 loading 状态
  const [isViewSwitching, setIsViewSwitching] = useState(false)

  const viewType = controlledViewType !== undefined ? controlledViewType : internalViewType

  // 合并外部 loading 和内部视图切换 loading
  const effectiveLoading = externalLoading || isViewSwitching

  // 监听外部 loading 变化，当加载完成时重置视图切换状态
  useEffect(() => {
    if (!externalLoading && isViewSwitching) {
      setIsViewSwitching(false)
    }
  }, [externalLoading, isViewSwitching])

  const handleViewTypeChange = useCallback(
    (type: ViewType) => {
      // 如果视图类型真的改变了，设置 loading 状态
      if (type !== viewType) {
        setIsViewSwitching(true)
      }

      if (onViewTypeChange) {
        onViewTypeChange(type)
      } else {
        setInternalViewType(type)
      }
    },
    [onViewTypeChange, viewType],
  )

  const handlePageChange = useCallback(
    (page: number, pageSize: number) => {
      if (onPagerChange) {
        onPagerChange(page, pageSize)
      }
    },
    [onPagerChange],
  )

  return (
    <div className={`h-full flex flex-col bg-[#F8F9FC] dark:bg-gray-900 px-6 ${className || ''}`}>
      <PageHeader
        title={title}
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        viewType={viewType}
        onViewTypeChange={handleViewTypeChange}
        showViewToggle={showViewToggle}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
      />

      {error && (
        <div className="mx-6 mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-[4px] p-3">
          <div className="flex items-center">
            <AlertCircle className="w-4 h-4 text-red-500 dark:text-red-400 mr-2" />
            <span className="text-red-800 dark:text-red-300 text-sm">{error}</span>
          </div>
        </div>
      )}

      {renderContentAbove?.()}

      <div className="flex-1 overflow-hidden flex flex-col" key={`tab-${activeTab}-view-${viewType}`}>
        {effectiveLoading ? (
          <LoadingState />
        ) : viewType === 'grid' && gridView ? (
          <div className="flex-1 min-h-0 overflow-auto pt-2">{gridView}</div>
        ) : viewType === 'table' && tableView ? (
          <div className="h-full">{tableView}</div>
        ) : null}
      </div>

      {renderContentBelow?.()}

      {showPagination && pager.total > 0 && (
        <div className="border-t border-[#e5e7eb] dark:border-gray-700 px-6 pt-4 mb-4">
          {renderPagination ? (
            renderPagination()
          ) : (
            <div className="flex items-center justify-end">
              <Pagination pager={pager} loading={effectiveLoading} onPagerChange={handlePageChange} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export const CommonPageLayout = CommonPageLayoutInner as (
  props: CommonPageLayoutProps & { key?: string | number },
) => React.ReactElement | null

export default CommonPageLayout
