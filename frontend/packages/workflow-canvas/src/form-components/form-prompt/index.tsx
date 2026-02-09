/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React from 'react'
import { Field } from '@flowgram.ai/free-layout-editor'

import { IFlowTemplateValue, PromptEditorWithInputs } from '../../form-materials'
import { useIsSidebar, useNodeRenderContext } from '../../hooks'
import { FormItem } from '../form-item'
import { useTranslation } from '../../i18n'
import { PromptTitleActions } from '@/components/Agent/PromptTitleActions'
import { PromptGenerationBanner } from '@/components/Agent/PromptGenerationBanner'
import { PromptRelationInfoBar } from '@/components/Agent/PromptRelationInfoBar'
import { useWorkflowNodePrompt } from '../../hooks/use-workflow-node-prompt'
import AgentAssociatePromptDialog from '@/components/Agent/AgentAssociatePromptDialog'
import SavePromptDialog from '@/components/Agent/SavePromptDialog'
import OverridePromptTemplateDialog from '@/components/Agent/OverridePromptTemplateDialog'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import UnifiedSnackbar from '@/Common/UnifiedSnackbar'
import { ENV_CONFIG } from '@/config/environment'

export interface FormPromptProps {
  systemPromptName?: string
  userPromptName?: string
  inputParametersName?: string
  modelName?: string
  disableMarkdownHighlight?: boolean
  style?: React.CSSProperties
  mode?: 'both' | 'systemOnly' | 'userOnly'
}

