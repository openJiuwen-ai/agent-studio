/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import '@flowgram.ai/free-layout-editor/index.css'
import './styles/index.css'

import {
  EditorRenderer,
  FreeLayoutEditorProvider,
  FreeLayoutPluginContext,
  useClientContext,
  useService,
  WorkflowSelectService,
  HistoryService,
} from '@flowgram.ai/free-layout-editor'
import React, { useEffect, useRef } from 'react'
import { HistoryPanel } from './components/history-panel'
import { useParams, useSearchParams } from 'react-router-dom'

import { nodeRegistries } from './nodes'
import { useEditorProps, useWorkflowData } from './hooks'
import { Tools } from './components/tools'
import { ExecutionProvider } from './context'
import { WorkflowOperation } from './components/workflow-operation'
import { LoadingState, ErrorState } from './components/editor-states'
import { useTranslation } from './i18n'

import { WorkflowCanvasWrapper, DocFreeFeatureOverview, EditorContainer } from './styles/styles'
import { WorkflowService } from '@test-agentstudio/api-client'
import { useWorkflowStore } from './stores/useWorkflowStore'
import { Toast } from '@douyinfe/semi-ui'
import { nodeFormPanelFactory } from './components/sidebar'
import { usePanelManager } from '@flowgram.ai/panel-manager-plugin'
import { scrollToView } from './components/base-node/utils'
import { testRunRuntimeService } from './components/testrun/runtime/testrun-runtime-service'
import { clearLastTestRunValues } from './components/testrun/testrun-panel/test-run-panel'
import { clearLastNodeTestValues } from './components/testrun/testdebug/test-debug-panel'

const HistoryVersionHandler: React.FC<{
  editorRef: React.RefObject<FreeLayoutPluginContext>
  workflowId: string | undefined
  spaceId: string | undefined
  versionId: string | null
}> = ({ editorRef, workflowId, spaceId, versionId }) => {
  const historyService = useService(HistoryService)
  const { t } = useTranslation()
  const context = useWorkflowStore(s => s.context)
  const setSelectedVersion = useWorkflowStore(s => s.setSelectedVersion)

  useEffect(() => {
    if (!versionId) return

    const handleVersionSwitch = async () => {
      try {
        const response = await WorkflowService.getWorkflowCanvas({
          workflow_id: context?.workflowId || workflowId || '',
          space_id: context?.spaceId || spaceId || '',
          version: versionId === 'draft' ? undefined : versionId,
        })
        if (response.code === 200) {
          const schemaString = response?.data?.workflow?.schema
          if (!schemaString) {
            console.warn(t('workflowCanvas.editor.historyVersionSchemaEmpty'))
            return
          }
          try {
            const parsed = typeof schemaString === 'string' ? JSON.parse(schemaString) : schemaString
            historyService.stop()
            editorRef.current?.document.clear()
            editorRef.current?.document.fromJSON(parsed)
            historyService.start()
            setTimeout(() => {
              try {
                const bounds = editorRef.current?.document.root.bounds.pad(30)
                if (bounds) {
                  editorRef.current?.playground.config.fitView(bounds)
                }
              } catch (e) {
                // ignore
              }
            }, 100)
            Toast.destroyAll()
            const versionDisplay = versionId === 'draft' ? t('workflowCanvas.ui.draft') : versionId
            Toast.success({ content: t('workflowCanvas.ui.switchedToVersion', { version: versionDisplay }) })
          } catch (e) {
            console.error(t('workflowCanvas.editor.historySchemaParseFailed'), e)
            historyService.start()
          }
        } else {
          console.error(t('workflowCanvas.editor.fetchHistoryVersionFailed'), response)
        }
      } catch (err) {
        console.error(t('workflowCanvas.editor.fetchHistoryVersionFailed'), err)
      }
    }

    handleVersionSwitch()
  }, [versionId, historyService, editorRef, workflowId, spaceId, context, t])

  return null
}

