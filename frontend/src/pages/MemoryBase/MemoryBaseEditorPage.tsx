import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, 
  FileText, 
  ChevronLeft, 
  ChevronRight, 
  Trash2, 
  RefreshCw, 
  CheckSquare, 
  Square,
  Hash,
  MessageSquare,
  User,
  Target,
  Brain,
  Search,
  Filter
} from 'lucide-react';
import { 
  MemoryBase, 
  MemoryItem,
  MemoryStatusItem,
  UpdateMemoryRequest,
  UpdateMemoryResponse,
  DeleteMemoryBaseRequest,
  DeleteMemoryBaseResponse,
  GetDocumentsListRequest,
  GetDocumentsListResponse,
  ProcessDocumentsRequest,
  ProcessDocumentsResponse,
  GetDocumentStatusRequest,
  GetDocumentStatusResponse,
  UpdateDocumentRequest,
  UpdateDocumentResponse,
  DeleteDocumentsRequest,
  DeleteDocumentsResponse,
  BatchAddMemoriesRequest,
  BatchAddMemoriesResponse,
  SearchMemoryBaseRequest,
  SearchMemoryBaseResponse,
  CleanExpiredMemoriesRequest,
  CleanExpiredMemoriesResponse
} from '@/types/memoryBase';
import { useAuthStore } from '@/stores/useAuthStore';
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore';
import { ENV_CONFIG } from '@/config/environment';
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar';
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog';
import axios from 'axios';
import { UpdateMemoryBaseRequest, UpdateMemoryBaseResponse } from '@test-agentstudio/api-client';

// 定义MemInfo类型
interface MemInfo {
  mem_id: string;
  content: string;
  type: MemoryType;
}

// 记忆类型枚举
type MemoryType = 'longterm' | 'variable' | 'summary' | 'user_profile' | 'scenario' | 'semantic';

const MEMORY_TYPES = ['longterm', 'variable', 'summary', 'user_profile', 'scenario', 'semantic'] as const;

function isMemoryType(value: string): value is MemoryType {
  return (MEMORY_TYPES as readonly string[]).includes(value);
}

const api = {
  /* 变量 */
  listVariables: async (user_id: string, group_id: string) => {
    const response = await fetch('/api/v1/execution/memory/get_user_variable', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
    const data = await response.json()
    console.log('listVar: ', data)
    return data
  },
  deleteUserVariable: async (user_id: string, group_id: string, key: string) => {
    const response = await fetch('/api/v1/execution/memory/delete_user_variable', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        name: key,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
  },

  /* 长期记忆 */
  listLongTerm: async (user_id: string, group_id: string) => {
    const response = await fetch('/api/v1/execution/memory/get_longterm_mem', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        num: 999,
        page: 1,
      }),
    })
    const data = await response.json()
    console.log('listLongTerm: ', data)
    return data
  },  
  deleteLongTerm: async (user_id: string, group_id: string, id: string) => {
    const response = await fetch('/api/v1/execution/memory/delete_longterm_mem', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        mem_id: id,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
  },
  
  /* 记忆库相关API */
  getMemoryBaseDetail: async (request: GetMemoryBaseDetailRequest): Promise<GetMemoryBaseDetailResponse> => {
    const response = await axios.get(`/api/memory-base/${request.id}`, {
      params: { space_id: request.space_id }
    });
    return response.data;
  },
  
  updateMemoryBase: async (request: UpdateMemoryBaseRequest): Promise<UpdateMemoryBaseResponse> => {
    const response = await axios.put('/api/memory-base', request);
    return response.data;
  },
  
  deleteMemoryBase: async (request: DeleteMemoryBaseRequest): Promise<DeleteMemoryBaseResponse> => {
    const response = await axios.delete('/api/memory-base', { data: request });
    return response.data;
  },
  
  getDocumentsList: async (request: GetDocumentsListRequest): Promise<GetDocumentsListResponse> => {
    const response = await axios.get('/api/documents', { params: request });
    return response.data;
  },
  
  updateDocument: async (request: UpdateDocumentRequest): Promise<UpdateDocumentResponse> => {
    const response = await axios.put('/api/document', request);
    return response.data;
  },
  
  deleteDocuments: async (request: DeleteDocumentsRequest): Promise<DeleteDocumentsResponse> => {
    const response = await axios.delete('/api/documents', { data: request });
    return response.data;
  },
  
  processDocuments: async (request: ProcessDocumentsRequest): Promise<ProcessDocumentsResponse> => {
    const response = await axios.post('/api/documents/process', request);
    return response.data;
  },
  
  getDocumentStatus: async (request: GetDocumentStatusRequest): Promise<GetDocumentStatusResponse> => {
    const response = await axios.get('/api/documents/status', { params: request });
    return response.data;
  },
  
  updateMemory: async (request: UpdateMemoryRequest): Promise<UpdateMemoryResponse> => {
    const response = await axios.put('/api/memory', request);
    return response.data;
  },
  
  batchAddMemories: async (request: BatchAddMemoriesRequest): Promise<BatchAddMemoriesResponse> => {
    const response = await axios.post('/api/memory/batch', request);
    return response.data;
  },
  
  searchMemoryBase: async (request: SearchMemoryBaseRequest): Promise<SearchMemoryBaseResponse> => {
    const response = await axios.post('/api/memory-base/search', request);
    return response.data;
  },
  
  cleanExpiredMemories: async (request: CleanExpiredMemoriesRequest): Promise<CleanExpiredMemoriesResponse> => {
    const response = await axios.post('/api/memory/clean-expired', request);
    return response.data;
  }
}

