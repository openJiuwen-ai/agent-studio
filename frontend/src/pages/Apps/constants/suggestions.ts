/**
 * 建议提示词配置
 */

export interface Suggestion {
  id: number
  text: string
  icon: string
}

/**
 * 根据智能体 ID 获取建议提示词
 */
export const getSuggestionsByAgent = (agentId: string, t: (key: string) => string): Suggestion[] => {
  switch (agentId) {
    case 'deepsearch':
      return [
        { id: 1, text: t('apps.suggestions.deepsearch.question1'), icon: '📊' },
        { id: 2, text: t('apps.suggestions.deepsearch.question2'), icon: '🏭' },
      ]
    default:
      return []
  }
}