const AutoOpenNodePanel: React.FC<{ nodeId: string | undefined }> = ({ nodeId }) => {
  const ctx = useClientContext()
  const { document } = ctx
  const panelManager = usePanelManager()
  const selectService = useService(WorkflowSelectService)
  const nodeIdOpenedRef = useRef<string | null>(null)

  useEffect(() => {
    if (!nodeId || !document) {
      return
    }

    if (nodeIdOpenedRef.current === nodeId) {
      return
    }

    const timer = setTimeout(() => {
      try {
        const node = document.getNode(nodeId)

        if (!node) {
          console.warn(t('workflowCanvas.editor.nodeNotFound', { nodeId }))
          return
        }

        if (selectService) {
          selectService.selectNode(node)
        }

        if (!testRunRuntimeService.getIsRunning()) {
          panelManager.open(nodeFormPanelFactory.key, 'right', {
            props: {
              nodeId: nodeId,
            },
          })
        }

        scrollToView(ctx, node)

        nodeIdOpenedRef.current = nodeId
      } catch (error) {
        console.error(t('workflowCanvas.editor.openNodePanelFailed'), error)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [nodeId, document, selectService, panelManager, ctx])

  return null
}

export const Editor = () => {
  const { id: workflowId } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const spaceId = searchParams.get('spaceId') || undefined
  const version = searchParams.get('version') || undefined
  const nodeIdFromUrl = searchParams.get('node_id') || searchParams.get('nodeId') || undefined

  const showHistoryPanel = useWorkflowStore(s => s.showHistoryPanel)
  const context = useWorkflowStore(s => s.context)
  const selectedVersion = useWorkflowStore(s => s.selectedVersion)
  const historyRefreshTs = useWorkflowStore(s => s.historyRefreshTs)
  const closeHistoryPanel = useWorkflowStore(s => s.closeHistoryPanel)
  const setSelectedVersion = useWorkflowStore(s => s.setSelectedVersion)

  const { canvasData, initialCanvasData, isLoading, error, handleAutoSave } = useWorkflowData(workflowId, spaceId, version)
  const editorRef = React.useRef<FreeLayoutPluginContext>(null)
  const { t } = useTranslation()

  const editorProps = useEditorProps(initialCanvasData, nodeRegistries, handleAutoSave)

  React.useEffect(() => {
    try {
      useWorkflowStore.getState().resetStore()
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    return () => {
      clearLastTestRunValues()
      clearLastNodeTestValues()
    }
  }, [])

  const handleHistoryVersionSelect = (versionId: string) => {
    setSelectedVersion(versionId)
  }

  React.useEffect(() => {
    if (version && version !== 'draft') {
      setSelectedVersion(version)
    }
  }, [version, setSelectedVersion])

  if (isLoading) {
    return <LoadingState />
  }

  if (error) {
    return <ErrorState error={error instanceof Error ? error : error ? new Error(String(error)) : null} onRetry={() => window.location.reload()} />
  }

  return (
    <div className="w-full h-full">
      <WorkflowCanvasWrapper>
        <DocFreeFeatureOverview>
          <FreeLayoutEditorProvider ref={editorRef} {...editorProps}>
            <ExecutionProvider>
              <HistoryVersionHandler
                editorRef={editorRef}
                workflowId={context?.workflowId || workflowId}
                spaceId={context?.spaceId || spaceId}
                versionId={selectedVersion}
              />
              {!isLoading && initialCanvasData && nodeIdFromUrl && <AutoOpenNodePanel nodeId={nodeIdFromUrl} />}
              <div className="w-full h-full" style={{ display: 'flex', height: '100%' }}>
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                  <EditorContainer>
                    <EditorRenderer className="editor" />
                  </EditorContainer>
                </div>

                {showHistoryPanel && (
                  <HistoryPanel
                    title={t('workflowCanvas.editor.versionHistory')}
                    width={360}
                    onClose={() => closeHistoryPanel()}
                    workflowId={context?.workflowId || workflowId || undefined}
                    spaceId={context?.spaceId || spaceId || undefined}
                    onSelectVersion={handleHistoryVersionSelect}
                    selectedVersion={selectedVersion || undefined}
                    refreshKey={historyRefreshTs}
                  />
                )}
              </div>
              <Tools workflowId={workflowId} spaceId={spaceId} />
              <WorkflowOperation workflowId={workflowId} spaceId={spaceId} canvasData={canvasData} />
            </ExecutionProvider>
          </FreeLayoutEditorProvider>
        </DocFreeFeatureOverview>
      </WorkflowCanvasWrapper>
    </div>
  )
}
