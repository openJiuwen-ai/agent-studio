/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { FC, useState, useMemo } from 'react'

import { Tooltip, Input } from '@douyinfe/semi-ui'
import { NodePanelRenderProps } from '@flowgram.ai/free-node-panel-plugin'
import { useClientContext, WorkflowNodeEntity, WorkflowPortEntity } from '@flowgram.ai/free-layout-editor'

import { FlowNodeRegistry } from '../../typings'
import { nodeRegistries } from '../../nodes'
import { WorkflowNodeType } from '../../nodes/constants'
import { canContainNode } from '../../utils'
import { NodesContainer, SearchContainer, CategoriesContainer, CategoryTitle, NodesGrid, NodeWrap, NodeLabel } from './styled'
import { useTranslation } from '../../i18n'

// 节点类型枚举键到可搜索名称的映射
const nodeTypeKeyNames: Record<WorkflowNodeType, string> = {
  [WorkflowNodeType.Start]: 'Start',
  [WorkflowNodeType.End]: 'End',
  [WorkflowNodeType.LLM]: 'LLM',
  [WorkflowNodeType.Code]: 'Code',
  [WorkflowNodeType.Condition]: 'Condition',
  [WorkflowNodeType.Loop]: 'Loop',
  [WorkflowNodeType.BlockStart]: 'BlockStart',
  [WorkflowNodeType.BlockEnd]: 'BlockEnd',
  [WorkflowNodeType.Comment]: 'Comment',
  [WorkflowNodeType.VariableMerge]: 'VariableMerge',
  [WorkflowNodeType.Continue]: 'Continue',
  [WorkflowNodeType.Break]: 'Break',
  [WorkflowNodeType.Input]: 'Input',
  [WorkflowNodeType.Output]: 'Output',
  [WorkflowNodeType.Intent]: 'Intent',
  [WorkflowNodeType.Questioner]: 'Questioner',
  [WorkflowNodeType.TextEditor]: 'TextEditor',
  [WorkflowNodeType.Workflow]: 'Workflow',
  [WorkflowNodeType.Variable]: 'Variable',
  [WorkflowNodeType.Plugin]: 'Plugin',
}

// Node type to i18n key mapping
const nodeTypeI18nKeys: Record<WorkflowNodeType, string> = {
  [WorkflowNodeType.Start]: 'workflowCanvas.node.Start',
  [WorkflowNodeType.End]: 'workflowCanvas.node.End',
  [WorkflowNodeType.LLM]: 'workflowCanvas.node.LLM',
  [WorkflowNodeType.Code]: 'workflowCanvas.node.Code',
  [WorkflowNodeType.Condition]: 'workflowCanvas.node.Selector',
  [WorkflowNodeType.Loop]: 'workflowCanvas.node.Loop',
  [WorkflowNodeType.BlockStart]: 'workflowCanvas.node.Start',
  [WorkflowNodeType.BlockEnd]: 'workflowCanvas.node.End',
  [WorkflowNodeType.Comment]: 'workflowCanvas.node.Comment',
  [WorkflowNodeType.VariableMerge]: 'workflowCanvas.node.VariableMerge',
  [WorkflowNodeType.Continue]: 'workflowCanvas.node.Continue',
  [WorkflowNodeType.Break]: 'workflowCanvas.node.Break',
  [WorkflowNodeType.Input]: 'workflowCanvas.node.Input',
  [WorkflowNodeType.Output]: 'workflowCanvas.node.Output',
  [WorkflowNodeType.Intent]: 'workflowCanvas.node.Intent',
  [WorkflowNodeType.Questioner]: 'workflowCanvas.node.Questioner',
  [WorkflowNodeType.TextEditor]: 'workflowCanvas.node.TextEditor',
  [WorkflowNodeType.Workflow]: 'workflowCanvas.node.Workflow',
  [WorkflowNodeType.Variable]: 'workflowCanvas.node.Variable',
  [WorkflowNodeType.Plugin]: 'workflowCanvas.node.Plugin',
}

// Get translated node name (moved to component to use useTranslation hook)

