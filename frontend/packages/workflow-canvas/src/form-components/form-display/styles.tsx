/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import styled from 'styled-components'

export const FormDisplayStyle = styled.div`
  padding: 4px;
  width: 100%;
  min-height: 20px;
  font-size: 12px;
  line-height: 16px;
  display: flex;
  align-items: center;
  gap: 8px;

  .form-label {
    color: var(--workflow-text-secondary);
    font-weight: 500;
    flex-shrink: 0;
    line-height: 16px;
    min-width: 30px;
  }

  .form-content {
    color: var(--workflow-text-primary);
    flex: 1;
    white-space: pre-wrap;
    word-wrap: break-word;
    word-break: break-word;
    overflow-wrap: break-word;
    line-height: 16px;

    /* 只有在内容确实很长且是单行时才截断 */
    &[data-is-long-string='true'] {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-height: 20px;
    }
  }
`
