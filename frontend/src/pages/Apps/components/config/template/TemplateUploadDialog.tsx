/**
 * Template Upload Dialog Component
 * 模板上传对话框组件
 * 用于上传新的报告模板
 */

import React, { useState, useRef } from 'react'
import { X, Upload, FileText, Loader2, AlertCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { RADIUS_CONTAINER, RADIUS_BUTTON } from '../../../constants/styles'

/** 导入模式类型 */
export type ImportMode = 'extract' | 'direct'

export interface TemplateUploadDialogProps {
  /** 是否显示对话框 */
  open: boolean
  /** 关闭对话框 */
  onClose: () => void
  /** 上传确认回调 */
  onConfirm: (file: File, templateName: string, templateDesc: string, isTemplate: boolean) => Promise<void>
  /** 是否正在上传 */
  uploading?: boolean
}

/**
 * 模板上传对话框组件
 */
export const TemplateUploadDialog: React.FC<TemplateUploadDialogProps> = ({
  open,
  onClose,
  onConfirm,
  uploading = false
}) => {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [templateName, setTemplateName] = useState('')
  const [templateDesc, setTemplateDesc] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const [importMode, setImportMode] = useState<ImportMode>('extract')
  const [localError, setLocalError] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const NAME_PATTERN = /^[一-龥a-zA-Z0-9_\-.]+$/
  const NAME_MAX_LENGTH = 199

  const sanitizeTemplateName = (name: string): string => {
    const cleaned = name.replace(/[^一-龥a-zA-Z0-9_\-.]/g, '')
    return cleaned.slice(0, NAME_MAX_LENGTH)
  }

  const validateTemplateName = (name: string): string | null => {
    const trimmed = name.trim()
    if (!trimmed) return null
    if (trimmed.length > NAME_MAX_LENGTH) return t('apps.config.template.nameInvalidChars')
    if (!NAME_PATTERN.test(trimmed)) return t('apps.config.template.nameInvalidChars')
    return null
  }

  const getAllowedExtensions = (mode: ImportMode): string[] => {
    return mode === 'extract' ? ['.md', '.html', '.doc', '.docx', '.pdf'] : ['.md']
  }

  const validateFileType = (selectedFile: File, mode: ImportMode): boolean => {
    const allowedExtensions = getAllowedExtensions(mode)
    const fileName = selectedFile.name.toLowerCase()
    return allowedExtensions.some(ext => fileName.endsWith(ext))
  }

  const resetForm = () => {
    setFile(null)
    setTemplateName('')
    setTemplateDesc('')
    setDragActive(false)
    setImportMode('extract')
    setLocalError(null)
    setNameError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // 关闭对话框
  const handleClose = () => {
    if (!uploading) {
      resetForm()
      onClose()
    }
  }

  // 处理文件选择
  const handleFileSelect = (selectedFile: File | null) => {
    if (!selectedFile) return

    if (!validateFileType(selectedFile, importMode)) {
      const allowedExtensions = getAllowedExtensions(importMode)
      setLocalError(t('apps.config.template.invalidFileType', { formats: allowedExtensions.join(', ') }))
      return
    }

    setLocalError(null)
    setFile(selectedFile)
    const nameWithoutExt = selectedFile.name.replace(/\.[^/.]+$/, '')
    setTemplateName(sanitizeTemplateName(nameWithoutExt))
    setNameError(null)
  }

  // 拖拽相关处理
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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  // 处理文件输入变化
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
    }
  }

  // 确认上传
  const handleConfirm = async () => {
    const nameErr = validateTemplateName(templateName)
    if (!file || !templateName.trim() || nameErr) {
      if (nameErr) setNameError(nameErr)
      return
    }

    // 清除之前的错误
    setLocalError(null)

    try {
      await onConfirm(file, templateName.trim(), templateDesc.trim(), importMode === 'direct')
      resetForm()
      onClose()
    } catch (error) {
      console.error('上传模板失败:', error)
      // 提取错误消息
      const errorMessage = error instanceof Error ? error.message : t('apps.config.template.uploadFailedRetry')
      setLocalError(errorMessage)
    }
  }

  // 是否可以上传
  const canUpload = file && templateName.trim() && !uploading && !validateTemplateName(templateName)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className={`bg-white ${RADIUS_CONTAINER} shadow-2xl w-full max-w-md mx-4 overflow-hidden`}>
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{t('apps.config.template.importTemplate')}</h2>
          <button
            onClick={handleClose}
            disabled={uploading}
            className={`p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 ${RADIUS_BUTTON} transition-colors disabled:opacity-50`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4 space-y-4">
          {/* 模板生成方式 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('apps.config.template.generationMethod')}
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  if (file && !validateFileType(file, 'extract')) {
                    setFile(null)
                    setTemplateName('')
                    setLocalError(t('apps.config.template.fileTypeChanged'))
                  } else {
                    setLocalError(null)
                  }
                  setImportMode('extract')
                }}
                disabled={uploading}
                className={`
                  flex-1 px-4 py-3 rounded-lg text-sm font-medium transition-all
                  ${importMode === 'extract'
                    ? 'bg-blue-50 text-blue-700 border-2 border-blue-500'
                    : 'bg-gray-50 text-gray-600 border-2 border-gray-200 hover:bg-gray-100'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <span className="flex items-center justify-center gap-2">
                  {t('apps.config.template.extractMode')}
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  if (file && !validateFileType(file, 'direct')) {
                    setFile(null)
                    setTemplateName('')
                    setLocalError(t('apps.config.template.fileTypeChanged'))
                  } else {
                    setLocalError(null)
                  }
                  setImportMode('direct')
                }}
                disabled={uploading}
                className={`
                  flex-1 px-4 py-3 rounded-lg text-sm font-medium transition-all
                  ${importMode === 'direct'
                    ? 'bg-blue-50 text-blue-700 border-2 border-blue-500'
                    : 'bg-gray-50 text-gray-600 border-2 border-gray-200 hover:bg-gray-100'
                  }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
              >
                <span className="flex items-center justify-center gap-2">
                  {t('apps.config.template.directMode')}
                </span>
              </button>
            </div>
          </div>

          {/* 文件拖放区域 */}
          <div
            className={`
              relative border-2 border-dashed rounded-xl p-6 text-center transition-colors
              ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
              ${file ? 'border-green-500 bg-green-50' : ''}
            `}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              onChange={handleFileInputChange}
              accept={importMode === 'extract' ? '.md,.html,.doc,.docx,.pdf' : '.md'}
              disabled={uploading}
            />

            {file ? (
              <div className="flex items-center justify-center gap-2 text-green-700">
                <FileText className="w-5 h-5" />
                <span className="text-sm font-medium">{file.name}</span>
              </div>
            ) : (
              <>
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  {t('apps.config.template.dragDropOrClick')}{' '}
                  <span className="text-blue-600 font-medium">{t('apps.config.template.clickToSelect')}</span>
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {importMode === 'extract'
                    ? t('apps.config.template.supportFormats')
                    : t('apps.config.template.supportMarkdownOnly')
                  }
                </p>
              </>
            )}
          </div>

          {/* 文件类型错误提示 */}
          {localError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 flex-1">{localError}</p>
            </div>
          )}

          {/* 模板名称 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('apps.config.template.templateName')} <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => {
                setTemplateName(e.target.value)
                setNameError(validateTemplateName(e.target.value))
              }}
              placeholder={t('apps.config.template.namePlaceholder')}
              disabled={uploading}
              className={`
                w-full px-3 py-2 ${RADIUS_BUTTON} border
                ${nameError ? 'border-red-400 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'}
                text-sm text-gray-900 placeholder-gray-400
                focus:outline-none focus:ring-2 focus:border-transparent
                disabled:bg-gray-100 disabled:cursor-not-allowed
              `}
            />
            {nameError && (
              <p className="mt-1 text-xs text-red-600">{nameError}</p>
            )}
          </div>

          {/* 模板描述 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('apps.config.template.templateDesc')}
            </label>
            <textarea
              value={templateDesc}
              onChange={(e) => setTemplateDesc(e.target.value)}
              placeholder={t('apps.config.template.descPlaceholder')}
              rows={3}
              disabled={uploading}
              className={`
                w-full px-3 py-2 ${RADIUS_BUTTON} border border-gray-300
                text-sm text-gray-900 placeholder-gray-400
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                resize-none disabled:bg-gray-100 disabled:cursor-not-allowed
              `}
            />
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={handleClose}
            disabled={uploading}
            className={`
              px-4 py-2 text-sm font-medium text-gray-700
              hover:text-gray-900 hover:bg-gray-200
              ${RADIUS_BUTTON} transition-all duration-200 disabled:opacity-50
            `}
          >
            {t('apps.config.template.cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canUpload}
            className={`
              px-6 py-2 text-sm font-medium ${RADIUS_BUTTON}
              transition-all duration-200 flex items-center gap-2
              ${canUpload
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t('apps.config.template.uploading')}
              </>
            ) : (
              t('apps.config.template.confirmUpload')
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TemplateUploadDialog
