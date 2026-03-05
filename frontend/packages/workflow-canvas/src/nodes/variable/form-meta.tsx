/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useCallback } from 'react'
import { FieldArray, FormMeta, ValidateTrigger } from '@flowgram.ai/free-layout-editor'

import { AssignRows, createInferAssignPlugin, type AssignValueType } from '../../form-materials'
import { FormHeader, FormContent, FormDisplay, FormItem } from '../../form-components'
import { defaultFormMeta } from '../default-form-meta'
import { useIsSidebar, useNodeRenderContext } from '../../hooks'
import { t, useTranslation } from '../../i18n'
import { validation } from './validation'

export const FormRender = (): JSX.Element => {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const { node } = useNodeRenderContext()

  // Filter variables from parent loop container: only allow intermediate variables for left side
  const skipVariable = useCallback(
    (variable: any) => {
      if (!variable?.keyPath || !node?.parent?.id) {
        return false
      }

      // Check if variable is from parent loop's private scope
      const loopLocalsKey = `${node.parent.id}_locals`
      const isFromParentLoop = variable.keyPath[0] === loopLocalsKey

      if (isFromParentLoop) {
        // Get intermediate variable keys from parent loop node's form data
        const intermediateVar = (node.parent as any).form?.getValueIn?.('inputs.loopParam.intermediateVar') || {}
        const intermediateKeys = Object.keys(intermediateVar)
        // variable.keyPath[1] is the variable name inside the loop locals
        const varName = variable.keyPath[1]
        // Only allow variables that are in intermediateVar
        return !intermediateKeys.includes(varName)
      }

      return false
    },
    [node?.parent],
  )

  return (
    <>
      <FormHeader />
      <FormContent>
        {isSidebar ? (
          <FormItem name={t('workflowCanvas.nodes.variable.settings')}>
            <AssignRows name="assign" enableDeclaration={false} skipVariable={skipVariable} />
          </FormItem>
        ) : (
          <>
            <FieldArray name="assign">
              {({ field }) => {
                const getVariableNames = () => {
                  const assignData = field.value as AssignValueType[]
                  if (Array.isArray(assignData) && assignData.length > 0) {
                    const variableNames: string[] = []

                    assignData.forEach(assignItem => {
                      if (
                        assignItem &&
                        assignItem.operator === 'assign' &&
                        assignItem.left &&
                        assignItem.left.type === 'ref' &&
                        Array.isArray(assignItem.left.content) &&
                        assignItem.left.content.length > 1
                      ) {
                        variableNames.push(assignItem.left.content[1])
                      }
                    })

                    return variableNames.length > 0 ? variableNames.join(', ') : t('workflowCanvas.nodes.variable.notConfigured')
                  }

                  return t('workflowCanvas.nodes.variable.notConfigured')
                }

                return <FormDisplay label={t('workflowCanvas.nodes.variable.settings')} content={getVariableNames()} />
              }}
            </FieldArray>
          </>
        )}
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta = {
  render: () => <FormRender />,
  effect: defaultFormMeta.effect,
  plugins: [
    createInferAssignPlugin({
      assignKey: 'assign',
      outputKey: 'outputs',
    }),
  ],
  validateTrigger: ValidateTrigger.onChange,
  validate: validation,
}
