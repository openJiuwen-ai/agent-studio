/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { FormItem } from '../../../form-components'
import { InputsValues } from '../../../form-materials'
import { t } from '../../../i18n'

export const HeadersConfig = () => {
  return (
    <FormItem name={t('workflowCanvas.nodes.httpRequest.headersSection.title')}>
      <InputsValues path="inputs.httpRequestParam.headers" />
    </FormItem>
  )
}
