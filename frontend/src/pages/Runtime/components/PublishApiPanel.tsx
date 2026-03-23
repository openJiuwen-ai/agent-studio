import React, { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import Handlebars from 'handlebars'
import { ChevronDown, ChevronRight, Copy } from 'lucide-react'
import TabSwitch from '@/components/Common/TabSwitch'
import type { JsonSchema } from '@/types/jsonSchema'

/** 将扁平 key（如 "query.a" "body.bot_id"）合并为嵌套对象，供 Handlebars 模板使用 */
function buildTemplateData(
  paramValues: Record<string, string>,
  apiUrl?: string
): { data: Record<string, unknown> } {
  const data: Record<string, unknown> = {}
  const query: Record<string, unknown> = {}
  const body: Record<string, unknown> = {}

  const setNested = (obj: Record<string, unknown>, path: string, value: string) => {
    const parts = path.split('.')
    let cur: Record<string, unknown> = obj
    for (let i = 0; i < parts.length - 1; i++) {
      const key = parts[i]
      if (!(key in cur) || typeof cur[key] !== 'object' || cur[key] === null) {
        cur[key] = {}
      }
      cur = cur[key] as Record<string, unknown>
    }
    cur[parts[parts.length - 1]] = value
  }

  Object.entries(paramValues).forEach(([key, value]) => {
    if (!key.includes('.')) return
    const [location, ...pathParts] = key.split('.')
    const path = pathParts.join('.')
    if (location === 'header') {
      if (path === 'token') data.token = value
      else data[path] = value
    } else if (location === 'query') {
      setNested(query, path, value)
    } else if (location === 'body') {
      setNested(body, path, value)
    }
  })

  if (Object.keys(query).length > 0) data.query = query
  if (Object.keys(body).length > 0) {
    data.body = body
    try {
      data.raw_body = JSON.stringify(body, null, 2)
    } catch {
      data.raw_body = ''
    }
  }
  if (apiUrl) {
    data.url = apiUrl
    data.baseUrl = apiUrl
  }
  return { data }
}

/** 调用示例项（与接口 code_example 元素一致） */
export interface CodeExampleItem {
  example_name: string[]
  examples: string[]
  language: string
  title: string
}

/** API 发布数据结构（与接口返回 / DEMO_API_PUBLISH 一致） */
export interface ApiPublishData {
  api_name?: string
  api_desc?: string
  method?: string
  url?: string
  code_example?: CodeExampleItem[]
  /** Header 入参（JSON Schema object） */
  header_params?: JsonSchema
  /** Query 入参（JSON Schema object） */
  query_params?: JsonSchema
  /** Body 入参（JSON Schema object） */
  body_params?: JsonSchema
  /** 返回参数说明（JSON Schema object，支持嵌套） */
  return_params?: JsonSchema
  /** 返回参数区块标题，如「非流式响应」 */
  return_section_title?: string
}

export interface PublishApiPanelProps {
  /** API 发布数据（与接口返回结构一致） */
  data: ApiPublishData
  /** 自定义 class */
  className?: string
}

const DESC_COLLAPSE_LEN = 80

function hasSchemaProperties(schema: JsonSchema | undefined): boolean {
  return !!(schema?.properties && typeof schema.properties === 'object' && Object.keys(schema.properties).length > 0)
}

const PublishApiPanel: React.FC<PublishApiPanelProps> = ({ data, className = '' }) => {
  const { t } = useTranslation()
  const [configTab, setConfigTab] = useState<'config' | 'return'>('config')
  const [paramValues, setParamValues] = useState<Record<string, string>>({})
  const [descExpanded, setDescExpanded] = useState<Record<string, boolean>>({})
  const [requestExpandedPaths, setRequestExpandedPaths] = useState<Record<string, boolean>>({})
  const [returnExpandedPaths, setReturnExpandedPaths] = useState<Record<string, boolean>>({})
  const [returnDescExpanded, setReturnDescExpanded] = useState<Record<string, boolean>>({})
  const [selectedCodeExampleIndex, setSelectedCodeExampleIndex] = useState(0)
  const [selectedExampleIndex, setSelectedExampleIndex] = useState(0)
  const [copySuccess, setCopySuccess] = useState(false)

  const hasRequestConfig = useMemo(
    () =>
      hasSchemaProperties(data.header_params) ||
      hasSchemaProperties(data.query_params) ||
      hasSchemaProperties(data.body_params),
    [data.header_params, data.query_params, data.body_params]
  )
  const returnSectionTitle = data.return_section_title

  const toggleRequestExpanded = (path: string) => {
    setRequestExpandedPaths(prev => ({ ...prev, [path]: !prev[path] }))
  }

  const codeExample = data.code_example ?? []
  const hasCodeExample = codeExample.length > 0
  const currentCodeItem = hasCodeExample ? codeExample[selectedCodeExampleIndex] : null
  const currentExamples = currentCodeItem?.examples ?? []
  const currentExampleNames = currentCodeItem?.example_name ?? []
  const hasSubExamples = currentExamples.length > 1
  const codeTemplate = hasCodeExample
    ? (currentExamples[selectedExampleIndex] ?? currentExamples[0] ?? '')
    : ''

  const templateContext = useMemo(
    () => buildTemplateData(paramValues, data.url),
    [paramValues, data.url]
  )

  const codeContent = useMemo(() => {
    if (!codeTemplate) return ''
    try {
      const template = Handlebars.compile(codeTemplate)
      return template(templateContext)
    } catch {
      return codeTemplate
    }
  }, [codeTemplate, templateContext])

  const handleCopyCode = async () => {
    if (!codeContent) return
    try {
      await navigator.clipboard.writeText(codeContent)
      setCopySuccess(true)
      setTimeout(() => setCopySuccess(false), 1500)
    } catch {
      setCopySuccess(false)
    }
  }

  const getParamValueKey = (location: string, name: string) => `${location}.${name}`
  const getParamValue = (location: string, name: string) =>
    paramValues[getParamValueKey(location, name)] ?? ''
  const setParamValue = (location: string, name: string, value: string) => {
    setParamValues(prev => ({ ...prev, [getParamValueKey(location, name)]: value }))
  }
  const toggleDescExpanded = (key: string) => {
    setDescExpanded(prev => ({ ...prev, [key]: !prev[key] }))
  }

  /** 递归渲染请求参数字段（直接基于 JSON Schema；object 可展开子属性，array 展示 items） */
  const renderRequestParamField = (
    name: string,
    prop: JsonSchema,
    required: boolean,
    location: 'header' | 'query' | 'body',
    path: string,
    showAuthorizeLink: boolean
  ): React.ReactNode => {
    const type = prop?.type ?? 'string'
    const isObject = type === 'object' && hasSchemaProperties(prop)
    const isArray = type === 'array'
    const isPrimitive = !isObject && !isArray
    const descKey = `${location}.${path}.desc`
    const isDescLong = (prop?.description?.length ?? 0) > DESC_COLLAPSE_LEN
    const descExp = descExpanded[descKey]
    const showDesc = !isDescLong || descExp
    const expanded = requestExpandedPaths[path] !== false

    return (
      <div key={path} className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          {isObject && (
            <button
              type="button"
              className="p-0 border-0 bg-transparent cursor-pointer text-gray-500 hover:text-gray-700 shrink-0"
              onClick={() => toggleRequestExpanded(path)}
              aria-label={expanded ? t('runtime.publish.api.collapseAll') : t('runtime.publish.api.expandAll')}
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          )}
          <span className="font-medium text-gray-900 font-mono" style={{ fontSize: 'clamp(0.75rem, 1.4vw, 0.8125rem)' }}>
            {name}
            {required && <span className="text-red-500 ml-0.5">*</span>}
          </span>
          <span
            className="inline-flex px-2 py-0.5 rounded text-gray-500 bg-gray-200/80"
            style={{ fontSize: '0.7rem' }}
          >
            {type}
            {isArray && prop?.items?.type && (
              <span className="ml-0.5 opacity-90">&lt;{prop.items.type}&gt;</span>
            )}
          </span>
        </div>
        {prop?.description && (
          <div className="text-gray-600" style={{ fontSize: 'clamp(0.7rem, 1.3vw, 0.75rem)', lineHeight: 1.5 }}>
            {showDesc ? prop.description : (prop.description?.slice(0, DESC_COLLAPSE_LEN) ?? '') + '...'}
            {isDescLong && (
              <button
                type="button"
                className="text-blue-600 hover:underline ml-1"
                style={{ fontSize: 'inherit' }}
                onClick={() => toggleDescExpanded(descKey)}
              >
                {descExp ? t('runtime.publish.api.collapseAll') : t('runtime.publish.api.expandAll')}
              </button>
            )}
          </div>
        )}
        {prop?.example != null && (
          <p className="text-gray-400" style={{ fontSize: '0.7rem' }}>
            {t('runtime.publish.api.exampleLabel')}: {String(prop.example)}
          </p>
        )}
        {isPrimitive && (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={getParamValue(location, path)}
              onChange={e => setParamValue(location, path, e.target.value)}
              placeholder={t('runtime.publish.api.enterPlaceholder', { name })}
              className="flex-1 min-w-0 px-2.5 py-1.5 border border-gray-200 rounded-md bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              style={{ fontSize: 'clamp(0.75rem, 1.4vw, 0.8125rem)' }}
            />
            {showAuthorizeLink && name === 'token' && (
              <a href="#" className="text-blue-600 hover:underline whitespace-nowrap" style={{ fontSize: 'clamp(0.75rem, 1.4vw, 0.8125rem)' }}>
                {t('runtime.publish.api.authorize')}
              </a>
            )}
          </div>
        )}
        {isObject && expanded && prop?.properties && (
          <div className="pl-4 mt-2 space-y-3 border-l-2 border-gray-200">
            {Object.entries(prop.properties).map(([k, v]) =>
              renderRequestParamField(k, v, prop.required?.includes(k) ?? false, location, `${path}.${k}`, false)
            )}
          </div>
        )}
        {isArray && prop?.items && (prop.items.type === 'object' && prop.items.properties) && (
          <div className="pl-4 mt-2 text-gray-500" style={{ fontSize: '0.7rem' }}>
            <span className="font-medium text-gray-600">{t('runtime.publish.api.itemsSchema') || 'Item schema'}:</span>
            <div className="mt-1 pl-2 border-l border-gray-200 space-y-2">
              {Object.entries(prop.items.properties).map(([k, v]) => (
                <div key={k}>
                  <span className="font-mono text-gray-700">{k}</span>
                  <span className="mx-1 text-gray-400">({v?.type ?? 'string'})</span>
                  {v?.description && <span className="text-gray-500">— {v.description}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderSchemaSection = (
    title: string,
    schema: JsonSchema | undefined,
    location: 'header' | 'query' | 'body',
    showAuthorizeLink?: boolean
  ) => {
    if (!hasSchemaProperties(schema)) return null
    const required = new Set(schema!.required ?? [])
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50/50 overflow-hidden">
        <div className="px-3 py-2 border-b border-gray-200 bg-white">
          <h3 className="font-semibold text-gray-800" style={{ fontSize: 'clamp(0.8125rem, 1.5vw, 0.875rem)' }}>
            {title}
          </h3>
        </div>
        <div className="p-3 space-y-4">
          {Object.entries(schema!.properties!).map(([name, prop]) =>
            renderRequestParamField(name, prop, required.has(name), location, name, showAuthorizeLink ?? false)
          )}
        </div>
      </div>
    )
  }

  const toggleReturnExpanded = (path: string) => {
    setReturnExpandedPaths(prev => ({ ...prev, [path]: !prev[path] }))
  }
  const toggleReturnDescExpanded = (key: string) => {
    setReturnDescExpanded(prev => ({ ...prev, [key]: !prev[key] }))
  }

  /** 直接基于 JSON Schema 递归渲染返回参数字段（object 可展开，array 展示 items） */
  const renderReturnSchemaNode = (
    prop: JsonSchema,
    name: string,
    depth: number,
    path: string
  ): React.ReactNode => {
    const type = prop?.type ?? 'string'
    const isObject = type === 'object' && hasSchemaProperties(prop)
    const isArray = type === 'array'
    const expanded = returnExpandedPaths[path] !== false
    const descKey = `return.${path}.desc`
    const isDescLong = (prop?.description?.length ?? 0) > DESC_COLLAPSE_LEN
    const descExp = returnDescExpanded[descKey]
    const showFullDesc = !isDescLong || descExp

    return (
      <div key={path} className="border-b border-gray-100 last:border-b-0">
        <div
          className="py-2.5 pr-2"
          style={{
            paddingLeft: `${12 + depth * 16}px`,
            fontSize: 'clamp(0.75rem, 1.5vw, 0.8125rem)',
          }}
        >
          <div className="flex flex-wrap items-center gap-2">
            {isObject && (
              <button
                type="button"
                className="p-0 border-0 bg-transparent cursor-pointer text-gray-500 hover:text-gray-700 shrink-0"
                onClick={() => toggleReturnExpanded(path)}
                aria-label={expanded ? t('runtime.publish.api.collapseAll') : t('runtime.publish.api.expandAll')}
              >
                {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>
            )}
            <span className="font-mono text-gray-900 font-medium">{name}</span>
            <span
              className="inline-flex px-2 py-0.5 rounded text-gray-500 bg-gray-200/80 shrink-0"
              style={{ fontSize: '0.7rem' }}
            >
              {type}
              {isArray && prop?.items?.type && (
                <span className="ml-0.5 opacity-90">&lt;{prop.items.type}&gt;</span>
              )}
            </span>
          </div>
          {prop?.description && (
            <div className="mt-1 text-gray-600" style={{ lineHeight: 1.5 }}>
              {showFullDesc ? prop.description : (prop.description?.slice(0, DESC_COLLAPSE_LEN) ?? '') + '...'}
              {isDescLong && (
                <button
                  type="button"
                  className="text-blue-600 hover:underline ml-1"
                  onClick={() => toggleReturnDescExpanded(descKey)}
                >
                  {descExp ? t('runtime.publish.api.collapseAll') : t('runtime.publish.api.expandAll')}
                </button>
              )}
            </div>
          )}
          {prop?.example != null && (
            <p className="mt-0.5 text-gray-400" style={{ fontSize: '0.7rem' }}>
              {t('runtime.publish.api.exampleLabel')}: {String(prop.example)}
            </p>
          )}
          {isArray && prop?.items && (prop.items.type === 'object' && prop.items.properties) && (
            <div className="mt-1.5 pl-2 border-l border-gray-200 text-gray-500" style={{ fontSize: '0.7rem' }}>
              <span className="font-medium text-gray-600">{t('runtime.publish.api.itemsSchema') || 'Item schema'}:</span>
              <div className="mt-0.5 space-y-0.5">
                {Object.entries(prop.items.properties).map(([k, v]) => (
                  <div key={k}>
                    <span className="font-mono text-gray-700">{k}</span>
                    <span className="mx-1 text-gray-400">({v?.type ?? 'string'})</span>
                    {v?.description && <span className="text-gray-500">— {v.description}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        {isObject && expanded && prop?.properties && (
          <div className="bg-gray-50/50">
            {Object.entries(prop.properties).map(([k, v]) =>
              renderReturnSchemaNode(v, k, depth + 1, path ? `${path}.${k}` : k)
            )}
          </div>
        )}
      </div>
    )
  }

  const renderReturnParamsContent = () => {
    if (!hasSchemaProperties(data.return_params)) {
      return (
        <div className="py-6 text-center text-gray-500" style={{ fontSize: 'clamp(0.75rem, 1.5vw, 0.8125rem)' }}>
          -
        </div>
      )
    }
    const schema = data.return_params!
    return (
      <div className="p-3">
        {Object.entries(schema.properties!).map(([name, prop]) =>
          renderReturnSchemaNode(prop, name, 0, name)
        )}
      </div>
    )
  }

  const contentPadding = 'clamp(0.75rem, 2vw, 1.25rem)'
  return (
    <div
      className={`h-full min-h-0 flex flex-col w-full max-w-full overflow-auto ${className}`}
      style={{
        paddingLeft: contentPadding,
        paddingRight: contentPadding,
        paddingBottom: 0,
        paddingTop: 0,
        backgroundImage: "url('/images/chat-bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 flex-1 min-h-full items-stretch">
        {/* 左侧：API 名称、描述、入参、返回参数（与标题栏切换按钮中心对齐，故 6:6） */}
        <div className="lg:col-span-6 flex flex-col gap-4 pt-4 pb-4">
          {/* 第一行：API 名称 */}
          <div>
            <h2
              className="font-semibold text-gray-900 break-words"
              style={{ fontSize: 'clamp(1rem, 2vw, 1.125rem)' }}
            >
              {data.api_name || '-'}
            </h2>
            {(data.method || data.url) && (
              <div
                className="mt-1.5 flex flex-wrap items-center gap-2"
                style={{ fontSize: 'clamp(0.8125rem, 1.5vw, 0.875rem)' }}
              >
                {data.method && (
                  <span
                    className="inline-flex items-center font-semibold uppercase px-2.5 py-1 rounded-full shrink-0"
                    style={{
                      backgroundColor: '#e6ffe6',
                      color: '#28a745',
                    }}
                  >
                    {data.method}
                  </span>
                )}
                {data.url && (
                  <span className="font-mono text-gray-500 break-all">
                    {data.url}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* API 描述 */}
          <div>
            <p
              className="text-gray-700 whitespace-pre-wrap break-words"
              style={{ fontSize: 'clamp(0.8125rem, 1.75vw, 0.875rem)', lineHeight: 1.5 }}
            >
              {data.api_desc || '-'}
            </p>
          </div>

          {/* 请求配置 / 返回参数说明：Tab 切换 */}
          <div>
            <div className="flex justify-center mb-2">
              <TabSwitch
                options={[
                  { value: 'config', label: t('runtime.publish.api.requestConfig') },
                  { value: 'return', label: t('runtime.publish.api.returnParamsDesc') },
                ]}
                value={configTab}
                onChange={v => setConfigTab(v as 'config' | 'return')}
              />
            </div>
            {configTab === 'config' ? (
              <div className="space-y-3">
                {hasRequestConfig ? (
                  <>
                    {renderSchemaSection(t('runtime.publish.api.header'), data.header_params, 'header', true)}
                    {renderSchemaSection(t('runtime.publish.api.queryParams'), data.query_params, 'query')}
                    {renderSchemaSection(t('runtime.publish.api.bodyParams'), data.body_params, 'body')}
                  </>
                ) : (
                  <div className="rounded-lg border border-gray-200 bg-white py-6 text-center text-gray-500" style={{ fontSize: 'clamp(0.75rem, 1.5vw, 0.8125rem)' }}>
                    -
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
                {returnSectionTitle && (
                  <div className="px-3 py-2 border-b border-gray-200 bg-gray-50/80">
                    <h3 className="font-semibold text-gray-800" style={{ fontSize: 'clamp(0.8125rem, 1.5vw, 0.875rem)' }}>
                      {returnSectionTitle}
                    </h3>
                  </div>
                )}
                {renderReturnParamsContent()}
              </div>
            )}
          </div>

        </div>

        {/* 右侧：调用示例 + Shell | Python + 代码区域（左侧竖线分割，与标题栏 Tab 中心对齐） */}
        <div className="lg:col-span-6 pt-4 pb-4 lg:pl-5">
          <div className="flex h-full flex-col gap-3 rounded-xl border border-gray-200 bg-white/95 p-4 shadow-sm">
          {/* 调用示例 标题 */}
          <h2
            className="font-semibold text-gray-900 break-words"
            style={{ fontSize: 'clamp(1rem, 2vw, 1.125rem)' }}
          >
            {t('runtime.publish.api.callExample')}
          </h2>

          {/* 语言切换：按 code_example 的 language 分 tab */}
          <div className="flex flex-col items-center gap-2">
            {hasCodeExample && (
              <div className="flex justify-center">
                <TabSwitch
                  options={codeExample.map((item, i) => ({ value: String(i), label: item.language }))}
                  value={String(selectedCodeExampleIndex)}
                  onChange={v => {
                    setSelectedCodeExampleIndex(Number(v))
                    setSelectedExampleIndex(0)
                  }}
                />
              </div>
            )}
          </div>

          {/* 工具栏 + 代码区域包在同一容器内，避免 gap 造成分割线过粗；不拉伸以免下方出现空边框 */}
          <div className={`flex flex-col shrink-0 ${hasCodeExample ? 'rounded-lg border border-gray-200' : ''}`}>
          {hasCodeExample && (
            <div
              className="flex items-center justify-end gap-2 rounded-t-lg border-b border-gray-600/60 bg-gray-800 px-3 py-2 shrink-0"
              style={{ fontSize: 'clamp(0.75rem, 1.5vw, 0.8125rem)' }}
            >
              {hasSubExamples && (
                <select
                  value={selectedExampleIndex}
                  onChange={e => setSelectedExampleIndex(Number(e.target.value))}
                  className="rounded border border-gray-600 bg-gray-700 text-gray-100 px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-gray-500"
                  aria-label={t('runtime.publish.api.switchExample')}
                >
                  {currentExampleNames.map((name, i) => (
                    <option key={i} value={i}>
                      {name}
                    </option>
                  ))}
                </select>
              )}
              <button
                type="button"
                onClick={handleCopyCode}
                disabled={!codeContent}
                className="flex items-center gap-1.5 rounded border border-gray-600 bg-gray-700 px-2.5 py-1.5 text-gray-100 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-1 focus:ring-gray-500"
                title={t('runtime.publish.api.copy')}
              >
                <Copy className="w-3.5 h-3.5 shrink-0" />
                <span>{copySuccess ? t('runtime.publish.api.copied') : t('runtime.publish.api.copy')}</span>
              </button>
            </div>
          )}

          {/* 调用示例代码区域：相对视窗高度，超出显示滚动条 */}
          <div
            className={`min-h-[40vh] max-h-[70vh] h-[50vh] shrink-0 bg-gray-900 text-gray-100 overflow-auto ${hasCodeExample ? 'rounded-b-lg' : 'rounded-lg border border-gray-200'}`}
            style={{
              padding: 'clamp(0.75rem, 1.5vw, 1rem)',
              fontSize: 'clamp(0.75rem, 1.5vw, 0.8125rem)',
              lineHeight: 1.6,
              fontFamily: 'ui-monospace, monospace',
            }}
          >
            <pre className="m-0 whitespace-pre-wrap break-words">
              <code>{codeContent}</code>
            </pre>
          </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PublishApiPanel
