/**
 * Model Config Tab Component
 * 模型配置标签页组件
 * 包含基础配置（通用模型）和高级配置（生成大纲、信息选择、报告撰写）
 */

import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Info, Play, Loader2, X } from 'lucide-react'
import { Button, Dialog, DialogContent, DialogTitle, DialogActions, TextField, Chip, Typography, Box } from '@mui/material'
import { useTestModel } from '@test-agentstudio/api-client'
import { ConfigTabProps } from '../ConfigRegistry'
import { ConfigSection } from '../ConfigSection'
import { ModelSelector } from '@/components/Prompts'
import type { PromptModel } from '@test-agentstudio/api-client'

// 从父组件传入的控件组件
export interface ModelConfigTabProps extends ConfigTabProps {
  /** 可用模型列表 */
  availableModels: PromptModel[]
  /** 模型加载状态 */
  modelsLoading: boolean
  /** 空间 ID */
  spaceId: string
}

// 模型配置项类型
interface ModelConfigItem {
  id: string
  labelKey: string
  descKey: string
  recommendationKey: string
  configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId'
}

/**
 * 模型配置项组件
 */
const ModelConfigItem: React.FC<{
  label: string
  description: string
  recommendation?: string
  availableModels: PromptModel[]
  selectedModel: PromptModel | null
  modelsLoading: boolean
  onModelChange: (model: PromptModel | null) => void
  onClear?: () => void
  placeholder?: string
  required?: boolean
  onOpenTestDialog: (model: PromptModel) => void
}> = ({
  label,
  description,
  recommendation,
  availableModels,
  selectedModel,
  modelsLoading,
  onModelChange,
  onClear,
  placeholder,
  required = false,
  onOpenTestDialog,
}) => {
  // 清空处理：只调用 onClear 回调，由父组件负责更新配置
  const handleClear = React.useCallback(() => {
    onClear?.()
  }, [onClear])

  return (
    <div className="flex items-center gap-4 py-1">
      <div className="flex-shrink-0 w-[300px]">
        <span className="text-sm text-gray-900 font-medium">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </span>
        {description && (
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        )}
        {recommendation && (
          <p className="text-xs text-gray-500 mt-1">{recommendation}</p>
        )}
      </div>
      <div className="flex-1 min-w-[240px]">
        <ModelSelector
          availableModels={availableModels}
          selectedModel={selectedModel}
          onModelChange={onModelChange}
          onClear={handleClear}
          modelsLoading={modelsLoading}
          placeholder={placeholder}
          className="bg-white rounded-lg"
          onOpenTestDialog={onOpenTestDialog}
        />
      </div>
    </div>
  )
}

/**
 * 模型配置标签组件
 */
