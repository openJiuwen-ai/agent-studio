/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useState } from 'react'

import { Typography, Tooltip, Divider } from '@douyinfe/semi-ui'
import { ChevronDown, ChevronRight } from 'lucide-react'

import './index.css'

const { Text } = Typography

interface FormItemProps {
  children: React.ReactNode
  name: string
  required?: boolean
  description?: string
  labelStyle?: React.CSSProperties
  vertical?: boolean
  style?: React.CSSProperties
  defaultCollapsed?: boolean
  customComponent?: React.ReactNode
}

export function FormItem({
  children,
  name,
  required,
  description,
  labelStyle,
  vertical = true,
  style,
  defaultCollapsed = false,
  customComponent,
}: FormItemProps): React.ReactElement {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)
  const renderTitle = useCallback(
    (showTooltip?: boolean) => (
      <div style={{ width: '0', display: 'flex', flex: '1' }}>
        <Text style={{ width: '100%' }} ellipsis={{ showTooltip: !!showTooltip }}>
          {name}
          {required && <span style={{ color: 'var(--semi-color-danger)', paddingLeft: '2px' }}>*</span>}
        </Text>
      </div>
    ),
    [],
  )

  return (
    <div
      style={{
        fontSize: 12,
        marginBottom: 6,
        width: '100%',
        position: 'relative',
        display: 'flex',
        gap: 8,
        ...(vertical
          ? { flexDirection: 'column' }
          : {
              justifyContent: 'center',
              alignItems: 'center',
            }),
        ...style,
      }}
    >
      <Divider />

      {/* 标题行 - 占满整行，依次显示标题、自定义组件和折叠按钮 */}
      <div
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          color: 'var(--semi-color-text-0)',
          position: 'relative',
          cursor: 'pointer',
          ...labelStyle,
        }}
      >
        {/* 标题区域 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flex: 1,
            minWidth: 0,
          }}
        >
          {description ? <Tooltip content={description}>{renderTitle()}</Tooltip> : renderTitle(true)}
        </div>

        {/* 右侧区域 - 包含自定义组件和折叠按钮 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexShrink: 0,
          }}
        >
          {/* 自定义右侧组件 */}
          {customComponent && (
            <div
              onClick={e => e.stopPropagation()}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {customComponent}
            </div>
          )}

          {/* 折叠按钮 */}
          <div
            onClick={e => {
              e.stopPropagation()
              setIsCollapsed(!isCollapsed)
            }}
            style={{
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '4px',
              transition: 'background-color 0.2s',
              flexShrink: 0,
              color: 'var(--workflow-text-secondary)'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.backgroundColor = 'var(--workflow-bg-hover)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      {!isCollapsed && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            width: '100%',
          }}
        >
          {children}
        </div>
      )}
    </div>
  )
}
