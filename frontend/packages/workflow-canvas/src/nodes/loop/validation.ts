/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { validateFlowValue } from '../../form-materials'
import { FlowNodeEntity } from '@flowgram.ai/free-layout-editor'
import { t } from '../../i18n'

interface LoopValidationContext {
  value?: any
  context: {
    node: FlowNodeEntity
  }
  name?: string
  formValues?: any
}

export const validateLoopNum = ({ value, context, formValues }: LoopValidationContext) => {
  const loopType = formValues?.inputs?.loopParam?.type

  if (loopType !== 'numLoop') {
    return undefined
  }

  const validationResult = validateFlowValue(value, {
    node: context.node,
    required: true,
    includePrivateScope: true,
    errorMessages: {
      required: t('workflowCanvas.nodes.loop.loopCountCannotBeEmpty'),
      unknownVariable: t('workflowCanvas.nodes.loop.loopCountVariableNotFound'),
    },
  })

  if (validationResult) {
    return validationResult.message
  }

  if (value?.type === 'constant') {
    const loopNum = value.content
    if (typeof loopNum === 'number') {
      if (loopNum < 1) {
        return t('workflowCanvas.nodes.loop.loopCountMustBePositive')
      }
      if (loopNum > 1000) {
        return t('workflowCanvas.nodes.loop.loopCountExceedsLimit')
      }
    } else {
      return t('workflowCanvas.nodes.loop.loopCountMustBeNumber')
    }
  }

  return undefined
}

export const validateLoopArray = ({ value, context, name, formValues }: LoopValidationContext) => {
  const loopType = formValues?.inputs?.loopParam?.type

  if (loopType !== 'arrayLoop') {
    return undefined
  }

  if (name === 'inputs.loopParam.loopArray') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return t('workflowCanvas.nodes.loop.loopArrayConfigCannotBeEmpty')
    }

    const arrayKeys = Object.keys(value)
    if (arrayKeys.length === 0) {
      return t('workflowCanvas.nodes.loop.atLeastOneArrayVariable')
    }

    for (const [key] of Object.entries(value)) {
      if (!key || key.trim() === '') {
        return t('workflowCanvas.nodes.loop.arrayVariableNameCannotBeEmpty')
      }
    }
  }

  return undefined
}

export const validateIntermediateVarField = ({ value, context, name, formValues }: LoopValidationContext) => {
  const fieldName = name?.replace(/^inputs\.loopParam\.intermediateVar\./, '') || ''

  const validationResult = validateFlowValue(value, {
    node: context.node,
    required: true,
    includePrivateScope: true,
    errorMessages: {
      required: t('workflowCanvas.nodes.loop.intermediateVarCannotBeEmpty', { field: fieldName }),
      unknownVariable: t('workflowCanvas.nodes.loop.intermediateVarNotFound', { field: fieldName }),
    },
  })

  return validationResult?.message
}

export const validateIntermediateVarDuplicate = ({ value, formValues }: LoopValidationContext) => {
  const loopType = formValues?.inputs?.loopParam?.type

  if (loopType !== 'arrayLoop') {
    return undefined
  }

  const loopArray = formValues?.inputs?.loopParam?.loopArray || {}
  const arrayKeys = Object.keys(loopArray).filter(key => key && key.trim() !== '')

  if (!value || typeof value !== 'object') {
    return undefined
  }

  for (const key of Object.keys(value)) {
    if (key && arrayKeys.includes(key)) {
      return t('workflowCanvas.loop.variableNameDuplicate')
    }
  }

  return undefined
}

