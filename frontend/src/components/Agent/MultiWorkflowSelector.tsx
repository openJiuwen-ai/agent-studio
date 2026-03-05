import { styled } from '@mui/material/styles'
import ArrowForwardIosSharpIcon from '@mui/icons-material/ArrowForwardIosSharp'
import MuiAccordion, { AccordionProps } from '@mui/material/Accordion'
import MuiAccordionSummary, { AccordionSummaryProps, accordionSummaryClasses } from '@mui/material/AccordionSummary'
import MuiAccordionDetails from '@mui/material/AccordionDetails'
import Typography from '@mui/material/Typography'
import { AgentDetailResponse, SaveAgentRequest, useModels } from '@test-agentstudio/api-client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { ModelDetail, WorkflowDetail, WorkflowSelectDetail } from '../../types/agentTypes'
import { Button, Alert, TextField, Select, MenuItem, Box, IconButton, Popover, Tooltip } from '@mui/material'
import { Link } from 'react-router-dom'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import WorkflowSelector from './WorkflowSelector'
import { useAgentStore } from '@/stores/useAgentStore'
import AddButton from './AddButton'
import WorkflowList from './WorkflowList'
import ModelDetailForm from './ModelDetailForm'
import { useAuthStore } from '../../stores/useAuthStore'
import { AlertCircle, RefreshCcw } from 'lucide-react'
import { useWorkflowValidation } from '@/hooks/useWorkflowValidation'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { useScopedTranslation } from '@/i18n'

// 保留其他 Accordion 样式用于其他部分
const Accordion = styled((props: AccordionProps) => <MuiAccordion disableGutters elevation={0} square {...props} />)(({ theme }) => ({
  border: `1px solid ${theme.palette.divider}`,
  '&:not(:last-child)': {
    marginBottom: '8px',
  },
  '::before': {
    display: 'none',
  },
  backgroundColor: '#f9fafb',
  '&.Mui-expanded': {
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)', // 添加阴影效果
  },
}))

