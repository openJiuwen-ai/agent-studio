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
import { t } from './i18n'

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

// 内部组件：用于在编辑器上下文中打开节点面板
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

    // 如果已经打开过该节点，不再重复打开
    if (nodeIdOpenedRef.current === nodeId) {
      return
    }

    // 等待编辑器完全初始化
    const timer = setTimeout(() => {
      try {
        const node = document.getNode(nodeId)

        if (!node) {
          console.warn(`节点 ${nodeId} 不存在`)
          return
        }

        // 选择节点
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

        // 滚动到节点位置
        scrollToView(ctx, node)

        // 标记已打开
        nodeIdOpenedRef.current = nodeId
      } catch (error) {
        console.error('打开节点详情面板失败:', error)
      }
    }, 500) // 延迟 500ms 确保编辑器完全初始化

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

  const historyService = useService(HistoryService)

  const showHistoryPanel = useWorkflowStore(s => s.showHistoryPanel)
  const context = useWorkflowStore(s => s.context)
  const selectedVersion = useWorkflowStore(s => s.selectedVersion)
  const historyRefreshTs = useWorkflowStore(s => s.historyRefreshTs)
  const closeHistoryPanel = useWorkflowStore(s => s.closeHistoryPanel)
  const setSelectedVersion = useWorkflowStore(s => s.setSelectedVersion)

  const { canvasData, initialCanvasData, isLoading, error, handleAutoSave } = useWorkflowData(workflowId, spaceId, version)
  const editorRef = React.useRef<FreeLayoutPluginContext>(null)

  const editorProps = useEditorProps(initialCanvasData, nodeRegistries, handleAutoSave)

  React.useEffect(() => {
    try {
      useWorkflowStore.getState().resetStore()
    } catch {
      // do nothing
    }
  }, [])

  // 离开当前编辑器页面时，清理试运行输入缓存，确保重新进入时使用默认值
  useEffect(() => {
    return () => {
      clearLastTestRunValues()
      clearLastNodeTestValues()
    }
  }, [])

  // 当URL中有version参数时，自动选中对应的版本
  React.useEffect(() => {
    if (version && version !== 'draft') {
      setSelectedVersion(version)
    }
  }, [version, setSelectedVersion])
  // 当用户选择历史版本时，查询历史版本信息并显示在画布中
  const handleHistoryVersionSelect = async (versionId: string) => {
    setSelectedVersion(versionId)
    try {
      const response = await WorkflowService.getWorkflowCanvas({
        workflow_id: context?.workflowId || workflowId || '',
        space_id: context?.spaceId || spaceId || '',
        version: versionId === 'draft' ? undefined : versionId,
      })
      if (response.code === 200) {
        const schemaString = response?.data?.workflow?.schema
        if (!schemaString) {
          console.warn('历史版本 schema 为空，无法加载到画布')
          return
        }
        try {
          const parsed = typeof schemaString === 'string' ? JSON.parse(schemaString) : schemaString
          historyService.stop()
          editorRef.current?.document.clear()
          editorRef.current?.document.fromJSON(parsed)
          historyService.start()
          // 加载后触发 fitView，让节点居中展示
          setTimeout(() => {
            try {
              const bounds = editorRef.current?.document.root.bounds.pad(30)
              if (bounds) {
                editorRef.current?.playground.config.fitView(bounds)
              }
            } catch (e) {
              // 忽略居中失败
            }
          }, 100)
          // 切换成功后提示版本信息（先清空旧消息，再弹新消息）
          Toast.destroyAll()
          const versionDisplay = versionId === 'draft' ? t('workflowCanvas.ui.draft') : versionId
          Toast.success({ content: t('workflowCanvas.ui.switchedToVersion', { version: versionDisplay }) })
        } catch (e) {
          console.error('历史版本 schema 解析失败或导入失败', e)
          historyService.start()
        }
      } else {
        console.error('获取历史版本失败', response)
      }
    } catch (err) {
      console.error('获取历史版本失败', err)
    }
  }

  // 加载状态
  if (isLoading) {
    return <LoadingState />
  }

  // 错误状态 - 只有在真正出错时才显示错误状态
  if (error) {
    return <ErrorState error={error instanceof Error ? error : error ? new Error(String(error)) : null} onRetry={() => window.location.reload()} />
  }

  // 正常显示
  return (
    <div className="w-full h-full">
      <WorkflowCanvasWrapper>
        <DocFreeFeatureOverview>
          <FreeLayoutEditorProvider ref={editorRef} {...editorProps}>
            <ExecutionProvider>
              {/* 自动打开节点详情面板 */}
              {!isLoading && initialCanvasData && nodeIdFromUrl && <AutoOpenNodePanel nodeId={nodeIdFromUrl} />}
              <div className="w-full h-full" style={{ display: 'flex', height: '100%' }}>
                {/* 左侧画布区域：在侧边面板打开时自动压缩 */}
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                  <EditorContainer>
                    <EditorRenderer className="editor" />
                  </EditorContainer>
                </div>

                {/* 右侧固定宽度版本历史面板 */}
                {showHistoryPanel && (
                  <HistoryPanel
                    title="版本历史"
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
