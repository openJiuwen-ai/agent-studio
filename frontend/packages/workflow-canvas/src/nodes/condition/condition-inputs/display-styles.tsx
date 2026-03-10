/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import styled from 'styled-components'

// 条件卡片容器（非sidebar模式）
export const ConditionCardContainer = styled.div`
  position: relative;
  margin-bottom: 8px;
  background: transparent;
  border-radius: 6px;
`

// 条件卡片标签
export const ConditionCardLabel = styled.div`
  font-size: 13px;
  color: var(--workflow-text-primary);
  font-weight: 500;
  margin-bottom: 4px;
  padding: 4px 8px;
  background: var(--workflow-bg-input);
  border-radius: 4px;
  border: 1px solid var(--workflow-border-input);
`

// 条件内容容器
export const ConditionContentContainer = styled.div`
  padding: 8px;
  background: var(--workflow-bg-surface);
  border: 1px solid var(--workflow-border-input);
  border-radius: 4px;
  min-height: 32px;
  margin-bottom: 4px;

  &.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--workflow-text-tertiary);
    font-size: 12px;
    min-height: 32px;
  }
`

// 单个条件显示
export const ConditionItem = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--workflow-text-secondary);
  line-height: 1.4;

  &:last-child {
    margin-bottom: 0;
  }
`

// 条件标签（半标签样式）
export const ConditionTag = styled.div`
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  background: var(--workflow-bg-surface);
  border: 1px solid var(--workflow-border-input);
  border-radius: 4px;
  font-size: 12px;
  color: var(--workflow-text-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`

// 逻辑操作符显示
export const LogicOperator = styled.div`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 20px;
  background: var(--workflow-bg-input);
  border: 1px solid var(--workflow-border-input);
  border-radius: 3px;
  font-size: 12px;
  color: var(--workflow-text-secondary);
  margin: 0 4px;
  font-weight: 500;
`

// 端口容器
export const PortContainer = styled.div<{ top?: number; style?: React.CSSProperties }>`
  position: absolute;
  right: -12px;
  top: ${props => props.top || 0}px;
  z-index: 10;
  ${props => props.style && { ...props.style }}
`

// 分割线
export const Divider = styled.div`
  height: 1px;
  background: var(--workflow-border-input);
  margin: 4px 0;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 16px;
    right: 16px;
    height: 1px;
    background: var(--workflow-border-input);
  }
`

// 操作符图标容器
export const OperatorIcon = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin: 0 4px;
  color: var(--workflow-text-secondary);
  font-size: 14px;
`
