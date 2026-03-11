/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/* eslint-disable no-console */
import { useMemo, useRef } from 'react'

import { debounce } from 'lodash-es'
import { createPanelManagerPlugin } from '@flowgram.ai/panel-manager-plugin'
import { createMinimapPlugin } from '@flowgram.ai/minimap-plugin'
import { createFreeSnapPlugin } from '@flowgram.ai/free-snap-plugin'
import { createFreeNodePanelPlugin } from '@flowgram.ai/free-node-panel-plugin'
import { createFreeLinesPlugin } from '@flowgram.ai/free-lines-plugin'
import { FlowNodeBaseType, FreeLayoutProps, WorkflowNodeLinesData } from '@flowgram.ai/free-layout-editor'
import { createContainerNodePlugin } from '@flowgram.ai/free-container-plugin'
import { createTypePresetPlugin } from '../form-materials'

import { testRunPanelFactory } from '../components/testrun/testrun-panel'
import { testDebugPanelFactory } from '../components/testrun/testdebug'
import { nodeFormPanelFactory } from '../components/sidebar'
import { nodeValidationErrorPanelFactory } from '../components/validation'
import { canContainNode, onDragLineEnd } from '../utils'
import { FlowNodeRegistry, FlowDocumentJSON } from '../typings'
import { shortcuts } from '../shortcuts'
import { CustomService } from '../services'
import { createContextMenuPlugin } from '../plugins'
import { defaultFormMeta } from '../nodes/default-form-meta'
import { WorkflowNodeType } from '../nodes'
import { SelectorBoxPopover } from '../components/selector-box-popover'
import { BaseNode, CommentRender, LineAddButton, NodePanel } from '../components'
import { useWorkflowStore } from '../stores/useWorkflowStore'

