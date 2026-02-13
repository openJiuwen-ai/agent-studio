import React, { useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Chip,
  Paper,
  IconButton,
  FormControlLabel,
  TextField,
  Button,
  FormControl,
  Select,
  MenuItem,
  Alert,
  RadioGroup,
  Radio,
} from '@mui/material'
import { Settings, Cpu, Code, Copy, Edit, Trash2, Plus, ChevronRight, ChevronDown, X } from 'lucide-react'
import JsonEditor from './JsonEditor'
import ModelSelector from './ModelSelector'
import ModelParameterEditor from './ModelParameterEditor'
import ConditionalTooltip from './ConditionalTooltip'
import ToolSettingsPanel from './ToolSettingsPanel'
import { ModelConfig, Tool, Model, PromptParameter as Parameter } from '@/types/promptType'

export interface AdvancedConfigEditorProps {
  // 标签页状态
  activeTab: number
  onTabChange: (event: React.SyntheticEvent, newValue: number) => void
  readOnly?: boolean

  // 变量定义相关
  parameters: Parameter[]
  templateEngine: 'normal' | 'jinja2'
  onParametersChange: (parameters: Parameter[]) => void
  onParameterChange: (paramName: string, value: string) => void
  onParameterBlur?: (paramName: string, value: string) => void
  onCopyToClipboard: (content: string) => Promise<void>
  onEditVariable: (index: number) => void
  onDeleteVariable: (index: number) => void
  onAddVariable?: () => void
  editingParamId?: string | null
  onEditingParamIdChange?: (id: string | null) => void

  // 模型设置相关
  availableModels: Model[]
  selectedModel: Model | null
  modelConfig: ModelConfig
  onModelChange: (model: Model | null) => void
  onModelConfigChange: (config: ModelConfig) => void
  modelsLoading: boolean

  // 工具设置相关
  tools: Tool[]
  toolsEnabled: boolean
  onToolsChange: (tools: Tool[]) => void
  onToolsEnabledChange: (enabled: boolean) => void
  onAddTool: () => void
  onEditTool: (tool: Tool) => void
  onDeleteTool: (toolId: string) => void

  // 其他回调
  onHasUnsavedChanges: (hasChanges: boolean) => void
  onTriggerAutoSave: (data?: any) => void

  // 控制是否启用自动保存（主页面启用，对比模式不启用）
  enableAutoSave?: boolean
}

