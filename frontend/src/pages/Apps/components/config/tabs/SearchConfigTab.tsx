/**
 * Search Config Tab Component
 * 搜索配置标签内容组件
 * 包含搜索方式、搜索来源（搜索引擎 + 本地知识库）和搜索结果设置
 */

import React from 'react'
import { Check, Loader2, Plus, Trash2, Play } from 'lucide-react'
import { Tooltip, IconButton } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'
import { RADIUS_BUTTON } from '../../../constants/styles'

// 知识库详情类型（带状态支持）
export interface KnowledgeBaseDetail {
  id: string
  name: string
  desc?: string
  status?: string
}

// 从父组件传入的控件和数据类型
export interface WebSearchEngineConfig {
  web_search_engine_id: number
  search_engine_name: string
}

interface RangeSliderProps {
  label: string
  description: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
  step?: number
}

/**
 * Text input with label for search mode config fields
 */
const ConfigInput: React.FC<{
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: string
  required?: boolean
}> = ({ label, value, onChange, placeholder, type = 'text', required = false }) => (
  <div className="flex flex-col gap-1.5">
    <span className="text-sm text-gray-700 font-medium">
      {label}
      {required && <span className="text-red-500 ml-0.5">*</span>}
    </span>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
    />
  </div>
)

export interface SearchConfigTabProps extends ConfigTabProps {
  /** 滑块组件 */
  RangeSlider: React.FC<RangeSliderProps>
  /** 搜索引擎列表 */
  engines: WebSearchEngineConfig[]
  /** 搜索引擎加载状态 */
  enginesLoading: boolean
  /** 修改搜索引擎回调 */
  onEditEngine: (engineId: number) => void
  /** 显示搜索引擎配置对话框 */
  onShowEngineConfig: () => void
  /** 测试搜索引擎 */
  onTestEngine: (engineId: number) => void
  /** 知识库列表（用于显示已选知识库的详细信息）*/
  knowledgeBases: KnowledgeBaseDetail[]
  /** 显示知识库选择对话框 */
  onShowKnowledgeBaseSelector: () => void
  /** 删除知识库 */
  onRemoveKnowledgeBase: (kbId: string) => void
  /** 配置模式 */
  mode?: 'research' | 'search'
}

/**
 * 搜索配置标签组件
 */