export function useEditorProps(
  initialData: FlowDocumentJSON | null,
  nodeRegistries: FlowNodeRegistry[],
  onSaveWorkflow?: (workflowData: any) => Promise<void>,
): FreeLayoutProps {
  // 用于跟踪是否已经执行过初始自动布局
  const hasInitialLayoutRef = useRef(false)
  // 用于跟踪是否处于初始化阶段，避免初始化时触发自动保存
  const isInitializingRef = useRef(true)
  // 从 store 订阅只读状态，统一驱动画布只读
  const panelReadonly = useWorkflowStore(s => s.panelReadonly)

  return useMemo<FreeLayoutProps>(
    () => ({
      /**
       * Whether to enable the background
       */
      background: false,
      /**
       * 画布相关配置
       * Canvas-related configurations
       */
      playground: {
        /**
         * Prevent Mac browser gestures from turning pages
         * 阻止 mac 浏览器手势翻页
         */
        preventGlobalGesture: true,
      },
      /**
       * Whether it is read-only or not, the node cannot be dragged in read-only mode
       */
      readonly: panelReadonly,
      /**
       * Initial data
       * 初始化数据
       */
      initialData: initialData || undefined,
      /**
       * Node registries
       * 节点注册
       */
      nodeRegistries,
      /**
       * Get the default node registry, which will be merged with the 'nodeRegistries'
       * 提供默认的节点注册，这个会和 nodeRegistries 做合并
       */
      getNodeDefaultRegistry(type) {
        return {
          type,
          meta: {
            expandable: false,
            defaultExpanded: true,
          },
          formMeta: defaultFormMeta,
        }
      },
      /**
       * 节点数据转换, 由 ctx.document.fromJSON 调用
       * Node data transformation, called by ctx.document.fromJSON
       * @param node
       * @param json
       */
      fromNodeJSON(_node, json) {
        return json
      },
      /**
       * 节点数据转换, 由 ctx.document.toJSON 调用
       * Node data transformation, called by ctx.document.toJSON
       * @param node
       * @param json
       */
      toNodeJSON(node, json) {
        // 检查是否是variableMerge节点
        if (node.type === '18' && json.data?.inputs?.variableMerge) {
          const variableMerge = json.data.inputs.variableMerge
          const inputParameters = json.data.inputs.inputParameters || {}

          // 为每个分组生成对应的input名称
          const updatedVariableMerge = variableMerge.map((group: any, groupIndex: number) => {
            // 找到该分组对应的input名称
            const groupInputs = Object.keys(inputParameters).filter(inputName => inputParameters[inputName].extra?.index === groupIndex)

            return {
              ...group,
              items: groupInputs,
            }
          })

          // 更新json中的variableMerge
          json.data.inputs.variableMerge = updatedVariableMerge
        }
        return json
      },
      lineColor: {
        hidden: 'var(--g-workflow-line-color-hidden,transparent)',
        default: 'var(--g-workflow-line-color-default,#4d53e8)',
        drawing: 'var(--g-workflow-line-color-drawing, #5DD6E3)',
        hovered: 'var(--g-workflow-line-color-hover,#37d0ff)',
        selected: 'var(--g-workflow-line-color-selected,#37d0ff)',
        error: 'var(--g-workflow-line-color-error,red)',
        flowing: 'var(--g-workflow-line-color-flowing,#4d53e8)',
      },
      /*
       * Check whether the line can be added
       * 判断是否连线
       */
      canAddLine(_ctx, fromPort, toPort) {
        // Cannot be a self-loop on the same node / 不能是同一节点自循环
        if (fromPort.node === toPort.node) {
          return false
        }
        // TODO: move to node's validate
        // output port cannot be connected to multiple lines
        // if (fromPort.availableLines.length >= 1) {
        //   return false;
        // }
        // Cannot be in different containers - 不能在不同容器
        if (
          fromPort.node.parent?.id !== toPort.node.parent?.id &&
          ![fromPort.node.parent?.flowNodeType, toPort.node.parent?.flowNodeType].includes(FlowNodeBaseType.GROUP)
        ) {
          return false
        }
        /** Allow circular connections for condition nodes (type '4')
        * This enables condition nodes to connect back to previous nodes in the workflow
        */
        if (fromPort.node.flowNodeType === '4') { // Condition node type
          return true
        }
        /**
         * 线条环检测，不允许连接到前面的节点
         * Line loop detection, which is not allowed to connect to the node in front of it
         */
        return !fromPort.node.getData(WorkflowNodeLinesData).allInputNodes.includes(toPort.node)
      },
      /**
       * Check whether the line can be deleted, this triggers on the default shortcut `Bakspace` or `Delete`
       * 判断是否能删除连线, 这个会在默认快捷键 (Backspace or Delete) 触发
       */
      canDeleteLine(_ctx, _line, _newLineInfo, _silent) {
        return true
      },
      /**
       * Check whether the node can be deleted, this triggers on the default shortcut `Bakspace` or `Delete`
       * 判断是否能删除节点, 这个会在默认快捷键 (Backspace or Delete) 触发
       */
      canDeleteNode(_ctx, _node) {
        return true
      },
      /**
       * 是否允许拖入子画布 (loop or group)
       * Whether to allow dragging into the sub-canvas (loop or group)
       */
      canDropToNode: (ctx, params) => canContainNode(params.dragNodeType!, params.dropNodeType!),
      /**
       * Drag the end of the line to create an add panel (feature optional)
       * 拖拽线条结束需要创建一个添加面板 （功能可选）
       * 希望提供控制线条粗细的配置项
       */
      onDragLineEnd,
      /**
       * SelectBox config
       */
      selectBox: {
        SelectorBoxPopover,
      },
      scroll: {
        /**
         * Whether to restrict the node from rolling out of the canvas needs to be closed because there is a running results pane
         * 是否限制节点不能滚出画布，由于有运行结果面板，所以需要关闭
         */
        enableScrollLimit: false,
      },
      materials: {
        components: {},
        /**
         * Render Node
         */
        renderDefaultNode: BaseNode,
        renderNodes: {
          [WorkflowNodeType.Comment]: CommentRender as any,
        },
      },
      /**
       * Node engine enable, you can configure formMeta in the FlowNodeRegistry
       */
      nodeEngine: {
        enable: true,
      },
      /**
       * Variable engine enable
       */
      variableEngine: {
        enable: true,
      },
      /**
       * Redo/Undo enable
       */
      history: {
        enable: true,
        enableChangeNode: true, // Listen Node engine data change
      },
      /**
       * Content change
       */
      onContentChange: debounce(async (ctx, event) => {
        // 跳过初始化阶段的变更，避免不必要的自动保存
        if (isInitializingRef.current || ctx.document.disposed) return

        // 当正在查看历史版本（非 draft）时，禁止自动保存（从 store 读取选中版本）
        const viewingVersion = useWorkflowStore.getState().selectedVersion
        if (viewingVersion && viewingVersion !== 'draft') {
          console.log('Skip auto save: viewing history version ->', viewingVersion)
          return
        }

        const workflowData = ctx.document.toJSON()
        console.log('Auto Save: ', event, workflowData)

        // Call the real save interface if provided
        if (onSaveWorkflow) {
          try {
            await onSaveWorkflow(workflowData)
            console.log('Auto save completed successfully')
          } catch (error) {
            console.error('Auto save failed:', error)
          }
        }
      }, 500),
      /**
       * Running line
       */
      //   isFlowingLine: (ctx, line) => ctx.get(WorkflowRuntimeService).isFlowingLine(line),
      /**
       * Shortcuts
       */
      shortcuts,
      /**
       * Bind custom service
       */
      onBind: ({ bind }) => {
        bind(CustomService).toSelf().inSingletonScope()
      },
      /**
       * Playground init
       */
      onInit(_ctx) {
        console.log('--- Playground init ---')
      },
      /**
       * Playground render
       */
      onAllLayersRendered(ctx) {
        // 只在第一次渲染时执行自动布局
        if (!hasInitialLayoutRef.current) {
          ctx.tools.autoLayout() // init auto layout
          ctx.tools.fitView(true) // fit view with padding to ensure nodes are visible
          // Set default zoom to 80% so all nodes are fully visible
          ctx.playground.config.updateZoom(0.8)
          // Ensure the viewport is positioned correctly to show all nodes
          setTimeout(() => {
            ctx.tools.fitView(true)
            // 延迟启用自动保存，确保初始化完成
            setTimeout(() => {
              isInitializingRef.current = false
              console.log('--- Auto save enabled ---')
            }, 2000) // 额外延迟2秒确保所有初始化操作完成
          }, 100)
          hasInitialLayoutRef.current = true
          console.log('--- Playground rendered (initial layout) ---')
        } else {
          console.log('--- Playground rendered (skip layout) ---')
        }
      },
      /**
       * Playground dispose
       */
      onDispose() {
        console.log('---- Playground Dispose ----')
      },
      plugins: () => [
        /**
         * Line render plugin
         * 连线渲染插件
         */
        createFreeLinesPlugin({
          renderInsideLine: LineAddButton,
        }),
        /**
         * Minimap plugin
         * 缩略图插件
         */
        createMinimapPlugin({
          disableLayer: true,
          canvasStyle: {
            canvasWidth: 182,
            canvasHeight: 102,
            canvasPadding: 50,
            canvasBackground: 'rgba(242, 243, 245, 1)',
            canvasBorderRadius: 10,
            viewportBackground: 'rgba(255, 255, 255, 1)',
            viewportBorderRadius: 4,
            viewportBorderColor: 'rgba(6, 7, 9, 0.10)',
            viewportBorderWidth: 1,
            viewportBorderDashLength: undefined,
            nodeColor: 'rgba(0, 0, 0, 0.10)',
            nodeBorderRadius: 2,
            nodeBorderWidth: 0.145,
            nodeBorderColor: 'rgba(6, 7, 9, 0.10)',
            overlayColor: 'rgba(255, 255, 255, 0.55)',
          },
        }),

        /**
         * Snap plugin
         * 自动对齐及辅助线插件
         */
        createFreeSnapPlugin({
          edgeColor: '#00B2B2',
          alignColor: '#00B2B2',
          edgeLineWidth: 1,
          alignLineWidth: 1,
          alignCrossWidth: 8,
        }),
        /**
         * NodeAddPanel render plugin
         * 节点添加面板渲染插件
         */
        createFreeNodePanelPlugin({
          renderer: NodePanel,
        }),
        /**
         * This is used for the rendering of the loop node sub-canvas
         * 这个用于 loop 节点子画布的渲染
         */
        createContainerNodePlugin({}),
        /**
         * ContextMenu plugin
         */
        createContextMenuPlugin({}),
        /** Float layout plugin */
        createPanelManagerPlugin({
          factories: [nodeFormPanelFactory, testRunPanelFactory, testDebugPanelFactory, nodeValidationErrorPanelFactory],
        }),
        /**
         * Type preset plugin
         */
        createTypePresetPlugin({ unregisterTypes: ['map'] }),
      ],
    }),
    [initialData, nodeRegistries, onSaveWorkflow, panelReadonly],
  )
}
