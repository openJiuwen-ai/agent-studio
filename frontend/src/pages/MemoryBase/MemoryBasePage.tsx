import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, Brain, Plus, Grid, List, Trash2, Settings, Upload, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar';
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog';
import { useUIStore } from '@/stores/useUIStore';
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { ENV_CONFIG } from '@/config/environment';
import { MemoryBase } from '@/types/memoryBase';
import MemoryBaseFormDialog from './components/MemoryBaseFormDialog';
import MemoryBaseCard from './components/MemoryBaseCard';

const MemoryBasePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedMemoryBase, setSelectedMemoryBase] = useState<MemoryBase | null>(null);
  const [referencingAgents, setReferencingAgents] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);

  const {
    memoryBases,
    isLoading,
    isSearching,
    fetchMemoryBases,
    searchMemoryBases,
    deleteMemoryBase,
    total,
    currentPage,
    pageSize,
    setPage,
    setPageSize,
  } = useMemoryBaseStore();
  
  const { memoryBaseViewMode, setMemoryBaseViewMode } = useUIStore();
  const { user } = useAuthStore();
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar();

  // 计算总页数
  const totalPages = Math.ceil(total / pageSize) + 1;
  const MAX_MEMORY_BASES = 100;
  const isAtLimit = total >= MAX_MEMORY_BASES;

  const isResettingRef = useRef<boolean>(false);
  const hasCheckedRef = useRef<boolean>(false);

  // 检测页面切换并重置分页
  useEffect(() => {
    const currentPath = location.pathname;
    
    if (currentPath === '/dashboard/memory-bases') {
      // 只在第一次进入时检查
      if (!hasCheckedRef.current) {
        hasCheckedRef.current = true;
        
        // 检查是否从详情页返回
        const fromDetail = sessionStorage.getItem('mb_from_detail') === 'true';
        
        // 如果是从详情页返回，清除标记但不重置分页
        if (fromDetail) {
          sessionStorage.removeItem('mb_from_detail');
          return;
        }
        
        // 获取上一个非 memory-bases 的路径
        const prevNonMbPath = sessionStorage.getItem('mb_last_non_mb_path') || '';
        
        // 判断是否从其他页面切换回来（上一个路径不是 memory-bases 相关的）
        const isFromOtherPage = prevNonMbPath !== '' && 
                               prevNonMbPath !== '/dashboard/memory-bases' && 
                               !prevNonMbPath.startsWith('/dashboard/memory-bases/');
        
        if (isFromOtherPage) {
          console.log('[MemoryBasePage] 从其他页面切换回来，重置分页', { prevNonMbPath, currentPath });
          isResettingRef.current = true;
          const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
          const currentSearchTerm = searchTerm.trim();
          
          setPage(1);
          const loadPromise = !currentSearchTerm
            ? fetchMemoryBases(spaceId, 1, pageSize)
            : searchMemoryBases(spaceId, currentSearchTerm, 1, pageSize);
          
          loadPromise.finally(() => {
            isResettingRef.current = false;
          });
        }
      }
    } else {
      // 不在 memory-bases 列表页时，重置检查标记
      hasCheckedRef.current = false;
      // 只有在不是 memory-bases 相关页面时，才更新 mb_last_non_mb_path
      if (!currentPath.startsWith('/dashboard/memory-bases')) {
        sessionStorage.setItem('mb_last_non_mb_path', currentPath);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  // 处理页码变化
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  // 处理页面大小变化
  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setPage(1); // 重置到第一页
  };

  // 搜索记忆库
  const handleSearch = async (query: string, page: number = currentPage) => {
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    if (query.trim()) {
      await searchMemoryBases(spaceId, query, page, pageSize);
    } else {
      await fetchMemoryBases(spaceId, page, pageSize);
    }
  };

  // 防抖搜索
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(searchTerm);
  const prevSearchTermRef = useRef<string>('');
  const prevPageRef = useRef<number>(currentPage);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 500); // 500ms 防抖

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // 统一处理搜索逻辑
  useEffect(() => {
    if (isResettingRef.current) {
      return;
    }
    
    const prevSearchTerm = prevSearchTermRef.current;
    const isSearchTermChanged = debouncedSearchTerm !== prevSearchTerm;
    const isPageChanged = prevPageRef.current !== currentPage;
    
    // 当搜索关键词改变时，如果当前不在第一页，重置到第一页
    if (isSearchTermChanged && debouncedSearchTerm.trim() !== '' && currentPage !== 1) {
      prevSearchTermRef.current = debouncedSearchTerm;
      prevPageRef.current = 1;
      setPage(1);
      return; // 重置页码后，会在下一次 useEffect 触发时执行搜索
    }
    
    // 更新 ref
    if (isSearchTermChanged) {
      prevSearchTermRef.current = debouncedSearchTerm;
    }
    if (isPageChanged) {
      prevPageRef.current = currentPage;
    }
    
    // 执行搜索
    handleSearch(debouncedSearchTerm, currentPage);
  }, [debouncedSearchTerm, currentPage, pageSize]);

  useEffect(() => {
    if (isResettingRef.current) {
      return;
    }
    
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    if (!searchTerm.trim() && location.pathname === '/dashboard/memory-bases') {
      fetchMemoryBases(spaceId, currentPage, pageSize);
    }
  }, [fetchMemoryBases, user?.spaceId, location.pathname]);

  const handleCreateMemoryBase = () => {
    setSelectedMemoryBase(null);
    setShowCreateDialog(true);
  };

  const handleEditMemoryBase = (mb: MemoryBase) => {
    if (!mb.mdb_id) return;
    
    // 设置标记，表示是从列表页进入详情页的
    sessionStorage.setItem('mb_from_detail', 'true');
    
    // 导航到编辑页面，传递记忆库数据
    navigate(`/dashboard/memory-bases/${mb.mdb_id}/edit`, {
      state: { memoryBase: mb },
    });
  };

  const handleDeleteMemoryBase = async (mb: MemoryBase) => {
    setSelectedMemoryBase(mb);
    // 检查是否被智能体引用
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
      const { MemoryBaseService } = await import('@test-agentstudio/api-client');
      // 注意：这里需要根据实际API调整，假设存在获取引用智能体的方法
      const result = await MemoryBaseService.getReferencingAgents({
        space_id: spaceId,
        mb_id: mb.mdb_id,
      });
      setReferencingAgents(result.agent_names || []);
      setReferencingAgents([]); // 暂时设为空数组，因为API可能不存在
    } catch (error) {
      console.error('Failed to get referencing agents:', error);
      setReferencingAgents([]);
    }
    setShowDeleteDialog(true);
  };

  const confirmDelete = async () => {
    // 防止重复点击
    if (!selectedMemoryBase || isDeleting) {
      return;
    }
    
    setIsDeleting(true);
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
      await deleteMemoryBase(selectedMemoryBase.mdb_id, spaceId);
      setShowDeleteDialog(false);
      setSelectedMemoryBase(null);
      setReferencingAgents([]);
      showSuccess(t('memoryBases.delete.success'));
      // 重新获取记忆库列表或搜索结果
      if (searchTerm.trim()) {
        await searchMemoryBases(spaceId, searchTerm, currentPage, pageSize);
      } else {
        await fetchMemoryBases(spaceId, currentPage, pageSize);
      }
    } catch (error) {
      console.error('Failed to delete memory base:', error);
      showError(t('memoryBases.delete.error'));
    } finally {
      setIsDeleting(false);
    }
  };

  const TabButton = ({ tab, label, count, isActive, onClick }: { tab: string; label: string; count?: number; isActive: boolean; onClick: () => void }) => (
    <button
      className={`px-4 py-2 rounded-lg font-medium transition-colors ${isActive ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
      onClick={onClick}
    >
      <div className="flex items-center space-x-2">
        <span>{label}</span>
        {count !== undefined && (
          <span className={`px-2 py-1 rounded-full text-xs ${isActive ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'}`}>{count}</span>
        )}
      </div>
    </button>
  );

  const ViewModeButton = ({
    mode,
    icon: Icon,
    isActive,
    onClick,
  }: {
    mode: 'grid' | 'list';
    icon: React.ElementType;
    isActive: boolean;
    onClick: () => void;
  }) => (
    <button
      className={`p-2 rounded-lg transition-colors ${isActive ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
      onClick={onClick}
    >
      <Icon className="w-4 h-4" />
    </button>
  );

  const CustomButton = ({
    children,
    variant = 'primary',
    size = 'md',
    onClick,
    type = 'button',
    disabled = false,
    className = '',
  }: {
    children: React.ReactNode;
    variant?: 'primary' | 'secondary' | 'outline';
    size?: 'sm' | 'md';
    onClick?: () => void;
    type?: 'button' | 'submit';
    disabled?: boolean;
    className?: string;
  }) => {
    const baseClasses =
      'font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 inline-flex items-center justify-center';
    const variantClasses = {
      primary: 'bg-blue-500 text-white hover:bg-blue-600',
      secondary: 'bg-gray-500 text-white hover:bg-gray-600',
      outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50',
    };
    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm min-w-[100px]',
      md: 'px-4 py-2 min-w-[140px]',
    };

    return (
      <button
        type={type}
        className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
        onClick={onClick}
        disabled={disabled}
      >
        {children}
      </button>
    );
  };

  // 示例记忆库数据
  // const sampleMemoryBases: MemoryBase[] = [
  //   {
  //     id: 'sample-mb-1',
  //     name: '出游助手记忆库',
  //     description: '记录出游助手Agent的记忆',
  //     type: 'text',
  //     status: 'active',
  //     memoryCount: 120,
  //     size: 1024 * 1024 * 50, // 50MB
  //     space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
  //     created_at: '2023-05-15T10:30:00Z',
  //     updated_at: '2023-06-20T14:20:00Z',
  //     created_by: user?.id || 'admin',
  //     embedding_model_config_id: 1,
  //     llm_model_id: 1,
  //     embeddingModel: 'text-embedding-ada-002',
  //     config: {
  //       type: 'memory',
  //       llm_model_id: 1
  //     }
  //   },
  //   {
  //     id: 'sample-mb-2',
  //     name: '金融类记忆库',
  //     description: '记录金融相关Agent的记忆库',
  //     type: 'text',
  //     status: 'inactive',
  //     memoryCount: 85,
  //     size: 1024 * 1024 * 30, // 30MB
  //     space_id: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
  //     created_at: '2023-06-01T09:15:00Z',
  //     updated_at: '2023-06-22T11:45:00Z',
  //     created_by: user?.id || 'admin',
  //     embedding_model_config_id: 2,
  //     llm_model_id: 2,
  //     embeddingModel: 'text-embedding-3-small',
  //     config: {
  //       type: 'memory',
  //       llm_model_id: 2
  //     }
  //   }
  // ];

  const displayMemoryBases = searchTerm ? memoryBases : [...memoryBases];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 p-6">
      {/* 页面头部介绍 */}
      <div className="mb-8 text-center">
        <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-4 shadow-lg">
          <Brain className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600 mb-2">{t('memoryBases.title')}</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">{t('memoryBases.description')}</p>
      </div>

      {/* 页面主要内容 */}
      <div className="w-full mx-auto">
        {/* 标签页 */}
        <div className="flex space-x-2 mb-6">
          <TabButton
            tab="list"
            label={searchTerm.trim() ? t('memoryBases.search.results') : t('memoryBases.tabs.myMemoryBases')}
            count={displayMemoryBases.length}
            isActive={true}
            onClick={() => {}}
          />
        </div>

        {/* 工具栏 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4 flex-1">
            {/* 搜索框 */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder={t('memoryBases.searchPlaceholder')}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* 视图切换 */}
            <div className="flex items-center space-x-2 bg-white rounded-lg border border-gray-200 p-1">
              <ViewModeButton mode="grid" icon={Grid} isActive={memoryBaseViewMode === 'grid'} onClick={() => setMemoryBaseViewMode('grid')} />
              <ViewModeButton mode="list" icon={List} isActive={memoryBaseViewMode === 'list'} onClick={() => setMemoryBaseViewMode('list')} />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-col items-end space-y-1">
            <CustomButton onClick={handleCreateMemoryBase} className="px-6" disabled={isAtLimit}>
              <Plus className="w-4 h-4 mr-2" />
              {t('memoryBases.createButton')}
            </CustomButton>
            {isAtLimit && (
              <p className="text-sm text-red-500">{t('memoryBases.limit.reached')}</p>
            )}
          </div>
        </div>

        {/* 记忆库列表/网格 */}
        <div className={memoryBaseViewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-4'}>
          {displayMemoryBases.map(mb => (
            <MemoryBaseCard
              key={mb.mdb_id}
              memoryBase={mb}
              viewMode={memoryBaseViewMode}
              onEdit={() => handleEditMemoryBase(mb)}
              onDelete={() => handleDeleteMemoryBase(mb)}
              onClick={() => {
                // 导航到记忆库详情页
                console.log('Navigate to memory base:', mb.mdb_id);
              }}
            />
          ))}
        </div>

        {/* 加载状态 */}
        {(isLoading || isSearching) && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2 text-gray-600">{isSearching ? t('memoryBases.search.searching') : t('memoryBases.search.loading')}</span>
          </div>
        )}

        {/* 空状态 */}
        {displayMemoryBases.length === 0 && !isLoading && !isSearching && (
          <div className="text-center py-12">
            <Brain className="mx-auto w-16 h-16 text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">{searchTerm.trim() ? t('memoryBases.search.noResults') : t('memoryBases.empty.title')}</h3>
            <p className="text-gray-600">{searchTerm.trim() ? t('memoryBases.search.tryOtherKeywords') : t('memoryBases.empty.description')}</p>
          </div>
        )}

        {/* 分页组件 */}
        {!isLoading && !isSearching && displayMemoryBases.length > 0 && (
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
              <span className="text-sm text-gray-600">{t('common.pagination.total', { total: displayMemoryBases.length })}</span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className={`p-2 rounded-lg ${currentPage === 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                <ChevronLeft className="w-5 h-5" />
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
                      key={`page-${pageNum}`}
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
                <ChevronRight className="w-5 h-5" />
              </button>

              <span className="text-sm text-gray-600 ml-4">{t('common.pagination.page', { current: currentPage, total: totalPages })}</span>
            </div>
          </div>
        )}
      </div>

      {/* 创建/编辑记忆库对话框 */}
      <MemoryBaseFormDialog
        open={showCreateDialog}
        memoryBase={selectedMemoryBase}
        onClose={() => {
          setShowCreateDialog(false);
          setSelectedMemoryBase(null);
        }}
        onSuccess={() => {
          setShowCreateDialog(false);
          setSelectedMemoryBase(null);
          const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
          if (searchTerm.trim()) {
            searchMemoryBases(spaceId, searchTerm, currentPage, pageSize);
          } else {
            fetchMemoryBases(spaceId, currentPage, pageSize);
          }
        }}
      />

      {/* 删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        title={t('memoryBases.delete.title')}
        message={
          referencingAgents.length > 0 ? (
            <div className="space-y-3 text-base">
              <p className="text-gray-600">{t('memoryBases.delete.referencedByAgents')}</p>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <ul className="list-disc list-inside space-y-1">
                  {referencingAgents.map((agentName, index) => (
                    <li key={index} className="text-gray-800 font-medium">
                      {agentName}
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-gray-600">{t('memoryBases.delete.deleteWarning')}</p>
              <p className="text-gray-600">{t('memoryBases.delete.confirmDelete')}</p>
            </div>
          ) : (
            <p className="text-gray-600 text-lg leading-relaxed">
              {t('memoryBases.delete.confirmMessage')}
              {selectedMemoryBase?.name && selectedMemoryBase.name.length > 30 ? (
                <span title={selectedMemoryBase.name} className="font-medium">
                  「{selectedMemoryBase.name.substring(0, 30)}...」
                </span>
              ) : (
                <span className="font-medium">「{selectedMemoryBase?.name}」</span>
              )}
              {t('memoryBases.delete.cannotUndo')}
            </p>
          )
        }
        confirmButtonText={t('common.buttons.delete')}
        cancelButtonText={t('common.cancel')}
        onConfirm={confirmDelete}
        onClose={() => {
          if (!isDeleting) {
            setShowDeleteDialog(false);
            setSelectedMemoryBase(null);
            setReferencingAgents([]);
          }
        }}
        isLoading={isDeleting}
        itemType="memoryBase"
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  );
};

export default MemoryBasePage;
