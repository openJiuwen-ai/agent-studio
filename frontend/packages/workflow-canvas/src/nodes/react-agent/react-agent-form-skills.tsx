/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useState } from 'react'
import { Field } from '@flowgram.ai/free-layout-editor'
import { Button, Tag } from '@douyinfe/semi-ui'
import { Plus, X } from 'lucide-react'
import { createRoot } from 'react-dom/client'
import { FormItem } from '../../form-components'
import { useTranslation } from '../../i18n'
import PluginSelector from '../../components/PluginSelector'
import WorkflowSelector from '../../components/WorkflowSelector'
import { dragStateManager } from '../../utils/drag-state-manager'
import { SkillItem } from './type'

// Helper function to open PluginSelector modal
const showPluginSelector = () => {
  return new Promise<any[] | null>(resolve => {
    try {
      dragStateManager.openModal()

      const container = document.createElement('div')
      document.body.appendChild(container)
      const root = createRoot(container)

      const handleClose = () => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }
        dragStateManager.closeModal()
        resolve(null)
      }

      const handleConfirm = (selectedPlugins: any[]) => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }
        dragStateManager.closeModal()

        if (selectedPlugins && selectedPlugins.length > 0) {
          resolve(selectedPlugins)
        } else {
          resolve(null)
        }
      }

      root.render(
        <div
          className="plugin-selector-modal"
          onMouseDown={e => e.stopPropagation()}
          onMouseUp={e => e.stopPropagation()}
          onClick={e => e.stopPropagation()}
        >
          <PluginSelector open={true} onClose={handleClose} onConfirm={handleConfirm} allowDuplicate={true} />
        </div>
      )
    } catch (error) {
      resolve(null)
    }
  })
}

// Helper function to open WorkflowSelector modal
const showWorkflowSelector = () => {
  return new Promise<any[] | null>(resolve => {
    try {
      dragStateManager.openModal()

      const container = document.createElement('div')
      document.body.appendChild(container)
      const root = createRoot(container)

      const handleClose = () => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }
        dragStateManager.closeModal()
        resolve(null)
      }

      const handleConfirm = (selectedWorkflows: any[]) => {
        try {
          root.unmount()
          document.body.removeChild(container)
        } catch (e) {
          console.error('清理DOM时出错:', e)
        }
        dragStateManager.closeModal()

        if (selectedWorkflows && selectedWorkflows.length > 0) {
          resolve(selectedWorkflows)
        } else {
          resolve(null)
        }
      }

      root.render(
        <div
          className="workflow-selector-modal"
          onMouseDown={e => e.stopPropagation()}
          onMouseUp={e => e.stopPropagation()}
          onClick={e => e.stopPropagation()}
        >
          <WorkflowSelector open={true} onClose={handleClose} onConfirm={handleConfirm} allowDuplicate={true} />
        </div>
      )
    } catch (error) {
      resolve(null)
    }
  })
}

export function ReactAgentFormSkills() {
  const { t } = useTranslation()
  const [isAddingPlugin, setIsAddingPlugin] = useState(false)
  const [isAddingWorkflow, setIsAddingWorkflow] = useState(false)

  return (
    <FormItem
      name={t('workflowCanvas.nodes.reactAgent.skills', 'Skills')}
      vertical
      description={t(
        'workflowCanvas.nodes.reactAgent.skillsDescription',
        'Select plugins and workflows as tools for the ReAct agent'
      )}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Plugins section */}
        <Field name="inputs.skillsParam.plugins" defaultValue={[]}>
          {({ field }) => (
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 500, color: '#666' }}>
                  {t('workflowCanvas.nodes.reactAgent.plugins', 'Plugins')}
                </span>
                <Button
                  icon={<Plus size={14} />}
                  size="small"
                  theme="borderless"
                  disabled={isAddingPlugin}
                  onClick={async () => {
                    setIsAddingPlugin(true)
                    try {
                      const selectedPlugins = await showPluginSelector()
                      if (selectedPlugins && selectedPlugins.length > 0) {
                        const newPlugins: SkillItem[] = selectedPlugins.map(plugin => ({
                          id: plugin.plugin_id,
                          name: plugin.name || plugin.plugin_id,
                          type: 'plugin' as const,
                        }))
                        field.onChange([...(field.value || []), ...newPlugins])
                      }
                    } finally {
                      setIsAddingPlugin(false)
                    }
                  }}
                >
                  {t('workflowCanvas.nodes.reactAgent.addPlugin', 'Add Plugin')}
                </Button>
              </div>

              {/* Plugin list */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', minHeight: '32px' }}>
                {field.value && field.value.length > 0 ? (
                  field.value.map((plugin: SkillItem, index: number) => (
                    <Tag
                      key={`${plugin.id}-${index}`}
                      closable
                      onClose={() => {
                        const newPlugins = field.value.filter((_: any, i: number) => i !== index)
                        field.onChange(newPlugins)
                      }}
                      style={{ marginBottom: '4px' }}
                    >
                      {plugin.name}
                    </Tag>
                  ))
                ) : (
                  <span style={{ fontSize: '12px', color: '#999' }}>
                    {t('workflowCanvas.nodes.reactAgent.noPlugins', 'No plugins selected')}
                  </span>
                )}
              </div>
            </div>
          )}
        </Field>

        {/* Workflows section */}
        <Field name="inputs.skillsParam.workflows" defaultValue={[]}>
          {({ field }) => (
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 500, color: '#666' }}>
                  {t('workflowCanvas.nodes.reactAgent.workflows', 'Workflows')}
                </span>
                <Button
                  icon={<Plus size={14} />}
                  size="small"
                  theme="borderless"
                  disabled={isAddingWorkflow}
                  onClick={async () => {
                    setIsAddingWorkflow(true)
                    try {
                      const selectedWorkflows = await showWorkflowSelector()
                      if (selectedWorkflows && selectedWorkflows.length > 0) {
                        const newWorkflows: SkillItem[] = selectedWorkflows.map(workflow => ({
                          id: workflow.workflow_id,
                          name: workflow.name || workflow.workflow_id,
                          type: 'workflow' as const,
                        }))
                        field.onChange([...(field.value || []), ...newWorkflows])
                      }
                    } finally {
                      setIsAddingWorkflow(false)
                    }
                  }}
                >
                  {t('workflowCanvas.nodes.reactAgent.addWorkflow', 'Add Workflow')}
                </Button>
              </div>

              {/* Workflow list */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', minHeight: '32px' }}>
                {field.value && field.value.length > 0 ? (
                  field.value.map((workflow: SkillItem, index: number) => (
                    <Tag
                      key={`${workflow.id}-${index}`}
                      closable
                      onClose={() => {
                        const newWorkflows = field.value.filter((_: any, i: number) => i !== index)
                        field.onChange(newWorkflows)
                      }}
                      style={{ marginBottom: '4px' }}
                    >
                      {workflow.name}
                    </Tag>
                  ))
                ) : (
                  <span style={{ fontSize: '12px', color: '#999' }}>
                    {t('workflowCanvas.nodes.reactAgent.noWorkflows', 'No workflows selected')}
                  </span>
                )}
              </div>
            </div>
          )}
        </Field>
      </div>
    </FormItem>
  )
}
