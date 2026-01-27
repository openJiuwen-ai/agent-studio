import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface LanguageContextType {
  currentLanguage: string
  changeLanguage: (language: string) => void
  availableLanguages: Array<{ code: string; name: string }>
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export const useLanguage = () => {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}

interface LanguageProviderProps {
  children: ReactNode
}

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const { i18n } = useTranslation()
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language)

  const availableLanguages = [
    { code: 'zh-CN', name: '简体中文' },
    { code: 'en-US', name: 'English' },
  ]

  const changeLanguage = async (language: string) => {
    try {
      await i18n.changeLanguage(language)
      setCurrentLanguage(language)
    } catch (error) {
      console.error('Failed to change language:', error)
    }
  }

  useEffect(() => {
    const savedLanguage = localStorage.getItem('language')
    if (savedLanguage && savedLanguage !== i18n.language) {
      changeLanguage(savedLanguage)
    }
  }, [])

  useEffect(() => {
    const handleLanguageChange = () => {
      setCurrentLanguage(i18n.language)
    }

    i18n.on('languageChanged', handleLanguageChange)

    return () => {
      i18n.off('languageChanged', handleLanguageChange)
    }
  }, [i18n])

  const value: LanguageContextType = {
    currentLanguage,
    changeLanguage,
    availableLanguages,
  }

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
