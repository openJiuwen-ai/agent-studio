import React from 'react'
import { useTranslation } from 'react-i18next'

/**
 * SummaryPanel — placeholder for the Deep Search Summary tab.
 * Design pending; renders an empty state message.
 */
const SummaryPanel: React.FC = () => {
  const { t } = useTranslation()

  return (
    <div className="h-full flex items-center justify-center text-gray-400">
      <div className="text-center space-y-2">
        <p className="text-lg font-medium">{t('apps.deepSearchExplorer.summaryPlaceholder', 'Summary')}</p>
        <p className="text-sm">{t('apps.deepSearchExplorer.summaryComingSoon', 'Summary view is coming soon.')}</p>
      </div>
    </div>
  )
}

export default SummaryPanel
