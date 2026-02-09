import { styled } from '@mui/material/styles'
import ArrowForwardIosSharpIcon from '@mui/icons-material/ArrowForwardIosSharp'
import MuiAccordion, { AccordionProps } from '@mui/material/Accordion'
import MuiAccordionSummary, { AccordionSummaryProps, accordionSummaryClasses } from '@mui/material/AccordionSummary'
import MuiAccordionDetails from '@mui/material/AccordionDetails'
import Typography from '@mui/material/Typography'
import { AgentDetailResponse, AgentPlugin, SaveAgentRequest, useModels, KnowledgeBaseService, type PluginApiInfo, MemoryBaseService } from '@test-agentstudio/api-client'
import { useState, useEffect, useCallback, useRef } from 'react'
import { AlertCircle, RefreshCcw, Trash2, Settings } from 'lucide-react'
import { ModelDetail, WorkflowDetail, WorkflowSelectDetail } from '../../types/agentTypes'
import { Select, Button, Alert, MenuItem, TextField, Box, IconButton, List, ListItem, ListItemText, Switch, FormControlLabel, Tooltip, Popover, RadioGroup, Radio, Slider } from '@mui/material'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import { Link } from 'react-router-dom'
import ModelDetailForm from './ModelDetailForm'
import WorkflowSelector from './WorkflowSelector'
import { useAgentStore } from '@/stores/useAgentStore'
import PluginSelector from '../../../packages/workflow-canvas/src/components/PluginSelector'
import AddButton from './AddButton'
import WorkflowList from './WorkflowList'
import PluginList from './PluginList'
import KnowledgeBaseSelector from './KnowledgeBaseSelector'
import KnowledgeBaseList from './KnowledgeBaseList'
import MemoryBaseSelector from './MemoryBaseSelector'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { useAuthStore } from '../../stores/useAuthStore'
import axios from 'axios'
import { useWorkflowValidation } from '@/hooks/useWorkflowValidation'
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
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
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

const AccordionDetails = styled(MuiAccordionDetails)(() => ({
  padding: 16,
  borderTop: '1px solid rgba(0, 0, 0, .125)',
  backgroundColor: '#fff',
}))

// 记忆变量类型定义 - 描述、默认值设为可选，增加启用状态
interface MemoryVariable {
  id: string
  name: string
  description?: string
  enabled?: boolean // 新增：是否启用，默认 true
}

// 记忆库项类型定义
interface MemoryBaseItem {
  mdb_id: string;
  name: string;
  status: string;
  description?: string;
  embedding_model_config_id?: number;
  llm_model_config_id?: number;
}

const api = {
  deleteUserVariable: async (user_id: string, group_id: string, key: string) => {
    await axios.post('/api/v1/execution/memory/delete_user_variable', {
      user_id: user_id,
      group_id: group_id,
      name: key,
    })
  },
}

