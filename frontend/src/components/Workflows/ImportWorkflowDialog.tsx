import React, { useState } from 'react'
import { X, Upload, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { getToken } from '@test-agentstudio/api-client'

export interface ImportWorkflowDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  spaceId: string
}

const ImportWorkflowDialog: React.FC<ImportWorkflowDialogProps> = ({ isOpen, onClose, onSuccess, spaceId }) => {
  const { t } = useTranslation()

  const [file, setFile] = useState<File | null>(null)
  const [validateStrict, setValidateStrict] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      // Validate file type
      if (!selectedFile.name.endsWith('.json')) {
        setError(t('workflows.import.errors.invalidFileType'))
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) {
      if (!droppedFile.name.endsWith('.json')) {
        setError(t('workflows.import.errors.invalidFileType'))
        return
      }
      setFile(droppedFile)
      setError(null)
    }
  }

  const handleImport = async () => {
    if (!file) {
      setError(t('workflows.import.errors.noFile'))
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('space_id', spaceId)
      formData.append('validate_strict', String(validateStrict))

      const token = getToken()
      const response = await fetch('/api/v1/workflows/import', {
        method: 'POST',
        body: formData,
        headers: {
          // Don't set Content-Type - browser will set it with boundary for multipart
          Authorization: `Bearer ${token || ''}`,
        },
      })

      const result = await response.json()

      if (result.code === 200) {
        // Show success state
        setIsSuccess(true)

        // Wait 1.5 seconds to show success message, then close
        setTimeout(() => {
          onSuccess()
          onClose()
          // Reset form
          setFile(null)
          setValidateStrict(false)
          setIsSuccess(false)
        }, 1500)
      } else {
        setError(result.message || t('workflows.import.errors.importFailed'))
      }
    } catch (err: any) {
      setError(err.message || t('workflows.import.errors.importFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    if (!isLoading && !isSuccess) {
      setFile(null)
      setError(null)
      setValidateStrict(false)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={handleClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-2xl w-full mx-4 transform transition-all max-h-[90vh] overflow-y-auto">
        {/* Close button */}
        <button onClick={handleClose} className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 transition-colors" disabled={isLoading}>
          <X className="w-6 h-6" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-100 to-pink-100 rounded-full flex items-center justify-center">
            <Upload className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900">{t('workflows.import.title')}</h3>
            <p className="text-gray-500 text-sm">{t('workflows.import.subtitle')}</p>
          </div>
        </div>

        {/* File Upload Area */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {t('workflows.import.file')} <span className="text-red-500">*</span>
          </label>
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive ? 'border-purple-500 bg-purple-50' : file ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-purple-400'
            }`}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <CheckCircle className="w-8 h-8 text-green-600" />
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
                <button onClick={() => setFile(null)} className="ml-auto p-2 text-gray-400 hover:text-red-600 transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">{t('workflows.import.dragDrop')}</p>
                <label className="inline-block px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 cursor-pointer transition-colors">
                  {t('workflows.import.selectFile')}
                  <input type="file" accept=".json" onChange={handleFileChange} className="hidden" disabled={isLoading} />
                </label>
                <p className="text-xs text-gray-500 mt-2">{t('workflows.import.fileFormat')}</p>
              </>
            )}
          </div>
        </div>

        {/* Validate Strict Toggle - HIDDEN */}
        <div className="mb-6 hidden">
          <label className="flex items-center justify-between p-4 border-2 border-gray-200 rounded-xl hover:border-purple-300 transition-colors cursor-pointer">
            <div>
              <div className="font-medium text-gray-900">{t('workflows.import.validateStrict')}</div>
              <div className="text-sm text-gray-500 mt-1">{t('workflows.import.validateStrictDesc')}</div>
            </div>
            <input
              type="checkbox"
              checked={validateStrict}
              onChange={e => setValidateStrict(e.target.checked)}
              disabled={isLoading}
              className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
            />
          </label>
        </div>

        {/* Success Message */}
        {isSuccess && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-green-700">{t('workflows.import.success')}</div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-700">{error}</div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={handleClose}
            disabled={isLoading || isSuccess}
            className="flex-1 px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleImport}
            disabled={isLoading || !file || isSuccess}
            className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
              isSuccess
                ? 'bg-green-600 text-white'
                : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700'
            }`}
          >
            {isSuccess ? (
              <>
                <CheckCircle className="w-5 h-5" />
                {t('workflows.import.success')}
              </>
            ) : isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {t('workflows.import.importing')}
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                {t('workflows.import.importButton')}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ImportWorkflowDialog
