/**
 * Config Registry
 * 配置项注册管理系统
 * 支持类型安全的配置标签注册和动态扩展
 */

import React from 'react'

// ==================== 类型定义 ====================

/**
 * 配置标签ID类型
 * 使用字面量类型确保类型安全
 */
export type ConfigTabId = 'general' | 'search' | 'template'

/**
 * 配置标签Props
 * 所有标签组件必须实现的接口
 * 这是一个基础接口，各个标签组件可以扩展额外的 props
 */
export interface ConfigTabProps {
  /** 当前配置值 */
  config: import('../AgentConfigDialog').DeepSearchConfig
  /** 更新配置 */
  updateConfig: <K extends keyof import('../AgentConfigDialog').DeepSearchConfig>(
    key: K,
    value: import('../AgentConfigDialog').DeepSearchConfig[K]
  ) => void
  /** 验证错误列表 */
  errors: string[]
  /** 是否只读 */
  disabled?: boolean
  /** 允许扩展额外的 props */
  [key: string]: any
}

/**
 * 配置标签元数据接口
 */
export interface ConfigTabMeta {
  /** 标签唯一标识 */
  id: ConfigTabId
  /** 显示名称 */
  label: string
  /** 图标组件 */
  icon: React.ReactNode
  /** 描述信息 */
  description?: string
  /** 是否显示徽章 */
  badge?: boolean
  /** 徽章文本 */
  badgeText?: string
  /** 渲染组件 */
  component: React.ComponentType<ConfigTabProps>
  /** 是否启用 */
  enabled?: boolean
  /** 优先级（控制排序，数字越小越靠前） */
  order?: number
}

/**
 * 配置注册表类型
 */
export type ConfigRegistry = Record<ConfigTabId, ConfigTabMeta>

// ==================== 注册管理器 ====================

/**
 * 配置注册管理器类
 * 提供类型安全的配置项注册、查询和管理功能
 */
export class ConfigRegistryManager {
  private registry: ConfigRegistry

  constructor(initialRegistry?: ConfigRegistry) {
    this.registry = initialRegistry ? { ...initialRegistry } : {} as ConfigRegistry
  }

  /**
   * 注册新的配置标签
   * 如果已存在则覆盖，并发出警告
   */
  register(tabMeta: ConfigTabMeta): void {
    if (this.registry[tabMeta.id]) {
      console.warn(`[ConfigRegistry] 配置标签 "${tabMeta.id}" 已存在，将被覆盖`)
    }
    this.registry[tabMeta.id] = tabMeta
  }

  /**
   * 批量注册配置标签
   */
  registerAll(tabMetas: ConfigTabMeta[]): void {
    tabMetas.forEach(meta => this.register(meta))
  }

  /**
   * 取消注册配置标签
   */
  unregister(tabId: ConfigTabId): void {
    delete this.registry[tabId]
  }

  /**
   * 获取所有配置标签（按order排序）
   */
  getAllTabs(): ConfigTabMeta[] {
    return Object.values(this.registry)
      .filter(tab => tab.enabled !== false)
      .sort((a, b) => (a.order || 0) - (b.order || 0))
  }

  /**
   * 根据ID获取配置标签
   */
  getTab(tabId: ConfigTabId): ConfigTabMeta | undefined {
    return this.registry[tabId]
  }

  /**
   * 更新配置标签元数据
   */
  updateTab(tabId: ConfigTabId, updates: Partial<ConfigTabMeta>): void {
    const tab = this.registry[tabId]
    if (tab) {
      this.registry[tabId] = { ...tab, ...updates }
    } else {
      console.warn(`[ConfigRegistry] 配置标签 "${tabId}" 不存在，更新失败`)
    }
  }

  /**
   * 检查配置标签是否存在
   */
  hasTab(tabId: ConfigTabId): boolean {
    return tabId in this.registry
  }

  /**
   * 获取注册表快照
   */
  getSnapshot(): ConfigRegistry {
    return { ...this.registry }
  }
}

export default ConfigRegistryManager
