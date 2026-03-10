/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { Button } from '@douyinfe/semi-ui'
import styled from 'styled-components'

// 意图行容器
export const IntentRowContainer = styled.div<{ isDragging: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  padding: 4px 0;
  cursor: ${props => (props.isDragging ? 'grabbing' : 'grab')};
  opacity: ${props => (props.isDragging ? 0.5 : 1)};
  position: relative;
  transition: opacity 0.2s ease;

  &:hover {
    background-color: ${props => (props.isDragging ? 'transparent' : 'var(--workflow-bg-hover)')};
    border-radius: 4px;
  }
`

// 拖拽手柄
export const DragHandle = styled.div`
  width: 16px;
  height: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  cursor: grab;
  color: var(--workflow-text-tertiary);
  font-size: 12px;
  transition: color 0.2s ease;

  &:hover {
    color: var(--workflow-text-secondary);
  }

  &.dragging {
    cursor: grabbing;
  }
`

// 拖拽手柄内部线条
export const DragHandleLines = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;

  div {
    width: 12px;
    height: 2px;
    background-color: var(--workflow-border-input);
    transition: background-color 0.2s ease;
  }

  &:hover div {
    background-color: var(--workflow-text-tertiary);
  }
`

// 端口容器
export const PortContainer = styled.div`
  position: absolute;
  right: -12px;
  top: 50%;
`

// 删除按钮容器
export const DeleteButtonContainer = styled.div`
  transition: transform 0.2s ease;

  &:hover {
    transform: scale(1.05);
  }
`

// 其他意图容器
export const OtherIntentContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 1px;
  padding: 4px 8px;
  position: relative;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
`

// 其他意图文本
export const OtherIntentText = styled.div`
  flex: 1;
  font-size: 13px;
  display: flex;
  align-items: center;
  height: 28px;
  padding-left: 4px;
`

// 添加按钮容器
export const AddButtonContainer = styled.div`
  margin-bottom: 6px;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
`

// 空状态容器
export const EmptyStateContainer = styled.div`
  text-align: center;
  color: #999;
  padding: 16px;
  font-size: 13px;
  background-color: #fafafa;
  border-radius: 4px;
  border: 1px dashed #ddd;
`

// 占位宽度
export const Spacer = styled.div<{ width?: number }>`
  width: ${props => props.width || 16}px;
`

// 添加意图按钮样式
export const AddIntentButton = styled(Button)`
  &:hover {
    border-color: #1890ff !important;
    background-color: #f5f5f5 !important;

    .lucide-plus {
      color: #1890ff !important;
    }
  }
`
