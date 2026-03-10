/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { MapIcon } from 'lucide-react'
import styled from 'styled-components'

export const ToolContainer = styled.div`
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  min-width: 360px;
  pointer-events: none;
  gap: 8px;

  z-index: 20;
`

export const ToolSection = styled.div`
  display: flex;
  align-items: center;
  background-color: var(--workflow-bg-toolbar);
  border: 1px solid var(--workflow-border-toolbar);
  border-radius: 10px;
  box-shadow: var(--workflow-shadow-toolbar);
  column-gap: 2px;
  height: 40px;
  padding: 0 4px;
  pointer-events: auto;
`

export const SelectZoom = styled.span`
  padding: 4px;
  border-radius: 8px;
  border: 1px solid var(--workflow-border-toolbar);
  font-size: 12px;
  width: 50px;
  cursor: pointer;
`

export const MinimapContainer = styled.div`
  position: fixed;
  bottom: 16px; /* 距离底部16px */
  left: calc(var(--sidebar-width, 256px) + 20px); /* 侧边栏宽度 + 间距 */
  width: 198px;
  z-index: 30;
  pointer-events: auto;
  transition: left 0.3s ease-in-out; /* 与侧边栏动画同步 */
`

export const UIIconMinimap = styled(MapIcon)`
  width: ${props => props.width || 16}px;
  height: ${props => props.height || 16}px;
`
