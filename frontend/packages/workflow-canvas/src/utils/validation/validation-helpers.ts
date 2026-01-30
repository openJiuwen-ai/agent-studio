/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import type { FlowNodeEntity } from '@flowgram.ai/free-layout-editor'
import type { ValidationErrorInfo } from '../../components/validation/types'
import { t } from '../../i18n'

/**
 * Node type to translation key mapping
 */
const NODE_TYPE_I18N_KEYS: Record<string, string> = {
  '1': 'workflowCanvas.node.Start',
  '2': 'workflowCanvas.node.End',
  '3': 'workflowCanvas.node.LLM',
  '4': 'workflowCanvas.node.Selector',
  '5': 'workflowCanvas.node.Loop',
  '6': 'workflowCanvas.node.Intent',
  '7': 'workflowCanvas.node.Questioner',
  '8': 'workflowCanvas.node.Input',
  '9': 'workflowCanvas.node.Output',
  '10': 'workflowCanvas.node.Code',
  '11': 'workflowCanvas.node.TextEditor',
  '12': 'workflowCanvas.node.Continue',
  '13': 'workflowCanvas.node.Break',
  '14': 'workflowCanvas.node.Workflow',
  '15': 'workflowCanvas.node.Start',
  '16': 'workflowCanvas.node.End',
  '17': 'workflowCanvas.node.Variable',
  '18': 'workflowCanvas.node.Variable',
  '19': 'workflowCanvas.node.Plugin',
  '99': 'workflowCanvas.node.Comment',
}

/**
 * Get node display name
 * @param node - Node entity
 * @returns Node display name
 */
export const getNodeDisplayName = (node: FlowNodeEntity): string => {
  if (node?.form?.values?.title) {
    const formData = node.form.values
    if (formData?.title) {
      return formData.title
    }
  }

  const nodeType = node?.type
  const i18nKey = NODE_TYPE_I18N_KEYS[nodeType]

  if (i18nKey) {
    return t(i18nKey)
  }

  return t('workflowCanvas.node.Node')
}

/**
 * 检查节点是否有连接
 * @param node 节点实体
 * @returns 是否有连接
 */
export const hasConnections = (node: FlowNodeEntity): boolean => {
  // 检查输入输出线
  if (node.lines?.inputLines?.length || node.lines?.outputLines?.length) {
    return true
  }

  // 检查可用线
  if (node.lines?.availableLines?.length) {
    return true
  }

  // 检查端口
  if (node.ports?.inputPorts || node.ports?.outputPorts) {
    const ports = [...(node.ports.inputPorts || []), ...(node.ports.outputPorts || [])]
    return ports.some((port: any) => port.availableLines?.length || port.lines?.length)
  }

  return false
}

/**
 * 提取属性名的辅助函数
 * @param name 完整属性名
 * @param pattern 匹配模式
 * @returns 提取后的属性名
 */
export const extractPropertyName = (name: string, pattern: RegExp = /^inputs\.inputParameters\./): string => {
  return name.replace(pattern, '')
}

/**
 * 创建验证错误对象
 * @param nodeId 节点ID
 * @param nodeTitle 节点标题
 * @param error 错误消息
 * @param field 字段路径
 * @param severity 严重程度
 * @returns 验证错误对象
 */
export const createValidationError = (
  nodeId: string,
  nodeTitle: string,
  error: string,
  field?: string,
  severity: 'error' | 'warning' = 'error',
): ValidationErrorInfo => {
  return {
    nodeId,
    nodeTitle,
    error,
    severity,
    field,
  }
}

/**
 * 验证常量值是否为空
 * @param value 值对象
 * @returns 是否为空
 */
export const isConstantValueEmpty = (value: any): boolean => {
  return value?.type === 'constant' && (value?.content === undefined || value?.content === null || value?.content === '')
}

/**
 * 提取模板内容的辅助函数
 * @param value 模板值对象
 * @returns 提取的内容
 */
export const extractTemplateContent = (value?: any): string => {
  return value?.content ?? ''
}

/**
 * 检查输出数量是否符合要求
 * @param outputs 输出配置
 * @param minCount 最小数量
 * @returns 是否符合要求
 */
export const hasMinimumOutputs = (outputs: any, minCount: number): boolean => {
  if (!outputs?.properties) return false
  const outputCount = Object.keys(outputs.properties).length
  return outputCount >= minCount
}