export function FormPrompt({
  systemPromptName = 'inputs.llmParam.systemPrompt',
  userPromptName = 'inputs.llmParam.prompt',
  inputParametersName = 'inputs.inputParameters',
  modelName = 'inputs.llmParam.model',
  disableMarkdownHighlight = false,
  style = { flexGrow: 4 },
  mode = 'both',
}: FormPromptProps) {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const { node } = useNodeRenderContext()

  if (!isSidebar) {
    return null
  }

  const renderUserPrompt = (inputsValues: Record<string, any>) => (
    <FormItem name={t('workflowCanvas.formPrompt.userPrompt')} vertical defaultCollapsed={true}>
      <Field<IFlowTemplateValue> name={userPromptName}>
        {({ field }) => (
          <PromptEditorWithInputs
            key={`user-${userPromptName}`}
            disableMarkdownHighlight={disableMarkdownHighlight}
            style={style}
            value={field.value}
            onChange={value => field.onChange(value as any)}
            inputsValues={inputsValues}
          />
        )}
      </Field>
    </FormItem>
  )

  if (mode === 'userOnly') {
    return (
      <Field<Record<string, any> | undefined> name={inputParametersName}>
        {({ field: inputParametersField }) => {
          const inputsValues = inputParametersField.value || {}

          return renderUserPrompt(inputsValues)
        }}
      </Field>
    )
  }

  return (
    <Field<Record<string, any> | undefined> name={inputParametersName}>
      {({ field: inputParametersField }) => {
        const inputsValues = inputParametersField.value || {}

        return (
          <Field<IFlowTemplateValue> name={systemPromptName}>
            {({ field: systemPromptField }) => {
              // 获取系统提示词的文本内容
              const systemPromptText = systemPromptField.value?.content || ''
              const handleSystemPromptChange = (text: string) => {
                systemPromptField.onChange({
                  type: 'template',
                  content: text,
                  extra: systemPromptField.value?.extra,
                } as IFlowTemplateValue)
              }

              // 获取模型信息和节点标题
              return (
                <Field<{ id: string; name: string; type: string } | undefined> name={modelName}>
                  {({ field: modelField }) => {
                    // 构建符合新API格式的modelInfo
                    const modelInfo = modelField.value
                      ? {
                          id: parseInt(modelField.value.id) || 0,
                          model: modelField.value.type || '',
                          model_from: 'db',
                          headers: {
                            temperature: 0.7,
                            max_tokens: 4000,
                            top_p: 0.9,
                          },
                        }
                      : {
                          id: 0,
                          model: '',
                          model_from: 'db',
                          headers: {
                            temperature: 0.7,
                            max_tokens: 4000,
                            top_p: 0.9,
                          },
                        }

                    return (
                      <Field<string> name="title">
                        {({ field: titleField }) => {
                          const nodeTitle = titleField.value || node.id

                          // 使用 hook 管理提示词功能
                          const promptHook = useWorkflowNodePrompt({
                            nodeId: node.id,
                            nodeName: nodeTitle,
                            systemPrompt: systemPromptText,
                            onSystemPromptChange: handleSystemPromptChange,
                            readonly: false,
                            modelInfo,
                          })

                          return (
                            <>
                              <FormItem name={t('workflowCanvas.formPrompt.systemPrompt')} vertical defaultCollapsed={true}>
                                <div className="flex flex-col gap-2">
                                  {/* 操作按钮 */}
                                  <div className="flex items-center gap-2">
                                    <PromptTitleActions
                                      readonly={false}
                                      isGenerating={promptHook.isGenerating}
                                      candidatePrompt={promptHook.candidatePrompt}
                                      saving={promptHook.saving}
                                      systemPrompt={systemPromptText}
                                      onOptimize={promptHook.handleQuickOptimizeGenerate}
                                      onAssociate={promptHook.handleOpenAssociateDialog}
                                      onSave={promptHook.handleOpenSaveDialog}
                                    />
                                  </div>

                                  {/* 生成提示词横幅 */}
                                  <PromptGenerationBanner
                                    isGenerating={promptHook.isGenerating}
                                    candidatePrompt={promptHook.candidatePrompt}
                                    readonly={false}
                                    onCancel={promptHook.handleCancelCandidate}
                                    onAdopt={promptHook.handleAdoptCandidate}
                                  />

                                  {/* 关联提示词信息条 */}
                                  <PromptRelationInfoBar
                                    currentRelation={promptHook.currentRelation}
                                    readonly={false}
                                    safeSelectedVersion={promptHook.safeSelectedVersion}
                                    selectedVersion={promptHook.selectedVersion}
                                    latestVersion={promptHook.latestVersion}
                                    versionOptions={promptHook.versionOptions}
                                    versionLoading={promptHook.versionLoading}
                                    onVersionChange={promptHook.handleVersionSelectChange}
                                    onOpenOverrideDialog={() => promptHook.setOverrideDraftDialogOpen(true)}
                                    onOpenUnlinkConfirm={() => promptHook.setUnlinkConfirmOpen(true)}
                                  />

                                  {/* 提示词编辑器 */}
                                  <PromptEditorWithInputs
                                    key={`system-${systemPromptName}`}
                                    disableMarkdownHighlight={disableMarkdownHighlight}
                                    style={style}
                                    onChange={value => {
                                      const newValue = value as IFlowTemplateValue
                                      handleSystemPromptChange(newValue?.content || '')
                                    }}
                                    value={
                                      promptHook.isLockedForCandidate
                                        ? {
                                            type: 'template',
                                            content: promptHook.effectiveText,
                                            extra: systemPromptField.value?.extra,
                                          }
                                        : systemPromptField.value
                                    }
                                    inputsValues={inputsValues}
                                  />
                                </div>
                              </FormItem>

                              {mode !== 'systemOnly' && renderUserPrompt(inputsValues)}

                              {/* 关联提示词弹窗 */}
                              <AgentAssociatePromptDialog
                                open={promptHook.associateDialogOpen}
                                onClose={promptHook.handleCloseAssociateDialog}
                                onReplace={promptHook.handleReplacePromptText}
                                onInsert={promptHook.handleInsertPromptText}
                                workspaceId={promptHook.workspaceId}
                                relatedMemberInfo={promptHook.nodeInfo}
                                onRelationUpdated={promptHook.handleRelationUpdated}
                              />

                              {/* 保存提示词弹窗 */}
                              <SavePromptDialog
                                open={promptHook.saveDialogOpen}
                                onClose={() => promptHook.setSaveDialogOpen(false)}
                                onConfirm={promptHook.handleConfirmSave}
                                saving={promptHook.saving}
                                existingPromptInfo={promptHook.existingPromptInfo ?? undefined}
                                saveForm={promptHook.saveForm}
                                setSaveForm={promptHook.setSaveForm}
                              />

                              {/* 覆盖提示词模板弹窗 */}
                              <OverridePromptTemplateDialog
                                open={promptHook.overrideDraftDialogOpen}
                                onClose={() => promptHook.setOverrideDraftDialogOpen(false)}
                                onJump={() => {
                                  promptHook.setOverrideDraftDialogOpen(false)
                                  const pid = promptHook.currentRelation?.promptId
                                  if (pid) {
                                    const versionParam =
                                      promptHook.selectedVersion || promptHook.versionOptions[0]?.version || ENV_CONFIG.DEFAULT_PROMPT_VERSION
                                    window.open(`/dashboard/prompts/${pid}?version=${versionParam}&from=workflow`, '_blank')
                                  }
                                }}
                                onOverwrite={() => {
                                  promptHook.setOverrideDraftDialogOpen(false)
                                  // 从 field 中获取最新的 systemPrompt 值，确保是最新的
                                  const currentSystemPrompt = systemPromptField.value?.content || ''
                                  const overrideData = {
                                    systemPrompt: currentSystemPrompt,
                                    type: 'System',
                                    fromWorkflow: true,
                                    timestamp: Date.now(),
                                  }
                                  try {
                                    sessionStorage.setItem('promptOverrideData', JSON.stringify(overrideData))
                                  } catch (err) {
                                    // noop
                                  }
                                  const pid = promptHook.currentRelation?.promptId
                                  if (pid) {
                                    window.open(`/dashboard/prompts/${pid}`, '_blank')
                                  }
                                }}
                              />

                              {/* 解关联确认弹窗 */}
                              <DeleteConfirmationDialog
                                isOpen={promptHook.unlinkConfirmOpen}
                                onClose={() => promptHook.setUnlinkConfirmOpen(false)}
                                onConfirm={async () => {
                                  await promptHook.handleUnlinkRelation()
                                  promptHook.setUnlinkConfirmOpen(false)
                                }}
                                itemType="workflow"
                                itemName={nodeTitle}
                                title={t('workflowCanvas.formPrompt.unlink')}
                                message={t('workflowCanvas.formPrompt.unlinkConfirm', {
                                  promptName: promptHook.currentRelation?.promptName || '',
                                  version: promptHook.selectedVersion || promptHook.currentRelation?.promptVersion || ''
                                })}
                                confirmButtonText={t('workflowCanvas.formPrompt.confirm')}
                              />

                              {/* 消息提示 */}
                              <UnifiedSnackbar snackbar={promptHook.snackbar} onClose={() => promptHook.setSnackbar((s: any) => ({ ...s, open: false }))} />
                            </>
                          )
                        }}
                      </Field>
                    )
                  }}
                </Field>
              )
            }}
          </Field>
        )
      }}
    </Field>
  )
}
