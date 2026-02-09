/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { ASTFactory, EffectOptions, FlowNodeRegistry, createEffectFromVariableProvider } from '@flowgram.ai/editor'

import { IFlowRefValue } from '../../'

export const provideBatchInputEffect: EffectOptions[] = createEffectFromVariableProvider({
  private: true,
  parse: (value: IFlowRefValue, ctx) => [
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
        properties: [
          ASTFactory.createProperty({
            key: 'item',
            initializer: ASTFactory.createEnumerateExpression({
              enumerateFor: ASTFactory.createKeyPathExpression({
                keyPath: value.content || [],
              }),
            }),
          }),
          ASTFactory.createProperty({
            key: 'index',
            type: ASTFactory.createNumber(),
          }),
        ],
      }),
    }),
  ],
})
