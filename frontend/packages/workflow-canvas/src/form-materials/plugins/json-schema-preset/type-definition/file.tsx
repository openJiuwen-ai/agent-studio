/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable react/prop-types */
import React, { useState, useEffect } from 'react'

import { Upload, Button, Input, Radio, RadioGroup, Toast } from '@douyinfe/semi-ui'
import { IconUpload, IconFile, IconImage, IconVideo, IconMusic, IconBook, IconCode, IconArchive } from '@douyinfe/semi-icons'

import { ConditionPresetOp } from '../../..'
import { useTranslation } from '../../../../i18n'

import { type JsonSchemaTypeRegistry } from '../types'

export const ENABLE_FILE_TYPE = false

const loadFileUploadService = async () => {
  try {
    const module = await import('../../../../components/testrun/runtime')
    return module.fileUploadService
  } catch (error) {
    console.warn('File upload service not available:', error)
    return null
  }
}

export type FileValue = { url: string; object_key: string; metadata?: FileMetadata }

export interface FileMetadata {
  name?: string
  size?: number
  mimeType?: string
}

interface FileInputProps {
  value?: FileValue
  onChange?: (value: FileValue | undefined) => void
  readonly?: boolean
  context?: 'testrun' | 'form'
  fileType?: string
  [key: string]: any
}

const FILE_ACCEPT_PATTERNS: Record<string, string> = {
  default: '*',
  image: 'image/*',
  svg: '.svg,image/svg+xml',
  audio: 'audio/*',
  video: 'video/*',
  voice: '.mp3,.wav,.ogg,.m4a,.aac',
  doc: '.doc,.docx',
  ppt: '.ppt,.pptx',
  excel: '.xls,.xlsx',
  txt: '.txt',
  code: '.js,.ts,.jsx,.tsx,.py,.java,.cpp,.c,.cs,.go,.rs,.php,.rb,.swift,.kt,.json,.xml,.yaml,.yml,.html,.css,.scss,.less,.sh,.bash,.zsh,.fish,.sql,.md,.markdown',
  zip: '.zip,.rar,.7z,.tar,.gz,.bz2,.xz',
}

export function FileInput(props: FileInputProps) {
  const { value, onChange, readonly, context = 'form', fileType = 'default' } = props
  const { t } = useTranslation()

  const isTestrun = context === 'testrun'
  const isForm = context === 'form'
  const acceptPattern = FILE_ACCEPT_PATTERNS[fileType] || FILE_ACCEPT_PATTERNS.default

  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  const getFileUrl = (): string | undefined => {
    return value?.url
  }

  const getFileMetadata = (): FileMetadata | undefined => {
    return value?.metadata
  }

  const handleFileUpload = async (file: File, semiOnProgress?: (event: { total: number; loaded: number }) => void): Promise<void> => {
    if (!file) return

    setIsUploading(true)
    setUploadProgress(0)

    try {
      const fileUploadService = await loadFileUploadService()

      if (fileUploadService) {
        const result = await fileUploadService.uploadFileAndGetUrl({
          file,
          onProgress: percent => {
            setUploadProgress(percent)
            semiOnProgress?.({ total: 100, loaded: percent })
          },
        })

        Toast.success({
          content: t('workflowCanvas.formMaterials.input.uploadSuccess') || 'File uploaded successfully',
          duration: 2,
        })

        onChange?.({
          url: result.url,
          object_key: result.object_key,
          metadata: result.metadata,
        })
      } else {
        throw new Error('File upload service not available')
      }
    } catch (error) {
      console.error('[FileInput] Upload failed:', error)
      Toast.error({
        content: error instanceof Error ? error.message : 'File upload failed',
        duration: 3,
      })
      throw error
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
    }
  }

  if (isTestrun && !readonly) {
    const currentUrl = getFileUrl()
    const hasUrl = !!currentUrl
    const [justUploaded, setJustUploaded] = useState(false)
    const [mode, setMode] = useState(hasUrl ? 'url' : 'upload')

    React.useEffect(() => {
      if (justUploaded) {
        setJustUploaded(false)
        return
      }
      if (!currentUrl && mode === 'url') {
        setMode('upload')
      } else if (currentUrl && !mode) {
        setMode('url')
      }
    }, [currentUrl, justUploaded])

    const handleModeChange = (newMode: string) => {
      setMode(newMode as 'upload' | 'url')
      onChange?.(undefined)
    }

    return (
      <div>
        <RadioGroup type="button" value={mode} onChange={e => handleModeChange(e.target.value)} style={{ marginBottom: 8 }}>
          <Radio value="upload">{t('workflowCanvas.formMaterials.input.uploadMode')}</Radio>
          <Radio value="url">{t('workflowCanvas.formMaterials.input.urlMode')}</Radio>
        </RadioGroup>

        {mode === 'upload' && (
          <Upload
            action=""
            draggable={true}
            limit={1}
            maxSize={500 * 1024 * 1024}
            dragMainText={t('workflowCanvas.formMaterials.input.dragUploadText')}
            dragSubText={t('workflowCanvas.formMaterials.input.dragUploadSubText')}
            disabled={readonly || isUploading}
            accept={acceptPattern}
            customRequest={({ file, onProgress, onError, onSuccess }) => {
              const fileObj = file.fileInstance
              if (!fileObj) {
                console.error('[FileInput] No fileInstance in file object')
                onError?.({ status: 400 }, new Error('No file selected') as Event)
                return
              }
              handleFileUpload(fileObj, onProgress)
                .then(result => {
                  setJustUploaded(true)
                  onSuccess?.(result)
                })
                .catch(error => {
                  console.error('[FileInput] Upload error:', error)
                  onError?.({ status: 500 }, error as Event)
                })
            }}
          />
        )}

        {mode === 'url' && (
          <Input
            size="small"
            placeholder={t('workflowCanvas.formMaterials.input.enterFileUrl')}
            value={currentUrl || ''}
            onChange={(val: string) => {
              if (val) {
                onChange?.({ url: val, object_key: '' })
              } else {
                onChange?.(undefined)
              }
            }}
          />
        )}
      </div>
    )
  }

  if (isForm && !readonly) {
    const metadata = getFileMetadata()
    const fileName = metadata?.name || (value?.url ? 'File' : '')
    return (
      <div>
        <Button
          icon={<IconUpload />}
          size="small"
          onClick={() => {
            const input = document.createElement('input')
            input.type = 'file'
            input.accept = acceptPattern
            input.onchange = e => {
              const file = (e.target as HTMLInputElement).files?.[0]
              if (file) {
                handleFileUpload(file)
              }
            }
            input.click()
          }}
          disabled={readonly || isUploading}
          loading={isUploading}
        >
          {isUploading
            ? `${t('workflowCanvas.formMaterials.input.uploading') || 'Uploading...'} ${uploadProgress}%`
            : fileName || t('workflowCanvas.formMaterials.input.uploadFile')}
        </Button>
      </div>
    )
  }

  if (readonly) {
    const currentUrl = getFileUrl()
    const metadata = getFileMetadata()
    const displayName = metadata?.name || currentUrl || ''

    return <span>{displayName}</span>
  }

  return null
}

