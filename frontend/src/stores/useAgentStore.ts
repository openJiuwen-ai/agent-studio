import { ModelDetail, WorkflowDetail } from '@/types/agentTypes'
import { Memory } from '@mui/icons-material'
import { SaveAgentRequest, AgentService, AgentPlugin } from '@test-agentstudio/api-client'
import { create } from 'zustand'

interface MemoryVariable {
  id: string
  name: string
  description?: string
  defaultValue?: string
  enabled?: boolean
}
interface MemoryBase {
	mdb_id: string
  name: string
  desc?: string
  embedding_model_config_id?: number
  llm_model_config_id?: number
}
interface Memory {
  max_tokens: number
  longterm_memory_config: boolean
  memory_base?: MemoryBase
  variable_config: MemoryVariable[]
}

interface AgentState {
  saveAgentRequest: SaveAgentRequest
  isSaving: boolean
  saveError: string | null
  saveDebounceTimer: ReturnType<typeof setTimeout> | null
  lastAutoSaveTime: string | null
  readonly: boolean
  modelActive: boolean // 添加模型活动状态
}

interface AgentActions {
  setSaveAgentRequest: (request: SaveAgentRequest) => void
  updateModelDetail: (modelDetail: ModelDetail) => void
  updateWorkflowDetail: (workflowDetail: WorkflowDetail[]) => void
  updatePluginDetail: (pluginDetail: AgentPlugin[]) => void
  updateKnowledgeDetail: (knowledgeIds: string[]) => void
  updateRetrievalConfig: (retrievalConfig: { retrieval_type: number; use_agent?: boolean; use_sync?: boolean; source?: number; topk: number; score_threshold: number | null }) => void
  updateGreeting: (greeting: string) => void
  updateSaveAgentRequest: (updates: Partial<SaveAgentRequest>) => void
  updateMemoryConfig: (memoryConfig: Memory) => void
  saveAgent: () => Promise<boolean>
  resetStore: () => void
  setReadonly: (readonly: boolean) => void
  setModelActive: (active: boolean) => void // 添加设置模型活动状态的方法
}

export const useAgentStore = create<AgentState & AgentActions>((set, get) => ({
  saveAgentRequest: {} as SaveAgentRequest,
  isSaving: false,
  saveError: null,
  saveDebounceTimer: null,
  lastAutoSaveTime: null,
  readonly: false,
  modelActive: false, // 初始为未激活

  setSaveAgentRequest: request => {
    set({ saveAgentRequest: request })
  },

  updateModelDetail: (modelDetail: ModelDetail) => {
    if (get().readonly) {
      return
    }
    const { model_provider, ...other } = modelDetail
    const model = {
      model_provider: model_provider || '',
      model_info: other,
    }
    // 更新模型活动状态，添加 guard condition 防止不必要的状态更新
    const currentModelActive = get().modelActive
    const newModelActive = modelDetail.is_active
        if (currentModelActive !== newModelActive) {
      set({ modelActive: newModelActive })
    }
    get().updateSaveAgentRequest({ model })
  },

  updateWorkflowDetail: (workflowDetail: WorkflowDetail[]) => {
    if (get().readonly) {
      return
    }
    get().updateSaveAgentRequest({ workflows: workflowDetail })
  },

  updatePluginDetail: (pluginDetail: AgentPlugin[]) => {
    if (get().readonly) {
      return
    }
    const sanitized = pluginDetail
      .filter(p => p.plugin_id && p.tool_id)
      .map(p => ({
        ...p,
        plugin_name: p.plugin_name || undefined,
        tool_name: p.tool_name || undefined,
      }))
    get().updateSaveAgentRequest({ plugins: sanitized })
  },

  // 更新知识库
  updateKnowledgeDetail: (knowledgeIds: string[]) => {
    if (get().readonly) {
      return
    }
    get().updateSaveAgentRequest({ knowledge: knowledgeIds })
  },

  updateRetrievalConfig: (retrievalConfig: { retrieval_type: number; use_agent?: boolean; use_sync?: boolean; source?: number; topk: number; score_threshold: number | null }) => {
    if (get().readonly) {
      return
    }
    const currentConfigs = get().saveAgentRequest.configs || {}
    // 移除 source 字段，因为后端 KBRetrievalConfig 中不包含此字段
    const { source, ...configWithoutSource } = retrievalConfig
    get().updateSaveAgentRequest({
      configs: {
        ...currentConfigs,
        retrieval_config: configWithoutSource,
      },
    })
  },

  // 更新开场白
  updateGreeting: (greeting: string) => {
    if (get().readonly) {
      return
    }
    get().updateSaveAgentRequest({ opening_remarks: greeting })
  },

  // 更新记忆配置
  updateMemoryConfig: (memoryConfig: Memory) => {
    if (get().readonly) {
      return
    }
    console.log(memoryConfig)
    get().updateSaveAgentRequest({ memory: memoryConfig })
  },

  updateSaveAgentRequest: (updates: Partial<SaveAgentRequest>) => {
    if (get().readonly) {
      return
    }
    set({ saveAgentRequest: { ...get().saveAgentRequest, ...updates } })

    // 使用防抖处理，延迟500ms执行保存
    const saveAgentDebounced = () => {
      const currentTimer = get().saveDebounceTimer
      if (currentTimer !== null) {
        clearTimeout(currentTimer)
      }

      const timer = setTimeout(() => {
        get().saveAgent()
      }, 500)

      set({ saveDebounceTimer: timer })
    }

    saveAgentDebounced()
  },

  saveAgent: async () => {
    try {
      set({ isSaving: true, saveError: null })
      const request = {
        ...get().saveAgentRequest,
        auto_generated_prompt: get().saveAgentRequest.auto_generated_prompt || '',
        agent_version: '',
      }
      await AgentService.saveAgent(request)
      // 更新自动保存时间
      const now = new Date()
      const formattedTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
      set({ isSaving: false, lastAutoSaveTime: `${formattedTime}` })
      return true
    } catch (error) {
      set({
        isSaving: false,
        saveError: error instanceof Error ? error.message : '保存失败，请重试',
      })
      return false
    }
  },

  // 重置 store 数据
  resetStore: () => {
    // 清除防抖定时器
    const currentTimer = get().saveDebounceTimer
    if (currentTimer !== null) {
      clearTimeout(currentTimer)
    }

    // 重置所有状态
    set({
      saveAgentRequest: {} as SaveAgentRequest,
      isSaving: false,
      saveError: null,
      saveDebounceTimer: null,
      lastAutoSaveTime: null,
      readonly: false,
      modelActive: false,
    })
  },

  setReadonly: (readonly: boolean) => {
    set({ readonly })
  },

  // 设置模型活动状态
  setModelActive: (active: boolean) => {
    set({ modelActive: active })
  },
}))
