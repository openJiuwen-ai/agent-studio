/**
 * InferenceGraph 全局多实例管理器
 *
 * @description
 * 使用 Map 结构管理多个推理图实例的状态和数据
 * 支持多个报告同时存在并独立工作
 *
 * 工作流程：
 * 1. InferenceGraph 组件通过 register(instanceId, messages, openFn) 注册
 * 2. InferenceLink 通过 open(instanceId, index) 打开推理图
 */

import type { InferMessage } from '@/pages/Apps/types'

class InferenceGraphManagerClass {
  /** 多实例存储：instanceId -> { messages, openFn } */
  private instances = new Map<string, {
    messages: InferMessage[]
    openFn: (htmlBase64: string) => void
  }>()

  /**
   * 注册推理图数据和打开方法
   * 由 InferenceGraph 组件调用
   *
   * @param instanceId - 实例唯一标识（通常是 report.id）
   * @param messages - 推理图数据列表
   * @param openFn - 打开推理图的回调函数
   */
  register(instanceId: string, messages: InferMessage[], openFn: (htmlBase64: string) => void) {
    this.instances.set(instanceId, { messages, openFn })
  }

  /**
   * 清空指定实例的注册数据
   * 由 InferenceGraph 组件卸载时调用
   *
   * @param instanceId - 实例唯一标识
   */
  unregister(instanceId: string) {
    this.instances.delete(instanceId)
  }

  /**
   * 打开推理图
   * 由 InferenceLink 组件调用
   *
   * @param instanceId - 实例唯一标识
   * @param index - 推理图 ID
   * @returns 是否成功打开（true 成功，false 失败）
   */
  open(instanceId: string, index: number): boolean {
    const instance = this.instances.get(instanceId)
    if (!instance) {
      console.warn(`[InferenceGraphManager] 实例 ${instanceId} 未注册`)
      return false
    }

    const message = instance.messages.find(m => m.id === index)
    if (message) {
      instance.openFn(message.html_base64)
      return true
    } else {
      const availableIds = instance.messages.map(m => m.id).join(', ')
      console.warn(`[InferenceGraphManager] 实例 ${instanceId} 未找到 index 为 ${index} 的推理图数据。可用 ID: ${availableIds}`)
      return false
    }
  }

  /**
   * 检查实例是否已注册
   *
   * @param instanceId - 实例唯一标识
   * @returns 是否已注册
   */
  isRegistered(instanceId: string): boolean {
    return this.instances.has(instanceId)
  }
}

/** 导出单例 */
export const InferenceGraphManager = new InferenceGraphManagerClass()
