/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const UrlConfig = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.url.label')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.url"
          placeholder="https://api.example.com/endpoint"
        />
      </FormItem>

      <FormItem name={t('workflowCanvas.nodes.httpRequest.method.label')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.method"
          type="select"
          options={[
            { label: 'GET', value: 'GET' },
            { label: 'POST', value: 'POST' },
            { label: 'PUT', value: 'PUT' },
            { label: 'DELETE', value: 'DELETE' },
            { label: 'PATCH', value: 'PATCH' },
            { label: 'HEAD', value: 'HEAD' },
            { label: 'OPTIONS', value: 'OPTIONS' },
          ]}
        />
      </FormItem>
    </>
  )
}
