import React from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export interface PagerState {
  total: number
  currentPage: number
  pageSize: number
  pageSizeOptions?: number[]
}

export type PagerChangeHandler = (page: number, pageSize: number) => void

interface PaginationProps {
  pager: PagerState
  loading?: boolean
  error?: string | null
  onPagerChange: PagerChangeHandler
}

const Pagination: React.FC<PaginationProps> = ({
  pager,
  loading = false,
  error = null,
  onPagerChange,
}) => {
  const { t } = useTranslation()

  const { currentPage, total, pageSize, pageSizeOptions } = pager
  const totalPages = Math.ceil(total / pageSize)

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const page = parseInt(e.target.value)
    if (page >= 1 && page <= totalPages) {
      onPagerChange(page, pageSize)
    }
  }

  const handlePageInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.currentTarget.blur()
    }
  }

  if (loading || error) {
    return null
  }

  return (
    <div className="flex items-center justify-end space-x-6">
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-700">{t('common.pagination.pageSize')}</span>
        <select
          value={pageSize}
          onChange={e => onPagerChange(1, Number(e.target.value))}
          className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {(pageSizeOptions && pageSizeOptions.length > 0 ? pageSizeOptions : [10, 20, 30, 40, 50]).map(opt => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <span className="text-sm text-gray-700">{t('common.pagination.items')}</span>
      </div>

      {total > 0 && (
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-700">{t('common.pagination.total', { total })}</span>
          <div className="flex items-center space-x-1">
            <button
              onClick={() => onPagerChange(1, pageSize)}
              disabled={currentPage === 1}
              className="p-2 text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('common.pagination.first')}
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>

            <button
              onClick={() => onPagerChange(currentPage - 1, pageSize)}
              disabled={currentPage === 1}
              className="p-2 text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('common.pagination.previous')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-700">
              <span>{t('common.pagination.pagePrefix')}</span>
              <input
                type="number"
                value={currentPage}
                onChange={handlePageInputChange}
                onKeyPress={handlePageInputKeyPress}
                min={1}
                max={totalPages}
                className="w-12 px-2 py-1 text-center text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span>{t('common.pagination.pageSuffix', { total: totalPages })}</span>
            </div>

            <button
              onClick={() => onPagerChange(currentPage + 1, pageSize)}
              disabled={currentPage >= totalPages}
              className="p-2 text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('common.pagination.next')}
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => onPagerChange(totalPages, pageSize)}
              disabled={currentPage >= totalPages}
              className="p-2 text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('common.pagination.last')}
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Pagination
