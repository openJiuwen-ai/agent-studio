/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { commonValidators, createInputParametersValidator, createTitleValidator } from '../../utils/validation'
import { checkPortConnection } from '../../form-materials'
import { t } from '../../i18n'

export const validateTitle = createTitleValidator({ message: t('workflowCanvas.validation.titleRequired') })

export const validateInputParameters = createInputParametersValidator({
  requiredParams: ['query'],
  errorMessages: {
    required: t('workflowCanvas.validation.paramRequired', { param: '{{param}}' }),
    unknownVariable: t('workflowCanvas.validation.variableUnknown'),
  },
})

export const validateIntents = ({ value, context }: any) => {
  if (!value || !Array.isArray(value) || value.length === 0) {
    return t('workflowCanvas.nodes.intent.atLeastOneIntent')
  }

  for (let i = 0; i < value.length; i++) {
    const intent = value[i]
    if (!intent.name || intent.name.trim() === '') {
      return t('workflowCanvas.nodes.intent.intentNameCannotBeEmpty', { index: i + 1 })
    }
    if (intent.name.length > 50) {
      return t('workflowCanvas.nodes.intent.intentNameTooLong', { index: i + 1 })
    }
  }

  const intentPorts = value.map((intent: any) => intent.id)
  const node = context.node

  if (!node) {
    return undefined
  }

  const connectionStatus = intentPorts.map(portId => ({
    portId,
    hasConnection: checkPortConnection(node, portId, 'output'),
  }))

  const unconnectedIntents = connectionStatus.filter(status => !status.hasConnection)

  if (unconnectedIntents.length > 0) {
    const unconnectedIntentNames = value
      .filter((intent: any) => unconnectedIntents.some(status => status.portId === intent.id))
      .map((intent: any) => intent.name)

    if (unconnectedIntentNames.length === 1) {
      return t('workflowCanvas.nodes.intent.intentMustBeConnected', { name: unconnectedIntentNames[0] })
    } else {
      return t('workflowCanvas.nodes.intent.intentsMustBeConnected', { names: unconnectedIntentNames.join(', ') })
    }
  }

  const hasOtherIntentConnection = checkPortConnection(node, '0', 'output')

  if (!hasOtherIntentConnection) {
    return t('workflowCanvas.nodes.intent.otherIntentMustBeConnected')
  }

  return undefined
}

export const validation = {
  'inputs.inputParameters.*': validateInputParameters,
  'inputs.llmParam.model': commonValidators.model,
  'inputs.intents': validateIntents,
}
