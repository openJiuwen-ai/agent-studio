import React from 'react'
import { Box, Checkbox, TableCell, TableRow } from '@mui/material'
import { TableColumn, TableStyles } from './types'
import { getDefaultRowId } from './utils'
import { ActionButtons } from './ConfigTableOperations'

export interface ConfigTableBodyProps<T> {
  rows: T[]
  columns: TableColumn<T>[]
  columnWidths: Record<string, number>
  tableStyles?: TableStyles
  slotMap: Record<string, React.ReactElement>
  enableSelection: boolean
  selectionKey?: keyof T & string
  getRowId?: (row: T) => string | number
  effectiveSelectedIds: Array<string | number>
  onToggleRow: (row: T, index: number) => void
  onOpenOperationMenu: (event: React.MouseEvent<HTMLElement>, rowId: string | number, columnKey: string) => void
  operationMenuState: {
    anchorEl: HTMLElement | null
    rowId: string | number | null
    columnKey: string | null
  }
}

/**
 * ConfigTableBody component - renders the table body with rows
 */
export function ConfigTableBody<T extends object>({
  rows,
  columns,
  columnWidths,
  tableStyles,
  slotMap,
  enableSelection,
  selectionKey,
  getRowId,
  effectiveSelectedIds,
  onToggleRow,
  onOpenOperationMenu,
  operationMenuState,
}: ConfigTableBodyProps<T>) {
  const getRowIdInternal = (row: T, index: number) => getDefaultRowId(row, index, selectionKey, getRowId)

  return (
    <>
      {rows.map((row, rowIndex) => {
        const rowId = getRowIdInternal(row, rowIndex)
        const isSelected = effectiveSelectedIds.includes(rowId)
        return (
          <TableRow
            hover
            key={rowId}
            selected={isSelected}
            sx={{
              ...tableStyles?.tableRow?.root,
              '&:hover': {
                ...tableStyles?.tableRow?.hover,
              },
            }}
          >
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
                  zIndex: 1,
                  ...tableStyles?.tableCell?.body,
                }}
              >
                <Checkbox checked={isSelected} onChange={() => onToggleRow(row, rowIndex)} />
              </TableCell>
            )}
            {columns.map(column => {
              const dataKey = (column.dataIndex ?? (column.key as keyof T & string)) as keyof T
              const value = (row as any)[dataKey]
              const slot = slotMap[column.key]
              let content: React.ReactNode
              if (slot) {
                content = React.cloneElement(
                  slot as React.ReactElement<any>,
                  {
                    row,
                    value,
                    rowIndex,
                    column,
                  } as any,
                )
              } else if (column.render) {
                content = column.render({
                  row,
                  value,
                  rowIndex,
                  column,
                })
              } else if (column.type === 'date') {
                if (column.dateFormatter) {
                  content = column.dateFormatter(value, row, rowIndex, column)
                } else {
                  content = (
                    <Box component="span" sx={{ color: 'error.main', fontSize: '0.75rem' }}>
                      dateFormatter required
                    </Box>
                  )
                }
              } else if (column.type === 'operate') {
                const operations = column.operations ?? []
                if (operations.length === 0) {
                  content = null
                } else {
                  const isMenuOpen = operationMenuState.rowId === rowId && operationMenuState.columnKey === column.key
                  content = (
                    <ActionButtons
                      operations={operations}
                      row={row}
                      rowIndex={rowIndex}
                      rowId={rowId}
                      columnKey={column.key}
                      onOpenMenu={onOpenOperationMenu}
                      isMenuOpen={isMenuOpen}
                    />
                  )
                }
              } else {
                content = value === undefined || value === null ? '' : String(value)
              }
              const width = columnWidths[column.key] ?? column.width
              return (
                <TableCell
                  key={column.key}
                  align={column.align}
                  sx={{
                    width: width,
                    minWidth: column.minWidth ?? 80,
                    maxWidth: column.maxWidth,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    ...tableStyles?.tableCell?.body,
                  }}
                >
                  {content}
                </TableCell>
              )
            })}
          </TableRow>
        )
      })}
    </>
  )
}

export default ConfigTableBody
