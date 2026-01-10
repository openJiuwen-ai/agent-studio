import React, { useState, useEffect } from 'react'
import { Typography, Button, IconButton, CircularProgress, MenuItem, Select, SelectChangeEvent, Chip } from '@mui/material'
import { X } from 'lucide-react'
import { PluginService, PluginInfo, PluginApiInfo, PluginApiMethod } from '@test-agentstudio/api-client'
import { getDefaultSpaceId } from '../../../../../src/utils/spaceUtils'
import { dragStateManager } from '../../utils/drag-state-manager'
import { useTranslation } from '../../i18n'

interface PluginSelectorProps {
  open: boolean
  onClose: () => void
  onConfirm: (selectedPlugins: (PluginInfo & { selectedTool?: PluginApiInfo })[]) => void
  initialSelected?: string[]
  /**
   * 是否允许重复添加同一个插件
   * @default false
   */
  allowDuplicate?: boolean
}

interface PluginVersion {
  plugin_version: string
  published_at?: string
  description?: string
}

const PluginSelector: React.FC<PluginSelectorProps> = ({ open, onClose, onConfirm }) => {
  const { t } = useTranslation()
  const [pluginList, setPluginList] = useState<PluginInfo[]>([])
  const [pluginLoading, setPluginLoading] = useState(false)

  // 版本相关状态
  const [pluginVersions, setPluginVersions] = useState<Map<string, PluginVersion[]>>(new Map())
  const [selectedVersions, setSelectedVersions] = useState<Map<string, string>>(new Map())
  const [loadingVersions, setLoadingVersions] = useState<Set<string>>(new Set())

  // 工具相关状态
  const [pluginTools, setPluginTools] = useState<Map<string, PluginApiInfo[]>>(new Map())
  const [loadingTools, setLoadingTools] = useState<Set<string>>(new Set())
  const [selectedTools, setSelectedTools] = useState<Map<string, Set<string>>>(new Map()) // pluginId -> toolIds

  // 通知拖拽状态管理器模态框状态变化
  useEffect(() => {
    if (open) {
      dragStateManager.openModal()
    } else {
      dragStateManager.closeModal()
    }

    return () => {
      if (open) {
        dragStateManager.closeModal()
      }
    }
  }, [open])

  useEffect(() => {
    if (open) {
      loadPlugins()
    }
  }, [open])

  const loadPlugins = async () => {
    setPluginLoading(true)
    try {
      const spaceId = getDefaultSpaceId()
      if (!spaceId) {
        setPluginList([])
        return
      }

      const response = await PluginService.getPluginList({
        space_id: spaceId,
        page: 1,
        size: 100,
      })

      if (response.code === 200 && Array.isArray(response.data?.plugin_infos)) {
        setPluginList(response.data.plugin_infos)
      } else {
        setPluginList([])
      }
    } catch (error) {
      console.error('Failed to load plugins:', error)
      setPluginList([])
    } finally {
      setPluginLoading(false)
    }
  }

  // 加载插件版本列表
  const loadPluginVersions = async (pluginId: string) => {
    const spaceId = getDefaultSpaceId()
    if (!spaceId || loadingVersions.has(pluginId)) {
      return
    }

    setLoadingVersions(prev => new Set(prev).add(pluginId))

    try {
      const response = await PluginService.getPluginPublishList({
        space_id: spaceId,
        plugin_id: pluginId,
      })

      let versions: PluginVersion[] = []

      if (response.code === 200 && Array.isArray(response.data?.plugin_infos)) {
        versions = response.data.plugin_infos.map((publish: any) => ({
          plugin_version: publish.plugin_version,
          published_at: publish.published_at,
          description: publish.description,
        }))
      }

      // 添加 draft 版本到最后
      versions.push({
        plugin_version: 'draft',
        description: t('workflowCanvas.pluginSelector.draftVersion'),
      })

      setPluginVersions(prev => new Map(prev).set(pluginId, versions))

      // 如果还没有选择版本，默认选择最新版本（非draft的第一个版本，或者draft）
      if (!selectedVersions.has(pluginId) && versions.length > 0) {
        const defaultVersion = versions.length > 1 ? versions[0].plugin_version : 'draft'
        setSelectedVersions(prev => new Map(prev).set(pluginId, defaultVersion))

        // 自动加载默认版本的工具列表
        // 确保无论是发布版本还是draft版本，都会调用对应的接口获取工具列表
        setTimeout(() => {
          loadPluginTools(pluginId, defaultVersion)
        }, 100) // 添加小延迟确保状态更新完成
      }
    } catch (error) {
      console.error(`Failed to load versions for plugin ${pluginId}:`, error)
      // 即使加载失败，也添加 draft 版本
      const draftVersions = [
        {
          plugin_version: 'draft',
          description: t('workflowCanvas.pluginSelector.draftVersion'),
        },
      ]

      setPluginVersions(prev => new Map(prev).set(pluginId, draftVersions))

      // 如果还没有选择版本，默认选择draft版本并加载工具列表
      if (!selectedVersions.has(pluginId)) {
        setSelectedVersions(prev => new Map(prev).set(pluginId, 'draft'))

        // 自动加载draft版本的工具列表
        setTimeout(() => {
          loadPluginTools(pluginId, 'draft')
        }, 100) // 添加小延迟确保状态更新完成
      }
    } finally {
      setLoadingVersions(prev => {
        const newSet = new Set(prev)
        newSet.delete(pluginId)
        return newSet
      })
    }
  }

  // 处理版本选择变化
  const handleVersionChange = (pluginId: string, version: string) => {
    setSelectedVersions(prev => new Map(prev).set(pluginId, version))

    // 每次点击具体版本的时候都会调用对应的接口
    // 点插件版本时，都调用一次publish_get，点draft的时候，都调用一次list_api
    loadPluginTools(pluginId, version)
  }

  // 加载插件工具列表
  const loadPluginTools = async (pluginId: string, version: string) => {
    const spaceId = getDefaultSpaceId()
    if (!spaceId) {
      return
    }

    // 每次都重新加载，不使用缓存，确保获取最新数据
    const toolsKey = `${pluginId}-${version}`
    setLoadingTools(prev => new Set(prev).add(toolsKey))

    try {
      let tools: PluginApiInfo[] = []

      if (version === 'draft') {
        // 对于draft版本，需要调用get接口获取最新的插件信息
        try {
          const response = await PluginService.getPlugin({
            space_id: spaceId,
            plugin_id: pluginId,
          })

          if (response.code === 200 && response.data?.plugin_info) {
            const freshPluginInfo = response.data.plugin_info
            // 更新插件列表中的插件信息
            setPluginList(prev => prev.map(plugin => (plugin.plugin_id === pluginId ? freshPluginInfo : plugin)))
            console.log(`Updated plugin info for draft version: ${pluginId}`)
          }
        } catch (error) {
          console.warn(`Failed to load plugin info for ${pluginId}, continuing with tools loading:`, error)
        }

        // 对于draft版本，需要根据插件类型选择不同的API
        const plugin = pluginList.find(p => p.plugin_id === pluginId)

        if (plugin?.plugin_type === 2) {
          // 本地代码插件 (plugin_type = 2)，调用 list_code API
          console.log(`Loading draft code tools for plugin ${pluginId}`)
          const response = await PluginService.getPluginCodeList({
            space_id: spaceId,
            plugin_id: pluginId,
          })

          if (response.code === 200 && Array.isArray(response.data?.code_info)) {
            // 将 PluginCodeInfo[] 转换为 PluginApiInfo[] 格式以保持一致性
            tools = response.data.code_info.map(codeTool => ({
              tool_id: codeTool.tool_id,
              space_id: codeTool.space_id,
              plugin_id: codeTool.plugin_id,
              name: codeTool.name,
              desc: codeTool.desc,
              path: codeTool.tool_id, // 对于本地代码插件，使用tool_id作为path
              method: 1 as PluginApiMethod, // 默认使用GET方法
              plugin_version: codeTool.plugin_version,
              request_params: codeTool.request_params || [],
              response_params: codeTool.response_params || [],
              headers: [],
            }))
            console.log(`Loaded ${tools.length} draft code tools for plugin ${pluginId}`)
          } else {
            console.warn(`No draft code tools found for plugin ${pluginId}, response:`, response)
          }
        } else {
          // URL插件 (plugin_type = 1) 或未知类型，调用原有的 list_tools API
          console.log(`Loading draft URL tools for plugin ${pluginId}`)
          const response = await PluginService.getPluginApiList({
            space_id: spaceId,
            plugin_id: pluginId,
          })

          if (response.code === 200 && Array.isArray(response.data?.api_info)) {
            tools = response.data.api_info
            console.log(`Loaded ${tools.length} draft URL tools for plugin ${pluginId}`)
          } else {
            console.warn(`No draft URL tools found for plugin ${pluginId}, response:`, response)
          }
        }
      } else {
        // publish版本总是调用 publish_get API，从 plugin_info.tools[] 获取工具
        console.log(`Loading published tools for plugin ${pluginId}, version ${version}`)
        const response = await PluginService.getPluginPublish({
          space_id: spaceId,
          plugin_id: pluginId,
          plugin_version: version,
        })

        if (response.code === 200 && response.data?.plugin_info) {
          tools = response.data.plugin_info.tools || []

          // IMPORTANT: 保存插件级别的request_params到plugin对象中
          // 这样publish版本也能像draft版本一样正确显示插件级别参数
          if (response.data.plugin_info.request_params) {
            setPluginList(prev =>
              prev.map(plugin => (plugin.plugin_id === pluginId ? { ...plugin, request_params: response.data.plugin_info.request_params } : plugin)),
            )
            console.log(`Updated plugin ${pluginId} with plugin-level request_params from publish version ${version}`)
          }

          console.log(`Loaded ${tools.length} published tools for plugin ${pluginId}, version ${version}`)
        } else {
          console.warn(`No published tools found for plugin ${pluginId}, version ${version}, response:`, response)
        }
      }

      // 更新工具列表
      setPluginTools(prev => new Map(prev).set(toolsKey, tools))
    } catch (error) {
      console.error(`Failed to load tools for plugin ${pluginId} version ${version}:`, error)
      // 设置空数组表示加载失败
      setPluginTools(prev => new Map(prev).set(toolsKey, []))
    } finally {
      setLoadingTools(prev => {
        const newSet = new Set(prev)
        newSet.delete(toolsKey)
        return newSet
      })
    }
  }

  const handleConfirm = () => {
    // 检查是否选择了工具
    const hasSelectedTools = Array.from(selectedTools.values()).some(toolSet => toolSet.size > 0)

    if (!hasSelectedTools) {
      return
    }

    // 构建选中的插件对象列表（基于选中的工具）
    const selectedPluginObjects: (PluginInfo & { selectedVersion?: string; selectedTools?: PluginApiInfo[] })[] = []

    // 遍历所有选择了工具的插件
    selectedTools.forEach((toolIds, pluginId) => {
      if (toolIds.size > 0) {
        const plugin = pluginList.find(p => p.plugin_id === pluginId)
        const selectedVersion = selectedVersions.get(pluginId) || 'draft'

        if (plugin) {
          const toolsKey = `${pluginId}-${selectedVersion}`
          const allTools = pluginTools.get(toolsKey) || []
          const selectedToolObjects = allTools.filter(tool => toolIds.has(tool.tool_id))

          if (selectedToolObjects.length > 0) {
            selectedPluginObjects.push({
              ...plugin,
              selectedVersion,
              selectedTools: selectedToolObjects,
            })
          }
        }
      }
    })

    if (selectedPluginObjects.length > 0) {
      onConfirm(selectedPluginObjects)
    } else {
      onClose()
    }
  }

  const handleCancel = () => {
    onClose()
  }

  const handleToolSelect = (pluginId: string, tool: PluginApiInfo) => {
    // Prevent selection if tool is disabled
    if (tool.available === false) {
      return
    }

    setSelectedTools(prev => {
      const newMap = new Map(prev)
      const currentTools = newMap.get(pluginId) || new Set()

      if (currentTools.has(tool.tool_id)) {
        // 取消选择工具
        currentTools.delete(tool.tool_id)
        // 如果该插件没有选中的工具，则删除该插件条目
        if (currentTools.size === 0) {
          newMap.delete(pluginId)
        }
      } else {
        // 多选逻辑：添加新选择的工具
        currentTools.add(tool.tool_id)
        newMap.set(pluginId, currentTools)
      }
      return newMap
    })
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <div>
            <Typography variant="h6">{t('workflowCanvas.pluginSelector.selectPluginTools')}</Typography>
            <Typography variant="caption" color="textSecondary">
              {t('workflowCanvas.pluginSelector.supportMultipleSelection')}
            </Typography>
          </div>
          <IconButton onClick={handleCancel}>
            <X />
          </IconButton>
        </div>

        {pluginLoading ? (
          <div className="flex items-center justify-center flex-1">
            <CircularProgress />
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto mb-4">
              {pluginList.length === 0 ? (
                <div className="text-center text-gray-500 py-8">{t('workflowCanvas.pluginSelector.noAvailablePlugins')}</div>
              ) : (
                <div className="space-y-2">
                  {pluginList.map(plugin => {
                    return (
                      <div key={plugin.plugin_id} className="border rounded-lg border-gray-200">
                        <div className="p-3">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <Typography variant="subtitle1" className="font-medium">
                                  {plugin.name || `${t('workflowCanvas.pluginSelector.plugin')} ${plugin.plugin_id.slice(-5)}`}
                                </Typography>
                              </div>
                              <Typography variant="body2" color="textSecondary" className="mt-1">
                                {plugin.desc || t('workflowCanvas.pluginSelector.noDescription')}
                              </Typography>

                              {/* 版本下拉选择器 */}
                              <div className="flex items-center space-x-2 mt-2">
                                <Typography variant="caption" color="textSecondary">
                                  {t('workflowCanvas.pluginSelector.version')}:
                                </Typography>
                                <Select
                                  size="small"
                                  value={selectedVersions.get(plugin.plugin_id) || 'draft'}
                                  onChange={(e: SelectChangeEvent) => {
                                    e.stopPropagation()
                                    handleVersionChange(plugin.plugin_id, e.target.value)
                                  }}
                                  onClick={e => e.stopPropagation()}
                                  onFocus={() => loadPluginVersions(plugin.plugin_id)}
                                  sx={{
                                    minWidth: 120,
                                    fontSize: '0.75rem',
                                    height: 24,
                                  }}
                                  disabled={loadingVersions.has(plugin.plugin_id)}
                                >
                                  {pluginVersions.get(plugin.plugin_id)?.map(version => (
                                    <MenuItem key={version.plugin_version} value={version.plugin_version} sx={{ fontSize: '0.75rem' }}>
                                      {version.plugin_version} {version.plugin_version === 'draft' ? `(${t('workflowCanvas.pluginSelector.draft')})` : ''}
                                    </MenuItem>
                                  )) || [
                                    <MenuItem key="draft" value="draft" sx={{ fontSize: '0.75rem' }}>
                                      {t('workflowCanvas.pluginSelector.selectVersion')}
                                    </MenuItem>,
                                  ]}
                                </Select>
                                {loadingVersions.has(plugin.plugin_id) && <CircularProgress size={16} />}
                              </div>

                              {/* 工具列表显示 */}
                              {(() => {
                                const selectedVersion = selectedVersions.get(plugin.plugin_id) || 'draft'
                                const toolsKey = `${plugin.plugin_id}-${selectedVersion}`
                                return selectedVersion ? (
                                  <div className="mt-3">
                                    <div className="flex items-center space-x-2 mb-2">
                                      <Typography variant="caption" color="textSecondary">
                                        {t('workflowCanvas.pluginSelector.toolList')}:
                                      </Typography>
                                      {loadingTools.has(toolsKey) && <CircularProgress size={12} />}
                                    </div>
                                    {(() => {
                                      const tools = pluginTools.get(toolsKey) || []
                                      if (tools.length > 0) {
                                        return (
                                          <div className="space-y-1">
                                            {tools.map(tool => {
                                              const isSelected = selectedTools.get(plugin.plugin_id)?.has(tool.tool_id)
                                              const isDisabled = tool.available === false
                                              return (
                                                <div
                                                  key={tool.tool_id}
                                                  className={`rounded p-2 text-xs transition-colors ${
                                                    isDisabled
                                                      ? 'bg-gray-100 opacity-60 cursor-not-allowed'
                                                      : isSelected
                                                        ? 'bg-blue-100 border border-blue-300 cursor-pointer'
                                                        : 'bg-gray-50 hover:bg-gray-100 cursor-pointer'
                                                  }`}
                                                  onClick={e => {
                                                    e.stopPropagation()
                                                    handleToolSelect(plugin.plugin_id, tool)
                                                  }}
                                                >
                                                  <div className="flex items-center justify-between">
                                                    <Typography variant="caption" className={`font-medium ${isDisabled ? 'text-gray-500' : ''}`}>
                                                      {tool.name || tool.tool_id}
                                                    </Typography>
                                                    <div className="flex items-center space-x-1">
                                                      <Chip
                                                        label={
                                                          tool.available === true
                                                            ? t('plugins.pluginConfig.enabled', '启用')
                                                            : t('plugins.pluginConfig.disabled', '禁用')
                                                        }
                                                        size="small"
                                                        color={tool.available === true ? 'success' : 'default'}
                                                        sx={{ height: 18, fontSize: '0.65rem', '& .MuiChip-label': { px: 0.5 } }}
                                                      />
                                                      {isSelected && <span className="bg-blue-500 text-white text-xs px-1 py-0.5 rounded">✓</span>}
                                                    </div>
                                                  </div>
                                                  {tool.desc && (
                                                    <Typography
                                                      variant="caption"
                                                      color="textSecondary"
                                                      className={`mt-1 block ${isDisabled ? 'text-gray-400' : ''}`}
                                                    >
                                                      {tool.desc}
                                                    </Typography>
                                                  )}
                                                </div>
                                              )
                                            })}
                                          </div>
                                        )
                                      } else {
                                        return loadingTools.has(toolsKey) ? (
                                          <Typography variant="caption" color="textSecondary">
                                            {t('workflowCanvas.pluginSelector.loadingTools')}
                                          </Typography>
                                        ) : (
                                          <Typography variant="caption" color="textSecondary">
                                            {t('workflowCanvas.pluginSelector.noTools')}
                                          </Typography>
                                        )
                                      }
                                    })()}
                                  </div>
                                ) : null
                              })()}
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-2">
              <Button variant="outlined" onClick={handleCancel}>
                {t('workflowCanvas.pluginSelector.cancel')}
              </Button>
              <Button variant="contained" onClick={handleConfirm} disabled={Array.from(selectedTools.values()).every(toolSet => toolSet.size === 0)}>
                {t('workflowCanvas.pluginSelector.confirm')}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PluginSelector
