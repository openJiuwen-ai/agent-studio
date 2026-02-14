import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import {
  MemoryBase,
  CreateMemoryBaseRequest,
  GetMemoryBasesRequest,
  MemoryBaseItem,
  UpdateMemoryBaseRequest,
  SearchMemoryBaseRequest,
  SearchMemoryBaseItem,
} from '@/types/memoryBase' // 替换为记忆库对应的类型文件
import { MemoryBaseService } from '@test-agentstudio/api-client' // 替换为记忆库对应的API服务

interface MemoryBaseState {
  memoryBases: MemoryBase[]
  currentMemoryBase: MemoryBase | null
  isLoading: boolean
  error: string | null
  searchQuery: string
  selectedMemoryBaseIds: string[]
  isSearching: boolean
  // 分页相关
  total: number
  currentPage: number
  pageSize: number
}

interface MemoryBaseActions {
  fetchMemoryBases: (spaceId?: string, page?: number, size?: number) => Promise<void>
  searchMemoryBases: (spaceId: string, query: string, page?: number, size?: number) => Promise<void>
  createMemoryBase: (data: CreateMemoryBaseRequest) => Promise<{ mdb_id: string }>
  updateMemoryBase: (data: UpdateMemoryBaseRequest) => Promise<void>
  deleteMemoryBase: (id: string, spaceId: string) => Promise<void>
  getMemoryBaseById: (id: string, spaceId: string) => Promise<MemoryBase | null>
  setCurrentMemoryBase: (memoryBase: MemoryBase | null) => void
  setSearchQuery: (query: string) => void
  setSelectedMemoryBaseIds: (ids: string[]) => void
  toggleMemoryBaseSelection: (id: string) => void
  selectAllMemoryBases: () => void
  clearSelection: () => void
  clearError: () => void
  reset: () => void
  // 分页相关actions
  setPage: (page: number) => void
  setPageSize: (size: number) => void
}

type MemoryBaseStore = MemoryBaseState & MemoryBaseActions

const initialState: MemoryBaseState = {
  memoryBases: [],
  currentMemoryBase: null,
  isLoading: false,
  error: null,
  searchQuery: '',
  selectedMemoryBaseIds: [],
  isSearching: false,
  // 分页相关
  total: 0,
  currentPage: 1,
  pageSize: 20,
}

