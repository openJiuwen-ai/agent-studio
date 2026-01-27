import React from 'react'
import { useTranslation } from 'react-i18next'
import { X, AlertTriangle } from 'lucide-react'

interface ImportConflictDialogProps {
  isOpen: boolean
  agentName: string
  onOverwrite: () => void
  onCreateCopy: () => void
  onCancel: () => void
}

export const ImportConflictDialog: React.FC<ImportConflictDialogProps> = ({
  isOpen,
  agentName,
  onOverwrite,
  onCreateCopy,
  onCancel,
}) => {
  const { t } = useTranslation()

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
        <button onClick={onCancel} className="absolute top-6 right-6 text-[#9ca3af] hover:text-[#374151]">
          <X className="w-6 h-6" />
        </button>
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-orange-600" />
          </div>
        </div>
        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">{t('agents.importConflictDialog.title')}</h3>
          <p className="text-gray-600 text-lg leading-relaxed break-words">
            {t('agents.importConflictDialog.message', { name: agentName })}
            <br />
            {t('agents.importConflictDialog.question')}
          </p>
        </div>
        <div className="flex flex-col gap-3">
          <button
            onClick={onOverwrite}
            className="w-full px-6 py-3 bg-orange-600 text-white rounded-xl hover:bg-orange-700 font-medium transition-all"
          >
            {t('agents.importConflictDialog.overwriteButton')}
          </button>
          <button
            onClick={onCreateCopy}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 font-medium transition-all"
          >
            {t('agents.importConflictDialog.createCopyButton')}
          </button>
          <button
            onClick={onCancel}
            className="w-full px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all"
          >
            {t('agents.importConflictDialog.cancelButton')}
          </button>
        </div>
      </div>
    </div>
  )
}