const AgentModelSelector = (props: {
  agentDetailResponse: AgentDetailResponse | null
  saveAgentRequest: SaveAgentRequest
  onLongTermChange?: (enabled: boolean) => void
}) => {
  const { agentDetailResponse, saveAgentRequest, onLongTermChange } = props
  const { updateModelDetail, updateWorkflowDetail, updatePluginDetail, updateKnowledgeDetail, updateRetrievalConfig, updateGreeting, updateMemoryConfig, updateSaveAgentRequest } = useAgentStore()
  const readonly = useAgentStore(s => s.readonly)
  const { user } = useAuthStore()
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  const user_id = saveAgentRequest?.space_id || ''
  const group_id = saveAgentRequest?.agent_id || ''

  const [selectedModelName, setSelectedModelName] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<ModelDetail | null>(null)
  const [modelsList, setModelsList] = useState<ModelDetail[]>([])
  const [modelExpanded, setModelExpanded] = useState<boolean>(false)

  // 使用 ref 来跟踪是否已经初始化
  const initializedRef = useRef(false)

  // 获取模型管理API的完整模型列表
  const { data: modelsData } = useModels({
    spaceId: user?.spaceId || '0',
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })
  const [workflowObjects, setWorkflowObjects] = useState<WorkflowDetail[]>([])
  const [showWorkflowSelector, setShowWorkflowSelector] = useState(false)
  const [workflowListRefreshToken, setWorkflowListRefreshToken] = useState<number>(0)
  const [pluginObjects, setPluginObjects] = useState<AgentPlugin[]>([])
  const [showPluginSelector, setShowPluginSelector] = useState(false)
  const [knowledgeBaseObjects, setKnowledgeBaseObjects] = useState<Array<{ id: string; name: string; description?: string; has_graph_enhancement?: boolean }>>([])
  const [showKnowledgeBaseSelector, setShowKnowledgeBaseSelector] = useState(false)
  const [knowledgeSettingsAnchorEl, setKnowledgeSettingsAnchorEl] = useState<HTMLElement | null>(null)
  const [greeting, setGreeting] = useState<string>('')

  // 记忆库相关状态
  const [memoryBaseObject, setMemoryBaseObject] = useState<MemoryBaseItem | null>(null)
  const [showMemoryBaseSelector, setShowMemoryBaseSelector] = useState(false)

  const spaceId = getDefaultSpaceId() || ''
  const maxGreetingLength = 2000

  const { validationResults, setValidationResults, validateWorkflows, isValidating, workflowValidationErrorCount } = useWorkflowValidation({
    workflows: workflowObjects,
    spaceId,
  })

  useEffect(() => {
    if (!initializedRef.current) return
    const newWorkflows = saveAgentRequest?.workflows || []
    setWorkflowObjects(newWorkflows)
  }, [saveAgentRequest?.workflows])

  useEffect(() => {
    if (!initializedRef.current) return
    if (!spaceId) return
    const t = setTimeout(() => {
      validateWorkflows(workflowObjects).catch(() => {})
    }, 200)
    return () => clearTimeout(t)
  }, [workflowObjects, spaceId, validateWorkflows])

  // 知识库设置状态
  const [graphEnhancement, setGraphEnhancement] = useState<'off' | 'normal' | 'agent'>('off')
  const [graphRetrievalStrategy, setGraphRetrievalStrategy] = useState<'base' | 'agentic'>('base')
  const [enableGraphRetrieval, setEnableGraphRetrieval] = useState<boolean>(false)
  // 检查是否有图增强文档
  const hasGraphEnhancementDocs = knowledgeBaseObjects.some(kb => kb.has_graph_enhancement)
  const [retrievalSource, setRetrievalSource] = useState<'hybrid' | 'text' | 'triple'>('hybrid')
  const [maxRecallCount, setMaxRecallCount] = useState<number>(5)
  const [minMatchScore, setMinMatchScore] = useState<number>(0.5)
  // 使用 ref 保存最小匹配分数的原始输入字符串（用于处理中间状态如 "0."）
  const minMatchScoreInputRef = useRef<string>('')

  // 使用 ref 跟踪是否已经初始化完成，避免初始化时触发保存
  const isRetrievalConfigInitializedRef = useRef(false)

  // 记忆配置状态
  const [memoryVariables, setMemoryVariables] = useState<MemoryVariable[]>([])
  const [longTermMemoryEnabled, setLongTermMemoryEnabled] = useState<boolean>(false)
  const [newVariableName, setNewVariableName] = useState<string>('')
  const [newVariableDescription, setNewVariableDescription] = useState<string>('')
  const [duplicateVariableWarning, setDuplicateVariableWarning] = useState<string>('')

  // 限制配置状态
  const [maxIteration, setMaxIteration] = useState<number>(5)
  const [maxMessageRounds, setMaxMessageRounds] = useState<number>(10)

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
        is_active: model.isActive,
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
          setSelectedModel(matchedModel)
          updateModelDetail(matchedModel)
        } else {
          // 如果模型列表中没有找到匹配的模型，仍然设置名称但使用保存的数据
          setSelectedModelName(initModelName)
          // 创建一个包含保存的模型信息的对象
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
            // 优先使用模型列表中的 is_active，如果没有则使用保存的值
            is_active: initModelInfo?.is_active !== undefined ? initModelInfo.is_active : true,
          } as ModelDetail
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
        } as ModelDetail
        setSelectedModel(modelFromSaved)
        updateModelDetail(modelFromSaved)
      }

      // 获取详情中的workflow数据
      const initWorkflows = saveAgentRequest?.workflows || []
      setWorkflowObjects(initWorkflows)

      // 获取详情中的plugin数据
      const initPlugins = saveAgentRequest?.plugins || []
      setPluginObjects(initPlugins)

      // 获取详情中的开场白数据
      const initGreeting = saveAgentRequest?.opening_remarks || ''
      setGreeting(initGreeting)

      // 获取记忆配置数据
      const initVariables = saveAgentRequest?.memory?.variable_config || []
      const initLongTermMemory = saveAgentRequest?.memory?.longterm_memory_config || false

      setMemoryVariables(
        initVariables.map((v: { id?: string; name?: string; description?: string; enabled?: boolean }, index: number) => ({
          id: v.id || `var_${Date.now()}_${index}`,
          name: v.name || '',
          description: v.description || '',
          enabled: v.enabled !== undefined ? v.enabled : true, // 默认启用
        })),
      )
      setLongTermMemoryEnabled(initLongTermMemory)

      // 初始化限制配置
      const initMaxIteration = saveAgentRequest?.constraint?.max_iteration ?? 5
      const initMaxRounds = saveAgentRequest?.constraint?.reserved_max_chat_rounds ?? 10
      setMaxIteration(initMaxIteration)
      setMaxMessageRounds(initMaxRounds)

      // 初始化检索配置
      const retrievalConfig = saveAgentRequest?.configs?.retrieval_config as { use_agent?: boolean; use_sync?: boolean; source?: number; topk?: number; score_threshold?: number | null } | undefined
      if (retrievalConfig) {
        // 根据 use_agent 和 use_sync 判断图检索策略
        if (retrievalConfig.use_agent) {
          setGraphRetrievalStrategy('agentic')
          setGraphEnhancement('agent')
          setEnableGraphRetrieval(true)
        } else if (retrievalConfig.use_sync) {
          setGraphRetrievalStrategy('base')
          setGraphEnhancement('normal')
          setEnableGraphRetrieval(true)
        } else {
          setGraphRetrievalStrategy('base')
          setGraphEnhancement('off')
          setEnableGraphRetrieval(false)
        }

        // 映射 source 数字到字符串
        const sourceMap: Record<number, 'hybrid' | 'text' | 'triple'> = { 1: 'hybrid', 2: 'text', 3: 'triple' }
        setRetrievalSource(sourceMap[retrievalConfig.source || 1] || 'hybrid')
        setMaxRecallCount(retrievalConfig.topk || 5)
        setMinMatchScore(retrievalConfig.score_threshold || 0.5)
      }
      // 标记初始化完成
      isRetrievalConfigInitializedRef.current = true
    }
  }, [agentDetailResponse, saveAgentRequest, modelsData])

  // 使用 ref 来跟踪知识库是否已经初始化
  const knowledgeBaseInitializedRef = useRef(false)
  const lastAgentIdRef = useRef<string | null>(null)

  // 初始化知识库列表，使用列表API获取知识库信息
  useEffect(() => {
    if (!agentDetailResponse || !agentDetailResponse.data) {
      return
    }

    // 如果切换了智能体，重置初始化标记
    const currentAgentId = agentDetailResponse.data.agent_info?.agent_id
    if (currentAgentId && lastAgentIdRef.current !== currentAgentId) {
      knowledgeBaseInitializedRef.current = false
      lastAgentIdRef.current = currentAgentId
    }

    // 只在初始化时执行一次
    if (knowledgeBaseInitializedRef.current) {
      return
    }

    const initKnowledgeIds = saveAgentRequest?.knowledge || []
    if (initKnowledgeIds.length > 0) {
      // 调用列表API获取知识库信息
      const fetchKnowledgeBaseInfo = async () => {
        try {
          const spaceId = getDefaultSpaceId()
          if (!spaceId) {
            // 如果没有spaceId，只使用ID
            setKnowledgeBaseObjects(initKnowledgeIds.map(id => ({ id, name: id, description: undefined })))
            knowledgeBaseInitializedRef.current = true
            return
          }

          // 调用列表API，获取足够多的知识库（假设最多100个）
          const response = await KnowledgeBaseService.getKnowledgeBases({
            space_id: spaceId,
            page: 1,
            size: 100,
          })

          if (response.code === 200 && response.data?.items) {
            // 创建ID到知识库信息的映射
            const kbMap = new Map<string, { name: string; desc: string | null; has_graph_enhancement?: boolean }>()
            response.data.items.forEach((item: { id: string; name: string; desc: string | null; has_graph_enhancement?: boolean }) => {
              kbMap.set(item.id, { name: item.name, desc: item.desc, has_graph_enhancement: item.has_graph_enhancement })
            })

            // 根据ID列表匹配知识库信息
            const knowledgeBaseObjects = initKnowledgeIds.map(id => {
              const kbInfo = kbMap.get(id)
              if (kbInfo) {
                return {
                  id,
                  name: kbInfo.name,
                  description: kbInfo.desc || undefined,
                  has_graph_enhancement: kbInfo.has_graph_enhancement,
                }
              }
              // 如果找不到，使用ID作为名称
              return { id, name: id, description: undefined, has_graph_enhancement: false }
            })
            setKnowledgeBaseObjects(knowledgeBaseObjects)
          } else {
            // API调用失败，只使用ID
            setKnowledgeBaseObjects(initKnowledgeIds.map(id => ({ id, name: id, description: undefined })))
          }
          knowledgeBaseInitializedRef.current = true
        } catch (error) {
          console.error('获取知识库列表失败:', error)
          // 出错时，只使用ID
          setKnowledgeBaseObjects(initKnowledgeIds.map(id => ({ id, name: id, description: undefined })))
          knowledgeBaseInitializedRef.current = true
        }
      }
      fetchKnowledgeBaseInfo()
    } else {
      setKnowledgeBaseObjects([])
      knowledgeBaseInitializedRef.current = true
    }
  }, [agentDetailResponse, saveAgentRequest?.knowledge])

  // 初始化记忆库列表
  useEffect(() => {
    if (!agentDetailResponse || !agentDetailResponse.data) {
      return
    }
    const initMemoryBase = saveAgentRequest?.memory?.memory_base;
    const initMemoryBaseId = initMemoryBase ? initMemoryBase.mdb_id : null;

    if (initMemoryBaseId) {
      const fetchMemoryBaseInfo = async () => {
        try {
          const spaceId = getDefaultSpaceId();
          if (!spaceId) {
            setMemoryBaseObject({ mdb_id: initMemoryBaseId, name: initMemoryBaseId, description: undefined, status: "active" });
            return;
          }

          const response = await MemoryBaseService.getMemoryBases({
            space_id: spaceId,
            page: 1,
            page_size: 100,
          });

          if (response.code === 200 && response.data?.items) {
            const mbMap = new Map<string, MemoryBaseItem>();
            response.data.items.forEach((item: MemoryBaseItem) => {
              mbMap.set(item.mdb_id, item);
            });

            const mbInfo = mbMap.get(initMemoryBaseId);
            if (mbInfo) {
              setMemoryBaseObject(mbInfo);
            } else {
              setMemoryBaseObject(null);
              if (saveAgentRequest?.memory) {
                updateMemoryConfig({
                  max_tokens: 1000,
                  variable_config: memoryVariables,
                  longterm_memory_config: longTermMemoryEnabled,
                  memory_base: undefined, // ✅ 清空
                });
              }
            }
          } else {
            setMemoryBaseObject({ mdb_id: initMemoryBaseId, name: initMemoryBaseId, description: undefined, status: "active" });
          }
        } catch (error) {
          console.error('获取记忆库列表失败:', error);
          setMemoryBaseObject({ mdb_id: initMemoryBaseId, name: initMemoryBaseId, description: undefined, status: "active" });
        }
      };
      fetchMemoryBaseInfo();
    } else {
      setMemoryBaseObject(null); // ✅ 初始为空
    }
  }, [agentDetailResponse, saveAgentRequest?.memory?.memory_bases]);

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
  }, [modelsList.length, selectedModelName])

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
  const handleAccordionChange = (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setModelExpanded(isExpanded)
  }

  // 处理最大迭代次数变化
  const handleMaxIterationChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(event.target.value, 10)
    if (!isNaN(val)) {
      let finalVal = val
      if (val > 50) finalVal = 50
      
      if (finalVal >= 1) {
        setMaxIteration(finalVal)
        updateSaveAgentRequest({
          constraint: {
            ...(saveAgentRequest?.constraint || {}),
            max_iteration: finalVal,
            reserved_max_chat_rounds: maxMessageRounds,
          },
        })
      } else {
        setMaxIteration(finalVal)
      }
    } else if (event.target.value === '') {
       setMaxIteration(-1)
    }
  }

  // 处理最大迭代次数失去焦点
  const handleMaxIterationBlur = () => {
    if (maxIteration === -1 || maxIteration < 1) {
      const finalVal = maxIteration === -1 ? 5 : 1
      setMaxIteration(finalVal)
      updateSaveAgentRequest({
        constraint: {
            ...(saveAgentRequest?.constraint || {}),
            max_iteration: finalVal,
            reserved_max_chat_rounds: maxMessageRounds,
          },
      })
    }
  }

  // 处理最大对话轮数变化
  const handleMaxMessageRoundsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(event.target.value, 10)
    if (!isNaN(val)) {
      let finalVal = val
      if (val > 50) finalVal = 50
      
      if (finalVal >= 1) {
        setMaxMessageRounds(finalVal)
        updateSaveAgentRequest({
          constraint: {
            ...(saveAgentRequest?.constraint || {}),
            reserved_max_chat_rounds: finalVal,
            max_iteration: maxIteration,
          },
        })
      } else {
        setMaxMessageRounds(finalVal)
      }
    } else if (event.target.value === '') {
      setMaxMessageRounds(-1)
    }
  }

  // 处理最大对话轮数失去焦点
  const handleMaxMessageRoundsBlur = () => {
    if (maxMessageRounds === -1 || maxMessageRounds < 1) {
      const finalVal = maxMessageRounds === -1 ? 10 : 1
      setMaxMessageRounds(finalVal)
      updateSaveAgentRequest({
        constraint: {
          ...(saveAgentRequest?.constraint || {}),
          reserved_max_chat_rounds: finalVal,
          max_iteration: maxIteration,
        },
      })
    }
  }

  const handleWorkflowConfirm = (_workflowsIds: string[], workflowObjects: WorkflowSelectDetail[]) => {
    const workflowDetails = workflowObjects.map(workflow => ({
      workflow_id: workflow.workflow_id,
      workflow_name: workflow.name || '',
      workflow_version: workflow.version || '',
      description: workflow.desc || '',
    }))
    setWorkflowObjects(workflowDetails)
    updateWorkflowDetail(workflowDetails)
    setShowWorkflowSelector(false)
    validateWorkflows(workflowDetails).catch(() => {})
  }

  // 处理插件选择
  interface PluginObject {
    plugin_id: string
    name?: string
    selectedVersion?: string
    selectedTools?: PluginApiInfo[]
  }
  const handlePluginConfirm = (pluginObject: PluginObject[]) => {
    const mapped: AgentPlugin[] = []
    for (const p of pluginObject || []) {
      if (!p?.plugin_id || !Array.isArray(p.selectedTools) || p.selectedTools.length === 0) {
        continue
      }

      // 为每个选中的工具创建一个插件条目
      for (const tool of p.selectedTools) {
        mapped.push({
          plugin_id: p.plugin_id,
          plugin_name: p.name || undefined,
          tool_id: tool.tool_id,
          tool_name: tool.name || undefined,
          plugin_version: p.selectedVersion || 'draft',
        })
      }
    }
    if (mapped.length === 0) {
      return
    }
    const deduped = [...pluginObjects]
    for (const m of mapped) {
      if (!deduped.some(x => x.plugin_id === m.plugin_id && x.tool_id === m.tool_id)) {
        deduped.push(m)
      }
    }
    setPluginObjects(deduped)
    updatePluginDetail(deduped)
    setShowPluginSelector(false)
  }

  // 处理工作流操作（删除/设置）
  const handleWorkflowOperation = (operate: 'delete' | 'setting', workflowId: string, version?: string) => {
    if (operate === 'delete') {
      setWorkflowObjects(prevWorkflows => {
        const updatedWorkflows = prevWorkflows.filter(workflow => workflow.workflow_id !== workflowId)
        updateWorkflowDetail(updatedWorkflows)
        return updatedWorkflows
      })
      setValidationResults(prev => {
        const next = { ...prev }
        delete next[workflowId]
        return next
      })
    } else if (operate === 'setting') {
      // 处理设置操作，打开新页面设置工作流
      const versionParam = version && version !== 'draft' ? `&version=${version}` : ''
      window.open(`/dashboard/workflows/editor/${workflowId}?spaceId=${spaceId}${versionParam}`, '_blank')
    }
  }

  const handleRefreshWorkflows = useCallback(() => {
    setWorkflowListRefreshToken(t => t + 1)
    validateWorkflows(workflowObjects).catch(() => {})
  }, [validateWorkflows, workflowObjects])

  // 处理插件操作（删除）
  const handlePluginOperation = (operate: 'delete', _pluginId: string, toolId: string) => {
    if (operate === 'delete') {
      setPluginObjects(prevPlugins => {
        const updatedPlugins = prevPlugins.filter(plugin => plugin.tool_id !== toolId)
        // 更新插件数据到store
        updatePluginDetail(updatedPlugins)
        return updatedPlugins
      })
    }
  }

  // 处理知识库选择确认
  const handleKnowledgeBaseConfirm = async (selectedIds: string[]) => {
    // selectedIds 已经包含了所有选中的知识库ID（包括之前已选中的）
    const existingIds = knowledgeBaseObjects.map(kb => kb.id)
    const newIds = selectedIds.filter(id => !existingIds.includes(id))
    const removedIds = existingIds.filter(id => !selectedIds.includes(id))

    // 更新知识库对象列表
    if (newIds.length > 0 || removedIds.length > 0) {
      // 如果有新增的知识库，从列表API获取信息
      if (newIds.length > 0) {
        try {
          const spaceId = getDefaultSpaceId()
          if (spaceId) {
            // 调用列表API获取知识库信息
            const response = await KnowledgeBaseService.getKnowledgeBases({
              space_id: spaceId,
              page: 1,
              size: 100,
            })

            if (response.code === 200 && response.data?.items) {
              // 创建ID到知识库信息的映射
              const kbMap = new Map<string, { name: string; desc: string | null; has_graph_enhancement?: boolean }>()
              response.data.items.forEach((item: { id: string; name: string; desc: string | null; has_graph_enhancement?: boolean }) => {
                kbMap.set(item.id, { name: item.name, desc: item.desc, has_graph_enhancement: item.has_graph_enhancement })
              })

              // 获取新增知识库的信息
              const newKnowledgeBases = newIds.map(id => {
                const kbInfo = kbMap.get(id)
                if (kbInfo) {
                  return {
                    id,
                    name: kbInfo.name,
                    description: kbInfo.desc || undefined,
                    has_graph_enhancement: kbInfo.has_graph_enhancement,
                  }
                }
                // 如果找不到，使用ID作为名称
                return { id, name: id, description: undefined, has_graph_enhancement: false }
              })

              // 合并新的和保留的（排除被移除的）
              const updated = [...knowledgeBaseObjects.filter(kb => !removedIds.includes(kb.id)), ...newKnowledgeBases]
              setKnowledgeBaseObjects(updated)
            } else {
              // API调用失败，只使用ID
              const newKnowledgeBases = newIds.map(id => ({ id, name: id, description: undefined, has_graph_enhancement: false }))
              const updated = [...knowledgeBaseObjects.filter(kb => !removedIds.includes(kb.id)), ...newKnowledgeBases]
              setKnowledgeBaseObjects(updated)
            }
          } else {
            // 没有spaceId，只使用ID
            const newKnowledgeBases = newIds.map(id => ({ id, name: id, description: undefined, has_graph_enhancement: false }))
            const updated = [...knowledgeBaseObjects.filter(kb => !removedIds.includes(kb.id)), ...newKnowledgeBases]
            setKnowledgeBaseObjects(updated)
          }
        } catch (error) {
          console.error('获取知识库列表失败:', error)
          // 出错时，只使用ID
          const newKnowledgeBases = newIds.map(id => ({ id, name: id, description: undefined, has_graph_enhancement: false }))
          const updated = [...knowledgeBaseObjects.filter(kb => !removedIds.includes(kb.id)), ...newKnowledgeBases]
          setKnowledgeBaseObjects(updated)
        }
      } else {
        // 只移除，没有新增
        const updated = knowledgeBaseObjects.filter(kb => !removedIds.includes(kb.id))
        setKnowledgeBaseObjects(updated)
      }
      updateKnowledgeDetail(selectedIds)
    }
    setShowKnowledgeBaseSelector(false)
  }

  // 处理知识库操作（删除/设置）
  const handleKnowledgeBaseOperation = (operate: 'delete' | 'setting', knowledgeBaseId: string) => {
    if (operate === 'delete') {
      setKnowledgeBaseObjects(prev => {
        const updated = prev.filter(kb => kb.id !== knowledgeBaseId)
        const updatedIds = updated.map(kb => kb.id)
        updateKnowledgeDetail(updatedIds)
        return updated
      })
    } else if (operate === 'setting') {
      // 打开知识库设置页面（新窗口，页面会自己获取知识库数据）
      window.open(`/dashboard/knowledge-bases/${knowledgeBaseId}/edit`, '_blank')
    }
  }

  // 处理记忆库选择确认