export const SearchConfigTab: React.FC<SearchConfigTabProps> = ({
  config,
  updateConfig,
  RangeSlider,
  engines,
  enginesLoading,
  onEditEngine,
  onShowEngineConfig,
  onTestEngine,
  knowledgeBases,
  onShowKnowledgeBaseSelector,
  onRemoveKnowledgeBase,
  mode = 'research',
}) => {
  const { t } = useTranslation()

  // ==================== Search mode (Deep Search Explorer) ====================
  if (mode === 'search') {
    const searchModeOptions = [
      { value: 'local' as const, label: t('apps.config.search.local'), desc: t('apps.config.search.localDesc') },
      { value: 'web' as const, label: t('apps.config.search.web'), desc: t('apps.config.search.webDesc') },
    ]

    const showLocalSearch = config.searchMode === 'local'
    const showWebSearch = config.searchMode === 'web'

    return (
      <div className="space-y-8">
        {/* Search mode picker (no "all") */}
        <ConfigSection title={t('apps.config.search.mode')}>
          <div className="flex flex-col gap-2">
            {searchModeOptions.map(option => (
              <button
                key={option.value}
                onClick={() => updateConfig('searchMode', option.value)}
                className={`
                  px-4 py-3 ${RADIUS_BUTTON} text-sm font-medium transition-all duration-200 border text-left
                  ${
                    config.searchMode === option.value
                      ? 'bg-blue-50 border-blue-200 text-blue-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
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

        {/* Local KB selection */}
        {showLocalSearch && (
          <ConfigSection title={t('apps.config.search.localKB')}>
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">📚</span>
                  <span className="text-sm font-medium text-gray-900">{t('apps.config.search.localKB')}</span>
                </div>
                <button onClick={onShowKnowledgeBaseSelector} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                  <Plus className="w-3 h-3" />
                  {t('apps.config.search.configure')}
                </button>
              </div>

              {knowledgeBases.length === 0 ? (
                <div className="p-3 bg-gray-50 rounded-xl text-center">
                  <p className="text-sm text-gray-500 mb-1">{t('apps.config.search.noKB')}</p>
                  <p className="text-xs text-gray-400">{t('apps.config.search.clickToAddKB')}</p>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {knowledgeBases.slice(0, 1).map(kb => (
                    <div
                      key={kb.id}
                      className="px-3 py-2 border border-gray-200 rounded-xl bg-white hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">📚</div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{kb.name}</p>
                            {kb.desc && <p className="text-xs text-gray-500 truncate">{kb.desc}</p>}
                          </div>
                        </div>
                        <button
                          onClick={() => onRemoveKnowledgeBase(kb.id)}
                          className="p-1 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0"
                          title={t('apps.config.search.removeSelectedKb', 'Remove')}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ConfigSection>
        )}

        {/* Online enhancement keys: both Serper (search) and Jina (fetch) are required */}
        {showWebSearch && (
          <ConfigSection title={t('apps.config.search.onlineProvider')}>
            <div className="space-y-4">
              <ConfigInput
                label={t('apps.config.search.serperApiKey')}
                value={config.serperApiKey ?? ''}
                onChange={v => updateConfig('serperApiKey', v)}
                placeholder={t('apps.config.search.apiKeyPlaceholder')}
                type="password"
                required
              />
              <ConfigInput
                label={t('apps.config.search.jinaApiKey')}
                value={config.jinaApiKey ?? ''}
                onChange={v => updateConfig('jinaApiKey', v)}
                placeholder={t('apps.config.search.apiKeyPlaceholder')}
                type="password"
                required
              />
            </div>
          </ConfigSection>
        )}
      </div>
    )
  }

  // ==================== Research mode (original) ====================
  // 获取状态显示信息
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

  const isAvailable = (status?: string): boolean => {
    return status === 'indexed'
  }

  const showWebSearch = config.searchMode === 'web' || config.searchMode === 'all'
  const showLocalSearch = config.searchMode === 'local' || config.searchMode === 'all'

  const searchModeOptions = [
    { value: 'local' as const, label: t('apps.config.search.local'), desc: t('apps.config.search.localDesc') },
    { value: 'web' as const, label: t('apps.config.search.web'), desc: t('apps.config.search.webDesc') },
    { value: 'all' as const, label: t('apps.config.search.all'), desc: t('apps.config.search.allDesc') },
  ]

  return (
    <div className="space-y-8">
      {/* 搜索方式 */}
      <ConfigSection title={t('apps.config.search.mode')}>
        <div className="flex flex-col gap-2">
          {searchModeOptions.map(option => (
            <button
              key={option.value}
              onClick={() => updateConfig('searchMode', option.value)}
              className={`
                px-4 py-3 ${RADIUS_BUTTON} text-sm font-medium transition-all duration-200 border text-left
                ${
                  config.searchMode === option.value
                    ? 'bg-blue-50 border-blue-200 text-blue-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                }
              `}
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

      {/* 搜索来源 - 统一区块 */}
      <ConfigSection title={t('apps.config.search.source')}>
        {/* 网络搜索引擎 */}
        {showWebSearch && (
          <div className={showLocalSearch ? 'mb-4' : ''}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">🔍</span>
                <span className="text-sm font-medium text-gray-900">{t('apps.config.search.webEngine')}</span>
              </div>
              <button
                onClick={onShowEngineConfig}
                className="px-3 py-1.5 text-sm font-medium bg-blue-50 hover:bg-blue-100 text-blue-700 hover:text-blue-800 rounded-lg border border-blue-200 transition-all duration-200 flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                {t('apps.config.search.configure')}
              </button>
            </div>

            {enginesLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
              </div>
            ) : (
              (() => {
                const selectedEngine = engines.find(e => e.web_search_engine_id === config.selectedWebSearchEngineId)
                if (!config.selectedWebSearchEngineId || !selectedEngine) {
                  return (
                    <div className="p-3 bg-gray-50 rounded-xl text-center">
                      <p className="text-sm text-gray-500 mb-1">{t('apps.config.search.noEngine')}</p>
                      <p className="text-xs text-gray-400">{t('apps.config.search.clickToConfig')}</p>
                    </div>
                  )
                }
                return (
                  <div className="flex flex-col gap-2">
                    <div
                      key={selectedEngine.web_search_engine_id}
                      className="px-3 py-2 border border-gray-200 rounded-xl bg-white hover:border-gray-300 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">
                          🔍
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{selectedEngine.search_engine_name}</p>
                        </div>
                        <Tooltip title={t('apps.config.engine.action.test')} placement="top">
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation()
                              onTestEngine(selectedEngine.web_search_engine_id)
                            }}
                            className="text-gray-700 hover:text-blue-600 hover:bg-blue-50"
                          >
                            <Play className="w-4 h-4" />
                          </IconButton>
                        </Tooltip>
                      </div>
                    </div>
                  </div>
                )
              })()
            )}
          </div>
        )}

        {/* 本地知识库 */}
        {showLocalSearch && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">📚</span>
                <span className="text-sm font-medium text-gray-900">{t('apps.config.search.localKB')}</span>
              </div>
              <button onClick={onShowKnowledgeBaseSelector} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                <Plus className="w-3 h-3" />
                {t('apps.config.search.configure')}
              </button>
            </div>

            {knowledgeBases.length === 0 ? (
              <div className="p-3 bg-gray-50 rounded-xl text-center">
                <p className="text-sm text-gray-500 mb-1">{t('apps.config.search.noKB')}</p>
                <p className="text-xs text-gray-400">{t('apps.config.search.clickToAddKB')}</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {knowledgeBases.map(kb => {
                  const available = isAvailable(kb.status)
                  const statusDisplay = getStatusDisplay(kb.status)
                  return (
                    <div
                      key={kb.id}
                      className={`
                        px-3 py-2 ${RADIUS_BUTTON} border transition-all duration-200
                        ${!available ? 'bg-gray-100 border-gray-200 opacity-70' : 'bg-white border-gray-200 hover:border-gray-300'}
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 flex-shrink-0">📚</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className={`text-sm font-medium truncate ${!available ? 'text-gray-500' : 'text-gray-900'}`}>{kb.name}</p>
                              {kb.status && statusDisplay && (
                                <span className={`px-1.5 py-0.5 text-xs rounded-full flex-shrink-0 ${statusDisplay.color}`}>{statusDisplay.text}</span>
                              )}
                            </div>
                            {kb.desc && <p className={`text-xs truncate ${!available ? 'text-gray-400' : 'text-gray-500'}`}>{kb.desc}</p>}
                          </div>
                        </div>
                        <button
                          onClick={() => onRemoveKnowledgeBase(kb.id)}
                          disabled={!available}
                          className="p-1 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
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
        )}
      </ConfigSection>

      {/* 请求速率控制 - 仅联网搜索模式显示 */}
      {showWebSearch && (
        <ConfigSection title={t('apps.config.search.qpsTitle')}>
          <div className="flex items-center gap-3">
            <QpsInput
              value={config.webSearchMaxQps}
              onChange={value => updateConfig('webSearchMaxQps', value)}
              suffix={t('apps.config.search.qpsInputSuffix')}
              placeholder={t('apps.config.search.qpsInputPlaceholder')}
            />
            <span className="text-xs text-gray-500">{t('apps.config.search.qpsUnlimited')}</span>
          </div>
        </ConfigSection>
      )}
    </div>
  )
}

/**
 * QPS 输入框组件 (research mode only)
 */
const QpsInput: React.FC<{
  value: number
  onChange: (value: number) => void
  placeholder?: string
  suffix?: string
}> = ({ value, onChange, placeholder, suffix }) => {
  const [inputValue, setInputValue] = React.useState('')
  const [isFocused, setIsFocused] = React.useState(false)

  const handleFocus = () => {
    setIsFocused(true)
    if (value === 0) {
      setInputValue('')
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value
    if (v === '') {
      setInputValue('')
      onChange(0)
      return
    }
    if (!/^\d*\.?\d*$/.test(v)) return
    const parsedValue = parseFloat(v)
    if (!isNaN(parsedValue) && parsedValue >= 0) {
      setInputValue(v)
      onChange(parsedValue)
    }
  }

  const handleBlur = () => {
    setIsFocused(false)
    setInputValue('')
  }

  const displayValue = isFocused
    ? (inputValue || (value === 0 ? '' : String(value)))
    : String(value)

  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={displayValue}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={placeholder}
        step="any"
        min="0"
        className="w-28 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-inner-spin-button]:m-auto"
      />
      {suffix && <span className="text-sm text-gray-500">{suffix}</span>}
    </div>
  )
}

export default SearchConfigTab
