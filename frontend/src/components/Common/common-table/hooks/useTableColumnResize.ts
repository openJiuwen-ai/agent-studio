import { useCallback, useState, useMemo } from 'react'
import { TableColumn } from '../types'

export interface UseTableColumnResizeProps {
  columns: TableColumn<any>[]
  columnResizePersistenceKey?: string
  onColumnWidthChange?: (columnKey: string, width: number) => void
}

export interface UseTableColumnResizeReturn {
  columnWidths: Record<string, number>
  handleColumnResizeMouseDown: (event: React.MouseEvent<HTMLDivElement>, columnKey: string) => void
  totalColumnsMinWidth: number
  getColumnWidth: (columnKey: string) => number | undefined
}

/**
 * Hook to manage table column resize functionality
 */
export function useTableColumnResize(props: UseTableColumnResizeProps): UseTableColumnResizeReturn {
  const { columns, columnResizePersistenceKey, onColumnWidthChange } = props

  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    if (!columnResizePersistenceKey) return {}
    if (typeof window === 'undefined') return {}
    try {
      const raw = window.localStorage.getItem(columnResizePersistenceKey)
      if (!raw) return {}
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object') {
        return parsed as Record<string, number>
      }
      return {}
    } catch {
      return {}
    }
  })

  const totalColumnsMinWidth = useMemo(() => {
    if (!columns || columns.length === 0) return 0
    return columns.reduce((sum, column) => {
      const storedWidth = columnWidths[column.key]
      const width = storedWidth ?? column.width ?? column.minWidth
      if (typeof width === 'number') return sum + width
      return sum + (column.minWidth ?? 80)
    }, 0)
  }, [columns, columnWidths])

  const handleColumnResizeMouseDown = useCallback(
    (event: React.MouseEvent<HTMLDivElement>, columnKey: string) => {
      event.preventDefault()
      event.stopPropagation()

      const cell = event.currentTarget.parentElement as HTMLTableCellElement | null
      if (!cell) return

      const startX = event.clientX
      // 优先使用存储宽度或列定义宽度，避免因 getBoundingClientRect 四舍五入导致的跳动
      const column = columns.find(c => c.key === columnKey)
      const storedOrDefinedWidth = columnWidths[columnKey] ?? column?.width
      const startWidth = typeof storedOrDefinedWidth === 'number'
        ? storedOrDefinedWidth
        : cell.getBoundingClientRect().width
      let latestWidth = startWidth

      const minWidth = typeof column?.minWidth === 'number' ? column.minWidth : 60
      const maxWidth = typeof column?.maxWidth === 'number' ? column.maxWidth : undefined

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const delta = moveEvent.clientX - startX
        let nextWidth = startWidth + delta
        nextWidth = Math.max(minWidth, nextWidth)
        if (typeof maxWidth === 'number') {
          nextWidth = Math.min(maxWidth, nextWidth)
        }
        latestWidth = nextWidth
        setColumnWidths(prev => {
          const next = { ...prev, [columnKey]: nextWidth }
          if (columnResizePersistenceKey && typeof window !== 'undefined') {
            try {
              window.localStorage.setItem(columnResizePersistenceKey, JSON.stringify(next))
            } catch {}
          }
          return next
        })
      }

      const handleMouseUp = () => {
        if (onColumnWidthChange) {
          onColumnWidthChange(columnKey, latestWidth)
        }
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseup', handleMouseUp)
      }

      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    },
    [columns, columnWidths, columnResizePersistenceKey, onColumnWidthChange],
  )

  const getColumnWidth = useCallback(
    (columnKey: string): number | undefined => {
      return columnWidths[columnKey]
    },
    [columnWidths],
  )

  return {
    columnWidths,
    handleColumnResizeMouseDown,
    totalColumnsMinWidth,
    getColumnWidth,
  }
}
