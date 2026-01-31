import React from 'react'
import { Box, Button, Checkbox, Menu, MenuItem, Radio, TextField } from '@mui/material'
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import dayjs from 'dayjs'
import { TableColumn, FilterValue, DateRangeFilter, ColumnFilterState } from './types'

export interface ConfigTableFilterMenuProps<T> {
  column: TableColumn<T> | null
  anchorEl: HTMLElement | null
  draftFilters: ColumnFilterState
  onFilterChange: (columnKey: string, value: FilterValue) => void
  onApply: (nextFilters?: ColumnFilterState) => void
  onClose: () => void
}

/**
 * ConfigTableFilterMenu component - renders the filter menu for table columns
 */
export function ConfigTableFilterMenu<T extends object>({
  column,
  anchorEl,
  draftFilters,
  onFilterChange,
  onApply,
  onClose,
}: ConfigTableFilterMenuProps<T>) {
  if (!column) return null

  const handleReset = () => {
    const key = column.key
    let clearedValue: FilterValue = ''
    if (column.filterType === 'select' && column.filterMultiple) {
      clearedValue = []
    } else if (column.filterType === 'dateRange') {
      clearedValue = { from: null, to: null }
    }
    const nextFilters = {
      ...draftFilters,
      [key]: clearedValue,
    }
    onApply(nextFilters)
    onClose()
  }

  const handleApply = () => {
    onApply()
    onClose()
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
    >
      <Box px={2} pt={2} pb={1} minWidth={220}>
        {column.filterType === 'select' && column.filterOptions ? (
          <Box>
            {column.filterMultiple
              ? (() => {
                  const rawValue = draftFilters[column.key]
                  const selectedValues: Array<string | number> = Array.isArray(rawValue)
                    ? rawValue
                    : rawValue === undefined || rawValue === null || rawValue === ''
                      ? []
                      : [rawValue as string | number]
                  return column.filterOptions?.map(option => {
                    const checked = selectedValues.includes(option.value)
                    return (
                      <Box key={option.value} display="flex" alignItems="center" mb={0.5}>
                        <Checkbox
                          size="small"
                          checked={checked}
                          onChange={event => {
                            const nextSelected = event.target.checked
                              ? [...selectedValues, option.value]
                              : selectedValues.filter(v => v !== option.value)
                            onFilterChange(column.key, nextSelected)
                          }}
                          sx={{ p: 0.25, mr: 1 }}
                        />
                        <Box component="span">{option.label}</Box>
                      </Box>
                    )
                  })
                })()
              : column.filterOptions?.map(option => {
                  const rawValue = draftFilters[column.key] as string | number | undefined
                  const selectedValue = rawValue === undefined || rawValue === null ? '' : rawValue
                  const checked = selectedValue === option.value
                  return (
                    <Box key={option.value} display="flex" alignItems="center" mb={0.5}>
                      <Radio
                        size="small"
                        checked={checked}
                        onChange={() => {
                          onFilterChange(column.key, option.value)
                        }}
                        sx={{ p: 0.25, mr: 1 }}
                      />
                      <Box component="span">{option.label}</Box>
                    </Box>
                  )
                })}
          </Box>
        ) : column.filterType === 'dateRange' ? (
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box display="flex" flexDirection="column" gap={1}>
              {(() => {
                const raw = draftFilters[column.key] as DateRangeFilter | undefined
                const from = raw?.from ?? ''
                const to = raw?.to ?? ''
                const fromValue = from ? dayjs(from) : null
                const toValue = to ? dayjs(to) : null
                return (
                  <>
                    <DatePicker
                      value={fromValue}
                      onChange={value => {
                        const nextFrom = value ? value.startOf('day').format('YYYY-MM-DD') : null
                        onFilterChange(column.key, {
                          from: nextFrom,
                          to,
                        } as DateRangeFilter)
                      }}
                      slotProps={{
                        textField: {
                          size: 'small',
                          fullWidth: true,
                        },
                      }}
                    />
                    <DatePicker
                      value={toValue}
                      onChange={value => {
                        const nextTo = value ? value.endOf('day').format('YYYY-MM-DD') : null
                        onFilterChange(column.key, {
                          from,
                          to: nextTo,
                        } as DateRangeFilter)
                      }}
                      slotProps={{
                        textField: {
                          size: 'small',
                          fullWidth: true,
                        },
                      }}
                    />
                  </>
                )
              })()}
            </Box>
          </LocalizationProvider>
        ) : (
          <TextField
            fullWidth
            size="small"
            variant="standard"
            value={(draftFilters[column.key] as string | undefined) ?? ''}
            onChange={event => onFilterChange(column.key, event.target.value)}
            autoFocus
          />
        )}
        <Box display="flex" justifyContent="space-between" mt={2}>
          <Button size="small" onClick={handleReset}>
            Reset
          </Button>
          <Button size="small" variant="contained" onClick={handleApply}>
            Filter
          </Button>
        </Box>
      </Box>
    </Menu>
  )
}

export default ConfigTableFilterMenu
