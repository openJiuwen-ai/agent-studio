import React from 'react'
import { X, Trash2, Loader2, AlertTriangle } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export interface DeleteConfirmationDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  itemType?: 'agent' | 'workflow' | 'model' | 'plugin' | 'knowledgeBase'
  itemName?: string
  isLoading?: boolean
  title?: string
  message?: string | React.ReactNode
  confirmButtonText?: string
  cancelButtonText?: string
  iconType?: 'danger' | 'warning'
}

const DeleteConfirmationDialog: React.FC<DeleteConfirmationDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  itemType,
  itemName,
  isLoading = false,
  title,
  message,
  confirmButtonText,
  cancelButtonText,
  iconType = 'danger',
}) => {
  const { t } = useTranslation()

  // Default titles and messages based on item type
  const getDefaultTitle = () => {
    switch (itemType) {
      case 'agent':
        return t('common.confirmDialog.titles.agent')
      case 'workflow':
        return t('common.confirmDialog.titles.workflow')
      case 'model':
        return t('common.confirmDialog.titles.model')
      case 'plugin':
        return t('common.confirmDialog.titles.plugin')
      case 'knowledgeBase':
        return t('common.confirmDialog.titles.knowledgeBase')
      default:
        return t('common.confirmDialog.titles.default')
    }
  }

  const getDefaultMessage = () => {
    switch (itemType) {
      case 'agent':
        return t('common.confirmDialog.messages.agent', { name: itemName })
      case 'workflow':
        return t('common.confirmDialog.messages.workflow', { name: itemName })
      case 'model':
        return t('common.confirmDialog.messages.model', { name: itemName })
      case 'plugin':
        return t('common.confirmDialog.messages.plugin', { name: itemName })
      case 'knowledgeBase':
        return t('common.confirmDialog.messages.knowledgeBase', { name: itemName })
      default:
        return t('common.confirmDialog.messages.default', { name: itemName })
    }
  }

  const getDefaultConfirmButtonText = () => {
    switch (itemType) {
      case 'agent':
        return t('common.confirmDialog.buttons.deleteAgent')
      case 'workflow':
        return t('common.confirmDialog.buttons.deleteWorkflow')
      case 'model':
        return t('common.confirmDialog.buttons.deleteModel')
      case 'plugin':
        return t('common.confirmDialog.buttons.deletePlugin')
      case 'knowledgeBase':
        return t('common.confirmDialog.buttons.deleteKnowledgeBase')
      default:
        return t('common.confirmDialog.buttons.delete')
    }
  }

  const displayTitle = title || getDefaultTitle()
  const displayMessage = message || getDefaultMessage()
  const displayConfirmButtonText = confirmButtonText || getDefaultConfirmButtonText()
  const displayCancelButtonText = cancelButtonText || t('common.confirmDialog.buttons.cancel')

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
        {/* Close button */}
        <button onClick={onClose} className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 transition-colors" disabled={isLoading}>
          <X className="w-6 h-6" />
        </button>

        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className={`w-16 h-16 ${iconType === 'warning' ? 'bg-orange-100' : 'bg-red-100'} rounded-full flex items-center justify-center`}>
            {iconType === 'warning' ? <AlertTriangle className="w-8 h-8 text-orange-600" /> : <Trash2 className="w-8 h-8 text-red-600" />}
          </div>
        </div>

        {/* Content */}
        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">{displayTitle}</h3>
          {typeof displayMessage === 'string' ? (
            <p className="text-gray-600 text-lg leading-relaxed break-all max-w-full">{displayMessage}</p>
          ) : (
            <div className="text-gray-600 text-lg leading-relaxed break-words max-w-full">{displayMessage}</div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="flex-1 px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {displayCancelButtonText}
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {t('common.confirmDialog.buttons.deleting')}
              </>
            ) : (
              displayConfirmButtonText
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteConfirmationDialog
