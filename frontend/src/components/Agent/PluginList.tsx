import Typography from '@mui/material/Typography'
import { AgentPlugin } from '@test-agentstudio/api-client'
import { Trash2, Plug } from 'lucide-react'
import React, { useState } from 'react'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import { useScopedTranslation } from '@/i18n'

// 插件列表组件
const PluginList = ({
  pluginObjects,
  onClick,
  disabled = false,
}: {
  pluginObjects: AgentPlugin[]
  onClick: (operate: 'delete', pluginId: string, toolId: string) => void
  disabled?: boolean
}) => {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<{ pluginId: string; toolId: string; name: string } | null>(null)
  const { t } = useScopedTranslation('agents.agentEditor.orchestration.pluginSetting')
  return (
    <div className="space-y-3">
      {pluginObjects.map(plugin => (
        <div
          key={plugin.tool_id}
          className="flex items-center justify-between py-2 px-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm hover:shadow-sm transition-all duration-200"
        >
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 rounded-lg flex items-center justify-center border border-purple-200 dark:border-purple-800">
              <Plug className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <Typography sx={{ fontWeight: 'bold', fontSize: '1rem', color: '#1F2937' }} className="dark:text-gray-100">{plugin.plugin_name}</Typography>
              <Typography sx={{ color: 'text.secondary', fontSize: '0.875rem' }} className="text-gray-500 dark:text-gray-400">{plugin.tool_name}</Typography>
            </div>
          </div>
          <div className="flex space-x-4">
            <button
              title={t('delete.tooltip')}
              onClick={e => {
                e.stopPropagation()
                if (!disabled) {
                  setPendingDelete({ pluginId: plugin.plugin_id, toolId: plugin.tool_id, name: plugin.plugin_name || '' })
                  setConfirmOpen(true)
                }
              }}
              disabled={disabled}
              className={`${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Trash2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>
      ))}
      {pluginObjects.length === 0 && <div className="text-center py-6 text-gray-500 dark:text-gray-400">{t('list.empty')}</div>}
      <DeleteConfirmationDialog
        isOpen={confirmOpen}
        onClose={() => {
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        onConfirm={() => {
          if (pendingDelete) onClick('delete', pendingDelete.pluginId, pendingDelete.toolId)
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        itemType="plugin"
        itemName={pendingDelete?.name || ''}
        title={t('delete.title')}
        confirmButtonText={t('delete.confirmButtonText')}
        message={t('delete.message')}
      />
    </div>
  )
}

export default PluginList
