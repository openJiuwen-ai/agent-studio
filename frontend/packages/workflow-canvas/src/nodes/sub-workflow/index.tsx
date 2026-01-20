/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { createRoot } from 'react-dom/client'
import { FlowNodeJSON, FlowNodeRegistry } from '../../typings'
import { WorkflowNodeType } from '../constants'
import { GitFork } from 'lucide-react'
import { FreeLayoutPluginContext } from '@flowgram.ai/free-layout-editor'

import WorkflowSelector from '../../components/WorkflowSelector'
import { formMeta } from './form-meta'
import { dragStateManager } from '../../utils/drag-state-manager'
import { customNanoid } from '../../utils/nanoid-custom'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import WorkflowService from '../../../../api-client/src/services/workflowService'
import { t } from '../../i18n'

export const handleWorkflowNodesSelection = (
  nodeType: string,
  results: { id: string; title: string; workflow?: any }[] | null,
  onNodeSelect: (nodeData: any) => void,
) => {
  if (!results || results.length === 0) {
    // Notify drag state manager that modal is closing
    dragStateManager.closeModal()
    return false
  }

  // 遍历所有选中的工作流，为每个工作流创建一个节点
  results.forEach(workflowInfo => {
    const nodeJSON = {
      id: `workflow_${customNanoid(5)}`,
      type: nodeType,
      data: {
        title: workflowInfo.title,
        workflowId: workflowInfo.id,
      },
    }

    // 调用回调函数添加节点
    onNodeSelect(nodeJSON)
  })

  // Notify drag state manager that modal is closing
  dragStateManager.closeModal()

  return true
}

// 依据子工作流画布 Start 节点的 schema 构建
const formatInputParametersFromStartSchema = (startSchema: any) => {
  const build = (schema: any): Record<string, any> => {
    const properties = schema?.properties || {}
    const keys = Object.keys(properties)
    const result: Record<string, any> = {}
    keys.forEach((name, index) => {
      const propSchema = properties[name] || { type: 'string' }
      if (propSchema?.type === 'object' && propSchema?.properties) {
        result[name] = build(propSchema)
      } else {
        result[name] = {
          type: 'constant',
          content: '',
          schema: propSchema,
          extra: { index: index + 1 },
        }
      }
    })
    return result
  }

  return build(startSchema)
}

export const canvasDetailCache = new Map<string, any>()

// 依据子工作流画布 End 节点的 inputParameters 推断
const getCanvasDetail = async (workflowId: string, spaceId: string, version?: string) => {
  const cacheKey = `${workflowId}-${spaceId}-${version || 'draft'}`

  if (canvasDetailCache.has(cacheKey)) {
    return canvasDetailCache.get(cacheKey)
  }

  const requestParams: any = { workflow_id: workflowId, space_id: spaceId }
  if (version && version !== 'draft') {
    requestParams.version = version
  }

  const canvas = await WorkflowService.getWorkflowCanvas(requestParams)
  const wfDetail = canvas?.data?.workflow || {}
  const fullSchema = wfDetail?.schema ? JSON.parse(wfDetail.schema) : {}
  const nodesList = Array.isArray(fullSchema?.nodes) ? fullSchema.nodes : []
  const result = { wfDetail, fullSchema, nodesList }

  canvasDetailCache.set(cacheKey, result)

  return result
}

const extractStartSchema = (nodesList: any[]) => {
  const startNode = nodesList.find((n: any) => String(n?.type) === '1')
  return startNode?.data?.outputs
}

export const buildOutputsSchemaFromNodes = (nodesList: any[]) => {
  const inputParams = nodesList.find((n: any) => String(n?.type) === '2')?.data?.inputs?.inputParameters || {}
  const outputsMap: Record<string, any> = {}
  nodesList.forEach((n: any) => {
    if (n?.data?.outputs) outputsMap[n.id] = n.data.outputs
  })

  const props: Record<string, any> = {}
  let idx = 2 // Start from index 2 since responseContent is index 1
  Object.keys(inputParams || {}).forEach(key => {
    const v = inputParams[key]
    let fieldSchema: any = { type: 'string' }
    if (v?.type === 'constant' && v?.schema) {
      fieldSchema = v.schema
    } else if (v?.type === 'ref' && Array.isArray(v?.content) && v.content.length >= 2) {
      const [refNodeId, refField] = v.content
      const refSchema = outputsMap[refNodeId]
      let refFieldSchema = refSchema?.properties?.[refField]

      if (!refFieldSchema && refField === 'output' && refSchema?.properties?.output?.type === 'object') {
        refFieldSchema = refSchema.properties.output
      }
      if (refFieldSchema && refFieldSchema.type === 'object' && refFieldSchema.properties) {
        if (key === 'result' && Object.keys(refFieldSchema.properties).length === 1) {
          const nestedKey = Object.keys(refFieldSchema.properties)[0]
          const nestedSchema = refFieldSchema.properties[nestedKey]
          props[key] = { ...nestedSchema, extra: { index: idx++ } }
          return
        }
      }

      if (refFieldSchema) {
        fieldSchema = refFieldSchema
      }
    }
    props[key] = { ...fieldSchema, extra: { index: idx++ } }
  })

  return {
    type: 'object',
    properties: {
      responseContent: { type: 'string', extra: { index: 1 } },
      output: {
        type: 'object',
        extra: {
          index: 2,
        },
        properties: props,
        required: Object.keys(props),
      },
    },
    required: ['responseContent', 'output'],
  }
}

