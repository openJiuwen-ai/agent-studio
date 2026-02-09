import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useScopedTranslation } from '@/i18n'
import { X, Loader2, Sparkles } from 'lucide-react'
import CreateAgentIcon from '@/assets/icons/create-agent-react.svg?react'
import CreateAgentWorkflowIcon from '@/assets/icons/create-agent-workflow.svg?react'
import CreateAgentReactPreview from '@/assets/icons/create-agent-react-preview.png'
import CreateAgentWorkflowPreview from '@/assets/icons/create-agent-workflow-preview.png'
import CreateAgentReactPreviewEn from '@/assets/icons/create-agent-react-preview-en.png'
import CreateAgentWorkflowPreviewEn from '@/assets/icons/create-agent-workflow-preview-en.png'
import { TextField, Button, Typography, IconButton, Popover } from '@mui/material'
import UnifiedSnackbar, { SnackbarMessage } from '../../Common/UnifiedSnackbar'
import { useCreateAgent } from '@test-agentstudio/api-client'
import { CreateAgentRequest } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { ENV_CONFIG } from '../../config/environment'

type AgentMode = 'single-react-agent' | 'multi-workflow'

interface AgentModeInfo {
  id: AgentMode
  icon: string
  name: string
  description: string
  detailDescription: string
}

interface AgentCreateData {
  mode: AgentMode
  name: string
  description: string
  icon: string
}