export const validateLoopArrayField = ({ value, context, name, formValues }: LoopValidationContext) => {
  const fieldName = name?.replace(/^inputs\.loopParam\.loopArray\./, '') || ''
  const loopType = formValues?.inputs?.loopParam?.type

  if (loopType !== 'arrayLoop') {
    return undefined
  }

  if (!value) {
    return t('workflowCanvas.nodes.loop.arrayVariableValueCannotBeEmpty', { field: fieldName })
  }

  const validationResult = validateFlowValue(value, {
    node: context.node,
    required: true,
    includePrivateScope: true,
    errorMessages: {
      required: t('workflowCanvas.nodes.loop.arrayVariableCannotBeEmpty', { field: fieldName }),
      unknownVariable: t('workflowCanvas.nodes.loop.arrayVariableNotFound', { field: fieldName }),
    },
  })

  if (validationResult) {
    return validationResult.message
  }

  if (value?.type === 'constant') {
    if (!Array.isArray(value.content)) {
      return t('workflowCanvas.nodes.loop.arrayVariableMustBeArray', { field: fieldName })
    }
    if (Array.isArray(value.content) && value.content.length === 0) {
      return t('workflowCanvas.nodes.loop.arrayVariableCannotBeEmptyArray', { field: fieldName })
    }
  }

  return undefined
}

export const validateLoopBlocks = ({ value, context }: LoopValidationContext) => {
  const blocks = context.node?.blocks || []

  if (!blocks || blocks.length === 0) {
    return undefined
  }

  const collectAllLines = (blocks: FlowNodeEntity[]) => {
    const allLines: any[] = []
    blocks.forEach(block => {
      if (block.lines) {
        const { inputLines, outputLines } = block.lines
        if (inputLines && Array.isArray(inputLines)) {
          allLines.push(...inputLines)
        }
        if (outputLines && Array.isArray(outputLines)) {
          allLines.push(...outputLines)
        }
      }
    })
    return allLines
  }

  const lines = collectAllLines(blocks)
  const edges = lines
    .map(line => ({
      sourceNodeID: line.from?.id,
      targetNodeID: line.to?.id,
    }))
    .filter(edge => edge.sourceNodeID && edge.targetNodeID)

  const blockStart = blocks.find(block => block.flowNodeType === '15')
  const blockEnd = blocks.find(block => block.flowNodeType === '16')

  if (!blockStart || !blockEnd) {
    return t('workflowCanvas.nodes.loop.loopBodyMustContainStartAndEnd')
  }

  // continue 和 break 也可以作为有效的结束节点
  const continueNode = blocks.find(block => block.flowNodeType === '12')
  const breakNode = blocks.find(block => block.flowNodeType === '13')
  const validEndNodes = [blockEnd, continueNode, breakNode].filter(Boolean) as FlowNodeEntity[]

  const buildGraph = (nodes: FlowNodeEntity[], edgeList: any[]) => {
    const graph = new Map<string, string[]>()

    nodes.forEach(node => {
      graph.set(node.id, [])
    })

    edgeList.forEach(edge => {
      const neighbors = graph.get(edge.sourceNodeID) || []
      neighbors.push(edge.targetNodeID)
      graph.set(edge.sourceNodeID, neighbors)
    })

    return graph
  }

  const hasPath = (graph: Map<string, string[]>, start: string, end: string): boolean => {
    const visited = new Set<string>()
    const queue = [start]

    while (queue.length > 0) {
      const current = queue.shift()!
      if (current === end) {
        return true
      }

      if (visited.has(current)) {
        continue
      }

      visited.add(current)
      const neighbors = graph.get(current) || []
      queue.push(...neighbors)
    }

    return false
  }

  const graph = buildGraph(blocks, edges)
  // 检查从 blockStart 是否有路径能到达任一有效结束节点
  const hasCompletePath = validEndNodes.some(endNode => hasPath(graph, blockStart.id, endNode.id))

  if (!hasCompletePath) {
    return t('workflowCanvas.nodes.loop.loopBodyMustHaveCompletePath')
  }

  return undefined
}

export const validation = {
  'inputs.loopParam.loopNum': validateLoopNum,
  'inputs.loopParam.loopArray': validateLoopArray,
  'inputs.loopParam.loopArray.*': validateLoopArrayField,
  'inputs.loopParam.intermediateVar': validateIntermediateVarDuplicate,
  'inputs.loopParam.intermediateVar.*': validateIntermediateVarField,
  blocks: validateLoopBlocks,
}
