import React, { useCallback, useImperativeHandle, useMemo, useState } from 'react'
import { Box, Checkbox, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material'
import { ConfigTableHeader } from './ConfigTableHeader'
import { ConfigTableBody } from './ConfigTableBody'
import { ConfigTableFilterMenu } from './ConfigTableFilterMenu'
import { ActionMenu } from './ConfigTableOperations'
import { useTableSelection } from './hooks/useTableSelection'
import { useTableColumnResize } from './hooks/useTableColumnResize'
import {
  ConfigTableProps,
  ConfigTableRef,
  TableItemProps,
  SortOrder,
  ColumnFilterState,
  SortState,
  FilterValue,
  TableStyles,
} from './types'
import { applyLocalFilterAndSort, extractSlotMap } from './utils'

// Re-export types for convenience
export type {
  ConfigTableProps,
  ConfigTableRef,
  TableItemProps,
  SortOrder,
  ColumnFilterState,
  SortState,
  FilterValue,
  TableStyles,
} from './types'

// Default styles
const DEFAULT_CONTAINER_SX = { backgroundColor: 'var(--table-bg-container)' }

const DEFAULT_TABLE_STYLES: TableStyles = {
  tableCell: {
    head: {
      backgroundColor: 'var(--table-bg-cell)',
      color: 'var(--table-text-head)',
      fontWeight: 500,
      fontSize: 'var(--table-font-size)',
    },
    body: {
      fontSize: 'var(--table-font-size)',
      backgroundColor: 'var(--table-bg-cell)',
    },
  },
  tableRow: {
    root: {
      height: 'var(--table-row-height)',
    },
    hover: {
      '& .MuiTableCell-body': {
        backgroundColor: 'var(--table-bg-cell-hover)',
      },
    },
  },
}

export const TableItem: React.FC<TableItemProps> = () => null

TableItem.displayName = 'ConfigTableItem'

function createConfigTableInner<T extends object>(props: ConfigTableProps<T>, ref: React.Ref<ConfigTableRef<T>>) {
  const {
    tableData,
    onFetchData,
    remoteFilter: remoteFilterProp,
    remoteSort: remoteSortProp,
    onFilterChange,
    onSortChange,
    defaultSort,
    enableSelection,
    selectionKey,
    getRowId,
    selectedRowIds,
    onSelectionChange,
    columnResizePersistenceKey,
    onColumnWidthChange,
    size,
    loading,
    stickyHeader,
    className,
    containerSx,
    tableSx,
    tableStyles,
    emptyState,
    children,
  } = props

  const remoteFilter = remoteFilterProp ?? !!onFetchData
  const remoteSort = remoteSortProp ?? !!onFetchData

  const [filters, setFilters] = useState<ColumnFilterState>({})
  const [draftFilters, setDraftFilters] = useState<ColumnFilterState>({})
  const [sort, setSort] = useState<SortState>(() => defaultSort ?? { field: null, order: null })

  const [operationMenuState, setOperationMenuState] = useState<{
    anchorEl: HTMLElement | null
    rowId: string | number | null
    columnKey: string | null
  }>({
    anchorEl: null,
    rowId: null,
    columnKey: null,
  })

  const [filterMenuState, setFilterMenuState] = useState<{
    anchorEl: HTMLElement | null
    columnKey: string | null
  }>({
    anchorEl: null,
    columnKey: null,
  })

  const allRows = tableData.rows || []
  const columns = tableData.columns || []

  const slotMap = useMemo(() => extractSlotMap(children), [children])

  // Merge default styles with user-provided styles
  const mergedContainerSx = useMemo(
    () => ({
      ...DEFAULT_CONTAINER_SX,
      ...containerSx,
    }),
    [containerSx],
  )

  const mergedTableStyles = useMemo(
    () => ({
      tableCell: {
        ...DEFAULT_TABLE_STYLES.tableCell,
        ...tableStyles?.tableCell,
        head: {
          ...DEFAULT_TABLE_STYLES.tableCell?.head,
          ...tableStyles?.tableCell?.head,
        },
        body: {
          ...DEFAULT_TABLE_STYLES.tableCell?.body,
          ...tableStyles?.tableCell?.body,
        },
      },
      tableRow: {
        ...DEFAULT_TABLE_STYLES.tableRow,
        ...tableStyles?.tableRow,
        root: {
          ...DEFAULT_TABLE_STYLES.tableRow?.root,
          ...tableStyles?.tableRow?.root,
        },
        hover: {
          ...DEFAULT_TABLE_STYLES.tableRow?.hover,
          ...tableStyles?.tableRow?.hover,
        },
        selected: {
          ...DEFAULT_TABLE_STYLES.tableRow?.selected,
          ...tableStyles?.tableRow?.selected,
        },
      },
    }),
    [tableStyles],
  )

  // Column resize hook
  const { columnWidths, handleColumnResizeMouseDown, totalColumnsMinWidth } = useTableColumnResize({
    columns,
    columnResizePersistenceKey,
    onColumnWidthChange,
  })

  // Process rows (filter and sort)
  const processedRows = useMemo(() => {
    const baseRows = allRows
    const filteredSorted = applyLocalFilterAndSort(
      baseRows,
      columns,
      remoteFilter ? {} : filters,
      remoteSort ? { field: null, order: null } : sort,
    )
    return filteredSorted
  }, [allRows, columns, filters, sort, remoteFilter, remoteSort])

  // Selection hook
  const { effectiveSelectedIds, selectedRows, clearSelection, handleToggleRow, handleToggleAllCurrentPage, getRowSelectionState } =
    useTableSelection(processedRows, {
      rows: allRows,
      enableSelection,
      selectionKey,
      getRowId,
      selectedRowIds,
      onSelectionChange,
    })

  // Expose ref methods
  useImperativeHandle(
    ref,
    () => ({
      getSelectedRows: () => selectedRows,
      clearSelection: () => {
        clearSelection()
      },
    }),
    [selectedRows, clearSelection],
  )

  // Check if all rows on current page are selected
  const allRowIdsOnPage = processedRows.map((row, index) => {
    const { id } = getRowSelectionState(row, index)
    return id
  })
  const allSelectedOnPage = allRowIdsOnPage.length > 0 && allRowIdsOnPage.every(id => effectiveSelectedIds.includes(id))
  const hasAnyGlobalSelection = effectiveSelectedIds.length > 0
  const someSelectedOnPage = hasAnyGlobalSelection && !allSelectedOnPage

  // Filter handlers
  const handleFilterChange = useCallback((columnKey: string, value: FilterValue) => {
    setDraftFilters(prev => ({
      ...prev,
      [columnKey]: value,
    }))
  }, [])

  const handleApplyFilters = useCallback(
    (overrideFilters?: ColumnFilterState) => {
      const nextFilters = overrideFilters ?? draftFilters
      setFilters(nextFilters)
      setDraftFilters(nextFilters)
      onFilterChange?.(nextFilters)
      if (remoteFilter && onFetchData) {
        onFetchData({
          field: sort.field,
          order: sort.order,
          filters: nextFilters,
        })
      }
    },
    [draftFilters, sort, onFilterChange, remoteFilter, onFetchData],
  )

  // Sort handler
  const handleSortChange = useCallback(
    (columnKey: string) => {
      const column = columns.find(c => c.key === columnKey)
      const sortFieldValue = column?.sortField || columnKey
      const currentSort = sort
      const isSameField = currentSort.field === sortFieldValue
      let nextSort: SortState
      if (!isSameField) {
        nextSort = { field: sortFieldValue, order: 'desc' }
      } else if (currentSort.order === 'desc') {
        nextSort = { field: sortFieldValue, order: 'asc' as SortOrder }
      } else if (currentSort.order === 'asc') {
        nextSort = { field: null, order: null }
      } else {
        nextSort = { field: sortFieldValue, order: 'desc' as SortOrder }
      }

      if (remoteSort) {
        setSort(nextSort)
        onSortChange?.(nextSort)
        return
      }

      setSort(nextSort)
    },
    [sort, remoteSort, onSortChange, columns],
  )

  // Menu handlers
  const handleOpenFilterMenu = useCallback((event: React.MouseEvent<HTMLElement>, columnKey: string) => {
    event.stopPropagation()
    setFilterMenuState({
      anchorEl: event.currentTarget,
      columnKey,
    })
  }, [])

  const handleCloseFilterMenu = useCallback(() => {
    setFilterMenuState({
      anchorEl: null,
      columnKey: null,
    })
  }, [])

  const handleOpenOperationMenu = useCallback((event: React.MouseEvent<HTMLElement>, rowId: string | number, columnKey: string) => {
    event.stopPropagation()
    setOperationMenuState({
      anchorEl: event.currentTarget,
      rowId,
      columnKey,
    })
  }, [])

  const handleCloseOperationMenu = useCallback(() => {
    setOperationMenuState({
      anchorEl: null,
      rowId: null,
      columnKey: null,
    })
  }, [])

  // Get active filter column
  const activeFilterColumn = useMemo(
    () => columns.find(column => column.key === filterMenuState.columnKey) ?? null,
    [columns, filterMenuState.columnKey],
  )

  return (
    <TableContainer
      component={Paper}
      className={className}
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'none',
        ...mergedContainerSx,
      }}
    >
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflowX: 'auto',
          overflowY: 'auto',
        }}
      >
        <Table
          stickyHeader={stickyHeader}
          size={size ?? 'medium'}
          sx={{
            minWidth: Math.max(650, (totalColumnsMinWidth || 0) + (enableSelection ? 50 : 0)),
            tableLayout: 'fixed',
            width: '100%',
            ...tableSx,
          }}
        >
          <colgroup>
            {enableSelection && <col style={{ width: 50 }} />}
            {columns.map(column => (
              <col
                key={column.key}
                style={{
                  width: columnWidths[column.key] ?? column.width,
                }}
              />
            ))}
          </colgroup>
          <TableHead>
            <TableRow>
              {enableSelection && (
                <TableCell
                  padding="checkbox"
                  align="center"
                  sx={{
                    width: 50,
                    minWidth: 50,
                    maxWidth: 50,
                    position: 'sticky',
                    left: 0,
                    zIndex: 2,
                    ...mergedTableStyles?.tableCell?.head,
                  }}
                >
                  <Checkbox indeterminate={someSelectedOnPage} checked={allSelectedOnPage} onChange={() => handleToggleAllCurrentPage(processedRows)} />
                </TableCell>
              )}
              <ConfigTableHeader
                columns={columns}
                sortState={sort}
                filters={filters}
                columnWidths={columnWidths}
                tableStyles={mergedTableStyles}
                onSortChange={handleSortChange}
                onOpenFilterMenu={handleOpenFilterMenu}
                onColumnResizeMouseDown={handleColumnResizeMouseDown}
              />
            </TableRow>
          </TableHead>
          <TableBody>
            <ConfigTableBody
              rows={processedRows}
              columns={columns}
              columnWidths={columnWidths}
              tableStyles={mergedTableStyles}
              slotMap={slotMap}
              enableSelection={enableSelection ?? false}
              selectionKey={selectionKey}
              getRowId={getRowId}
              effectiveSelectedIds={effectiveSelectedIds}
              onToggleRow={handleToggleRow}
              onOpenOperationMenu={handleOpenOperationMenu}
              operationMenuState={operationMenuState}
            />
            {processedRows.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={(columns.length || 1) + (enableSelection ? 1 : 0)}
                  align="center"
                  sx={{
                    py: size === 'small' ? 6 : 8,
                    borderBottom: 0,
                    color: 'text.secondary',
                  }}
                >
                  {emptyState ?? (
                    <Box display="flex" alignItems="center" justifyContent="center">
                      <Box>
                        <Box fontSize={16} fontWeight={600} mb={0.5}>
                          {loading ? 'Loading...' : 'No data'}
                        </Box>
                        {!loading && <Box fontSize={13}>Try adjusting filters or changing your search.</Box>}
                      </Box>
                    </Box>
                  )}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>

      {/* Filter Menu */}
      <ConfigTableFilterMenu
        column={activeFilterColumn}
        anchorEl={filterMenuState.anchorEl}
        draftFilters={draftFilters}
        onFilterChange={handleFilterChange}
        onApply={handleApplyFilters}
        onClose={handleCloseFilterMenu}
      />

      {/* Operations Menu */}
      {operationMenuState.anchorEl && operationMenuState.rowId !== null && (
        <ActionMenu
          rowId={operationMenuState.rowId}
          anchorEl={operationMenuState.anchorEl}
          operations={
            columns.find(c => c.key === operationMenuState.columnKey)?.operations ?? []
          }
          row={processedRows.find(r => getRowSelectionState(r, processedRows.indexOf(r)).id === operationMenuState.rowId)!}
          rowIndex={processedRows.findIndex(r => getRowSelectionState(r, processedRows.indexOf(r)).id === operationMenuState.rowId)}
          onClose={handleCloseOperationMenu}
        />
      )}
    </TableContainer>
  )
}

const ConfigTableInner = React.forwardRef(createConfigTableInner) as <T extends object>(
  props: ConfigTableProps<T> & { ref?: React.Ref<ConfigTableRef<T>> },
) => React.ReactElement | null

export const ConfigTable = ConfigTableInner

export default ConfigTableInner
