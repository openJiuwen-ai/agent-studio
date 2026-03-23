import i18n from 'i18next'
import { initReactI18next, useTranslation } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import zhCN from '../locales/zh-CN.json'
import enUS from '../locales/en-US.json'

import agentCommonZh from '../locales/agent/zh-CN/common.json'
import agentEditorZh from '../locales/agent/zh-CN/editor.json'

import agentCommonEn from '../locales/agent/en-US/common.json'
import agentEditorEn from '../locales/agent/en-US/editor.json'

import workflowCommonZh from '../locales/workflow/zh-CN/common.json'
import workflowNodesZh from '../locales/workflow/zh-CN/nodes.json'

import workflowCommonEn from '../locales/workflow/en-US/common.json'
import workflowNodesEn from '../locales/workflow/en-US/nodes.json'

import runtimeZh from '../locales/runtime/zh-CN.json'
import runtimeEn from '../locales/runtime/en-US.json'

const resources = {
  'zh-CN': {
    translation: {
      ...zhCN,
      agents: {
        ...agentCommonZh,
        ...agentEditorZh,
      },
      workflowCanvas: {
        ...workflowCommonZh,
        ...workflowNodesZh,
      },
      runtime: {
        ...runtimeZh,
      },
    },
  },
  'en-US': {
    translation: {
      ...enUS,
      agents: {
        ...agentCommonEn,
        ...agentEditorEn,
      },
      workflowCanvas: {
        ...workflowCommonEn,
        ...workflowNodesEn,
      },
      runtime: {
        ...runtimeEn,
      },
    },
  },
}
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh-CN',
    debug: false,

    interpolation: {
      escapeValue: false,
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
  })

if (typeof window !== 'undefined') {
  // @ts-ignore - i18next global access
  window.i18next = i18n
}

export const useScopedTranslation = (keyPrefix: string, ns = 'translation') => {
  const { t, i18n: i18nInstance, ready } = useTranslation(ns, { keyPrefix })
  return { t, i18n: i18nInstance, ready }
}

export default i18n
