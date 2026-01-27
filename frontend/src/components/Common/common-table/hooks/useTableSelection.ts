import { useCallback, useEffect, useMemo, useState } from 'react'
import { getDefaultRowId } from '../utils'

export interface UseTableSelectionProps<T> {
  rows: T[]
  enableSelection?: boolean
  selectionKey?: keyof T & string
  getRowId?: (row: T) => string | number
  selectedRowIds?: Array<string | number>
  onSelectionChange?: (selectedRows: T[], selectedIds: Array<string | number>) => void
}

export interface UseTableSelectionReturn<T> {
  effectiveSelectedIds: Array<string | number>
  selectedRows: T[]
  isSelectionControlled: boolean
  handleToggleRow: (row: T, index: number) => void
  handleToggleAllCurrentPage: (currentRows: T[]) => void
  clearSelection: () => void
  getRowSelectionState: (row: T, index: number) => { id: string | number; isSelected: boolean }
}

/**
 * Hook to manage table selection state
 */
export function useTableSelection<T extends object>(
  processedRows: T[],
  props: UseTableSelectionProps<T>,
): UseTableSelectionReturn<T> {
  const { rows: allRows, enableSelection, selectionKey, getRowId, selectedRowIds, onSelectionChange } = props

  const [internalSelectedIds, setInternalSelectedIds] = useState<Array<string | number>>([])

  const isSelectionControlled = selectedRowIds !== undefined
  const effectiveSelectedIds = isSelectionControlled ? selectedRowIds! : internalSelectedIds

  // Sync internal state when controlled mode prop changes
  useEffect(() => {
    if (isSelectionControlled && selectedRowIds) {
      setInternalSelectedIds(selectedRowIds)
    }
  }, [isSelectionControlled, selectedRowIds])

  const computeSelectedRows = useCallback(
    (ids: Array<string | number>): T[] => {
      if (!ids || ids.length === 0) return []
      const idSet = new Set(ids)
      return allRows.filter((row, index) => {
        const id = getDefaultRowId(row, index, selectionKey, getRowId)
        return idSet.has(id)
      })
    },
    [allRows, selectionKey, getRowId],
  )

  const handleSelectionChangeInternal = useCallback(
    (nextIds: Array<string | number>) => {
      const nextRows = computeSelectedRows(nextIds)
      if (!isSelectionControlled) {
        setInternalSelectedIds(nextIds)
      }
      if (onSelectionChange) {
        onSelectionChange(nextRows, nextIds)
      }
    },
    [computeSelectedRows, isSelectionControlled, onSelectionChange],
  )

  const handleToggleRow = useCallback(
    (row: T, index: number) => {
      const id = getDefaultRowId(row, index, selectionKey, getRowId)
      const exists = effectiveSelectedIds.includes(id)
      const nextIds = exists ? effectiveSelectedIds.filter(x => x !== id) : [...effectiveSelectedIds, id]
      handleSelectionChangeInternal(nextIds)
    },
    [effectiveSelectedIds, selectionKey, getRowId, handleSelectionChangeInternal],
  )

  const handleToggleAllCurrentPage = useCallback(
    (currentRows: T[]) => {
      const currentIds = currentRows.map((row, index) => getDefaultRowId(row, index, selectionKey, getRowId))
      const setCurrent = new Set(currentIds)
      const allSelectedOnPage = currentIds.length > 0 && currentIds.every(id => effectiveSelectedIds.includes(id))
      let nextIds: Array<string | number>
      if (allSelectedOnPage) {
        nextIds = effectiveSelectedIds.filter(id => !setCurrent.has(id))
      } else {
        const merged = new Set(effectiveSelectedIds)
        currentIds.forEach(id => merged.add(id))
        nextIds = Array.from(merged)
      }
      handleSelectionChangeInternal(nextIds)
    },
    [effectiveSelectedIds, selectionKey, getRowId, handleSelectionChangeInternal],
  )

  const clearSelection = useCallback(() => {
    if (!isSelectionControlled) {
      setInternalSelectedIds([])
    }
    if (onSelectionChange) {
      onSelectionChange([], [])
    }
  }, [isSelectionControlled, onSelectionChange])

  const selectedRows = useMemo(() => computeSelectedRows(effectiveSelectedIds), [computeSelectedRows, effectiveSelectedIds])

  const getRowSelectionState = useCallback(
    (row: T, index: number) => {
      const id = getDefaultRowId(row, index, selectionKey, getRowId)
      return {
        id,
        isSelected: effectiveSelectedIds.includes(id),
      }
    },
    [effectiveSelectedIds, selectionKey, getRowId],
  )

  return {
    effectiveSelectedIds,
    selectedRows,
    isSelectionControlled,
    handleToggleRow,
    handleToggleAllCurrentPage,
    clearSelection,
    getRowSelectionState,
  }
}
