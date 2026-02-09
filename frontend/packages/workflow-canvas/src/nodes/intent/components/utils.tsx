/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../../utils/nanoid-custom'
import { t } from '../../../i18n'

export interface IntentOption {
  name: string
  id: string
  [key: string]: any
}

export const generateIntentId = (): string => {
  return `intent_${customNanoid(8)}`
}

export const normalizeIntents = (value: any): IntentOption[] => {
  if (!Array.isArray(value)) return []

  return value.map((intent, index) => {
    if (typeof intent === 'string' && intent !== null) {
      return { name: intent, id: intent.id || generateIntentId() }
    } else if (intent && typeof intent === 'object') {
      return {
        name: intent.name || '',
        id: intent.id || generateIntentId(),
      }
    } else {
      return { name: '', id: generateIntentId() }
    }
  })
}

export const getIntentLabel = (index: number): string => {
  return t('workflowCanvas.intent.defaultIntentName', { index: index + 1 })
}

export const getIntentPortId = (intent: IntentOption, index: number): string => {
  return intent.id || generateIntentId()
}
