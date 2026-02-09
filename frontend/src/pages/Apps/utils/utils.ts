/**
 * 复制文本到剪贴板
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('复制失败:', error)
    return false
  }
}

/**
 * 本地存储相关工具
 */
export const STORAGE_KEYS = {
  APPS_PAGE_STATE: 'appsPageState',
  // 智能体配置 key 模板，需要传入 spaceId 来生成唯一 key
  AGENT_CONFIGS: (spaceId: string) => `agentConfigs_${spaceId}`,
} as const

/**
 * 获取当前用户的所有智能体配置 localStorage keys
 * 用于清理旧数据
 * @param currentSpaceId 当前用户的 spaceId
 * @returns 匹配的 keys 数组
 */
export const getAgentConfigKeys = (currentSpaceId?: string | null): string[] => {
  const allKeys = Object.keys(localStorage)
  const agentConfigPattern = /^agentConfigs_(.+)$/

  if (currentSpaceId) {
    // 返回除当前用户外的所有其他用户的配置 keys
    return allKeys.filter(key => agentConfigPattern.test(key) && key !== `agentConfigs_${currentSpaceId}`)
  } else {
    // 返回所有智能体配置 keys
    return allKeys.filter(key => agentConfigPattern.test(key))
  }
}

/**
 * 清空所有智能体配置（用于登出时）
 */
export const clearAllAgentConfigs = (): void => {
  const keys = getAgentConfigKeys()
  keys.forEach(key => localStorage.removeItem(key))
}

export const storage = {
  get: <T>(key: string): T | null => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : null
    } catch {
      return null
    }
  },

  set: <T>(key: string, value: T): boolean => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
      return true
    } catch {
      return false
    }
  },

  remove: (key: string): void => {
    localStorage.removeItem(key)
  },
}
