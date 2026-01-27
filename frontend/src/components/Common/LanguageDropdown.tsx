import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe, ChevronDown } from 'lucide-react'

interface LanguageDropdownProps {
  className?: string
}

const LanguageDropdown: React.FC<LanguageDropdownProps> = ({ className }) => {
  const { t, i18n } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLanguageChange = (language: string) => {
    i18n.changeLanguage(language)
    setIsOpen(false)
  }

  return (
    <div className={`relative ${className || ''}`} ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
        title={t('layout.header.language')}
      >
        <Globe className="w-4 h-4 text-gray-600" />
        <span className="hidden sm:block text-sm font-medium text-gray-700">{t('layout.header.currentLanguage')}</span>
        <ChevronDown className="w-3 h-3 text-gray-400" />
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-sm border border-gray-200 z-50">
          <div className="py-1">
            <button
              onClick={() => handleLanguageChange('zh-CN')}
              className={`flex items-center w-full px-4 py-2 text-sm hover:bg-gray-100 ${
                i18n.language === 'zh-CN' ? 'text-blue-600 font-medium' : 'text-gray-700'
              }`}
            >
              {t('layout.header.switchToChinese')}
            </button>
            <button
              onClick={() => handleLanguageChange('en-US')}
              className={`flex items-center w-full px-4 py-2 text-sm hover:bg-gray-100 ${
                i18n.language === 'en-US' ? 'text-blue-600 font-medium' : 'text-gray-700'
              }`}
            >
              {t('layout.header.switchToEnglish')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default LanguageDropdown