// 节点分类
const nodeCategories = {
  llmAndWorkflow: {
    nameKey: 'workflowCanvas.category.llmAndWorkflow',
    nodes: [WorkflowNodeType.LLM, WorkflowNodeType.Workflow, WorkflowNodeType.Plugin],
  },
  businessLogic: {
    nameKey: 'workflowCanvas.category.businessLogic',
    nodes: [
      WorkflowNodeType.Code,
      WorkflowNodeType.Condition,
      WorkflowNodeType.Loop,
      WorkflowNodeType.Intent,
      WorkflowNodeType.VariableMerge,
      WorkflowNodeType.Variable,
      WorkflowNodeType.Continue,
      WorkflowNodeType.Break,
    ],
  },
  inputOutput: {
    nameKey: 'workflowCanvas.category.inputOutput',
    nodes: [WorkflowNodeType.Input, WorkflowNodeType.Output],
  },
  components: {
    nameKey: 'workflowCanvas.category.components',
    nodes: [WorkflowNodeType.Questioner, WorkflowNodeType.TextEditor],
  },
}

interface NodeProps {
  label: string
  icon: React.ReactElement
  onClick: React.MouseEventHandler<HTMLDivElement>
  disabled: boolean
  description?: string
}

const getTooltipPosition = (index: number): 'left' | 'right' | 'top' => {
  const isInRightColumn = index % 2 === 1
  return isInRightColumn ? 'right' : 'left'
}

function Node(props: NodeProps & { index: number }) {
  const tooltipPosition = getTooltipPosition(props.index)

  return (
    <Tooltip content={props.description} position={tooltipPosition} align="center" getPopupContainer={() => document.body}>
      <NodeWrap disabled={props.disabled} data-testid={`canContainNodenode-list-${props.label}`} onClick={props.disabled ? undefined : props.onClick}>
        <div style={{ fontSize: 16, marginRight: 8 }}>{props.icon}</div>
        <NodeLabel>{props.label}</NodeLabel>
      </NodeWrap>
    </Tooltip>
  )
}

interface NodeListProps {
  onSelect: NodePanelRenderProps['onSelect']
  fromPort?: WorkflowPortEntity // 从哪个端口添加 From which port to add
  containerNode?: WorkflowNodeEntity
  onClose?: () => void // 添加关闭回调
}

