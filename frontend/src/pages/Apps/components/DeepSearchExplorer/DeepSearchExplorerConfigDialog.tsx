import React, { useCallback, useMemo, useState } from 'react'
import { AlertCircle, Check, CheckCircle, Cpu, Eye, EyeOff, Loader2, Play, Search, Settings, Trash2, X } from 'lucide-react'
import { IconButton, Tooltip } from '@mui/material'
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
import { taskSpaceWebSearchEngineService } from './taskSpaceWebSearchEngineService'

interface DeepSearchExplorerConfigDialogProps {
  agent: MentionItem | null
  open: boolean
  onClose: () => void
  onSave: (agentId: string, config: DeepSearchExplorerConfig) => void
  savedConfigs?: Record<string, AppAgentConfig>
  spaceId?: string
  isFirstConfig?: boolean
  availableModels?: Model[]
  modelsLoading?: boolean
}

type DeepSearchExplorerTabId = 'general' | 'search' | 'model'

interface KnowledgeBaseDetail {
  id: string
  name: string
  desc?: string
  status?: string
}

type ProviderTestName = 'jina' | 'serper'

type ProviderTestStatus = 'idle' | 'testing' | 'success' | 'error'

interface ProviderTestState {
  status: ProviderTestStatus
  message: string
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
  savedConfigs = {},
  spaceId = '',
  isFirstConfig = false,
  availableModels = [],
  modelsLoading = false,
}) => {
  const { t } = useTranslation()
  const [showKnowledgeBaseSelector, setShowKnowledgeBaseSelector] = useState(false)
  const [activeTab, setActiveTab] = useState<DeepSearchExplorerTabId>('general')
  const [selectedKnowledgeBasesDetail, setSelectedKnowledgeBasesDetail] = useState<KnowledgeBaseDetail[]>([])
  const [providerTests, setProviderTests] = useState<Record<ProviderTestName, ProviderTestState>>({
    jina: { status: 'idle', message: '' },
    serper: { status: 'idle', message: '' },
  })
  const [apiKeyVisibility, setApiKeyVisibility] = useState<Record<ProviderTestName, boolean>>({
    jina: false,
    serper: false,
  })

  const defaultConfig = useMemo(
    () => toDeepSearchExplorerConfig(savedConfigs[agent?.id || 'deepsearch-explorer']),
    [savedConfigs, agent?.id],
  )

  const [config, setConfig] = useState<DeepSearchExplorerConfig>(defaultConfig)

  React.useEffect(() => {
    if (open) {
      setConfig(toDeepSearchExplorerConfig(savedConfigs[agent?.id || 'deepsearch-explorer']))
      setActiveTab('general')
    }
    setShowKnowledgeBaseSelector(false)
    setProviderTests({
      jina: { status: 'idle', message: '' },
      serper: { status: 'idle', message: '' },
    })
    setApiKeyVisibility({
      jina: false,
      serper: false,
    })
  }, [open, savedConfigs, agent?.id])

  const getProviderErrorMessage = useCallback((
    provider: ProviderTestName,
    rawMessage: string,
    statusCode?: number
  ) => {
    const normalizedMessage = rawMessage.toLowerCase()
    const providerLabel = t(`apps.config.explorerEngine.test.providers.${provider}`)
    const isAuthorizationError =
      statusCode === 401
      || statusCode === 403
      || normalizedMessage.includes('forbidden')
      || normalizedMessage.includes('unauthorized')
      || normalizedMessage.includes('invalid api key')
      || normalizedMessage.includes('api key is invalid')
      || normalizedMessage.includes('permission denied')
      || normalizedMessage.includes('execution_error')

    if (isAuthorizationError) {
      return t('apps.config.explorerEngine.test.invalidApiKey', { provider: providerLabel })
    }

    const isNetworkIssue =
      normalizedMessage.includes('network')
      || normalizedMessage.includes('timeout')
      || normalizedMessage.includes('timed out')
      || normalizedMessage.includes('connection')
      || normalizedMessage.includes('dns')

    if (isNetworkIssue) {
      return t('apps.config.explorerEngine.test.networkError')
    }

    return t('apps.config.explorerEngine.test.providerFailed', { provider: providerLabel })
  }, [t])

  const updateConfig = useCallback(<K extends keyof DeepSearchExplorerConfig>(
    key: K,
    value: DeepSearchExplorerConfig[K],
  ) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }, [])

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
      if (!(config.jinaApiKey ?? '').trim() || !(config.serperApiKey ?? '').trim()) {
        errors.push(t('apps.config.validation.webModeRequiresApiKey'))
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
  }, [config, t])

  const { valid, errors } = validateConfig()

  const handleSave = () => {
    if (!agent || !valid) return
    onSave(agent.id, config)
    onClose()
  }

  const handleProviderConnectionTest = useCallback(async (provider: ProviderTestName) => {
    const apiKey = (provider === 'jina' ? config.jinaApiKey : config.serperApiKey) ?? ''
    if (!spaceId) {
      setProviderTests(prev => ({
        ...prev,
        [provider]: {
          status: 'error',
          message: t('apps.config.explorerEngine.test.networkError'),
        },
      }))
      return
    }
    if (!apiKey.trim()) {
      setProviderTests(prev => ({
        ...prev,
        [provider]: {
          status: 'error',
          message: t('apps.config.validation.webModeRequiresApiKey'),
        },
      }))
      return
    }

    setProviderTests(prev => ({
      ...prev,
      [provider]: {
        status: 'testing',
        message: '',
      },
    }))

    try {
      const response = await taskSpaceWebSearchEngineService.testProviderConnection(spaceId, provider, apiKey.trim())
      if (response.code >= 200 && response.code < 300) {
        const providerLabel = t(`apps.config.explorerEngine.test.providers.${provider}`)
        setProviderTests(prev => ({
          ...prev,
          [provider]: {
            status: 'success',
            message: t('apps.config.explorerEngine.test.providerSuccess', { provider: providerLabel }),
          },
        }))
      } else {
        setProviderTests(prev => ({
          ...prev,
          [provider]: {
            status: 'error',
            message: getProviderErrorMessage(
              provider,
              response.msg || t('apps.config.explorerEngine.test.testFailed'),
              response.code
            ),
          },
        }))
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('apps.config.explorerEngine.test.networkError')
      setProviderTests(prev => ({
        ...prev,
        [provider]: {
          status: 'error',
          message: getProviderErrorMessage(provider, errorMessage),
        },
      }))
    }
  }, [config.jinaApiKey, config.serperApiKey, getProviderErrorMessage, spaceId, t])

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
            <label className="block">
              <span className="block text-sm font-medium text-gray-700 mb-2">{t('apps.config.search.jinaApiKey')}</span>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    type={apiKeyVisibility.jina ? 'text' : 'password'}
                    value={config.jinaApiKey ?? ''}
                    onChange={e => {
                      updateConfig('jinaApiKey', e.target.value)
                      setProviderTests(prev => ({
                        ...prev,
                        jina: { status: 'idle', message: '' },
                      }))
                    }}
                    placeholder={t('apps.config.search.apiKeyPlaceholder')}
                    className={`w-full px-3 pr-10 py-2 ${RADIUS_BUTTON} border border-gray-300 text-sm`}
                  />
                  <Tooltip title={apiKeyVisibility.jina ? t('apps.config.explorerEngine.test.hideApiKey') : t('apps.config.explorerEngine.test.showApiKey')}>
                    <IconButton
                      size="small"
                      onClick={() => {
                        setApiKeyVisibility(prev => ({
                          ...prev,
                          jina: !prev.jina,
                        }))
                      }}
                      className="!absolute right-1 top-1/2 -translate-y-1/2 text-gray-700 hover:text-blue-600 hover:bg-blue-50"
                    >
                      {apiKeyVisibility.jina ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </IconButton>
                  </Tooltip>
                </div>
                <Tooltip title={providerTests.jina.status === 'testing' ? t('apps.config.explorerEngine.test.testing') : t('apps.config.explorerEngine.action.test')}>
                  <span>
                    <IconButton
                      size="small"
                      onClick={() => handleProviderConnectionTest('jina')}
                      disabled={providerTests.jina.status === 'testing'}
                      className="text-gray-700 hover:text-blue-600 hover:bg-blue-50"
                    >
                      {providerTests.jina.status === 'testing'
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Play className="w-4 h-4" />}
                    </IconButton>
                  </span>
                </Tooltip>
              </div>
              {providerTests.jina.status !== 'idle' && (
                <p className={`mt-2 text-xs flex items-center gap-1.5 ${providerTests.jina.status === 'success' ? 'text-green-700' : providerTests.jina.status === 'error' ? 'text-red-700' : 'text-gray-600'}`}>
                  {providerTests.jina.status === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
                  {providerTests.jina.status === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
                  {providerTests.jina.status === 'testing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{providerTests.jina.status === 'testing' ? t('apps.config.explorerEngine.test.testing') : providerTests.jina.message}</span>
                </p>
              )}
            </label>

            <label className="block">
              <span className="block text-sm font-medium text-gray-700 mb-2">{t('apps.config.search.serperApiKey')}</span>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    type={apiKeyVisibility.serper ? 'text' : 'password'}
                    value={config.serperApiKey ?? ''}
                    onChange={e => {
                      updateConfig('serperApiKey', e.target.value)
                      setProviderTests(prev => ({
                        ...prev,
                        serper: { status: 'idle', message: '' },
                      }))
                    }}
                    placeholder={t('apps.config.search.apiKeyPlaceholder')}
                    className={`w-full px-3 pr-10 py-2 ${RADIUS_BUTTON} border border-gray-300 text-sm`}
                  />
                  <Tooltip title={apiKeyVisibility.serper ? t('apps.config.explorerEngine.test.hideApiKey') : t('apps.config.explorerEngine.test.showApiKey')}>
                    <IconButton
                      size="small"
                      onClick={() => {
                        setApiKeyVisibility(prev => ({
                          ...prev,
                          serper: !prev.serper,
                        }))
                      }}
                      className="!absolute right-1 top-1/2 -translate-y-1/2 text-gray-700 hover:text-blue-600 hover:bg-blue-50"
                    >
                      {apiKeyVisibility.serper ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </IconButton>
                  </Tooltip>
                </div>
                <Tooltip title={providerTests.serper.status === 'testing' ? t('apps.config.explorerEngine.test.testing') : t('apps.config.explorerEngine.action.test')}>
                  <span>
                    <IconButton
                      size="small"
                      onClick={() => handleProviderConnectionTest('serper')}
                      disabled={providerTests.serper.status === 'testing'}
                      className="text-gray-700 hover:text-blue-600 hover:bg-blue-50"
                    >
                      {providerTests.serper.status === 'testing'
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Play className="w-4 h-4" />}
                    </IconButton>
                  </span>
                </Tooltip>
              </div>
              {providerTests.serper.status !== 'idle' && (
                <p className={`mt-2 text-xs flex items-center gap-1.5 ${providerTests.serper.status === 'success' ? 'text-green-700' : providerTests.serper.status === 'error' ? 'text-red-700' : 'text-gray-600'}`}>
                  {providerTests.serper.status === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
                  {providerTests.serper.status === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
                  {providerTests.serper.status === 'testing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{providerTests.serper.status === 'testing' ? t('apps.config.explorerEngine.test.testing') : providerTests.serper.message}</span>
                </p>
              )}
            </label>
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
    </>
  )
}

export default DeepSearchExplorerConfigDialog
