/**
 * Template View Dialog Component
 * 模板查看对话框组件
 * 用于展示模板的详细内容（仅读模式）
 * 支持预览、代码、分屏三种视图模式
 */

import React, { useState, useEffect, useMemo } from 'react'
import { X, Loader2, Eye, Code, Columns } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { RADIUS_CONTAINER, RADIUS_BUTTON } from '../../../constants/styles'
import CodeMirror from '@uiw/react-codemirror'
import { markdown } from '@codemirror/lang-markdown'
import ReactMarkdown from 'react-markdown'

export type ViewMode = 'preview' | 'code' | 'split'

export interface TemplateViewDialogProps {
  /** 是否显示对话框 */
  open: boolean
  /** 关闭对话框 */
  onClose: () => void
  /** 模板名称 */
  templateName?: string
  /** 模板描述 */
  templateDesc?: string
  /** 模板内容（Base64 编码或纯文本） */
  templateContent?: string
  /** 加载状态 */
  loading?: boolean
}

/**
 * 模板查看对话框组件
 */
export const TemplateViewDialog: React.FC<TemplateViewDialogProps> = ({
  open,
  onClose,
  templateName,
  templateDesc,
  templateContent,
  loading = false
}) => {
  const { t } = useTranslation()
  const [viewMode, setViewMode] = useState<ViewMode>('preview')

  // 解码内容 - 尝试 Base64（支持 UTF-8 中文），如果失败则直接使用原始内容
  const decodedContent = useMemo(() => {
    if (!templateContent) {
      return ''
    }

    // 尝试解码 Base64（支持 UTF-8）
    try {
      const binaryString = atob(templateContent)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }
      return new TextDecoder('utf-8').decode(bytes)
    } catch (e) {
      // Base64 解码失败，可能是纯文本，直接使用
      return templateContent
    }
  }, [templateContent])

  // 计算是否显示空状态
  const isEmpty = !decodedContent || decodedContent.trim() === ''

  // 根据视图模式动态调整宽度
  const dialogWidth = viewMode === 'split' ? 'max-w-5xl' : 'max-w-3xl'

  // 键盘事件处理
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className={`bg-white ${RADIUS_CONTAINER} shadow-xl w-full ${dialogWidth} mx-4 overflow-hidden flex flex-col min-h-[40vh] max-h-[95vh]`}>
        {/* 头部 - 精简设计 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div>
              <h2 className="text-base font-semibold text-gray-900 truncate">{templateName || t('apps.config.template.details')}</h2>
              {templateDesc && (
                <p className="text-xs text-gray-500 truncate mt-0.5">{templateDesc}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* 视图模式切换 - 更紧凑的设计 */}
            <div className={`flex items-center bg-gray-100/80 ${RADIUS_BUTTON} p-0.5`}>
              <button
                onClick={() => setViewMode('preview')}
                className={`p-1.5 ${RADIUS_BUTTON} transition-all ${
                  viewMode === 'preview'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                title={t('apps.config.template.preview')}
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('code')}
                className={`p-1.5 ${RADIUS_BUTTON} transition-all ${
                  viewMode === 'code'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                title={t('apps.config.template.code')}
              >
                <Code className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('split')}
                className={`p-1.5 ${RADIUS_BUTTON} transition-all ${
                  viewMode === 'split'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                title={t('apps.config.template.split')}
              >
                <Columns className="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              onClick={onClose}
              className={`p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 ${RADIUS_BUTTON} transition-colors`}
              title={t('apps.config.template.close')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
                <p className="text-sm text-gray-500">{t('apps.model.loading')}</p>
              </div>
            </div>
          ) : isEmpty ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <p className="text-sm text-gray-500">{t('apps.config.template.available')}</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-hidden">
              {/* 单视图模式：预览或代码 */}
              {viewMode !== 'split' && (
                <div className="h-full overflow-y-auto">
                  {viewMode === 'preview' ? (
                    <div className="p-6">
                      <article className="prose prose-sm prose-gray max-w-none">
                        <ReactMarkdown>{decodedContent}</ReactMarkdown>
                      </article>
                    </div>
                  ) : (
                    <div className="h-full">
                      <CodeMirror
                        value={decodedContent}
                        editable={false}
                        extensions={[markdown()]}
                        className="h-full text-sm"
                        style={{ fontSize: '14px' }}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* 分屏模式 */}
              {viewMode === 'split' && (
                <div className="h-full flex">
                  {/* 左侧：预览 */}
                  <div className="flex-1 overflow-y-auto border-r border-gray-100">
                    <div className="p-5">
                      <article className="prose prose-sm prose-gray max-w-none">
                        <ReactMarkdown>{decodedContent}</ReactMarkdown>
                      </article>
                    </div>
                  </div>

                  {/* 右侧：代码 */}
                  <div className="flex-1 overflow-hidden">
                    <CodeMirror
                      value={decodedContent}
                      editable={false}
                      extensions={[markdown()]}
                      className="h-full text-sm"
                      style={{ fontSize: '14px' }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TemplateViewDialog
