/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'
import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const AuthConfig = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.type')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.auth.authType"
          type="select"
          options={[
            { label: 'None', value: 'none' },
            { label: 'Basic Auth', value: 'basic' },
            { label: 'Bearer Token', value: 'bearer' },
            { label: 'API Key', value: 'api_key' },
          ]}
        />
      </FormItem>

      <Field<string> name="inputs.httpRequestParam.auth.authType">
        {({ field }) => {
          const authType = field.value

          return (
            <>
              {authType === 'basic' && (
                <>
                  <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.username')}>
                    <InjectDynamicValueInput
                      path="inputs.httpRequestParam.auth.username"
                      placeholder="username"
                    />
                  </FormItem>
                  <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.password')}>
                    <InjectDynamicValueInput
                      path="inputs.httpRequestParam.auth.password"
                      type="password"
                      placeholder="password"
                    />
                  </FormItem>
                </>
              )}

              {authType === 'bearer' && (
                <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.token')}>
                  <InjectDynamicValueInput
                    path="inputs.httpRequestParam.auth.token"
                    placeholder="Bearer token"
                  />
                </FormItem>
              )}

              {authType === 'api_key' && (
                <>
                  <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.apiKey')}>
                    <InjectDynamicValueInput
                      path="inputs.httpRequestParam.auth.apiKey"
                      placeholder="API Key"
                    />
                  </FormItem>
                  <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.location')}>
                    <InjectDynamicValueInput
                      path="inputs.httpRequestParam.auth.apiKeyLocation"
                      type="select"
                      options={[
                        { label: 'Header', value: 'header' },
                        { label: 'Query Parameter', value: 'query' },
                        { label: 'Body', value: 'body' },
                      ]}
                    />
                  </FormItem>
                  <FormItem name={t('workflowCanvas.nodes.httpRequest.auth.paramName')}>
                    <InjectDynamicValueInput
                      path="inputs.httpRequestParam.auth.apiKeyParamName"
                      placeholder="X-API-Key"
                    />
                  </FormItem>
                </>
              )}
            </>
          )
        }}
      </Field>
    </>
  )
}
