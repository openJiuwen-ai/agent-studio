import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { Plus } from 'lucide-react'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import { useUIStore } from '@/stores/useUIStore'
import { useKnowledgeBaseStore } from '@/stores/useKnowledgeBaseStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { useEmbeddingModels } from '@test-agentstudio/api-client'
import { ENV_CONFIG } from '@/config/environment'
import { KnowledgeBase } from '@/types/knowledgeBase'
import { CommonPageLayout, SearchInput } from '@/components/Common/common-page'
import { useOptimizedSearch } from '@/hooks/useSearchOptimization'
import KnowledgeBaseFormDialog from './components/KnowledgeBaseFormDialog'
import { KnowledgeBaseGridView } from './components/KnowledgeBaseGridView'
import { KnowledgeBaseTableView } from './components/KnowledgeBaseTableView'

type ViewType = 'grid' | 'table'

const PAGE_SIZE_OPTIONS = [20, 60, 100]
const MAX_KNOWLEDGE_BASES = 100

const KnowledgeBasePageNew: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()

  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedKnowledgeBase, setSelectedKnowledgeBase] = useState<KnowledgeBase | null>(null)
  const [referencingAgents, setReferencingAgents] = useState<string[]>([])
  const [isDeleting, setIsDeleting] = useState(false)

  const {
    knowledgeBases,
    isLoading,
    isSearching,
    fetchKnowledgeBases,
    searchKnowledgeBases,
    deleteKnowledgeBase,
    total,
    currentPage,
    pageSize,
    setPage,
    setPageSize,
  } = useKnowledgeBaseStore()

  const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const { data: embeddingModelsResponse, isLoading: embeddingModelsLoading } = useEmbeddingModels({
    spaceId,
    page: 1,
    size: 100,
  })
  const embeddingModelMap = useMemo(() => {
    const items = embeddingModelsResponse?.items || []
    return items.reduce((acc, m) => {
      acc[m.id] = { name: m.name, isActive: m.isActive }
      return acc
    }, {} as Record<string, { name: string; isActive: boolean }>)
  }, [embeddingModelsResponse?.items])

  const { knowledgeBaseViewMode, setKnowledgeBaseViewMode } = useUIStore()
  const viewType: ViewType = knowledgeBaseViewMode === 'list' ? 'table' : 'grid'
  const setViewType = useCallback(
    (type: ViewType) => setKnowledgeBaseViewMode(type === 'table' ? 'list' : 'grid'),
    [setKnowledgeBaseViewMode],
  )

  const searchOptimization = useOptimizedSearch(undefined, {
    debounceDelay: 300,
    minChars: 0,
    immediateOnEmpty: false,
    respectComposition: true,
  })
  const { searchTerm, debouncedSearchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd } =
    searchOptimization

  const isAtLimit = total >= MAX_KNOWLEDGE_BASES
  const effectiveLoading = isLoading || isSearching
  const isResettingRef = useRef<boolean>(false)
  const hasCheckedRef = useRef<boolean>(false)
  const prevSearchTermRef = useRef<string>('')

  // 返场/重置：从其他模块切回时重置分页并重新拉数；从详情返回不重置
  useEffect(() => {
    const currentPath = location.pathname
    if (currentPath === '/dashboard/knowledge-bases') {
      if (!hasCheckedRef.current) {
        hasCheckedRef.current = true
        const fromDetail = sessionStorage.getItem('kb_from_detail') === 'true'
        if (fromDetail) {
          sessionStorage.removeItem('kb_from_detail')
          return
        }
        const prevNonKbPath = sessionStorage.getItem('kb_last_non_kb_path') || ''
        const isFromOtherPage =
          prevNonKbPath !== '' &&
          prevNonKbPath !== '/dashboard/knowledge-bases' &&
          !prevNonKbPath.startsWith('/dashboard/knowledge-bases/')
        if (isFromOtherPage) {
          isResettingRef.current = true
          const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
          const term = searchTerm.trim()
          setPage(1)
          const loadPromise = term
            ? searchKnowledgeBases(spaceId, term, 1, pageSize)
            : fetchKnowledgeBases(spaceId, 1, pageSize)
          loadPromise.finally(() => {
            isResettingRef.current = false
          })
        }
      }
    } else {
      hasCheckedRef.current = false
      if (!currentPath.startsWith('/dashboard/knowledge-bases')) {
        sessionStorage.setItem('kb_last_non_kb_path', currentPath)
      }
    }
    // 仅依赖路由与空间；fetch/search 为 store 方法，放入 deps 会导致每次渲染重新执行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, user?.spaceId, pageSize, searchTerm])

  // 搜索词由空变为非空时，重置到第一页
  useEffect(() => {
    const cur = debouncedSearchTerm.trim()
    const prev = prevSearchTermRef.current.trim()
    if (cur !== '' && prev === '') {
      setPage(1)
    }
    prevSearchTermRef.current = debouncedSearchTerm
  }, [debouncedSearchTerm, setPage])

  // 根据 debouncedSearchTerm、currentPage、pageSize 拉数（仅依赖请求参数，避免 store 方法引用变化导致重复请求）
  useEffect(() => {
    if (isResettingRef.current) return
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
    const term = debouncedSearchTerm.trim()
    if (term) {
      searchKnowledgeBases(spaceId, term, currentPage, pageSize)
    } else {
      fetchKnowledgeBases(spaceId, currentPage, pageSize)
    }
    // 不将 fetchKnowledgeBases/searchKnowledgeBases 放入 deps：Zustand 每次渲染返回新引用，会导致无限请求循环
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearchTerm, currentPage, pageSize, user?.spaceId])

  const handlePagerChange = useCallback(
    (page: number, newPageSize: number) => {
      setPage(page)
      setPageSize(newPageSize)
      // 不在此处请求：由上面的 useEffect(debouncedSearchTerm, currentPage, pageSize) 统一拉数，避免重复请求
    },
    [setPage, setPageSize],
  )

  const handleCreateKnowledgeBase = useCallback(() => {
    setSelectedKnowledgeBase(null)
    setShowCreateDialog(true)
  }, [])

  const handleEditKnowledgeBase = useCallback(
    (kb: KnowledgeBase) => {
      if (!kb.id) return
      sessionStorage.setItem('kb_from_detail', 'true')
      navigate(`/dashboard/knowledge-bases/${kb.id}/edit`, { state: { knowledgeBase: kb } })
    },
    [navigate],
  )

  const handleDeleteKnowledgeBase = useCallback(
    async (kb: KnowledgeBase) => {
      setSelectedKnowledgeBase(kb)
      try {
        const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
        const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
        const result = await KnowledgeBaseService.getReferencingAgents({ space_id: spaceId, kb_id: kb.id })
        setReferencingAgents(result.agent_names || [])
      } catch (err) {
        console.error('Failed to get referencing agents:', err)
        setReferencingAgents([])
      }
      setShowDeleteDialog(true)
    },
    [user?.spaceId],
  )

  const confirmDelete = useCallback(async () => {
    if (!selectedKnowledgeBase || isDeleting) return
    setIsDeleting(true)
    try {
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
      await deleteKnowledgeBase(selectedKnowledgeBase.id, spaceId)
      setShowDeleteDialog(false)
      setSelectedKnowledgeBase(null)
      setReferencingAgents([])
      showSuccess(t('knowledgeBases.delete.success'))
      const term = debouncedSearchTerm.trim()
      if (term) {
        await searchKnowledgeBases(spaceId, term, currentPage, pageSize)
      } else {
        await fetchKnowledgeBases(spaceId, currentPage, pageSize)
      }
    } catch (err) {
      console.error('Failed to delete knowledge base:', err)
      showError(t('knowledgeBases.delete.error'))
    } finally {
      setIsDeleting(false)
    }
  }, [
    selectedKnowledgeBase,
    isDeleting,
    user?.spaceId,
    deleteKnowledgeBase,
    showSuccess,
    showError,
    t,
    debouncedSearchTerm,
    currentPage,
    pageSize,
    fetchKnowledgeBases,
    searchKnowledgeBases,
  ])

  const handleViewTypeChange = useCallback(
    (type: ViewType) => {
      setViewType(type)
      setPage(1)
    },
    [setViewType, setPage],
  )

  const toolbarLeft = useMemo(
    () => (
      <SearchInput
        searchTerm={searchTerm}
        placeholder={t('knowledgeBases.searchPlaceholder')}
        onChange={setSearchTerm}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
      />
    ),
    [searchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd, t],
  )

  const toolbarRight = useMemo(
    () => (
      <>
        <button
          className="btn-primary h-8 flex items-center gap-2 text-sm px-4 disabled:cursor-not-allowed"
          onClick={handleCreateKnowledgeBase}
          disabled={isAtLimit}
        >
          <Plus className="w-4 h-4" />
          <span>{t('knowledgeBases.createButton')}</span>
        </button>
        {isAtLimit && (
          <span className="text-xs text-red-500 ml-1">{t('knowledgeBases.limit.reached')}</span>
        )}
      </>
    ),
    [handleCreateKnowledgeBase, isAtLimit, t],
  )

  const gridView = useMemo(
    () => (
      <KnowledgeBaseGridView
        knowledgeBases={knowledgeBases}
        searchTerm={debouncedSearchTerm}
        onCreateClick={handleCreateKnowledgeBase}
        onEdit={handleEditKnowledgeBase}
        onDelete={handleDeleteKnowledgeBase}
      />
    ),
    [knowledgeBases, debouncedSearchTerm, handleCreateKnowledgeBase, handleEditKnowledgeBase, handleDeleteKnowledgeBase],
  )

  const tableView = useMemo(
    () => (
      <KnowledgeBaseTableView
        knowledgeBases={knowledgeBases}
        loading={effectiveLoading}
        searchTerm={debouncedSearchTerm}
        onCreateClick={handleCreateKnowledgeBase}
        onEdit={handleEditKnowledgeBase}
        onDelete={handleDeleteKnowledgeBase}
        embeddingModelMap={embeddingModelMap}
        embeddingModelsLoading={embeddingModelsLoading}
      />
    ),
    [
      knowledgeBases,
      effectiveLoading,
      debouncedSearchTerm,
      handleCreateKnowledgeBase,
      handleEditKnowledgeBase,
      handleDeleteKnowledgeBase,
      embeddingModelMap,
      embeddingModelsLoading,
    ],
  )

  return (
    <>
      <CommonPageLayout
        title={t('knowledgeBases.title')}
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

      <KnowledgeBaseFormDialog
        open={showCreateDialog}
        knowledgeBase={selectedKnowledgeBase}
        onClose={() => {
          setShowCreateDialog(false)
          setSelectedKnowledgeBase(null)
        }}
        onSuccess={() => {
          setShowCreateDialog(false)
          setSelectedKnowledgeBase(null)
          const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
          const term = debouncedSearchTerm.trim()
          if (term) {
            searchKnowledgeBases(spaceId, term, currentPage, pageSize)
          } else {
            fetchKnowledgeBases(spaceId, currentPage, pageSize)
          }
        }}
      />

      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        title={t('knowledgeBases.delete.title')}
        message={
          referencingAgents.length > 0 ? (
            <div className="space-y-3 text-base">
              <p className="text-gray-600">{t('knowledgeBases.delete.referencedByAgents')}</p>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <ul className="list-disc list-inside space-y-1">
                  {referencingAgents.map((name, i) => (
                    <li key={i} className="text-gray-800 font-medium">
                      {name}
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-gray-600">{t('knowledgeBases.delete.deleteWarning')}</p>
              <p className="text-gray-600">{t('knowledgeBases.delete.confirmDelete')}</p>
            </div>
          ) : (
            <p className="text-gray-600 text-lg leading-relaxed">
              {t('knowledgeBases.delete.confirmMessage')}
              {selectedKnowledgeBase?.name && selectedKnowledgeBase.name.length > 30 ? (
                <span title={selectedKnowledgeBase.name} className="font-medium">
                  「{selectedKnowledgeBase.name.substring(0, 30)}...」
                </span>
              ) : (
                <span className="font-medium">「{selectedKnowledgeBase?.name}」</span>
              )}
              {t('knowledgeBases.delete.cannotUndo')}
            </p>
          )
        }
        confirmButtonText={t('common.buttons.delete')}
        cancelButtonText={t('common.cancel')}
        onConfirm={confirmDelete}
        onClose={() => {
          if (!isDeleting) {
            setShowDeleteDialog(false)
            setSelectedKnowledgeBase(null)
            setReferencingAgents([])
          }
        }}
        isLoading={isDeleting}
        itemType="knowledgeBase"
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default KnowledgeBasePageNew
