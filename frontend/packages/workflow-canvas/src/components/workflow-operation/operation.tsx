/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'
import { WorkflowOperationsHandler } from './handler'
import { WorkflowControl } from './control'

interface WorkflowOperationProps {
  workflowId?: string
  spaceId?: string
  canvasData: any
}

export function WorkflowOperation({ workflowId, spaceId, canvasData }: WorkflowOperationProps) {
  // Reference to store the async save function
  const saveWorkflowRef = React.useRef<(() => Promise<void>) | null>(null)

  // Button handlers
  const handleSaveWorkflow = () => {
    window.dispatchEvent(new CustomEvent('workflow-save'))
  }

  const handleImportWorkflow = () => {
    window.dispatchEvent(new CustomEvent('workflow-import'))
  }

  const handleExportWorkflow = () => {
    window.dispatchEvent(new CustomEvent('workflow-export'))
  }

  const handleExportWorkflowPy = () => {
    window.dispatchEvent(new CustomEvent('workflow-export-py'))
  }

  return (
    <>
      {/* Workflow Control Panel */}
      <WorkflowControl
        onSave={handleSaveWorkflow}
        onImport={handleImportWorkflow}
        onExport={handleExportWorkflow}
        onExportPy={handleExportWorkflowPy}
        workflowId={workflowId}
        spaceId={spaceId}
        asyncSaveRef={saveWorkflowRef}
        canvasData={canvasData}
      />

      {/* Workflow Operations Handler */}
      <WorkflowOperationsHandler workflowId={workflowId} canvasData={canvasData} spaceId={spaceId} onSaveRef={saveWorkflowRef} />
    </>
  )
}
