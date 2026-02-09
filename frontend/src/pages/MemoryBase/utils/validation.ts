import { TFunction } from 'i18next'

/**
 * 验证记忆库名称
 * @param name 记忆库名称
 * @param t 翻译函数
 * @param requiredMessageKey 必填项错误消息的翻译key
 * @returns 错误消息，如果没有错误则返回null
 */
export function validateMemoryBaseName(name: string, t: TFunction, requiredMessageKey: string): string | null {
  // 检查是否为空
  if (!name || !name.trim()) {
    return t(requiredMessageKey)
  }

  const trimmedName = name.trim()

  // 检查长度
  if (trimmedName.length > 100) {
    return t('memoryBases.form.nameTooLong', { max: 100 }) || '记忆库名称不能超过100个字符'
  }

  if (trimmedName.length < 1) {
    return t(requiredMessageKey)
  }

  // 检查特殊字符（不允许的字符）
  const invalidChars = /[<>:"/\\|?*\x00-\x1f]/
  if (invalidChars.test(trimmedName)) {
    return t('memoryBases.form.invalidChars') || '记忆库名称不能包含以下字符: < > : " / \\ | ? * 以及控制字符'
  }

  // 检查是否以空格开头或结尾（这个在trim后已经处理，但保留检查）
  if (name !== trimmedName) {
    return t('memoryBases.form.noLeadingTrailingSpaces') || '记忆库名称不能以空格开头或结尾'
  }

  return null
}