const handleMemoryBaseConfirm = async (selectedId: string | null) => { // ✅ 新的单选回调
    if (selectedId === null) {
      // 用户取消了选择或清除了选择
      setMemoryBaseObject(null);
      if (saveAgentRequest?.memory) {
        // 清空 agent 的记忆库绑定
        updateMemoryConfig({
          max_tokens: 1000,
          variable_config: memoryVariables,
          longterm_memory_config: longTermMemoryEnabled,
          memory_base: undefined, // ✅ 清空
        });
      }
      setShowMemoryBaseSelector(false);
      return;
    }

    // 用户选择了一个新的记忆库
    let newMemoryBase: MemoryBaseItem | null = null;
    try {
      const spaceId = getDefaultSpaceId();
      if (spaceId) {
        const response = await MemoryBaseService.getMemoryBases({
          space_id: spaceId,
          page: 1,
          page_size: 100,
        });
        if (response.code === 200 && response.data?.items) {
          const mbMap = new Map<string, MemoryBaseItem>();
          response.data.items.forEach((item: MemoryBaseItem) => {
            mbMap.set(item.mdb_id, item);
          });
          newMemoryBase = mbMap.get(selectedId) ?? { mdb_id: selectedId, name: selectedId, description: undefined, status: "active" };
        } else {
          newMemoryBase = { mdb_id: selectedId, name: selectedId, description: undefined, status: "active" };
        }
      } else {
        newMemoryBase = { mdb_id: selectedId, name: selectedId, description: undefined, status: "active" };
      }
    } catch (error) {
      console.error('获取记忆库列表失败:', error);
      newMemoryBase = { mdb_id: selectedId, name: selectedId, description: undefined, status: "active" };
    }

    // 更新状态和 store
    setMemoryBaseObject(newMemoryBase);
    if (saveAgentRequest?.memory) {
      updateMemoryConfig({
        max_tokens: 1000,
        variable_config: memoryVariables,
        longterm_memory_config: longTermMemoryEnabled,
        memory_base: newMemoryBase, // ✅ 绑定单个对象
      });
    }
    setShowMemoryBaseSelector(false);
  };


  // 处理记忆库操作（删除/设置）
  const handleMemoryBaseOperation = (operate: 'delete' | 'setting', memoryBaseId: string) => {
    if (operate === 'delete') {
      setMemoryBaseObject(null); // ✅ 删除即清空
      if (saveAgentRequest?.memory) {
        updateMemoryConfig({
          max_tokens: 1000,
          variable_config: memoryVariables,
          longterm_memory_config: longTermMemoryEnabled,
          memory_base: undefined, // ✅ 清空
        });
      }
    } else if (operate === 'setting') {
      window.open(`/dashboard/memory-bases/${memoryBaseId}/edit`, '_blank');
    }
  };

  // 保存知识库设置到 store
  const saveRetrievalConfig = useCallback(() => {
    if (!agentDetailResponse || readonly || !isRetrievalConfigInitializedRef.current) return

    // 映射值到数字
    const sourceMap: Record<'hybrid' | 'text' | 'triple', number> = { hybrid: 1, text: 2, triple: 3 }

    // 根据文档图检索策略设置 use_agent 和 use_sync
    // 如果文档图检索开关关闭，则 use_agent 和 use_sync 都为 false
    // "基础" (base) -> use_agent=False, use_sync=True
    // "Agentic" (agentic) -> use_agent=True, use_sync=True
    // 未启用/禁用 -> use_agent=False, use_sync=False
    const useAgent = enableGraphRetrieval && graphRetrievalStrategy === 'agentic' && hasGraphEnhancementDocs
    const useSync = enableGraphRetrieval && graphRetrievalStrategy === 'base' && hasGraphEnhancementDocs

    updateRetrievalConfig({
      retrieval_type: 2, // 固定为 2 (vector/semantic)，因为 Chroma 只支持向量检索
      use_agent: useAgent,
      use_sync: useSync,
      source: sourceMap[retrievalSource],
      topk: maxRecallCount,
      score_threshold: minMatchScore === -1 ? 0.5 : minMatchScore, // 始终设置最小匹配分数，如果为空则使用默认值
    })
  }, [graphRetrievalStrategy, enableGraphRetrieval, hasGraphEnhancementDocs, retrievalSource, maxRecallCount, minMatchScore, agentDetailResponse, readonly, updateRetrievalConfig])

  // 当知识库设置改变时，自动保存
  useEffect(() => {
    if (agentDetailResponse && isRetrievalConfigInitializedRef.current && !readonly) {
      saveRetrievalConfig()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphEnhancement, retrievalSource, maxRecallCount, minMatchScore, graphRetrievalStrategy, enableGraphRetrieval, hasGraphEnhancementDocs])

  // 检查变量名是否重复
  useEffect(() => {
    if (newVariableName.trim()) {
      const duplicateVariable = memoryVariables.find(v => v.name === newVariableName.trim())
      if (duplicateVariable) {
        setDuplicateVariableWarning(t('orchestrationPage.memory.duplicateVariableWarning', { name: newVariableName.trim() }))
      } else {
        setDuplicateVariableWarning('')
      }
    } else {
      setDuplicateVariableWarning('')
    }
  }, [newVariableName, memoryVariables, t])

  // 记忆配置相关函数
  const handleAddMemoryVariable = async () => {
    if (newVariableName.trim() && !duplicateVariableWarning) {
      const newVariable: MemoryVariable = {
        id: `var_${Date.now()}`,
        name: newVariableName.trim(),
        description: newVariableDescription.trim(),
        enabled: true, // 默认启用
      }
      const updatedVariables = [...memoryVariables, newVariable]
      setMemoryVariables(updatedVariables)
      const req = {
        max_tokens: 1000,
        variable_config: updatedVariables,
        longterm_memory_config: longTermMemoryEnabled,
        memory_base: saveAgentRequest?.memory?.memory_base, // 保持记忆库绑定
      }

      try {
        await updateMemoryConfig(req)
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } }; message?: string }
        console.error(error.response?.data?.detail || error.message)
      }
      setNewVariableName('')
      setNewVariableDescription('')
    }
  }

  const handleDeleteMemoryVariable = async (id: string) => {
    const target = memoryVariables.find(v => v.id === id)
    if (!target) return
    const updatedVariables = memoryVariables.filter(variable => variable.id !== id)
    setMemoryVariables(updatedVariables)
    const req = {
      max_tokens: 1000,
      variable_config: updatedVariables,
      longterm_memory_config: longTermMemoryEnabled,
      memory_base: saveAgentRequest?.memory?.memory_base, // 保持记忆库绑定
    }
    try {
      await updateMemoryConfig(req)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      console.error(error.response?.data?.detail || error.message)
      // setMemoryVariables(backup) // 失败回滚
    }
    try {
      await api.deleteUserVariable(user_id, group_id, target.name)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err.message || t('orchestrationPage.errors.deleteFailed')
      console.error(msg)
    }
  }

  const handleToggleVariableEnabled = async (id: string) => {
    // 先更新本地状态
    const updatedVariables = memoryVariables.map(v => (v.id === id ? { ...v, enabled: !v.enabled } : v))
    setMemoryVariables(updatedVariables)

    // 同步更新到store
    const req = {
      max_tokens: 1000,
      variable_config: updatedVariables,
      longterm_memory_config: longTermMemoryEnabled,
      memory_base: saveAgentRequest?.memory?.memory_base, // 保持记忆库绑定
    }

    try {
      await updateMemoryConfig(req)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      console.error(error.response?.data?.detail || error.message)
      // 失败时回滚状态
      setMemoryVariables(memoryVariables)
    }
  }

  const handleLongTermMemoryToggle = async () => {
    const next = !longTermMemoryEnabled
    setLongTermMemoryEnabled(next)
    onLongTermChange?.(next)

    const req = {
      max_tokens: 1000,
      variable_config: memoryVariables,
      longterm_memory_config: !longTermMemoryEnabled,
      memory_base: saveAgentRequest?.memory?.memory_base, // 保持记忆库绑定
    }

    try {
      await updateMemoryConfig(req)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      console.error(error.response?.data?.detail || error.message)
    }
  }

  // 检查是否有绑定记忆库
  const hasMemoryBases = memoryBaseObject !== null;

  return (
    <div className="h-full overflow-auto">
      <div className="model-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('orchestrationPage.sections.modelTitle')}</Typography>
        <Accordion expanded={modelExpanded} onChange={handleAccordionChange}>
          <AccordionSummary aria-controls="model-content" id="model-header">
            <Typography component="span">{t('orchestrationPage.model.title')}</Typography>
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
                    if (value && !modelsList.find(model => model.model_name === value && model.is_active)) {
                      return <span style={{ color: '#d32f2f' }}>{t('orchestrationPage.select.disabledModel', { name: value })}</span>
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
                      <span style={{ color: 'rgba(0, 0, 0, 0.38)' }}>{t('orchestrationPage.select.placeholder')}</span>
                    )
                  }}
                  sx={{
                    width: 200,
                    height: 30,
                    '&.Mui-disabled': {
                      cursor: 'not-allowed',
                    },
                    '& .MuiOutlinedInput-root.Mui-disabled': {
                      cursor: 'not-allowed',
                    },
                    '& .MuiSelect-select.Mui-disabled': {
                      cursor: 'not-allowed',
                    },
                  }}
                  disabled={readonly}
                >
                  {modelsList
                    .filter(model => model.is_active)
                    .map(model => (
                      <MenuItem
                        key={model.model_name}
                        value={model.model_name}
                      >
                        <span style={{ display: 'block', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {model.model_name}
                        </span>
                      </MenuItem>
                    ))}
                </Select>
              </div>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                {t('orchestrationPage.alerts.noModelsInline')}
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
                        {t('orchestrationPage.alerts.modelDisabledAction')}
                      </Button>
                    }
                  >
                    {t('orchestrationPage.alerts.modelDisabledMessage', { name: selectedModelName })}
                  </Alert>
                ) : !selectedModel ? (
                  <Alert
                    severity="info"
                    action={
                      <Button color="primary" size="small" onClick={() => setModelExpanded(true)} sx={{ mt: -1 }}>
                        {t('orchestrationPage.alerts.noModelSelectedAction')}
                      </Button>
                    }
                  >
                    {t('orchestrationPage.alerts.noModelSelectedMessage')}
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
                    {t('orchestrationPage.alerts.noModelsConfiguredAction')}
                  </Button>
                }
              >
                {t('orchestrationPage.alerts.noModelsConfiguredMessage')}
              </Alert>
            )}
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary aria-controls="constraint-content" id="constraint-header">
            <Typography component="span">{t('orchestrationPage.sections.constraintTitle')}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label={t('orchestrationPage.constraint.maxIteration')}
                type="number"
                value={maxIteration === -1 ? '' : maxIteration}
                onChange={handleMaxIterationChange}
                onBlur={handleMaxIterationBlur}
                disabled={readonly}
                size="small"
                fullWidth
                InputProps={{ inputProps: { min: 1, max: 50 } }}
              />
              <TextField
                label={t('orchestrationPage.constraint.maxChatRounds')}
                type="number"
                value={maxMessageRounds === -1 ? '' : maxMessageRounds}
                onChange={handleMaxMessageRoundsChange}
                onBlur={handleMaxMessageRoundsBlur}
                disabled={readonly}
                size="small"
                fullWidth
                InputProps={{ inputProps: { min: 1, max: 50 } }}
              />
            </Box>
          </AccordionDetails>
        </Accordion>
      </div>

      {/* 记忆配置部分 - 独立于技能部分 */}
      <div className="memory-form mb-2 p-2">
        <div className="flex items-center justify-between mb-2">
          <Typography>{t('orchestrationPage.sections.memoryTitle')}</Typography>
        </div>

        {/* 绑定记忆库部分 */}
        <Accordion>
          <AccordionSummary aria-controls="memory-bases-content" id="memory-bases-header">
            <Typography component="span" className="flex items-center">
              记忆库
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${
                  memoryBaseObject ? 'bg-blue-500' : 'bg-gray-400'
                }`}
              >
                {memoryBaseObject ? 1 : 0}
              </span>
            </Typography>
            <AddButton
              options={[
                { label: '添加已有记忆库', value: 'existing' },
                { label: '创建新记忆库', value: 'new' },
              ]}
              onSelect={addType => {
                if (addType === 'existing') {
                  // 打开记忆库选择器
                  setShowMemoryBaseSelector(true)
                } else if (addType === 'new') {
                  // 导航到记忆库管理页面
                  window.open('/dashboard/memory-bases', '_blank')
                }
              }}
              disabled={readonly}
            />
          </AccordionSummary>
          <AccordionDetails>
            {/* 记忆库列表组件 */}
            <div className="space-y-3">
              {memoryBaseObject && ( (
                <div
                  key={memoryBaseObject.mdb_id}
                  className="flex items-start justify-between py-2 px-3 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-start space-x-3 flex-1 min-w-0">
                    <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-purple-100 to-indigo-100 rounded-lg flex items-center justify-center border border-purple-200 mt-1">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-purple-600">
                        <path d="M11.25 4.533A9.707 9.707 0 0 0 6 3a9.735 9.735 0 0 0-3.25.555.75.75 0 0 0-.5.707v14.25a.75.75 0 0 0 1 .707A8.237 8.237 0 0 1 6 18.75c1.995 0 3.823.707 5.25 1.886V4.533ZM12.75 20.636A8.214 8.214 0 0 1 18 18.75c.966 0 1.89.166 2.75.47a.75.75 0 0 0 1-.708V4.262a.75.75 0 0 0-.5-.707A9.735 9.735 0 0 0 18 3a9.707 9.707 0 0 0-5.25 1.533v16.103Z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <Typography sx={{ fontWeight: 'bold', fontSize: '1rem' }}>{memoryBaseObject.name}</Typography>
                      {memoryBaseObject.description && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            fontSize: '0.875rem',
                            lineHeight: 1.4,
                            mt: 0.5,
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {memoryBaseObject.description}
                        </Typography>
                      )}
                    </div>
                  </div>
                  <div className="flex space-x-4 pt-1">
                    <button
                      title="设置"
                      onClick={e => {
                        e.stopPropagation();
                        handleMemoryBaseOperation('setting', memoryBaseObject.mdb_id);
                      }}
                    >
                      <Settings className="w-4 h-4 text-gray-600" />
                    </button>
                    <button
                      title="删除"
                      onClick={e => {
                        e.stopPropagation();
                        if (!readonly) {
                          handleMemoryBaseOperation('delete', memoryBaseObject.mdb_id);
                        }
                      }}
                      disabled={readonly}
                      className={`${readonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <Trash2 className="w-4 h-4 text-gray-600" />
                    </button>
                  </div>
                </div>
              ))}
              {!memoryBaseObject && <div className="text-center py-6 text-gray-500">未添加记忆库，记忆配置不生效，可点击右上角进行添加</div>}
            </div>
          </AccordionDetails>
        </Accordion>

        {/* 记忆变量部分 - 仅当绑定了记忆库时启用 */}
        <Accordion>
          <AccordionSummary aria-controls="memory-variables-content" id="memory-variables-header">
            <Typography component="span" className="flex items-center">
              {t('orchestrationPage.memory.variablesTitle')}
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${
                  memoryVariables.length > 0 ? 'bg-blue-500' : 'bg-gray-400'
                }`}
              >
                {memoryVariables.length}
              </span>
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {/* 添加新变量表单 */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 1 }}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label={t('orchestrationPage.memory.fields.nameLabel')}
                  value={newVariableName}
                  onChange={e => setNewVariableName(e.target.value)}
                  disabled={readonly || !hasMemoryBases}
                  size="small"
                  sx={{ flex: 1 }}
                  error={!!duplicateVariableWarning}
                />
                <TextField
                  label={t('orchestrationPage.memory.fields.descLabel')}
                  value={newVariableDescription}
                  onChange={e => setNewVariableDescription(e.target.value)}
                  disabled={readonly || !hasMemoryBases}
                  size="small"
                  sx={{ flex: 2 }}
                />
                <Button
                  variant="outlined"
                  onClick={handleAddMemoryVariable}
                  disabled={readonly || !newVariableName.trim() || !newVariableDescription.trim() || !!duplicateVariableWarning || !hasMemoryBases}
                  size="small"
                  sx={{ alignSelf: 'flex-end', height: '40px' }}
                >
                  {t('orchestrationPage.memory.actions.addVariable')}
                </Button>
              </Box>

              {/* 预留警告空间，防止按钮移动 */}
              <Box sx={{ minHeight: '20px', pl: '12px' }}>
                {duplicateVariableWarning && (
                  <Typography variant="caption" color="error">
                    {duplicateVariableWarning}
                  </Typography>
                )}
                {!hasMemoryBases && (
                  <Typography variant="caption" color="warning.main">
                    请先绑定记忆库以启用记忆变量功能
                  </Typography>
                )}
              </Box>
            </Box>

            {/* 变量列表 */}
            {memoryVariables.length > 0 ? (
              <List sx={{ width: '100%', bgcolor: 'background.paper', maxHeight: 300, overflow: 'auto', mt: 0.5 }}>
                {memoryVariables.map(variable => (
                  <ListItem
                    key={variable.id}
                    secondaryAction={
                      <>
                        {!readonly && hasMemoryBases && (
                          <FormControlLabel
                            control={<Switch size="small" checked={variable.enabled !== false} onChange={() => handleToggleVariableEnabled(variable.id)} />}
                            label={
                              variable.enabled !== false ? t('orchestrationPage.memory.list.enabledLabel') : t('orchestrationPage.memory.list.disabledLabel')
                            }
                            labelPlacement="start"
                            sx={{ mr: 1 }}
                          />
                        )}
                        {!readonly && hasMemoryBases && (
                          <IconButton edge="end" aria-label="delete" onClick={() => handleDeleteMemoryVariable(variable.id)}>
                            <Trash2 className="w-4 h-4 text-gray-600" />
                          </IconButton>
                        )}
                        {!hasMemoryBases && (
                          <Typography variant="caption" color="text.disabled">
                            需绑定记忆库
                          </Typography>
                        )}
                      </>
                    }
                  >
                    <ListItemText 
                      primary={variable.name} 
                      secondary={
                        <>{variable.description || t('orchestrationPage.memory.list.noDescription')}</>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {t('orchestrationPage.memory.list.empty') }
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>

        {/* 长期记忆部分 - 仅当绑定了记忆库时启用 */}
        <Accordion>
          <AccordionSummary aria-controls="long-term-memory-content" id="long-term-memory-header">
            <Typography component="span">{t('orchestrationPage.memory.longTermTitle')}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ mb: 2, mt: 1 }}>
              <FormControlLabel
                control={
                  <Switch 
                    checked={longTermMemoryEnabled} 
                    onChange={handleLongTermMemoryToggle} 
                    disabled={readonly || !hasMemoryBases} 
                  />
                }
                label={t('orchestrationPage.memory.longTermToggleLabel')}
              />
              <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                {t('orchestrationPage.memory.longTermDescription')}
              </Typography>
              {!hasMemoryBases && (
                <Typography variant="caption" color="warning.main" sx={{ mt: 1, display: 'block' }}>
                  请先绑定记忆库以启用长期记忆功能
                </Typography>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      </div>

      <div className="skills-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('orchestrationPage.sections.skillsTitle')}</Typography>

        <Accordion>
          <AccordionSummary aria-controls="workflow-content" id="workflow-header">
            <Typography component="span" className="flex items-center">
              {t('orchestrationPage.sections.workflowTitle')}
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${
                  workflowObjects.length > 0 ? 'bg-blue-500' : 'bg-gray-400'
                }`}
              >
                {workflowObjects.length}
              </span>
              {workflowValidationErrorCount > 0 && ( 
                 <Tooltip title={t('orchestrationPage.workflow.validationWarning', { count: workflowValidationErrorCount })} arrow> 
                   <span className="inline-flex items-center ml-2"> 
                     <AlertCircle className="w-[20px] h-[20px] text-red-500" /> 
                   </span> 
                 </Tooltip> 
               )}
            </Typography>
            <div className="action-area" onClick={e => e.stopPropagation()} style={{ marginLeft: '16px', display: 'flex', gap: '8px' }}>
              <Tooltip title={t('orchestrationPage.workflow.refreshTooltip')} arrow>
                <span>
                  <IconButton 
                    component="div"
                    size="small" 
                    onClick={handleRefreshWorkflows} 
                    disabled={workflowObjects.length === 0} 
                    aria-label={t('orchestrationPage.workflow.refreshAriaLabel')}
                    sx={{ cursor: workflowObjects.length === 0 ? 'not-allowed' : 'pointer' }}
                  >
                    <RefreshCcw className={`w-4 h-4 ${isValidating ? 'animate-spin' : ''}`} />
                  </IconButton>
                </span>
              </Tooltip>
              <AddButton
                options={[
                  { label: t('addWorkflow.addExisting'), value: 'existing' },
                  { label: t('addWorkflow.createNew'), value: 'new' },
                ]}
                onSelect={addType => {
                  if (addType === 'existing') {
                    setShowWorkflowSelector(true)
                  } else if (addType === 'new') {
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
             />
            {workflowObjects.length === 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                {t('orchestrationPage.alerts.noWorkflow')}
              </Alert>
            )}
          </AccordionDetails>
        </Accordion>

        <Accordion>
          <AccordionSummary aria-controls="plugin-content" id="plugin-header">
            <Typography component="span" className="flex items-center">
              {t('orchestrationPage.sections.pluginTitle')}
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${
                  pluginObjects.length > 0 ? 'bg-blue-500' : 'bg-gray-400'
                }`}
              >
                {pluginObjects.length}
              </span>
            </Typography>
            <AddButton
              options={[
                { label: t('addPlugin.addExisting'), value: 'existing' },
                { label: t('addPlugin.createNew'), value: 'new' },
              ]}
              onSelect={addType => {
                if (addType === 'existing') {
                  // 打开插件选择器
                  setShowPluginSelector(true)
                } else if (addType === 'new') {
                  // 导航到创建新插件页面
                  window.open('/dashboard/plugins', '_blank ')
                }
              }}
              disabled={readonly}
            />
          </AccordionSummary>
          <AccordionDetails>
            {/* 插件列表 */}
            <PluginList pluginObjects={pluginObjects} onClick={handlePluginOperation} disabled={readonly} />
          </AccordionDetails>
        </Accordion>
      </div>

      <div className="knowledge-form mb-2 p-2">
        <div className="flex items-center justify-between mb-2">
          <Typography>{t('orchestrationPage.knowledge.sectionTitle')}</Typography>
          <IconButton
            size="small"
            onClick={e => setKnowledgeSettingsAnchorEl(e.currentTarget)}
            disabled={readonly}
            sx={{
              color: 'text.secondary',
              '&:hover': { color: 'primary.main', backgroundColor: 'action.hover' },
            }}
          >
            <Settings className="w-4 h-4" />
          </IconButton>
        </div>

        <Accordion>
          <AccordionSummary aria-controls="knowledge-content" id="knowledge-header">
            <Typography component="span" className="flex items-center">
              {t('orchestrationPage.knowledge.accordionTitle')}
              <span
                className={`inline-flex items-center justify-center ml-2 w-[18px] h-[18px] text-xs font-medium text-white rounded-full ${
                  knowledgeBaseObjects.length > 0 ? 'bg-blue-500' : 'bg-gray-400'
                }`}
              >
                {knowledgeBaseObjects.length}
              </span>
            </Typography>
            <AddButton
              options={[
                { label: t('addKnowledgeBase.addExisting'), value: 'existing' },
                { label: t('addKnowledgeBase.createNew'), value: 'new' },
              ]}
              onSelect={addType => {
                if (addType === 'existing') {
                  // 打开知识库选择器
                  setShowKnowledgeBaseSelector(true)
                } else if (addType === 'new') {
                  // 导航到知识库管理页面
                  window.open('/dashboard/knowledge-bases', '_blank')
                }
              }}
              disabled={readonly}
            />
          </AccordionSummary>
          <AccordionDetails>
            {/* 知识库列表 */}
            <KnowledgeBaseList knowledgeBaseObjects={knowledgeBaseObjects} onClick={handleKnowledgeBaseOperation} disabled={readonly} />
          </AccordionDetails>
        </Accordion>
      </div>

      <div className="panel3d-form mb-2 p-2">
        <Typography sx={{ mb: 2 }}>{t('orchestrationPage.sections.conversationTitle')}</Typography>
        <Accordion defaultExpanded={true}>
          <AccordionSummary aria-controls="greeting-content" id="greeting-header">
            <Typography component="span">{t('orchestrationPage.sections.greetingTitle')}</Typography>
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
              disabled={readonly}
              sx={{
                '& .MuiInputBase-root.Mui-disabled': {
                  cursor: 'not-allowed',
                },
                '& .MuiInputBase-input.Mui-disabled': {
                  cursor: 'not-allowed',
                },
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
      {showPluginSelector && !readonly && (
        <PluginSelector open={showPluginSelector} onClose={() => setShowPluginSelector(false)} onConfirm={handlePluginConfirm} initialSelected={[]} />
      )}
      {showKnowledgeBaseSelector && !readonly && (
        <KnowledgeBaseSelector
          open={showKnowledgeBaseSelector}
          onClose={() => setShowKnowledgeBaseSelector(false)}
          onConfirm={handleKnowledgeBaseConfirm}
          initialSelected={knowledgeBaseObjects.map(kb => kb.id)}
        />
      )}
      {showMemoryBaseSelector && !readonly && (
        <MemoryBaseSelector
          open={showMemoryBaseSelector}
          onClose={() => setShowMemoryBaseSelector(false)}
          onConfirm={handleMemoryBaseConfirm}
          initialSelected={memoryBaseObject?.mdb_id ?? null}
        />
      )}

      {/* 知识库设置 Popover */}
      <Popover
        open={Boolean(knowledgeSettingsAnchorEl)}
        anchorEl={knowledgeSettingsAnchorEl}
        onClose={() => setKnowledgeSettingsAnchorEl(null)}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: {
            p: 3,
            minWidth: 480,
            maxWidth: 550,
          },
        }}
      >
        <Typography variant="h6" sx={{ mb: 2, fontSize: '1rem', fontWeight: 'bold' }}>
          {t('orchestrationPage.knowledgeSettings.title')}
        </Typography>

        {/* 文档图检索策略 */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="body2" sx={{ fontWeight: 'medium', color: hasGraphEnhancementDocs ? 'text.primary' : 'text.disabled' }}>
                {t('orchestrationPage.knowledgeSettings.graphStrategyLabel')}
              </Typography>
              <Tooltip title={t('orchestrationPage.knowledgeSettings.graphStrategyTooltip')} arrow placement="top">
                <HelpOutlineIcon sx={{ fontSize: 16, color: hasGraphEnhancementDocs ? 'text.secondary' : 'text.disabled', cursor: 'help' }} />
              </Tooltip>
            </Box>
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={enableGraphRetrieval}
                  onChange={e => {
                    const checked = e.target.checked
                    setEnableGraphRetrieval(checked)
                    if (!checked) {
                      setGraphRetrievalStrategy('base')
                      setGraphEnhancement('off')
                    }
                    if (isRetrievalConfigInitializedRef.current && !readonly) {
                      saveRetrievalConfig()
                    }
                  }}
                  disabled={readonly || !hasGraphEnhancementDocs}
                />
              }
              label={enableGraphRetrieval ? t('orchestrationPage.knowledgeSettings.enabled') : t('orchestrationPage.knowledgeSettings.disabled')}
              sx={{
                margin: 0,
                '& .MuiFormControlLabel-label': {
                  fontSize: '0.875rem',
                  color: hasGraphEnhancementDocs ? 'text.primary' : 'text.disabled'
                }
              }}
            />
          </Box>
          <RadioGroup
            value={graphRetrievalStrategy}
            onChange={e => {
              const value = e.target.value as 'base' | 'agentic'
              setGraphRetrievalStrategy(value)
              setGraphEnhancement(value === 'base' ? 'normal' : 'agent')
              if (isRetrievalConfigInitializedRef.current && !readonly) {
                saveRetrievalConfig()
              }
            }}
            row
            sx={{
              opacity: enableGraphRetrieval && hasGraphEnhancementDocs ? 1 : 0.5,
              pointerEvents: enableGraphRetrieval && hasGraphEnhancementDocs ? 'auto' : 'none'
            }}
          >
            <Tooltip title={t('orchestrationPage.knowledgeSettings.baseTooltip')} arrow placement="top">
              <FormControlLabel
                value="base"
                control={<Radio size="small" />}
                label={t('orchestrationPage.knowledgeSettings.base')}
                disabled={readonly || !enableGraphRetrieval || !hasGraphEnhancementDocs}
              />
            </Tooltip>
            <Tooltip title={t('orchestrationPage.knowledgeSettings.agenticTooltip')} arrow placement="top">
              <FormControlLabel
                value="agentic"
                control={<Radio size="small" />}
                label={t('orchestrationPage.knowledgeSettings.agentic')}
                disabled={readonly || !enableGraphRetrieval || !hasGraphEnhancementDocs}
              />
            </Tooltip>
          </RadioGroup>
          {!hasGraphEnhancementDocs && (
            <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
              {t('orchestrationPage.knowledgeSettings.noGraphDocsMessage')}
            </Typography>
          )}
        </Box>

        {/* 最大召回数量 */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
              {t('orchestrationPage.knowledgeSettings.maxRecallLabel')}
            </Typography>
            <Tooltip title={t('orchestrationPage.knowledgeSettings.maxRecallTooltip')} arrow placement="top">
              <HelpOutlineIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
            </Tooltip>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Slider
                value={maxRecallCount}
                onChange={(_, value) => {
                  setMaxRecallCount(value as number)
                  if (isRetrievalConfigInitializedRef.current && !readonly) {
                    saveRetrievalConfig()
                  }
                }}
                min={1}
                max={10}
                step={1}
                marks
                valueLabelDisplay="auto"
                disabled={readonly}
              />
            </Box>
            <Box sx={{ width: 80, minWidth: 80, maxWidth: 80 }}>
              <TextField
                type="text"
                value={maxRecallCount === -1 ? '' : maxRecallCount}
                onChange={e => {
                  const inputValue = e.target.value
                  // 允许用户清空输入框
                  if (inputValue === '') {
                    setMaxRecallCount(-1 as any)
                    return
                  }
                  // 只允许数字输入（不允许负号）
                  if (/^\d*$/.test(inputValue)) {
                    const value = parseInt(inputValue, 10)
                    if (!isNaN(value)) {
                      // 允许输入任何数字，不进行范围限制
                      setMaxRecallCount(value)
                      if (isRetrievalConfigInitializedRef.current && !readonly) {
                        saveRetrievalConfig()
                      }
                    }
                  }
                }}
                onBlur={e => {
                  const inputValue = e.target.value
                  if (inputValue === '') {
                    // 如果为空，设置为默认值
                    setMaxRecallCount(5)
                    if (isRetrievalConfigInitializedRef.current && !readonly) {
                      saveRetrievalConfig()
                    }
                    return
                  }
                  const value = parseInt(inputValue, 10)
                  if (isNaN(value) || value < 1) {
                    setMaxRecallCount(1)
                    if (isRetrievalConfigInitializedRef.current && !readonly) {
                      saveRetrievalConfig()
                    }
                  } else if (value > 10) {
                    setMaxRecallCount(10)
                    if (isRetrievalConfigInitializedRef.current && !readonly) {
                      saveRetrievalConfig()
                    }
                  }
                }}
                size="small"
                disabled={readonly}
                inputProps={{ min: 1, max: 10 }}
              />
            </Box>
          </Box>
        </Box>

        {/* 最小匹配分数 */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
              {t('orchestrationPage.knowledgeSettings.minScoreLabel')}
            </Typography>
            <Tooltip title={t('orchestrationPage.knowledgeSettings.minScoreTooltip')} arrow placement="top">
              <HelpOutlineIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
            </Tooltip>
          </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Slider
                  value={minMatchScore === -1 ? 0.5 : minMatchScore}
                  onChange={(_, value) => {
                    setMinMatchScore(value as number)
                    minMatchScoreInputRef.current = '' // 清空 ref，因为 Slider 设置的是完整数字
                    if (isRetrievalConfigInitializedRef.current && !readonly) {
                      saveRetrievalConfig()
                    }
                  }}
                  min={0}
                  max={1}
                  step={0.1}
                  marks={[
                    { value: 0, label: '0' },
                    { value: 0.5, label: '0.5' },
                    { value: 1, label: '1' },
                  ]}
                  valueLabelDisplay="auto"
                  disabled={readonly}
                />
              </Box>
              <Box sx={{ width: 80, minWidth: 80, maxWidth: 80 }}>
                <TextField
                  type="text"
                  value={minMatchScoreInputRef.current || (minMatchScore === -1 ? '' : String(minMatchScore))}
                  onChange={e => {
                    const inputValue = e.target.value
                    // 允许用户清空输入框
                    if (inputValue === '') {
                      setMinMatchScore(-1 as any)
                      minMatchScoreInputRef.current = ''
                      return
                    }
                    // 允许数字、小数点和最多一位小数（不允许负号）
                    // 允许：纯数字（如 "0", "1"）、数字加小数点（如 "0.", "1."）、数字加小数点和数字（如 "0.5"）、小数点开头加数字（如 ".5"）
                    if (/^(\d+\.?|\d*\.\d{0,1})$/.test(inputValue)) {
                      // 保存原始输入到 ref（用于显示中间状态）
                      minMatchScoreInputRef.current = inputValue
                      // 尝试转换为数字
                      const value = parseFloat(inputValue)
                      if (!isNaN(value) && !inputValue.endsWith('.') && !inputValue.startsWith('.')) {
                        // 如果是完整数字（不是中间状态），更新状态并清空 ref
                        setMinMatchScore(value)
                        minMatchScoreInputRef.current = '' // 清空 ref，因为已经是完整数字
                        if (isRetrievalConfigInitializedRef.current && !readonly) {
                          saveRetrievalConfig()
                        }
                      } else {
                        // 如果是中间状态（如 "0." 或 ".5"），设置为 -1 标记，保留 ref 中的原始输入
                        setMinMatchScore(-1 as any)
                      }
                    }
                  }}
                  onBlur={e => {
                    const inputValue = e.target.value
                    if (inputValue === '') {
                      // 如果为空，设置为默认值
                      setMinMatchScore(0.5)
                      minMatchScoreInputRef.current = ''
                      if (isRetrievalConfigInitializedRef.current && !readonly) {
                        saveRetrievalConfig()
                      }
                      return
                    }
                    const value = parseFloat(inputValue)
                    if (isNaN(value) || value < 0) {
                      setMinMatchScore(0)
                      minMatchScoreInputRef.current = ''
                      if (isRetrievalConfigInitializedRef.current && !readonly) {
                        saveRetrievalConfig()
                      }
                    } else if (value > 1) {
                      setMinMatchScore(1)
                      minMatchScoreInputRef.current = ''
                      if (isRetrievalConfigInitializedRef.current && !readonly) {
                        saveRetrievalConfig()
                      }
                    } else {
                      // 格式化值为一位小数
                      const formattedValue = Math.round(value * 10) / 10
                      setMinMatchScore(formattedValue)
                      minMatchScoreInputRef.current = ''
                      if (isRetrievalConfigInitializedRef.current && !readonly) {
                        saveRetrievalConfig()
                      }
                    }
                  }}
                  size="small"
                  disabled={readonly}
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                />
              </Box>
            </Box>
            {minMatchScore !== -1 && minMatchScore === 1 && (
              <Typography variant="caption" sx={{ color: 'error.main', mt: 0.5, display: 'block' }}>
                {t('orchestrationPage.knowledgeSettings.minScoreWarning')}
              </Typography>
            )}
        </Box>
      </Popover>
    </div>
  )
}

export default AgentModelSelector