export const FILE_SUBTYPES = [
  { type: 'default', label: 'Default', accept: '*', icon: React.createElement(IconFile, { size: '14px' }) },
  { type: 'image', label: 'Image', accept: 'image/*', icon: React.createElement(IconImage, { size: '14px' }) },
  { type: 'svg', label: 'Svg', accept: '.svg,image/svg+xml', icon: React.createElement(IconImage, { size: '14px' }) },
  { type: 'audio', label: 'Audio', accept: 'audio/*', icon: React.createElement(IconMusic, { size: '14px' }) },
  { type: 'video', label: 'Video', accept: 'video/*', icon: React.createElement(IconVideo, { size: '14px' }) },
  { type: 'voice', label: 'Voice', accept: '.mp3,.wav,.ogg,.m4a,.aac', icon: React.createElement(IconMusic, { size: '14px' }) },
  { type: 'doc', label: 'Doc', accept: '.doc,.docx', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'ppt', label: 'PPT', accept: '.ppt,.pptx', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'excel', label: 'Excel', accept: '.xls,.xlsx', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'txt', label: 'Txt', accept: '.txt', icon: React.createElement(IconBook, { size: '14px' }) },
  {
    type: 'code',
    label: 'Code',
    accept:
      '.js,.ts,.jsx,.tsx,.py,.java,.cpp,.c,.cs,.go,.rs,.php,.rb,.swift,.kt,.json,.xml,.yaml,.yml,.html,.css,.scss,.less,.sh,.bash,.zsh,.fish,.sql,.md,.markdown',
    icon: React.createElement(IconCode, { size: '14px' }),
  },
  { type: 'zip', label: 'Zip', accept: '.zip,.rar,.7z,.tar,.gz,.bz2,.xz', icon: React.createElement(IconArchive, { size: '14px' }) },
] as const

export type FileSubtype = (typeof FILE_SUBTYPES)[number]['type']

const getFileIcon = (fileType?: string): React.ReactNode => {
  const subtype = FILE_SUBTYPES.find(s => s.type === (fileType || 'default'))
  return subtype?.icon || React.createElement(IconFile, { size: '14px' })
}

export const fileRegistry: Partial<JsonSchemaTypeRegistry> = {
  type: 'file',
  label: 'File',
  icon: React.createElement(IconFile, { size: '14px' }),
  container: true,
  ConstantRenderer: (props: FileInputProps) => {
    const fileType = props.schema?.fileType || 'default'
    return <FileInput {...props} fileType={fileType} />
  },
  getDefaultSchema: () => ({
    type: 'file',
    fileType: 'default',
  }),
  getValueText: (value?: FileValue) => {
    if (!value) return ''
    return value.url || value.metadata?.name || 'File'
  },
  getDefaultValue: () => undefined,
  getJsonPaths: () => ['fileType'],
  getDisplayIcon: typeSchema => {
    const fileType = typeSchema.fileType || 'default'
    return getFileIcon(fileType)
  },
  getDisplayLabel: typeSchema => {
    const fileType = typeSchema.fileType || 'default'
    const subtype = FILE_SUBTYPES.find(s => s.type === fileType)
    return subtype?.label || 'File'
  },
  getDisplayText: typeSchema => {
    const fileType = typeSchema.fileType || 'default'
    const subtype = FILE_SUBTYPES.find(s => s.type === fileType)
    return subtype?.label || 'File'
  },
  getComplexText: typeSchema => {
    const fileType = typeSchema.fileType || 'default'
    const subtype = FILE_SUBTYPES.find(s => s.type === fileType)
    return subtype ? `File<${subtype.label}>` : 'File'
  },
  conditionRule: {
    [ConditionPresetOp.IS_EMPTY]: null,
    [ConditionPresetOp.IS_NOT_EMPTY]: null,
  },
}
