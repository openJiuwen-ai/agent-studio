import React from 'react'
import { useTranslation } from 'react-i18next'
import { Typography, Chip, Paper, FormControlLabel, Switch, TextField, Button, Alert, IconButton } from '@mui/material'
import { Code, X } from 'lucide-react'
import ConditionalTooltip from './ConditionalTooltip'
import { Tool } from '@/types/promptType'

export interface ToolSettingsPanelProps {
  // 工具相关数据
  tools: Tool[]
  toolsEnabled: boolean

  // 事件回调
  onToolsChange: (tools: Tool[]) => void
  onToolsEnabledChange: (enabled: boolean) => void
  onAddTool: () => void
  onEditTool: (tool: Tool) => void
  onDeleteTool: (toolId: string) => void

  // 状态控制
  onHasUnsavedChanges: (hasChanges: boolean) => void
  onTriggerAutoSave: (data?: any) => void
  enableAutoSave?: boolean
  isReadOnly?: boolean
  showDefaultValue?: boolean
  showToolFunctionHint?: boolean // 控制是否显示工具函数提示信息，默认为 true
}

const ToolSettingsPanel: React.FC<ToolSettingsPanelProps> = ({
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
  isReadOnly = false,
  showDefaultValue = true,
  showToolFunctionHint = true,
}) => {
  const { t } = useTranslation()
  // 使用本地状态立即更新 UI，避免等待父组件状态更新导致的延迟
  const [localToolsEnabled, setLocalToolsEnabled] = React.useState(toolsEnabled)
  // 提示框显示状态管理
  const [showHint, setShowHint] = React.useState(true)
  // 工具列表最大高度响应式管理
  const [toolListMaxHeight, setToolListMaxHeight] = React.useState('calc(100vh - 475px)')

  // 当父组件传入的 toolsEnabled 变化时，同步本地状态（用于外部状态更新）
  React.useEffect(() => {
    setLocalToolsEnabled(toolsEnabled)
  }, [toolsEnabled])

  // 响应式计算工具列表的最大高度
  React.useEffect(() => {
    const updateMaxHeight = () => {
      if (window.innerWidth < 640) {
        // 小屏幕：手机等移动设备
        setToolListMaxHeight('calc(100vh - 300px)')
      } else if (window.innerWidth < 2000) {
        // 中等屏幕：平板、14寸笔记本等
        setToolListMaxHeight('calc(100vh - 270px)')
      } else {
        // 大屏幕：15寸以上笔记本、台式显示器
        setToolListMaxHeight('calc(100vh - 500px)')
      }
    }

    updateMaxHeight()
    window.addEventListener('resize', updateMaxHeight)
    return () => window.removeEventListener('resize', updateMaxHeight)
  }, [])

  return (
    <div 
      className="flex-1 flex flex-col"
      style={{ maxHeight: toolListMaxHeight }}
    >
      {/* 工具列表区域 */}
      <div className="flex items-center justify-between gap-2 mb-3 flex-wrap flex-shrink-0">
        <div className="flex items-center gap-3 flex-shrink-0">
          <Typography
            variant="h6"
            className="text-gray-800 font-bold"
            sx={{
              fontSize: 'clamp(0.275rem, 1.5vw, 0.8125rem)',
            }}
          >
            {t('components.prompts.toolEditDialog.toolList')}
          </Typography>
          <FormControlLabel
            disabled={isReadOnly}
            control={
              <Switch
                checked={localToolsEnabled}
                onChange={e => {
                  if (isReadOnly) {
                    return
                  }
                  const newToolsEnabled = e.target.checked
                  // 立即更新本地状态，确保 UI 立即响应
                  setLocalToolsEnabled(newToolsEnabled)
                  // 异步调用父组件回调，避免阻塞 UI 更新
                  // 使用 requestAnimationFrame 确保在下一个渲染周期执行
                  requestAnimationFrame(() => {
                    onToolsEnabledChange(newToolsEnabled)
                    onHasUnsavedChanges(true)
                    // 启用工具开关变化时触发自动保存
                    if (enableAutoSave) {
                      onTriggerAutoSave({ toolsEnabled: newToolsEnabled })
                    }
                  })
                }}
                color="primary"
                size="small"
                disabled={isReadOnly}
              />
            }
            label={
              <Typography
                variant="body2"
                className="text-gray-700"
                sx={{
                  fontSize: 'clamp(0.7rem, 1.5vw, 0.75rem)',
                }}
              >
                {t('components.prompts.toolEditDialog.enableTool')}
              </Typography>
            }
            className="m-0"
            sx={{
              '& .MuiSwitch-root': {
                transform: 'scale(clamp(0.75, 1vw, 0.85))',
              },
            }}
          />
        </div>
        <Button
          size="small"
          variant="contained"
          startIcon={<Code className="w-3 h-3 sm:w-4 sm:h-4" />}
          onClick={() => {
            if (isReadOnly) {
              return
            }
            if (onAddTool && typeof onAddTool === 'function') {
              onAddTool()
            } else {
              console.error(`🔧 [TOOL-SETTINGS-PANEL] onAddTool函数不存在或不是函数:`, onAddTool)
            }
          }}
          disabled={!toolsEnabled || isReadOnly}
          className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          sx={{
            fontSize: 'clamp(0.7rem, 1.5vw, 0.75rem)',
            padding: 'clamp(3px, 0.5vw, 4px) clamp(6px, 1vw, 10px)',
          }}
        >
          {t('components.prompts.toolEditDialog.addTool')}
        </Button>
      </div>

      <div className="space-y-2 sm:space-y-3 flex-1 overflow-y-auto scrollbar-hide min-h-0">
        {!toolsEnabled ? (
          <div className="text-center py-6 sm:py-8">
            <Code className="w-8 h-8 sm:w-10 sm:h-10 text-gray-300 mx-auto mb-3 sm:mb-4" />
            <Typography
              variant="body1"
              className="text-gray-500 mb-2"
              sx={{
                fontSize: 'clamp(0.8125rem, 2vw, 0.9375rem)',
              }}
            >
              {t('components.prompts.toolEditDialog.toolDisabled')}
            </Typography>
            <Typography
              variant="body2"
              className="text-gray-400"
              sx={{
                fontSize: 'clamp(0.7rem, 1.5vw, 0.8125rem)',
              }}
            >
              {t('components.prompts.toolEditDialog.enableToolHint')}
            </Typography>
          </div>
        ) : tools.length > 0 ? (
          tools.map((tool, index) => (
            <Paper key={tool.id} elevation={1} className="p-1.5 sm:p-2 bg-white/80 border border-green-200">
              <div className="space-y-1.5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5">
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-white text-xs font-bold">{index + 1}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <ConditionalTooltip title={tool.name}>
                        <Typography
                          variant="subtitle2"
                          className="text-gray-800 font-medium truncate"
                          sx={{
                            maxWidth: { xs: '120px', sm: '180px', md: '250px' },
                            fontSize: 'clamp(0.7rem, 1.5vw, 0.8125rem)',
                          }}
                        >
                          {tool.name}
                        </Typography>
                      </ConditionalTooltip>
                    </div>
                    <Chip
                      label={t('components.prompts.toolEditDialog.parameters', { count: tool.parameters?.length || 0 })}
                      size="small"
                      className="bg-blue-100 text-blue-700"
                      sx={{
                        fontSize: 'clamp(0.5625rem, 1.2vw, 0.6875rem)',
                        height: 'auto',
                        '& .MuiChip-label': {
                          padding: 'clamp(1px, 0.3vw, 3px) clamp(3px, 0.6vw, 6px)',
                        },
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-1.5 self-end sm:self-auto">
                    <Button
                      size="small"
                      onClick={() => {
                        if (isReadOnly) {
                          return
                        }
                        onEditTool(tool)
                      }}
                      className="text-green-600 hover:bg-green-50"
                      disabled={isReadOnly}
                      sx={{
                        fontSize: 'clamp(0.65rem, 1.4vw, 0.75rem)',
                        padding: 'clamp(2px, 0.4vw, 3px) clamp(4px, 0.8vw, 6px)',
                        minWidth: 'auto',
                      }}
                    >
                      {t('components.prompts.toolEditDialog.edit')}
                    </Button>
                    <Button
                      size="small"
                      onClick={() => {
                        if (isReadOnly) {
                          return
                        }
                        onDeleteTool(tool.id)
                      }}
                      className="text-red-600 hover:bg-red-50"
                      disabled={isReadOnly}
                      sx={{
                        fontSize: 'clamp(0.65rem, 1.4vw, 0.75rem)',
                        padding: 'clamp(2px, 0.4vw, 3px) clamp(4px, 0.8vw, 6px)',
                        minWidth: 'auto',
                      }}
                    >
                      {t('components.prompts.toolEditDialog.delete')}
                    </Button>
                  </div>
                </div>
                <ConditionalTooltip title={tool.description}>
                  <Typography
                    variant="body2"
                    className="text-gray-600 truncate"
                    sx={{
                      maxWidth: '100%',
                      fontSize: 'clamp(0.65rem, 1.4vw, 0.8125rem)',
                    }}
                  >
                    {tool.description}
                  </Typography>
                </ConditionalTooltip>

                {/* 默认模拟值显示和编辑 */}
                {showDefaultValue && (
                  <div className="mt-1.5 sm:mt-2 flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
                    <Typography
                      variant="caption"
                      className="text-gray-700 font-medium whitespace-nowrap"
                      sx={{
                        fontSize: 'clamp(0.625rem, 1.3vw, 0.6875rem)',
                      }}
                    >
                      {t('components.prompts.toolEditDialog.defaultMockValue')}
                    </Typography>
                    <TextField
                      fullWidth
                      size="small"
                      multiline
                      minRows={1}
                      maxRows={2}
                      value={tool.defaultValue || ''}
                      onChange={e => {
                        if (isReadOnly) {
                          return
                        }
                        const newTools = tools.map(t => (t.id === tool.id ? { ...t, defaultValue: e.target.value } : t))
                        onToolsChange(newTools)
                        onHasUnsavedChanges(true)
                        // 如果启用了自动保存，触发自动保存
                        if (enableAutoSave && onTriggerAutoSave) {
                          onTriggerAutoSave({
                            tools: newTools,
                            toolsEnabled: toolsEnabled,
                          })
                        }
                      }}
                      onBlur={e => {
                        if (isReadOnly) {
                          return
                        }
                        const newTools = tools.map(t => (t.id === tool.id ? { ...t, defaultValue: e.target.value } : t))
                        onToolsChange(newTools)
                        onHasUnsavedChanges(true)
                        // 如果启用了自动保存，触发自动保存
                        if (enableAutoSave && onTriggerAutoSave) {
                          onTriggerAutoSave({
                            tools: newTools,
                            toolsEnabled: toolsEnabled,
                          })
                        }
                      }}
                      placeholder={t('components.prompts.toolEditDialog.defaultMockValuePlaceholder')}
                      variant="outlined"
                      disabled={isReadOnly}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          backgroundColor: 'rgba(255, 255, 255, 0.8)',
                          fontSize: 'clamp(0.65rem, 1.4vw, 0.75rem)',
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
                  </div>
                )}
              </div>
            </Paper>
          ))
        ) : (
          <div className="text-center py-6 sm:py-8 text-gray-500">
            <Code className="w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-2 sm:mb-3 text-gray-300" />
            <p
              style={{
                fontSize: 'clamp(0.8125rem, 2vw, 0.9375rem)',
              }}
            >
              {t('components.prompts.toolEditDialog.noTools')}
            </p>
            <p
              style={{
                fontSize: 'clamp(0.7rem, 1.5vw, 0.8125rem)',
              }}
            >
              {t('components.prompts.toolEditDialog.addToolHint')}
            </p>
          </div>
        )}
      </div>

      {/* 页签底部提示文本 */}
      {showToolFunctionHint && showHint && (
        <div className="mt-3 sm:mt-4 md:mt-6 flex-shrink-0">
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
            <Typography
              variant="body2"
              sx={{
                fontSize: 'clamp(0.65rem, 1.4vw, 0.8125rem)',
              }}
            >
              {t('components.prompts.toolEditDialog.toolFunctionHint')}
            </Typography>
          </Alert>
        </div>
      )}
    </div>
  )
}

export default ToolSettingsPanel
