/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const ResponseConfig = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.response.format')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.response.responseFormat"
          type="select"
          options={[
            { label: 'Auto-detect', value: 'auto' },
            { label: 'JSON', value: 'json' },
            { label: 'Text', value: 'text' },
            { label: 'Binary', value: 'binary' },
          ]}
        />
      </FormItem>

      <FormItem name={t('workflowCanvas.nodes.httpRequest.response.mode')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.response.responseMode"
          type="select"
          options={[
            { label: 'Full Response', value: 'full' },
            { label: 'On Success Only', value: 'on-success' },
            { label: 'On Error Only', value: 'on-error' },
          ]}
        />
      </FormItem>
    </>
  )
}