const AccordionSummary = styled((props: AccordionSummaryProps) => {
  // 提取children和其他props
  const { children, ...other } = props
  return (
    <MuiAccordionSummary expandIcon={<ArrowForwardIosSharpIcon sx={{ fontSize: '0.9rem' }} />} {...other}>
      <div style={{ display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="clickable-area" style={{ flexGrow: 1 }}>
          {Array.isArray(children) ? children[0] : children}
        </div>
        {Array.isArray(children) && children.length > 1 && (
          <div className="action-area" onClick={e => e.stopPropagation()} style={{ marginLeft: '16px' }}>
            {children.slice(1)}
          </div>
        )}
      </div>
    </MuiAccordionSummary>
  )
})(() => ({
  height: '50px',
  flexDirection: 'row-reverse',
  [`& .${accordionSummaryClasses.expandIconWrapper}.${accordionSummaryClasses.expanded}`]: {
    transform: 'rotate(90deg)',
  },
  [`& .${accordionSummaryClasses.content}`]: {
    marginLeft: '8px',
    width: '100%',
  },
}))

const AccordionDetails = styled(MuiAccordionDetails)(({ theme }) => ({
  padding: theme.spacing(2),
  borderTop: '1px solid rgba(0, 0, 0, .125)',
  backgroundColor: '#fff',
}))

const MultiWorkflowSelector = (props: { agentDetailResponse: AgentDetailResponse | null; saveAgentRequest: SaveAgentRequest }) => {
  const { agentDetailResponse, saveAgentRequest } = props
  const { updateWorkflowDetail, updateModelDetail, updateGreeting, updateSaveAgentRequest } = useAgentStore()
  const readonly = useAgentStore(s => s.readonly)
  const { user } = useAuthStore()
  const [selectedModelName, setSelectedModelName] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<ModelDetail | null>(null)
  const [modelsList, setModelsList] = useState<ModelDetail[]>([])
  const [modelExpanded, setModelExpanded] = useState<boolean>(true)

  // 使用 ref 来跟踪是否已经初始化
  const initializedRef = useRef(false)
  const [workflowObjects, setWorkflowObjects] = useState<WorkflowDetail[]>([])
  const [showWorkflowSelector, setShowWorkflowSelector] = useState(false)
  const [greeting, setGreeting] = useState<string>('')
  const [defaultResponse, setDefaultResponse] = useState<string>('')
  const [maxMessageRounds, setMaxMessageRounds] = useState<number>(3)
  const [conversationSettingsAnchorEl, setConversationSettingsAnchorEl] = useState<null | HTMLElement>(null)
  const [workflowListRefreshToken, setWorkflowListRefreshToken] = useState<number>(0)

  const spaceId = getDefaultSpaceId() || ''
  const maxGreetingLength = 2000
  const maxDefaultResponseLength = 2000

  const { validationResults, validateWorkflows, isValidating, workflowValidationErrorCount, cleanupDeletedWorkflows } = useWorkflowValidation({
    workflows: workflowObjects,
    spaceId,
  })

  const { t } = useScopedTranslation('agents.multiAgent')

  // 获取模型管理API的完整模型列表
  const { data: modelsData } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })

  useEffect(() => {
    if (!initializedRef.current) return
    const newWorkflows = saveAgentRequest?.workflows || []
    setWorkflowObjects(newWorkflows)
  }, [])

  // 将模型管理API的数据转换为ModelDetail格式
  useEffect(() => {
    if (modelsData?.items) {
      const convertedModels: ModelDetail[] = modelsData.items.map(model => ({
        model_id: parseInt(model.id),
        model_name: model.name,
        model_type: model.modelId,
        model_provider: model.provider,
        max_tokens: model.maxTokens,
        temperature: model.temperature,
        top_p: model.topp,
        timeout: model.timeout,
        retry_count: model.retryCount,
        enable_streaming: model.enableStreaming,
        enable_function_calling: model.enableFunctionCalling,
        is_active: model.isActive, // 使用转换后的 isActive 字段
        api_key: model.apiKey,
        api_base: model.baseUrl,
        streaming: model.enableStreaming,
      }))

      setModelsList(convertedModels)
    }
  }, [modelsData])

  // 当获取到 agentDetail 值时，初始化数据
  useEffect(() => {
    // 只在数据加载完成且未初始化时执行一次
    if (agentDetailResponse && agentDetailResponse.data && modelsData && !initializedRef.current) {
      initializedRef.current = true

      // 获取详情中的model数据,并做初始化
      const initModelInfo = saveAgentRequest?.model?.model_info || {}
      const initModelName = initModelInfo?.model_name || ''

      // 如果有模型列表且未选择模型，则默认选择第一个
      if (modelsList.length > 0 && !initModelName) {
        setSelectedModelName(modelsList[0].model_name)
        setSelectedModel(modelsList[0])
        // 修改store中的数据
        updateModelDetail(modelsList[0])
      }
      // 如果有已选择的模型名称，从模型列表中找到完整的模型信息并更新状态
      else if (initModelName && modelsList.length > 0) {
        const matchedModel = modelsList.find(model => model.model_name === initModelName)
        if (matchedModel) {
          setSelectedModelName(initModelName)
          // 合并模型列表中的默认值和保存的数据中的值
          // 优先使用保存的数据中的参数值（temperature、top_p、timeout），这些是用户实际保存的值
          const modelToUpdate: ModelDetail = {
            ...matchedModel,
            // 使用保存的数据中的参数值，这些值可能是用户修改过的
            temperature: initModelInfo?.temperature ?? matchedModel.temperature,
            top_p: initModelInfo?.top_p ?? matchedModel.top_p,
            timeout: initModelInfo?.timeout ?? matchedModel.timeout,
            max_tokens: initModelInfo?.max_tokens ?? matchedModel.max_tokens,
            // 保留其他保存的字段（如果存在）
            api_key: initModelInfo?.api_key || matchedModel.api_key,
            api_base: initModelInfo?.api_base || matchedModel.api_base,
            streaming: initModelInfo?.streaming ?? matchedModel.streaming,
          }
          setSelectedModel(modelToUpdate)
          updateModelDetail(modelToUpdate)
        } else {
          // 如果模型列表中没有找到匹配的模型，使用保存的数据
          setSelectedModelName(initModelName)
          const modelFromSaved = {
            model_name: initModelName,
            model_id: initModelInfo?.model_id || 0,
            model_type: initModelInfo?.model_type || '',
            model_provider: initModelInfo?.model_provider || initModelInfo?.provider || '',
            // 从保存的数据中恢复所有参数
            temperature: initModelInfo?.temperature ?? 0.7,
            top_p: initModelInfo?.top_p ?? 0.9,
            max_tokens: initModelInfo?.max_tokens ?? 4000,
            timeout: initModelInfo?.timeout ?? 3600,
            api_key: initModelInfo?.api_key || '',
            api_base: initModelInfo?.api_base || '',
            streaming: initModelInfo?.streaming ?? true,
            // 如果保存的数据中没有 is_active，默认为 true
            is_active: initModelInfo?.is_active !== undefined ? initModelInfo.is_active : true,
          }
          setSelectedModel(modelFromSaved)
          updateModelDetail(modelFromSaved)
        }
      } else if (initModelName) {
        // 模型列表为空但有保存的模型名称
        setSelectedModelName(initModelName)
        const modelFromSaved = {
          model_name: initModelName,
          model_id: initModelInfo?.model_id || 0,
          model_type: initModelInfo?.model_type || '',
          model_provider: initModelInfo?.model_provider || initModelInfo?.provider || '',
          // 从保存的数据中恢复所有参数
          temperature: initModelInfo?.temperature ?? 0.7,
          top_p: initModelInfo?.top_p ?? 0.9,
          max_tokens: initModelInfo?.max_tokens ?? 4000,
          timeout: initModelInfo?.timeout ?? 3600,
          api_key: initModelInfo?.api_key || '',
          api_base: initModelInfo?.api_base || '',
          streaming: initModelInfo?.streaming ?? true,
          // 如果保存的数据中没有 is_active，默认为 true
          is_active: initModelInfo?.is_active !== undefined ? initModelInfo.is_active : true,
        }
        setSelectedModel(modelFromSaved)
        updateModelDetail(modelFromSaved)
      }

      // 获取详情中的workflow数据
      const initWorkflows = saveAgentRequest?.workflows || []
      setWorkflowObjects(initWorkflows)

      // 初始化时验证所有工作流（只执行一次）
      if (initWorkflows.length > 0 && spaceId) {
        setTimeout(() => {
          const initIds = initWorkflows.map(w => w.workflow_id)
          validateWorkflows(initWorkflows, initIds).catch(() => {})
        }, 100)
      }

      // 获取详情中的开场白数据
      const initGreeting = saveAgentRequest?.opening_remarks || ''
      setGreeting(initGreeting)

      const initDefaultResponse = saveAgentRequest?.default_response || ''
      setDefaultResponse(initDefaultResponse)

      // 获取详情中的最大消息轮数 - 只在初始化时设置，避免循环依赖
      const currentMaxRounds = saveAgentRequest?.constraint?.reserved_max_chat_rounds
      if (currentMaxRounds !== undefined) {
        setMaxMessageRounds(currentMaxRounds)
      }
    }
  }, [agentDetailResponse, saveAgentRequest, modelsData])

  // 当模型列表更新时，如果当前选择的模型在列表中，更新为最新数据
  // 注意：只在初始化时同步，避免覆盖用户的修改
  useEffect(() => {
    if (selectedModelName && modelsList.length > 0 && !selectedModel) {
      // 只在 selectedModel 不存在时（初始化阶段）才从 modelsList 中获取
      const updatedModel = modelsList.find(model => model.model_name === selectedModelName)
      if (updatedModel) {
        setSelectedModel(updatedModel)
        updateModelDetail(updatedModel)
      }
    }
  }, [modelsList, selectedModelName])

  // 当模型列表加载完成后，如果未选择模型或模型列表为空，则自动展开折叠面板
  useEffect(() => {
    if (modelsList.length === 0 || !selectedModelName) {
      // 模型列表为空或未选择模型时展开
      setModelExpanded(true)
    } else if (selectedModelName) {
      // 如果已选择模型且模型列表不为空，可以折叠面板
      setModelExpanded(false)
    }
  }, [modelsList.length, selectedModelName]) // 使用 selectedModelName 而不是 selectedModel

  // 处理模型变化（选择）
  const handleModelChange = (modelName: string) => {
    setSelectedModelName(modelName)

    // 根据选择的模型名称找到对应的模型对象
    const selectedModelObj = modelsList.find(model => model.model_name === modelName)
    if (selectedModelObj) {
      setSelectedModel(selectedModelObj)

      // 选择模型后，自动折叠折叠面板
      setModelExpanded(false)

      // 修改store中的数据
      updateModelDetail(selectedModelObj)
    }
  }

  // 处理模型详细信息变化
  const handleModelDetailChange = (updatedModel: ModelDetail) => {
    // 更新本地状态，确保 UI 显示最新值，避免被 useEffect 重置
    setSelectedModel(updatedModel)
    // 修改store中的数据
    updateModelDetail(updatedModel)
  }

  // 处理折叠面板展开/收起状态变化
  const handleAccordionChange = (event: React.SyntheticEvent, isExpanded: boolean) => {
    setModelExpanded(isExpanded)
  }

  const handleWorkflowConfirm = (selectedIds: string[], newObjects: WorkflowSelectDetail[]) => {
    // 步骤1: 从 store 获取已存在的工作流详情
    const existingWorkflows = workflowObjects || []

    // 步骤2: 将 newObjects 转换为 WorkflowDetail 格式
    const newWorkflows: WorkflowDetail[] = newObjects.map(obj => ({
      workflow_id: obj.id,
      workflow_name: obj.name || '',
      workflow_version: obj.version || 'draft',  // 空字符串或 undefined 时默认为 'draft'
      description: obj.desc || '',
    }))

    // 步骤3: 合并所有来源的工作流详情
    const allWorkflows: WorkflowDetail[] = [
      // 保留 existingWorkflows 中仍在 selectedIds 中的
      ...existingWorkflows.filter(w => selectedIds.includes(w.workflow_id)),
      // 添加从 WorkflowSelector 传递的新增详情
      ...newWorkflows,
    ]

    // 步骤4: 更新状态
    setWorkflowObjects(allWorkflows)
    updateWorkflowDetail(allWorkflows)
    setShowWorkflowSelector(false)

    // 步骤5: 只对新增的工作流进行验证
    if (newWorkflows.length > 0) {
      setTimeout(() => {
        const newIds = newWorkflows.map(w => w.workflow_id)
        validateWorkflows(allWorkflows, newIds).catch(() => {})
      }, 100)
    }
  }

  // 处理工作流操作（删除/设置）
  const handleWorkflowOperation = (operate: 'delete' | 'setting', workflowId: string, version?: string) => {
    if (operate === 'delete') {
      setWorkflowObjects(prevWorkflows => {
        const updatedWorkflows = prevWorkflows.filter(workflow => workflow.workflow_id !== workflowId)
        updateWorkflowDetail(updatedWorkflows)
        // 清理已删除工作流的验证结果
        cleanupDeletedWorkflows(updatedWorkflows)
        return updatedWorkflows
      })
    } else if (operate === 'setting') {
      // 处理设置操作，打开新页面设置工作流，携带版本信息
      const versionParam = version && version !== 'draft' ? `&version=${version}` : ''
      window.open(`/dashboard/workflows/editor/${workflowId}?spaceId=${spaceId}${versionParam}`, '_blank')
    }
  }

  // 处理工作流版本切换
  const handleWorkflowVersionChange = (workflowId: string, version: string) => {
    setWorkflowObjects(prev => {
      const updated = prev.map(w => (w.workflow_id === workflowId ? { ...w, workflow_version: version } : w))
      // 触发验证
      validateWorkflows(updated, [workflowId]).catch(() => {})
      return updated
    })
  }

  const handleRefreshWorkflows = useCallback(() => {
    setWorkflowListRefreshToken(t => t + 1)
    validateWorkflows(workflowObjects).catch(() => {})
  }, [validateWorkflows, workflowObjects])

  // 处理最大消息轮数变化
  const handleMaxMessageRoundsChange = (value: number) => {
    setMaxMessageRounds(value)
    updateSaveAgentRequest({
      constraint: {
        ...(saveAgentRequest?.constraint || {}),
        reserved_max_chat_rounds: value,
        max_iteration: saveAgentRequest?.constraint?.max_iteration || 10,
      },
    })
  }

  // 处理对话设置关闭
  const handleConversationSettingsClose = () => {
    setConversationSettingsAnchorEl(null)
  }

  return (
    <div className="h-full overflow-auto">
      <div className="workflow-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('sections.orchestrationTitle')}</Typography>
        <Accordion defaultExpanded={true}>
          <AccordionSummary aria-controls="workflow-content" id="workflow-header">
            <Typography component="span" className="flex items-center">
              {t('sections.workflowTitle')}
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${workflowObjects.length > 0 ? 'bg-blue-500' : 'bg-gray-400'}`}
              >
                {workflowObjects.length}
              </span>
              {workflowValidationErrorCount > 0 && (
                <Tooltip title={t('workflowValidation.tooltip', { count: workflowValidationErrorCount })} arrow>
                  <span className="inline-flex items-center ml-2">
                    <AlertCircle className="w-[20px] h-[20px] text-red-500" />
                  </span>
                </Tooltip>
              )}
            </Typography>
            <div className="action-area" onClick={e => e.stopPropagation()} style={{ marginLeft: '16px', display: 'flex', gap: '8px' }}>
              {/* <Tooltip title={t('sections.conversationTitle')} arrow>
                <IconButton
                  size="small"
                  onClick={handleConversationSettingsClick}
                  disabled={readonly}
                  sx={{
                    color: 'text.secondary',
                    '&:hover': { color: 'primary.main' },
                    '&.Mui-disabled': { cursor: 'not-allowed' },
                  }}
                >
                  <SettingsIcon fontSize="small" />
                </IconButton>
              </Tooltip> */}
              <Tooltip title={t('refreshWorkflows.tooltip')} arrow>
                <span>
                  <IconButton size="small" onClick={handleRefreshWorkflows} disabled={workflowObjects.length === 0} aria-label={t('refreshWorkflows.ariaLabel')}>
                    <RefreshCcw className={`w-4 h-4 ${isValidating ? 'animate-spin' : ''}`} />
                  </IconButton>
                </span>
              </Tooltip>
              <AddButton
                options={[
                  { label: t('addButton.addExistingWorkflow'), value: 'existing' },
                  { label: t('addButton.createNewWorkflow'), value: 'new' },
                ]}
                onSelect={addType => {
                  if (addType === 'existing') {
                    // 打开工作流选择器
                    setShowWorkflowSelector(true)
                  } else if (addType === 'new') {
                    // 创建工作流的逻辑，在新页面打开
                    window.open('/dashboard/workflows/new', '_blank')
                  }
                }}
                disabled={readonly}
              />
            </div>
          </AccordionSummary>
          <AccordionDetails>
            {/* 工作流列表 */}
            <WorkflowList
              workflowObjects={workflowObjects}
              onClick={handleWorkflowOperation}
              disabled={readonly}
              refreshToken={workflowListRefreshToken}
              validationResults={validationResults}
              onVersionChange={handleWorkflowVersionChange}
            />
            {workflowObjects.length === 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                {t('alerts.noWorkflow')}
              </Alert>
            )}
          </AccordionDetails>
        </Accordion>
      </div>
      <div className="model-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('sections.modelTitle')}</Typography>
        <Accordion expanded={modelExpanded} onChange={handleAccordionChange}>
          <AccordionSummary aria-controls="model-content" id="model-header">
            <Typography component="span">{t('sections.modelTitle')}</Typography>
            {modelsList.length > 0 ? (
              <div onClick={e => e.stopPropagation()} onKeyDown={e => e.stopPropagation()}>
                <Select
                  value={selectedModelName || ''}
                  onChange={event => handleModelChange(event.target.value as string)}
                  displayEmpty
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        maxHeight: 320,
                        width: 360,
                        borderRadius: 2,
                      },
                    }
                  }}
                  renderValue={value => {
                    // 如果选择的模型不在可用列表中，显示提示
                    if (value && !modelsList.find(model => model.model_name === value && model.is_active)) {
                      return <span style={{ color: '#d32f2f' }}>{t('select.disabledModel', { name: value })}</span>
                    }
                    return value ? (
                      <span
                        title={String(value)}
                        style={{
                          display: 'block',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {String(value)}
                      </span>
                    ) : (
                      <span style={{ color: 'rgba(0, 0, 0, 0.38)' }}>{t('select.placeholder')}</span>
                    )
                  }}
                  sx={{
                    width: 200,
                    height: 30,
                    '&.Mui-disabled': { cursor: 'not-allowed' },
                    '& .MuiOutlinedInput-root.Mui-disabled': { cursor: 'not-allowed' },
                    '& .MuiSelect-select.Mui-disabled': { cursor: 'not-allowed' },
                  }}
                  disabled={readonly}
                >
                  {modelsList
                    .filter(model => model.is_active)
                    .map(model => (
                      <MenuItem key={model.model_name} value={model.model_name}>
                        <span style={{ display: 'block', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {model.model_name}
                        </span>
                      </MenuItem>
                    ))}
                </Select>
              </div>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                {t('alerts.noModelsInline')}
              </Typography>
            )}
          </AccordionSummary>
          <AccordionDetails>
            {modelsList.length > 0 ? (
              <>
                {selectedModelName && !modelsList.find(model => model.model_name === selectedModelName && model.is_active) ? (
                  <Alert
                    severity="warning"
                    action={
                      <Button
                        color="primary"
                        size="small"
                        component={Link}
                        to="/dashboard/models"
                        disabled={readonly}
                        sx={{ '&.Mui-disabled': { cursor: 'not-allowed' } }}
                      >
                        {t('alerts.modelDisabledAction')}
                      </Button>
                    }
                  >
                    {t('alerts.modelDisabledMessage', { name: selectedModelName })}
                  </Alert>
                ) : !selectedModel ? (
                  <Alert
                    severity="info"
                    action={
                      <Button color="primary" size="small" onClick={() => setModelExpanded(true)} sx={{ mt: -1 }}>
                        {t('alerts.noModelSelectedAction')}
                      </Button>
                    }
                  >
                    {t('alerts.noModelSelectedMessage')}
                  </Alert>
                ) : (
                  selectedModel && <ModelDetailForm modelDetail={selectedModel} onModelDetailChange={handleModelDetailChange} readonly={readonly} />
                )}
              </>
            ) : (
              <Alert
                severity="info"
                action={
                  <Button
                    color="primary"
                    size="small"
                    component={Link}
                    to="/dashboard/models"
                    disabled={readonly}
                    sx={{ '&.Mui-disabled': { cursor: 'not-allowed' } }}
                  >
                    {t('alerts.noModelsConfiguredAction')}
                  </Button>
                }
              >
                {t('alerts.noModelsConfiguredMessage')}
              </Alert>
            )}
          </AccordionDetails>
        </Accordion>
        <Accordion defaultExpanded={true}>
          <AccordionSummary aria-controls="default-response-content" id="default-response-header">
            <Typography component="span">{t('sections.defaultResponseTitle')}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              value={defaultResponse}
              onChange={e => {
                const val = e.target.value
                setDefaultResponse(val)
                updateSaveAgentRequest({
                  default_response: val,
                })
              }}
              fullWidth
              multiline
              rows={4}
              placeholder={t('defaultResponse.placeholder')}
              disabled={readonly}
              inputProps={{ maxLength: maxDefaultResponseLength }}
              helperText={`${defaultResponse.length}/${maxDefaultResponseLength}`}
              sx={{
                '& .MuiInputBase-root.Mui-disabled': { cursor: 'not-allowed' },
                '& .MuiInputBase-input.Mui-disabled': { cursor: 'not-allowed' },
              }}
            />
          </AccordionDetails>
        </Accordion>
      </div>
      <div className="dialog-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('sections.conversationTitle')}</Typography>
        <Accordion defaultExpanded={true}>
          <AccordionSummary aria-controls="greeting-content" id="greeting-header">
            <Typography component="span">{t('sections.greetingTitle')}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              value={greeting}
              onChange={e => {
                setGreeting(e.target.value)
                updateGreeting(e.target.value)
              }}
              inputProps={{ maxLength: maxGreetingLength }}
              helperText={`${greeting.length}/${maxGreetingLength}`}
              fullWidth
              multiline
              rows={4}
              placeholder={t('greeting.placeholder')}
              disabled={readonly}
              sx={{
                '& .MuiInputBase-root.Mui-disabled': { cursor: 'not-allowed' },
                '& .MuiInputBase-input.Mui-disabled': { cursor: 'not-allowed' },
              }}
            />
          </AccordionDetails>
        </Accordion>
      </div>
      {showWorkflowSelector && !readonly && (
        <WorkflowSelector
          open={showWorkflowSelector}
          onClose={() => setShowWorkflowSelector(false)}
          onConfirm={handleWorkflowConfirm}
          initialSelected={workflowObjects.map(workflow => workflow.workflow_id)}
        />
      )}

      {/* 对话设置 Popover */}
      <Popover
        open={Boolean(conversationSettingsAnchorEl)}
        anchorEl={conversationSettingsAnchorEl}
        onClose={handleConversationSettingsClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        PaperProps={{
          sx: {
            p: 2,
            minWidth: 280,
            maxWidth: 320,
          },
        }}
      >
        <Typography variant="h6" sx={{ mb: 1, fontSize: '1rem' }}>
          {t('popover.title')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('popover.description')}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton
            onClick={() => handleMaxMessageRoundsChange(Math.max(0, maxMessageRounds - 1))}
            disabled={readonly || maxMessageRounds <= 0}
            size="small"
            sx={{
              width: 28,
              height: 28,
              color: 'text.secondary',
              '&.Mui-disabled': { color: 'action.disabled' },
            }}
          >
            <RemoveIcon fontSize="small" />
          </IconButton>

          <TextField
            value={maxMessageRounds}
            onChange={e => {
              const inputValue = e.target.value.trim()

              // 允许空字符串（用户正在删除输入）
              if (inputValue === '') {
                return
              }

              // 检查是否只包含数字
              if (!/^\d+$/.test(inputValue)) {
                return
              }

              // 转换为数字，支持0值
              const value = parseInt(inputValue, 10)

              // 验证范围：0-100，且为有效数字
              if (!isNaN(value) && value >= 0 && value <= 100) {
                handleMaxMessageRoundsChange(value)
              }
            }}
            onBlur={e => {
              // 失焦时确保有有效值，如果没有则设置为0
              const inputValue = e.target.value.trim()
              if (inputValue === '') {
                handleMaxMessageRoundsChange(0)
              } else if (/^\d+$/.test(inputValue)) {
                const value = parseInt(inputValue, 10)
                if (!isNaN(value) && value >= 0 && value <= 100) {
                  handleMaxMessageRoundsChange(value)
                } else {
                  handleMaxMessageRoundsChange(0)
                }
              } else {
                handleMaxMessageRoundsChange(0)
              }
            }}
            type="text"
            inputProps={{
              inputMode: 'numeric',
              pattern: '[0-9]*',
              min: 0,
              max: 100,
              style: {
                textAlign: 'center',
                fontSize: '14px',
                padding: '4px 8px',
                height: '28px',
              },
            }}
            disabled={readonly}
            sx={{
              width: 60,
              '& .MuiOutlinedInput-root': {
                '& fieldset': {
                  borderColor: 'rgba(0, 0, 0, 0.23)',
                },
                '&:hover fieldset': {
                  borderColor: 'rgba(0, 0, 0, 0.87)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: 'primary.main',
                },
                '&.Mui-disabled fieldset': {
                  borderColor: 'rgba(0, 0, 0, 0.12)',
                },
              },
              '& .MuiInputBase-input': {
                height: '20px',
                padding: '4px 8px !important',
              },
              '& .MuiFormHelperText-root': {
                display: 'none',
              },
            }}
          />

          <IconButton
            onClick={() => handleMaxMessageRoundsChange(Math.min(100, maxMessageRounds + 1))}
            disabled={readonly || maxMessageRounds >= 100}
            size="small"
            sx={{
              width: 28,
              height: 28,
              color: 'text.secondary',
              '&.Mui-disabled': { color: 'action.disabled' },
            }}
          >
            <AddIcon fontSize="small" />
          </IconButton>

          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            {t('popover.maxRoundsLabel')}
          </Typography>
        </Box>
      </Popover>
    </div>
  )
}

export default MultiWorkflowSelector