const AdvancedConfigEditor: React.FC<AdvancedConfigEditorProps> = ({
  activeTab,
  onTabChange,
  parameters,
  templateEngine,
  onParametersChange,
  onParameterChange,
  onParameterBlur,
  onCopyToClipboard,
  onEditVariable,
  onDeleteVariable,
  onAddVariable,
  editingParamId,
  onEditingParamIdChange,
  availableModels,
  selectedModel,
  modelConfig,
  onModelChange,
  onModelConfigChange,
  modelsLoading,
  tools,
  toolsEnabled,
  onToolsChange,
  onToolsEnabledChange,
  onAddTool,
  onEditTool,
  onDeleteTool,
  onHasUnsavedChanges,
  onTriggerAutoSave,
  enableAutoSave = false,
  readOnly = false,
}) => {
  const { t } = useTranslation()
  const isReadOnly = !!readOnly

  // 变量值/消息内容本地编辑，防抖同步到父组件，减少输入卡顿与 triggerAutoSave 频繁触发
  const PARAM_DEBOUNCE_MS = 300
  const [localEdits, setLocalEdits] = React.useState<Record<string, string>>({})
  const localEditsRef = useRef<Record<string, string>>({})
  const paramDebounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  localEditsRef.current = localEdits

  const buildMergedParameters = useCallback(
    (params: Parameter[], edits: Record<string, string>): Parameter[] => {
      return params.map(param => {
        const valueKey = `value_${param.name}`
        const value = edits[valueKey] !== undefined ? edits[valueKey] : param.value
        if (param.type === 'placeholder' && param.messages) {
          const messages = param.messages.map((msg, msgIndex) => {
            const msgKey = `msg_${param.name}_${msgIndex}`
            const content = edits[msgKey] !== undefined ? edits[msgKey] : msg.content
            return { ...msg, content }
          })
          return { ...param, value, messages }
        }
        return { ...param, value }
      })
    },
    [],
  )

  const flushLocalEdits = useCallback(() => {
    if (paramDebounceTimerRef.current) {
      clearTimeout(paramDebounceTimerRef.current)
      paramDebounceTimerRef.current = null
    }
    const edits = localEditsRef.current
    if (Object.keys(edits).length === 0) return
    const merged = buildMergedParameters(parameters, edits)
    onParametersChange(merged)
    setLocalEdits({})
  }, [parameters, onParametersChange, buildMergedParameters])

  const scheduleFlush = useCallback(() => {
    if (paramDebounceTimerRef.current) clearTimeout(paramDebounceTimerRef.current)
    paramDebounceTimerRef.current = setTimeout(flushLocalEdits, PARAM_DEBOUNCE_MS)
  }, [flushLocalEdits])

  useEffect(() => {
    setLocalEdits({})
  }, [parameters])

  useEffect(() => {
    return () => {
      if (paramDebounceTimerRef.current) clearTimeout(paramDebounceTimerRef.current)
    }
  }, [])

  // 变量展开收起状态管理，默认展开
  const [variableExpanded, setVariableExpanded] = React.useState<{ [key: string]: boolean }>({})
  
  // 提示框显示状态管理
  const [showHint, setShowHint] = React.useState(true)
  
  // 模型设置提示框显示状态管理
  const [showModelHint, setShowModelHint] = React.useState(true)
  
  // 响应式计算变量定义区域的最大高度（包含变量列表和底部提示）
  const [variableTabMaxHeight, setVariableTabMaxHeight] = React.useState('calc(100vh - 350px)')
  
  // 响应式计算模型设置区域的最大高度
  const [modelSettingsMaxHeight, setModelSettingsMaxHeight] = React.useState('calc(100vh - 425px)')

  React.useEffect(() => {
    const updateMaxHeight = () => {
      if (window.innerWidth < 640) {
        // 小屏幕：手机等移动设备
        setVariableTabMaxHeight('calc(100vh - 320px)')
        setModelSettingsMaxHeight('calc(100vh - 320px)')
      } else if (window.innerWidth < 2000) {
        // 中等屏幕：平板、14寸笔记本等
        setVariableTabMaxHeight('calc(100vh - 260px)')
        setModelSettingsMaxHeight('calc(100vh - 260px)')
      } else {
        // 大屏幕：15寸以上笔记本、台式显示器
        setVariableTabMaxHeight('calc(100vh - 380px)')
        setModelSettingsMaxHeight('calc(100vh - 425px)')
      }
    }

    updateMaxHeight()
    window.addEventListener('resize', updateMaxHeight)
    return () => window.removeEventListener('resize', updateMaxHeight)
  }, [])

  // 切换变量展开收起状态
  const toggleVariableExpanded = (paramName: string) => {
    if (isReadOnly) {
      return
    }
    setVariableExpanded(prev => ({
      ...prev,
      [paramName]: prev[paramName] === false ? true : false,
    }))
  }

  // 辅助函数：处理模型选择变更
  const handleModelChange = (model: Model | null) => {
    if (isReadOnly) {
      return
    }
    onModelChange(model)
    if (enableAutoSave) {
      onHasUnsavedChanges(true)
    }
  }

  // 辅助函数：处理模型配置变更
  const handleModelConfigChange = (newConfig: ModelConfig) => {
    if (isReadOnly) {
      return
    }
    onModelConfigChange(newConfig)
    if (enableAutoSave) {
      onHasUnsavedChanges(true)
    }
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* 标签页导航 */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={activeTab}
          onChange={(event, newValue) => {
            if (isReadOnly) {
              return
            }
            onTabChange(event, newValue)
          }}
          aria-label={t('components.prompts.advancedConfigEditor.tabs.ariaLabel')}
          className="bg-white/60 rounded-t-lg"
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            minHeight: 'clamp(2rem, 5.5vh, 2.75rem)',
            height: 'clamp(2rem, 5.5vh, 2.75rem)',
            '& .MuiTabs-flexContainer': {
              height: '100%',
            },
            '& .MuiTab-root': {
              fontSize: 'clamp(0.625rem, 1.5vw, 0.8125rem)',
              padding: 'clamp(0.3rem, 1vw, 0.6rem) clamp(0.375rem, 1.5vw, 0.75rem)',
              minHeight: 'clamp(2rem, 5.5vh, 2.75rem)',
            },
          }}
        >
          <Tab
            disabled={isReadOnly}
            label={
              <div className="flex items-center" style={{ gap: 'clamp(0.25rem, 0.5vw, 0.375rem)' }}>
                <Settings style={{ width: 'clamp(0.625rem, 1.5vw, 0.875rem)', height: 'clamp(0.625rem, 1.5vw, 0.875rem)' }} />
                <span>{t('components.prompts.advancedConfigEditor.tabs.variableDefinition')}</span>
                <Chip 
                  label={parameters.length} 
                  size="small" 
                  className="bg-blue-100 text-blue-700"
                  sx={{ 
                    fontSize: 'clamp(0.5rem, 1.2vw, 0.6875rem)',
                    height: 'clamp(0.875rem, 2vh, 1.125rem)',
                  }}
                />
              </div>
            }
          />
          <Tab
            disabled={isReadOnly}
            label={
              <div className="flex items-center" style={{ gap: 'clamp(0.25rem, 0.5vw, 0.375rem)' }}>
                <Cpu style={{ width: 'clamp(0.625rem, 1.5vw, 0.875rem)', height: 'clamp(0.625rem, 1.5vw, 0.875rem)' }} />
                <span>{t('components.prompts.advancedConfigEditor.tabs.modelSettings')}</span>
              </div>
            }
          />
          <Tab
            disabled={isReadOnly}
            label={
              <div className="flex items-center" style={{ gap: 'clamp(0.25rem, 0.5vw, 0.375rem)' }}>
                <Code style={{ width: 'clamp(0.625rem, 1.5vw, 0.875rem)', height: 'clamp(0.625rem, 1.5vw, 0.875rem)' }} />
                <span>{t('components.prompts.advancedConfigEditor.tabs.toolSettings')}</span>
                <Chip 
                  label={tools.length} 
                  size="small" 
                  className="bg-blue-100 text-blue-700"
                  sx={{ 
                    fontSize: 'clamp(0.5rem, 1.2vw, 0.6875rem)',
                    height: 'clamp(0.875rem, 2vh, 1.125rem)',
                  }}
                />
              </div>
            }
          />
        </Tabs>
      </Box>

      {/* 变量定义标签页 */}
      <div role="tabpanel" hidden={activeTab !== 0} className="flex-1 flex-col" style={{ padding: 'clamp(0.25rem, 1vw, 1rem)' }}>
        {activeTab === 0 && (
          <div 
            className="flex-1 flex flex-col overflow-y-auto scrollbar-hide" 
            style={{ 
              gap: 'clamp(0.25rem, 1vh, 1rem)',
              maxHeight: variableTabMaxHeight
            }}
          >
            <div 
              className="flex-1" 
              style={{ 
                gap: 'clamp(0.2rem, 0.75vh, 0.75rem)', 
                display: 'flex', 
                flexDirection: 'column'
              }}
            >
              {parameters.length > 0 ? (
                parameters.map((param, index) => (
                  <Paper 
                    key={index} 
                    elevation={1} 
                    className="bg-white/80 border border-green-200"
                    sx={{ padding: 'clamp(0.1rem, 0.5vw, 0.35rem)' }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.1rem, 0.3vh, 0.3rem)' }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center" style={{ gap: 'clamp(0.15rem, 0.5vw, 0.5rem)' }}>
                          <div 
                            className="bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg flex items-center justify-center"
                            style={{
                              width: 'clamp(0.75rem, 2vw, 1.25rem)',
                              height: 'clamp(0.75rem, 2vw, 1.25rem)',
                            }}
                          >
                            <span className="text-white font-bold" style={{ fontSize: 'clamp(0.4rem, 1.2vw, 0.75rem)' }}>{index + 1}</span>
                          </div>
                          <div className="min-w-0 flex-1">
                            <ConditionalTooltip title={param.name}>
                              <Typography 
                                variant="subtitle2" 
                                className="text-gray-800 font-medium truncate" 
                                sx={{ 
                                  maxWidth: '200px',
                                  fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                }}
                              >
                                {param.name}
                              </Typography>
                            </ConditionalTooltip>
                          </div>
                          <IconButton
                            size="small"
                            disabled={isReadOnly}
                            onClick={() => toggleVariableExpanded(param.name)}
                            className="text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                            title={
                              variableExpanded[param.name] === undefined || variableExpanded[param.name] === true
                                ? t('components.prompts.advancedConfigEditor.variable.collapse')
                                : t('components.prompts.advancedConfigEditor.variable.expand')
                            }
                            sx={{
                              width: 'clamp(1rem, 2.5vw, 2rem)',
                              height: 'clamp(1rem, 2.5vw, 2rem)',
                            }}
                          >
                            {variableExpanded[param.name] === undefined || variableExpanded[param.name] === true ? (
                              <ChevronDown style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />
                            ) : (
                              <ChevronRight style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />
                            )}
                          </IconButton>
                        </div>
                        <div className="flex items-center" style={{ gap: 'clamp(0.05rem, 0.25vw, 0.5rem)' }}>
                          {templateEngine === 'normal' && (
                            <Chip
                              label={param.type === 'placeholder' ? 'Placeholder' : t('components.prompts.advancedConfigEditor.variable.autoGenerated')}
                              size="small"
                              className={param.type === 'placeholder' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}
                              sx={{ 
                                fontSize: 'clamp(0.4rem, 1.2vw, 0.75rem)',
                                height: 'clamp(0.75rem, 2vh, 1.25rem)',
                              }}
                            />
                          )}
                          {templateEngine === 'jinja2' && param.type === 'placeholder' && (
                            <Chip 
                              label="Placeholder" 
                              size="small" 
                              className="bg-purple-100 text-purple-700"
                              sx={{ 
                                fontSize: 'clamp(0.4rem, 1.2vw, 0.75rem)',
                                height: 'clamp(0.75rem, 2vh, 1.25rem)',
                              }}
                            />
                          )}
                          {templateEngine === 'jinja2' && param.dataType && param.type !== 'placeholder' && (
                            <Chip 
                              label={param.dataType} 
                              size="small" 
                              color="primary" 
                              variant="outlined"
                              sx={{ 
                                fontSize: 'clamp(0.4rem, 1.2vw, 0.75rem)',
                                height: 'clamp(0.75rem, 2vh, 1.25rem)',
                              }}
                            />
                          )}
                          <IconButton
                            size="small"
                            disabled={isReadOnly}
                            onClick={async () => {
                              if (isReadOnly) {
                                return
                              }
                              try {
                                await onCopyToClipboard(param.value)
                              } catch (error) {
                                console.error('复制失败:', error)
                              }
                            }}
                            className="text-blue-500 hover:bg-blue-50"
                            title={t('components.prompts.advancedConfigEditor.variable.copyVariableValue')}
                            sx={{
                              width: 'clamp(1rem, 2.5vw, 2rem)',
                              height: 'clamp(1rem, 2.5vw, 2rem)',
                            }}
                          >
                            <Copy style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />
                          </IconButton>
                          {templateEngine === 'jinja2' && (
                            <>
                              {/* placeholder类型变量不显示编辑按钮 */}
                              {param.type !== 'placeholder' && (
                                <IconButton
                                  size="small"
                                  disabled={isReadOnly}
                                  onClick={() => {
                                    if (isReadOnly) {
                                      return
                                    }
                                    onEditVariable(index)
                                  }}
                                  className="text-green-500 hover:bg-green-50"
                                  title={t('components.prompts.advancedConfigEditor.variable.editVariable')}
                                  sx={{
                                    width: 'clamp(1rem, 2.5vw, 2rem)',
                                    height: 'clamp(1rem, 2.5vw, 2rem)',
                                  }}
                                >
                                  <Edit style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />
                                </IconButton>
                              )}
                              <IconButton
                                size="small"
                                disabled={isReadOnly}
                                onClick={() => {
                                  if (isReadOnly) {
                                    return
                                  }
                                  onDeleteVariable(index)
                                }}
                                className="text-red-500 hover:bg-red-50"
                                title={t('components.prompts.advancedConfigEditor.variable.deleteVariable')}
                                sx={{
                                  width: 'clamp(1rem, 2.5vw, 2rem)',
                                  height: 'clamp(1rem, 2.5vw, 2rem)',
                                }}
                              >
                                <Trash2 style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />
                              </IconButton>
                            </>
                          )}
                        </div>
                      </div>

                      {(variableExpanded[param.name] === undefined || variableExpanded[param.name] === true) && (
                        <div>
                          {param.type === 'placeholder' ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.25rem, 1vh, 0.75rem)' }}>
                              <Typography 
                                variant="caption" 
                                className="text-gray-600"
                                sx={{ fontSize: 'clamp(0.5rem, 1.3vw, 0.75rem)' }}
                              >
                                {t('components.prompts.advancedConfigEditor.variable.configurePlaceholderMessages')}
                              </Typography>

                              {/* Placeholder消息列表 */}
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.25rem, 1vh, 0.75rem)' }}>
                                {param.messages?.map((msg, msgIndex) => {
                                  const getRoleStyles = (role: string) => {
                                    switch (role) {
                                      case 'system':
                                        return {
                                          bg: 'from-blue-500 to-cyan-500',
                                          text: 'text-blue-700',
                                          border: 'border-blue-200',
                                          lightBg: 'bg-blue-50',
                                        }
                                      case 'user':
                                        return {
                                          bg: 'from-purple-500 to-indigo-500',
                                          text: 'text-purple-700',
                                          border: 'border-purple-200',
                                          lightBg: 'bg-purple-50',
                                        }
                                      case 'assistant':
                                        return {
                                          bg: 'from-orange-500 to-red-500',
                                          text: 'text-orange-700',
                                          border: 'border-orange-200',
                                          lightBg: 'bg-orange-50',
                                        }
                                      default:
                                        return {
                                          bg: 'from-gray-500 to-gray-600',
                                          text: 'text-gray-700',
                                          border: 'border-gray-200',
                                          lightBg: 'bg-gray-50',
                                        }
                                    }
                                  }

                                  const roleStyles = getRoleStyles(msg.role)

                                  return (
                                    <div
                                      key={msg.id}
                                      className={`bg-white/80 border ${roleStyles.border} rounded-lg shadow-sm hover:shadow-sm transition-shadow`}
                                      style={{ padding: 'clamp(0.2rem, 0.75vw, 0.5rem)' }}
                                    >
                                      <div className="flex items-center justify-between" style={{ marginBottom: 'clamp(0.2rem, 0.75vh, 0.5rem)' }}>
                                        <div className="flex items-center" style={{ gap: 'clamp(0.2rem, 0.75vw, 0.5rem)' }}>
                                          <FormControl 
                                            size="small" 
                                            disabled={isReadOnly}
                                            sx={{ minWidth: 'clamp(60px, 12vw, 100px)' }}
                                          >
                                            <Select
                                              value={msg.role}
                                              onChange={e => {
                                                if (isReadOnly) {
                                                  return
                                                }
                                                const newParams = [...parameters]
                                                if (newParams[index].messages) {
                                                  newParams[index].messages![msgIndex].role = e.target.value as any
                                                  onParametersChange(newParams)
                                                }
                                              }}
                                              disabled={isReadOnly}
                                              renderValue={value => {
                                                const roleLabels: Record<string, string> = {
                                                  system: 'System',
                                                  user: 'User',
                                                  assistant: 'Assistant',
                                                }
                                                return roleLabels[value] || value
                                              }}
                                              className={`${roleStyles.lightBg} ${roleStyles.text} font-medium`}
                                              sx={{
                                                '& .MuiOutlinedInput-notchedOutline': {
                                                  borderColor: roleStyles.border.replace('border-', ''),
                                                },
                                                '&:hover .MuiOutlinedInput-notchedOutline': {
                                                  borderColor: roleStyles.text.replace('text-', ''),
                                                },
                                                height: 'clamp(1.2rem, 3vh, 1.75rem)',
                                                fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                                '& .MuiSelect-select': {
                                                  padding: 'clamp(0.15rem, 0.5vw, 0.5rem)',
                                                  fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                                },
                                              }}
                                              MenuProps={{
                                                PaperProps: {
                                                  sx: {
                                                    maxHeight: 140,
                                                    '& .MuiMenuItem-root': {
                                                      fontSize: 'clamp(0.5rem, 1.3vw, 0.75rem)',
                                                      padding: 'clamp(0.15rem, 0.5vw, 0.375rem) clamp(0.4rem, 1.5vw, 1rem)',
                                                      minHeight: 'auto',
                                                    },
                                                  },
                                                },
                                              }}
                                            >
                                              <MenuItem value="system">
                                                <span>System</span>
                                              </MenuItem>
                                              <MenuItem value="user">
                                                <span>User</span>
                                              </MenuItem>
                                              <MenuItem value="assistant">
                                                <span>Assistant</span>
                                              </MenuItem>
                                            </Select>
                                          </FormControl>
                                        </div>

                                        <div className="flex items-center" style={{ gap: 'clamp(0.05rem, 0.25vw, 0.25rem)' }}>
                                          <IconButton
                                            size="small"
                                            disabled={isReadOnly}
                                            onClick={async () => {
                                              if (isReadOnly) {
                                                return
                                              }
                                              try {
                                                await onCopyToClipboard(msg.content)
                                              } catch (error) {
                                                console.error('复制失败:', error)
                                              }
                                            }}
                                            className="text-blue-500 hover:bg-blue-50 transition-colors"
                                            title={t('components.prompts.advancedConfigEditor.variable.copyContent')}
                                            sx={{
                                              width: 'clamp(0.9rem, 2vw, 1.5rem)',
                                              height: 'clamp(0.9rem, 2vw, 1.5rem)',
                                            }}
                                          >
                                            <Copy style={{ width: 'clamp(0.4rem, 1.2vw, 0.75rem)', height: 'clamp(0.4rem, 1.2vw, 0.75rem)' }} />
                                          </IconButton>

                                          <IconButton
                                            size="small"
                                            disabled={isReadOnly}
                                            onClick={() => {
                                              if (isReadOnly) {
                                                return
                                              }
                                              const newParams = [...parameters]
                                              if (newParams[index].messages) {
                                                newParams[index].messages = newParams[index].messages!.filter((_, i) => i !== msgIndex)
                                                onParametersChange(newParams)
                                              }
                                            }}
                                            className="text-red-500 hover:bg-red-50 transition-colors"
                                            title={t('components.prompts.advancedConfigEditor.variable.deleteMessage')}
                                            sx={{
                                              width: 'clamp(0.9rem, 2vw, 1.5rem)',
                                              height: 'clamp(0.9rem, 2vw, 1.5rem)',
                                            }}
                                          >
                                            <Trash2 style={{ width: 'clamp(0.4rem, 1.2vw, 0.75rem)', height: 'clamp(0.4rem, 1.2vw, 0.75rem)' }} />
                                          </IconButton>
                                        </div>
                                      </div>

                                      <TextField
                                        size="small"
                                        multiline
                                        minRows={1}
                                        maxRows={8}
                                        fullWidth
                                        value={localEdits[`msg_${param.name}_${msgIndex}`] ?? msg.content}
                                        onChange={e => {
                                          if (isReadOnly) return
                                          const v = e.target.value
                                          setLocalEdits(prev => ({ ...prev, [`msg_${param.name}_${msgIndex}`]: v }))
                                          scheduleFlush()
                                        }}
                                        disabled={isReadOnly}
                                        onFocus={() => onEditingParamIdChange?.(param.name + '_' + msgIndex)}
                                        onBlur={() => {
                                          flushLocalEdits()
                                          onEditingParamIdChange?.(null)
                                        }}
                                        placeholder={t('components.prompts.advancedConfigEditor.variable.inputMessagePlaceholder', { role: msg.role })}
                                        className={`${roleStyles.lightBg}`}
                                        InputProps={{
                                          className: 'bg-white/60',
                                          sx: {
                                            fontSize: 'clamp(0.5rem, 1.3vw, 0.8125rem)',
                                            '& .MuiOutlinedInput-notchedOutline': {
                                              borderColor: roleStyles.border.replace('border-', ''),
                                            },
                                            '&:hover .MuiOutlinedInput-notchedOutline': {
                                              borderColor: roleStyles.text.replace('text-', ''),
                                            },
                                            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                              borderColor: roleStyles.text.replace('text-', ''),
                                            },
                                            '& textarea': {
                                              resize: 'none',
                                              overflow: 'hidden',
                                              fontSize: 'clamp(0.5rem, 1.3vw, 0.8125rem)',
                                              lineHeight: '1.5',
                                              minHeight: 'clamp(0.75rem, 2vh, 1.25rem)',
                                            },
                                          },
                                        }}
                                        autoFocus={editingParamId === param.name + '_' + msgIndex}
                                      />
                                    </div>
                                  )
                                })}
                              </div>

                              {/* 添加消息按钮 */}
                              <div className="flex justify-center" style={{ marginTop: 'clamp(0.2rem, 0.75vh, 0.5rem)' }}>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  startIcon={<Plus style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />}
                                  onClick={() => {
                                    if (isReadOnly) {
                                      return
                                    }
                                    const newParams = [...parameters]
                                    if (!newParams[index].messages) {
                                      newParams[index].messages = []
                                    }
                                    // 根据当前消息数量决定下一个消息的角色：偶数索引为user，奇数索引为assistant
                                    const nextRole = newParams[index].messages!.length % 2 === 0 ? 'user' : 'assistant'
                                    newParams[index].messages!.push({
                                      id: Date.now().toString(),
                                      role: nextRole,
                                      content: '',
                                    })
                                    onParametersChange(newParams)
                                  }}
                                  className="border-green-300 text-green-600 hover:bg-green-50"
                                  disabled={isReadOnly}
                                  sx={{
                                    fontSize: 'clamp(0.5rem, 1.3vw, 0.75rem)',
                                    padding: 'clamp(0.15rem, 0.5vw, 0.375rem) clamp(0.3rem, 1vw, 0.75rem)',
                                  }}
                                >
                                  {t('components.prompts.advancedConfigEditor.variable.addMessage')}
                                </Button>
                              </div>
                            </div>
                          ) : param.dataType === 'boolean' ? (
                            <FormControl component="fieldset" fullWidth disabled={isReadOnly}>
                              <RadioGroup
                                value={param.value || 'false'}
                                onChange={e => {
                                  if (isReadOnly) {
                                    return
                                  }
                                  onParameterChange(param.name, e.target.value)
                                }}
                                row
                                sx={{ gap: 'clamp(0.25rem, 1vw, 1rem)' }}
                              >
                                <FormControlLabel
                                  value="true"
                                  control={<Radio size="small" disabled={isReadOnly} />}
                                  label="True"
                                  disabled={isReadOnly}
                                  sx={{
                                    marginRight: 'clamp(0.3rem, 1.5vw, 1.5rem)',
                                    '& .MuiFormControlLabel-label': {
                                      fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                    },
                                  }}
                                />
                                <FormControlLabel 
                                  value="false" 
                                  control={<Radio size="small" disabled={isReadOnly} />} 
                                  label="False" 
                                  disabled={isReadOnly}
                                  sx={{
                                    '& .MuiFormControlLabel-label': {
                                      fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                    },
                                  }}
                                />
                              </RadioGroup>
                            </FormControl>
                          ) : param.dataType === 'object' ? (
                            <div className="w-full">
                              <JsonEditor
                                value={localEdits[`value_${param.name}`] !== undefined ? localEdits[`value_${param.name}`] : param.value}
                                onChange={newValue => {
                                  if (isReadOnly) return
                                  setLocalEdits(prev => ({ ...prev, [`value_${param.name}`]: newValue }))
                                  scheduleFlush()
                                }}
                                placeholder={t('components.prompts.advancedConfigEditor.variable.jsonPlaceholder')}
                                minHeight={40}
                                maxHeight={150}
                                className="bg-white/60"
                                disabled={isReadOnly}
                              />
                            </div>
                          ) : (
                            <TextField
                              fullWidth
                              size="small"
                              value={localEdits[`value_${param.name}`] ?? param.value}
                              onChange={e => {
                                if (isReadOnly) return
                                const v = e.target.value
                                setLocalEdits(prev => ({ ...prev, [`value_${param.name}`]: v }))
                                scheduleFlush()
                              }}
                              onBlur={e => {
                                if (isReadOnly) return
                                flushLocalEdits()
                                onParameterBlur?.(param.name, e.target.value)
                              }}
                              placeholder={
                                param.dataType === 'integer'
                                  ? t('components.prompts.advancedConfigEditor.variable.integerPlaceholder')
                                  : param.dataType === 'float'
                                    ? t('components.prompts.advancedConfigEditor.variable.floatPlaceholder')
                                    : t('components.prompts.advancedConfigEditor.variable.variableReferencePlaceholder', { name: param.name })
                              }
                              className="bg-white/60"
                              variant="outlined"
                              disabled={isReadOnly}
                              sx={{
                                '& .MuiOutlinedInput-root': {
                                  fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                  '& input': {
                                    fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                                  },
                                  '& fieldset': {
                                    borderColor: '#d1d5db',
                                  },
                                  '&:hover fieldset': {
                                    borderColor: '#9ca3af',
                                  },
                                  '&.Mui-focused fieldset': {
                                    borderColor: '#10b981',
                                  },
                                },
                              }}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  </Paper>
                ))
              ) : (
                <div className="text-center text-gray-500" style={{ padding: 'clamp(0.5rem, 2vh, 1.5rem) 0' }}>
                  <Settings 
                    className="mx-auto text-gray-300" 
                    style={{ 
                      width: 'clamp(1.5rem, 4vw, 2.5rem)', 
                      height: 'clamp(1.5rem, 4vw, 2.5rem)',
                      marginBottom: 'clamp(0.2rem, 0.75vh, 0.5rem)',
                    }} 
                  />
                  <p style={{ fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)' }}>{t('components.prompts.advancedConfigEditor.variable.noVariables')}</p>
                  <p style={{ fontSize: 'clamp(0.5rem, 1.3vw, 0.8125rem)' }}>{t('components.prompts.advancedConfigEditor.variable.variableDefinitionHint')}</p>
                </div>
              )}
            </div>

            {templateEngine === 'jinja2' && onAddVariable && (
              <div className="text-center" style={{ marginTop: 'clamp(0.3rem, 1.5vh, 1rem)' }}>
                <Button
                  variant="outlined"
                  sx={{
                    fontSize: 'clamp(0.5rem, 1.5vw, 0.875rem)',
                    padding: 'clamp(0.2rem, 0.75vw, 0.5rem) clamp(0.4rem, 1.5vw, 1rem)',
                  }}
                  startIcon={<Plus style={{ width: 'clamp(0.5rem, 1.5vw, 1rem)', height: 'clamp(0.5rem, 1.5vw, 1rem)' }} />}
                  onClick={e => {
                    if (isReadOnly) {
                      return
                    }
                    if (onAddVariable && typeof onAddVariable === 'function') {
                      onAddVariable()
                    } else {
                      console.error(`🔧 [ADVANCED-EDITOR] onAddVariable函数不存在或不是函数:`, onAddVariable)
                    }
                  }}
                  className="border-green-300 text-green-600 hover:bg-green-50"
                  disabled={isReadOnly}
                >
                  {t('components.prompts.advancedConfigEditor.variable.addVariable')}
                </Button>
              </div>
            )}

            {/* 页签底部提示文本 */}
            {showHint && (
              <div style={{ marginTop: 'clamp(0.5rem, 2vh, 1.5rem)' }}>
                <Alert 
                  severity="info"
                  action={
                    <IconButton
                      aria-label="close"
                      color="inherit"
                      size="small"
                      onClick={() => setShowHint(false)}
                      sx={{
                        padding: 'clamp(0.1rem, 0.5vw, 0.2rem)',
                      }}
                    >
                      <X style={{ width: 'clamp(0.5rem, 2vw, 0.875rem)', height: 'clamp(0.5rem, 2vw, 0.875rem)' }} />
                    </IconButton>
                  }
                  sx={{
                    padding: 'clamp(0.25rem, 0.5vw, 0.5rem) clamp(0.5rem, 1vw, 0.75rem)',
                    '& .MuiAlert-message': {
                      padding: 0,
                    },
                    '& .MuiAlert-icon': {
                      padding: 0,
                      marginRight: 'clamp(0.375rem, 0.75vw, 0.5rem)',
                    },
                  }}
                >
                  <Typography variant="body2" sx={{ fontSize: 'clamp(0.65rem, 1.4vw, 0.8125rem)' }}>
                    {templateEngine === 'normal'
                      ? t('components.prompts.advancedConfigEditor.variable.normalModeHint')
                      : t('components.prompts.advancedConfigEditor.variable.jinja2ModeHint')}
                  </Typography>
                </Alert>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 模型设置标签页 */}
      <div role="tabpanel" hidden={activeTab !== 1} className="flex-1 flex-col" style={{ padding: 'clamp(0.375rem, 1vw, 1rem)' }}>
        {activeTab === 1 && (
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-y-auto scrollbar-hide" style={{ maxHeight: modelSettingsMaxHeight }}>
              {/* 模型选择区域 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.375rem, 1vh, 0.75rem)' }}>
                <Typography 
                  variant="h6" 
                  className="text-gray-800 font-bold"
                  sx={{ fontSize: 'clamp(0.35rem, 1.75vw, 1rem)' }}
                >
                  {t('components.prompts.advancedConfigEditor.model.modelSelection')}
                </Typography>

                <div>
                  <ModelSelector
                    availableModels={availableModels}
                    selectedModel={selectedModel}
                    onModelChange={handleModelChange}
                    modelsLoading={modelsLoading}
                    placeholder={t('components.prompts.advancedConfigEditor.model.selectModel')}
                    disabled={isReadOnly}
                  />
                </div>
              </div>

              {/* 分隔线 */}
              <div className="border-t border-gray-300" style={{ margin: 'clamp(0.5rem, 1.5vh, 1rem) 0' }}></div>

              {/* 参数配置区域 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.5rem, 1.5vh, 1rem)' }}>
                <Typography 
                  variant="h6" 
                  className="text-gray-800 font-bold"
                  sx={{ fontSize: 'clamp(0.35rem, 1.75vw, 1rem)' }}
                >
                  {t('components.prompts.advancedConfigEditor.model.parameterConfig')}
                </Typography>

                <ModelParameterEditor
                  selectedModel={selectedModel}
                  modelConfig={modelConfig}
                  onModelConfigChange={handleModelConfigChange}
                  readonly={isReadOnly}
                />
              </div>

              {/* 页签底部提示文本 */}
              {showModelHint && (
                <div style={{ marginTop: 'clamp(0.75rem, 2vh, 1.5rem)' }}>
                  <Alert 
                    severity="info"
                    action={
                      <IconButton
                        aria-label="close"
                        color="inherit"
                        size="small"
                        onClick={() => setShowModelHint(false)}
                        sx={{
                          padding: 'clamp(0.1rem, 0.5vw, 0.2rem)',
                        }}
                      >
                        <X style={{ width: 'clamp(0.5rem, 2vw, 0.875rem)', height: 'clamp(0.5rem, 2vw, 0.875rem)' }} />
                      </IconButton>
                    }
                    sx={{
                      padding: 'clamp(0.25rem, 0.5vw, 0.5rem) clamp(0.5rem, 1vw, 0.75rem)',
                      '& .MuiAlert-message': {
                        padding: 0,
                      },
                      '& .MuiAlert-icon': {
                        padding: 0,
                        marginRight: 'clamp(0.375rem, 0.75vw, 0.5rem)',
                      },
                    }}
                  >
                    <Typography variant="body2" sx={{ fontSize: 'clamp(0.65rem, 1.4vw, 0.8125rem)' }}>
                      {t('components.prompts.advancedConfigEditor.model.settingsHint')}
                    </Typography>
                  </Alert>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 工具设置标签页 */}
      <div role="tabpanel" hidden={activeTab !== 2} className="flex-1 flex-col" style={{ padding: 'clamp(0.375rem, 1vw, 1rem)' }}>
        {activeTab === 2 && (
          <ToolSettingsPanel
            tools={tools}
            toolsEnabled={toolsEnabled}
            onToolsChange={onToolsChange}
            onToolsEnabledChange={onToolsEnabledChange}
            onAddTool={onAddTool}
            onEditTool={onEditTool}
            onDeleteTool={onDeleteTool}
            onHasUnsavedChanges={onHasUnsavedChanges}
            onTriggerAutoSave={onTriggerAutoSave}
            enableAutoSave={enableAutoSave}
            isReadOnly={isReadOnly}
            showDefaultValue={true}
          />
        )}
      </div>
    </div>
  )
}

export default React.memo(AdvancedConfigEditor)
