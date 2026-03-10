/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const BodyConfig = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.body.contentType')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.body.contentType"
          type="select"
          options={[
            { label: 'JSON', value: 'application/json' },
            { label: 'Form', value: 'application/x-www-form-urlencoded' },
            { label: 'Multipart Form', value: 'multipart/form-data' },
            { label: 'Text', value: 'text/plain' },
            { label: 'Binary', value: 'application/octet-stream' },
          ]}
        />
      </FormItem>

      <FormItem name={t('workflowCanvas.nodes.httpRequest.body.content')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.body.content"
          type="textarea"
          placeholder='{"key": "value"}'
        />
      </FormItem>
    </>
  )
}
