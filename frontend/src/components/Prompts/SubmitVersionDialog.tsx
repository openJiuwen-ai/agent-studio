import React from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Typography, Alert, Chip, IconButton } from '@mui/material'
import { Save, ArrowLeft, Brain, Settings, Cpu, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { DiffViewer } from '@/components/Prompts'
import { validateVersionNumber } from '@/utils/prompts/utils'

// 比较两个版本号，返回 1 / -1 / 0
// 1: a > b, -1: a < b, 0: a === b
const compareVersions = (a?: string, b?: string): number => {
  // 移除 "v" 前缀
  const normalizeVersion = (version: string) => version.replace(/^v/i, '')

  const versionA = normalizeVersion(a || '')
  const versionB = normalizeVersion(b || '')

  const pa = versionA.split('.').map(n => parseInt(n, 10) || 0)
  const pb = versionB.split('.').map(n => parseInt(n, 10) || 0)
  const len = Math.max(pa.length, pb.length)

  for (let i = 0; i < len; i++) {
    const va = pa[i] || 0
    const vb = pb[i] || 0
    if (va > vb) return 1
    if (va < vb) return -1
  }
  return 0
}

interface SubmitVersionDialogProps {
  open: boolean
  onClose: () => void
  submitVersionStep: number
  promptCommitData: any
  promptDraftData: any
  latestVersion: string | null
  versionNumber: string
  setVersionNumber: (version: string) => void
  versionDescription: string
  setVersionDescription: (description: string) => void
  versionNumberError: string
  setVersionNumberError: (error: string) => void
  onNextStep: () => void
  onPrevStep: () => void
  onConfirmSubmit: () => void
}

const SubmitVersionDialog: React.FC<SubmitVersionDialogProps> = ({
  open,
  onClose,
  submitVersionStep,
  promptCommitData,
  promptDraftData,
  latestVersion,
  versionNumber,
  setVersionNumber,
  versionDescription,
  setVersionDescription,
  versionNumberError,
  setVersionNumberError,
  onNextStep,
  onPrevStep,
  onConfirmSubmit,
}) => {
  const { t } = useTranslation()
  // 预处理函数：过滤null值和key字段
  const preprocessForComparison = (data: any): any => {
    if (Array.isArray(data)) {
      return data.map(item => preprocessForComparison(item))
    } else if (data && typeof data === 'object') {
      const filtered: any = {}
      for (const [key, value] of Object.entries(data)) {
        // 跳过key字段和null值
        if (key !== 'key' && value !== null) {
          filtered[key] = preprocessForComparison(value)
        }
      }
      return filtered
    }
    return data
  }
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        className: 'bg-gradient-to-br from-blue-50 to-indigo-50',
      }}
    >
      <DialogTitle className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Save className="w-6 h-6" />
            <span>{t('components.prompts.submitVersionDialog.title')}</span>
          </div>
          <IconButton
            onClick={onClose}
            size="small"
            sx={{
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            <X className="w-5 h-5" />
          </IconButton>
        </div>
      </DialogTitle>

      <DialogContent className="p-6">
        {/* 步骤指示器 */}
        <div className="flex items-center justify-center mt-4 mb-6">
          <div className="flex items-center space-x-4">
            {promptCommitData && (
              <>
                <div className={`flex items-center space-x-2 ${submitVersionStep >= 0 ? 'text-blue-600' : 'text-gray-400'}`}>
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      submitVersionStep >= 0 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    1
                  </div>
                  <span className="text-sm font-medium">{t('components.prompts.submitVersionDialog.step1')}</span>
                </div>
                <div className="w-8 h-0.5 bg-gray-300"></div>
              </>
            )}
            <div className={`flex items-center space-x-2 ${submitVersionStep >= (promptCommitData ? 1 : 0) ? 'text-blue-600' : 'text-gray-400'}`}>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  submitVersionStep >= (promptCommitData ? 1 : 0) ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                }`}
              >
                {promptCommitData ? '2' : '1'}
              </div>
              <span className="text-sm font-medium">{t('components.prompts.submitVersionDialog.step2')}</span>
            </div>
          </div>
        </div>

        {submitVersionStep === 0 ? (
          // Step 1: 确认版本差异
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Typography variant="h5" className="text-gray-800 font-semibold mb-2">
                {t('components.prompts.submitVersionDialog.confirmChanges')}
              </Typography>
            </div>

            {(() => {
              // 比较prompt_commit（原版本）和prompt_draft（当前版本）
              const commitData = promptCommitData // 原版本
              const draftData = promptDraftData // 当前版本

              // 检查是否有变更 - 比较prompt_commit与prompt_draft
              let hasPromptChanges = false
              let hasParameterChanges = false
              let hasModelChanges = false
              let hasToolChanges = false

              if (commitData && draftData) {
                // 对比提示词内容（包括template_type和messages）
                const commitTemplateType = commitData.prompt_template?.template_type || 'normal'
                const draftTemplateType = draftData.prompt_template?.template_type || 'normal'
                const commitMessages = JSON.stringify(preprocessForComparison(commitData.prompt_template?.messages || []))
                const draftMessages = JSON.stringify(preprocessForComparison(draftData.prompt_template?.messages || []))
                hasPromptChanges = commitTemplateType !== draftTemplateType || commitMessages !== draftMessages

                // 对比变量定义
                const commitVariables = commitData.prompt_template?.variable_defs || []
                const draftVariables = draftData.prompt_template?.variable_defs || []

                // 检查是否有变量变更
                hasParameterChanges =
                  draftVariables.some(draftParam => {
                    const commitParam = commitVariables.find(v => v.key === draftParam.key)
                    return !commitParam || commitParam.type !== draftParam.type
                  }) ||
                  commitVariables.some(commitParam => {
                    const draftParam = draftVariables.find(p => p.key === commitParam.key)
                    return !draftParam
                  })

                // 对比模型配置
                const commitModelConfig = commitData.prompt_model_config || {}
                const draftModelConfig = draftData.prompt_model_config || {}
                hasModelChanges =
                  commitModelConfig.models_name !== draftModelConfig.models_name ||
                  commitModelConfig.models_id !== draftModelConfig.models_id ||
                  commitModelConfig.temperature !== draftModelConfig.temperature ||
                  commitModelConfig.max_tokens !== draftModelConfig.max_tokens ||
                  commitModelConfig.top_p !== draftModelConfig.top_p ||
                  commitModelConfig.frequency_penalty !== draftModelConfig.frequency_penalty ||
                  commitModelConfig.presence_penalty !== draftModelConfig.presence_penalty

                // 对比工具配置
                const commitToolChoice = commitData.tool_call_config?.tool_choice || 'none'
                const draftToolChoice = draftData.tool_call_config?.tool_choice || 'none'
                const commitTools = JSON.stringify(preprocessForComparison(commitData.tools || []))
                const draftTools = JSON.stringify(preprocessForComparison(draftData.tools || []))
                hasToolChanges = commitToolChoice !== draftToolChoice || commitTools !== draftTools
              } else if (draftData && !commitData) {
                // 如果只有draft数据没有commit数据，认为都是新的变更
                hasPromptChanges = true
                hasParameterChanges = draftData.prompt_template?.variable_defs?.length > 0
                hasModelChanges = !!draftData.prompt_model_config
                hasToolChanges = !!(draftData.tool_call_config || draftData.tools?.length > 0)
              } else {
                // 如果都没有数据，无变更
                hasPromptChanges = false
                hasParameterChanges = false
                hasModelChanges = false
                hasToolChanges = false
              }

              const hasAnyChanges = hasPromptChanges || hasModelChanges || hasParameterChanges || hasToolChanges

              if (!hasAnyChanges) {
                return (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <Typography variant="h6" className="text-gray-600 font-medium mb-2">
                      {t('components.prompts.submitVersionDialog.noChanges')}
                    </Typography>
                    <Typography variant="body2" className="text-gray-500">
                      {t('components.prompts.submitVersionDialog.noChangesDescription')}
                    </Typography>
                  </div>
                )
              }

              return (
                <div className="space-y-4">
                  {/* 提示词内容差异 */}
                  {hasPromptChanges && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                            <Brain className="w-4 h-4 text-blue-600" />
                          </div>
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('components.prompts.submitVersionDialog.modifyPrompt')}
                          </Typography>
                        </div>
                        <Chip label={t('components.prompts.submitVersionDialog.modified')} size="small" className="bg-orange-100 text-orange-700 font-medium" />
                      </div>

                      <div className="space-y-3">
                        {/* 模板类型变化 */}
                        {(() => {
                          const commitTemplateType = commitData?.prompt_template?.template_type || 'normal'
                          const draftTemplateType = draftData?.prompt_template?.template_type || 'normal'
                          if (commitTemplateType !== draftTemplateType) {
                            return (
                              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                <div className="text-sm text-blue-700">
                                  <span className="font-medium">{t('components.prompts.submitVersionDialog.promptTemplate')}: </span>
                                  <span className="text-red-600">{commitTemplateType === 'normal' ? 'Normal' : 'Jinja2'}</span>
                                  <span className="mx-1">→</span>
                                  <span className="text-green-600 font-medium">{draftTemplateType === 'normal' ? 'Normal' : 'Jinja2'}</span>
                                </div>
                              </div>
                            )
                          }
                          return null
                        })()}

                        {/* Messages变化 */}
                        {(() => {
                          const commitMessages = JSON.stringify(preprocessForComparison(commitData?.prompt_template?.messages || []), null, 2)
                          const draftMessages = JSON.stringify(preprocessForComparison(draftData?.prompt_template?.messages || []), null, 2)
                          if (commitMessages !== draftMessages) {
                            return (
                              <div className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
                                <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 flex">
                                  <div className="flex-1 text-center">
                                    <Typography variant="body2" className="text-gray-700 font-medium">
                                      {latestVersion || t('components.prompts.submitVersionDialog.latestVersion')}
                                    </Typography>
                                  </div>
                                  <div className="w-px bg-gray-300 mx-2"></div>
                                  <div className="flex-1 text-center">
                                    <Typography variant="body2" className="text-gray-700 font-medium">
                                      {t('components.prompts.submitVersionDialog.draft')}
                                    </Typography>
                                  </div>
                                </div>

                                {/* GitHub风格的Split对比视图 */}
                                <DiffViewer oldContent={commitMessages} newContent={draftMessages} />
                              </div>
                            )
                          }
                          return null
                        })()}
                      </div>
                    </div>
                  )}

                  {/* 变量定义差异 */}
                  {hasParameterChanges && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center">
                            <Settings className="w-4 h-4 text-purple-600" />
                          </div>
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('components.prompts.submitVersionDialog.modifyVariables')}
                          </Typography>
                        </div>
                        <Chip label={t('components.prompts.submitVersionDialog.modified')} size="small" className="bg-orange-100 text-orange-700 font-medium" />
                      </div>

                      <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                        <div className="space-y-2">
                          {(() => {
                            const commitVariables = commitData?.prompt_template?.variable_defs || []
                            const draftVariables = draftData?.prompt_template?.variable_defs || []
                            const allVariableKeys = [...new Set([...commitVariables.map(v => v.key), ...draftVariables.map(v => v.key)])]

                            return allVariableKeys
                              .map((key, index) => {
                                const commitVar = commitVariables.find(v => v.key === key)
                                const draftVar = draftVariables.find(v => v.key === key)

                                const oldType = commitVar?.type || 'string'
                                const newType = draftVar?.type || 'string'

                                // 只显示有变化的变量
                                if (oldType === newType && commitVar && draftVar) return null

                                return (
                                  <div key={index} className="text-sm text-purple-700">
                                    {!commitVar && draftVar && (
                                      <span className="text-green-600 font-medium">
                                        {t('components.prompts.submitVersionDialog.addVariable', { key, type: newType })}
                                      </span>
                                    )}
                                    {commitVar && !draftVar && (
                                      <span className="text-red-600 font-medium">
                                        {t('components.prompts.submitVersionDialog.deleteVariable', { key, type: oldType })}
                                      </span>
                                    )}
                                    {commitVar && draftVar && (
                                      <span className="font-medium">
                                        {t('components.prompts.submitVersionDialog.modifyVariable', { key, oldType, newType })}
                                      </span>
                                    )}
                                  </div>
                                )
                              })
                              .filter(Boolean)
                          })()}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 模型配置差异 */}
                  {hasModelChanges && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                            <Cpu className="w-4 h-4 text-green-600" />
                          </div>
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('components.prompts.submitVersionDialog.modifyModel')}
                          </Typography>
                        </div>
                        <Chip label={t('components.prompts.submitVersionDialog.modified')} size="small" className="bg-orange-100 text-orange-700 font-medium" />
                      </div>

                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                        <div className="space-y-2">
                          {/* 模型名称变化 */}
                          {commitData?.prompt_model_config?.models_name !== draftData?.prompt_model_config?.models_name && (
                            <div className="text-sm text-green-700">
                              <span className="font-medium">{t('components.prompts.submitVersionDialog.modelName')}: </span>
                              <span className="text-red-600">
                                {commitData?.prompt_model_config?.models_name || t('components.prompts.submitVersionDialog.notSet')}
                              </span>
                              <span className="mx-1">→</span>
                              <span className="text-green-600 font-medium">
                                {draftData?.prompt_model_config?.models_name || t('components.prompts.submitVersionDialog.notSet')}
                              </span>
                            </div>
                          )}

                          {/* 其他模型参数变化 */}
                          {(() => {
                            const commitConfig = commitData?.prompt_model_config || {}
                            const draftConfig = draftData?.prompt_model_config || {}
                            const changedParams = []

                            // 检查各个参数的变化
                            if (commitConfig.temperature !== draftConfig.temperature) {
                              changedParams.push({ name: 'temperature', old: commitConfig.temperature, new: draftConfig.temperature })
                            }
                            if (commitConfig.max_tokens !== draftConfig.max_tokens) {
                              changedParams.push({ name: 'max_tokens', old: commitConfig.max_tokens, new: draftConfig.max_tokens })
                            }
                            if (commitConfig.top_p !== draftConfig.top_p) {
                              changedParams.push({ name: 'top_p', old: commitConfig.top_p, new: draftConfig.top_p })
                            }
                            if (commitConfig.frequency_penalty !== draftConfig.frequency_penalty) {
                              changedParams.push({ name: 'frequency_penalty', old: commitConfig.frequency_penalty, new: draftConfig.frequency_penalty })
                            }
                            if (commitConfig.presence_penalty !== draftConfig.presence_penalty) {
                              changedParams.push({ name: 'presence_penalty', old: commitConfig.presence_penalty, new: draftConfig.presence_penalty })
                            }

                            return changedParams.map((param, index) => (
                              <div key={index} className="text-sm text-green-700">
                                <span className="font-medium">{t('components.prompts.submitVersionDialog.modelParam', { name: param.name })}: </span>
                                <span className="text-red-600">{param.old ?? t('components.prompts.submitVersionDialog.notSet')}</span>
                                <span className="mx-1">→</span>
                                <span className="text-green-600 font-medium">{param.new ?? t('components.prompts.submitVersionDialog.notSet')}</span>
                              </div>
                            ))
                          })()}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 工具配置差异 */}
                  {hasToolChanges && (
                    <div className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-orange-100 rounded-full flex items-center justify-center">
                            <Settings className="w-4 h-4 text-orange-600" />
                          </div>
                          <Typography variant="subtitle1" className="text-gray-800 font-medium">
                            {t('components.prompts.submitVersionDialog.modifyTools')}
                          </Typography>
                        </div>
                        <Chip label={t('components.prompts.submitVersionDialog.modified')} size="small" className="bg-orange-100 text-orange-700 font-medium" />
                      </div>

                      <div className="space-y-3">
                        {/* tool_choice变化 */}
                        {(() => {
                          const commitToolChoice = commitData?.tool_call_config?.tool_choice || 'none'
                          const draftToolChoice = draftData?.tool_call_config?.tool_choice || 'none'
                          if (commitToolChoice !== draftToolChoice) {
                            const commitEnabled =
                              commitToolChoice === 'auto'
                                ? t('components.prompts.submitVersionDialog.enableTools')
                                : t('components.prompts.submitVersionDialog.disableTools')
                            const draftEnabled =
                              draftToolChoice === 'auto'
                                ? t('components.prompts.submitVersionDialog.enableTools')
                                : t('components.prompts.submitVersionDialog.disableTools')
                            return (
                              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                                <div className="text-sm text-orange-700">
                                  <span className="text-red-600">{commitEnabled}</span>
                                  <span className="mx-1">→</span>
                                  <span className="text-green-600 font-medium">{draftEnabled}</span>
                                </div>
                              </div>
                            )
                          }
                          return null
                        })()}

                        {/* Tools变化 */}
                        {(() => {
                          const commitTools = JSON.stringify(preprocessForComparison(commitData?.tools || []), null, 2)
                          const draftTools = JSON.stringify(preprocessForComparison(draftData?.tools || []), null, 2)
                          if (commitTools !== draftTools) {
                            return (
                              <div className="bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
                                <div className="bg-gray-100 px-4 py-2 border-b border-gray-200">
                                  <Typography variant="body2" className="text-gray-700 font-medium">
                                    {t('components.prompts.submitVersionDialog.toolsComparison')}
                                  </Typography>
                                </div>

                                {/* GitHub风格的Split对比视图 */}
                                <DiffViewer oldContent={commitTools} newContent={draftTools} />
                              </div>
                            )
                          }
                          return null
                        })()}
                      </div>
                    </div>
                  )}

                  <Alert severity="info" className="border-blue-200 bg-blue-50">
                    <Typography variant="body2" className="text-blue-800">
                      {t('components.prompts.submitVersionDialog.confirmChangesInfo')}
                    </Typography>
                  </Alert>
                </div>
              )
            })()}
          </div>
        ) : (
          // Step 2: 确认版本信息
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Typography variant="h5" className="text-gray-800 font-semibold mb-2">
                {t('components.prompts.submitVersionDialog.confirmVersionInfo')}
              </Typography>
              <Typography variant="body2" className="text-gray-600">
                {t('components.prompts.submitVersionDialog.fillVersionInfo')}
              </Typography>
            </div>

            <div className="space-y-4">
              {/* 版本号 */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <Typography variant="subtitle1" className="text-gray-800 font-medium mb-3">
                  {t('components.prompts.submitVersionDialog.versionNumber')} <span className="text-red-500">*</span>
                </Typography>
                <TextField
                  fullWidth
                  size="small"
                  value={versionNumber}
                  onChange={e => {
                    const value = e.target.value
                    setVersionNumber(value)

                    // 先验证格式
                    const formatError = validateVersionNumber(value)
                    if (formatError) {
                      setVersionNumberError(formatError)
                      return
                    }

                    // 如果格式正确，检查版本号是否小于等于当前版本号
                    if (latestVersion && value.trim()) {
                      const comparison = compareVersions(value, latestVersion)
                      if (comparison <= 0) {
                        setVersionNumberError(t('components.prompts.submitVersionDialog.versionNumberMustBeGreater'))
                        return
                      }
                    }

                    // 没有错误
                    setVersionNumberError('')
                  }}
                  inputProps={{ maxLength: 50 }}
                  placeholder={t('components.prompts.submitVersionDialog.versionNumberPlaceholder')}
                  className="bg-white/80"
                  error={!!versionNumberError}
                  helperText={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{versionNumberError || t('components.prompts.submitVersionDialog.versionNumberFormat')}</span>
                      <span style={{ color: versionNumber.length >= 50 ? '#f56565' : '#6b7280' }}>{versionNumber.length}/50</span>
                    </div>
                  }
                />
              </div>

              {/* 版本描述 */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <Typography variant="subtitle1" className="text-gray-800 font-medium mb-3">
                  {t('components.prompts.submitVersionDialog.versionDescription')}
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={versionDescription}
                  onChange={e => setVersionDescription(e.target.value)}
                  inputProps={{ maxLength: 200 }}
                  placeholder={t('components.prompts.submitVersionDialog.versionDescriptionPlaceholder')}
                  className="bg-white/80"
                  size="small"
                  helperText={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{t('components.prompts.submitVersionDialog.versionDescriptionHelper')}</span>
                      <span style={{ color: versionDescription.length >= 200 ? '#f56565' : '#6b7280' }}>{versionDescription.length}/200</span>
                    </div>
                  }
                />
              </div>

              <Alert severity="info" className="border-blue-200 bg-blue-50">
                <Typography variant="body2" className="text-blue-800">
                  {t('components.prompts.submitVersionDialog.versionInfoHelp')}
                </Typography>
              </Alert>
            </div>
          </div>
        )}
      </DialogContent>

      <DialogActions className="p-6 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-2">
            {submitVersionStep === 1 && promptCommitData && (
              <Button
                onClick={onPrevStep}
                variant="contained"
                startIcon={<ArrowLeft className="w-4 h-4" />}
                className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-sm"
              >
                {t('components.prompts.submitVersionDialog.previous')}
              </Button>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {submitVersionStep === 0 ? (
              (() => {
                // 检查是否有变更
                const commitData = promptCommitData
                const draftData = promptDraftData

                let hasAnyChanges = false
                if (commitData && draftData) {
                  const commitTemplateType = commitData.prompt_template?.template_type || 'normal'
                  const draftTemplateType = draftData.prompt_template?.template_type || 'normal'
                  const commitMessages = JSON.stringify(preprocessForComparison(commitData.prompt_template?.messages || []))
                  const draftMessages = JSON.stringify(preprocessForComparison(draftData.prompt_template?.messages || []))
                  const hasPromptChanges = commitTemplateType !== draftTemplateType || commitMessages !== draftMessages

                  const commitVariables = commitData.prompt_template?.variable_defs || []
                  const draftVariables = draftData.prompt_template?.variable_defs || []
                  const hasParameterChanges =
                    draftVariables.some(draftParam => {
                      const commitParam = commitVariables.find(v => v.key === draftParam.key)
                      return !commitParam || commitParam.type !== draftParam.type
                    }) ||
                    commitVariables.some(commitParam => {
                      const draftParam = draftVariables.find(p => p.key === commitParam.key)
                      return !draftParam
                    })

                  const commitModelConfig = commitData.prompt_model_config || {}
                  const draftModelConfig = draftData.prompt_model_config || {}
                  const hasModelChanges =
                    commitModelConfig.models_name !== draftModelConfig.models_name ||
                    commitModelConfig.models_id !== draftModelConfig.models_id ||
                    commitModelConfig.temperature !== draftModelConfig.temperature ||
                    commitModelConfig.max_tokens !== draftModelConfig.max_tokens ||
                    commitModelConfig.top_p !== draftModelConfig.top_p ||
                    commitModelConfig.frequency_penalty !== draftModelConfig.frequency_penalty ||
                    commitModelConfig.presence_penalty !== draftModelConfig.presence_penalty

                  const commitToolChoice = commitData.tool_call_config?.tool_choice || 'none'
                  const draftToolChoice = draftData.tool_call_config?.tool_choice || 'none'
                  const commitTools = JSON.stringify(preprocessForComparison(commitData.tools || []))
                  const draftTools = JSON.stringify(preprocessForComparison(draftData.tools || []))
                  const hasToolChanges = commitToolChoice !== draftToolChoice || commitTools !== draftTools

                  hasAnyChanges = hasPromptChanges || hasParameterChanges || hasModelChanges || hasToolChanges
                } else if (draftData && !commitData) {
                  hasAnyChanges = true
                }

                if (!hasAnyChanges) {
                  return (
                    <Button variant="outlined" disabled className="border-gray-300 text-gray-500 cursor-not-allowed">
                      {t('components.prompts.submitVersionDialog.noNeedToSubmit')}
                    </Button>
                  )
                }

                return (
                  <Button
                    onClick={onNextStep}
                    variant="contained"
                    endIcon={<ArrowLeft className="w-4 h-4 rotate-180" />}
                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-sm"
                  >
                    {t('components.prompts.submitVersionDialog.next')}
                  </Button>
                )
              })()
            ) : (
              <Button
                onClick={onConfirmSubmit}
                variant="contained"
                startIcon={<Save className="w-4 h-4" />}
                disabled={!!versionNumberError || !versionNumber.trim()}
                className={`shadow-sm ${
                  !!versionNumberError || !versionNumber.trim()
                    ? 'bg-gray-400 hover:bg-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700'
                }`}
              >
                {t('components.prompts.submitVersionDialog.confirmSubmit')}
              </Button>
            )}
          </div>
        </div>
      </DialogActions>
    </Dialog>
  )
}

export default SubmitVersionDialog
