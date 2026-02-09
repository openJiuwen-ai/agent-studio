/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { ASTFactory, EffectOptions, FlowNodeRegistry, DataEvent, EffectFuncProps } from '@flowgram.ai/editor'
import { JsonSchemaUtils } from '@flowgram.ai/json-schema'
import { IFlowValue, IFlowConstantValue, FlowValueUtils } from '../../form-materials'

const resolveFlowValueType = (flowVal: IFlowValue, scope: any, privateScope: any) => {
  if (!flowVal) {
    return ASTFactory.createString()
  }

  if (flowVal.type === 'constant') {
    const constantVal = flowVal as IFlowConstantValue
    if (constantVal.schema) {
      try {
        return JsonSchemaUtils.schemaToAST(constantVal.schema)
      } catch (error) {
        console.warn('Failed to convert constant schema to AST:', error)
      }
    }
  }

  if (flowVal.type === 'ref' || flowVal.type === 'expression') {
    try {
      let schema = undefined
      if (privateScope) {
        schema = FlowValueUtils.inferJsonSchema(flowVal, privateScope)
      }

      if (!schema && scope) {
        schema = FlowValueUtils.inferJsonSchema(flowVal, scope)
      }

      if (schema) {
        return JsonSchemaUtils.schemaToAST(schema)
      }
    } catch (error) {
      console.warn('Failed to infer type from variable:', error)
    }
  }

  return ASTFactory.createString()
}

const parseLoopEffect = (value: any, ctx: EffectFuncProps['context']) => {
  const loopParam = value || {}
  const loopType = loopParam.type || 'numLoop'
  const loopArray: Record<string, IFlowValue> = loopType === 'arrayLoop' ? loopParam.loopArray || {} : {}
  const intermediateVar: Record<string, IFlowValue> = loopParam.intermediateVar || {}

  const scope = ctx.node.scope
  const privateScope = ctx.node.privateScope

  const arrayProperties =
    loopType === 'arrayLoop'
      ? Object.entries(loopArray).map(([key, flowValue]) => {
          const extractElementType = (schema: any) => {
            if (schema?.type === 'array' && schema.items) {
              try {
                return JsonSchemaUtils.schemaToAST(schema.items)
              } catch (error) {
                console.warn('Failed to convert array element schema to AST:', error)
              }
            }
            return null
          }

          if (flowValue?.type === 'constant') {
            const constantVal = flowValue as IFlowConstantValue
            const elementType = extractElementType(constantVal.schema)
            if (elementType) {
              return ASTFactory.createProperty({
                key,
                type: elementType,
              })
            }
          }

          if (flowValue?.type === 'ref') {
            try {
              let schema = undefined
              if (privateScope) {
                schema = FlowValueUtils.inferJsonSchema(flowValue, privateScope)
              }
              if (!schema && scope) {
                schema = FlowValueUtils.inferJsonSchema(flowValue, scope)
              }
              const elementType = extractElementType(schema)
              if (elementType) {
                return ASTFactory.createProperty({
                  key,
                  type: elementType,
                })
              }
            } catch (error) {
              console.warn('Failed to infer ref array element type:', error)
            }
          }

          return ASTFactory.createProperty({
            key,
            type: resolveFlowValueType(flowValue, scope, privateScope),
          })
        })
      : []

  const intermediateProperties = Object.entries(intermediateVar).map(([key, flowValue]) =>
    ASTFactory.createProperty({
      key,
      type: resolveFlowValueType(flowValue as IFlowValue, scope, privateScope),
    }),
  )

  const properties = [
    ASTFactory.createProperty({
      key: 'index',
      type: ASTFactory.createInteger(),
    }),
    ...intermediateProperties,
  ]

  if (loopType === 'arrayLoop') {
    properties.unshift(
      ASTFactory.createProperty({
        key: 'item',
        initializer: ASTFactory.createEnumerateExpression({
          enumerateFor: ASTFactory.createKeyPathExpression({
            keyPath: [],
          }),
        }),
      }),
      ...arrayProperties,
    )
  }

  return [
    ASTFactory.createVariableDeclaration({
      key: `${ctx.node.id}_locals`,
      meta: {
        title: ctx.node.form?.getValueIn('title'),
        icon: (() => {
          const info = ctx.node.getNodeRegistry<FlowNodeRegistry>().info
          return typeof info === 'function' ? info().icon : info?.icon
        })(),
      },
      type: ASTFactory.createObject({
        properties,
      }),
    }),
  ]
}

export const provideLoopEffect: EffectOptions[] = [
  {
    event: DataEvent.onValueInitOrChange,
    effect: (params: EffectFuncProps) => {
      const { value, context } = params
      setTimeout(() => {
        const variables = parseLoopEffect(value, context)
        variables.forEach(variable => {
          context.node.privateScope?.setVar(variable)
        })
      }, 0)
    },
  },
]

// Export intermediate variables to public scope, merged with outputs
export const exportIntermediateVarsEffect: EffectOptions[] = [
  {
    event: DataEvent.onValueInitOrChange,
    effect: (params: EffectFuncProps) => {
      const { value, context } = params

      const loopParam = value || {}
      const intermediateVar: Record<string, IFlowValue> = loopParam.intermediateVar || {}
      const outputsProperties: Record<string, any> = context.node.form?.getValueIn('outputs.properties') || {}

      const scope = context.node.scope
      const privateScope = context.node.privateScope

      // Build output properties (wrapArray)
      const outputProperties = Object.entries(outputsProperties).map(([key, refValue]) =>
        ASTFactory.createProperty({
          key,
          initializer: ASTFactory.createWrapArrayExpression({
            wrapFor: ASTFactory.createKeyPathExpression({
              keyPath: refValue?.content || [],
            }),
          }),
        }),
      )

      // Build intermediate properties
      const intermediateProperties = Object.entries(intermediateVar).map(([key, flowValue]) =>
        ASTFactory.createProperty({
          key,
          type: resolveFlowValueType(flowValue as IFlowValue, scope, privateScope),
        }),
      )

      // Merge outputs and intermediate vars
      const allProperties = [...outputProperties, ...intermediateProperties]

      if (allProperties.length === 0) {
        return
      }

      // Run after provideBatchOutputsEffect to merge with outputs
      setTimeout(() => {
        const declaration = ASTFactory.createVariableDeclaration({
          key: `${context.node.id}`,
          meta: {
            title: context.node.form?.getValueIn('title'),
            icon: (() => {
              const info = context.node.getNodeRegistry<FlowNodeRegistry>().info
              return typeof info === 'function' ? info().icon : info?.icon
            })(),
          },
          type: ASTFactory.createObject({
            properties: allProperties,
          }),
        })

        context.node.scope?.setVar(declaration)
      }, 10)
    },
  },
]
