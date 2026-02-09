import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';
import { Plus } from 'lucide-react';
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar';
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog';
import { useUIStore } from '@/stores/useUIStore';
import { useMemoryBaseStore } from '@/stores/useMemoryBaseStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { useEmbeddingModels, MemoryBaseService } from '@test-agentstudio/api-client';
import { ENV_CONFIG } from '@/config/environment';
import { MemoryBase } from '@/types/memoryBase';
import { CommonPageLayout, SearchInput } from '@/components/Common/common-page';
import { useOptimizedSearch } from '@/hooks/useSearchOptimization';
import MemoryBaseFormDialog from './components/MemoryBaseFormDialog';
import { MemoryBaseGridView } from './components/MemoryBaseGridview';
import { MemoryBaseTableView } from './components/MemoryBaseTableView';

type ViewType = 'grid' | 'table';

const PAGE_SIZE_OPTIONS = [20, 60, 100, 200];
const MAX_MEMORY_BASES = 100;

const MemoryBasePageNew: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar();

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

  const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
  const { data: embeddingModelsResponse, isLoading: embeddingModelsLoading } = useEmbeddingModels({ spaceId });
  const embeddingModelMap = useMemo(() => {
    const items = embeddingModelsResponse?.items || [];
    return items.reduce((acc, m) => {
      acc[m.id] = { name: m.name, isActive: m.isActive };
      return acc;
    }, {} as Record<string, { name: string; isActive: boolean }>);
  }, [embeddingModelsResponse?.items]);

  const { memoryBaseViewMode, setMemoryBaseViewMode } = useUIStore();
  const viewType: ViewType = memoryBaseViewMode === 'list' ? 'table' : 'grid';
  const setViewType = useCallback(
    (type: ViewType) => setMemoryBaseViewMode(type === 'table' ? 'list' : 'grid'),
    [setMemoryBaseViewMode],
  );

  const searchOptimization = useOptimizedSearch(undefined, {
    debounceDelay: 300,
    minChars: 0,
    immediateOnEmpty: false,
    respectComposition: true,
  });
  const { searchTerm, debouncedSearchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd } =
    searchOptimization;

  const isAtLimit = total >= MAX_MEMORY_BASES;
  const effectiveLoading = isLoading || isSearching;
  const isResettingRef = useRef<boolean>(false);
  const hasCheckedRef = useRef<boolean>(false);
  const prevSearchTermRef = useRef<string>('');

  // 返场/重置：从其他模块切回时重置分页并重新拉数；从详情返回不重置
  useEffect(() => {
    const currentPath = location.pathname;
    if (currentPath === '/dashboard/memory-bases') {
      if (!hasCheckedRef.current) {
        hasCheckedRef.current = true;
        const fromDetail = sessionStorage.getItem('mb_from_detail') === 'true';
        if (fromDetail) {
          sessionStorage.removeItem('mb_from_detail');
          return;
        }
        const prevNonMbPath = sessionStorage.getItem('mb_last_non_mb_path') || '';
        const isFromOtherPage =
          prevNonMbPath !== '' &&
          prevNonMbPath !== '/dashboard/memory-bases' &&
          !prevNonMbPath.startsWith('/dashboard/memory-bases/');
        if (isFromOtherPage) {
          isResettingRef.current = true;
          const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
          const term = searchTerm.trim();
          setPage(1);
          const loadPromise = term
            ? searchMemoryBases(spaceId, term, 1, pageSize)
            : fetchMemoryBases(spaceId, 1, pageSize);
          loadPromise.finally(() => {
            isResettingRef.current = false;
          });
        }
      }
    } else {
      hasCheckedRef.current = false;
      if (!currentPath.startsWith('/dashboard/memory-bases')) {
        sessionStorage.setItem('mb_last_non_mb_path', currentPath);
      }
    }
  }, [location.pathname, user?.spaceId, setPage, pageSize, fetchMemoryBases, searchMemoryBases, searchTerm]);

  // 搜索词由空变为非空时，重置到第一页
  useEffect(() => {
    const cur = debouncedSearchTerm.trim();
    const prev = prevSearchTermRef.current.trim();
    if (cur !== '' && prev === '') {
      setPage(1);
    }
    prevSearchTermRef.current = debouncedSearchTerm;
  }, [debouncedSearchTerm, setPage]);

  // 根据 debouncedSearchTerm、currentPage、pageSize 拉数
  useEffect(() => {
    if (isResettingRef.current) return;
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
    const term = debouncedSearchTerm.trim();
    if (term) {
      searchMemoryBases(spaceId, term, currentPage, pageSize);
    } else {
      fetchMemoryBases(spaceId, currentPage, pageSize);
    }
  }, [debouncedSearchTerm, currentPage, pageSize, user?.spaceId, fetchMemoryBases, searchMemoryBases]);

  const handlePagerChange = useCallback(
    (page: number, newPageSize: number) => {
      setPage(page);
      setPageSize(newPageSize);
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
      const term = debouncedSearchTerm.trim();
      if (term) {
        searchMemoryBases(spaceId, term, page, newPageSize);
      } else {
        fetchMemoryBases(spaceId, page, newPageSize);
      }
    },
    [user?.spaceId, debouncedSearchTerm, setPage, setPageSize, fetchMemoryBases, searchMemoryBases],
  );

  const handleCreateMemoryBase = useCallback(() => {
    setSelectedMemoryBase(null);
    setShowCreateDialog(true);
  }, []);

  const handleEditMemoryBase = useCallback(
    (mb: MemoryBase) => {
      if (!mb.mdb_id) return;
      sessionStorage.setItem('mb_from_detail', 'true');
      navigate(`/dashboard/memory-bases/${mb.mdb_id}/edit`, { state: { memoryBase: mb } });
    },
    [navigate],
  );

  const handleDeleteMemoryBase = useCallback(
    async (mb: MemoryBase) => {
      setSelectedMemoryBase(mb);
      try {
        const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
        const result = await MemoryBaseService.getReferencingAgents({
          space_id: spaceId,
          mb_id: mb.mdb_id,
        });
        setReferencingAgents(result.agent_names || []);
      } catch (err) {
        console.error('Failed to get referencing agents:', err);
        setReferencingAgents([]);
      }
      setShowDeleteDialog(true);
    },
    [user?.spaceId],
  );

  const confirmDelete = useCallback(async () => {
    if (!selectedMemoryBase || isDeleting) return;
    setIsDeleting(true);
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID;
      await deleteMemoryBase(selectedMemoryBase.mdb_id, spaceId);
      setShowDeleteDialog(false);
      setSelectedMemoryBase(null);
      setReferencingAgents([]);
      showSuccess(t('memoryBases.delete.success'));
      const term = debouncedSearchTerm.trim();
      if (term) {
        await searchMemoryBases(spaceId, term, currentPage, pageSize);
      } else {
        await fetchMemoryBases(spaceId, currentPage, pageSize);
      }
    } catch (err) {
      console.error('Failed to delete memory base:', err);
      showError(t('memoryBases.delete.error'));
    } finally {
      setIsDeleting(false);
    }
  }, [
    selectedMemoryBase,
    isDeleting,
    user?.spaceId,
    deleteMemoryBase,
    showSuccess,
    showError,
    t,
    debouncedSearchTerm,
    currentPage,
    pageSize,
    fetchMemoryBases,
    searchMemoryBases,
  ]);

  const handleViewTypeChange = useCallback(
    (type: ViewType) => {
      setViewType(type);
      setPage(1);
    },
    [setViewType, setPage],
  );

  const toolbarLeft = useMemo(
    () => (
      <SearchInput
        searchTerm={searchTerm}
        placeholder={t('memoryBases.searchPlaceholder')}
        onChange={setSearchTerm}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
      />
    ),
    [searchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd, t],
  );

  const toolbarRight = useMemo(
    () => (
      <>
        <button
          className="btn-primary h-8 flex items-center gap-2 text-sm px-4 disabled:cursor-not-allowed"
          onClick={handleCreateMemoryBase}
          disabled={isAtLimit}
        >
          <Plus className="w-4 h-4" />
          <span>{t('memoryBases.createButton')}</span>
        </button>
        {isAtLimit && (
          <span className="text-xs text-red-500 ml-1">{t('memoryBases.limit.reached')}</span>
        )}
      </>
    ),
    [handleCreateMemoryBase, isAtLimit, t],
  );

  const gridView = useMemo(
    () => (
      <MemoryBaseGridView
        memoryBases={memoryBases}
        searchTerm={debouncedSearchTerm}
        onCreateClick={handleCreateMemoryBase}
        onEdit={handleEditMemoryBase}
        onDelete={handleDeleteMemoryBase}
      />
    ),
    [memoryBases, debouncedSearchTerm, handleCreateMemoryBase, handleEditMemoryBase, handleDeleteMemoryBase],
  );

  const tableView = useMemo(
    () => (
      <MemoryBaseTableView
        memoryBases={memoryBases}
        loading={effectiveLoading}
        searchTerm={debouncedSearchTerm}
        onCreateClick={handleCreateMemoryBase}
        onEdit={handleEditMemoryBase}
        onDelete={handleDeleteMemoryBase}
        embeddingModelMap={embeddingModelMap}
        embeddingModelsLoading={embeddingModelsLoading}
      />
    ),
    [
      memoryBases,
      effectiveLoading,
      debouncedSearchTerm,
      handleCreateMemoryBase,
      handleEditMemoryBase,
      handleDeleteMemoryBase,
      embeddingModelMap,
      embeddingModelsLoading,
    ],
  );

  return (
    <>
      <CommonPageLayout
        title={t('memoryBases.title')}
        viewType={viewType}
        onViewTypeChange={handleViewTypeChange}
        showViewToggle
        pager={{
          total,
          currentPage,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
        }}
        onPagerChange={handlePagerChange}
        loading={effectiveLoading}
        error={null}
        gridView={gridView}
        tableView={tableView}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
      />

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
          const term = debouncedSearchTerm.trim();
          if (term) {
            searchMemoryBases(spaceId, term, currentPage, pageSize);
          } else {
            fetchMemoryBases(spaceId, currentPage, pageSize);
          }
        }}
      />

      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        title={t('memoryBases.delete.title')}
        message={
          referencingAgents.length > 0 ? (
            <div className="space-y-3 text-base">
              <p className="text-gray-600">{t('memoryBases.delete.referencedByAgents')}</p>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <ul className="list-disc list-inside space-y-1">
                  {referencingAgents.map((name, i) => (
                    <li key={i} className="text-gray-800 font-medium">
                      {name}
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
    </>
  );
};

export default MemoryBasePageNew;
