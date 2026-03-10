/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import styled from 'styled-components'

// 工作流画布包装器样式
export const WorkflowCanvasWrapper = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: var(--workflow-bg-canvas) !important;
`

export const DocFreeFeatureOverview = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
  background-color: var(--workflow-bg-canvas);
`

export const EditorContainer = styled.div`
  width: 100%;
  height: 100%;
  position: relative;
  background-color: var(--workflow-bg-canvas);
`

// 历史版本胶囊标签样式（与 Agents 页面一致的黄色样式）
export const HistoryVersionTag = styled.span`
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid #fde68a;
  background-color: #fffbeb;
  color: #b45309;
  font-size: 12px;
  line-height: 1;
`
