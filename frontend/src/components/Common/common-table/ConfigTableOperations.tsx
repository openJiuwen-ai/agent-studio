import React from 'react'
import { Box, IconButton, Menu, MenuItem, Tooltip } from '@mui/material'
import { Ellipsis } from 'lucide-react'
import { TableOperation } from './types'

export interface ActionMenuProps<T> {
  rowId: string | number
  anchorEl: HTMLElement | null
  operations: TableOperation<T>[]
  row: T
  rowIndex: number
  onClose: () => void
}

/**
 * ActionMenu component - renders the operations menu for table rows
 * Shows only overflow operations (from index 3 onwards) to avoid duplication with primary buttons
 */
export function ActionMenu<T extends object>({
  rowId,
  anchorEl,
  operations,
  row,
  rowIndex,
  onClose,
}: ActionMenuProps<T>) {
  const visibleOperations = operations.filter(op =>
    typeof op.visible === 'function' ? op.visible(row, rowIndex) : (op.visible ?? true),
  )
  // Only show overflow operations (4th onwards), first 3 are shown as buttons
  const overflowOperations = visibleOperations.slice(3)

  const handleOperationClick = (op: TableOperation<T>) => {
    onClose()
    op.onClick?.(row, rowIndex)
  }

  return (
    <Menu
      anchorEl={anchorEl}
      open={Boolean(anchorEl)}
      onClose={onClose}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'right',
      }}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'right',
      }}
      slotProps={{
        paper: {
          sx: {
            maxHeight: 300,
            overflow: 'auto',
          },
        },
      }}
    >
      {overflowOperations.map(op => {
        const disabled = typeof op.disabled === 'function' ? op.disabled(row, rowIndex) : (op.disabled ?? false)
        const icon = typeof op.icon === 'function' ? op.icon(row, rowIndex) : op.icon
        const tooltip = typeof op.tooltip === 'function' ? op.tooltip(row, rowIndex) : op.tooltip
        const menuItem = (
          <MenuItem
            key={op.key}
            disabled={disabled}
            onClick={() => handleOperationClick(op)}
            sx={op.danger ? { color: '#DC2626', '&:hover': { backgroundColor: 'rgba(220, 38, 38, 0.08)' } } : undefined}
          >
            {icon && (
              <Box component="span" mr={1} display="inline-flex">
                {icon}
              </Box>
            )}
            {op.label}
          </MenuItem>
        )
        return tooltip ? (
          <Tooltip key={op.key} title={tooltip}>
            <span>{menuItem}</span>
          </Tooltip>
        ) : (
          menuItem
        )
      })}
    </Menu>
  )
}

export interface ActionButtonsRenderProps<T> {
  operations: TableOperation<T>[]
  row: T
  rowIndex: number
  rowId: string | number
  columnKey: string
  onOpenMenu: (event: React.MouseEvent<HTMLElement>, rowId: string | number, columnKey: string) => void
  isMenuOpen: boolean
}

/**
 * ActionButtons - Renders the primary operation buttons and overflow menu button
 */
export function ActionButtons<T extends object>({
  operations,
  row,
  rowIndex,
  rowId,
  columnKey,
  onOpenMenu,
  isMenuOpen,
}: ActionButtonsRenderProps<T>) {
  const visibleOperations = operations.filter(op =>
    typeof op.visible === 'function' ? op.visible(row, rowIndex) : (op.visible ?? true),
  )
  const primary = visibleOperations.slice(0, 3)
  const overflow = visibleOperations.slice(3)

  return (
    <Box
      display="flex"
      alignItems="center"
      gap={1}
      sx={{
        minWidth: 'fit-content',
      }}
    >
      {primary.map((op) => {
        const disabled = typeof op.disabled === 'function' ? op.disabled(row, rowIndex) : (op.disabled ?? false)
        const icon = typeof op.icon === 'function' ? op.icon(row, rowIndex) : op.icon
        const tooltip = typeof op.tooltip === 'function' ? op.tooltip(row, rowIndex) : op.tooltip
        const button = (
          <IconButton
            size="small"
            disabled={disabled}
            onClick={event => {
              event.stopPropagation()
              op.onClick?.(row, rowIndex)
            }}
            sx={op.danger ? { color: '#DC2626', '&:hover': { backgroundColor: 'rgba(220, 38, 38, 0.08)' } } : undefined}
          >
            {icon ?? <Box sx={{ fontSize: '0.75rem', fontWeight: 500 }}>{op.label}</Box>}
          </IconButton>
        )
        return tooltip ? <Tooltip key={op.key} title={tooltip}><span>{button}</span></Tooltip> : button
      })}
      {overflow.length > 0 && (
        <IconButton size="small" onClick={event => onOpenMenu(event, rowId, columnKey)}>
          <Ellipsis className="w-4 h-4" />
        </IconButton>
      )}
    </Box>
  )
}

export { ActionButtons as default }
