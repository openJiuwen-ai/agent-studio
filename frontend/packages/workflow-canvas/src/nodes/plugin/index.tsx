/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { createRoot } from 'react-dom/client'
import { FlowNodeJSON, FlowNodeRegistry } from '../../typings'
import { WorkflowNodeType } from '../constants'
import { Plug } from 'lucide-react'
import { PluginInfo, PluginApiInfo } from '../../../../api-client/src/types'
import { FreeLayoutPluginContext, WorkflowSelectService } from '@flowgram.ai/free-layout-editor'
import { t } from '../../i18n'
import { IJsonSchema } from '@flowgram.ai/json-schema'

// PluginSelector component
import PluginSelector from '../../components/PluginSelector'
import { dragStateManager } from '../../utils'
import { customNanoid } from '../../utils/nanoid-custom'
import { formMeta as pluginFormMeta } from './form-meta'

// 处理插件节点选择的工具函数
export const handlePluginNodesSelection = (
  nodeType: string,
  results: { id: string; title: string; plugin: PluginInfo }[] | null,
  onNodeSelect: (nodeData: FlowNodeJSON) => void,
) => {
  if (!results || results.length === 0) {
    dragStateManager.closeModal()
    return false
  }

  // 遍历所有选中的插件，为每个插件创建一个节点
  results.forEach(pluginInfo => {
    const nodeJSON = {
      id: `plugin_${customNanoid(5)}`,
      type: nodeType,
      data: {
        title: pluginInfo.title,
        pluginName: pluginInfo.plugin?.name || pluginInfo.title || '',
        pluginId: pluginInfo.id,
        plugin: pluginInfo.plugin, // 保存完整的插件对象
      },
    }

    onNodeSelect(nodeJSON)
  })

  dragStateManager.closeModal()
  return true
}

// 参数类型映射函数 - 返回IJsonSchema格式
const getParameterType = (type: number): IJsonSchema => {
  // 映射到IJsonSchema格式，支持嵌套的数组类型
  const typeToSchemaMap: Record<number, IJsonSchema> = {
    1: { type: 'string' },
    2: { type: 'integer' }, // int
    3: { type: 'number' }, // float
    4: { type: 'boolean' },
    5: { type: 'object' },
    6: { type: 'array', items: { type: 'string' } }, // array_string
    7: { type: 'array', items: { type: 'integer' } }, // array_int
    8: { type: 'array', items: { type: 'number' } }, // array_float
    9: { type: 'array', items: { type: 'boolean' } }, // array_boolean
  }
  return typeToSchemaMap[type] || { type: 'string' }
}

// 格式化插件输入参数
const formatPluginInputs = (toolInfo: PluginApiInfo | null | undefined, plugin: PluginInfo, selectedVersion?: string) => {
  const formattedInputs: Record<string, unknown> = {
    inputParameters: {},
    pluginParam: {
      toolID: toolInfo?.tool_id || '',
      toolName: toolInfo?.name || '',
      pluginID: plugin.plugin_id,
      pluginName: plugin.name || `Plugin ${plugin.plugin_id.slice(-5)}`,
      pluginVersion: selectedVersion || plugin.plugin_version || '',
    },
  }

  // 处理插件级别的运行时参数
  if (plugin.request_params && plugin.request_params.length > 0) {
    plugin.request_params
      .filter(p => p.is_runtime !== false)
      .forEach(param => {
        const paramName = param.name
        const paramType = getParameterType(param.type)

        formattedInputs.inputParameters[paramName] = {
          type: 'constant',
          content: '',
          schema: paramType,
        }
      })
  }

  // 处理工具级别的运行时参数
  if (toolInfo?.request_params && toolInfo.request_params.length > 0) {
    toolInfo.request_params
      .filter(p => p.is_runtime !== false)
      .forEach(param => {
        const paramName = param.name
        const paramType = getParameterType(param.type)

        // 如果工具参数和插件参数同名，工具参数会覆盖插件参数
        formattedInputs.inputParameters[paramName] = {
          type: 'constant',
          content: '',
          schema: paramType,
        }
      })
  }

  return formattedInputs
}

// 格式化插件输出参数，构建 data 字段的内容
const formatPluginOutputData = (toolInfo: PluginApiInfo | null | undefined) => {
  if (!toolInfo || !toolInfo.response_params || toolInfo.response_params.length === 0) {
    return {}
  }

  const dataProperties: Record<string, any> = {}

  toolInfo.response_params.forEach(param => {
    const paramName = param.name
    const paramType = getParameterType(param.type)

    dataProperties[paramName] = {
      ...paramType,
      extra: {
        index: Object.keys(dataProperties).length + 1,
      },
    }
  })

  return dataProperties
}

