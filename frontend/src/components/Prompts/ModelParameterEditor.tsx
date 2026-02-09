import React from 'react'
import { Typography, TextField, Slider, Switch, IconButton, Tooltip, Box } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Cpu } from 'lucide-react'
import { Model, ModelConfig } from '@/types/promptType'

export interface ModelParameterEditorProps {
  // 选中的模型
  selectedModel: Model | null
  // 模型配置
  modelConfig: ModelConfig
  // 模型配置变更回调
  onModelConfigChange: (config: ModelConfig) => void
  // 自定义样式类名
  className?: string
  // 是否只读模式
  readonly?: boolean
}

const ModelParameterEditor: React.FC<ModelParameterEditorProps> = ({ selectedModel, modelConfig, onModelConfigChange, className = '', readonly = false }) => {
  const { t } = useTranslation()
  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(0.5rem, 1.5vh, 0.75rem)' }}>
      {selectedModel?.openModel?.param_config?.param_schemas ? (
        selectedModel.openModel.param_config.param_schemas.map(paramSchema => (
          <div key={paramSchema.name} style={{ marginBottom: 'clamp(0.375rem, 1vh, 0.5rem)' }}>
            {paramSchema.type === 'float' || paramSchema.type === 'int' ? (
              paramSchema.min !== undefined && paramSchema.max !== undefined ? (
                // 使用滑块控件（当有min和max时）
                <div className="flex items-center" style={{ gap: 0 }}>
                  <div className="flex items-center flex-shrink-0" style={{ width: 'clamp(1rem, 8vw, 6.9rem)', gap: 0 }}>
                    <Tooltip title={paramSchema.label}>
                      <Typography
                        variant="subtitle2"
                        className="text-gray-700 truncate"
                        sx={{
                          fontSize: 'clamp(0.7rem, 1.5vw, 0.8rem)',
                        }}
                      >
                        {paramSchema.label}
                      </Typography>
                    </Tooltip>
                    <Tooltip title={paramSchema.desc}>
                      <IconButton
                        size="small"
                        className="text-gray-400 hover:text-gray-600 p-0 flex-shrink-0"
                        sx={{
                          width: 'clamp(1rem, 2vw, 2rem)',
                          height: 'clamp(1rem, 2vw, 2rem)',
                        }}
                      >
                        <svg
                          style={{
                            width: 'clamp(0.85rem, 1.5vw, 0.85rem)',
                            height: 'clamp(0.85rem, 1.5vw, 0.85rem)',
                          }}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </IconButton>
                    </Tooltip>
                  </div>
                  <div className="flex-1 flex items-center" style={{ gap: 'clamp(0.125rem, 0.5vw, 0.25rem)', minWidth: 0 }}>
                    <Typography
                      variant="caption"
                      className="text-gray-500 text-right flex-shrink-0"
                      sx={{
                        width: 'clamp(0.75rem, 3vw, 1.5rem)',
                        fontSize: 'clamp(0.5rem, 1.25vw, 0.65rem)',
                      }}
                    >
                      {paramSchema.min}
                    </Typography>
                    <Slider
                      value={(() => {
                        const val = modelConfig[paramSchema.name as keyof typeof modelConfig] ?? paramSchema.default_val
                        const numVal = Number(val)
                        return isNaN(numVal) ? Number(paramSchema.default_val) || 0 : numVal
                      })()}
                      onChange={(_, value) => onModelConfigChange({ ...modelConfig, [paramSchema.name]: value as number })}
                      min={Number(paramSchema.min)}
                      max={Number(paramSchema.max)}
                      step={paramSchema.type === 'float' ? 0.1 : 1}
                      valueLabelDisplay="auto"
                      valueLabelFormat={value => (paramSchema.type === 'float' ? Number(value).toFixed(1) : Number(value).toString())}
                      disabled={readonly}
                      sx={{
                        flex: 1,
                        minWidth: 0,
                        '& .MuiSlider-valueLabel': {
                          fontSize: 'clamp(0.625rem, 1.25vw, 0.7rem)',
                        },
                      }}
                      className="bg-white/60 rounded"
                      style={{ padding: 'clamp(0.125rem, 0.5vw, 0.375rem)' }}
                    />
                    <Typography
                      variant="caption"
                      className="text-gray-500 text-left flex-shrink-0"
                      sx={{
                        width: 'clamp(0.75rem, 3vw, 2rem)',
                        fontSize: 'clamp(0.5rem, 1.25vw, 0.65rem)',
                      }}
                    >
                      {paramSchema.max}
                    </Typography>
                  </div>
                  <Box
                    sx={{
                      width: 'clamp(3.5rem, 12vw, 5rem)',
                      flexShrink: 0,
                      display: { xs: 'none', sm: 'block' },
                    }}
                  >
                    <TextField
                      size="small"
                      type="number"
                      value={(() => {
                        const val = modelConfig[paramSchema.name as keyof typeof modelConfig] ?? paramSchema.default_val
                        return val === null || val === undefined ? '' : String(val)
                      })()}
                      onChange={e => {
                        // 编辑时只更新值，不做校验
                        const value = paramSchema.type === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value)
                        if (!isNaN(value)) {
                          onModelConfigChange({ ...modelConfig, [paramSchema.name]: value })
                        } else if (e.target.value === '') {
                          // 允许清空输入
                          onModelConfigChange({ ...modelConfig, [paramSchema.name]: '' })
                        }
                      }}
                      onBlur={e => {
                        // 编辑完成后进行参数校验
                        let value = parseFloat(e.target.value)

                        if (!isNaN(value)) {
                          // 根据类型进行四舍五入
                          if (paramSchema.type === 'int') {
                            // int 类型：四舍五入保留到整数
                            value = Math.round(value)
                          } else if (paramSchema.type === 'float') {
                            // float 类型：四舍五入保留1位小数
                            value = Math.round(value * 10) / 10
                          }

                          const min = Number(paramSchema.min)
                          const max = Number(paramSchema.max)
                          if (value < min) value = min
                          if (value > max) value = max
                          onModelConfigChange({ ...modelConfig, [paramSchema.name]: value })
                        } else {
                          // 如果输入无效，恢复为默认值
                          const defaultValue = paramSchema.default_val ?? (paramSchema.type === 'float' ? 0 : 0)
                          onModelConfigChange({ ...modelConfig, [paramSchema.name]: defaultValue })
                        }
                      }}
                      disabled={readonly}
                      inputProps={{
                        min: paramSchema.min,
                        max: paramSchema.max,
                        step: paramSchema.type === 'float' ? 0.1 : 1,
                      }}
                      className="bg-white/60"
                      fullWidth
                      sx={{
                        fontSize: 'clamp(0.65rem, 1.5vw, 0.8rem)',
                        '& .MuiOutlinedInput-root': {
                          fontSize: 'clamp(0.65rem, 1.5vw, 0.8rem)',
                          '& input': {
                            padding: 'clamp(0.125rem, 0.5vw, 0.375rem)',
                            textAlign: 'left',
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
                  </Box>
                </div>
              ) : (
                // 使用文本输入框（当没有min和max时）
                <div className="flex items-center" style={{ gap: 0 }}>
                  <div className="flex items-center flex-shrink-0" style={{ minWidth: 'clamp(2rem, 8vw, 3rem)', gap: 0 }}>
                    <Tooltip title={paramSchema.label}>
                      <Typography
                        variant="subtitle2"
                        className="text-gray-700 truncate"
                        sx={{
                          fontSize: 'clamp(0.7rem, 1.5vw, 0.8rem)',
                        }}
                      >
                        {paramSchema.label}
                      </Typography>
                    </Tooltip>
                    <Tooltip title={paramSchema.desc}>
                      <IconButton
                        size="small"
                        className="text-gray-400 hover:text-gray-600 p-0 flex-shrink-0"
                        sx={{
                          width: 'clamp(1rem, 2vw, 1rem)',
                          height: 'clamp(1rem, 2vw, 1rem)',
                        }}
                      >
                        <svg
                          style={{
                            width: 'clamp(0.85rem, 1.5vw, 0.85rem)',
                            height: 'clamp(0.85rem, 1.5vw, 0.85rem)',
                          }}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                      </IconButton>
                    </Tooltip>
                  </div>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    value={(() => {
                      const val = modelConfig[paramSchema.name as keyof typeof modelConfig] ?? paramSchema.default_val
                      return val === null || val === undefined ? '' : String(val)
                    })()}
                    onChange={e => {
                      const value = paramSchema.type === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value)
                      if (!isNaN(value)) {
                        onModelConfigChange({ ...modelConfig, [paramSchema.name]: value })
                      }
                    }}
                    disabled={readonly}
                    className="bg-white/60"
                    sx={{
                      fontSize: 'clamp(0.7rem, 1.5vw, 0.8rem)',
                      '& .MuiOutlinedInput-root': {
                        fontSize: 'clamp(0.7rem, 1.5vw, 0.8rem)',
                        '& input': {
                          padding: 'clamp(0.375rem, 1vw, 0.4rem)',
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
                </div>
              )
            ) : paramSchema.type === 'bool' ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-shrink-0" style={{ minWidth: 'clamp(2rem, 10vw, 3.5rem)', gap: 0 }}>
                  <Tooltip title={paramSchema.label}>
                    <Typography
                      variant="subtitle2"
                      className="text-gray-700 truncate"
                      sx={{
                        fontSize: 'clamp(0.75rem, 1.5vw, 0.875rem)',
                      }}
                    >
                      {paramSchema.label}
                    </Typography>
                  </Tooltip>
                  <Tooltip title={paramSchema.desc}>
                    <IconButton
                      size="small"
                      className="text-gray-400 hover:text-gray-600 p-0 flex-shrink-0"
                      sx={{
                        width: 'clamp(0.875rem, 2vw, 1.25rem)',
                        height: 'clamp(0.875rem, 2vw, 1.25rem)',
                      }}
                    >
                      <svg
                        style={{
                          width: 'clamp(0.75rem, 1.5vw, 1rem)',
                          height: 'clamp(0.75rem, 1.5vw, 1rem)',
                        }}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </IconButton>
                  </Tooltip>
                </div>
                <Switch
                  checked={Boolean(modelConfig[paramSchema.name as keyof typeof modelConfig] ?? paramSchema.default_val)}
                  onChange={e => onModelConfigChange({ ...modelConfig, [paramSchema.name]: e.target.checked })}
                  disabled={readonly}
                  sx={{
                    '& .MuiSwitch-switchBase': {
                      padding: 'clamp(0.3rem, 0.75vw, 0.4rem)',
                    },
                    '& .MuiSwitch-thumb': {
                      width: 'clamp(0.65rem, 1.5vw, 0.85rem)',
                      height: 'clamp(0.65rem, 1.5vw, 0.85rem)',
                    },
                  }}
                />
              </div>
            ) : (
              // 其他类型使用文本输入框
              <div className="flex items-center" style={{ gap: 0 }}>
                <div className="flex items-center flex-shrink-0" style={{ minWidth: 'clamp(2rem, 10vw, 3.5rem)', gap: 0 }}>
                  <Tooltip title={paramSchema.label}>
                    <Typography
                      variant="subtitle2"
                      className="text-gray-700 truncate"
                      sx={{
                        fontSize: 'clamp(0.75rem, 1.5vw, 0.875rem)',
                      }}
                    >
                      {paramSchema.label}
                    </Typography>
                  </Tooltip>
                  <Tooltip title={paramSchema.desc}>
                    <IconButton
                      size="small"
                      className="text-gray-400 hover:text-gray-600 p-0 flex-shrink-0"
                      sx={{
                        width: 'clamp(0.875rem, 2vw, 1.25rem)',
                        height: 'clamp(0.875rem, 2vw, 1.25rem)',
                      }}
                    >
                      <svg
                        style={{
                          width: 'clamp(0.75rem, 1.5vw, 1rem)',
                          height: 'clamp(0.75rem, 1.5vw, 1rem)',
                        }}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </IconButton>
                  </Tooltip>
                </div>
                <TextField
                  fullWidth
                  size="small"
                  value={(() => {
                    const val = modelConfig[paramSchema.name as keyof typeof modelConfig] ?? paramSchema.default_val
                    return val === null || val === undefined ? '' : String(val)
                  })()}
                  onChange={e => onModelConfigChange({ ...modelConfig, [paramSchema.name]: e.target.value })}
                  disabled={readonly}
                  className="bg-white/60"
                  sx={{
                    fontSize: 'clamp(0.75rem, 1.5vw, 0.875rem)',
                    '& .MuiOutlinedInput-root': {
                      fontSize: 'clamp(0.75rem, 1.5vw, 0.875rem)',
                      '& input': {
                        padding: 'clamp(0.375rem, 1vw, 0.5rem)',
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
              </div>
            )}
          </div>
        ))
      ) : (
        <div
          className="text-center text-gray-500"
          style={{
            padding: 'clamp(0.75rem, 2vh, 1rem) 0',
          }}
        >
          <Cpu
            className="mx-auto text-gray-300"
            style={{
              width: 'clamp(1.5rem, 3vw, 2rem)',
              height: 'clamp(1.5rem, 3vw, 2rem)',
              marginBottom: 'clamp(0.25rem, 0.5vh, 0.375rem)',
            }}
          />
          <p style={{ fontSize: 'clamp(0.7rem, 1.5vw, 0.8rem)' }}>{t('components.prompts.modelParameterEditor.selectModelFirst')}</p>
          <p style={{ fontSize: 'clamp(0.6rem, 1.25vw, 0.7rem)' }}>{t('components.prompts.modelParameterEditor.selectModelDescription')}</p>
        </div>
      )}
    </div>
  )
}

export default ModelParameterEditor