export const NodeList: FC<NodeListProps> = props => {
  const { onSelect, containerNode, fromPort, onClose } = props
  const context = useClientContext()
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')

  // Get translated node name
  const getNodeTypeName = (type: WorkflowNodeType): string => {
    const i18nKey = nodeTypeI18nKeys[type]
    return i18nKey ? t(i18nKey) : String(type)
  }

  const handleClick = async (e: React.MouseEvent, registry: FlowNodeRegistry) => {
    // 插件节点和工作流节点需要异步处理
    if (registry.type === WorkflowNodeType.Plugin || registry.type === WorkflowNodeType.Workflow) {
      e.stopPropagation()

      // 打开插件选择器前关闭节点面板
      onClose?.()

      try {
        // 调用onAdd添加节点，等待异步完成
        const result = await registry.onAdd?.(context)
        // 使用工具函数处理节点选择
        if (Array.isArray(result)) {
          // 直接遍历数组处理多节点
          result.forEach(nodeJSON => {
            onSelect({
              nodeType: registry.type as string,
              selectEvent: e,
              nodeJSON,
            })
          })
        } else if (result) {
          // 处理返回单个节点的情况
          onSelect({
            nodeType: registry.type as string,
            selectEvent: e,
            nodeJSON: result,
          })
        }
      } catch (error) {
        console.error('添加节点时出错:', error)
      }
    } else {
      // 其他类型节点使用原来的同步处理
      const json = registry.onAdd?.(context)
      onSelect({
        nodeType: registry.type as string,
        selectEvent: e,
        nodeJSON: json,
      })
    }
  }

  // 改进的模糊搜索算法，返回匹配分数（0-1）
  const fuzzyMatchWithScore = (text: string, query: string): number => {
    if (!query.trim()) return 1

    const textLower = text.toLowerCase()
    const queryLower = query.toLowerCase()
    const textLength = textLower.length
    const queryLength = queryLower.length

    // 精确匹配，返回最高分
    if (textLower.includes(queryLower)) return 1

    let score = 0
    let textIndex = 0
    let consecutiveMatches = 0

    // 计算每个字符的匹配分数
    for (let i = 0; i < queryLength; i++) {
      const char = queryLower[i]
      const foundIndex = textLower.indexOf(char, textIndex)

      if (foundIndex === -1) return 0

      // 计算字符匹配分数
      const charScore = 1 / (foundIndex - textIndex + 1)

      // 连续匹配奖励
      if (foundIndex === textIndex) {
        consecutiveMatches++
        score += charScore * (1 + consecutiveMatches * 0.2)
      } else {
        consecutiveMatches = 0
        score += charScore
      }

      // 首字符匹配额外奖励
      if (i === 0 && foundIndex === 0) {
        score += 0.5
      }

      // 单词开头匹配额外奖励
      if (foundIndex === 0 || textLower[foundIndex - 1] === ' ') {
        score += 0.3
      }

      textIndex = foundIndex + 1
    }

    // 归一化分数，考虑查询长度和文本长度的比例
    const normalizedScore = score / queryLength
    const lengthRatio = queryLength / textLength
    const finalScore = normalizedScore * (1 + lengthRatio * 0.5)

    return Math.min(finalScore, 1)
  }

  // 根据搜索查询和分类过滤节点
  const filteredRegistriesByCategory = useMemo(() => {
    const visibleRegistries = nodeRegistries
      .filter(register => register.meta.nodePanelVisible !== false)
      .filter(register => {
        if (register.meta.onlyInContainer) {
          return register.meta.onlyInContainer === containerNode?.flowNodeType
        }
        /**
         * 循环节点无法嵌套循环节点
         * Loop node cannot nest loop node
         */
        if (containerNode && !canContainNode(register.type, containerNode.flowNodeType)) {
          return false
        }
        return true
      })

    let filtered = visibleRegistries
    if (searchQuery.trim()) {
      filtered = visibleRegistries
        .map(registry => {
          const translatedName = getNodeTypeName(registry.type as WorkflowNodeType)
          const nodeType = String(registry.type)
          const nodeTypeKey = nodeTypeKeyNames[registry.type as WorkflowNodeType] || ''
          const info = typeof registry.info === 'function' ? registry.info() : registry.info
          const description = info?.description || ''

          // 计算各字段的匹配分数
          const nameScore = fuzzyMatchWithScore(translatedName, searchQuery)
          const typeScore = fuzzyMatchWithScore(nodeType, searchQuery)
          const typeKeyScore = fuzzyMatchWithScore(nodeTypeKey, searchQuery)
          const descScore = fuzzyMatchWithScore(description, searchQuery)

          // 取最高分数作为整体匹配分数，权重排序：翻译名称 > 类型键名 > 原始类型 > 描述
          const finalScore = Math.max(
            nameScore * 1.5, // 翻译名称权重最高
            typeKeyScore * 1.4, // 类型键名（如"LLM"）权重次之
            typeScore * 1.2, // 原始类型权重较低
            descScore, // 描述权重最低
          )

          return {
            registry,
            score: finalScore,
          }
        })
        .filter(item => item.score > 0) // 过滤掉不匹配的结果
        .sort((a, b) => b.score - a.score) // 按分数降序排列
        .map(item => item.registry) // 只返回原始 registry 对象
    }

    // 按分类组织节点
    const categorized: Record<string, FlowNodeRegistry[]> = {}

    Object.entries(nodeCategories).forEach(([categoryKey, category]) => {
      categorized[categoryKey] = filtered.filter(registry => category.nodes.includes(registry.type as WorkflowNodeType))
    })

    return categorized
  }, [searchQuery, containerNode, t, getNodeTypeName])

  console.log('>>> fromNode', fromPort?.node)
  return (
    <NodesContainer>
      {/* 搜索框 */}
      <SearchContainer>
        <Input
          placeholder={t('workflowCanvas.nodePanel.searchPlaceholder')}
          value={searchQuery}
          onChange={setSearchQuery}
          style={{ width: '100%', height: '32px' }}
        />
      </SearchContainer>

      <CategoriesContainer>
        {Object.entries(nodeCategories).map(([categoryKey, category]) => {
          const categoryRegistries = filteredRegistriesByCategory[categoryKey]

          // 如果分类中没有节点，不显示该分类
          if (categoryRegistries.length === 0) return null

          return (
            <div key={categoryKey} style={{ marginBottom: '12px' }}>
              {category.nameKey && <CategoryTitle>{t(category.nameKey)}</CategoryTitle>}

              <NodesGrid>
                {categoryRegistries.map((registry, index) => {
                  const info = typeof registry.info === 'function' ? registry.info() : registry.info
                  return (
                    <Node
                      key={`${registry.type}-${index}`}
                      index={index}
                      disabled={!(registry.canAdd?.(context) ?? true)}
                      icon={
                        typeof info?.icon === 'string' ? (
                          <img style={{ width: 20, height: 20, borderRadius: 4 }} src={info.icon} />
                        ) : (
                          <div style={{ width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{info?.icon}</div>
                        )
                      }
                      label={getNodeTypeName(registry.type as WorkflowNodeType)}
                      description={info?.description}
                      onClick={e => handleClick(e, registry)}
                    />
                  )
                })}
              </NodesGrid>
            </div>
          )
        })}
      </CategoriesContainer>
    </NodesContainer>
  )
}
