import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Trash2, Eye, Plus, RotateCw, CheckCircle, Clock, AlertCircle, Pause, RefreshCw, BarChart3, Search, Edit } from 'lucide-react'
import {
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Box,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
} from '@mui/material'
import { useOptimizationJobList, useDeleteOptimizationJob, useRefreshOptimizationJobList, type JobDetail } from '@test-agentstudio/api-client'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import ConditionalTooltip from '@/components/Prompts/ConditionalTooltip'
import { Pagination } from '@/components/Common/common-table'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'

// 定义提示词优化记录的类型
interface PromptOptimization {
  id: string
  name: string
  status: 'pending' | 'optimizing' | 'completed' | 'failed' | 'stopping' | 'draft'
  optimizationRounds: number
  progress: number // 0-100
  createdAt: string
  duration: string // 任务耗时
  description: string
  errorMsg?: string // 错误信息
  jobType?: 'formal' | 'draft' // 任务类型
}

const PromptOptimizePage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // 获取用户信息
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const userId = user?.id || ENV_CONFIG.DEFAULT_USER_ID
  const [statistics, setStatistics] = useState({
    total: 0,
    optimizing: 0,
    completed: 0,
    failed: 0,
    draft: 0,
  })
  const { snackbar, showSnackbar, closeSnackbar } = useUnifiedSnackbar()
  const [deleteDialog, setDeleteDialog] = useState({
    open: false,
    jobId: '',
    jobName: '',
    jobType: 'formal' as 'formal' | 'draft',
  })

  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [allPrompts, setAllPrompts] = useState<PromptOptimization[]>([]) // 存储所有数据

  // 搜索相关状态
  const [searchTerm, setSearchTerm] = useState('')

  // 状态筛选相关状态
  const [statusFilter, setStatusFilter] = useState<PromptOptimization['status'] | 'all'>('all')

  // 处理状态筛选
  const handleStatusFilter = (status: PromptOptimization['status'] | 'all') => {
    setStatusFilter(status)
    setCurrentPage(1)
  }

  // 获取空状态提示信息
  const getEmptyStateMessage = () => {
    if (searchTerm) {
      return {
        title: t('prompts.optimizePage.emptyStates.noMatch.title'),
        description: t('prompts.optimizePage.emptyStates.noMatch.description', { searchTerm }),
      }
    }

    switch (statusFilter) {
      case 'optimizing':
        return {
          title: t('prompts.optimizePage.emptyStates.noOptimizing.title'),
          description: t('prompts.optimizePage.emptyStates.noOptimizing.description'),
        }
      case 'completed':
        return {
          title: t('prompts.optimizePage.emptyStates.noCompleted.title'),
          description: t('prompts.optimizePage.emptyStates.noCompleted.description'),
        }
      case 'failed':
        return {
          title: t('prompts.optimizePage.emptyStates.noFailed.title'),
          description: t('prompts.optimizePage.emptyStates.noFailed.description'),
        }
      case 'draft':
        return {
          title: t('prompts.optimizePage.emptyStates.noDraft.title'),
          description: t('prompts.optimizePage.emptyStates.noDraft.description'),
        }
      default:
        return {
          title: t('prompts.optimizePage.emptyStates.noTasks.title'),
          description: t('prompts.optimizePage.emptyStates.noTasks.description'),
        }
    }
  }

  // 搜索过滤函数
  const getStatusDisplayName = (status: PromptOptimization['status']): string => {
    switch (status) {
      case 'completed':
        return t('prompts.optimizePage.status.completed')
      case 'optimizing':
        return t('prompts.optimizePage.status.optimizing')
      case 'pending':
        return t('prompts.optimizePage.status.pending')
      case 'failed':
        return t('prompts.optimizePage.status.failed')
      case 'stopping':
        return t('prompts.optimizePage.status.stopping')
      case 'draft':
        return t('prompts.optimizePage.status.draft')
      default:
        return ''
    }
  }

  // 过滤搜索结果
  const filteredPrompts = React.useMemo(() => {
    let filtered = allPrompts

    // 状态筛选
    if (statusFilter !== 'all') {
      filtered = filtered.filter(prompt => prompt.status === statusFilter)
    }

    // 搜索筛选
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        prompt =>
          prompt.name.toLowerCase().includes(term) ||
          prompt.description.toLowerCase().includes(term) ||
          getStatusDisplayName(prompt.status).toLowerCase().includes(term),
      )
    }

    return filtered
  }, [allPrompts, searchTerm, statusFilter])

  // 计算当前页显示的数据
  const currentPageData = React.useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize
    const endIndex = startIndex + pageSize
    return filteredPrompts.slice(startIndex, endIndex)
  }, [filteredPrompts, currentPage, pageSize])

  // 处理页码变化
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage)
  }

  // 处理每页大小变化
  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize)
    setCurrentPage(1) // 重置到第一页
  }

  // 搜索词变化时重置页码
  React.useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm])

  // 转换任务状态
  const convertStatus = (status: JobDetail['status'], jobType: string): PromptOptimization['status'] => {
    // 如果是草稿类型，直接返回草稿状态
    if (jobType === 'draft') {
      return 'draft'
    }

    // 正式任务的状态转换
    switch (status) {
      case 'running':
        return 'optimizing'
      case 'finished':
        return 'completed'
      case 'failed':
        return 'failed'
      case 'stopped':
        return 'failed'
      case 'stopping':
        return 'stopping'
      case 'queued':
      case 'deleted':
      default:
        return 'pending'
    }
  }

  // 格式化任务耗时
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
      return t('prompts.optimizePage.duration.seconds', { seconds })
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      return remainingSeconds > 0
        ? t('prompts.optimizePage.duration.minutesAndSeconds', { minutes, seconds: remainingSeconds })
        : t('prompts.optimizePage.duration.minutes', { minutes })
    } else {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return minutes > 0 ? t('prompts.optimizePage.duration.hoursAndMinutes', { hours, minutes }) : t('prompts.optimizePage.duration.hours', { hours })
    }
  }

  // 使用 hooks 获取任务列表
  const { data: jobListData, isLoading, refetch: refetchJobList } = useOptimizationJobList(['*'], workspaceId)
  const refreshJobListMutation = useRefreshOptimizationJobList()
  const deleteJobMutation = useDeleteOptimizationJob()

  // 处理数据转换
  useEffect(() => {
    if (jobListData && jobListData.code === 200) {
      // 转换数据格式
      const convertedData: PromptOptimization[] = jobListData.job_details.data.map(job => ({
        id: job.job_info.id,
        name: job.job_info.name,
        status: convertStatus(job.status, (job.job_info as any).job_type || 'formal'),
        optimizationRounds: job.job_info.num_iter,
        progress: Math.round(job.progress_rate * 100),
        createdAt: job.job_info.created_at,
        duration: job.status === 'queued' ? '-' : formatDuration(job.time_cost),
        description: job.job_info.desc,
        errorMsg: job.error_msg, // 添加错误信息
        jobType: (job.job_info as any).job_type || 'formal', // 添加任务类型
      }))

      setAllPrompts(convertedData)

      // 计算草稿数量
      const draftCount = convertedData.filter(prompt => prompt.jobType === 'draft').length

      // 设置统计数据
      setStatistics({
        total: jobListData.job_details.total_jobs + draftCount, // 总任务数包括草稿
        optimizing: jobListData.job_details.running_jobs,
        completed: jobListData.job_details.finished_jobs,
        failed: jobListData.job_details.failed_jobs,
        draft: draftCount,
      })
    }
  }, [jobListData])

  // 获取任务列表
  const fetchJobList = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
      try {
        await refreshJobListMutation.mutateAsync({ idList: ['*'], workspaceId })
      } catch (error) {
        console.error('刷新任务列表失败:', error)
        showSnackbar(t('prompts.optimizePage.messages.refreshFailed'), 'error')
      } finally {
        setRefreshing(false)
      }
    } else {
      // 初始加载，直接使用 refetchJobList
      refetchJobList()
    }
  }

  // 页面加载时获取任务列表和设置定时刷新
  useEffect(() => {
    setLoading(isLoading)

    // 设置定时刷新，每5分钟刷新一次
    const timer = setInterval(() => {
      refetchJobList()
    }, 300000) // 5分钟 = 300秒 = 300000毫秒

    return () => clearInterval(timer)
  }, [isLoading, refetchJobList])

  // 获取状态对应的芯片样式
  const getStatusChip = (prompt: PromptOptimization) => {
    const { status, errorMsg } = prompt

    switch (status) {
      case 'completed':
        return <Chip icon={<CheckCircle className="w-4 h-4" />} label={t('prompts.optimizePage.status.completed')} color="success" size="small" />
      case 'optimizing':
        return <Chip icon={<RotateCw className="w-4 h-4 animate-spin" />} label={t('prompts.optimizePage.status.optimizing')} color="primary" size="small" />
      case 'pending':
        return <Chip icon={<Clock className="w-4 h-4" />} label={t('prompts.optimizePage.status.pending')} color="default" size="small" />
      case 'failed':
        // eslint-disable-next-line no-case-declarations
        const failedChip = <Chip icon={<AlertCircle className="w-4 h-4" />} label={t('prompts.optimizePage.status.failed')} color="error" size="small" />
        // 如果有错误信息，添加 Tooltip
        if (errorMsg && errorMsg.trim()) {
          return (
            <Tooltip
              title={
                <Box>
                  <Typography variant="body2" fontWeight="bold" sx={{ mb: 1 }}>
                    {t('prompts.optimizePage.messages.failureReason')}
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', maxWidth: 400 }}>
                    {errorMsg}
                  </Typography>
                </Box>
              }
              placement="top"
              arrow
            >
              {failedChip}
            </Tooltip>
          )
        }
        return failedChip
      case 'stopping':
        return <Chip icon={<Pause className="w-4 h-4" />} label={t('prompts.optimizePage.status.stopping')} color="warning" size="small" />
      case 'draft':
        return <Chip icon={<Edit className="w-4 h-4" />} label={t('prompts.optimizePage.status.draft')} color="info" size="small" />
      default:
        return null
    }
  }

  // 处理查看操作
  const handleView = (prompt: PromptOptimization) => {
    // 根据任务类型直接跳转到编辑页面
    if (prompt.jobType === 'draft') {
      // 草稿类型，跳转到编辑页面并标记为草稿类型
      console.log('查看草稿:', prompt.id)
      navigate(`/dashboard/prompts/optimize/${prompt.id}?mode=edit&type=draft`)
    } else {
      // 正式任务类型，跳转到编辑页面
      console.log('查看优化任务:', prompt.id)
      navigate(`/dashboard/prompts/optimize/${prompt.id}?mode=edit`)
    }
  }
  // 处理删除操作 - 打开确认对话框
  const handleDelete = (id: string) => {
    const prompt = allPrompts.find(p => p.id === id)
    if (prompt) {
      setDeleteDialog({
        open: true,
        jobId: id,
        jobName: prompt.name,
        jobType: prompt.jobType || 'formal',
      })
    }
  }

  // 确认删除任务
  const handleConfirmDelete = async () => {
    const { jobId, jobType } = deleteDialog
    setDeleteDialog({ ...deleteDialog, open: false })

    try {
      await deleteJobMutation.mutateAsync({
        jobId,
        workspaceId,
        jobType,
      })
      showSnackbar(t('prompts.optimizePage.messages.deleteSuccess'), 'success')

      // 如果删除后当前页没有数据，自动跳转到上一页
      const newTotalPages = Math.ceil((allPrompts.length - 1) / pageSize)
      if (currentPage > newTotalPages && newTotalPages > 0) {
        setCurrentPage(newTotalPages)
      }
    } catch (error) {
      console.error('删除任务失败:', error)
      showSnackbar(t('prompts.optimizePage.messages.deleteFailed'), 'error')
    }
  }

  // 关闭删除对话框
  const handleCancelDelete = () => {
    setDeleteDialog({
      open: false,
      jobId: '',
      jobName: '',
      jobType: 'formal',
    })
  }

  // 创建新的优化任务
  const handleCreateNew = () => {
    navigate('/dashboard/prompts/optimize/new')
  }

  // 手动刷新任务列表
  const handleRefresh = () => {
    fetchJobList(true)
  }

  // 监听 URL 参数变化，如果包含 refresh=true 则自动刷新
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search)
    if (searchParams.get('refresh') === 'true') {
      // 清除 URL 参数并刷新数据
      navigate('/dashboard/prompts/optimize', { replace: true })
      handleRefresh()
    }
  }, [location.search, navigate])

  return (
    <div className="space-y-8 p-6" style={{ minHeight: '93vh' }}>
      {/* Page header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 via-blue-800 to-indigo-900 mb-2">
          {t('prompts.optimizePage.title')}
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">{t('prompts.optimizePage.subtitle')}</p>
      </div>

      {/* Search and action buttons */}
      <div className="flex items-center gap-4 mb-6">
        {/* Search */}
        <div className="flex-1">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors duration-200" />
            <input
              type="text"
              placeholder={t('prompts.optimizePage.searchPlaceholder')}
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 transition-all duration-200 bg-gray-50 focus:bg-white"
            />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center w-10 h-10 border border-gray-200 rounded-xl bg-gray-50 hover:bg-gray-100 text-gray-600 hover:text-gray-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            title={refreshing ? t('prompts.optimizePage.refreshing') : t('prompts.optimizePage.refresh')}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleCreateNew}
            className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
          >
            <Plus className="w-5 h-5" />
            <span>{t('prompts.optimizePage.createTask')}</span>
          </button>
        </div>
      </div>

      {/* 统计指标卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <div
          className={`bg-gradient-to-br from-gray-50 to-blue-50 border rounded-xl p-6 text-center shadow-sm hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer ${
            statusFilter === 'all' ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-200'
          }`}
          onClick={() => handleStatusFilter('all')}
        >
          <div className="w-12 h-12 bg-gradient-to-r from-gray-600 to-gray-800 rounded-xl flex items-center justify-center mx-auto mb-3">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div className="text-3xl font-bold text-gray-900 mb-1">{statistics.total}</div>
          <div className="text-gray-600 font-medium">{t('prompts.optimizePage.totalTasks')}</div>
        </div>

        <div
          className={`bg-gradient-to-br from-blue-50 to-indigo-50 border rounded-xl p-6 text-center shadow-sm hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer ${
            statusFilter === 'optimizing' ? 'border-blue-400 ring-2 ring-blue-200' : 'border-blue-200'
          }`}
          onClick={() => handleStatusFilter('optimizing')}
        >
          <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <RefreshCw className="w-6 h-6 text-white" />
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-1">{statistics.optimizing}</div>
          <div className="text-gray-600 font-medium">{t('prompts.optimizePage.optimizing')}</div>
        </div>

        <div
          className={`bg-gradient-to-br from-green-50 to-emerald-50 border rounded-xl p-6 text-center shadow-sm hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer ${
            statusFilter === 'completed' ? 'border-green-400 ring-2 ring-green-200' : 'border-green-200'
          }`}
          onClick={() => handleStatusFilter('completed')}
        >
          <div className="w-12 h-12 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <CheckCircle className="w-6 h-6 text-white" />
          </div>
          <div className="text-3xl font-bold text-green-600 mb-1">{statistics.completed}</div>
          <div className="text-gray-600 font-medium">{t('prompts.optimizePage.completed')}</div>
        </div>

        <div
          className={`bg-gradient-to-br from-red-50 to-pink-50 border rounded-xl p-6 text-center shadow-sm hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer ${
            statusFilter === 'failed' ? 'border-red-400 ring-2 ring-red-200' : 'border-red-200'
          }`}
          onClick={() => handleStatusFilter('failed')}
        >
          <div className="w-12 h-12 bg-gradient-to-r from-red-600 to-pink-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <AlertCircle className="w-6 h-6 text-white" />
          </div>
          <div className="text-3xl font-bold text-red-600 mb-1">{statistics.failed}</div>
          <div className="text-gray-600 font-medium">{t('prompts.optimizePage.failed')}</div>
        </div>

        <div
          className={`bg-gradient-to-br from-purple-50 to-indigo-50 border rounded-xl p-6 text-center shadow-sm hover:shadow-xl transition-all duration-300 transform hover:scale-105 cursor-pointer ${
            statusFilter === 'draft' ? 'border-purple-400 ring-2 ring-purple-200' : 'border-purple-200'
          }`}
          onClick={() => handleStatusFilter('draft')}
        >
          <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Edit className="w-6 h-6 text-white" />
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-1">{statistics.draft}</div>
          <div className="text-gray-600 font-medium">{t('prompts.optimizePage.draft')}</div>
        </div>
      </div>

      {/* 提示词列表表格 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center mr-3">
              <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
            </div>
            <span className="text-lg text-gray-600 font-medium">{t('prompts.optimizePage.loading')}</span>
          </div>
        ) : filteredPrompts.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gradient-to-r from-blue-100 to-indigo-200 rounded-full flex items-center justify-center mx-auto mb-6">
              {searchTerm ? <Search className="w-12 h-12 text-blue-400" /> : <AlertCircle className="w-12 h-12 text-blue-400" />}
            </div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">{getEmptyStateMessage().title}</h3>
            <p className="text-gray-500 mb-6">{getEmptyStateMessage().description}</p>
            {!searchTerm && statusFilter === 'all' && (
              <button
                onClick={handleCreateNew}
                className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-xl"
              >
                <Plus className="w-5 h-5" />
                <span>{t('prompts.optimizePage.newTask')}</span>
              </button>
            )}
          </div>
        ) : (
          <div>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow className="bg-gradient-to-r from-blue-100 to-indigo-100">
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.taskName')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.status')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.rounds')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.createdAt')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.duration')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.description')}</strong>
                    </TableCell>
                    <TableCell className="text-blue-900 font-semibold">
                      <strong>{t('prompts.optimizePage.table.actions')}</strong>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {currentPageData.map(prompt => (
                    <TableRow
                      key={prompt.id}
                      hover
                      className="cursor-pointer"
                      onClick={e => {
                        // 如果点击的是按钮区域，不触发行点击
                        const target = e.target as HTMLElement
                        if (target.closest('button') || target.closest('[role="button"]')) {
                          return
                        }
                        handleView(prompt)
                      }}
                    >
                      <TableCell className="font-medium">
                        <ConditionalTooltip title={prompt.name}>
                          <div className="truncate max-w-xs">{prompt.name}</div>
                        </ConditionalTooltip>
                      </TableCell>
                      <TableCell>
                        <Box className="flex items-center">
                          {getStatusChip(prompt)}
                          <Box className="flex items-center ml-3">
                            <LinearProgress
                              variant="determinate"
                              value={prompt.progress}
                              sx={{
                                width: '80px',
                                height: 6,
                                borderRadius: 3,
                                backgroundColor: 'rgba(0, 0, 0, 0.08)',
                                '& .MuiLinearProgress-bar': {
                                  borderRadius: 3,
                                  backgroundColor:
                                    prompt.status === 'completed'
                                      ? '#4caf50'
                                      : prompt.status === 'failed'
                                        ? '#f44336'
                                        : prompt.status === 'stopping'
                                          ? '#ff9800'
                                          : prompt.status === 'draft'
                                            ? '#9c27b0'
                                            : '#2196f3',
                                },
                              }}
                            />
                            <Typography variant="caption" className="text-gray-500 ml-2">
                              {prompt.progress}%
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box className="flex items-center">
                          <span className="mr-2">{prompt.optimizationRounds}</span>
                          {prompt.optimizationRounds > 0 && <span className="text-gray-500 text-sm">{t('prompts.optimizePage.table.round')}</span>}
                        </Box>
                      </TableCell>
                      <TableCell className="text-gray-600">{prompt.createdAt}</TableCell>
                      <TableCell className="text-gray-600">{prompt.duration}</TableCell>
                      <TableCell className="text-gray-600">
                        <ConditionalTooltip title={prompt.description}>
                          <div className="max-w-xs truncate">{prompt.description}</div>
                        </ConditionalTooltip>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-start space-x-1">
                          <Tooltip title={t('prompts.optimizePage.actions.view')}>
                            <IconButton size="small" onClick={() => handleView(prompt)} className="text-gray-400 hover:text-blue-600">
                              <Eye className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={t('prompts.optimizePage.actions.delete')}>
                            <IconButton size="small" onClick={() => handleDelete(prompt.id)} className="text-gray-400 hover:text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </IconButton>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </div>
        )}
      </div>

      {/* 分页组件 - 右下角 */}
      <Pagination
        pager={{
          total: filteredPrompts.length,
          currentPage: currentPage,
          pageSize: pageSize,
          pageSizeOptions: [10, 20, 30, 40, 50],
        }}
        loading={loading}
        onPagerChange={(page, pageSize) => {
          handlePageChange(page)
          handlePageSizeChange(pageSize)
        }}
      />

      {/* Snackbar提示 */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} anchorOrigin={{ vertical: 'top', horizontal: 'center' }} />

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialog.open} onClose={handleCancelDelete} aria-labelledby="delete-dialog-title" aria-describedby="delete-dialog-description">
        <DialogTitle id="delete-dialog-title">
          {deleteDialog.jobType === 'draft' ? t('prompts.optimizePage.deleteDialog.deleteDraftTitle') : t('prompts.optimizePage.deleteDialog.deleteTaskTitle')}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            {deleteDialog.jobType === 'draft'
              ? t('prompts.optimizePage.deleteDialog.deleteDraftMessage', { name: deleteDialog.jobName })
              : t('prompts.optimizePage.deleteDialog.deleteTaskMessage', { name: deleteDialog.jobName })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDelete} color="primary">
            {t('prompts.optimizePage.deleteDialog.cancel')}
          </Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            {t('prompts.optimizePage.deleteDialog.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}

export default PromptOptimizePage
