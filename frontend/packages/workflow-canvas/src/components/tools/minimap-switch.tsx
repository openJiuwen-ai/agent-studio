/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Tooltip, IconButton } from '@douyinfe/semi-ui'
import { UIIconMinimap } from './styles'
import { useTranslation } from '../../i18n'

export const MinimapSwitch = (props: { minimapVisible: boolean; setMinimapVisible: (visible: boolean) => void }) => {
  const { minimapVisible, setMinimapVisible } = props
  const { t } = useTranslation()

  return (
    <Tooltip content={t('workflowCanvas.tools.minimap')}>
      <IconButton
        type="tertiary"
        theme="borderless"
        icon={<UIIconMinimap height={18} width={18} style={{ opacity: minimapVisible ? 1 : 0.7 }} />}
        onClick={() => setMinimapVisible(!minimapVisible)}
      />
    </Tooltip>
  )
}
