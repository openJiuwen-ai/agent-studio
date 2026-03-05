import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import {
  KnowledgeBase,
  CreateKnowledgeBaseRequest,
  GetKnowledgeBasesRequest,
  KnowledgeBaseItem,
  UpdateKnowledgeBaseRequest,
  SearchKnowledgeBaseRequest,
  SearchKnowledgeBaseItem,
} from '@/types/knowledgeBase'
import { KnowledgeBaseService } from '@test-agentstudio/api-client'

interface KnowledgeBaseState {
  knowledgeBases: KnowledgeBase[]
  currentKnowledgeBase: KnowledgeBase | null
  isLoading: boolean
  error: string | null
  searchQuery: string
  selectedKnowledgeBaseIds: string[]
  isSearching: boolean
  // 分页相关
  total: number
  currentPage: number
  pageSize: number
}

interface KnowledgeBaseActions {
  fetchKnowledgeBases: (spaceId?: string, page?: number, size?: number) => Promise<void>
  searchKnowledgeBases: (spaceId: string, query: string, page?: number, size?: number) => Promise<void>
  createKnowledgeBase: (data: CreateKnowledgeBaseRequest) => Promise<{ id: string }>
  updateKnowledgeBase: (data: UpdateKnowledgeBaseRequest) => Promise<void>
  deleteKnowledgeBase: (id: string, spaceId: string) => Promise<void>
  getKnowledgeBaseById: (id: string, spaceId: string) => Promise<KnowledgeBase | null>
  setCurrentKnowledgeBase: (knowledgeBase: KnowledgeBase | null) => void
  setSearchQuery: (query: string) => void
  setSelectedKnowledgeBaseIds: (ids: string[]) => void
  toggleKnowledgeBaseSelection: (id: string) => void
  selectAllKnowledgeBases: () => void
  clearSelection: () => void
  clearError: () => void
  reset: () => void
  // 分页相关actions
  setPage: (page: number) => void
  setPageSize: (size: number) => void
}

type KnowledgeBaseStore = KnowledgeBaseState & KnowledgeBaseActions

const initialState: KnowledgeBaseState = {
  knowledgeBases: [],
  currentKnowledgeBase: null,
  isLoading: false,
  error: null,
  searchQuery: '',
  selectedKnowledgeBaseIds: [],
  isSearching: false,
  total: 0,
  currentPage: 1,
  pageSize: 20,
}

