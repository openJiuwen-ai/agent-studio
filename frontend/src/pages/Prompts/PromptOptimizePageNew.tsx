import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Plus, RotateCw } from 'lucide-react'
import { useOptimizationJobList, useDeleteOptimizationJob, useRefreshOptimizationJobList, type JobDetail } from '@test-agentstudio/api-client'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import Empty from '@/components/Common/Empty'
import { CommonPageLayout, SearchInput } from '@/components/Common/common-page'
import { useOptimizedSearch } from '@/hooks/useSearchOptimization'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import { PromptOptimizeTableView, type PromptOptimizationRow } from './components/PromptOptimizeTableView'

const PAGE_SIZE_OPTIONS = [20, 60, 100, 200]
const DEFAULT_PAGE_SIZE = 20

const PromptOptimizePageNew: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const userId = user?.id || ENV_CONFIG.DEFAULT_USER_ID
  const { snackbar, showSnackbar, closeSnackbar } = useUnifiedSnackbar()

  const [refreshing, setRefreshing] = useState(false)
  const [allPrompts, setAllPrompts] = useState<PromptOptimizationRow[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [statusFilter, setStatusFilter] = useState<PromptOptimizationRow['status'] | 'all'>('all')
  const [deleteDialog, setDeleteDialog] = useState({
    open: false,
    jobId: '',
    jobName: '',
    jobType: 'formal' as 'formal' | 'draft',
  })

  const { searchTerm, debouncedSearchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd } = useOptimizedSearch(
    undefined,
    { debounceDelay: 300, minChars: 0, immediateOnEmpty: false, respectComposition: true },
  )

  const { data: jobListData, isLoading, refetch: refetchJobList } = useOptimizationJobList(['*'], workspaceId, userId)
  const refreshJobListMutation = useRefreshOptimizationJobList()
  const deleteJobMutation = useDeleteOptimizationJob()

  const convertStatus = useCallback((status: JobDetail['status'], jobType: string): PromptOptimizationRow['status'] => {
    if (jobType === 'draft') return 'draft'
    switch (status) {
      case 'running':
        return 'optimizing'
      case 'finished':
        return 'completed'
      case 'failed':
      case 'stopped':
        return 'failed'
      case 'stopping':
        return 'stopping'
      default:
        return 'pending'
    }
  }, [])

  const formatDuration = useCallback(
    (seconds: number): string => {
      if (seconds < 60) return t('prompts.optimizePage.duration.seconds', { seconds })
      if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60)
        const remainingSeconds = seconds % 60
        return remainingSeconds > 0
          ? t('prompts.optimizePage.duration.minutesAndSeconds', { minutes, seconds: remainingSeconds })
          : t('prompts.optimizePage.duration.minutes', { minutes })
      }
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return minutes > 0 ? t('prompts.optimizePage.duration.hoursAndMinutes', { hours, minutes }) : t('prompts.optimizePage.duration.hours', { hours })
    },
    [t],
  )

  useEffect(() => {
    if (jobListData?.code === 200) {
      const converted: PromptOptimizationRow[] = jobListData.job_details.data.map(job => ({
        id: job.job_info.id,
        name: job.job_info.name,
        status: convertStatus(job.status, (job.job_info as any).job_type || 'formal'),
        optimizationRounds: job.job_info.num_iter,
        progress: Math.round(job.progress_rate * 100),
        createdAt: job.job_info.created_at,
        duration: job.status === 'queued' ? '-' : formatDuration(job.time_cost),
        description: job.job_info.desc ?? '',
        errorMsg: job.error_msg,
        jobType: (job.job_info as any).job_type || 'formal',
      }))
      setAllPrompts(converted)
    }
  }, [jobListData, convertStatus, formatDuration])

  const getStatusDisplayName = useCallback(
    (status: PromptOptimizationRow['status']): string => {
      const key = `prompts.optimizePage.status.${status}` as const
      return t(key)
    },
    [t],
  )

  const hasFilters = !!(debouncedSearchTerm.trim() || statusFilter !== 'all')
  const filteredPrompts = useMemo(() => {
    let list = allPrompts
    if (statusFilter !== 'all') list = list.filter(p => p.status === statusFilter)
    if (debouncedSearchTerm.trim()) {
      const term = debouncedSearchTerm.toLowerCase()
      list = list.filter(
        p =>
          p.name.toLowerCase().includes(term) ||
          (p.description ?? '').toLowerCase().includes(term) ||
          getStatusDisplayName(p.status).toLowerCase().includes(term),
      )
    }
    return list
  }, [allPrompts, statusFilter, debouncedSearchTerm, getStatusDisplayName])

  const totalFiltered = filteredPrompts.length
  const currentPageData = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return filteredPrompts.slice(start, start + pageSize)
  }, [filteredPrompts, currentPage, pageSize])

  useEffect(() => {
    setCurrentPage(1)
  }, [debouncedSearchTerm, statusFilter])

  const handleClearFilters = useCallback(() => {
    setSearchTerm('')
    setStatusFilter('all')
    setCurrentPage(1)
  }, [setSearchTerm])

  const handleView = useCallback(
    (prompt: PromptOptimizationRow) => {
      if (prompt.jobType === 'draft') {
        navigate(`/dashboard/prompts/optimize/${prompt.id}?mode=edit&type=draft`)
      } else {
        navigate(`/dashboard/prompts/optimize/${prompt.id}?mode=edit`)
      }
    },
    [navigate],
  )

  const handleDelete = useCallback((prompt: PromptOptimizationRow) => {
    setDeleteDialog({
      open: true,
      jobId: prompt.id,
      jobName: prompt.name,
      jobType: prompt.jobType ?? 'formal',
    })
  }, [])

  const handleConfirmDelete = useCallback(async () => {
    const { jobId, jobType } = deleteDialog
    setDeleteDialog(d => ({ ...d, open: false }))
    try {
      await deleteJobMutation.mutateAsync({ jobId, workspaceId, userId, jobType })
      showSnackbar(t('prompts.optimizePage.messages.deleteSuccess'), 'success')
      refetchJobList()
      const newTotal = Math.max(0, totalFiltered - 1)
      const newPages = Math.ceil(newTotal / pageSize) || 1
      if (currentPage > newPages) setCurrentPage(newPages)
    } catch (e) {
      console.error(e)
      showSnackbar(t('prompts.optimizePage.messages.deleteFailed'), 'error')
    }
  }, [deleteDialog, deleteJobMutation, workspaceId, userId, showSnackbar, t, refetchJobList, totalFiltered, pageSize, currentPage])

  const handleCreateNew = useCallback(() => navigate('/dashboard/prompts/optimize/new'), [navigate])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await refreshJobListMutation.mutateAsync({ idList: ['*'], workspaceId, userId })
    } catch (e) {
      showSnackbar(t('prompts.optimizePage.messages.refreshFailed'), 'error')
    } finally {
      setRefreshing(false)
    }
  }, [refreshJobListMutation, workspaceId, userId, showSnackbar, t])

  useEffect(() => {
    const timer = setInterval(() => refetchJobList(), 300000)
    return () => clearInterval(timer)
  }, [refetchJobList])

  useEffect(() => {
    const q = new URLSearchParams(location.search)
    if (q.get('refresh') === 'true') {
      navigate('/dashboard/prompts/optimize', { replace: true })
      handleRefresh()
    }
  }, [location.search, navigate, handleRefresh])

  const effectiveLoading = isLoading || refreshing

  const getEmptyStateMessage = useCallback(() => {
    if (debouncedSearchTerm.trim()) {
      return {
        title: t('prompts.optimizePage.emptyStates.noMatch.title'),
        description: t('prompts.optimizePage.emptyStates.noMatch.description', { searchTerm: debouncedSearchTerm }),
      }
    }
    switch (statusFilter) {
      case 'optimizing':
        return { title: t('prompts.optimizePage.emptyStates.noOptimizing.title'), description: t('prompts.optimizePage.emptyStates.noOptimizing.description') }
      case 'completed':
        return { title: t('prompts.optimizePage.emptyStates.noCompleted.title'), description: t('prompts.optimizePage.emptyStates.noCompleted.description') }
      case 'failed':
        return { title: t('prompts.optimizePage.emptyStates.noFailed.title'), description: t('prompts.optimizePage.emptyStates.noFailed.description') }
      case 'draft':
        return { title: t('prompts.optimizePage.emptyStates.noDraft.title'), description: t('prompts.optimizePage.emptyStates.noDraft.description') }
      default:
        return { title: t('prompts.optimizePage.emptyStates.noTasks.title'), description: t('prompts.optimizePage.emptyStates.noTasks.description') }
    }
  }, [debouncedSearchTerm, statusFilter, t])

  const emptyState = useMemo(() => {
    if (currentPageData.length > 0) return undefined
    const hasAnyFilter = !!debouncedSearchTerm.trim() || statusFilter !== 'all'
    const { title, description } = getEmptyStateMessage()
    return (
      <Empty
        searchTerm={debouncedSearchTerm}
        type="promptOptimize"
        hasFilters={hasAnyFilter}
        onCreateClick={hasAnyFilter ? undefined : handleCreateNew}
        customTitle={title}
        customDescription={description}
      />
    )
  }, [currentPageData.length, debouncedSearchTerm, statusFilter, handleCreateNew, getEmptyStateMessage])

  const toolbarLeft = useMemo(
    () => (
      <div className="flex items-center gap-3">
        <SearchInput
          searchTerm={searchTerm}
          placeholder={t('prompts.optimizePage.searchPlaceholder')}
          onChange={setSearchTerm}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value as PromptOptimizationRow['status'] | 'all')}
          className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6]"
        >
          <option value="all">{t('prompts.optimizePage.filters.allStatuses')}</option>
          <option value="optimizing">{t('prompts.optimizePage.status.optimizing')}</option>
          <option value="completed">{t('prompts.optimizePage.status.completed')}</option>
          <option value="failed">{t('prompts.optimizePage.status.failed')}</option>
          <option value="stopping">{t('prompts.optimizePage.status.stopping')}</option>
          <option value="draft">{t('prompts.optimizePage.status.draft')}</option>
        </select>
        {hasFilters && (
          <button
            type="button"
            onClick={handleClearFilters}
            className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] hover:border-[#d1d5db]"
          >
            {t('prompts.optimizePage.clearFilters')}
          </button>
        )}
      </div>
    ),
    [searchTerm, setSearchTerm, handleCompositionStart, handleCompositionEnd, statusFilter, hasFilters, handleClearFilters, t],
  )

  const toolbarRight = useMemo(
    () => (
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] disabled:opacity-50 flex items-center gap-2"
          title={refreshing ? t('prompts.optimizePage.refreshing') : t('prompts.optimizePage.refresh')}
        >
          <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{t('prompts.optimizePage.refresh')}</span>
        </button>
        <button
          type="button"
          onClick={handleCreateNew}
          className="btn-primary h-8 flex items-center gap-2 text-sm px-4"
        >
          <Plus className="w-4 h-4" />
          <span>{t('prompts.optimizePage.createTask')}</span>
        </button>
      </div>
    ),
    [handleRefresh, refreshing, handleCreateNew, t],
  )

  const tableView = useMemo(
    () => (
      <PromptOptimizeTableView
        prompts={currentPageData}
        loading={effectiveLoading}
        emptyState={emptyState}
        onView={handleView}
        onDelete={handleDelete}
        getStatusLabel={getStatusDisplayName}
      />
    ),
    [currentPageData, effectiveLoading, emptyState, handleView, handleDelete, getStatusDisplayName],
  )

  return (
    <>
      <CommonPageLayout
        title={t('prompts.optimizePage.title')}
        viewType="table"
        showViewToggle={false}
        tableView={tableView}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
        pager={{
          total: totalFiltered,
          currentPage,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
        }}
        onPagerChange={(page, size) => {
          if (size !== pageSize) setPageSize(size)
          setCurrentPage(page)
        }}
        loading={effectiveLoading}
        error={null}
      />
      <DeleteConfirmationDialog
        isOpen={deleteDialog.open}
        title={deleteDialog.jobType === 'draft' ? t('prompts.optimizePage.deleteDialog.deleteDraftTitle') : t('prompts.optimizePage.deleteDialog.deleteTaskTitle')}
        message={
          deleteDialog.jobType === 'draft'
            ? t('prompts.optimizePage.deleteDialog.deleteDraftMessage', { name: deleteDialog.jobName })
            : t('prompts.optimizePage.deleteDialog.deleteTaskMessage', { name: deleteDialog.jobName })
        }
        confirmButtonText={t('prompts.optimizePage.deleteDialog.confirm')}
        cancelButtonText={t('prompts.optimizePage.deleteDialog.cancel')}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeleteDialog(d => ({ ...d, open: false }))}
        isLoading={deleteJobMutation.isLoading}
      />
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default PromptOptimizePageNew
