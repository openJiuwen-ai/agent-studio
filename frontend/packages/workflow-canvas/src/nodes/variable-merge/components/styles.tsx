/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import styled from 'styled-components'

export const GroupCardWrapper = styled.div`
  border: 1px solid var(--workflow-border-input);
  border-radius: 8px;
  padding: 8px;
  margin-bottom: 12px;
  background: var(--workflow-bg-surface);

  &.read-only {
    border-color: var(--workflow-border-input);
    background: var(--workflow-bg-input);
  }
`

export const GroupHeader = styled.div`
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between;
  height: 24px;
  margin-bottom: 4px;
  padding: 0 4px;
`

export const GroupInfo = styled.div`
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 6px;
  flex: 1;
  overflow: hidden;
`

export const GroupName = styled.span`
  font-size: 12px;
  font-weight: 500;
  color: var(--workflow-text-primary);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background-color 0.15s ease-in-out;

  &:hover {
    background: var(--workflow-bg-hover);
  }
`

export const GroupMeta = styled.div`
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 4px;
  flex-shrink: 0;
`

export const TypeTag = styled.div`
  font-size: 10px;
  font-weight: 500;
  padding: 1px 4px;
  border-radius: 4px;
  min-width: auto;
`

export const InfoIcon = styled.div`
  color: var(--workflow-text-secondary);
  cursor: help;
  transition: color 0.15s ease-in-out;

  &:hover {
    color: var(--workflow-text-primary);
  }
`

export const DeleteGroupButton = styled.div`
  color: var(--workflow-text-secondary);
  transition: color 0.15s ease-in-out;

  &:hover {
    color: #ff4d4f;
  }
`

export const VariablesList = styled.div`
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
`

export const VariableItem = styled.div`
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 4px;
  padding: 4px 6px;
  background: #fafafa;
  border: 1px solid var(--workflow-border-input);
  border-radius: 6px;
  transition: all 0.15s ease-in-out;
  flex: 0 0 auto;

  &:hover {
    border-color: var(--accent-primary);
    background: var(--workflow-bg-hover);
  }

  &.dragging {
    opacity: 0.8;
    transform: scale(0.98);
  }
`

export const DragHandle = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: #999999;
  cursor: grab;
  transition: color 0.15s ease-in-out;
  flex-shrink: 0;

  &:hover {
    color: #666666;
  }

  &.dragging {
    cursor: grabbing;
  }
`

export const VariableContent = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
`

export const VariableTypeIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: #999999;
  flex-shrink: 0;
`

export const DeleteButton = styled.div`
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  min-width: 20px;
  color: #999999;
  opacity: 1;
  transition: color 0.15s ease-in-out;
  padding: 0;
  margin-left: 2px;

  &:hover {
    color: #ff4d4f;
  }
`

export const EmptyVariables = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px dashed #d9d9d9;
`

export const EmptyContent = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #999999;
  text-align: center;
`

export const EmptyIcon = styled.div`
  opacity: 0.6;
`

export const EmptyText = styled.div`
  font-size: 11px;
  line-height: 1.3;
`

export const VariableItemWrapper = styled.div`
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 4px;
  padding: 4px 6px;
  background: #fafafa;
  border: 1px solid var(--workflow-border-input);
  border-radius: 6px;
  transition: all 0.15s ease-in-out;
  flex: 0 0 auto;
  width: 100%;

  &:hover {
    border-color: var(--accent-primary);
    background: var(--workflow-bg-hover);
  }

  &.dragging {
    opacity: 0.8;
    transform: scale(0.98);
  }
`

export const VariableContentList = styled.div`
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
`