const AgentCreatePage: React.FC = () => {
  const { t, i18n } = useScopedTranslation('agents.agentCreate')
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const MODE_INFO: Record<AgentMode, AgentModeInfo> = {
    'single-react-agent': {
      id: 'single-react-agent',
      icon: '👤',
      name: t('mode.singleReact.name'),
      description: t('mode.singleReact.description'),
      detailDescription: t('mode.singleReact.description'),
    },
    'multi-workflow': {
      id: 'multi-workflow',
      icon: '🔄',
      name: t('mode.multiWorkflow.name'),
      description: t('mode.multiWorkflow.description'),
      detailDescription: t('mode.multiWorkflow.description'),
    },
  }

  const [agentData, setAgentData] = useState<AgentCreateData>({
    mode: 'single-react-agent',
    name: '',
    description: '',
    icon: '🤖',
  })

  const [errors, setErrors] = useState<Partial<AgentCreateData>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [snackbar, setSnackbar] = useState<SnackbarMessage>({ open: false, message: '', severity: 'success' })
  const [iconAnchorEl, setIconAnchorEl] = useState<HTMLElement | null>(null)
  const [descriptionRows, setDescriptionRows] = useState(6)
  const [descriptionMaxHeight, setDescriptionMaxHeight] = useState('45rem')

  const isZh = i18n.language.startsWith('zh')
  const reactPreviewImage = isZh ? CreateAgentReactPreview : CreateAgentReactPreviewEn
  const workflowPreviewImage = isZh ? CreateAgentWorkflowPreview : CreateAgentWorkflowPreviewEn

  const createAgentMutation = useCreateAgent()
  const selectedModeInfo = MODE_INFO[agentData.mode]

  // 响应式计算描述框的行数和最大高度
  useEffect(() => {
    const updateDimensions = () => {
      if (window.innerWidth < 640) {
        // 小屏幕：手机等移动设备
        setDescriptionRows(5)
        setDescriptionMaxHeight('20rem')
      } else if (window.innerWidth < 2000) {
        // 中等屏幕：平板、14寸笔记本等
        setDescriptionRows(6)
        setDescriptionMaxHeight('13rem')
      } else {
        // 大屏幕：15寸以上笔记本、台式显示器
        setDescriptionRows(12)
        setDescriptionMaxHeight('55vh')
      }
    }

    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // Predefined icon options
  const iconOptions = ['🤖', '🧠', '💡', '🔧', '📊', '💬', '🎯', '🚀', '🌟', '⚡', '🎨', '📝', '🔍', '💻', '🌍', '💰', '🏥', '🎓', '🏠', '🛒']

  const validateForm = (): boolean => {
    const newErrors: Partial<AgentCreateData> = {}

    if (!agentData.name.trim()) {
      newErrors.name = t('form.name.required')
    }

    if (!agentData.description.trim()) {
      newErrors.description = t('form.description.required')
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }

  const handleConfirm = async () => {
    if (!validateForm()) return

    setIsLoading(true)

    try {
      const createAgentRequest: CreateAgentRequest = {
        space_id: getDefaultSpaceId(),
        agent_name: agentData.name,
        description: agentData.description,
        agent_type: agentData.mode === 'single-react-agent' ? 'react' : 'workflow',
        icon: agentData.icon || selectedModeInfo.icon,
      }

      const response = await createAgentMutation.mutateAsync(createAgentRequest)

      if (response.code === 0 || response.code === 200) {
        setSnackbar({ open: true, message: t('messages.success'), severity: 'success' })

        await new Promise(resolve => setTimeout(resolve, 1500))

        navigate(`/dashboard/agents/${response.data.agent_id}`, {
          state: {
            agentEntryData: agentData,
            isNew: true,
            botId: response.data.agent_id,
            agentMode: agentData.mode,
          },
        })
      } else {
        setSnackbar({
          open: true,
          message: t('messages.failed', { reason: response.message || t('messages.unknownError') }),
          severity: 'error',
        })
      }
    } catch (error) {
      console.error('API调用失败:', error)
      setSnackbar({ open: true, message: t('messages.retry'), severity: 'error' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleCancel = () => {
    navigate('/dashboard/agents')
  }

  const handleClose = () => {
    navigate('/dashboard/agents')
  }

  const handleIconClick = (event: React.MouseEvent<HTMLElement>) => {
    setIconAnchorEl(event.currentTarget)
  }

  const handleIconClose = () => {
    setIconAnchorEl(null)
  }

  const handleIconSelect = (icon: string) => {
    setAgentData(prev => ({ ...prev, icon }))
    handleIconClose()
  }

  const iconPopoverOpen = Boolean(iconAnchorEl)

  return (
    <div
      className="bg-gray-50 flex flex-col px-6 py-6"
      style={{
        width: '100%',
        maxWidth: '100vw',
        boxSizing: 'border-box',
      }}
    >
      {/* Header */}
      <div
        className="flex-shrink-0 bg-white flex items-center justify-between"
        style={{
          paddingLeft: 'clamp(0.5rem, 1vw, 1.25rem)',
          paddingRight: 'clamp(0.5rem, 1vw, 1.25rem)',
          paddingTop: 'clamp(0.25rem, 0.5vh, 0.5rem)',
          paddingBottom: 'clamp(0.25rem, 0.5vh, 0.5rem)',
          height: 'clamp(2rem, 4.5vh, 3rem)',
          minHeight: '2rem',
          boxSizing: 'border-box',
        }}
      >
        <Typography
          variant="h5"
          className="font-bold"
          sx={{
            color: '#191919',
            fontSize: 'clamp(0.875rem, 1.5vw, 1.25rem)',
            lineHeight: 1.2,
          }}
        >
          {t('title')}
        </Typography>
        <IconButton
          onClick={handleClose}
          size="small"
          className="hover:bg-gray-100"
          sx={{
            width: 'clamp(1.75rem, 3vw, 2.25rem)',
            height: 'clamp(1.75rem, 3vw, 2.25rem)',
            padding: 0,
          }}
        >
          <X
            className="text-gray-600"
            style={{
              width: 'clamp(1rem, 2vw, 1.5rem)',
              height: 'clamp(1rem, 2vw, 1.5rem)',
            }}
          />
        </IconButton>
      </div>

      {/* Main Content */}
      <div
        className="flex-shrink-0 flex flex-col lg:flex-row overflow-hidden"
        style={{
          minHeight: 0,
          boxSizing: 'border-box',
        }}
      >
        {/* Left Panel */}
        <div
          className="bg-white flex flex-col overflow-hidden"
          style={{
            flex: '1 1 35%',
            minWidth: 0,
            maxWidth: '100%',
            boxSizing: 'border-box',
          }}
        >
          <div
            className="flex-shrink-0 overflow-y-auto"
            style={{
              paddingLeft: 'clamp(0.5rem, 1vw, 1rem)',
              paddingRight: 'clamp(0.5rem, 1vw, 1rem)',
              paddingTop: 'clamp(0.375rem, 0.75vh, 0.75rem)',
              paddingBottom: '0',
              boxSizing: 'border-box',
            }}
          >
            <div
              className="flex flex-col"
              style={{
                gap: 'clamp(0.375rem, 0.9vh, 0.75rem)',
                width: '100%',
                boxSizing: 'border-box',
              }}
            >
              {/* Create Mode Selection */}
              <div className="flex-shrink-0">
                <Typography
                  variant="subtitle1"
                  className="font-normal"
                  sx={{
                    color: 'rgba(0, 0, 0, 0.9)',
                    fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                    marginBottom: 'clamp(0.25rem, 0.5vh, 0.5rem)',
                    lineHeight: 1.2,
                  }}
                >
                  {t('mode.label')}
                </Typography>
                <div
                  className="flex flex-col sm:flex-row"
                  style={{
                    gap: 'clamp(0.25rem, 0.6vw, 0.5rem)',
                    width: '100%',
                    boxSizing: 'border-box',
                  }}
                >
                  {/* Single React Agent Mode */}
                  <div
                    onClick={() => setAgentData(prev => ({ ...prev, mode: 'single-react-agent' }))}
                    className={`flex-1 border-2 rounded-lg cursor-pointer transition-all duration-200 ${
                      agentData.mode === 'single-react-agent' ? 'border-blue-500' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                    }`}
                    style={{
                      padding: 'clamp(0.5rem, 1vw, 0.875rem)',
                      minHeight: 'clamp(4.5rem, 10vh, 6.5rem)',
                      boxSizing: 'border-box',
                    }}
                  >
                    <div className="flex flex-col items-start h-full" style={{ gap: 'clamp(0.375rem, 0.75vh, 0.5rem)' }}>
                      <div
                        className="rounded-lg flex items-center justify-center transition-all duration-200 flex-shrink-0"
                        style={{
                          width: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                          height: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                        }}
                      >
                        <CreateAgentIcon
                          className="text-white"
                          style={{
                            width: '100%',
                            height: '100%',
                          }}
                        />
                      </div>
                      <div className="w-full flex-1 flex flex-col justify-center">
                        <Typography
                          variant="h6"
                          className="font-bold text-left"
                          sx={{
                            color: 'rgba(0, 0, 0, 0.9)',
                            fontSize: 'clamp(0.6875rem, 1.2vw, 0.875rem)',
                            marginBottom: 'clamp(0.125rem, 0.25vh, 0.25rem)',
                            lineHeight: 1.2,
                          }}
                        >
                          {MODE_INFO['single-react-agent'].name}
                        </Typography>
                        <Typography
                          variant="body2"
                          className="text-left"
                          sx={{
                            color: 'rgba(0, 0, 0, 0.4)',
                            fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)',
                            lineHeight: 1.3,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {MODE_INFO['single-react-agent'].description}
                        </Typography>
                      </div>
                    </div>
                  </div>

                  {/* Multi Workflow Mode */}
                  <div
                    onClick={() => setAgentData(prev => ({ ...prev, mode: 'multi-workflow' }))}
                    className={`flex-1 border-2 rounded-lg cursor-pointer transition-all duration-200 ${
                      agentData.mode === 'multi-workflow' ? 'border-blue-500' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                    }`}
                    style={{
                      padding: 'clamp(0.375rem, 0.75vw, 0.625rem)',
                      minHeight: 'clamp(4rem, 8.5vh, 5.5rem)',
                      boxSizing: 'border-box',
                    }}
                  >
                    <div className="flex flex-col items-start h-full" style={{ gap: 'clamp(0.25rem, 0.5vh, 0.375rem)' }}>
                      <div
                        className="rounded-lg flex items-center justify-center transition-all duration-200 flex-shrink-0"
                        style={{
                          width: 'clamp(1.5rem, 3vw, 2.25rem)',
                          height: 'clamp(1.5rem, 3vw, 2.25rem)',
                        }}
                      >
                        <CreateAgentWorkflowIcon
                          className="text-white"
                          style={{
                            width: '100%',
                            height: '100%',
                          }}
                        />
                      </div>
                      <div className="w-full flex-1 flex flex-col justify-center">
                        <Typography
                          variant="h6"
                          className="font-bold text-left"
                          sx={{
                            color: 'rgba(0, 0, 0, 0.9)',
                            fontSize: 'clamp(0.6875rem, 1.2vw, 0.875rem)',
                            marginBottom: 'clamp(0.125rem, 0.25vh, 0.25rem)',
                            lineHeight: 1.2,
                          }}
                        >
                          {MODE_INFO['multi-workflow'].name}
                        </Typography>
                        <Typography
                          variant="body2"
                          className="text-left"
                          sx={{
                            color: 'rgba(0, 0, 0, 0.4)',
                            fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)',
                            lineHeight: 1.3,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                          }}
                        >
                          {MODE_INFO['multi-workflow'].description}
                        </Typography>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Agent Name */}
              <div
                className="flex-shrink-0 flex flex-col sm:flex-row items-start sm:items-start"
                style={{
                  gap: 'clamp(0.25rem, 0.6vw, 0.5rem)',
                  width: '100%',
                  boxSizing: 'border-box',
                }}
              >
                <div className="flex-1 w-full relative" style={{ boxSizing: 'border-box' }}>
                  <div
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                      marginBottom: 'clamp(0.25rem, 0.4vh, 0.3rem)',
                    }}
                  >
                    <span className="text-red-500" style={{ fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)' }}>
                      *
                    </span>
                    <Typography
                      variant="subtitle1"
                      className="font-semibold"
                      sx={{
                        color: '#191919',
                        fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                        lineHeight: 1.2,
                      }}
                    >
                      {t('form.name.label')}
                    </Typography>
                  </div>
                  <TextField
                    fullWidth
                    required
                    value={agentData.name}
                    onChange={e => setAgentData(prev => ({ ...prev, name: e.target.value }))}
                    onBlur={() => {
                      if (!agentData.name.trim()) {
                        setErrors(prev => ({ ...prev, name: t('form.name.required') }))
                      } else {
                        setErrors(prev => ({ ...prev, name: undefined }))
                      }
                    }}
                    placeholder={t('form.name.placeholder')}
                    error={!!errors.name}
                    helperText={errors.name || ''}
                    inputProps={{ maxLength: 100 }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        paddingRight: 'clamp(2rem, 4vw, 3rem)',
                        fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                        height: 'clamp(2rem, 4vh, 2.75rem)',
                      },
                      '& .MuiInputBase-input': {
                        padding: 'clamp(0.3125rem, 0.625vh, 0.5rem) clamp(0.5rem, 1vw, 0.75rem)',
                      },
                      '& .MuiFormHelperText-root': {
                        fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)',
                        margin: '1px 0 0 0',
                      },
                    }}
                  />
                  <div
                    className="absolute pointer-events-none"
                    style={{
                      bottom: errors.name ? 'clamp(1.5rem, 2.5vh, 2rem)' : 'clamp(0.4rem, 1vh, 0.8rem)',
                      right: 'clamp(0.3125rem, 0.625vw, 0.5rem)',
                    }}
                  >
                    <Typography variant="body2" className="text-gray-500" sx={{ fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)' }}>
                      {agentData.name.length}/100
                    </Typography>
                  </div>
                </div>
                <div
                  className="flex items-center justify-center flex-shrink-0"
                  style={{
                    width: 'clamp(2.5rem, 5vw, 3.5rem)',
                    height: 'clamp(2.5rem, 5vw, 3.5rem)',
                    alignSelf: 'flex-start',
                    boxSizing: 'border-box',
                  }}
                >
                  <IconButton
                    onClick={handleIconClick}
                    className="w-full h-full hover:bg-gray-100 rounded-lg"
                    sx={{
                      borderRadius: '0.5rem',
                      padding: 0,
                      '&:hover': {
                        borderRadius: '0.5rem',
                      },
                    }}
                  >
                    <span
                      style={{
                        fontSize: 'clamp(1.25rem, 2.5vw, 2rem)',
                        lineHeight: 1,
                      }}
                    >
                      {agentData.icon}
                    </span>
                  </IconButton>
                </div>
                <Popover
                  open={iconPopoverOpen}
                  anchorEl={iconAnchorEl}
                  onClose={handleIconClose}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                  }}
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                  }}
                >
                  <div
                    style={{
                      padding: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                      maxWidth: 'clamp(20rem, 40vw, 30rem)',
                    }}
                  >
                    <Typography
                      variant="subtitle2"
                      className="font-semibold text-gray-800"
                      sx={{
                        fontSize: 'clamp(0.75rem, 1.2vw, 0.875rem)',
                        marginBottom: 'clamp(0.5rem, 1vh, 0.75rem)',
                      }}
                    >
                      {t('form.icon.title')}
                    </Typography>
                    <div
                      className="flex flex-wrap"
                      style={{
                        gap: 'clamp(0.375rem, 0.75vw, 0.5rem)',
                        maxHeight: 'clamp(12rem, 25vh, 18rem)',
                        overflowY: 'auto',
                      }}
                    >
                      {iconOptions.map((icon, index) => (
                        <IconButton
                          key={index}
                          onClick={() => handleIconSelect(icon)}
                          className={`hover:bg-gray-50 hover:shadow-sm transition-all duration-200 rounded-lg ${
                            agentData.icon === icon ? 'bg-blue-100 border-2 border-blue-500 shadow-sm scale-110' : 'hover:scale-105'
                          }`}
                          sx={{
                            borderRadius: '0.5rem',
                            width: 'clamp(2rem, 4vw, 3rem)',
                            height: 'clamp(2rem, 4vw, 3rem)',
                            fontSize: 'clamp(0.875rem, 1.75vw, 1.25rem)',
                            padding: 0,
                            '&:hover': {
                              borderRadius: '0.5rem',
                            },
                          }}
                        >
                          {icon}
                        </IconButton>
                      ))}
                    </div>
                  </div>
                </Popover>
              </div>

              {/* Agent Description */}
              <div className="flex-shrink-0 relative" style={{ boxSizing: 'border-box' }}>
                <div
                  className="flex items-center"
                  style={{
                    gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                    marginBottom: 'clamp(0.25rem, 0.4vh, 0.3rem)',
                  }}
                >
                  <span className="text-red-500" style={{ fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)' }}>
                    *
                  </span>
                  <Typography
                    variant="subtitle1"
                    className="font-semibold"
                    sx={{
                      color: '#191919',
                      fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                      lineHeight: 1.2,
                    }}
                  >
                    {t('form.description.label')}
                  </Typography>
                </div>
                <TextField
                  fullWidth
                  required
                  multiline
                  rows={descriptionRows}
                  value={agentData.description}
                  onChange={e => setAgentData(prev => ({ ...prev, description: e.target.value }))}
                  onBlur={() => {
                    if (!agentData.description.trim()) {
                      setErrors(prev => ({ ...prev, description: t('form.description.required') }))
                    } else {
                      setErrors(prev => ({ ...prev, description: undefined }))
                    }
                  }}
                  placeholder={t('form.description.placeholder')}
                  error={!!errors.description}
                  helperText={errors.description}
                  inputProps={{ maxLength: 500 }}
                  sx={{
                    marginBottom: 0,
                    '& .MuiOutlinedInput-root': {
                      padding: '1px !important',
                      fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                      '& .MuiInputBase-input': {
                        padding: 'clamp(0.5rem, 1vw, 0.75rem) !important',
                        paddingBottom: 'clamp(1.75rem, 3vh, 2rem) !important',
                      },
                      '& textarea': {
                        resize: 'vertical',
                        minHeight: 'clamp(2rem, 10vh, 45rem)',
                        maxHeight: descriptionMaxHeight,
                        padding: 'clamp(0.5rem, 1vw, 0.75rem) !important',
                        paddingBottom: 'clamp(1.75rem, 3vh, 2rem) !important',
                      },
                    },
                    '& .MuiFormHelperText-root': {
                      fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)',
                      margin: '1px 0 0 0',
                    },
                  }}
                />
                <div
                  className="absolute pointer-events-none"
                  style={{
                    bottom: errors.description ? 'clamp(1.0rem, 2.05vh, 1.275rem)' : 'clamp(0.1rem, 0.25vh, 0.425rem)',
                    right: 'clamp(0.5rem, 1vw, 0.75rem)',
                  }}
                >
                  <Typography variant="body2" className="text-gray-500" sx={{ fontSize: 'clamp(0.5625rem, 0.9vw, 0.6875rem)' }}>
                    {agentData.description.length}/500
                  </Typography>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons - Fixed at bottom */}
          <div
            className="flex-shrink-0 bg-white border-t lg:border-t-0 lg:border-r-0 border-gray-200"
            style={{
              paddingLeft: 'clamp(0.5rem, 1vw, 1rem)',
              paddingRight: 'clamp(0.5rem, 1vw, 1rem)',
              paddingTop: 'clamp(0.25rem, 0.5vh, 0.5rem)',
              paddingBottom: 'clamp(0.25rem, 0.5vh, 0.5rem)',
              height: 'clamp(2.5rem, 5vh, 3.25rem)',
              minHeight: '2.5rem',
              boxSizing: 'border-box',
            }}
          >
            <div className="flex justify-end h-full items-center" style={{ gap: 'clamp(0.25rem, 0.6vw, 0.5rem)' }}>
              <Button
                variant="outlined"
                onClick={handleCancel}
                sx={{
                  minWidth: 'clamp(3rem, 6vw, 4.5rem)',
                  height: 'clamp(1.75rem, 3.5vh, 2.25rem)',
                  fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                  padding: 'clamp(0.1875rem, 0.375vh, 0.3125rem) clamp(0.5rem, 1vw, 0.75rem)',
                  borderColor: '#C9C9C9',
                  color: '#191919',
                  '&:hover': {
                    borderColor: '#C9C9C9',
                    backgroundColor: 'rgba(201, 201, 201, 0.08)',
                  },
                }}
              >
                {t('actions.cancel')}
              </Button>
              <Button
                className="btn-primary"
                startIcon={
                  isLoading ? (
                    <Loader2
                      className="animate-spin"
                      style={{
                        width: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                        height: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                      }}
                    />
                  ) : undefined
                }
                onClick={handleConfirm}
                disabled={!agentData.name.trim() || !agentData.description.trim() || isLoading}
                sx={{
                  minWidth: 'clamp(3rem, 6vw, 4.5rem)',
                  height: 'clamp(1.75rem, 3.5vh, 2.25rem)',
                  fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                  padding: 'clamp(0.1875rem, 0.375vh, 0.3125rem) clamp(0.5rem, 1vw, 0.75rem)',
                }}
              >
                {isLoading ? t('actions.creating') : t('actions.create')}
              </Button>
            </div>
          </div>
        </div>

        {/* Right Panel - Mode Details */}
        <div
          className="hidden lg:flex bg-white border-l border-gray-200 flex-col overflow-hidden"
          style={{
            flex: '1 1 65%',
            minWidth: 0,
            maxWidth: '100%',
            boxSizing: 'border-box',
          }}
        >
          <div
            className="flex-shrink-0 overflow-y-auto"
            style={{
              padding: 'clamp(0.75rem, 1.5vw, 1.25rem)',
              boxSizing: 'border-box',
            }}
          >
            <div className="flex flex-col items-start" style={{ gap: 'clamp(0.375rem, 0.75vh, 0.625rem)' }}>
              {/* Name */}
              <Typography
                variant="h4"
                className="font-bold text-left"
                sx={{
                  color: 'rgba(0, 0, 0, 0.9)',
                  fontSize: 'clamp(0.9375rem, 1.6vw, 1.25rem)',
                  lineHeight: 1.3,
                }}
              >
                {selectedModeInfo.name}
              </Typography>

              {/* Description */}
              <Typography
                variant="body1"
                className="text-left"
                sx={{
                  color: 'rgba(0, 0, 0, 0.4)',
                  fontSize: 'clamp(0.6875rem, 1.1vw, 0.8125rem)',
                  lineHeight: 1.5,
                }}
              >
                {selectedModeInfo.detailDescription}
              </Typography>
            </div>

            {/* Example Image */}
            <div style={{ marginTop: 'clamp(1.2rem, 5vh, 2.5rem)' }}>
              <div
                className="rounded-lg overflow-hidden"
                style={{
                  width: '100%',
                  minHeight: 'clamp(15rem, 70vh, 75rem)',
                  boxSizing: 'border-box',
                }}
              >
                <img
                  src={agentData.mode === 'single-react-agent' ? reactPreviewImage : workflowPreviewImage}
                  alt={agentData.mode === 'single-react-agent' ? t('preview.singleReactAlt') : t('preview.multiWorkflowAlt')}
                  style={{
                    width: '100%',
                    height: '100%',
                    minHeight: 'clamp(15rem, 70vh, 75rem)',
                    objectFit: 'cover',
                    display: 'block',
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <UnifiedSnackbar
        snackbar={snackbar}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      />
    </div>
  )
}

export default AgentCreatePage
