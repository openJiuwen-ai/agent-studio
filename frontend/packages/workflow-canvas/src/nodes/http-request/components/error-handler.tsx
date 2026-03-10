/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormItem } from '../../../form-components'
import { InjectDynamicValueInput } from '../../../form-materials'
import { t } from '../../../i18n'

export const ErrorHandler = () => {
  return (
    <>
      <FormItem name={t('workflowCanvas.nodes.httpRequest.error.processType')}>
        <InjectDynamicValueInput
          path="data.exceptionConfig.processType"
          type="select"
          options={[
            { label: 'Break', value: 'break' },
            { label: 'Return Content', value: 'return_content' },
            { label: 'Execute Exception Step', value: 'execute_exception_step' },
          ]}
        />
      </FormItem>

      <FormItem name={t('workflowCanvas.nodes.httpRequest.error.timeout')}>
        <InjectDynamicValueInput
          path="data.exceptionConfig.timeoutSeconds"
          type="number"
          placeholder="60"
        />
      </FormItem>
    </>
  )
}
