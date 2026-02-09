/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import type { TestRunFormMetaItem } from '../testrun-form/type'
import type { InteractionMessage } from '../runtime/types'

/**
 * 解析交互消息为表单元数据
 * @param msg 交互消息
 * @param inputDefaults 从 workflow 节点中提取的默认值
 */
export function parseInteractionMsgToFormMeta(
  msg: InteractionMessage | undefined,
  inputDefaults?: Record<string, unknown>
): TestRunFormMetaItem[] {
  const normalizeType = (t?: string): TestRunFormMetaItem['type'] => {
    const s = String(t || '').toLowerCase()
    if (s.includes('boolean')) return 'boolean'
    if (s.includes('integer')) return 'integer'
    if (s.includes('number')) return 'number'
    if (s.includes('array')) return 'array'
    if (s.includes('object')) return 'object'
    if (s.includes('date-time')) return 'date-time'
    if (s.includes('file')) return 'file'
    return 'string'
  }

  const items: TestRunFormMetaItem[] = []

  if (!msg) return items

  if (Array.isArray(msg)) {
    for (const f of msg) {
      const name = String(f?.input_name || f?.name || f?.label || '').trim()
      if (!name) continue
      // 优先使用从 workflow 节点提取的默认值
      const defaultValue = f?.default ?? inputDefaults?.[name] ?? ''
      items.push({
        name,
        description: String(f?.description || '').trim() || undefined,
        type: normalizeType(f?.type),
        defaultValue,
        required: Boolean(f?.required),
        itemsType: undefined,
      })
    }
    return items
  }

  if (typeof msg === 'string') {
    const name = msg.trim() || 'input'
    const defaultValue = (inputDefaults?.[name] ?? '') as string
    items.push({ name, type: 'string', defaultValue, required: false })
    return items
  }

  if (msg && typeof msg === 'object') {
    const objMsg = msg as any
    // 处理带 outputs 包装的情况：{ outputs: { type, properties, required } }
    let schemaObj = objMsg
    if (objMsg.outputs && typeof objMsg.outputs === 'object') {
      schemaObj = objMsg.outputs
    }

    if (schemaObj.properties && typeof schemaObj.properties === 'object') {
      const requiredArr: string[] = Array.isArray(schemaObj.required) ? schemaObj.required : []
      for (const [name, prop] of Object.entries<any>(schemaObj.properties)) {
        const type = normalizeType(prop?.type)
        const itemsType = prop?.items?.type ? normalizeType(prop.items.type) : undefined
        // 优先使用从 workflow 节点提取的默认值
        const defaultValue = prop?.default ?? inputDefaults?.[name] ?? ''
        items.push({
          name,
          type,
          itemsType,
          defaultValue,
          required: requiredArr.includes(name),
          description: prop?.description,
        })
      }
      return items
    }

    for (const [name, val] of Object.entries<any>(msg)) {
      const type = typeof val === 'string' ? normalizeType(val) : normalizeType(val?.type)
      const defaultValue = (inputDefaults?.[name] ?? '') as string
      items.push({ name, type, defaultValue, required: false })
    }
    return items
  }

  return items
}
