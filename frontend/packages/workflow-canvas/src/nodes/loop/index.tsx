/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'
import { WorkflowNodeEntity, PositionSchema, FlowNodeTransformData } from '@flowgram.ai/free-layout-editor'

import { FlowNodeRegistry } from '../../typings'
import { RotateCcw } from 'lucide-react'
import { formMeta } from './form-meta'
import { WorkflowNodeType } from '../constants'
import { LoopType } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const LoopNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.Loop,
  info: {
    icon: <RotateCcw size={16} className="text-cyan-600" />,
    description: t('workflowCanvas.nodes.loop.description'),
  },
  meta: {
    /**
     * Mark as subcanvas
     * 子画布标记
     */
    isContainer: true,
    /**
     * The subcanvas default size setting
     * 子画布默认大小设置
     */
    size: {
      width: 424,
      height: 400,
    },
    /**
     * The subcanvas padding setting
     * 子画布 padding 设置
     */
    padding: transform => {
      if (!transform.isContainer) {
        return {
          top: 0,
          bottom: 0,
          left: 0,
          right: 0,
        }
      }
      return {
        top: 160,
        bottom: 80,
        left: 80,
        right: 80,
      }
    },
    /**
     * Controls the node selection status within the subcanvas
     * 控制子画布内的节点选中状态
     */
    selectable(node: WorkflowNodeEntity, mousePos?: PositionSchema): boolean {
      if (!mousePos) {
        return true
      }
      const transform = node.getData<FlowNodeTransformData>(FlowNodeTransformData)
      // 鼠标开始时所在位置不包括当前节点时才可选中
      return !transform.bounds.contains(mousePos.x, mousePos.y)
    },
    wrapperStyle: {
      minWidth: 'unset',
      width: '100%',
    },
    singleComponentDebug: false,
    /**
     * 检查是否允许在容器内添加循环节点
     */
    shouldAllowAddingNode(props: any) {
      const { container } = props
      if (container && container.type === WorkflowNodeType.Loop) {
        // 如果当前容器已经是循环节点，则不允许添加嵌套循环
        return {
          allowed: false,
          reason: t('workflowCanvas.loop.nestedLoopNotAllowed'),
        }
      }
      return { allowed: true }
    },
  },
  onAdd(context?) {
    const nodeId = `loop_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.loop.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.Loop, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.Loop,
      data: {
        title: title,
        inputs: {
          loopParam: {
            type: LoopType.NUM_LOOP,
            loopNum: {
              type: 'constant',
              content: 5,
              schema: {
                type: 'integer',
              },
            },
          },
        },
        outputs: {
          type: 'object',
          properties: {},
        },
      },
      blocks: [
        {
          id: `block_start_${customNanoid(5)}`,
          type: WorkflowNodeType.BlockStart,
          meta: {
            position: {
              x: 32,
              y: -40,
            },
            moveDisable: false,
          },
          data: { title: t('workflowCanvas.block.start') },
        },
        {
          id: `block_end_${customNanoid(5)}`,
          type: WorkflowNodeType.BlockEnd,
          meta: {
            position: {
              x: 192,
              y: -40,
            },

            moveDisable: false,
          },
          data: { title: t('workflowCanvas.block.end') },
        },
      ],
    }
  },
  formMeta,
}