export const useMemoryBaseStore = create<MemoryBaseStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      fetchMemoryBases: async (spaceId = '0', page = 1, size = 20) => {
        try {
          set({ isLoading: true, error: null })
          const request: GetMemoryBasesRequest = {
            space_id: spaceId,
            page: page,
            page_size: size,
          }
          const response = await MemoryBaseService.getMemoryBases(request)
          // 转换API响应的MemoryBaseItem格式为前端使用的MemoryBase格式
          const memoryBases: MemoryBase[] = response.data.items.map((item: MemoryBaseItem) => ({
            mdb_id: item.mdb_id,
            name: item.name || '未命名记忆库',
            description: item.description,
            status: item.status,
            space_id: spaceId,
            embedding_model_config_id: item.embedding_model_config_id,
            llm_model_config_id: item.llm_model_config_id,
            created_at: item.created_at,
            updated_at: item.updated_at,
            created_by: '',
            memoryCount: 0, // 替换为记忆库的数量字段
            size: 0,
          }))

          set({
            memoryBases,
            total: response.data.total,
            currentPage: response.data.page || page,
            pageSize: response.data.size || size, // 统一分页参数
            isLoading: false,
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch memory bases'
          set({ error: errorMessage, isLoading: false })
        }
      },

      searchMemoryBases: async (spaceId: string, query: string, page = 1, size = 20) => {
        try {
          set({ isSearching: true, error: null })
          const request: SearchMemoryBaseRequest = {
            space_id: spaceId,
            query: query.trim(),
            page: page,
            page_size: size,
          }
          const response = await MemoryBaseService.searchMemoryBase(request)

          // 转换搜索API响应的SearchMemoryBaseItem格式为前端使用的MemoryBase格式
          const memoryBases: MemoryBase[] = response.data.memory_bases.map((item: SearchMemoryBaseItem) => ({
            mdb_id: item.mdb_id,
            name: item.name || '未命名记忆库',
            description: item.description,
            type: 'text' as const, // 搜索接口返回的都是文本记忆库（可根据实际业务调整）
            status: 'active' as const,
            space_id: item.space_id,
            embedding_model_config_id: item.embedding_model_config_id,
            llm_model_config_id: item.llm_model_config_id,
            created_at: item.created_at, // 时间戳转换为ISO字符串
            updated_at: item.updated_ad,
            created_by: '',
            memoryCount: 0,
            size: 0,
          }))

          set({
            memoryBases,
            total: response.data.total,
            currentPage: response.data.page || page, // 容错：优先用返回值，无则用入参
            pageSize: response.data.page_size || size, // 统一分页参数
            isSearching: false,
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to search memory bases'
          set({ error: errorMessage, isSearching: false })
        }
      },

      createMemoryBase: async (data: CreateMemoryBaseRequest) => {
        try {
          set({ isLoading: true, error: null })
          const response = await MemoryBaseService.createMemoryBase(data)
          set({ isLoading: false })
          return response
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to create memory base'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      updateMemoryBase: async (data: UpdateMemoryBaseRequest) => {
        try {
          await MemoryBaseService.updateMemoryBase(data);

          set((state) => {
            const updatedMemoryBases = state.memoryBases.map((mb) => {
              if (mb.mdb_id === data.mdb_id) {
                return {
                  ...mb,
                  name: data.name,
                  description: data.description,
                  llm_model_config_id: data.llm_model_config_id || mb.llm_model_config_id,
                } as MemoryBase;
              }
              return mb;
            });

            let updatedCurrentMemoryBase = state.currentMemoryBase;
            if (updatedCurrentMemoryBase?.mdb_id === data.mdb_id) {
              updatedCurrentMemoryBase = {
                ...updatedCurrentMemoryBase,
                name: data.name,
                description: data.description,
                llm_model_config_id: data.llm_model_config_id || updatedCurrentMemoryBase.llm_model_config_id,
              } as MemoryBase;
            }

            return {
              memoryBases: updatedMemoryBases,
              currentMemoryBase: updatedCurrentMemoryBase,
            };
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to update memory base';
          set({ error: errorMessage });
          throw error;
        }
      },

      deleteMemoryBase: async (id: string, spaceId: string) => {
        try {
          set({ isLoading: true, error: null })
          await MemoryBaseService.deleteMemoryBase({ space_id: spaceId, mdb_id: id })
          set(state => ({
            memoryBases: state.memoryBases.filter(mb => mb.mdb_id !== id),
            currentMemoryBase: state.currentMemoryBase?.mdb_id === id ? null : state.currentMemoryBase,
            selectedMemoryBaseIds: state.selectedMemoryBaseIds.filter(mbId => mbId !== id),
            isLoading: false,
          }))
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to delete memory base'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      getMemoryBaseById: async (id: string, spaceId: string) => {
        try {
          set({ isLoading: true, error: null })
          const response = await MemoryBaseService.getMemoryBaseDetail({ id, space_id: spaceId })
          set({ currentMemoryBase: response.data, isLoading: false })
          return response.data
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch memory base'
          set({ error: errorMessage, isLoading: false })
          return null
        }
      },

      setCurrentMemoryBase: (memoryBase: MemoryBase | null) => {
        set({ currentMemoryBase: memoryBase })
      },

      setSearchQuery: (query: string) => {
        set({ searchQuery: query })
      },

      setSelectedMemoryBaseIds: (ids: string[]) => {
        set({ selectedMemoryBaseIds: ids })
      },

      toggleMemoryBaseSelection: (id: string) => {
        set(state => ({
          selectedMemoryBaseIds: state.selectedMemoryBaseIds.includes(id)
            ? state.selectedMemoryBaseIds.filter(mbId => mbId !== id)
            : [...state.selectedMemoryBaseIds, id],
        }))
      },

      selectAllMemoryBases: () => {
        const { memoryBases } = get()
        set({ selectedMemoryBaseIds: memoryBases.map(mb => mb.mdb_id) })
      },

      clearSelection: () => {
        set({ selectedMemoryBaseIds: [] })
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
      name: 'memory-bases-store', // devtools标识名
    },
  ),
)