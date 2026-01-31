export type SortOrder = 'asc' | 'desc'

export interface DateRangeFilter {
  from?: string | null
  to?: string | null
}

export type FilterValue = string | number | boolean | Array<string | number> | DateRangeFilter | null | undefined

export interface CellRenderParams<T> {
  row: T
  value: unknown
  rowIndex: number
  column: TableColumn<T>
}

export type TableColumnType = 'text' | 'date' | 'operate'

export interface TableOperation<T> {
  key: string
  label?: React.ReactNode
  icon?: React.ReactNode | ((row: T, rowIndex: number) => React.ReactNode)
  tooltip?: React.ReactNode | ((row: T, rowIndex: number) => React.ReactNode)
  onClick?: (row: T, rowIndex: number) => void
  disabled?: boolean | ((row: T, rowIndex: number) => boolean)
  danger?: boolean
}

export interface TableColumn<T> {
  key: string
  title: React.ReactNode
  dataIndex?: keyof T & string
  width?: number
  minWidth?: number
  maxWidth?: number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  /** Sort field for remote sorting. Defaults to column.key if not specified. */
  sortField?: string
  filterable?: boolean
  filterType?: 'text' | 'select' | 'dateRange'
  filterOptions?: { label: string; value: string | number }[]
  filterMultiple?: boolean
  render?: (params: CellRenderParams<T>) => React.ReactNode
  type?: TableColumnType
  /** Required when type is 'date'. Provides date formatting logic from business layer. */
  dateFormatter?: (value: unknown, row: T, rowIndex: number, column: TableColumn<T>) => React.ReactNode
  operations?: TableOperation<T>[]
}

export type ColumnFilterState = Record<string, FilterValue>

export interface SortState {
  field: string | null
  order: SortOrder | null
}

/**
 * Remote query parameters for sorting and filtering.
 * Note: Pagination is managed by parent components (e.g., CommonPageLayout),
 * not by ConfigTable directly.
 */
export interface RemoteQueryParams {
  field?: string | null
  order?: SortOrder | null
  filters?: ColumnFilterState
}

/**
 * Table data structure.
 * Note: Pagination state is managed by parent components (e.g., CommonPageLayout),
 * not included in TableData.
 */
export interface TableData<T> {
  columns: TableColumn<T>[]
  rows: T[]
}

export interface TableStyles {
  tableRow?: {
    root?: any
    hover?: any
    selected?: any
  }
  tableCell?: {
    head?: any
    body?: any
  }
}

export interface ConfigTableProps<T> {
  tableData: TableData<T>
  onFetchData?: (params: RemoteQueryParams) => void | Promise<void>

  remoteFilter?: boolean
  remoteSort?: boolean

  onFilterChange?: (filters: ColumnFilterState) => void
  onSortChange?: (sort: SortState) => void

  defaultSort?: SortState

  enableSelection?: boolean
  selectionKey?: keyof T & string
  getRowId?: (row: T) => string | number
  selectedRowIds?: Array<string | number>
  onSelectionChange?: (selectedRows: T[], selectedIds: Array<string | number>) => void

  columnResizePersistenceKey?: string
  onColumnWidthChange?: (columnKey: string, width: number) => void

  size?: 'small' | 'medium'
  loading?: boolean
  stickyHeader?: boolean
  className?: string
  containerSx?: any
  tableSx?: any
  tableStyles?: TableStyles
  emptyState?: React.ReactNode
  children?: React.ReactNode
}

export interface ConfigTableRef<T> {
  getSelectedRows: () => T[]
  clearSelection: () => void
}

export interface TableItemProps {
  columnKey: string
  children: React.ReactElement
}