export const ModelConfigTab: React.FC<ModelConfigTabProps> = ({
  config,
  updateConfig,
  availableModels,
  modelsLoading,
  spaceId,
}) => {
  const { t } = useTranslation()
  const { mutateAsync: testModel } = useTestModel()

  // 测试对话框相关状态
  const [showTestDialog, setShowTestDialog] = useState(false)
  const [testingModel, setTestingModel] = useState<PromptModel | null>(null)
  const [testPrompt, setTestPrompt] = useState('你好，请介绍一下你自己')
  const [testResult, setTestResult] = useState('')
  const [isTesting, setIsTesting] = useState(false)
  const testGenerationRef = useRef(0)

  // 高级模型配置项
  const advancedModelConfigs: ModelConfigItem[] = [
    {
      id: 'outline',
      labelKey: 'apps.config.model.outline.label',
      descKey: 'apps.config.model.outline.description',
      recommendationKey: 'apps.config.model.outline.recommendation',
      configKey: 'planUnderstandingModelId',
    },
    {
      id: 'infoCollecting',
      labelKey: 'apps.config.model.infoCollecting.label',
      descKey: 'apps.config.model.infoCollecting.description',
      recommendationKey: 'apps.config.model.infoCollecting.recommendation',
      configKey: 'infoCollectingModelId',
    },
    {
      id: 'reportWriting',
      labelKey: 'apps.config.model.reportWriting.label',
      descKey: 'apps.config.model.reportWriting.description',
      recommendationKey: 'apps.config.model.reportWriting.recommendation',
      configKey: 'writingCheckingModelId',
    },
  ]

  // 根据模型 ID 获取模型对象
  const getModelById = (modelId: string | undefined): PromptModel | null => {
    if (!modelId) return null
    return availableModels.find(
      m => m.openModel.model_id === modelId
    ) || null
  }

  // 打开测试对话框
  const handleOpenTestDialog = (model: PromptModel) => {
    setTestingModel(model)
    setTestPrompt('你好，请介绍一下你自己')
    setTestResult('')
    setShowTestDialog(true)
  }

  // 关闭测试对话框
  const handleCloseTestDialog = () => {
    setShowTestDialog(false)
    setTestingModel(null)
    setTestPrompt('')
    setTestResult('')
  }

  // 执行测试
  const handleTestModel = async () => {
    if (!testPrompt.trim() || !testingModel) return
    if (testPrompt.length > 1000) return

    testGenerationRef.current += 1
    const currentGeneration = testGenerationRef.current
    const currentModelId = testingModel.openModel.model_id

    setIsTesting(true)

    try {
      const result = await testModel({
        id: currentModelId,
        prompt: testPrompt,
        spaceId,
        parameters: {
          temperature: 0.7,
          top_p: 0.9,
          max_tokens: 100,
        },
      })

      // 检查是否是当前最新的测试请求
      if (currentGeneration === testGenerationRef.current && showTestDialog) {
        if (result.success) {
          setTestResult(
            `${t('models.testSuccess')}\n${t('models.modelName')}: ${testingModel.openModel.name}\n${t('models.promptText')}: ${testPrompt}\n\n${t('models.testResponse')}: ${result.response || t('models.testCompletion')}\n\n${t('models.averageResponseTime')}: ${result.latency.toFixed(3)}s`,
          )
        } else {
          setTestResult(`${t('models.testFailed')}: ${result.error || t('models.unknownError')}\n${t('models.modelName')}: ${testingModel.openModel.name}\n${t('models.promptText')}: ${testPrompt}`)
        }
      }
    } catch (error: any) {
      let errorMessage = t('models.testFailed')

      // 尝试获取详细错误信息
      let detailData = null
      if (error?.response?.data?.detail) {
        detailData = error.response.data.detail
      } else if (error?.data?.detail) {
        detailData = error.data.detail
      } else if ((error as any)?.detail) {
        detailData = (error as any).detail
      }

      if (detailData) {
        if (typeof detailData === 'string') {
          errorMessage = detailData
        } else {
          errorMessage = JSON.stringify(detailData)
        }
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error?.message) {
        errorMessage = error.message
      }

      if (currentGeneration === testGenerationRef.current && showTestDialog) {
        setTestResult(`${t('models.testFailed')}: ${errorMessage}\n${t('models.modelName')}: ${testingModel.openModel.name}\n${t('models.promptText')}: ${testPrompt}`)
      }
    } finally {
      // 直接设置为 false，无需检查旧值
      setIsTesting(false)
    }
  }

  // 处理通用模型选择变更
  const handleGeneralModelChange = (model: PromptModel | null) => {
    const modelId = model?.openModel.model_id
    updateConfig('generalModelId', modelId)
  }

  // 处理通用模型清空
  const handleGeneralModelClear = () => {
    updateConfig('generalModelId', undefined)
  }

  // 处理高级模型选择变更
  const handleModelChange = (
    configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId',
    model: PromptModel | null
  ) => {
    updateConfig(configKey, model?.openModel.model_id)
  }

  // 处理高级模型清空
  const handleModelClear = (
    configKey: 'planUnderstandingModelId' | 'infoCollectingModelId' | 'writingCheckingModelId'
  ) => {
    updateConfig(configKey, undefined)
  }

  return (
    <>
      <div className="space-y-8">
        {/* 基础配置 */}
        <ConfigSection title={t('apps.config.model.general.title')}>
          <div className="space-y-4">
            <ModelConfigItem
              label={t('apps.config.model.general.label')}
              description={t('apps.config.model.general.description')}
              availableModels={availableModels}
              selectedModel={getModelById(config.generalModelId)}
              modelsLoading={modelsLoading}
              onModelChange={handleGeneralModelChange}
              onClear={handleGeneralModelClear}
              placeholder={t('apps.config.model.useGeneral')}
              required={true}
              spaceId={spaceId}
              onOpenTestDialog={handleOpenTestDialog}
            />
          </div>
        </ConfigSection>

        {/* 高级配置 */}
        <ConfigSection title={t('apps.config.model.advanced.title')}>
          {/* 提示信息横幅 */}
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">
              {t('apps.config.model.advanced.info')}
            </p>
          </div>

          {/* 高级配置项 */}
          <div className="space-y-4">
            {advancedModelConfigs.map((modelConfig) => (
              <ModelConfigItem
                key={modelConfig.id}
                label={t(modelConfig.labelKey)}
                description={t(modelConfig.descKey)}
                recommendation={t(modelConfig.recommendationKey)}
                availableModels={availableModels}
                selectedModel={getModelById(config[modelConfig.configKey])}
                modelsLoading={modelsLoading}
                onModelChange={(model) => handleModelChange(modelConfig.configKey, model)}
                onClear={() => handleModelClear(modelConfig.configKey)}
                placeholder={t('apps.config.model.useGeneral')}
                spaceId={spaceId}
                onOpenTestDialog={handleOpenTestDialog}
              />
            ))}
          </div>
        </ConfigSection>
      </div>

      {/* 测试模型对话框 */}
      <Dialog
        open={showTestDialog}
        onClose={handleCloseTestDialog}
        maxWidth="md"
        fullWidth
        PaperProps={{
          className: 'rounded-2xl shadow-2xl border border-gray-100',
        }}
        disableRestoreFocus
      >
        <DialogTitle className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <Play className="w-4 h-4 text-white" />
              </div>
              <Typography variant="h6" className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">
                {t('models.testModel')}: {testingModel?.openModel.name}
              </Typography>
            </div>
            <Button
              onClick={handleCloseTestDialog}
              disabled={isTesting}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </DialogTitle>
        <DialogContent>
          <div className="space-y-4 pt-4">
            {/* 常用语句 */}
            <div>
              <Typography variant="subtitle2" className="text-gray-700 mb-2 font-medium">
                {t('models.commonTestPrompts')}
              </Typography>
              <div className="flex flex-wrap gap-2 mb-3">
                <Chip
                  label={t('models.introducePrompt')}
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt(t('models.introducePrompt'))}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
                <Chip
                  label={t('models.aiConceptsPrompt')}
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt(t('models.aiConceptsPrompt'))}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
                <Chip
                  label="Hello World"
                  variant="outlined"
                  size="small"
                  onClick={() => setTestPrompt('Hello World')}
                  disabled={isTesting}
                  className={`${isTesting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-blue-50 hover:border-blue-300'}`}
                />
              </div>
            </div>

            <TextField
              fullWidth
              multiline
              rows={4}
              label={t('models.testPrompt')}
              value={testPrompt}
              onChange={e => setTestPrompt(e.target.value)}
              placeholder={t('models.testPrompt')}
              disabled={isTesting}
              helperText={
                testPrompt.length > 1000 ? t('models.promptLimit', { length: testPrompt.length }) : t('models.promptLength', { length: testPrompt.length })
              }
              error={testPrompt.length > 1000}
            />

            <div className="flex space-x-3">
              <Button
                variant="contained"
                startIcon={isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                onClick={handleTestModel}
                disabled={isTesting || !testPrompt.trim()}
                className={`px-6 py-2 rounded-lg font-semibold transition-all duration-300 shadow-lg ${
                  isTesting || !testPrompt.trim()
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white hover:scale-105 hover:shadow-xl'
                }`}
              >
                {isTesting ? t('models.testing') : t('models.startTest')}
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setTestPrompt('')
                  setTestResult('')
                }}
                disabled={isTesting}
                className="px-4 py-2 rounded-lg transition-all duration-200"
              >
                {t('models.reset')}
              </Button>
            </div>

            {testResult && (
              <div>
                <Typography variant="h6" className="mb-2 font-bold">
                  {t('models.testResult')}
                </Typography>
                <Box className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-blue-200 p-4">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono bg-white p-3 rounded-lg border border-gray-200">{testResult}</pre>
                </Box>
              </div>
            )}
          </div>
        </DialogContent>
        <DialogActions className="bg-gray-50 px-6 py-4">
          <Button
            onClick={handleCloseTestDialog}
            className="text-gray-600 hover:text-gray-700 hover:bg-gray-100 px-4 py-2 rounded-lg transition-all duration-200"
          >
            {t('models.close')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default ModelConfigTab