// 创建插件选择器弹窗
const showPluginSelector = (allowMultiple: boolean = true) => {
  return new Promise<{ id: string; title: string; plugin: PluginInfo; selectedTool?: PluginApiInfo }[] | null>(resolve => {
    try {
      dragStateManager.openModal()

      const container = document.createElement('div')
      document.body.appendChild(container)

      const root = createRoot(container)

      const handleClose = () => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }

        dragStateManager.closeModal()
        resolve(null)
      }

      const handleConfirm = (selectedPlugins: (PluginInfo & { selectedVersion?: string; selectedTools?: PluginApiInfo[] })[]) => {
        try {
          try {
            root.unmount()
            document.body.removeChild(container)
          } catch (e) {
            console.error('清理DOM时出错:', e)
          }

          if (selectedPlugins && selectedPlugins.length > 0) {
            const pluginInfos: Array<{ id: string; title: string; plugin: PluginInfo; selectedTool?: PluginApiInfo; selectedVersion?: string }> = []

            selectedPlugins.forEach(plugin => {
              // 如果插件有选中的工具，为每个选中的工具创建一个节点
              if (plugin.selectedTools && plugin.selectedTools.length > 0) {
                plugin.selectedTools.forEach(tool => {
                  pluginInfos.push({
                    id: `${plugin.plugin_id}_${tool.tool_id}`,
                    title: tool.name || plugin.name || `工具 ${tool.tool_id.slice(-5)}`,
                    plugin: plugin,
                    selectedTool: tool,
                    selectedVersion: plugin.selectedVersion,
                  })
                })
              } else {
                // 如果没有选中工具，创建插件节点（保持原有行为）
                pluginInfos.push({
                  id: plugin.plugin_id,
                  title: plugin.name || `插件 ${plugin.plugin_id.slice(-5)}`,
                  plugin: plugin,
                  selectedVersion: plugin.selectedVersion,
                })
              }
            })

            resolve(pluginInfos)
          } else {
            resolve(null)
          }
        } catch (error) {
          console.error('处理确认选择时出错:', error)

          try {
            root.unmount()
            document.body.removeChild(container)
          } catch (e) {
            console.error('清理DOM时出错:', e)
          }

          resolve(null)
        }
      }

      root.render(
        <div className="plugin-selector-modal" onMouseDown={e => e.stopPropagation()} onMouseUp={e => e.stopPropagation()} onClick={e => e.stopPropagation()}>
          <PluginSelector open={true} onClose={handleClose} onConfirm={handleConfirm} allowDuplicate={allowMultiple} />
        </div>,
      )
    } catch (error) {
      resolve(null)
    }
  })
}

export const PluginNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Plugin,
  meta: {
    label: 'Plugin',
    nodePanelVisible: true,
    defaultPorts: [{ type: 'output' }, { type: 'input' }],
    size: {
      width: 360,
      height: 280,
    },
    singleComponentDebug: true,
  },
  formMeta: pluginFormMeta,
  info: () => ({
    icon: <Plug size={16} className="text-green-600" />,
    description: t('workflowCanvas.nodes.plugin.description'),
  }),
  // 使用异步方法，支持多选插件创建多个节点
  onAdd: async (ctx: FreeLayoutPluginContext) => {
    try {
      // 显示插件选择器并等待用户选择（支持多选）
      const result = await showPluginSelector(true)

      if (!result || result.length === 0) {
        return null
      }

      // 如果选择了多个工具，我们需要手动创建多个节点
      if (result.length > 1) {
        // 为每个选中的工具创建节点，位置稍微错开避免重叠
        result.forEach((toolInfo, index) => {
          const nodeId = `plugin_${customNanoid(5)}`
          const plugin = toolInfo.plugin
          const selectedTool = toolInfo.selectedTool

          // 格式化工具的输入输出参数
          const formattedInputs = formatPluginInputs(selectedTool, plugin, toolInfo.selectedVersion)
          const outputDataProperties = formatPluginOutputData(selectedTool)

          // 计算节点位置，水平排列，每个节点间隔220px，使用固定中心点
          const centerX = 400 // 固定的画布中心X坐标
          const centerY = 300 // 固定的画布中心Y坐标
          const offsetX = index * 220
          const position = { x: centerX + offsetX - 110, y: centerY }

          // 创建节点数据
          const nodeData: FlowNodeJSON = {
            id: nodeId,
            type: WorkflowNodeType.Plugin,
            data: {
              title: selectedTool?.name || plugin.name || 'Plugin',
              pluginName: plugin.name || `Plugin ${plugin.plugin_id.slice(-5)}`,
              inputs: formattedInputs,
              outputs: {
                type: 'object',
                properties: {
                  error_code: {
                    type: 'integer',
                    extra: {
                      index: 1,
                    },
                  },
                  error_message: {
                    type: 'string',
                    extra: {
                      index: 2,
                    },
                  },
                  data: {
                    type: 'object',
                    extra: {
                      index: 3,
                    },
                    properties: outputDataProperties,
                  },
                },
                required: ['error_code', 'error_message', 'data'],
              },
            },
          }

          // 直接创建节点到文档中
          const node = ctx.document.createWorkflowNodeByType(
            WorkflowNodeType.Plugin,
            position,
            nodeData,
            undefined, // containerId, 顶级节点不需要容器
          )

          // 选择最后创建的节点
          if (index === result.length - 1) {
            const selectService = ctx.get(WorkflowSelectService)
            selectService.select(node)
          }
        })

        // 返回null，因为我们已经手动创建了所有节点
        return null
      }

      // 单个工具的情况，按原有逻辑处理
      const nodeId = `plugin_${customNanoid(5)}`
      const plugin = result[0].plugin
      const selectedTool = result[0].selectedTool

      // 格式化工具的输入输出参数
      const formattedInputs = formatPluginInputs(selectedTool, plugin, result[0].selectedVersion)
      const outputDataProperties = formatPluginOutputData(selectedTool)

      return {
        id: nodeId,
        type: WorkflowNodeType.Plugin,
        data: {
          title: selectedTool?.name || plugin.name || 'Plugin',
          pluginName: plugin.name || `Plugin ${plugin.plugin_id.slice(-5)}`,
          inputs: formattedInputs,
          outputs: {
            type: 'object',
            properties: {
              error_code: {
                type: 'integer',
                extra: {
                  index: 1,
                },
              },
              error_message: {
                type: 'string',
                extra: {
                  index: 2,
                },
              },
              data: {
                type: 'object',
                extra: {
                  index: 3,
                },
                properties: outputDataProperties,
              },
            },
            required: ['error_code', 'error_message', 'data'],
          },
        },
      } as FlowNodeJSON
    } catch (error) {
      dragStateManager.reset()
      return null
    }
  },
}
