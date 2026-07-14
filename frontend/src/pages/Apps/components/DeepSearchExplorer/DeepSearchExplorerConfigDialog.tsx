import React, { useCallback, useMemo, useState } from 'react'
import { AlertCircle, Check, Cpu, Loader2, Play, Search, Settings, Trash2, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { MentionItem } from '../MentionPicker'
import type { Model } from '@/types/promptType'
import { RADIUS_BUTTON, RADIUS_CIRCLE, RADIUS_CONTAINER } from '../../constants/styles'
import { ConfigSection } from '../config/ConfigSection'
import { KnowledgeBaseConfigDialog } from '../config/dialogs/KnowledgeBaseConfigDialog'
import {
  type AppAgentConfig,
  type DeepSearchExplorerConfig,
  toDeepSearchExplorerConfig,
} from '../../utils/deepsearchConstants'
import WebFetchProviderConfigDialog, { WebFetchProviderSummaryCard } from './WebFetchProviderConfigDialog'
import WebSearchEngineConfigDialog, { WebSearchEngineSummaryCard } from './WebSearchEngineConfigDialog'
import { testWebFetchProvider, testWebSearchProvider, type ProviderTestResponse } from './api'

interface DeepSearchExplorerConfigDialogProps {
  agent: MentionItem | null
  open: boolean
  onClose: () => void
  onSave: (agentId: string, config: DeepSearchExplorerConfig) => void
  onClearProviderCredentials?: (agentId: string, config: DeepSearchExplorerConfig) => void
  savedConfigs?: Record<string, AppAgentConfig>
  spaceId?: string
  isFirstConfig?: boolean
  availableModels?: Model[]
  modelsLoading?: boolean
}

type DeepSearchExplorerTabId = 'general' | 'search' | 'model'
type ProviderTestKind = 'search' | 'fetch'
type ProviderTestStatusValue = 'untested' | 'passed' | 'failed'
type ProviderTestStatus = Record<ProviderTestKind, ProviderTestStatusValue>

interface KnowledgeBaseDetail {
  id: string
  name: string
  desc?: string
  status?: string
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value))