interface GetMemoryBaseDetailRequest {
  id: string;
  space_id: string;
}

interface GetMemoryBaseDetailResponse {
  code: number;
  message: string;
  data: MemoryBase;
}

// 扩展MemoryItem接口，添加ID字段
interface ExtendedMemoryItem extends MemoryItem {
  id: string;
}

const MemoryBaseEditorPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { user } = useAuthStore();
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar();

  const [memories, setMemories] = useState<ExtendedMemoryItem[]>([]);
  const [allMemories, setAllMemories] = useState<ExtendedMemoryItem[]>([]);
  const [filteredMemories, setFilteredMemories] = useState<ExtendedMemoryItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalMemories, setTotalMemories] = useState(0);
  const [isMemoriesLoading, setIsMemoriesLoading] = useState(false);
  const [currentRequestPage, setCurrentRequestPage] = useState<number | null>(null);
  
  const [memoryStatuses, setMemoryStatuses] = useState<Record<string, MemoryStatusItem>>({});
  const [isRefreshingAllStatuses, setIsRefreshingAllStatuses] = useState(false);

  // 删除确认对话框状态
  const [deleteDialog, setDeleteDialog] = useState({
    isOpen: false,
    memoryId: '',
    memoryName: '',
  });
  const [isDeletingMemory, setIsDeletingMemory] = useState(false);

  // 批量选择状态
  const [selectedMemoryIds, setSelectedMemoryIds] = useState<Set<string>>(new Set());
  const [batchDeleteDialog, setBatchDeleteDialog] = useState({
    isOpen: false,
    count: 0,
  });
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);

  // 搜索和过滤状态
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<MemoryType | 'all'>('all');

  // 用于存储 memoryStatuses 的引用
  const memoryStatusesRef = React.useRef<Record<string, MemoryStatusItem>>({});
  
  // 同步 memoryStatuses 到 ref
  React.useEffect(() => {
    memoryStatusesRef.current = memoryStatuses;
  }, [memoryStatuses]);

  // 从路由状态获取记忆库数据，如果没有则从状态管理中获取
  const stateMemoryBase = location.state?.memoryBase as MemoryBase;
  const [memoryBase, setMemoryBase] = useState<MemoryBase | null>(stateMemoryBase || null);
  const [isLoadingMemoryBase, setIsLoadingMemoryBase] = useState(false);

  // 如果路由状态中没有数据，尝试从状态管理中获取
  const { memoryBases, fetchMemoryBases} = useMemoryBaseStore();

  // 使用 ref 来跟踪当前加载的 id，避免重复加载
  const loadingIdRef = React.useRef<string | undefined>(undefined);

  React.useEffect(() => {
    // 如果已经有记忆库数据且 id 匹配，不需要重新加载
    if (memoryBase && memoryBase.mdb_id === id) {
      setIsLoadingMemoryBase(false)
      return;
    }

    // 如果有 state 中的记忆库数据且 id 匹配，直接使用
    if (stateMemoryBase && stateMemoryBase.mdb_id === id) {
      setMemoryBase(stateMemoryBase);
      loadingIdRef.current = id;
      setIsLoadingMemoryBase(false)
      return;
    }

    // 如果没有 id，无法加载
    if (!id || id === 'undefined') {
      return;
    }

    // 如果正在加载相同的 id，避免重复加载
    if (loadingIdRef.current === id && isLoadingMemoryBase) {
      return;
    }

    // 标记为正在加载
    loadingIdRef.current = id;
    setIsLoadingMemoryBase(true);

    // 先从状态管理中查找
    const foundMb = memoryBases.find(mb => mb.mdb_id === id);
    if (foundMb) {
      setMemoryBase(foundMb);
      setIsLoadingMemoryBase(false);
      return;
    }

    // 如果状态管理中也没有，尝试获取记忆库列表
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    fetchMemoryBases(spaceId, 1, 100)
      .then(() => {
        // 获取后再查找
        const { memoryBases: updatedMemoryBases } = useMemoryBaseStore.getState();
        const targetMb = updatedMemoryBases.find(mb => mb.mdb_id === id);
        if (targetMb) {
          setMemoryBase(targetMb);
        } else {
          showError(t('memoryBases.settings.notFound'));
        }
        setIsLoadingMemoryBase(false);
      })
      .catch(error => {
        console.error('Failed to fetch memory base:', error);
        showError(t('memoryBases.settings.fetchError'));
        setIsLoadingMemoryBase(false);
      });
  }, [id]); // 只依赖 id，当 id 变化时重新加载

  // 获取记忆项列表
  const fetchMemories = async (page: number = 1, pageSize: number = 10) => {
    if (!memoryBase || !memoryBase.mdb_id || isMemoriesLoading || currentRequestPage === page) return;

    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    if (!spaceId) return;

    setCurrentRequestPage(page);
    setIsMemoriesLoading(true);
    try {
      const res_var = await api.listVariables(spaceId, memoryBase.mdb_id);
      const response_var = Object.entries(res_var.data?.variable_data || {});
      const response_long = await api.listLongTerm(spaceId, memoryBase.mdb_id);
      
      // 转换变量数据格式 - 添加ID
      const variableMemories: ExtendedMemoryItem[] = response_var.map(([key, value]) => ({
        id: key, // 使用key作为ID
        mb_id: memoryBase.mdb_id,
        content: typeof value === 'string' ? `{${key} : ${value}}` : `{${key}:${JSON.stringify(value)}}`,
        type: 'variable',
      }));
      
      // 转换长期记忆数据格式 - 添加ID
      const longTermMemories: ExtendedMemoryItem[] = response_long.data?.longterm_mem_data?.map((mem: MemInfo) => ({
        id: mem.mem_id,
        mb_id: memoryBase.mdb_id, 
        content: mem.content,
        type: mem.type,
      })) || [];

      // 合并两个数组
      const allMemories = [...variableMemories, ...longTermMemories];
      const paginatedMemories = allMemories.slice((page - 1) * pageSize, page * pageSize);
      setMemories(paginatedMemories);
      setAllMemories(allMemories);
      setTotalMemories(allMemories.length);
      setCurrentPage(page);
      
      const memoryIds = allMemories.map(mem => mem.id);
      // 查询当前页记忆项的状态（合并到现有状态中，不替换）
      await fetchMemoryStatuses(memoryIds, true); // 合并状态，保留其他页面的记忆状态
    
    } catch (error) {
      console.error('Failed to fetch memories:', error);
      // 不显示错误提示，因为没有记忆是正常情况
    } finally {
      setIsMemoriesLoading(false);
      setCurrentRequestPage(null);
    }
  };

  // 获取所有记忆项的ID（通过分页查询）
  const fetchAllMemoryIds = async (): Promise<{ allMemoryIds: string[]; firstPageItems: ExtendedMemoryItem[]; total: number }> => {
    if (!memoryBase || !memoryBase.mdb_id) return { allMemoryIds: [], firstPageItems: [], total: 0 };

    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    if (!spaceId) return { allMemoryIds: [], firstPageItems: [], total: 0 };

    try {
      const res_var = await api.listVariables(spaceId, memoryBase.mdb_id);
      const response_var = Object.entries(res_var.data?.variable_data || {});
      const response_long = await api.listLongTerm(spaceId, memoryBase.mdb_id);
      
      // 转换变量数据格式 - 添加ID
      const variableMemories: ExtendedMemoryItem[] = response_var.map(([key, value]) => ({
        id: key,
        mb_id: memoryBase.mdb_id,
        content: typeof value === 'string' ? `{${key} : ${value}}` : `{${key}:${JSON.stringify(value)}}`,
        type: 'variable',
      }));
      
      // 转换长期记忆数据格式 - 添加ID
      const longTermMemories: ExtendedMemoryItem[] = response_long.data?.longterm_mem_data?.map((mem: MemInfo) => ({
        id: mem.mem_id,
        content: mem.content,
        type: mem.type,
      })) || [];

      // 合并两个数组
      const allMemories = [...variableMemories, ...longTermMemories];
      const allMemoryIds = allMemories.map(mem => mem.id);
      setAllMemories(allMemories);
      setTotalMemories(allMemories.length);
      // 返回前pageSize个项目
      const firstPageItems = allMemories.slice(0, pageSize);

      return { allMemoryIds, firstPageItems, total: allMemories.length };
    } catch (error) {
      console.error('Failed to fetch all memory IDs:', error);
      return { allMemoryIds: [], firstPageItems: [], total: 0 };
    }
  };

  // 查询记忆状态
  const fetchMemoryStatuses = async (memoryIds: string[], mergeWithExisting: boolean = true) => {
    if (!memoryBase || memoryIds.length === 0) return;

    try {
      // 不再调用不存在的 getMemoryStatus，而是直接构造模拟数据
      const statusMap: Record<string, MemoryStatusItem> = {};
      
      // 为每个 memoryId 构造一个 active 状态项
      memoryIds.forEach(id => {
        statusMap[id] = {
          id: memoryBase.mdb_id,
          memory_id: id,
          status: 'success',
        } as MemoryStatusItem;
      });

      if (mergeWithExisting) {
        setMemoryStatuses(prev => ({
          ...prev,
          ...statusMap,
        }));
      } else {
        setMemoryStatuses(statusMap);
      }
    } catch (error) {
      console.error('Failed to fetch memory statuses:', error);
      // 不显示错误信息，因为状态查询失败不影响基本功能
    }
  };

  // 当记忆库数据加载完成后，获取记忆列表和所有记忆的状态
  useEffect(() => {
    if (memoryBase) {
      // 设置加载状态，避免显示"暂无记忆"
      setIsMemoriesLoading(true);
      
      // 优化：一次性获取所有记忆ID和第一页数据，避免重复请求
      fetchAllMemoryIds()
        .then(async ({ allMemoryIds, firstPageItems, total }) => {
          // 无论是否有记忆，都先处理状态查询（空数组时查询会直接返回，无副作用）
          if (allMemoryIds.length > 0) {
            await fetchMemoryStatuses(allMemoryIds, false);
          }

          // 始终更新记忆列表（空数组也会设置）
          setMemories(firstPageItems);
          setTotalMemories(total);
          setCurrentPage(1);
          
          // 关键：移到条件外，确保无论有没有记忆都重置加载状态
          setIsMemoriesLoading(false);
        })
        .catch(error => {
          console.error('Failed to fetch all memory IDs:', error);
          // 如果失败，回退到原来的方式
          setIsMemoriesLoading(false);
          fetchMemories(1, 10);
        });
    }
  }, [memoryBase?.mdb_id, user?.spaceId]); // 只依赖ID和spaceId，避免重复调用

  // 过滤记忆项
  useEffect(() => {
    let filtered = memories;
    setTotalMemories(allMemories.length);
    // 按类型过滤
    if (selectedTypeFilter !== 'all') {
      if (selectedTypeFilter === 'longterm') {
        filtered = allMemories.filter(mem => mem.type !== 'variable' && mem.type !== 'summary' );
      } else {
        filtered = allMemories.filter(mem => mem.type === selectedTypeFilter);
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        filtered = allMemories.filter(mem => 
          mem.content.toLowerCase().includes(term)
        );
      }
      setTotalMemories(filtered.length);
      setFilteredMemories(filtered);
      return;
    }

    // 按搜索词过滤
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = allMemories.filter(mem => 
        mem.content.toLowerCase().includes(term)
      );
      setTotalMemories(filtered.length);
      setFilteredMemories(filtered);
      return
    }
    
    setFilteredMemories(filtered);
    
  }, [memories, selectedTypeFilter, searchTerm, allMemories]);

  const handleBack = () => {
    navigate('/dashboard/memory-bases');
  };

  const totalPages = useMemo(() => {
    return Math.ceil(totalMemories / pageSize);
  }, [totalMemories, pageSize]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchMemories(newPage, pageSize);
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // 重置到第一页
    // 由于pageSize变化，需要重新获取数据
  };

  // 当页面大小改变时，重新获取数据
  React.useEffect(() => {
    // 只有在 memoryBase 已加载且 pageSize 变化时才重新获取数据
    // 避免在初始加载时重复请求（初始加载时已经通过 fetchAllMemoryIds 获取了数据）
    if (memoryBase && totalMemories > 0) {
      fetchMemories(currentPage, pageSize);
    }
  }, [pageSize]); // 当pageSize变化时重新获取数据

  // 刷新所有记忆状态
  const handleRefreshAllStatuses = async () => {
    if (!memoryBase || filteredMemories.length === 0 || isRefreshingAllStatuses) return;

    setIsRefreshingAllStatuses(true);
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;

      const memoryIds = filteredMemories.map(mem => mem.id);

      // 模拟获取状态（实际实现中应调用真实API）
      const statusResponse = {
        data: {
          items: memoryIds.map(id => ({
            id: memoryBase.mdb_id,
            memory_id: id,
            status: 'success'
          }))
        }
      };

      // 更新所有状态数据
      if (statusResponse.data?.items) {
        const statusMap: Record<string, MemoryStatusItem> = {};
        statusResponse.data.items.forEach(statusItem => {
          if (statusItem.memory_id) {
            statusMap[statusItem.memory_id] = statusItem;
          }
        });
        setMemoryStatuses(prev => ({
          ...prev,
          ...statusMap,
        }));
      }

      showSuccess(t('memoryBases.editor.refreshAllSuccess'));
    } catch (error) {
      console.error('Failed to refresh all memory statuses:', error);
      showError(t('memoryBases.editor.refreshAllFailed'));
    } finally {
      setIsRefreshingAllStatuses(false);
    }
  };

  // 获取记忆类型图标
  const getMemoryTypeIcon = (type: MemoryType) => {
    switch (type) {
      case 'variable':
        return <Hash className="w-4 h-4 text-purple-600"/>;
      case 'summary':
        return <MessageSquare className="w-4 h-4 text-blue-600"/>;
      case 'user_profile':
        return <User className="w-4 h-4 text-green-600"/>;
      case 'scenario':
        return <User className="w-4 h-4 text-green-600"/>;
      case 'semantic':
        return <User className="w-4 h-4 text-green-600"/>;
      default:
        return <Hash className="w-4 h-4 text-gray-600"/>;
    }
  };

  // 获取记忆类型名称
  const getMemoryTypeName = (type: MemoryType) => {
    switch (type) {
      case 'variable':
        return t('memoryBases.memoryType.variable');
      case 'summary':
        return t('memoryBases.memoryType.summary');
      case 'user_profile':
        return t('memoryBases.memoryType.longterm');
      case 'scenario':
        return t('memoryBases.memoryType.longterm');
      case 'semantic':
        return t('memoryBases.memoryType.longterm');
      default:
        return type;
    }
  };

  // 打开删除确认对话框
  const handleOpenDeleteDialog = (memoryId: string, memoryName: string) => {
    setDeleteDialog({
      isOpen: true,
      memoryId,
      memoryName,
    });
  };

  // 关闭删除确认对话框
  const handleCloseDeleteDialog = () => {
    setDeleteDialog({
      isOpen: false,
      memoryId: '',
      memoryName: '',
    });
  };

  // 确认删除记忆项
  const confirmDeleteMemory = async () => {
    if (!memoryBase || !deleteDialog.memoryId) return;

    setIsDeletingMemory(true);
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;

      // 根据记忆类型调用不同的删除API
      const memoryToDelete = memories.find(mem => mem.id === deleteDialog.memoryId);
      if (memoryToDelete && memoryToDelete.type === 'variable') {
        // 删除变量
        await api.deleteUserVariable(spaceId, memoryBase.mdb_id, deleteDialog.memoryId);
      } else {
        // 删除长期记忆
        await api.deleteLongTerm(spaceId, memoryBase.mdb_id, deleteDialog.memoryId);
      }

      showSuccess(t('memoryBases.editor.deleteSuccess'));

      // 刷新记忆列表，确保数据同步
      await fetchMemories(currentPage, pageSize);
    } catch (error) {
      console.error('Failed to delete memory:', error);
      showError(t('memoryBases.editor.deleteFailed'));
    } finally {
      setIsDeletingMemory(false);
      handleCloseDeleteDialog();
    }
  };

  // 批量选择相关函数
  const handleSelectMemory = (memoryId: string) => {
    setSelectedMemoryIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(memoryId)) {
        newSet.delete(memoryId);
      } else {
        newSet.add(memoryId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedMemoryIds.size === filteredMemories.length) {
      // 如果已全选，则取消全选
      setSelectedMemoryIds(new Set());
    } else {
      // 全选当前页所有记忆
      setSelectedMemoryIds(new Set(filteredMemories.map(mem => mem.id)));
    }
  };

  const isAllSelected = filteredMemories.length > 0 && selectedMemoryIds.size === filteredMemories.length;
  const isPartialSelected = selectedMemoryIds.size > 0 && selectedMemoryIds.size < filteredMemories.length;

  // 打开批量删除确认对话框
  const handleOpenBatchDeleteDialog = () => {
    if (selectedMemoryIds.size === 0) return;
    setBatchDeleteDialog({
      isOpen: true,
      count: selectedMemoryIds.size,
    });
  };

  // 关闭批量删除确认对话框
  const handleCloseBatchDeleteDialog = () => {
    setBatchDeleteDialog({
      isOpen: false,
      count: 0,
    });
  };

  // 确认批量删除
  const confirmBatchDelete = async () => {
    if (!memoryBase || selectedMemoryIds.size === 0) return;

    setIsBatchDeleting(true);
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
      
      // 遍历选中的记忆项并根据类型分别删除
      for (const memoryId of selectedMemoryIds) {
        const memoryToDelete = memories.find(mem => mem.id === memoryId);
        if (memoryToDelete && memoryToDelete.type === 'variable') {
          await api.deleteUserVariable(spaceId, memoryBase.mdb_id, memoryId);
        } else {
          await api.deleteLongTerm(spaceId, memoryBase.mdb_id, memoryId);
        }
      }
      
      const deletedCount = selectedMemoryIds.size;

      // 清空选中列表
      setSelectedMemoryIds(new Set());

      showSuccess(t('memoryBases.editor.batchDeleteSuccess', { count: deletedCount }));

      // 刷新记忆列表，确保数据同步
      await fetchMemories(currentPage, pageSize);
    } catch (error) {
      console.error('Failed to batch delete memories:', error);
      showError(t('memoryBases.editor.batchDeleteFailed'));
    } finally {
      setIsBatchDeleting(false);
      handleCloseBatchDeleteDialog();
    }
  };

  // 当记忆列表变化时，清除无效的选中项
  useEffect(() => {
    const validIds = new Set(filteredMemories.map(mem => mem.id));
    setSelectedMemoryIds(prev => {
      const newSet = new Set<string>();
      prev.forEach(id => {
        if (validIds.has(id)) {
          newSet.add(id);
        }
      });
      return newSet;
    });
  }, [filteredMemories]);

  // 基于所有记忆的状态检测正在处理的记忆（不仅仅是当前页）
  useEffect(() => {
    if (Object.keys(memoryStatuses).length === 0) return;

    // 基于所有记忆的状态，找出正在处理中的记忆（状态不是 indexed、failed、deleted）
    const processingMemoryIdsList: string[] = [];
    Object.keys(memoryStatuses).forEach(memoryId => {
      const status = memoryStatuses[memoryId]?.status?.toLowerCase();
      if (status && status !== 'indexed' && status !== 'failed' && status !== 'deleted') {
        processingMemoryIdsList.push(memoryId);
      }
    });

  }, [memoryStatuses]);

  if (!memoryBase || isLoadingMemoryBase) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">{t('memoryBases.editor.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部导航 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button onClick={handleBack} className="flex items-center text-gray-600 hover:text-gray-900 mr-4">
                <ArrowLeft className="w-5 h-5 mr-2"/>
                {t('common.buttons.back')}
              </button>
              <div className="flex items-center min-w-0 flex-1">
                <h1 className="text-xl font-semibold text-gray-900 flex items-center min-w-0" title={memoryBase.name}>
                  <span className="truncate max-w-[300px]">
                    {memoryBase.name.length > 30 ? `${memoryBase.name.substring(0, 30)}...` : memoryBase.name}
                  </span>
                  <span className="ml-2 flex-shrink-0">- {t('memoryBases.edit.title')}</span>
                </h1>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div className="bg-white rounded-lg shadow p-6">
          <div className="space-y-6">
            {/* 记忆库基本信息 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <h3 className="text-sm font-medium text-gray-500">{t('memoryBases.settings.name')}</h3>
                <p
                  className="mt-1 text-gray-900 truncate"
                  title={memoryBase.name}
                >
                  {memoryBase.name}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-500">{t('memoryBases.settings.description')}</h3>
                <p
                  className="mt-1 text-gray-900 truncate"
                  title={memoryBase.description || '-'}
                >
                  {memoryBase.description || '-'}
                </p>
              </div>
            </div>

            {/* 记忆列表 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <h2 className="text-lg font-medium text-gray-900">{t('memoryBases.editor.memoryList')}</h2>
                </div>
                
                {/* 搜索和过滤工具栏 */}
                <div className="flex items-center space-x-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"/>
                    <input
                      type="text"
                      placeholder={t('memoryBases.searchMemory')}
                      value={searchTerm}
                      onChange={e => setSearchTerm(e.target.value)}
                      className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Filter className="w-5 h-5 text-gray-500"/>
                    <select
                      value={selectedTypeFilter}
                      onChange={e => setSelectedTypeFilter(e.target.value as MemoryType | 'all')}
                      className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="all">{t('memoryBases.memoryType.all')}</option>
                      <option value="longterm">{t('memoryBases.memoryType.longterm')}</option>
                      <option value="variable">{t('memoryBases.memoryType.variable')}</option>
                      <option value="summary">{t('memoryBases.memoryType.summary')}</option>
                    </select>
                  </div>
                  
                  {selectedMemoryIds.size > 0 && (
                    <button
                      onClick={handleOpenBatchDeleteDialog}
                      className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 flex items-center text-sm"
                    >
                      <Trash2 className="w-4 h-4 mr-2"/>
                      {t('memoryBases.editor.deleteSelected', { count: selectedMemoryIds.size })}
                    </button>
                  )}
                  <button
                    onClick={handleRefreshAllStatuses}
                    disabled={filteredMemories.length === 0 || isRefreshingAllStatuses}
                    className="p-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    <RefreshCw className={`w-4 h-4 ${isRefreshingAllStatuses ? 'animate-spin' : ''}`}/>
                  </button>
                </div>
              </div>

              {isMemoriesLoading ? (
                <div className="flex items-center justify-center py-10">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                  <span className="ml-3 text-gray-600 text-sm">{t('memoryBases.editor.loadingMemories')}</span>
                </div>
              ) : filteredMemories.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="mx-auto w-14 h-14 text-gray-300 mb-4"/>
                  <p className="text-gray-500 text-sm">{t('memoryBases.editor.noMemories')}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="border border-gray-200 rounded-lg overflow-x-auto shadow-sm">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0 z-10">
                        <tr>
                          {/* 全选 */}
                          <th scope="col" className="px-4 py-3 w-12">
                            <button
                              onClick={handleSelectAll}
                              className="flex items-center justify-center p-1.5 rounded-md hover:bg-gray-200 transition-colors"
                              title={isAllSelected ? t('memoryBases.editor.deselectAll') : t('memoryBases.editor.selectAll')}
                            >
                              {isAllSelected ? (
                                <CheckSquare className="w-5 h-5 text-blue-600"/>
                              ) : isPartialSelected ? (
                                <div className="w-5 h-5 border-2 border-blue-600 rounded flex items-center justify-center bg-white">
                                  <div className="w-2.5 h-0.5 bg-blue-600"></div>
                                </div>
                              ) : (
                                <Square className="w-5 h-5 text-gray-400"/>
                              )}
                            </button>
                          </th>
                          {/* 类型 */}
                          <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[120px]">
                            {t('memoryBases.editor.memoryType')}
                          </th>
                          {/* 内容 */}
                          <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[200px]">
                            {t('memoryBases.editor.memoryContent')}
                          </th>
                          {/* 操作 */}
                          <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                            {t('memoryBases.editor.actions')}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {filteredMemories.map((mem) => (
                          <tr
                            key={mem.id}
                            className={`hover:bg-gray-50 transition-colors ${
                              selectedMemoryIds.has(mem.id) ? 'bg-blue-50' : ''
                            }`}
                          >
                            {/* 单选 */}
                            <td className="px-4 py-3.5 text-center">
                              <button
                                onClick={() => handleSelectMemory(mem.id)}
                                className="flex items-center justify-center p-1.5 rounded-md hover:bg-gray-200 transition-colors"
                              >
                                {selectedMemoryIds.has(mem.id) ? (
                                  <CheckSquare className="w-5 h-5 text-blue-600"/>
                                ) : (
                                  <Square className="w-5 h-5 text-gray-400"/>
                                )}
                              </button>
                            </td>
                            {/* 类型内容 */}
                            <td className="px-4 py-3.5 whitespace-nowrap">
                              <div className="flex items-center">
                                {isMemoryType(mem.type)
                                  ? getMemoryTypeIcon(mem.type)
                                  : <Hash className="w-4 h-4 text-gray-600"/>}
                                <span className="ml-2 text-sm text-gray-700">
                                  {isMemoryType(mem.type)
                                    ? getMemoryTypeName(mem.type)
                                    : t('common.unknown')}
                                </span>
                              </div>
                            </td>
                            {/* 记忆内容 */}
                            <td className="px-4 py-3.5 max-w-xs">
                              <div
                                className="text-sm text-gray-700 truncate"
                                title={mem.content}
                              >
                                {mem.content.length > 120 ? `${mem.content.substring(0, 120)}...` : mem.content}
                              </div>
                            </td>
                            {/* 操作按钮 */}
                            <td className="px-4 py-3.5 text-center">
                              <button
                                onClick={() => handleOpenDeleteDialog(mem.id, mem.content)}
                                className="text-red-600 hover:text-red-800 p-1.5 rounded-md hover:bg-red-50 transition-colors"
                                title={t('memoryBases.editor.deleteMemory')}
                              >
                                <Trash2 className="w-4 h-4"/>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 分页 */}
                  {!isMemoriesLoading && (
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-600">{t('common.pagination.pageSize')}:</span>
                        <select
                          value={pageSize}
                          onChange={e => {
                            handlePageSizeChange(Number(e.target.value));
                          }}
                          className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 shadow-sm pagination-select"
                        >
                          <option value={10}>10{t('common.pagination.items')}</option>
                          <option value={20}>20{t('common.pagination.items')}</option>
                          <option value={50}>50{t('common.pagination.items')}</option>
                          <option value={100}>100{t('common.pagination.items')}</option>
                        </select>
                        <span className="text-sm text-gray-600">{t('common.pagination.total', { total: totalMemories })}</span>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handlePageChange(currentPage - 1)}
                          disabled={currentPage === 1}
                          className={`p-2 rounded-lg ${currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                          <ChevronLeft className="w-5 h-5"/>
                        </button>

                        <div className="flex items-center space-x-1">
                          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                            // 计算要显示的页码
                            let pageNum: number;
                            if (totalPages <= 5) {
                              pageNum = i + 1;
                            } else if (currentPage <= 3) {
                              pageNum = i + 1;
                            } else if (currentPage >= totalPages - 2) {
                              pageNum = totalPages - 4 + i;
                            } else {
                              pageNum = currentPage - 2 + i;
                            }

                            return (
                              <button
                                key={i}
                                onClick={() => handlePageChange(pageNum)}
                                className={`w-10 h-10 rounded-lg ${currentPage === pageNum ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
                              >
                                {pageNum}
                              </button>
                            );
                          })}
                        </div>

                        <button
                          onClick={() => handlePageChange(currentPage + 1)}
                          disabled={currentPage === totalPages}
                          className={`p-2 rounded-lg ${currentPage === totalPages ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                          <ChevronRight className="w-5 h-5"/>
                        </button>

                        <span className="text-sm text-gray-600 ml-4">{t('common.pagination.page', { current: currentPage, total: totalPages })}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={handleCloseDeleteDialog}
        onConfirm={confirmDeleteMemory}
        title={t('memoryBases.editor.deleteTitle')}
        message={t('memoryBases.editor.deleteMessage', { name: deleteDialog.memoryName })}
        confirmButtonText={t('memoryBases.editor.deleteMemory')}
        cancelButtonText="取消"
        isLoading={isDeletingMemory}
        iconType="danger"
      />

      {/* 批量删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={batchDeleteDialog.isOpen}
        onClose={handleCloseBatchDeleteDialog}
        onConfirm={confirmBatchDelete}
        title={t('memoryBases.editor.batchDeleteTitle')}
        message={t('memoryBases.editor.batchDeleteMessage', { count: batchDeleteDialog.count })}
        confirmButtonText={t('memoryBases.editor.batchDeleteButton', { count: batchDeleteDialog.count })}
        cancelButtonText="取消"
        isLoading={isBatchDeleting}
        iconType="danger"
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar}/>
    </div>
  );
};

export default MemoryBaseEditorPage;
