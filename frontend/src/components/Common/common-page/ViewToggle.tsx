import React from 'react'
import { Grid, List } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ViewType } from './CommonPageLayout'

export interface ViewToggleProps {
  viewType: ViewType
  onChange: (type: ViewType) => void
  disabled?: boolean
}

export const ViewToggle: React.FC<ViewToggleProps> = ({ viewType, onChange, disabled = false }) => {
  const { t } = useTranslation()
  return (
    <div className="flex h-8 rounded-[4px] p-0.5 bg-[#ECECF0] dark:bg-gray-700">
      <button
        onClick={() => onChange('grid')}
        disabled={disabled}
        className={`h-7 px-2 rounded-[3px] transition-colors ${
          viewType === 'grid' ? 'text-[#295BFB] dark:text-blue-400' : 'text-[#777777] dark:text-gray-400 hover:bg-white/60 dark:hover:bg-gray-600/60'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        style={{ backgroundColor: viewType === 'grid' ? '#FFFFFF' : 'transparent' }}
        title={t('common.view.gridView')}
        type="button"
      >
        <Grid className="w-4 h-4" />
      </button>
      <button
        onClick={() => onChange('table')}
        disabled={disabled}
        className={`h-7 px-2 rounded-[3px] transition-colors ${
          viewType === 'table' ? 'text-[#0A59F7] dark:text-blue-400' : 'text-[#777777] dark:text-gray-400 hover:bg-white/60 dark:hover:bg-gray-600/60'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        style={{ backgroundColor: viewType === 'table' ? '#FFFFFF' : 'transparent' }}
        title={t('common.view.tableView')}
        type="button"
      >
        <List className="w-4 h-4" />
      </button>
    </div>
  )
}

export default ViewToggle