export const useKnowledgeBaseStore = create<KnowledgeBaseStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      fetchKnowledgeBases: async (spaceId = '0', page = 1, size = 10) => {
        try {
          set({ isLoading: true, error: null })
          const request: GetKnowledgeBasesRequest = {
            space_id: spaceId,
            page: page,
            size: size,
          }
          const response = await KnowledgeBaseService.getKnowledgeBases(request)

          // 转换API响应的KnowledgeBaseItem格式为前端使用的KnowledgeBase格式
          const knowledgeBases: KnowledgeBase[] = response.data.items.map((item: KnowledgeBaseItem) => ({
            id: item.id,
            name: item.name || '未命名知识库',
            description: item.desc,
            type: (item.type || 'document') as 'document' | 'web' | 'api' | 'database',
            status: 'active' as const,
            space_id: spaceId,
            embedding_model_config_id: item.embedding_model_config_id,
            created_at: item.created_at,
            updated_at: item.updated_at,
            created_by: '',
            documentCount: 0,
            size: 0,
          }))

          const total = response.data.total
          const totalPages = Math.max(1, Math.ceil(total / size))
          const safePage = Math.min(Math.max(1, response.data.page), totalPages)
          set({
            knowledgeBases,
            total,
            currentPage: safePage,
            pageSize: size, // 使用请求参数，与分页器一致，避免被后端返回值覆盖
            isLoading: false,
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch knowledge bases'
          set({ error: errorMessage, isLoading: false })
        }
      },

      searchKnowledgeBases: async (spaceId: string, query: string, page = 1, size = 10) => {
        try {
          set({ isSearching: true, error: null })
          const request: SearchKnowledgeBaseRequest = {
            space_id: spaceId,
            query: query.trim(),
            page: page,
            page_size: size,
          }
          const response = await KnowledgeBaseService.searchKnowledgeBase(request)

          // 转换搜索API响应的SearchKnowledgeBaseItem格式为前端使用的KnowledgeBase格式
          const knowledgeBases: KnowledgeBase[] = response.data.knowledge_bases.map((item: SearchKnowledgeBaseItem) => ({
            id: item.id,
            name: item.name || '未命名知识库',
            description: item.description,
            type: 'document' as const, // 搜索接口返回的都是文档知识库
            status: 'active' as const,
            space_id: item.space_id,
            embedding_model_config_id: item.embedding_model_config_id,
            created_at: new Date(item.create_time * 1000).toISOString(), // 时间戳转换为ISO字符串
            updated_at: new Date(item.update_time * 1000).toISOString(),
            created_by: '',
            documentCount: 0,
            size: 0,
          }))

          const total = response.data.total
          const totalPages = Math.max(1, Math.ceil(total / size))
          const safePage = Math.min(Math.max(1, response.data.page), totalPages)
          set({
            knowledgeBases,
            total,
            currentPage: safePage,
            pageSize: size,
            isSearching: false,
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to search knowledge bases'
          set({ error: errorMessage, isSearching: false })
        }
      },

      createKnowledgeBase: async (data: CreateKnowledgeBaseRequest) => {
        try {
          set({ isLoading: true, error: null })
          const response = await KnowledgeBaseService.createKnowledgeBase(data)
          set({ isLoading: false })
          return response
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to create knowledge base'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      updateKnowledgeBase: async (data: UpdateKnowledgeBaseRequest) => {
        try {
          await KnowledgeBaseService.updateKnowledgeBase(data)

          set(state => ({
            knowledgeBases: state.knowledgeBases.map(kb => (kb.id === data.kb_id ? { ...kb, name: data.name, description: data.desc, desc: data.desc } : kb)),
            currentKnowledgeBase:
              state.currentKnowledgeBase?.id === data.kb_id
                ? { ...state.currentKnowledgeBase, name: data.name, description: data.desc, desc: data.desc }
                : state.currentKnowledgeBase,
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to update knowledge base'
          set({ error: errorMessage })
          throw error
        }
      },

      deleteKnowledgeBase: async (id: string, spaceId: string) => {
        try {
          set({ isLoading: true, error: null })
          await KnowledgeBaseService.deleteKnowledgeBase({ space_id: spaceId, kb_id: id })
          set(state => ({
            knowledgeBases: state.knowledgeBases.filter(kb => kb.id !== id),
            currentKnowledgeBase: state.currentKnowledgeBase?.id === id ? null : state.currentKnowledgeBase,
            selectedKnowledgeBaseIds: state.selectedKnowledgeBaseIds.filter(kbId => kbId !== id),
            isLoading: false,
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to delete knowledge base'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      getKnowledgeBaseById: async (id: string, spaceId: string) => {
        try {
          set({ isLoading: true, error: null })
          const response = await KnowledgeBaseService.getKnowledgeBaseDetail({ id, space_id: spaceId })
          set({ currentKnowledgeBase: response.data, isLoading: false })
          return response.data
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch knowledge base'
          set({ error: errorMessage, isLoading: false })
          return null
        }
      },

      setCurrentKnowledgeBase: (knowledgeBase: KnowledgeBase | null) => {
        set({ currentKnowledgeBase: knowledgeBase })
      },

      setSearchQuery: (query: string) => {
        set({ searchQuery: query })
      },

      setSelectedKnowledgeBaseIds: (ids: string[]) => {
        set({ selectedKnowledgeBaseIds: ids })
      },

      toggleKnowledgeBaseSelection: (id: string) => {
        set(state => ({
          selectedKnowledgeBaseIds: state.selectedKnowledgeBaseIds.includes(id)
            ? state.selectedKnowledgeBaseIds.filter(kbId => kbId !== id)
            : [...state.selectedKnowledgeBaseIds, id],
        }))
      },

      selectAllKnowledgeBases: () => {
        const { knowledgeBases } = get()
        set({ selectedKnowledgeBaseIds: knowledgeBases.map(kb => kb.id) })
      },

      clearSelection: () => {
        set({ selectedKnowledgeBaseIds: [] })
      },

      clearError: () => {
        set({ error: null })
      },

      // 分页相关actions
      setPage: (page: number) => {
        set({ currentPage: page })
      },

      setPageSize: (size: number) => {
        set({ pageSize: size })
      },

      reset: () => {
        set(initialState)
      },
    }),
    {
      name: 'knowledge-base-store',
    },
  ),
)
