/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormRenderProps, FormMeta } from '@flowgram.ai/free-layout-editor'
import { Square } from 'lucide-react'

import { FlowNodeJSON } from '../../typings'
import { useTranslation } from '../../i18n'

export const renderForm = ({}: FormRenderProps<FlowNodeJSON>) => {
  const { t } = useTranslation()

  return (
    <>
      <div
        style={{
          width: 60,
          height: 60,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Square
          size={32}
          style={{
            color: '#dc2626',
            cursor: 'move',
          }}
        />
        <span
          style={{
            fontSize: '12px',
            fontWeight: 'bold',
            color: '#dc2626',
            marginTop: '4px',
          }}
        >
          {t('workflowCanvas.nodes.blockEnd.title')}
        </span>
      </div>
    </>
  )
}

export const formMeta: FormMeta<FlowNodeJSON> = {
  render: renderForm,
}
