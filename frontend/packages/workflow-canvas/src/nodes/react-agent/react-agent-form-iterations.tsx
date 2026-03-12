/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Field } from '@flowgram.ai/free-layout-editor'
import { InputNumber } from '@douyinfe/semi-ui'
import { FormItem } from '../../form-components'
import { useTranslation } from 'react-i18next'

export function ReactAgentFormIterations() {
  const { t } = useTranslation()

  return (
    <Field name="max_iterations" defaultValue={5}>
      {({ field }) => (
        <FormItem
          name={t('workflowCanvas.nodes.reactAgent.maxIterations', 'Max Iterations')}
          vertical
        >
          <InputNumber
            value={field.value}
            onChange={field.onChange}
            min={1}
            max={20}
            step={1}
            style={{ width: '100%' }}
            placeholder={t('workflowCanvas.nodes.reactAgent.maxIterationsPlaceholder', 'Enter max iterations (1-20)')}
          />
        </FormItem>
      )}
    </Field>
  )
}
