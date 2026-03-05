import React from 'react'
import { useTranslation, Trans } from 'react-i18next'
import { X } from 'lucide-react'

const PrivacyPolicyPage: React.FC = () => {
  const { t } = useTranslation()

  const handleClose = () => {
    window.close()
  }

  const boldComponent = <span className="font-bold" />

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-12 px-4 sm:px-6 lg:px-8">
      {/* 顶部导航 */}
      <div className="max-w-3xl mx-auto mb-8">
        <button onClick={handleClose} className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors">
          <X className="w-4 h-4" />
          {t('privacy.close', '关闭')}
        </button>
      </div>

      {/* 隐私政策内容 */}
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg p-8 sm:p-12">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">{t('privacy.title', '隐私声明')}</h1>

        <div className="text-sm text-gray-600 leading-loose">
          <p className="indent-8">
            <Trans i18nKey="privacy.policy.paragraph1" components={{ bold: boldComponent }} />
          </p>
          <p className="indent-8">
            <Trans i18nKey="privacy.policy.paragraph2" components={{ bold: boldComponent }} />
          </p>
        </div>
      </div>
    </div>
  )
}
export default PrivacyPolicyPage
