// Main export
export { default as ConfigTable, TableItem } from './ConfigTable'

// Types
export type {
  TableColumn,
  TableData,
  TableStyles,
  ConfigTableProps,
  ConfigTableRef,
  RemoteQueryParams,
  SortState,
  SortOrder,
  CellRenderParams,
  TableColumnType,
  TableOperation,
  ColumnFilterState,
  DateRangeFilter,
  FilterValue,
  TableItemProps,
} from './types'

// Sub-components (for advanced use cases)
export { default as ConfigTableHeader } from './ConfigTableHeader'
export { default as ConfigTableBody } from './ConfigTableBody'
export { default as ConfigTableFilterMenu } from './ConfigTableFilterMenu'
export { ActionButtons as default, ActionMenu } from './ConfigTableOperations'

// Hooks
export { useTableSelection, useTableColumnResize } from './hooks'
export type { UseTableSelectionProps, UseTableSelectionReturn } from './hooks/useTableSelection'
export type { UseTableColumnResizeProps, UseTableColumnResizeReturn } from './hooks/useTableColumnResize'

// Utils
export { getDefaultRowId, applyLocalFilterAndSort, hasActiveFilter, extractSlotMap } from './utils'

// Legacy exports
export { default as Pagination } from './Pagination'
