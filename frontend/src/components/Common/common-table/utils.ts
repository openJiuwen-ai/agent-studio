import React from 'react'
import { TableColumn, FilterValue, DateRangeFilter, ColumnFilterState, SortState, SortOrder } from './types'

/**
 * Get the default row ID for selection purposes
 */
export function getDefaultRowId<T extends object>(
  row: T,
  index: number,
  selectionKey?: keyof T & string,
  getRowId?: (row: T) => string | number,
): string | number {
  // Custom getter takes priority
  if (getRowId) return getRowId(row)

  // Use selectionKey if provided and the property exists
  if (selectionKey && row) {
    const value = (row as Record<string, unknown>)[selectionKey as string]
    if (value !== undefined && value !== null) {
      // Ensure the value is a valid ID type (string or number)
      return typeof value === 'string' || typeof value === 'number' ? value : index
    }
  }

  // Fallback to index
  return index
}

/**
 * Apply local filter and sort to rows
 */
export function applyLocalFilterAndSort<T>(
  rows: T[],
  columns: TableColumn<T>[],
  filters: ColumnFilterState,
  sort: SortState,
): T[] {
  let result = rows

  const hasFilters = Object.values(filters).some(value => {
    if (Array.isArray(value)) return value.length > 0
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const v = value as DateRangeFilter
      return !!(v.from || v.to)
    }
    return value !== undefined && value !== null && value !== ''
  })

  if (hasFilters) {
    result = result.filter(row => {
      return columns.every(column => {
        if (!column.filterable) return true
        const dataKey = (column.dataIndex ?? (column.key as keyof T & string)) as keyof T
        const cell = (row as any)[dataKey]
        const rawFilterValue = filters[column.key]

        if (column.filterType === 'dateRange' && rawFilterValue && typeof rawFilterValue === 'object' && !Array.isArray(rawFilterValue)) {
          const { from, to } = rawFilterValue as DateRangeFilter
          if (!from && !to) return true
          const cellTime = cell === undefined || cell === null ? NaN : new Date(cell).getTime()
          if (Number.isNaN(cellTime)) return false
          if (from && cellTime < new Date(from).getTime()) return false
          if (to && cellTime > new Date(to).getTime()) return false
          return true
        }

        const filterValue = rawFilterValue as Exclude<FilterValue, DateRangeFilter>
        if (filterValue === undefined || filterValue === null || filterValue === '') return true
        if (Array.isArray(filterValue)) {
          return filterValue.includes(cell as any)
        }
        if (typeof filterValue === 'string') {
          const cellText = cell === undefined || cell === null ? '' : String(cell)
          return cellText.toLowerCase().includes(filterValue.toLowerCase())
        }
        return cell === filterValue
      })
    })
  }

  if (sort.field && sort.order) {
    const column = columns.find(c => c.key === sort.field)
    if (column) {
      const dataKey = (column.dataIndex ?? (column.key as keyof T & string)) as keyof T
      const orderFactor = sort.order === 'asc' ? 1 : -1
      result = [...result].sort((a, b) => {
        const av = (a as any)[dataKey]
        const bv = (b as any)[dataKey]
        if (av === bv) return 0
        if (av === undefined || av === null) return -1 * orderFactor
        if (bv === undefined || bv === null) return 1 * orderFactor
        if (typeof av === 'number' && typeof bv === 'number') {
          return av < bv ? -1 * orderFactor : 1 * orderFactor
        }
        const as = String(av)
        const bs = String(bv)
        if (as === bs) return 0
        return as < bs ? -1 * orderFactor : 1 * orderFactor
      })
    }
  }

  return result
}

/**
 * Check if a filter value is active
 */
export function hasActiveFilter(value: FilterValue): boolean {
  if (value === undefined || value === null || value === '') return false
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const v = value as DateRangeFilter
    return !!(v.from || v.to)
  }
  if (Array.isArray(value)) return value.length > 0
  return true
}

/**
 * Extract slot map from children (for TableItem pattern)
 */
export function extractSlotMap(children: React.ReactNode): Record<string, React.ReactElement> {
  const map: Record<string, React.ReactElement> = {}

  React.Children.forEach(children, child => {
    if (!React.isValidElement(child)) return
    const type: any = child.type
    if (type && type.displayName === 'ConfigTableItem') {
      const props = child.props as { columnKey: string; children: React.ReactElement }
      const key = props.columnKey
      if (!key) return
      const slotChildren = React.Children.toArray(props.children)
      if (slotChildren.length === 0) return
      const firstChild = slotChildren[0]
      if (React.isValidElement(firstChild)) {
        map[key] = firstChild as React.ReactElement
      }
    }
  })

  return map
}
