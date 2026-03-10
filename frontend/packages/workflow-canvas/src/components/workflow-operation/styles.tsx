/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import styled from 'styled-components'

export const WorkflowOperationContainer = styled.div`
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  min-width: 360px;
  pointer-events: none;
  gap: 8px;

  z-index: 20;
`

export const WorkflowControlSection = styled.div`
  display: flex;
  align-items: center;
  background-color: var(--workflow-bg-toolbar);
  border: 1px solid var(--workflow-border-toolbar);
  border-radius: 10px;
  box-shadow: var(--workflow-shadow-toolbar);
  column-gap: 2px;
  min-height: 40px;
  padding: 0 4px;
  pointer-events: auto;
`