const buildNodeForWorkflow = async (workflow: { id: string; title: string; workflow?: any }, spaceId: string) => {
  const nodeId = `workflow_${customNanoid(5)}`
  const selectedVersion = workflow.workflow?.version || 'draft'

  const { wfDetail, nodesList } = await getCanvasDetail(workflow.id, spaceId, selectedVersion)
  const startSchema = extractStartSchema(nodesList)
  const outputsSchema = buildOutputsSchemaFromNodes(nodesList)
  const inputParameters = startSchema ? formatInputParametersFromStartSchema(startSchema) : {}
  return {
    id: nodeId,
    type: WorkflowNodeType.Workflow,
    data: {
      title: workflow.title,
      configs: {
        subWorkflow: {
          workflowId: workflow.id,
          workflowVersion: selectedVersion,
          startSchema,
        },
      },
      inputs: {
        inputParameters,
      },
      outputs: outputsSchema || {
        type: 'object',
        properties: {
          output: {
            type: 'object',
            extra: {
              index: 1,
            },
            properties: {},
            required: [],
          },
        },
        required: ['output'],
      },
    },
  }
}

const showWorkflowSelector = (allowMultiple: boolean = true, excludeWorkflowId?: string) => {
  return new Promise<{ id: string; title: string; workflow: any }[] | null>(resolve => {
    try {
      // Notify drag state manager that modal is opening
      dragStateManager.openModal()

      // 创建一个容器元素
      const container = document.createElement('div')
      document.body.appendChild(container)

      const root = createRoot(container)

      // 关闭弹窗的函数
      const handleClose = () => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }

        // Notify drag state manager that modal is closing
        dragStateManager.closeModal()

        // 用户点击关闭按钮，明确返回null表示取消操作
        resolve(null)
      }

      // 确认选择的函数 - 现在接收完整的工作流对象数组
      const handleConfirm = (selectedWorkflows: any[]) => {
        try {
          // 清理DOM - 无论是否选择了工作流，都需要清理DOM
          try {
            root.unmount()
            document.body.removeChild(container)
          } catch (e) {
            console.error('清理DOM时出错:', e)
          }

          // 只有当选择了工作流时才返回结果
          if (selectedWorkflows && selectedWorkflows.length > 0) {
            // 将每个选中的工作流对象转换为需要的格式
            const workflowInfos = selectedWorkflows.map(workflow => ({
              id: workflow.workflow_id,
              title: workflow.name || `工作流 ${workflow.workflow_id.slice(-5)}`, // 使用工作流名称或ID的最后5位作为标题
              workflow: workflow, // 保存完整的工作流对象
            }))

            resolve(workflowInfos)
          } else {
            // 如果没有选择工作流，明确返回null
            resolve(null)
          }
        } catch (error) {
          console.error('处理确认选择时出错:', error)

          // 确保DOM被清理
          try {
            root.unmount()
            document.body.removeChild(container)
          } catch (e) {
            console.error('清理DOM时出错:', e)
          }

          resolve(null)
        }
      }

      // 渲染WorkflowSelector组件 - 添加焦点管理
      root.render(
        <div
          className="workflow-selector-modal"
          onMouseDown={e => e.preventDefault()} // 防止鼠标事件冒泡到画布
          onMouseUp={e => e.preventDefault()} // 防止鼠标事件冒泡到画布
          onClick={e => e.preventDefault()} // 防止点击事件冒泡到画布
        >
          <WorkflowSelector
            open={true}
            onClose={handleClose}
            onConfirm={handleConfirm}
            initialSelected={[]}
            allowDuplicate={allowMultiple}
            excludeWorkflowId={excludeWorkflowId}
          />
        </div>,
      )
    } catch (error) {
      console.error('Error showing workflow selector:', error)
      resolve(null)
    }
  })
}

export const WorkflowNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Workflow,
  meta: {
    label: '工作流',
    nodePanelVisible: true,
    defaultPorts: [{ type: 'output' }, { type: 'input' }],
    size: {
      width: 360,
      height: 211,
    },
    singleComponentDebug: true,
  },
  info: {
    icon: <GitFork size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.subWorkflow.description'),
  },
  formMeta,
  // 使用异步方法，支持多选工作流创建多个节点
  onAdd: async (ctx: FreeLayoutPluginContext) => {
    try {
      // 检查是否处于拖拽状态（通过连线创建节点）
      const dragState = dragStateManager.getDragState()
      const isViaConnection = dragState.isDragActive

      // 如果是通过连线创建，只允许单选；否则允许多选
      const allowMultiple = !isViaConnection

      // 获取当前编辑的workflow_id
      const workflowId = window.location.pathname.split('/').pop()

      // 显示工作流选择器并等待用户选择
      const result = await showWorkflowSelector(allowMultiple, workflowId)

      // 如果用户取消了工作流选择，返回null
      if (!result) {
        return null
      }

      // 如果用户选择了多个工作流，返回数组（仅在允许多选时）
      if (result.length > 1 && allowMultiple) {
        const spaceId = getDefaultSpaceId() || ''
        const nodes = await Promise.all(result.map(workflow => buildNodeForWorkflow(workflow, spaceId)))
        return nodes
      }

      // 用户选择了工作流，返回单个对象（无论是单选还是强制单选模式）
      // 生成一个稳定的节点ID
      const nodeId = `workflow_${customNanoid(5)}`
      const spaceId = getDefaultSpaceId() || ''
      return (await buildNodeForWorkflow(result[0], spaceId)) as FlowNodeJSON
    } catch (error) {
      console.error('选择工作流时出错:', error)
      // 确保在出错时也重置拖拽状态
      dragStateManager.reset()
      return null
    }
  },
}
