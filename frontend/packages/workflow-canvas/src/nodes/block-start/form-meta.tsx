/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormRenderProps, FormMeta } from '@flowgram.ai/free-layout-editor'
import { PlayCircle } from 'lucide-react'

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
        <PlayCircle
          size={32}
          style={{
            color: '#16a34a',
            cursor: 'move',
          }}
        />
        <span
          style={{
            fontSize: '12px',
            fontWeight: 'bold',
            color: '#16a34a',
            marginTop: '4px',
          }}
        >
          {t('workflowCanvas.nodes.blockStart.title')}
        </span>
      </div>
    </>
  )
}

export const formMeta: FormMeta<FlowNodeJSON> = {
  render: renderForm,
}
