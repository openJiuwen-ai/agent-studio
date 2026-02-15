/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'
import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const AdvancedConfig = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.advanced.timeout')}>
        <InjectDynamicValueInput
          path="inputs.httpRequestParam.advanced.timeout"
          type="number"
          placeholder="60"
        />
      </FormItem>

      <Field<boolean> name="inputs.httpRequestParam.advanced.retry.enabled">
        {({ field: retryEnabledField }) => (
          <>
            {retryEnabledField.value && (
              <>
                <FormItem name={t('workflowCanvas.nodes.httpRequest.advanced.retry.maxRetries')}>
                  <InjectDynamicValueInput
                    path="inputs.httpRequestParam.advanced.retry.maxRetries"
                    type="number"
                    placeholder="3"
                  />
                </FormItem>

                <FormItem name={t('workflowCanvas.nodes.httpRequest.advanced.retry.backoffType')}>
                  <InjectDynamicValueInput
                    path="inputs.httpRequestParam.advanced.retry.backoffType"
                    type="select"
                    options={[
                      { label: 'Fixed', value: 'fixed' },
                      { label: 'Linear', value: 'linear' },
                      { label: 'Exponential', value: 'exponential' },
                    ]}
                  />
                </FormItem>
              </>
            )}
          </>
        )}
      </Field>

      <Field<boolean> name="inputs.httpRequestParam.advanced.rateLimit.enabled">
        {({ field: rateLimitEnabledField }) => (
          <>
            {rateLimitEnabledField.value && (
              <>
                <FormItem name={t('workflowCanvas.nodes.httpRequest.advanced.rateLimit.requestsPerUnit')}>
                  <InjectDynamicValueInput
                    path="inputs.httpRequestParam.advanced.rateLimit.requestsPerUnit"
                    type="number"
                    placeholder="10"
                  />
                </FormItem>

                <FormItem name={t('workflowCanvas.nodes.httpRequest.advanced.rateLimit.unit')}>
                  <InjectDynamicValueInput
                    path="inputs.httpRequestParam.advanced.rateLimit.unit"
                    type="select"
                    options={[
                      { label: 'Second', value: 'second' },
                      { label: 'Minute', value: 'minute' },
                      { label: 'Hour', value: 'hour' },
                    ]}
                  />
                </FormItem>
              </>
            )}
          </>
        )}
      </Field>
    </>
  )
}
