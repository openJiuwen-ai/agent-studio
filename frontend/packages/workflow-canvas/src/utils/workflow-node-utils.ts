/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FreeLayoutPluginContext } from '@flowgram.ai/free-layout-editor'
import { WorkflowNodeType } from '../nodes/constants'

/**
 * 递归查找节点，支持嵌套在循环节点内的节点
 * @param blocks - 节点块数组
 * @param targetId - 目标节点ID
 * @returns 找到的节点或 null
 */
export const findNodeRecursively = (blocks: any[], targetId: string): any => {
  const found = blocks.find(node => node.id === targetId)
  if (found) {
    return found
  }

  const shortId = targetId.includes('.') ? targetId.split('.').pop() : targetId
  if (shortId !== targetId) {
    const foundByShortId = blocks.find(node => node.id === shortId)
    if (foundByShortId) {
      return foundByShortId
    }
  }

  for (const block of blocks) {
    if (block.blocks && Array.isArray(block.blocks)) {
      const nestedResult = findNodeRecursively(block.blocks, targetId)
      if (nestedResult) {
        return nestedResult
      }
    }
  }

  return null
}

/**
 * 从标题中提取序号
 * @param title - 节点标题
 * @returns 提取的序号，如果无序号返回 null
 */
export const extractNumberFromTitle = (title: string): number | null => {
  if (!title) return null
  const match = title.match(/(\d+)$/)
  if (match) {
    return parseInt(match[1], 10)
  }
  return null
}

/**
 * 递归查找指定类型的所有节点（包括嵌套在循环节点中的）
 * @param nodes - 节点数组
 * @param targetType - 目标节点类型
 * @returns 匹配的节点数组
 */
export const findNodesByType = (nodes: any[], targetType: string | WorkflowNodeType): any[] => {
  const matchedNodes: any[] = []

  const checkNode = (node: any) => {
    if (node.type === targetType || node.data?.type === targetType) {
      matchedNodes.push(node)
    }

    if (node.children && Array.isArray(node.children)) {
      node.children.forEach(checkNode)
    }

    if (node.blocks && Array.isArray(node.blocks)) {
      node.blocks.forEach(checkNode)
    }

    if (node.data) {
      if (node.data.loopBody) {
        checkNode(node.data.loopBody)
      }
      if (node.data.subNodes && Array.isArray(node.data.subNodes)) {
        node.data.subNodes.forEach(checkNode)
      }
      if (node.data.children && Array.isArray(node.data.children)) {
        node.data.children.forEach(checkNode)
      }
    }
  }

  nodes.forEach(checkNode)
  return matchedNodes
}

/**
 * 生成节点标题，支持序号递增和编号复用
 * @param nodeType - 节点类型
 * @param context - onAdd 钩子上下文
 * @param titlePrefix - 标题前缀
 * @returns 生成的标题
 */
export const generateNodeTitle = (nodeType: string | WorkflowNodeType, context?: FreeLayoutPluginContext, titlePrefix: string = ''): string => {
  try {
    if (context?.document?.toJSON) {
      const canvasData = context.document.toJSON()

      if (canvasData.nodes && Array.isArray(canvasData.nodes)) {
        const existingNodes = findNodesByType(canvasData.nodes, nodeType)

        const usedNumbers = new Set<number>()

        existingNodes.forEach(node => {
          const title = node.data?.title || ''
          if (title.startsWith(titlePrefix)) {
            if (title === titlePrefix) {
              return
            }
            const number = extractNumberFromTitle(title)
            if (number !== null) {
              usedNumbers.add(number)
            }
          }
        })

        let nextNumber = 1
        while (usedNumbers.has(nextNumber)) {
          nextNumber++
        }

        if (existingNodes.length === 0) {
          return titlePrefix
        }

        return `${titlePrefix}_${nextNumber}`
      }
    }
  } catch (error) {}

  return titlePrefix
}
