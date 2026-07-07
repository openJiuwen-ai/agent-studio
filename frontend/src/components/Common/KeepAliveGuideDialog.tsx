import React, { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Copy, Check } from 'lucide-react'
import { copyToClipboard } from '../../pages/Apps/utils/utils'

/**
 * "设置本网页保持活跃"操作指引弹窗
 * 展示 Edge / Chrome 两种浏览器把当前站点加入"保持活跃"名单的操作步骤
 */

export interface KeepAliveGuideDialogProps {
  open: boolean
  onClose: () => void
}

type BrowserKind = 'edge' | 'chrome'

const detectBrowser = (): BrowserKind => {
  const ua = navigator.userAgent
  if (/Edg\//.test(ua)) return 'edge'
  return 'chrome'
}

// 步骤文案里用双引号标出的菜单项/按钮名称加粗显示，方便一眼看出要点哪里
const renderStepText = (step: string): React.ReactNode => {
  const parts = step.split('"')
  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <strong key={index} className="font-semibold text-gray-900">
        &quot;{part}&quot;
      </strong>
    ) : (
      <React.Fragment key={index}>{part}</React.Fragment>
    )
  )
}

const KeepAliveGuideDialog: React.FC<KeepAliveGuideDialogProps> = ({ open, onClose }) => {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const defaultBrowser = useMemo(() => detectBrowser(), [])
  const [activeBrowser, setActiveBrowser] = useState<BrowserKind>(defaultBrowser)

  if (!open) return null

  const siteUrl = window.location.origin

  const handleCopy = async () => {
    const success = await copyToClipboard(siteUrl)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const edgeSteps = t('apps.chat.taskRunning.keepAliveGuide.edge.steps', { returnObjects: true }) as string[]
  const chromeSteps = t('apps.chat.taskRunning.keepAliveGuide.chrome.steps', { returnObjects: true }) as string[]
  const steps = activeBrowser === 'edge' ? edgeSteps : chromeSteps

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full mx-4 transform transition-all">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Title */}
        <h3 className="text-lg font-bold text-gray-900 pr-8">
          {t('apps.chat.taskRunning.keepAliveGuide.title')}
        </h3>

        {/* Description */}
        <p className="text-sm text-gray-600 mt-2 leading-relaxed">
          {t('apps.chat.taskRunning.keepAliveGuide.description')}
        </p>

        {/* Current site address */}
        <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500">{t('apps.chat.taskRunning.keepAliveGuide.currentSite')}</p>
            <p className="text-sm font-medium text-gray-900 truncate">{siteUrl}</p>
          </div>
          <button
            onClick={handleCopy}
            className="shrink-0 flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors text-gray-700"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? t('apps.chat.taskRunning.keepAliveGuide.copied') : t('apps.chat.taskRunning.keepAliveGuide.copy')}
          </button>
        </div>

        {/* Browser tabs */}
        <div className="mt-5 flex gap-2 border-b border-gray-200">
          {(['edge', 'chrome'] as BrowserKind[]).map(browser => (
            <button
              key={browser}
              onClick={() => setActiveBrowser(browser)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeBrowser === browser
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t(`apps.chat.taskRunning.keepAliveGuide.${browser}.title`)}
            </button>
          ))}
        </div>

        {/* Steps */}
        <ol className="mt-4 space-y-2.5">
          {steps.map((step, index) => (
            <li key={index} className="flex items-start gap-3 text-sm text-gray-700">
              <span className="shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold flex items-center justify-center mt-0.5">
                {index + 1}
              </span>
              <span className="leading-relaxed">{renderStepText(step)}</span>
            </li>
          ))}
        </ol>

        {/* Actions */}
        <div className="mt-6">
          <button
            onClick={onClose}
            className="w-full px-6 py-3 rounded-xl font-medium transition-all bg-blue-600 text-white hover:bg-blue-700"
          >
            {t('apps.chat.taskRunning.keepAliveGuide.close')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default KeepAliveGuideDialog