const parseIntOr = (value: string, fallback: number) => {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

const ToggleSwitch: React.FC<{
  checked: boolean
  onChange: (checked: boolean) => void
}> = ({ checked, onChange }) => {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 ${RADIUS_CIRCLE} transition-colors duration-200 ${checked ? 'bg-blue-600' : 'bg-gray-300'}`}
    >
      <span
        className={`absolute top-1 left-1 w-4 h-4 bg-white ${RADIUS_CIRCLE} shadow transition-transform duration-200 ${checked ? 'translate-x-5' : ''}`}
      />
    </button>
  )
}

const DeepSearchExplorerConfigDialog: React.FC<DeepSearchExplorerConfigDialogProps> = ({
  agent,
  open,
  onClose,
  onSave,
  onClearProviderCredentials,
  savedConfigs = {},
  spaceId = '',
  isFirstConfig = false,
  availableModels = [],
  modelsLoading = false,
}) => {
  const { t } = useTranslation()
  const defaultConfig = useMemo(
    () => toDeepSearchExplorerConfig(savedConfigs[agent?.id || 'deepsearch-explorer']),
    [savedConfigs, agent?.id],
  )
  const [showKnowledgeBaseSelector, setShowKnowledgeBaseSelector] = useState(false)
  const [webSearchConfigDialogOpen, setWebSearchConfigDialogOpen] = useState(false)
  const [webFetchConfigDialogOpen, setWebFetchConfigDialogOpen] = useState(false)
  const [providerTestKind, setProviderTestKind] = useState<ProviderTestKind | null>(null)
  const [providerTestInput, setProviderTestInput] = useState('')
  const [providerTestResults, setProviderTestResults] = useState<Record<string, unknown>[] | null>(null)
  const [providerTestError, setProviderTestError] = useState('')
  const [providerTestRunning, setProviderTestRunning] = useState(false)
  const [providerTestStatus, setProviderTestStatus] = useState<ProviderTestStatus>({
    search: defaultConfig.webSearchProviderTestPassed ? 'passed' : 'untested',
    fetch: defaultConfig.webFetchProviderTestPassed ? 'passed' : 'untested',
  })
  const [activeTab, setActiveTab] = useState<DeepSearchExplorerTabId>('general')
  const [selectedKnowledgeBasesDetail, setSelectedKnowledgeBasesDetail] = useState<KnowledgeBaseDetail[]>([])

  const [config, setConfig] = useState<DeepSearchExplorerConfig>(defaultConfig)

  React.useEffect(() => {
    if (open) {
      const nextConfig = toDeepSearchExplorerConfig(savedConfigs[agent?.id || 'deepsearch-explorer'])
      setConfig(nextConfig)
      setActiveTab('general')
      setProviderTestStatus({
        search: nextConfig.webSearchProviderTestPassed ? 'passed' : 'untested',
        fetch: nextConfig.webFetchProviderTestPassed ? 'passed' : 'untested',
      })
    } else {
      setProviderTestStatus({ search: 'untested', fetch: 'untested' })
    }
    setShowKnowledgeBaseSelector(false)
    setProviderTestKind(null)
    setProviderTestInput('')
    setProviderTestResults(null)
    setProviderTestError('')
  }, [open, savedConfigs, agent?.id])

  const updateConfig = useCallback(<K extends keyof DeepSearchExplorerConfig>(
    key: K,
    value: DeepSearchExplorerConfig[K],
  ) => {
    const previousValue = config[key]
    if (JSON.stringify(previousValue) === JSON.stringify(value)) return

    setConfig(prev => ({ ...prev, [key]: value }))
    if (key === 'webSearchEngineConfig') {
      setProviderTestStatus(prev => ({ ...prev, search: 'untested' }))
      setConfig(prev => ({ ...prev, webSearchProviderTestPassed: false }))
    }
    if (key === 'webFetchProviderConfig') {
      setProviderTestStatus(prev => ({ ...prev, fetch: 'untested' }))
      setConfig(prev => ({ ...prev, webFetchProviderTestPassed: false }))
    }
  }, [config])

  const openProviderTest = useCallback((kind: ProviderTestKind) => {
    setProviderTestKind(kind)
    setProviderTestInput(kind === 'search' ? t('apps.config.deepSearchProviderTest.defaultQuery') : t('apps.config.deepSearchProviderTest.defaultUrl'))
    setProviderTestResults(null)
    setProviderTestError('')
  }, [t])

  const closeProviderTest = useCallback(() => {
    if (providerTestRunning) return
    setProviderTestKind(null)
    setProviderTestInput('')
    setProviderTestResults(null)
    setProviderTestError('')
  }, [providerTestRunning])

  const executeProviderTest = useCallback(async () => {
    if (!providerTestKind || !spaceId) return

    const searchConfig = config.webSearchEngineConfig
    const fetchConfig = config.webFetchProviderConfig
    if ((providerTestKind === 'search' && !searchConfig) || (providerTestKind === 'fetch' && !fetchConfig)) {
      setProviderTestError(t('apps.config.validation.webModeRequiresApiKey'))
      return
    }

    setProviderTestRunning(true)
    setProviderTestResults(null)
    setProviderTestError('')
    setProviderTestStatus(previous => ({ ...previous, [providerTestKind]: 'untested' }))
    try {
      const response: ProviderTestResponse = providerTestKind === 'search'
        ? await testWebSearchProvider(spaceId, searchConfig!, providerTestInput)
        : await testWebFetchProvider(spaceId, fetchConfig!, providerTestInput)
      setProviderTestResults(response.datas)
      setProviderTestStatus(previous => ({ ...previous, [providerTestKind]: 'passed' }))
      setConfig(previous => ({
        ...previous,
        ...(providerTestKind === 'search'
          ? { webSearchProviderTestPassed: true }
          : { webFetchProviderTestPassed: true }),
      }))
    } catch (err) {
      setProviderTestError(err instanceof Error ? err.message : t('apps.config.deepSearchProviderTest.failed'))
      setProviderTestStatus(previous => ({ ...previous, [providerTestKind]: 'failed' }))
    } finally {
      setProviderTestRunning(false)
    }
  }, [config.webFetchProviderConfig, config.webSearchEngineConfig, providerTestInput, providerTestKind, spaceId, t])

  const loadKnowledgeBasesDetail = useCallback(async (kbIds: string[]) => {
    if (!spaceId || kbIds.length === 0) {
      setSelectedKnowledgeBasesDetail([])
      return
    }

    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const unresolvedIds = new Set(kbIds)
      const details: KnowledgeBaseDetail[] = []
      const pageSize = 100
      let page = 1
      let hasMore = true

      while (hasMore && unresolvedIds.size > 0) {
        const response = await KnowledgeBaseService.getDeepSearchKnowledgeBasesList({
          space_id: spaceId,
          page,
          size: pageSize,
        })

        if (response.code !== 200 || !response.data) {
          break
        }

        const items = Array.isArray(response.data.items) ? response.data.items : []
        for (const item of items) {
          const itemId = typeof item?.id === 'string' ? item.id : ''
          if (!itemId || !unresolvedIds.has(itemId)) continue
          details.push({
            id: itemId,
            name: typeof item?.name === 'string' && item.name.trim().length > 0 ? item.name : itemId,
            desc: typeof item?.desc === 'string' ? item.desc : undefined,
            status: typeof item?.status === 'string' ? item.status : undefined,
          })
          unresolvedIds.delete(itemId)
        }

        hasMore = items.length === pageSize
        page += 1
      }

      setSelectedKnowledgeBasesDetail(details)
    } catch (err) {
      console.error('Failed to load knowledge bases details:', err)
      setSelectedKnowledgeBasesDetail([])
    }
  }, [spaceId])

  React.useEffect(() => {
    if (!open || !spaceId) {
      setSelectedKnowledgeBasesDetail([])
      return
    }

    if (config.selectedKnowledgeBaseIds.length > 0) {
      loadKnowledgeBasesDetail(config.selectedKnowledgeBaseIds)
    } else {
      setSelectedKnowledgeBasesDetail([])
    }
  }, [config.selectedKnowledgeBaseIds, loadKnowledgeBasesDetail, open, spaceId])

  const validateConfig = useCallback(() => {
    const errors: string[] = []

    if (!config.planningModelId) errors.push(t('apps.config.validation.planningModelRequired'))
    if (!config.searchModelId) errors.push(t('apps.config.validation.searchModelRequired'))

    if (config.searchMode === 'web') {
      const hasWebSearchConfig = Boolean(
        config.webSearchEngineConfig?.searchEngineName
        && config.webSearchEngineConfig.searchApiKey.trim()
        && config.webSearchEngineConfig.searchUrl.trim(),
      )
      const hasWebFetchConfig = Boolean(
        config.webFetchProviderConfig?.providerName && config.webFetchProviderConfig.apiKey.trim(),
      )
      if (!hasWebSearchConfig || !hasWebFetchConfig) {
        errors.push(t('apps.config.validation.webModeRequiresApiKey'))
      }
      if (providerTestStatus.search !== 'passed' || providerTestStatus.fetch !== 'passed') {
        errors.push(t('apps.config.validation.webModeRequiresProviderVerified'))
      }
    }

    if (config.searchMode === 'local') {
      if (!config.selectedKnowledgeBaseIds.length) errors.push(t('apps.config.validation.localModeRequires'))
    }

    if (config.actionsExploredLimit < 1 || config.actionsExploredLimit > 200) {
      errors.push(t('apps.config.validation.actionsExploredLimitRange'))
    }
    if (config.timeLimit < 1 || config.timeLimit > 3600) {
      errors.push(t('apps.config.validation.timeLimitRange'))
    }

    return { valid: errors.length === 0, errors }
  }, [config, providerTestStatus, t])

  const { valid, errors } = validateConfig()

  const handleSave = () => {
    if (!agent || !valid) return
    onSave(agent.id, config)
    onClose()
  }

  const clearProviderCredentials = () => {
    if (!agent) return

    const clearedConfig: DeepSearchExplorerConfig = {
      ...config,
      webSearchEngineConfig: undefined,
      webFetchProviderConfig: undefined,
      webSearchProviderTestPassed: false,
      webFetchProviderTestPassed: false,
    }
    setConfig(clearedConfig)
    setProviderTestStatus({ search: 'untested', fetch: 'untested' })
    onClearProviderCredentials?.(agent.id, clearedConfig)
  }

  const modelOptions = availableModels.map(model => ({
    id: model.openModel.model_id,
    label: model.openModel.name || model.openModel.model_id,
  }))

  const tabs = useMemo(
    () => [
      { id: 'general' as const, icon: <Settings className="w-5 h-5" />, label: t('apps.config.tabs.general') },
      { id: 'search' as const, icon: <Search className="w-5 h-5" />, label: t('apps.config.tabs.search') },
      { id: 'model' as const, icon: <Cpu className="w-5 h-5" />, label: t('apps.config.tabs.model') },
    ],
    [t],
  )

  const getStatusDisplay = (status?: string): { text: string; color: string } | null => {
    if (!status) return null
    if (status === 'indexed') {
      return { text: t('apps.config.knowledge.status.ready'), color: 'bg-green-100 text-green-700' }
    }
    if (status === 'failed') {
      return { text: t('apps.config.knowledge.status.failed'), color: 'bg-red-100 text-red-700' }
    }
    return { text: t('apps.config.knowledge.status.processing'), color: 'bg-gray-100 text-gray-700' }
  }

  const displayedKnowledgeBases = useMemo(() => {
    const mapped = new Map(selectedKnowledgeBasesDetail.map(kb => [kb.id, kb]))
    return config.selectedKnowledgeBaseIds.map(id => mapped.get(id) ?? { id, name: id })
  }, [config.selectedKnowledgeBaseIds, selectedKnowledgeBasesDetail])

  // Provider dialogs update this local task configuration immediately. Do not
  // compare against the initially loaded config here: doing so hides Test
  // whenever a user confirms an updated provider configuration.
  const hasTestableWebSearchConfig = Boolean(
    spaceId
    && config.webSearchEngineConfig?.searchEngineName
    && config.webSearchEngineConfig.searchApiKey.trim()
    && config.webSearchEngineConfig.searchUrl.trim(),
  )
  const hasTestableWebFetchConfig = Boolean(
    spaceId
    && config.webFetchProviderConfig?.providerName
    && config.webFetchProviderConfig.apiKey.trim(),
  )

  const renderGeneralTab = () => (
    <div className="space-y-8">
      <ConfigSection title={t('apps.config.general.searchProcessSettings')}>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-1">
            <div>
              <span className="text-sm text-gray-900 font-medium">{t('apps.config.general.enableQuestionRouter')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.enableQuestionRouterDesc')}</p>
            </div>
            <ToggleSwitch
              checked={config.enableQuestionRouter}
              onChange={checked => updateConfig('enableQuestionRouter', checked)}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <label className="text-sm text-gray-700">
              <span className="font-medium">{t('apps.config.general.actionsExploredLimit')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.actionsExploredLimitDesc')}</p>
              <input
                type="number"
                min={1}
                max={200}
                value={config.actionsExploredLimit}
                onChange={e => updateConfig('actionsExploredLimit', clamp(parseIntOr(e.target.value, 200), 1, 200))}
                className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </label>

            <label className="text-sm text-gray-700">
              <span className="font-medium">{t('apps.config.general.timeLimit')}</span>
              <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.general.timeLimitDesc')}</p>
              <input
                type="number"
                min={1}
                max={3600}
                value={config.timeLimit}
                onChange={e => updateConfig('timeLimit', clamp(parseIntOr(e.target.value, 3600), 1, 3600))}
                className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </label>
          </div>
        </div>
      </ConfigSection>
    </div>
  )

  const renderSearchTab = () => (
    <div className="space-y-8">
      <ConfigSection title={t('apps.config.search.mode')}>
        <div className="flex flex-col gap-2">
          {[
            { value: 'web' as const, label: t('apps.config.search.web'), desc: t('apps.config.search.webDesc') },
            { value: 'local' as const, label: t('apps.config.search.local'), desc: t('apps.config.search.localDesc') },
          ].map(option => (
            <button
              key={option.value}
              onClick={() => updateConfig('searchMode', option.value)}
              className={`px-4 py-3 ${RADIUS_BUTTON} text-sm font-medium transition-all duration-200 border text-left ${
                config.searchMode === option.value
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="block font-medium">{option.label}</span>
                  <span className="text-xs text-gray-500">{option.desc}</span>
                </div>
                {config.searchMode === option.value && <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />}
              </div>
            </button>
          ))}
        </div>
      </ConfigSection>

      <ConfigSection title={t('apps.config.search.source')}>
        {config.searchMode === 'web' ? (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm text-amber-900">
                {t('apps.config.deepSearchLocalStorage.warning')}
              </p>
              <button
                type="button"
                onClick={clearProviderCredentials}
                className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100"
              >
                {t('apps.config.deepSearchLocalStorage.clearKeys')}
              </button>
            </div>
            <WebSearchEngineSummaryCard
              config={config.webSearchEngineConfig}
              onConfigure={() => setWebSearchConfigDialogOpen(true)}
              onTest={hasTestableWebSearchConfig ? () => openProviderTest('search') : undefined}
              testStatus={providerTestStatus.search}
            />
            <WebFetchProviderSummaryCard
              config={config.webFetchProviderConfig}
              onConfigure={() => setWebFetchConfigDialogOpen(true)}
              onTest={hasTestableWebFetchConfig ? () => openProviderTest('fetch') : undefined}
              testStatus={providerTestStatus.fetch}
            />
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">📚</span>
                  <span className="text-sm font-medium text-gray-900">{t('apps.config.search.localKB')}</span>
                </div>
                <button
                  onClick={() => setShowKnowledgeBaseSelector(true)}
                  className="px-3 py-1.5 text-sm font-medium bg-blue-50 hover:bg-blue-100 text-blue-700 hover:text-blue-800 rounded-lg border border-blue-200 transition-all duration-200"
                >
                  {t('apps.config.search.configure')}
                </button>
              </div>

              {displayedKnowledgeBases.length === 0 ? (
                <div className="p-3 bg-gray-50 rounded-xl text-center">
                  <p className="text-sm text-gray-500 mb-1">{t('apps.config.search.noKB')}</p>
                  <p className="text-xs text-gray-400">{t('apps.config.search.clickToAddKB')}</p>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {displayedKnowledgeBases.map(kb => {
                    const statusDisplay = getStatusDisplay(kb.status)
                    return (
                      <div
                        key={kb.id}
                        className={`px-3 py-2 ${RADIUS_BUTTON} border transition-all duration-200 bg-white border-gray-200 hover:border-gray-300`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">📚</div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium truncate text-gray-900">{kb.name}</p>
                                {statusDisplay && (
                                  <span className={`px-1.5 py-0.5 text-xs rounded-full flex-shrink-0 ${statusDisplay.color}`}>
                                    {statusDisplay.text}
                                  </span>
                                )}
                              </div>
                              {kb.desc && <p className="text-xs truncate text-gray-500">{kb.desc}</p>}
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              updateConfig(
                                'selectedKnowledgeBaseIds',
                                config.selectedKnowledgeBaseIds.filter(id => id !== kb.id),
                              )
                              setSelectedKnowledgeBasesDetail(prev => prev.filter(item => item.id !== kb.id))
                            }}
                            className="p-1 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0"
                            title={t('apps.config.knowledge.cancel')}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </ConfigSection>
    </div>
  )

  const renderModelTab = () => (
    <div className="space-y-8">
      <ConfigSection title={t('apps.config.model.planningModel.title')}>
        <label className="text-sm text-gray-700 block">
          <span className="font-medium">{t('apps.config.model.planningModel.label')}</span>
          <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.model.planningModel.description')}</p>
          <select
            value={config.planningModelId ?? ''}
            onChange={e => updateConfig('planningModelId', e.target.value || undefined)}
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg bg-white"
            disabled={modelsLoading}
          >
            <option value="">{t('apps.config.model.selectModel')}</option>
            {modelOptions.map(option => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </ConfigSection>

      <ConfigSection title={t('apps.config.model.searchModel.title')}>
        <label className="text-sm text-gray-700 block">
          <span className="font-medium">{t('apps.config.model.searchModel.label')}</span>
          <p className="text-xs text-gray-500 mt-0.5">{t('apps.config.model.searchModel.description')}</p>
          <select
            value={config.searchModelId ?? ''}
            onChange={e => updateConfig('searchModelId', e.target.value || undefined)}
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg bg-white"
            disabled={modelsLoading}
          >
            <option value="">{t('apps.config.model.selectModel')}</option>
            {modelOptions.map(option => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </ConfigSection>
    </div>
  )

  if (!open || !agent) return null

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
        <div className={`bg-white ${RADIUS_CONTAINER} shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col`}>
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 bg-blue-100 ${RADIUS_BUTTON} flex items-center justify-center`}>
                <span className="text-blue-600 font-semibold text-sm">⚙</span>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  {isFirstConfig ? t('apps.config.title') : t('apps.config.titleEdit')}
                </h2>
                <p className="text-xs text-gray-500">
                  {agent.name}
                  {isFirstConfig ? ` · ${t('apps.config.subtitle')}` : ` · ${t('apps.config.subtitleEdit')}`}
                </p>
              </div>
            </div>
            <button onClick={onClose} className={`p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 ${RADIUS_BUTTON}`}>
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
            <div className="lg:w-60 lg:min-w-60 lg:border-r lg:border-gray-200 lg:bg-gray-50 w-full border-b border-gray-200 bg-white flex flex-col">
              <nav className="overflow-y-auto p-3 lg:flex-1 lg:space-y-1 flex flex-row lg:flex-col gap-2 lg:gap-0 overflow-x-auto">
                {tabs.map(tab => {
                  const isActive = activeTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        flex items-center gap-2 lg:gap-3 px-3 lg:px-4 py-2 lg:py-3
                        ${RADIUS_BUTTON} text-sm font-medium transition-all duration-200 text-left
                        group whitespace-nowrap flex-shrink-0
                        ${isActive ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-700 hover:bg-gray-50 lg:hover:bg-white lg:hover:shadow-sm'}
                      `}
                    >
                      <div className={`flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-500 group-hover:text-gray-600'}`}>
                        {tab.icon}
                      </div>
                      <span className={`truncate ${isActive ? 'font-semibold' : ''}`}>{tab.label}</span>
                    </button>
                  )
                })}
              </nav>
              <div className="hidden lg:block h-px bg-gray-200" />
            </div>

            <div className="flex-1 overflow-y-auto bg-white">
              <div className="p-4 lg:p-6 xl:p-8 animate-fade-in">
                {activeTab === 'general' && renderGeneralTab()}
                {activeTab === 'search' && renderSearchTab()}
                {activeTab === 'model' && renderModelTab()}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onClose}
              className={`px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-200 ${RADIUS_BUTTON}`}
            >
              {t('apps.config.cancel')}
            </button>
            <button
              onClick={handleSave}
              disabled={!valid}
              className={`px-6 py-2 text-sm font-medium ${RADIUS_BUTTON} ${valid ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
              title={!valid ? errors.join('; ') : undefined}
            >
              {t('apps.config.save')}
            </button>
          </div>
        </div>
      </div>

      <KnowledgeBaseConfigDialog
        open={showKnowledgeBaseSelector}
        onClose={() => setShowKnowledgeBaseSelector(false)}
        spaceId={spaceId}
        initialSelected={config.selectedKnowledgeBaseIds}
        onConfirm={selectedIds => {
          updateConfig('selectedKnowledgeBaseIds', selectedIds.slice(0, 1))
        }}
        selectionMode="single"
      />
      <WebSearchEngineConfigDialog
        open={webSearchConfigDialogOpen}
        config={config.webSearchEngineConfig}
        onCancel={() => setWebSearchConfigDialogOpen(false)}
        onConfirm={webSearchEngineConfig => {
          updateConfig('webSearchEngineConfig', webSearchEngineConfig)
          setWebSearchConfigDialogOpen(false)
        }}
      />
      <WebFetchProviderConfigDialog
        open={webFetchConfigDialogOpen}
        config={config.webFetchProviderConfig}
        onCancel={() => setWebFetchConfigDialogOpen(false)}
        onConfirm={webFetchProviderConfig => {
          updateConfig('webFetchProviderConfig', webFetchProviderConfig)
          setWebFetchConfigDialogOpen(false)
        }}
      />
      {providerTestKind && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
          <div className={`w-full max-w-lg ${RADIUS_CONTAINER} overflow-hidden bg-white shadow-2xl`}>
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {providerTestKind === 'search'
                  ? t('apps.config.deepSearchProviderTest.searchTitle')
                  : t('apps.config.deepSearchProviderTest.fetchTitle')}
              </h2>
              <button
                type="button"
                onClick={closeProviderTest}
                disabled={providerTestRunning}
                className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                aria-label={t('apps.config.deepSearchProviderTest.close')}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-6 py-4">
              <label className="block text-sm font-medium text-gray-700">
                {providerTestKind === 'search'
                  ? t('apps.config.deepSearchProviderTest.queryLabel')
                  : t('apps.config.deepSearchProviderTest.urlLabel')}
                <input
                  value={providerTestInput}
                  onChange={event => setProviderTestInput(event.target.value)}
                  disabled={providerTestRunning}
                  className={`mt-2 w-full border border-gray-300 px-3 py-2 text-sm ${RADIUS_BUTTON}`}
                />
              </label>

              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={executeProviderTest}
                  disabled={!providerTestInput.trim() || providerTestRunning}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${RADIUS_BUTTON} ${
                    !providerTestInput.trim() || providerTestRunning
                      ? 'cursor-not-allowed bg-gray-300 text-gray-500'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {providerTestRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  {providerTestRunning
                    ? t('apps.config.deepSearchProviderTest.testing')
                    : t('apps.config.deepSearchProviderTest.run')}
                </button>
                <button
                  type="button"
                  onClick={closeProviderTest}
                  disabled={providerTestRunning}
                  className={`px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 ${RADIUS_BUTTON}`}
                >
                  {t('apps.config.deepSearchProviderTest.cancel')}
                </button>
              </div>

              {providerTestError && (
                <div className="mt-4 flex gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                  <AlertCircle className="h-5 w-5 flex-shrink-0" />
                  <p className="break-words">{providerTestError}</p>
                </div>
              )}
              {providerTestResults && !providerTestError && (
                <div className="mt-4">
                  <div className="mb-4 flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-700">
                    <Check className="h-5 w-5 flex-shrink-0" />
                    <p>{t('apps.config.deepSearchProviderTest.succeeded')}</p>
                  </div>
                  <div className="border-t border-gray-200 pt-4">
                  <h3 className="mb-3 text-sm font-medium text-gray-900">
                    {t('apps.config.deepSearchProviderTest.results', { count: providerTestResults.length })}
                  </h3>
                  {providerTestResults.length === 0 ? (
                    <p className="text-sm text-gray-500">{t('apps.config.deepSearchProviderTest.noResults')}</p>
                  ) : (
                    <div className="max-h-64 space-y-3 overflow-y-auto">
                      {providerTestResults.map((result, index) => (
                        <pre
                          key={index}
                          className="whitespace-pre-wrap break-all rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700"
                        >
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      ))}
                    </div>
                  )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default DeepSearchExplorerConfigDialog
