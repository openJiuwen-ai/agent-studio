import React, { useState, useMemo, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts'
import * as XLSX from 'xlsx'
import {
  ArrowLeft,
  Play,
  Settings,
  FileText,
  BarChart,
  Target,
  Brain,
  CheckCircle,
  Upload,
  Plus,
  Trash2,
  Edit,
  Zap,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronsLeft,
  ChevronsRight,
  Copy,
  Info,
  TrendingUp,
  GitCompare,
  Check,
  X,
  Download,
  Trash,
  Maximize2,
  Minimize2,
  Code,
} from 'lucide-react'
import {
  Typography,
  Button,
  Paper,
  TextField,
  Box,
  Select,
  MenuItem,
  Slider,
  FormControlLabel,
  Divider,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Autocomplete,
  CircularProgress,
  Tabs,
  Tab,
  RadioGroup,
  Radio,
  Drawer,
  Tooltip,
} from '@mui/material'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQueryClient } from 'react-query'
import { useAuthStore } from '@/stores/useAuthStore'
import { useIsNewDashboard } from '@/hooks/useIsNewDashboard'
import { ENV_CONFIG } from '@/config/environment'
import {
  useOptimizationJobDetail,
  useCreateOptimizationJob,
  useSaveJobDraft,
  useJobDraftDetail,
  useDeleteOptimizationJob,
  useJobHistory,
  PromptModelService,
  PromptService,
  type Prompt,
  type PromptModel,
  type OptimizationCase,
  type EvaluateCase,
  type GetJobHistoryResponse,
} from '@test-agentstudio/api-client'
import { Tool } from '@/types/promptType'
import DiffViewer from '@/components/Prompts/DiffViewer'
import FieldEditor, { type FieldType } from '@/components/Prompts/FieldEditor'
import ConditionalTooltip from '@/components/Prompts/ConditionalTooltip'
import { FormattedPromptEditor, ModelSelector, ModelParameterEditor } from '@/components/Prompts'
import ToolSettingsPanel from '@/components/Prompts/ToolSettingsPanel'
import ToolEditDialog, { type EditingTool } from '@/components/Prompts/ToolEditDialog'
import { SliderField } from '@/components/Prompts/SliderField'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import EvaluationDetailDialog from '@/components/Prompts/EvaluationDetailDialog'
import { copyToClipboard } from '@/utils/prompts/utils'
import { convertApiToolsToFrontendTools, convertFrontendToolsToApiTools } from '@/utils/prompts/toolFormatConverter'

interface TestCase {
  id: number
  messages: string
}

interface TestCaseDetail {
  id: number
  role: 'inputs' | 'label'
  content: string
  variableName?: string
  contentType?: FieldType
}

// 用例数量限制常量
const MAX_TEST_CASES = 300

const PromptOptimizeEditPage: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const isEditMode = searchParams.get('mode') === 'edit'
  const isNewDashboard = useIsNewDashboard()

  // 基本信息状态
  const { user } = useAuthStore()
  const workspaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  const userId = user?.id || ENV_CONFIG.DEFAULT_USER_ID
  const queryClient = useQueryClient()

  // 检查是否是草稿类型
  const urlParams = new URLSearchParams(window.location.search)
  const isDraftType = urlParams.get('type') === 'draft'

  // 根据任务类型调用不同的详情查询接口
  const {
    data: formalJobDetailData,
    isLoading: formalJobDetailLoading,
    error: formalJobDetailError,
  } = useOptimizationJobDetail(id && isEditMode && !isDraftType ? id : undefined, workspaceId, userId)

  const {
    data: draftDetailData,
    isLoading: draftDetailLoading,
    refetch: refetchDraftDetail,
    error: draftDetailError,
  } = useJobDraftDetail(id && isEditMode && isDraftType ? parseInt(id) : undefined, workspaceId, userId)

  // 统一的数据和加载状态
  const jobDetailData = isDraftType ? draftDetailData : formalJobDetailData
  const jobDetailError = isDraftType ? draftDetailError : formalJobDetailError
  const createOptimizationJobMutation = useCreateOptimizationJob()
  const saveJobDraftMutation = useSaveJobDraft()
  const deleteJobMutation = useDeleteOptimizationJob()

  // 详情对话框相关状态（需要在useJobHistory之前定义）
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [detailDialogType, setDetailDialogType] = useState<'original' | 'optimized'>('original')
  const [detailDialogIterationRound, setDetailDialogIterationRound] = useState(0)
  const [detailDialogPageNum, setDetailDialogPageNum] = useState(1)
  const [detailDialogPageSize, setDetailDialogPageSize] = useState(10)
  const [evaluateCases, setEvaluateCases] = useState<EvaluateCase[]>([])

  // 获取用例历史记录
  const {
    data: jobHistoryData,
    isLoading: jobHistoryLoading,
    refetch: refetchJobHistory,
  } = useJobHistory(
    detailDialogOpen && id ? id : undefined,
    detailDialogOpen ? workspaceId : undefined,
    detailDialogOpen ? userId : undefined,
    detailDialogOpen ? detailDialogPageNum : undefined,
    detailDialogOpen ? detailDialogPageSize : undefined,
    detailDialogOpen ? detailDialogIterationRound : undefined,
  )
  const [taskName, setTaskName] = useState('')
  const [description, setDescription] = useState('')
  const [originalPrompt, setOriginalPrompt] = useState('') // 基本信息中可编辑的原始提示词
  const [historicalOriginalPrompt, setHistoricalOriginalPrompt] = useState('') // 从接口获取的历史原始提示词，用于对比
  const [fromEditor, setFromEditor] = useState(false)
  const [editorPromptId, setEditorPromptId] = useState<string | null>(null)
  const [optimizationConfigTab, setOptimizationConfigTab] = useState(0) // 优化配置Tab选中状态

  // 提示词选择相关状态
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null)
  const [promptList, setPromptList] = useState<Prompt[]>([])
  const [rawPromptList, setRawPromptList] = useState<any[]>([]) // 保存原始API数据
  const [promptListLoading, setPromptListLoading] = useState(false)

  // 优化配置状态
  const [maxRounds, setMaxRounds] = useState(5)
  const [llmParallel, setLlmParallel] = useState(1)
  const [exampleCount, setExampleCount] = useState(0)
  const [evaluationMetrics, setEvaluationMetrics] = useState<string[]>([])
  const [evaluationCriteria, setEvaluationCriteria] = useState('')
  const [targetAccuracy, setTargetAccuracy] = useState(90) // 目标准确率
  const [evaluationType, setEvaluationType] = useState('objective') // 评价类型：objective/subjective
  const [backgroundKnowledge, setBackgroundKnowledge] = useState('') // 背景知识

  // 模型相关状态
  const [models, setModels] = useState<PromptModel[]>([])
  const [selectedOptimizeModel, setSelectedOptimizeModel] = useState<PromptModel | null>(null)
  const [selectedRunModel, setSelectedRunModel] = useState<PromptModel | null>(null)
  const [optimizeModelParams, setOptimizeModelParams] = useState<Record<string, any>>({})
  const [runModelParams, setRunModelParams] = useState<Record<string, any>>({})
  const [modelsLoading, setModelsLoading] = useState(false)

  // 工具相关状态
  const [tools, setTools] = useState<Tool[]>([])
  const [toolsEnabled, setToolsEnabled] = useState(false)

  // 工具编辑对话框状态
  const [toolEditDialogOpen, setToolEditDialogOpen] = useState(false)
  const [editingTool, setEditingTool] = useState<EditingTool | null>(null)

  // 用例集状态
  const [testCases, setTestCases] = useState<TestCase[]>([])

  // 用例集分页状态
  const [testCasePage, setTestCasePage] = useState(0)
  const [testCaseRowsPerPage, setTestCaseRowsPerPage] = useState(5)
  const [currentPageInput, setCurrentPageInput] = useState('1')

  // 计算分页信息
  const totalPages = Math.max(1, Math.ceil(testCases.length / testCaseRowsPerPage))
  const currentPage = testCasePage + 1 // 转换为1开始的页码

  // 当用例数量变化时，如果当前页超出范围，重置到第一页
  useEffect(() => {
    if (testCases.length > 0 && testCasePage * testCaseRowsPerPage >= testCases.length) {
      setTestCasePage(0)
    }
  }, [testCases.length, testCaseRowsPerPage])

  // 同步页码输入框
  useEffect(() => {
    setCurrentPageInput(currentPage.toString())
  }, [currentPage])

  // 分页处理函数
  const handleFirstPage = () => setTestCasePage(0)
  const handlePrevPage = () => setTestCasePage(prev => Math.max(0, prev - 1))
  const handleNextPage = () => setTestCasePage(prev => Math.min(totalPages - 1, prev + 1))
  const handleLastPage = () => setTestCasePage(totalPages - 1)

  // Snackbar状态
  const { snackbar, showSnackbar, closeSnackbar, setSnackbar } = useUnifiedSnackbar()
  const { t } = useTranslation()

  // 最优轮数状态
  const [bestIteration, setBestIteration] = useState<number>(-1)

  // 任务状态
  const [taskStatus, setTaskStatus] = useState<string>('') // running, finished, failed, deleted, stopped, stopping, queued
  const [errorMsg, setErrorMsg] = useState<string>('') // 错误信息

  // Excel上传相关状态
  const [uploadConfirmOpen, setUploadConfirmOpen] = useState(false)
  const [pendingExcelData, setPendingExcelData] = useState<TestCase[]>([])
  const [uploadMode, setUploadMode] = useState<'append' | 'replace'>('replace')

  // 优化结果状态（只读展示）
  const [optimizedPrompt, setOptimizedPrompt] = useState('')
  const [optimizationHistory, setOptimizationHistory] = useState<any[]>([])
  const [currentOptimizedVersion, setCurrentOptimizedVersion] = useState(0)
  const [optimizedVersions, setOptimizedVersions] = useState<string[]>([])
  const [isCreatingJob, setIsCreatingJob] = useState(false)
  const [isSavingDraft, setIsSavingDraft] = useState(false)
  const [draftId, setDraftId] = useState<number | undefined>(undefined)
  const [autoSaveTimeout, setAutoSaveTimeout] = useState<NodeJS.Timeout | null>(null)
  const [lastSavedTime, setLastSavedTime] = useState<Date | null>(null)

  // 响应式高度状态
  const [contentHeight, setContentHeight] = useState<string>('80vh')

  // 页码编辑处理
  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    if (value === '' || /^\d+$/.test(value)) {
      setCurrentPageInput(value)
    }
  }

  const handlePageInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const pageNum = parseInt(currentPageInput, 10)
      if (pageNum >= 1 && pageNum <= totalPages) {
        setTestCasePage(pageNum - 1)
      } else {
        setCurrentPageInput(currentPage.toString())
      }
    }
  }

  const handlePageInputBlur = () => {
    const pageNum = parseInt(currentPageInput, 10)
    if (pageNum >= 1 && pageNum <= totalPages) {
      setTestCasePage(pageNum - 1)
    } else {
      setCurrentPageInput(currentPage.toString())
    }
  }

  // 对话框状态
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [currentTestCase, setCurrentTestCase] = useState<TestCase | null>(null)
  const [isViewMode, setIsViewMode] = useState(false) // 新增：是否为查看模式
  const [testCaseDetails, setTestCaseDetails] = useState<TestCaseDetail[]>([
    {
      id: 1,
      role: 'inputs',
      content:
        '高祖二十二子：窦皇后生建成（李建成）、太宗皇帝（李世民）、玄霸（李玄霸）、元吉（李元吉），万贵妃生智云（李智云），莫嫔生元景（李元景），孙嫔生元昌（李元昌））',
      variableName: 'query',
      contentType: 'PlainText',
    },
    {
      id: 2,
      role: 'label',
      content: '[李建成, 李世民, 李玄霸, 李元吉, 李智云, 李元景, 李元昌]',
      variableName: 'output',
      contentType: 'PlainText',
    },
  ])
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false)

  // 全屏状态
  const [isChartFullscreen, setIsChartFullscreen] = useState(false)
  const [isComparisonFullscreen, setIsComparisonFullscreen] = useState(false)

  // 三列布局拖动调整状态
  const [columnWidths, setColumnWidths] = useState([33.33, 33.33, 33.34]) // 三列的宽度百分比
  const [isDraggingColumn, setIsDraggingColumn] = useState<number | null>(null) // 正在拖动的分界线索引（0或1）

  // 模块展开/收起状态
  const [moduleCollapsed, setModuleCollapsed] = useState({
    basicInfo: false, // 基本信息（不可收起）
    optimizationConfig: false, // 优化配置
    optimizationResult: false, // 优化结果
  })

  // 保存模块收起前的宽度
  const [savedColumnWidths, setSavedColumnWidths] = useState([33.33, 33.33, 33.34])

  // 切换模块展开/收起状态
  const toggleModuleCollapse = (module: 'optimizationConfig' | 'optimizationResult') => {
    setModuleCollapsed(prev => {
      const isCurrentlyCollapsed = prev[module]

      if (!isCurrentlyCollapsed) {
        // 即将收起模块：保存当前的完整宽度设置（包括显示和隐藏的模块）
        // 如果当前有模块已经收起，使用savedColumnWidths，否则使用columnWidths
        const widthsToSave = prev.optimizationConfig || prev.optimizationResult ? savedColumnWidths : columnWidths
        setSavedColumnWidths([...widthsToSave])
      } else {
        // 即将展开模块：恢复保存的宽度设置
        setColumnWidths([...savedColumnWidths])
      }

      return {
        ...prev,
        [module]: !prev[module],
      }
    })
  }

  // 计算当前显示的模块数量和实际宽度
  const visibleModules = React.useMemo(() => {
    const modules = [
      { name: 'basicInfo', collapsed: false }, // 基本信息不可收起
      { name: 'optimizationConfig', collapsed: moduleCollapsed.optimizationConfig },
      { name: 'optimizationResult', collapsed: moduleCollapsed.optimizationResult },
    ]

    const visibleCount = modules.filter(m => !m.collapsed).length

    // 根据显示的模块重新分配宽度
    let actualWidths = [...columnWidths]

    if (visibleCount === 1) {
      // 只有基本信息显示时（优化配置和优化结果都收起），基本信息占满全屏
      if (moduleCollapsed.optimizationConfig && moduleCollapsed.optimizationResult) {
        actualWidths = [100, 0, 0]
      } else {
        // 其他情况不应该出现，因为基本信息不可收起
        actualWidths = [100, 0, 0]
      }
    } else if (visibleCount === 2) {
      // 两个模块显示时，使用用户设置的宽度比例
      if (moduleCollapsed.optimizationConfig) {
        // 只有基本信息和优化结果显示：使用第1、3列的比例
        const totalVisible = columnWidths[0] + columnWidths[2]
        if (totalVisible > 0) {
          const firstRatio = columnWidths[0] / totalVisible
          const thirdRatio = columnWidths[2] / totalVisible
          actualWidths = [firstRatio * 100, 0, thirdRatio * 100]
        } else {
          actualWidths = [50, 0, 50]
        }
      } else if (moduleCollapsed.optimizationResult) {
        // 只有基本信息和优化配置显示：使用第1、2列的比例
        const totalVisible = columnWidths[0] + columnWidths[1]
        if (totalVisible > 0) {
          const firstRatio = columnWidths[0] / totalVisible
          const secondRatio = columnWidths[1] / totalVisible
          actualWidths = [firstRatio * 100, secondRatio * 100, 0]
        } else {
          actualWidths = [50, 50, 0]
        }
      } else {
        // 这种情况不应该出现（visibleCount应该是3）
        actualWidths = [columnWidths[0], columnWidths[1], columnWidths[2]]
      }
    } else {
      // 三个模块都显示时，使用用户拖动设置的宽度
      actualWidths = columnWidths
    }

    return {
      modules,
      visibleCount,
      actualWidths,
    }
  }, [moduleCollapsed, columnWidths])

  // 处理列宽拖动
  const handleColumnMouseDown = (dividerIndex: number) => (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingColumn(dividerIndex)
  }

  const handleColumnMouseMove = React.useCallback(
    (e: MouseEvent) => {
      if (isDraggingColumn === null) return

      const container = document.querySelector('.resizable-columns-container') as HTMLElement
      if (!container) return

      const containerRect = container.getBoundingClientRect()
      const mouseX = e.clientX - containerRect.left
      const containerWidth = containerRect.width
      const mousePercentage = (mouseX / containerWidth) * 100

      // 限制拖动范围（每列最小20%，最大60%）
      const minWidth = 20
      const maxWidth = 60

      // 根据当前显示的模块调整拖动逻辑
      if (isDraggingColumn === 0) {
        // 拖动第一个分界线
        if (!moduleCollapsed.optimizationConfig && !moduleCollapsed.optimizationResult) {
          // 基本信息、优化配置和优化结果都显示：调整基本信息和优化配置的宽度
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const remainingWidth = 100 - newFirstWidth
          const secondWidth = columnWidths[1]
          const thirdWidth = columnWidths[2]
          const totalSecondThird = secondWidth + thirdWidth

          const newSecondWidth = Math.min(Math.max((secondWidth / totalSecondThird) * remainingWidth, minWidth), maxWidth)
          const newThirdWidth = remainingWidth - newSecondWidth

          setColumnWidths([newFirstWidth, newSecondWidth, newThirdWidth])
          // 同时更新保存的宽度
          setSavedColumnWidths([newFirstWidth, newSecondWidth, newThirdWidth])
        } else if (moduleCollapsed.optimizationConfig && !moduleCollapsed.optimizationResult) {
          // 只有基本信息和优化结果显示：调整两者的比例
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const newThirdWidth = 100 - newFirstWidth

          // 更新当前宽度，但保持优化配置的原始宽度在保存的设置中
          const newWidths = [newFirstWidth, savedColumnWidths[1], newThirdWidth]
          setColumnWidths([newFirstWidth, 0, newThirdWidth]) // 当前显示用
          setSavedColumnWidths(newWidths) // 保存完整宽度用于恢复
        } else if (!moduleCollapsed.optimizationConfig && moduleCollapsed.optimizationResult) {
          // 只有基本信息和优化配置显示：调整两者的比例
          const newFirstWidth = Math.min(Math.max(mousePercentage, minWidth), maxWidth)
          const newSecondWidth = 100 - newFirstWidth

          // 更新当前宽度，但保持优化结果的原始宽度在保存的设置中
          const newWidths = [newFirstWidth, newSecondWidth, savedColumnWidths[2]]
          setColumnWidths([newFirstWidth, newSecondWidth, 0]) // 当前显示用
          setSavedColumnWidths(newWidths) // 保存完整宽度用于恢复
        }
      } else if (isDraggingColumn === 1) {
        // 拖动第二个分界线
        if (!moduleCollapsed.optimizationConfig && !moduleCollapsed.optimizationResult) {
          // 所有模块都显示：调整优化配置和优化结果的宽度
          const firstWidth = columnWidths[0]
          const availableWidth = 100 - firstWidth
          const newSecondWidth = Math.min(Math.max(mousePercentage - firstWidth, minWidth), Math.min(maxWidth, availableWidth - minWidth))
          const newThirdWidth = availableWidth - newSecondWidth

          setColumnWidths([firstWidth, newSecondWidth, newThirdWidth])
          // 同时更新保存的宽度
          setSavedColumnWidths([firstWidth, newSecondWidth, newThirdWidth])
        }
      }
    },
    [isDraggingColumn, columnWidths, moduleCollapsed],
  )

  const handleColumnMouseUp = React.useCallback(() => {
    setIsDraggingColumn(null)
  }, [])

  // 添加全局鼠标事件监听
  React.useEffect(() => {
    if (isDraggingColumn !== null) {
      document.addEventListener('mousemove', handleColumnMouseMove)
      document.addEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.removeEventListener('mousemove', handleColumnMouseMove)
      document.removeEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleColumnMouseMove)
      document.removeEventListener('mouseup', handleColumnMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDraggingColumn, handleColumnMouseMove, handleColumnMouseUp])

  // 使用ref存储最新的状态值，确保自动保存时获取到最新值
  const latestValuesRef = useRef({
    taskName: '',
    description: '',
    originalPrompt: '',
    maxRounds: 5,
    llmParallel: 1,
    targetAccuracy: 90,
    exampleCount: 0,
    evaluationType: 'objective',
    evaluationCriteria: '',
    backgroundKnowledge: '',
    selectedOptimizeModel: null as PromptModel | null,
    selectedRunModel: null as PromptModel | null,
    optimizeModelParams: {} as Record<string, any>,
    runModelParams: {} as Record<string, any>,
    testCases: [] as TestCase[],
    tools: [] as Tool[],
    toolsEnabled: false,
  })

  // 使用ref跟踪已处理的jobDetailData，避免重复处理
  const processedJobDetailDataRef = useRef<string | null>(null)

  // 根据任务状态获取提示信息
  const getStatusMessage = (status: string): string => {
    switch (status) {
      case 'running':
        return t('prompts.optimizeEditPage.status.optimizing')
      case 'failed':
        return t('prompts.optimizeEditPage.status.failed')
      case 'deleted':
        return t('prompts.optimizeEditPage.status.deleted')
      case 'stopped':
        return t('prompts.optimizeEditPage.status.paused')
      case 'stopping':
        return t('prompts.optimizeEditPage.status.stopping')
      case 'queued':
        return t('prompts.optimizeEditPage.status.queued')
      default:
        return t('prompts.optimizeEditPage.status.unknown')
    }
  }

  // 处理任务详情API错误
  useEffect(() => {
    if (jobDetailError) {
      // 从错误对象中提取错误信息
      let errorMessage = '获取优化任务详情失败'

      if (jobDetailError instanceof Error) {
        // ApiError 继承自 Error，错误信息在 message 字段
        errorMessage = jobDetailError.message || errorMessage
      } else if (typeof jobDetailError === 'object' && jobDetailError !== null) {
        // 检查是否是 ApiError 类型，通常错误信息在 message 或 msg 字段
        const apiError = jobDetailError as any
        // 优先从 response.data.msg 获取，然后是 message，最后是默认值
        errorMessage = apiError.response?.data?.msg || apiError.message || apiError.msg || errorMessage
      } else if (typeof jobDetailError === 'string') {
        errorMessage = jobDetailError
      }

      // 只有当错误信息不为空时才显示
      if (errorMessage && errorMessage.trim()) {
        showSnackbar(errorMessage, 'error')
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobDetailError])

  // 处理任务详情数据（包括正式任务和草稿）
  useEffect(() => {
    if (!jobDetailData) {
      return
    }

    // 生成唯一标识，避免重复处理相同的数据
    const dataKey = `${id}_${jobDetailData.code}_${isDraftType ? 'draft' : 'formal'}`
    if (processedJobDetailDataRef.current === dataKey) {
      // 已经处理过这个数据，跳过
      return
    }

    if (jobDetailData.code === 200) {
      // 标记为已处理
      processedJobDetailDataRef.current = dataKey

      if (isDraftType) {
        // 草稿类型的数据处理
        const content = jobDetailData.content
        if (content) {
          // 设置基本信息
          setTaskName(content.name || '')
          setDescription(content.desc || '')
          setOriginalPrompt(content.rawTemplates || '')
          // 草稿数据不需要设置历史原始提示词，因为草稿本身就是可编辑的

          // 设置草稿ID - 使用响应中的 draft_id
          setDraftId(jobDetailData.draft_id)

          // 设置优化配置
          if (content.optimizeInfo) {
            setMaxRounds(content.optimizeInfo.num_iter || 5)
            setLlmParallel(content.optimizeInfo.llm_parallel || 1)
            setTargetAccuracy((content.optimizeInfo.early_stop_score || 0.9) * 100)
            setExampleCount(content.optimizeInfo.example_num || 0)
            setEvaluationType(content.optimizeInfo.user_compare_options === t('prompts.optimizeEditPage.evaluationType.objective') ? 'objective' : 'subjective')
            setEvaluationCriteria(content.optimizeInfo.user_compare_rules || '')
            setBackgroundKnowledge(content.optimizeInfo.external_knowledge || '')

            // 设置用例数据
            if (content.optimizeInfo.cases && content.optimizeInfo.cases.length > 0) {
              const testCases = content.optimizeInfo.cases.map((caseItem: any, index: number) => {
                // 新格式：字段值是 { content, format } 格式
                const inputs: any = {}
                const label: any = {}

                // 处理inputs字段
                if (caseItem.inputs) {
                  Object.keys(caseItem.inputs).forEach(key => {
                    const value = caseItem.inputs[key]
                    if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
                      inputs[key] = value
                    }
                  })
                }

                // 处理label字段
                if (caseItem.label) {
                  Object.keys(caseItem.label).forEach(key => {
                    const value = caseItem.label[key]
                    if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
                      label[key] = value
                    }
                  })
                }

                return {
                  id: index + 1,
                  messages: JSON.stringify(
                    {
                      inputs: inputs,
                      label: label,
                    },
                    null,
                    4,
                  ),
                }
              })
              setTestCases(testCases)
            }

            // 工具信息将在外层统一处理，这里先不设置
          }

          // 设置模型参数
          if (content.modelInfo && content.modelInfo.headers) {
            setOptimizeModelParams(content.modelInfo.headers)
          }

          if (content.assistantInfo && content.assistantInfo.headers) {
            setRunModelParams(content.assistantInfo.headers)
          }
        }

        // 设置工具信息 - 从content.agentTools加载
        if (jobDetailData.content?.agentTools && Array.isArray(jobDetailData.content.agentTools)) {
          const convertedTools = convertAgentToolsToTools(jobDetailData.content.agentTools)
          setTools(convertedTools)
          setToolsEnabled(convertedTools.length > 0)
        } else {
          // 没有找到工具数据
          setTools([])
          setToolsEnabled(false)
        }
      } else {
        // 正式任务类型的数据处理
        if (jobDetailData.progress) {
          // 填充基本信息（如果有job_info则从job_info获取，否则使用默认值）
          if (jobDetailData.progress.job_info) {
            setTaskName(jobDetailData.progress.job_info.name)
            setDescription(jobDetailData.progress.job_info.desc)
          }
          // 设置历史原始提示词（用于对比显示，不可编辑）
          setHistoricalOriginalPrompt(jobDetailData.progress.original_prompt || '')
          // 设置可编辑的原始提示词（用于基本信息编辑）
          setOriginalPrompt(jobDetailData.progress.original_prompt || '')

          // 设置任务状态
          setTaskStatus(jobDetailData.progress.status || '')
          // 设置错误信息
          setErrorMsg(jobDetailData.progress.error_msg || '')

          // 填充优化配置
          if (jobDetailData.optimizeInfo) {
            // 用例集配置
            const casesData = jobDetailData.optimizeInfo.cases.map((caseItem: any, index: number) => {
              // 新格式：字段值是 { content, format } 格式
              const inputs: any = {}
              const label: any = {}

              // 处理inputs字段
              if (caseItem.inputs) {
                Object.keys(caseItem.inputs).forEach(key => {
                  const value = caseItem.inputs[key]
                  if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
                    inputs[key] = value
                  }
                })
              }

              // 处理label字段
              if (caseItem.label) {
                Object.keys(caseItem.label).forEach(key => {
                  const value = caseItem.label[key]
                  if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
                    label[key] = value
                  }
                })
              }

              return {
                id: index + 1,
                messages: JSON.stringify(
                  {
                    inputs: inputs,
                    label: label,
                  },
                  null,
                  4,
                ),
              }
            })
            setTestCases(casesData)

            // 优化配置
            setMaxRounds(jobDetailData.optimizeInfo.num_iter)
            setLlmParallel(jobDetailData.optimizeInfo.llm_parallel || 1)
            setTargetAccuracy((jobDetailData.optimizeInfo.early_stop_score || 0.9) * 100)
            setExampleCount(jobDetailData.optimizeInfo.example_num)
            setEvaluationCriteria(jobDetailData.optimizeInfo.user_compare_rules)
            setEvaluationMetrics([jobDetailData.optimizeInfo.user_compare_options])
            setBackgroundKnowledge(jobDetailData.optimizeInfo.external_knowledge)

            // 设置工具信息
            if (jobDetailData.optimizeInfo.tools && Array.isArray(jobDetailData.optimizeInfo.tools)) {
              const convertedTools = convertAgentToolsToTools(jobDetailData.optimizeInfo.tools)
              setTools(convertedTools)
              setToolsEnabled(convertedTools.length > 0)
            } else {
              setTools([])
              setToolsEnabled(false)
            }
          }

          // 填充优化结果（处理历史数据）
          if (jobDetailData.history && jobDetailData.history.length > 0) {
            // 构建完整的优化历史（包含第0轮，用于显示分数）
            const allHistory = jobDetailData.history.map(item => ({
              round: item.iteration_round,
              score: (item.success_rate || 0) * 100, // 保留原始精度，转换为百分比
              improvement: `${((item.success_rate || 0) * 100).toFixed(2)}%`,
              summary: t('prompts.optimizeEditPage.optimizationConfig.roundResult', { round: item.iteration_round }),
            }))

            // 检查数据是否真的变化了，避免不必要的状态更新
            const historyChanged =
              optimizationHistory.length !== allHistory.length ||
              optimizationHistory.some((item, index) => item.round !== allHistory[index]?.round || item.score !== allHistory[index]?.score)

            if (historyChanged) {
              setOptimizationHistory(allHistory)
            }

            // 构建优化版本（只包含第1轮及以后的优化版本）
            const optimizedRounds = jobDetailData.history.filter(item => item.iteration_round > 0)
            const versions = optimizedRounds.map(item => item.optimized_prompt)
            setOptimizedVersions(versions)

            // 设置最优版本（需要调整索引，因为过滤掉了第0轮）
            const bestIterationNum = jobDetailData.progress.best_iteration
            setBestIteration(bestIterationNum)
            // 如果最优轮次大于0，则索引需要减1（因为数组不包含第0轮）
            const adjustedIndex = bestIterationNum > 0 ? bestIterationNum - 1 : 0
            setCurrentOptimizedVersion(adjustedIndex)
            setOptimizedPrompt(jobDetailData.progress.best_prompt)
          }
        }
      }
    } else {
      // 处理错误情况：code 不是 200
      const errorMessage = jobDetailData.msg || '获取优化任务详情失败'
      showSnackbar(errorMessage, 'error')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobDetailData, isDraftType, id])

  // 处理模型设置（当模型列表和任务详情都加载完成后）
  useEffect(() => {
    if (jobDetailData && jobDetailData.code === 200 && models.length > 0 && isEditMode) {
      if (isDraftType) {
        // 草稿类型的模型设置
        const content = jobDetailData.content
        if (content) {
          // 根据 id + model_from 设置优化模型
          if (content.modelInfo && content.modelInfo.id && content.modelInfo.model_from) {
            const optimizeModel = models.find(m => m.openModel.model_id === content.modelInfo.id.toString() && m.model_from === content.modelInfo.model_from)
            if (optimizeModel) {
              setSelectedOptimizeModel(optimizeModel)
              // 设置优化模型参数
              if (content.modelInfo.headers) {
                setOptimizeModelParams(content.modelInfo.headers)
              }
            } else {
              // 如果找不到匹配的模型，设置为 null（模型可能已被删除）
              console.warn('❌ 未找到匹配的优化模型:', {
                id: content.modelInfo.id,
                model_from: content.modelInfo.model_from,
              })
              setSelectedOptimizeModel(null)
              setOptimizeModelParams({})
            }
          } else {
            // 如果草稿中没有模型信息，设置为 null
            setSelectedOptimizeModel(null)
            setOptimizeModelParams({})
          }

          // 根据 id + model_from 设置运行模型
          if (content.assistantInfo && content.assistantInfo.id && content.assistantInfo.model_from) {
            const runModel = models.find(m => m.openModel.model_id === content.assistantInfo.id.toString() && m.model_from === content.assistantInfo.model_from)
            if (runModel) {
              setSelectedRunModel(runModel)
              // 设置运行模型参数
              if (content.assistantInfo.headers) {
                setRunModelParams(content.assistantInfo.headers)
              }
            } else {
              // 如果找不到匹配的模型，设置为 null（模型可能已被删除）
              console.warn('❌ 未找到匹配的运行模型:', {
                id: content.assistantInfo.id,
                model_from: content.assistantInfo.model_from,
              })
              setSelectedRunModel(null)
              setRunModelParams({})
            }
          } else {
            // 如果草稿中没有模型信息，设置为 null
            setSelectedRunModel(null)
            setRunModelParams({})
          }
        }
      } else if (jobDetailData.progress) {
        // 正式任务类型的模型设置
        const jobInfo = jobDetailData.progress.job_info
        const modelInfo = jobInfo?.modelInfo // 优化模型
        const assistantInfo = jobInfo?.assistantInfo // 运行模型

        // 根据 id + model_from 设置优化模型
        if (modelInfo && modelInfo.id && modelInfo.model_from && models.length > 0) {
          const optimizeModel = models.find(m => m.openModel.model_id === modelInfo.id.toString() && m.model_from === modelInfo.model_from)
          if (optimizeModel) {
            setSelectedOptimizeModel(optimizeModel)
            // 设置优化模型参数
            if (modelInfo.headers) {
              setOptimizeModelParams(modelInfo.headers)
            }
          } else {
            // 如果找不到匹配的模型，设置为 null（模型可能已被删除）
            console.warn('❌ 未找到匹配的优化模型:', {
              id: modelInfo.id,
              model_from: modelInfo.model_from,
            })
            setSelectedOptimizeModel(null)
            setOptimizeModelParams({})
          }
        } else {
          // 如果任务中没有模型信息，设置为 null
          setSelectedOptimizeModel(null)
          setOptimizeModelParams({})
        }

        // 根据 id + model_from 设置运行模型
        if (assistantInfo && assistantInfo.id && assistantInfo.model_from && models.length > 0) {
          const runModel = models.find(m => m.openModel.model_id === assistantInfo.id.toString() && m.model_from === assistantInfo.model_from)
          if (runModel) {
            setSelectedRunModel(runModel)
            // 设置运行模型参数
            if (assistantInfo.headers) {
              setRunModelParams(assistantInfo.headers)
            }
          } else {
            // 如果找不到匹配的模型，设置为 null（模型可能已被删除）
            console.warn('❌ 未找到匹配的运行模型:', {
              id: assistantInfo.id,
              model_from: assistantInfo.model_from,
            })
            setSelectedRunModel(null)
            setRunModelParams({})
          }
        } else {
          // 如果任务中没有模型信息，设置为 null
          setSelectedRunModel(null)
          setRunModelParams({})
        }
      }
    }
  }, [jobDetailData, models, isDraftType])

  // 加载优化任务详情（现在通过 hooks 处理，这个函数保留用于兼容性）
  const loadJobDetail = async (jobId: string) => {
    // 现在数据通过 hooks 自动获取和处理，这个函数主要用于兼容性
    // 如果任务正在运行，启动轮询
    if (jobDetailData?.progress?.status === 'running') {
      // TODO: 实现进度轮询
      // startProgressPolling(jobId)
    }
  }

  // 处理用例历史记录数据
  useEffect(() => {
    if (jobHistoryData && (jobHistoryData.code === 200 || jobHistoryData.code === 0)) {
      if (jobHistoryData.history && jobHistoryData.history.length > 0) {
        // 获取第一个历史记录项的评测用例
        const historyItem = jobHistoryData.history[0]
        if (historyItem.evaluate_cases) {
          setEvaluateCases(historyItem.evaluate_cases)
        } else {
          setEvaluateCases([])
        }
      } else {
        // 如果history为空数组，清空数据
        setEvaluateCases([])
        // 如果有错误消息，显示提示
        if (jobHistoryData.msg) {
          showSnackbar(jobHistoryData.msg, 'warning')
        }
      }
    } else if (jobHistoryData && jobHistoryData.code !== 200 && jobHistoryData.code !== 0) {
      // 如果返回错误，显示错误信息
      showSnackbar(jobHistoryData.msg || '获取用例历史记录失败', 'error')
      setEvaluateCases([])
    }
  }, [jobHistoryData])

  // 获取提示词列表
  useEffect(() => {
    const fetchPromptList = async () => {
      if (isEditMode) return // 编辑模式不需要加载提示词列表

      setPromptListLoading(true)
      try {
        // 直接调用API获取原始数据
        const apiParams = {
          workspace_id: workspaceId,
          page_num: 1,
          page_size: 100,
        }

        const apiResponse = await PromptService.getPrompts({
          workspaceId: apiParams.workspace_id,
          page: apiParams.page_num,
          pageSize: apiParams.page_size,
        })

        if (apiResponse.prompts) {
          // PromptService.getPrompts 返回的已经是转换后的 Prompt 对象数组
          // 直接使用这些数据，但需要为每个 prompt 添加 _raw 属性以便后续使用
          const promptsWithRaw = apiResponse.prompts.map((prompt: any) => ({
            ...prompt,
            // 保留原始数据的引用（如果需要的话，可以从其他地方获取）
            _raw: prompt,
          }))

          setPromptList(promptsWithRaw)
          setRawPromptList(apiResponse.prompts)
        }
      } catch (error) {
        console.error('获取提示词列表失败:', error)
      } finally {
        setPromptListLoading(false)
      }
    }

    fetchPromptList()
  }, [isEditMode])

  // 处理选择提示词
  const handlePromptSelect = async (prompt: any) => {
    setSelectedPrompt(prompt)

    if (prompt) {
      // 填充基本信息 - 现在 prompt 本身就是转换后的 Prompt 对象
      // 对任务名称和描述进行长度限制
      const taskName = prompt.name || ''
      const description = prompt.description || ''

      setTaskName(taskName.length > 32 ? taskName.substring(0, 32) : taskName)
      setDescription(description.length > 256 ? description.substring(0, 256) : description)
      setEditorPromptId(prompt.id || '')

      // 获取提示词详情以获取完整的提示词内容
      try {
        const detailResponse = await PromptService.getPromptDetail(prompt.id, {
          withDraft: true,
          withCommit: true,
          withDefaultConfig: false,
          workspaceId: workspaceId,
        })

        if (detailResponse.prompt && detailResponse.prompt.length > 0) {
          const promptDetail = detailResponse.prompt[0]

          // 优先从prompt_draft中提取system消息，如果没有则从prompt_commit中提取
          let systemMessage = null
          let messageSource = ''

          if (promptDetail.prompt_draft?.detail?.prompt_template?.messages) {
            const messages = promptDetail.prompt_draft.detail.prompt_template.messages
            systemMessage = messages.find((msg: any) => msg.role === 'system')
            messageSource = 'draft'
          } else if (promptDetail.prompt_commit?.detail?.prompt_template?.messages) {
            const messages = promptDetail.prompt_commit.detail.prompt_template.messages
            systemMessage = messages.find((msg: any) => msg.role === 'system')
            messageSource = 'commit'
          }

          if (systemMessage) {
            setOriginalPrompt(systemMessage.content)
          } else {
            setOriginalPrompt('')
          }

          // 填充工具信息
          // 优先从 prompt_draft 中获取工具，如果没有则从 prompt_commit 中获取
          let toolsData = null
          let toolsEnabledValue = false

          if (promptDetail.prompt_draft?.detail?.tools) {
            toolsData = promptDetail.prompt_draft.detail.tools
            toolsEnabledValue = promptDetail.prompt_draft.detail.tool_call_config?.tool_choice === 'auto'
          } else if (promptDetail.prompt_commit?.detail?.tools) {
            toolsData = promptDetail.prompt_commit.detail.tools
            toolsEnabledValue = promptDetail.prompt_commit.detail.tool_call_config?.tool_choice === 'auto'
          }

          if (toolsData && Array.isArray(toolsData) && toolsData.length > 0) {
            const convertedTools = convertAgentToolsToTools(toolsData)
            setTools(convertedTools)
            setToolsEnabled(toolsEnabledValue)
          } else {
            setTools([])
            setToolsEnabled(false)
          }
        } else {
          setOriginalPrompt('')
          setTools([])
          setToolsEnabled(false)
        }
      } catch (error) {
        console.error('获取提示词详情失败:', error)
        setOriginalPrompt('')
        setTools([])
        setToolsEnabled(false)
      }
    } else {
      // 清空相关字段
      setTaskName('')
      setDescription('')
      setOriginalPrompt('')
      setEditorPromptId(null)
      setTools([])
      setToolsEnabled(false)
    }
  }

  // 页面加载时获取模型列表
  React.useEffect(() => {
    fetchModels()
  }, [])

  // 响应式计算主体内容区域高度
  React.useEffect(() => {
    const updateContentHeight = () => {
      if (isNewDashboard) {
        setContentHeight('85vh')
      } else {
        if (window.innerWidth < 640) {
          // 小屏幕：手机等移动设备
          setContentHeight('70vh')
        } else if (window.innerWidth < 2000) {
          // 中等屏幕：平板、14寸笔记本等
          setContentHeight('72vh')
        } else {
          // 大屏幕：15寸以上笔记本、台式显示器
          setContentHeight('85vh')
        }
      }
    }

    updateContentHeight()
    window.addEventListener('resize', updateContentHeight)
    return () => window.removeEventListener('resize', updateContentHeight)
  }, [isNewDashboard])

  // 页面进入时，如果是草稿类型，强制刷新一次（确保获取最新数据）
  // 使用 ref 来跟踪是否已经执行过，确保只在组件挂载时执行一次
  const hasRefetchedRef = React.useRef(false)
  React.useEffect(() => {
    if (id && isEditMode && isDraftType && refetchDraftDetail && !hasRefetchedRef.current) {
      // 使草稿详情查询缓存失效，强制重新获取
      const draftIdNum = parseInt(id)
      queryClient.invalidateQueries(['selfOpt', 'draftDetail', draftIdNum, workspaceId, userId])
      // 立即刷新一次
      refetchDraftDetail()
      hasRefetchedRef.current = true
    }
  }, [id, isEditMode, isDraftType, refetchDraftDetail, queryClient, workspaceId, userId])

  // 从 sessionStorage 读取数据或加载已有数据
  React.useEffect(() => {
    if (id && isEditMode) {
      // 编辑模式，数据通过 hooks 自动加载
      loadJobDetail(id)
    } else {
      // 新建模式，从 sessionStorage 读取数据
      const optimizationData = sessionStorage.getItem('optimizationData')
      if (optimizationData) {
        try {
          const data = JSON.parse(optimizationData)
          // 对任务名称和描述进行长度限制
          const taskName = data.taskName || ''
          const description = data.description || ''

          setTaskName(taskName.length > 32 ? taskName.substring(0, 32) : taskName)
          setDescription(description.length > 256 ? description.substring(0, 256) : description)
          setOriginalPrompt(data.originalPrompt || '')
          setFromEditor(data.fromEditor || false)
          setEditorPromptId(data.editorPromptId || null)

          // 设置工具信息（如果存在）
          if (data.tools && Array.isArray(data.tools) && data.tools.length > 0) {
            const convertedTools = convertAgentToolsToTools(data.tools)
            setTools(convertedTools)
            setToolsEnabled(data.toolsEnabled !== undefined ? data.toolsEnabled : convertedTools.length > 0)
          } else {
            // 如果没有工具信息，清空工具
            setTools([])
            setToolsEnabled(false)
          }

          // 清除数据，避免重复使用
          sessionStorage.removeItem('optimizationData')
        } catch (error) {
          console.error('Failed to parse optimization data:', error)
        }
      }
    }
  }, [id, isEditMode])

  // 使用公共函数进行工具格式转换
  const convertAgentToolsToTools = (agentTools: any[]): Tool[] => {
    return convertApiToolsToFrontendTools(agentTools, 0)
  }

  const convertToolsToAgentTools = (tools: Tool[]) => {
    return convertFrontendToolsToApiTools(tools)
  }

  // 构建请求参数的公共函数
  const buildOptimizationRequest = (isDraft: boolean = false, values?: typeof latestValuesRef.current) => {
    // 如果传入了values参数，使用values中的数据，否则使用当前状态
    const data = values || {
      taskName,
      description,
      originalPrompt,
      maxRounds,
      llmParallel,
      targetAccuracy,
      exampleCount,
      evaluationType,
      evaluationCriteria,
      backgroundKnowledge,
      selectedOptimizeModel,
      selectedRunModel,
      optimizeModelParams,
      runModelParams,
      testCases,
      tools,
      toolsEnabled,
    }

    // 构建用例数据
    const cases: OptimizationCase[] = values ? convertTestCasesToCheckFormatWithValues(data.testCases) : convertTestCasesToCheckFormat()

    const baseRequest = {
      name: data.taskName || (isDraft ? t('prompts.optimizeEditPage.draft.unnamed') : ''),
      desc: data.description || '',
      rawTemplates: data.originalPrompt || '',
      optimizeInfo: {
        cases: cases.length > 0 ? cases : [],
        num_iter: data.maxRounds || 5,
        early_stop_score: (data.targetAccuracy || 90) / 100,
        example_num: data.exampleCount,
        placeholder: [],
        llm_parallel: data.llmParallel || 1,
        user_compare_options: isDraft
          ? data.evaluationType === 'objective'
            ? '客观评价'
            : '主观评价'
          : data.evaluationType === 'objective'
            ? t('prompts.optimizeEditPage.evaluationType.objective')
            : t('prompts.optimizeEditPage.evaluationType.subjective'),
        user_compare_rules: data.evaluationCriteria || '',
        external_knowledge: data.backgroundKnowledge || '',
      },
      modelInfo: data.selectedOptimizeModel
        ? {
            id: parseInt(data.selectedOptimizeModel.openModel.model_id),
            model: data.selectedOptimizeModel.openModel.name,
            model_from: data.selectedOptimizeModel.model_from,
            headers: data.optimizeModelParams,
          }
        : {
            id: 0,
            model: '',
            model_from: '',
            headers: {},
          },
      assistantInfo: data.selectedRunModel
        ? {
            id: parseInt(data.selectedRunModel.openModel.model_id),
            model: data.selectedRunModel.openModel.name,
            model_from: data.selectedRunModel.model_from,
            headers: data.runModelParams,
          }
        : data.selectedOptimizeModel
          ? {
              id: parseInt(data.selectedOptimizeModel.openModel.model_id),
              model: data.selectedOptimizeModel.openModel.name,
              model_from: data.selectedOptimizeModel.model_from,
              headers: data.runModelParams,
            }
          : {
              id: 0,
              model: '',
              model_from: '',
              headers: {},
            },
      agentTools: data.toolsEnabled ? convertToolsToAgentTools(data.tools || []) : [],
    }

    return baseRequest
  }

  // 自动保存函数
  const autoSave = async () => {
    if (isSavingDraft) return

    setIsSavingDraft(true)
    try {
      // 使用ref中的最新值构建草稿请求数据
      const draftData = buildOptimizationRequest(true, latestValuesRef.current)

      // 获取用户ID
      const userId = user?.id || ENV_CONFIG.DEFAULT_USER_ID

      // 调用保存草稿API
      const response = await saveJobDraftMutation.mutateAsync({
        data: draftData,
        workspaceId,
        userId,
        draftId,
      })

      if (response.code === 200) {
        // 保存成功
        if (response.draft_id) {
          setDraftId(response.draft_id)
        }
        setLastSavedTime(new Date())
        // 注意：自动保存时不使查询缓存失效，避免触发数据重新获取导致用户输入内容被覆盖
        // 数据已保存到服务器，下次进入页面时会自然获取最新数据
        // 自动保存不显示成功提示，避免打扰用户
      } else {
        // 保存失败，静默处理，不显示错误提示
        console.warn('自动保存失败:', response.msg)
      }
    } catch (error: any) {
      console.warn('自动保存失败:', error)
      // 自动保存失败时静默处理，不显示错误提示
    } finally {
      setIsSavingDraft(false)
    }
  }

  // 触发自动保存
  const triggerAutoSave = () => {
    // 清除之前的定时器
    if (autoSaveTimeout) {
      clearTimeout(autoSaveTimeout)
    }

    // 设置新的定时器，1秒后自动保存
    const timeout = setTimeout(() => {
      // 确保保存的是最新的状态
      autoSave()
    }, 1000)

    setAutoSaveTimeout(timeout)
  }

  // 包装setter函数，添加自动保存触发
  const createAutoSaveSetter = (setter: (value: any) => void, key: keyof typeof latestValuesRef.current) => {
    return (value: any) => {
      // 同时更新状态和ref
      setter(value)
      latestValuesRef.current[key] = value
      triggerAutoSave()
    }
  }

  // 创建带自动保存的setter函数
  const setTaskNameWithAutoSave = createAutoSaveSetter(setTaskName, 'taskName')
  const setDescriptionWithAutoSave = createAutoSaveSetter(setDescription, 'description')
  const setOriginalPromptWithAutoSave = createAutoSaveSetter(setOriginalPrompt, 'originalPrompt')
  const setMaxRoundsWithAutoSave = createAutoSaveSetter(setMaxRounds, 'maxRounds')
  const setLlmParallelWithAutoSave = createAutoSaveSetter(setLlmParallel, 'llmParallel')
  const setTargetAccuracyWithAutoSave = createAutoSaveSetter(setTargetAccuracy, 'targetAccuracy')
  const setExampleCountWithAutoSave = createAutoSaveSetter(setExampleCount, 'exampleCount')
  const setEvaluationTypeWithAutoSave = createAutoSaveSetter(setEvaluationType, 'evaluationType')
  const setEvaluationCriteriaWithAutoSave = createAutoSaveSetter(setEvaluationCriteria, 'evaluationCriteria')
  const setBackgroundKnowledgeWithAutoSave = createAutoSaveSetter(setBackgroundKnowledge, 'backgroundKnowledge')

  // 模型参数相关的自动保存setter函数
  const setOptimizeModelParamsWithAutoSave = createAutoSaveSetter(setOptimizeModelParams, 'optimizeModelParams')
  const setRunModelParamsWithAutoSave = createAutoSaveSetter(setRunModelParams, 'runModelParams')

  // 用例集相关的自动保存setter函数
  const setTestCasesWithAutoSave = createAutoSaveSetter(setTestCases, 'testCases')

  // 同步状态到ref
  useEffect(() => {
    latestValuesRef.current = {
      taskName,
      description,
      originalPrompt,
      maxRounds,
      llmParallel,
      targetAccuracy,
      exampleCount,
      evaluationType,
      evaluationCriteria,
      backgroundKnowledge,
      selectedOptimizeModel,
      selectedRunModel,
      optimizeModelParams,
      runModelParams,
      testCases,
      tools,
      toolsEnabled,
    }
  }, [
    taskName,
    description,
    originalPrompt,
    maxRounds,
    llmParallel,
    targetAccuracy,
    exampleCount,
    evaluationType,
    evaluationCriteria,
    backgroundKnowledge,
    selectedOptimizeModel,
    selectedRunModel,
    optimizeModelParams,
    runModelParams,
    testCases,
    tools,
    toolsEnabled,
  ])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout)
      }
    }
  }, [autoSaveTimeout])

  const handleStartOptimization = async () => {
    if (isCreatingJob) return

    setIsCreatingJob(true)
    try {
      // 使用 ref 中的最新值，避免状态延迟问题
      const latestValues = latestValuesRef.current
      const currentDraftId = draftId
      const shouldDeleteDraftBeforeCreate = Boolean(isDraftType && currentDraftId)
      const shouldDeleteDraftAfterCreate = Boolean(!isDraftType && currentDraftId)

      // 验证必填字段（使用最新值）
      if (!latestValues.taskName.trim()) {
        showSnackbar(t('prompts.optimizeEditPage.messages.taskNameRequired'), 'error')
        setIsCreatingJob(false)
        return
      }

      if (!latestValues.originalPrompt.trim()) {
        showSnackbar(t('prompts.optimizeEditPage.messages.originalPromptRequired'), 'error')
        setIsCreatingJob(false)
        return
      }

      if (latestValues.testCases.length === 0) {
        showSnackbar(t('prompts.optimizeEditPage.messages.testCasesRequired'), 'error')
        setIsCreatingJob(false)
        return
      }

      if (!latestValues.selectedOptimizeModel || !latestValues.selectedRunModel) {
        showSnackbar(t('prompts.optimizeEditPage.messages.modelsRequired'), 'error')
        setIsCreatingJob(false)
        return
      }

      // 先进行用例检查（使用最新值）
      const validation = validateTestCasesWithValues(latestValues)

      if (!validation.isValid) {
        showSnackbar(validation.errorMessage || '用例检查失败', 'error')
        setIsCreatingJob(false)
        return
      }

      // 用例检查通过后，如果是草稿状态且有草稿ID，删除草稿
      if (shouldDeleteDraftBeforeCreate && currentDraftId) {
        try {
          await deleteJobMutation.mutateAsync({
            jobId: currentDraftId.toString(),
            workspaceId,
            userId,
            jobType: 'draft',
          })
          setDraftId(undefined)
        } catch (error) {
          console.error('删除草稿失败:', error)
          showSnackbar(t('prompts.optimizeEditPage.messages.draftDeleteFailed'), 'error')
          setIsCreatingJob(false)
          return
        }
      }

      // 构建请求数据 - 使用公共函数，传入最新值
      const requestData = buildOptimizationRequest(false, latestValues)

      // 调用API创建优化任务
      const response = await createOptimizationJobMutation.mutateAsync({
        request: requestData,
        workspaceId,
        userId,
      })

      if (response.code === 200 || response.code === 0) {
        if (shouldDeleteDraftAfterCreate && currentDraftId) {
          try {
            await deleteJobMutation.mutateAsync({
              jobId: currentDraftId.toString(),
              workspaceId,
              userId,
              jobType: 'draft',
            })
            setDraftId(undefined)
          } catch (error) {
            console.error('删除草稿失败:', error)
            showSnackbar(t('prompts.optimizeEditPage.messages.draftDeleteFailed'), 'error')
          }
        }

        showSnackbar(t('prompts.optimizeEditPage.messages.jobCreateSuccess'), 'success')

        // 跳转到优化任务列表页
        // 延迟一下让用户看到成功提示
        setTimeout(() => {
          navigate('/dashboard/prompts/optimize', { replace: true })
        }, 1000)
      } else {
        const errorMessage = response.msg && response.msg.trim() ? response.msg.trim() : t('prompts.optimizeEditPage.messages.jobCreateFailed')
        showSnackbar(errorMessage, 'error')
      }
    } catch (error: any) {
      const rawErrorMessage =
        (typeof error?.response?.msg === 'string' && error.response.msg) ||
        (typeof error?.body?.msg === 'string' && error.body.msg) ||
        (typeof error?.message === 'string' && error.message) ||
        ''
      const errorMessage = typeof rawErrorMessage === 'string' ? rawErrorMessage.trim() : ''
      showSnackbar(errorMessage || t('prompts.optimizeEditPage.messages.jobCreateFailed'), 'error')
    } finally {
      setIsCreatingJob(false)
    }
  }

  const handleBack = () => {
    navigate('/dashboard/prompts/optimize?refresh=true')
  }

  // 将测试用例转换为新的显示格式
  const formatTestCaseForDisplay = (testCase: TestCase): string => {
    try {
      // 尝试解析JSON格式的messages
      const jsonData = JSON.parse(testCase.messages)
      if (jsonData.messages && Array.isArray(jsonData.messages)) {
        const displayData: any = {
          inputs: {},
          label: {},
        }

        // 处理每条消息
        jsonData.messages.forEach((msg: any) => {
          if (msg.role === 'inputs') {
            const key = msg.variableName && msg.variableName.trim() ? msg.variableName : 'query'
            displayData.inputs[key] = msg.content
          } else if (msg.role === 'label') {
            const key = msg.variableName && msg.variableName.trim() ? msg.variableName : 'output'
            // 尝试解析content为JSON，如果失败则作为字符串处理
            try {
              displayData.label[key] = JSON.parse(msg.content)
            } catch {
              displayData.label[key] = msg.content
            }
          }
        })

        return JSON.stringify(displayData, null, 2)
      }
    } catch (error) {
      // 如果不是JSON格式，创建默认格式
      const displayData = {
        inputs: {
          query: testCase.messages,
        },
        label: {
          output: '',
        },
      }
      return JSON.stringify(displayData, null, 2)
    }

    // 默认返回原始数据
    return testCase.messages
  }

  // 从提示词中提取变量的函数
  const extractVariablesFromPrompt = (prompt: string): string[] => {
    const variableRegex = /\{\{([^}]+)\}\}/g
    const variables: string[] = []
    let match

    while ((match = variableRegex.exec(prompt)) !== null) {
      const variableName = match[1].trim()
      if (variableName && !variables.includes(variableName)) {
        variables.push(variableName)
      }
    }

    return variables
  }

  // 根据提示词内容生成测试用例模板
  const generateTestCaseTemplate = (prompt: string): string => {
    const variables = extractVariablesFromPrompt(prompt)

    const inputs: any = {}
    const label: any = {}

    if (variables.length > 0) {
      // 如果有变量，为每个变量创建inputs字段（新格式：content + format）
      variables.forEach(variable => {
        inputs[variable] = {
          content: '',
          format: 'PlainText',
        }
      })
    } else {
      // 如果没有变量，创建一个默认的query输入（新格式：content + format）
      inputs.query = {
        content: '',
        format: 'PlainText',
      }
    }

    // 添加一个默认的label输出（新格式：content + format）
    label.output = {
      content: '',
      format: 'PlainText',
    }

    const testCaseData = {
      inputs: inputs,
      label: label,
    }

    return JSON.stringify(testCaseData, null, 2)
  }

  // 用例集相关操作
  const handleAddCase = () => {
    // 检查用例数量限制
    if (testCases.length >= MAX_TEST_CASES) {
      showSnackbar(t('prompts.optimizeEditPage.messages.testCasesLimitExceeded', { max: MAX_TEST_CASES }), 'warning')
      return
    }

    const newId = Math.max(...testCases.map(c => c.id), 0) + 1
    const template = generateTestCaseTemplate(originalPrompt)
    setTestCasesWithAutoSave([...testCases, { id: newId, messages: template }])
  }

  // 处理清空用例集
  const handleClearCases = () => {
    setClearConfirmOpen(true)
  }

  // 确认清空用例集
  const handleConfirmClear = () => {
    setTestCasesWithAutoSave([])
    setClearConfirmOpen(false)
    // 清空用例后跳转到第一页
    setTestCasePage(0)
    showSnackbar(t('prompts.optimizeEditPage.messages.testCasesCleared'), 'success')
  }

  // 处理下载数据集范例
  const handleDownloadSample = () => {
    // 无工具调用示例数据
    const noToolCallData = [
      {
        inputs_role: '信息提取',
        inputs_query: '潘之恒（约1536—1621）字景升，号鸾啸生，冰华生，安徽歙县、岩寺人，侨寓金陵（今江苏南京）',
        label_output: '[潘之恒]',
      },
      {
        inputs_role: '信息提取',
        inputs_query:
          '高祖二十二子：窦皇后生建成（李建成）、太宗皇帝（李世民）、玄霸（李玄霸）、元吉（李元吉），万贵妃生智云（李智云），莫嫔生元景（李元景），孙嫔生元昌（李元昌）',
        label_output: '[李建成, 李世民, 李玄霸, 李元吉, 李智云, 李元景, 李元昌]',
      },
      {
        inputs_role: '信息提取',
        inputs_query: '郭造卿（1532—1593），字建初，号海岳，福建福清县化南里人（今福清市人），郭遇卿之弟，郭造卿少年的时候就很有名气，曾游学吴越',
        label_output: '[郭造卿, 郭遇卿]',
      },
      {
        inputs_role: '信息提取',
        inputs_query: '沈自邠，字茂仁，号几轩，又号茂秀，浙江秀水长溪（今嘉兴南汇）人',
        label_output: '[沈自邠]',
      },
    ]

    // 工具调用示例数据
    const toolCallData = [
      {
        inputs_query: '请帮我打开空调',
        label_tool_calls: '[{ "name": "ac_open", "arguments": {} }]',
      },
      {
        inputs_query: '请帮我关闭空调',
        label_tool_calls: '[{ "name": "ac_close", "arguments": {} }]',
      },
      {
        inputs_query: '天气太热了，开一下空调',
        label_tool_calls: '[{ "name": "ac_open", "arguments": {} }]',
      },
      {
        inputs_query: '有点冷，先帮我关窗，再调整到29度',
        label_tool_calls: '[{ "name": "ac_control", "arguments": { "temperature": 29 } }]',
      },
      {
        inputs_query: '有点热，先帮我开窗，再调整到21度',
        label_tool_calls: '[{ "name": "ac_control", "arguments": { "temperature": 21 } }]',
      },
    ]

    // 创建工作簿
    const workbook = XLSX.utils.book_new()

    // 创建无工具调用示例工作表
    const noToolCallWorksheet = XLSX.utils.json_to_sheet(noToolCallData)
    noToolCallWorksheet['!cols'] = [
      { wch: 12 }, // inputs_role
      { wch: 60 }, // inputs_query
      { wch: 40 }, // label_output
    ]
    XLSX.utils.book_append_sheet(workbook, noToolCallWorksheet, '无工具调用示例')

    // 创建工具调用示例工作表
    const toolCallWorksheet = XLSX.utils.json_to_sheet(toolCallData)
    toolCallWorksheet['!cols'] = [
      { wch: 30 }, // inputs_query
      { wch: 60 }, // label_tool_calls
    ]
    XLSX.utils.book_append_sheet(workbook, toolCallWorksheet, '工具调用示例')

    // 生成Excel文件并下载
    XLSX.writeFile(workbook, '数据集范例.xlsx')

    showSnackbar(t('prompts.optimizeEditPage.messages.datasetExampleDownloaded'), 'success')
  }

  const handleEditCase = (testCase: TestCase) => {
    // 优先从最新的 testCases 状态中查找对应的用例，确保使用最新的数据（包括最新的 format）
    // 如果状态中找不到，则使用 ref 中的最新值，最后回退到传入的参数
    // 这样可以避免在状态更新过程中使用旧的闭包值
    const latestTestCase = testCases.find(c => c.id === testCase.id) || latestValuesRef.current.testCases.find(c => c.id === testCase.id) || testCase
    setCurrentTestCase(latestTestCase)
    setIsViewMode(false) // 设置为编辑模式

    // 尝试解析JSON格式的messages数据
    try {
      const jsonData = JSON.parse(latestTestCase.messages)

      // 新格式：直接包含inputs和label字段
      if (jsonData.inputs && jsonData.label) {
        const details: TestCaseDetail[] = []
        let detailId = 1

        // 处理inputs字段（新格式：包含content和format）
        Object.keys(jsonData.inputs).forEach(key => {
          const value = jsonData.inputs[key]
          if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
            details.push({
              id: detailId++,
              role: 'inputs',
              content: value.content || '',
              variableName: key,
              contentType: (value.format || 'PlainText') as FieldType,
            })
          }
        })

        // 处理label字段（新格式：包含content和format）
        Object.keys(jsonData.label).forEach(key => {
          const labelValue = jsonData.label[key]
          if (labelValue && typeof labelValue === 'object' && 'content' in labelValue && 'format' in labelValue) {
            details.push({
              id: detailId++,
              role: 'label',
              content: labelValue.content || '',
              variableName: key,
              contentType: (labelValue.format || 'PlainText') as FieldType,
            })
          }
        })

        setTestCaseDetails(details)
      }
    } catch (error) {
      // 如果不是JSON格式，按普通文本处理
      setTestCaseDetails([{ id: 1, role: 'inputs', content: latestTestCase.messages, variableName: '', contentType: 'PlainText' }])
    }

    setEditDialogOpen(true)
  }

  const handleViewCase = (testCase: TestCase) => {
    // 优先从最新的 testCases 状态中查找对应的用例，确保使用最新的数据（包括最新的 format）
    // 如果状态中找不到，则使用 ref 中的最新值，最后回退到传入的参数
    // 这样可以避免在状态更新过程中使用旧的闭包值
    const latestTestCase = testCases.find(c => c.id === testCase.id) || latestValuesRef.current.testCases.find(c => c.id === testCase.id) || testCase
    setCurrentTestCase(latestTestCase)
    setIsViewMode(true) // 设置为查看模式

    // 尝试解析JSON格式的messages数据
    try {
      const jsonData = JSON.parse(latestTestCase.messages)

      // 新格式：直接包含inputs和label字段
      if (jsonData.inputs && jsonData.label) {
        const details: TestCaseDetail[] = []
        let detailId = 1

        // 处理inputs字段（新格式：包含content和format）
        Object.keys(jsonData.inputs).forEach(key => {
          const value = jsonData.inputs[key]
          if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
            details.push({
              id: detailId++,
              role: 'inputs',
              content: value.content || '',
              variableName: key,
              contentType: (value.format || 'PlainText') as FieldType,
            })
          }
        })

        // 处理label字段（新格式：包含content和format）
        Object.keys(jsonData.label).forEach(key => {
          const labelValue = jsonData.label[key]
          if (labelValue && typeof labelValue === 'object' && 'content' in labelValue && 'format' in labelValue) {
            details.push({
              id: detailId++,
              role: 'label',
              content: labelValue.content || '',
              variableName: key,
              contentType: (labelValue.format || 'PlainText') as FieldType,
            })
          }
        })

        setTestCaseDetails(details)
      }
    } catch (error) {
      // 如果不是JSON格式，按普通文本处理
      setTestCaseDetails([{ id: 1, role: 'inputs', content: latestTestCase.messages, variableName: '', contentType: 'PlainText' }])
    }

    setEditDialogOpen(true) // 使用编辑 drawer 而不是查看对话框
  }

  const handleSwitchToEditMode = () => {
    setIsViewMode(false)
  }

  const handleSaveEdit = () => {
    if (currentTestCase) {
      // 验证必填字段（只验证字段名称，字段值可以为空）
      const emptyFields = testCaseDetails.filter(d => !d.variableName?.trim())
      if (emptyFields.length > 0) {
        showSnackbar('请填写所有必填字段', 'error')
        return
      }

      // 将用例详情转换为新格式的JSON格式（包含content和format）
      const inputs: any = {}
      const label: any = {}

      testCaseDetails.forEach(detail => {
        if (detail.role === 'inputs' && detail.variableName?.trim()) {
          // 新格式：使用 content 和 format
          inputs[detail.variableName] = {
            content: detail.content || '',
            format: detail.contentType || 'PlainText',
          }
        } else if (detail.role === 'label' && detail.variableName?.trim()) {
          // 新格式：使用 content 和 format
          label[detail.variableName] = {
            content: detail.content || '',
            format: detail.contentType || 'PlainText',
          }
        }
      })

      // 构建新格式的JSON
      const jsonData = {
        inputs: inputs,
        label: label,
      }

      // 将JSON字符串保存到messages字段
      const jsonString = JSON.stringify(jsonData, null, 2)

      // 使用函数式更新确保获取最新的状态，并立即更新 ref 以确保自动保存使用最新数据
      setTestCases(prevTestCases => {
        const updatedTestCases = prevTestCases.map(c => (c.id === currentTestCase.id ? { ...c, messages: jsonString } : c))
        // 立即更新 ref，确保自动保存使用最新的数据
        latestValuesRef.current.testCases = updatedTestCases
        return updatedTestCases
      })

      // 触发自动保存
      triggerAutoSave()

      setEditDialogOpen(false)
      setCurrentTestCase(null)

      showSnackbar(t('prompts.optimizeEditPage.messages.testCasesSaved'), 'success')
    }
  }

  const handleDeleteDetailRow = (detailId: number) => {
    setTestCaseDetails(testCaseDetails.filter(d => d.id !== detailId))
  }

  const handleUpdateDetail = (detailId: number, field: keyof TestCaseDetail, value: any) => {
    setTestCaseDetails(testCaseDetails.map(d => (d.id === detailId ? { ...d, [field]: value } : d)))
  }

  // 自定义用例检查函数（使用指定值，避免状态延迟）
  const validateTestCasesWithValues = (values: typeof latestValuesRef.current): { isValid: boolean; errorMessage?: string } => {
    if (values.testCases.length === 0) {
      return { isValid: false, errorMessage: '请至少添加一个测试用例' }
    }

    // 验证示例个数不能大于用例集总数
    if (values.exampleCount > values.testCases.length) {
      return {
        isValid: false,
        errorMessage: `示例个数(${values.exampleCount})不能大于用例集总数(${values.testCases.length})`,
      }
    }

    // 从原始提示词中提取变量
    const promptVariables = extractVariablesFromPrompt(values.originalPrompt)

    for (let i = 0; i < values.testCases.length; i++) {
      const testCase = values.testCases[i]
      const caseData: any = {
        inputs: {},
        label: {},
      }

      try {
        // 尝试解析JSON格式的messages
        const jsonData = JSON.parse(testCase.messages)

        // 处理inputs字段（新格式：包含content和format）
        if (jsonData.inputs) {
          Object.keys(jsonData.inputs).forEach(key => {
            const value = jsonData.inputs[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.inputs[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }

        // 处理label字段（新格式：包含content和format）
        if (jsonData.label) {
          Object.keys(jsonData.label).forEach(key => {
            const value = jsonData.label[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.label[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }
      } catch (error) {
        // 如果不是JSON格式，抛出错误
        return {
          isValid: false,
          errorMessage: `第${i + 1}个用例格式错误：无法解析JSON格式`,
        }
      }

      // 验证规则1和2：inputs变量名验证
      const inputKeys = Object.keys(caseData.inputs)

      if (promptVariables.length > 0) {
        // 规则1：如果原始提示词有{{variable}}，inputs变量名要一一对应
        if (inputKeys.length !== promptVariables.length) {
          return {
            isValid: false,
            errorMessage: `第${i + 1}个用例的inputs变量数量不匹配。提示词中有${promptVariables.length}个变量，但用例中有${inputKeys.length}个inputs变量`,
          }
        }

        for (const promptVar of promptVariables) {
          if (!inputKeys.includes(promptVar)) {
            return {
              isValid: false,
              errorMessage: `第${i + 1}个用例缺少变量"${promptVar}"，该变量在原始提示词中定义`,
            }
          }
        }

        for (const inputKey of inputKeys) {
          if (!promptVariables.includes(inputKey)) {
            return {
              isValid: false,
              errorMessage: `第${i + 1}个用例包含多余的变量"${inputKey}"，该变量不在原始提示词中`,
            }
          }
        }
      } else {
        // 规则2：如果原始提示词没有{{variable}}，inputs只能有一个变量且命名为query
        if (inputKeys.length !== 1 || inputKeys[0] !== 'query') {
          return {
            isValid: false,
            errorMessage: `第${i + 1}个用例的inputs变量不符合要求。当原始提示词没有{{variable}}时，inputs只能有一个变量且命名为"query"`,
          }
        }
      }

      // 验证规则3：label只有一个变量，命名为output或tool_calls
      const labelKeys = Object.keys(caseData.label)
      if (labelKeys.length !== 1) {
        return {
          isValid: false,
          errorMessage: `第${i + 1}个用例的label必须只有一个变量`,
        }
      }

      const labelKey = labelKeys[0]
      if (labelKey !== 'output' && labelKey !== 'tool_calls') {
        return {
          isValid: false,
          errorMessage: `第${i + 1}个用例的label变量名必须是"output"或"tool_calls"，当前是"${labelKey}"`,
        }
      }

      // 验证规则4：所有变量名长度不超过50个字符
      for (const inputKey of inputKeys) {
        if (inputKey.length > 50) {
          return {
            isValid: false,
            errorMessage: `第${i + 1}个用例的inputs变量名"${inputKey}"长度超过50个字符`,
          }
        }
      }

      if (labelKey.length > 50) {
        return {
          isValid: false,
          errorMessage: `第${i + 1}个用例的label变量名"${labelKey}"长度超过50个字符`,
        }
      }
    }

    return { isValid: true }
  }

  // 将testCases转换为用例检查API需要的格式
  const convertTestCasesToCheckFormat = (): OptimizationCase[] => {
    return testCases.map(testCase => {
      const caseData: any = {
        inputs: {},
        label: {},
      }

      try {
        // 尝试解析JSON格式的messages
        const jsonData = JSON.parse(testCase.messages)

        // 处理inputs字段（新格式：包含content和format）
        if (jsonData.inputs) {
          Object.keys(jsonData.inputs).forEach(key => {
            const value = jsonData.inputs[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.inputs[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }

        // 处理label字段（新格式：包含content和format）
        if (jsonData.label) {
          Object.keys(jsonData.label).forEach(key => {
            const value = jsonData.label[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.label[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }
      } catch (error) {
        // 如果不是JSON格式，抛出错误
        throw new Error(`Invalid test case format: ${testCase.messages}`)
      }

      return caseData
    })
  }

  // 使用指定testCases转换为用例检查API需要的格式（用于自动保存）
  const convertTestCasesToCheckFormatWithValues = (testCasesData: TestCase[]): OptimizationCase[] => {
    return testCasesData.map(testCase => {
      const caseData: any = {
        inputs: {},
        label: {},
      }

      try {
        // 尝试解析JSON格式的messages
        const jsonData = JSON.parse(testCase.messages)

        // 处理inputs字段（新格式：包含content和format）
        if (jsonData.inputs) {
          Object.keys(jsonData.inputs).forEach(key => {
            const value = jsonData.inputs[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.inputs[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }

        // 处理label字段（新格式：包含content和format）
        if (jsonData.label) {
          Object.keys(jsonData.label).forEach(key => {
            const value = jsonData.label[key]
            if (value && typeof value === 'object' && 'content' in value && 'format' in value) {
              caseData.label[key] = {
                content: value.content || '',
                format: value.format || 'PlainText',
              }
            }
          })
        }
      } catch (error) {
        // 如果不是JSON格式，抛出错误
        throw new Error(`Invalid test case format: ${testCase.messages}`)
      }

      return caseData
    })
  }

  const handleDeleteCase = (caseId: number) => {
    const newTestCases = testCases.filter(c => c.id !== caseId)
    setTestCasesWithAutoSave(newTestCases)

    // 删除用例后检查分页是否需要调整
    const newTotalPages = Math.ceil(newTestCases.length / testCaseRowsPerPage)
    if (testCasePage >= newTotalPages && newTotalPages > 0) {
      // 如果当前页超出了新的总页数，跳转到最后一页
      setTestCasePage(newTotalPages - 1)
    } else if (newTestCases.length === 0) {
      // 如果删除后没有用例了，跳转到第一页
      setTestCasePage(0)
    }
  }

  // 获取模型列表
  const fetchModels = async () => {
    setModelsLoading(true)
    try {
      const response = await PromptModelService.getModelsList({
        scenario: 'prompt_debug',
        pageSize: 100,
        pageToken: '0',
        workspaceId: workspaceId,
      })

      if (response.code === 0) {
        setModels(response.models)

        // 设置默认选中的模型（只在新建模式下，且没有选中模型时才自动选择）
        if (response.models.length > 0 && !isEditMode && !selectedOptimizeModel) {
          const defaultModel = response.models[0]
          setSelectedOptimizeModel(defaultModel)
          setSelectedRunModel(defaultModel)

          // 使用modelService的辅助方法获取默认参数
          const defaultParams = PromptModelService.getModelDefaultParams(defaultModel)
          setOptimizeModelParams(defaultParams)
          setRunModelParams(defaultParams)
        }
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
    } finally {
      setModelsLoading(false)
    }
  }

  // 处理模型选择变化
  const handleModelChange = (modelName: string, type: 'optimize' | 'run') => {
    const model = models.find(m => m.openModel.name === modelName)
    if (model) {
      if (type === 'optimize') {
        // 使用普通的setter，避免重复触发自动保存
        setSelectedOptimizeModel(model)
        // 使用modelService的辅助方法获取默认参数
        const defaultParams = PromptModelService.getModelDefaultParams(model)
        setOptimizeModelParams(defaultParams)
        // 更新ref中的值
        latestValuesRef.current.selectedOptimizeModel = model
        latestValuesRef.current.optimizeModelParams = defaultParams
      } else {
        // 使用普通的setter，避免重复触发自动保存
        setSelectedRunModel(model)
        // 使用modelService的辅助方法获取默认参数
        const defaultParams = PromptModelService.getModelDefaultParams(model)
        setRunModelParams(defaultParams)
        // 更新ref中的值
        latestValuesRef.current.selectedRunModel = model
        latestValuesRef.current.runModelParams = defaultParams
      }
      // 只在最后触发一次自动保存
      triggerAutoSave()
    }
  }

  // 工具操作回调函数
  const handleAddTool = () => {
    // 创建新工具
    const newTool: EditingTool = {
      id: '', // 新工具暂时没有ID
      name: '',
      description: '',
      defaultValue: '',
      fieldType: 'PlainText',
      parameters: [],
    }
    setEditingTool(newTool)
    setToolEditDialogOpen(true)
  }

  const handleEditTool = (tool: Tool) => {
    // 将Tool转换为EditingTool格式，保留parametersJsonSchema和parametersMode
    const editingTool: EditingTool = {
      id: tool.id,
      name: tool.name,
      description: tool.description,
      defaultValue: tool.defaultValue || '',
      fieldType: tool.fieldType || 'PlainText',
      parameters: tool.parameters,
      parametersJsonSchema: tool.parametersJsonSchema, // 保留JSON Schema，用于在对话框中自动切换到JSON模式
      parametersMode: tool.parametersMode, // 保留参数模式
    }
    setEditingTool(editingTool)
    setToolEditDialogOpen(true)
  }

  const handleDeleteTool = (toolId: string) => {
    const newTools = tools.filter(t => t.id !== toolId)
    setTools(newTools)
    triggerAutoSave()
  }

  const handleToolsChange = (newTools: Tool[]) => {
    setTools(newTools)
    triggerAutoSave()
  }

  const handleToolsEnabledChange = (enabled: boolean) => {
    setToolsEnabled(enabled)
    triggerAutoSave()
  }

  // 创建工具设置的回调函数，用于传递给ToolSettingsPanel
  const handleToolHasUnsavedChanges = (hasChanges: boolean) => {
    // 这里可以添加未保存更改的处理逻辑
  }

  const handleToolTriggerAutoSave = (data?: any) => {
    triggerAutoSave()
  }

  // 工具编辑对话框处理函数
  const handleToolEditDialogClose = () => {
    setToolEditDialogOpen(false)
    setEditingTool(null)
  }

  const handleToolEditDialogSave = (updatedEditingTool: EditingTool) => {
    // 使用传入的更新后的工具对象，而不是状态中的editingTool
    // 这样可以确保获取到最新的数据，特别是JSON模式下保存的parametersJsonSchema
    if (!updatedEditingTool || !updatedEditingTool.name.trim()) {
      showSnackbar('请输入工具名称', 'error')
      return
    }

    // 判断是新增还是编辑：检查原始工具是否有id（空字符串或undefined表示新增）
    const isNewTool = !updatedEditingTool.id || updatedEditingTool.id.trim() === ''

    // 工具名称重复检查函数
    const checkToolNameDuplicate = (toolList: Tool[], toolName: string, excludeToolId?: string): boolean => {
      return toolList.some(tool => {
        // 编辑模式下，排除当前编辑的工具本身
        if (excludeToolId && tool.id === excludeToolId) {
          return false
        }
        // 比较工具名称（区分大小写）
        return tool.name.trim() === toolName.trim()
      })
    }

    // 检查工具名称是否重复
    if (isNewTool) {
      // 新增工具：检查名称是否已存在
      if (checkToolNameDuplicate(tools, updatedEditingTool.name.trim())) {
        showSnackbar('工具名称已存在，请重新命名', 'error')
        return
      }
    } else {
      // 编辑工具：检查名称是否与其他工具重复（排除当前编辑的工具）
      if (checkToolNameDuplicate(tools, updatedEditingTool.name.trim(), updatedEditingTool.id)) {
        showSnackbar('工具名称已存在，请重新命名', 'error')
        return
      }
    }

    // 生成新的工具ID（如果是新工具）
    const toolId = updatedEditingTool.id || `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // 创建Tool对象，保留parametersJsonSchema和parametersMode
    const newTool: Tool = {
      id: toolId,
      name: updatedEditingTool.name.trim(),
      description: updatedEditingTool.description.trim(),
      defaultValue: updatedEditingTool.defaultValue,
      fieldType: updatedEditingTool.fieldType,
      parameters: updatedEditingTool.parameters,
      parametersJsonSchema: updatedEditingTool.parametersJsonSchema, // 保存JSON Schema，用于保留高级特性
      parametersMode: updatedEditingTool.parametersMode, // 保存参数模式
    }

    // 更新工具列表
    let newTools: Tool[]
    if (updatedEditingTool.id) {
      // 编辑现有工具
      newTools = tools.map(t => (t.id === updatedEditingTool.id ? newTool : t))
      showSnackbar('工具更新成功', 'success')
    } else {
      // 添加新工具
      newTools = [...tools, newTool]
      showSnackbar('工具添加成功', 'success')
    }

    setTools(newTools)
    triggerAutoSave()
    handleToolEditDialogClose()
  }

  const handleEditingToolChange = (tool: EditingTool | null) => {
    setEditingTool(tool)
  }

  // Excel文件格式验证函数
  const validateExcelFormat = (data: any[]): { isValid: boolean; errorMessage?: string } => {
    if (!data || data.length === 0) {
      return { isValid: false, errorMessage: t('prompts.optimizeEditPage.testCases.emptyFile') }
    }

    const firstRow = data[0]
    const columns = Object.keys(firstRow)

    // 检查是否有inputs和label相关的列
    const hasInputsColumns = columns.some(col => col.startsWith('inputs_'))
    const hasLabelColumns = columns.some(col => col.startsWith('label_'))

    if (!hasInputsColumns || !hasLabelColumns) {
      return {
        isValid: false,
        errorMessage: '文件格式不正确，需要包含inputs_和label_开头的列，例如：inputs_role, inputs_query, label_output',
      }
    }

    // 检查数据格式
    for (let i = 0; i < data.length; i++) {
      const row = data[i]

      // 检查inputs相关字段
      const inputsColumns = columns.filter(col => col.startsWith('inputs_'))
      for (const col of inputsColumns) {
        if (row[col] === undefined || row[col] === null || row[col] === '') {
          return {
            isValid: false,
            errorMessage: `第${i + 1}行的${col}字段不能为空`,
          }
        }
      }

      // 检查label相关字段
      const labelColumns = columns.filter(col => col.startsWith('label_'))
      for (const col of labelColumns) {
        if (row[col] === undefined || row[col] === null || row[col] === '') {
          return {
            isValid: false,
            errorMessage: `第${i + 1}行的${col}字段不能为空`,
          }
        }
      }
    }

    return { isValid: true }
  }

  // 将Excel数据转换为TestCase格式
  const convertExcelToTestCases = (excelData: any[]): TestCase[] => {
    const testCases: TestCase[] = []
    let id = 1

    excelData.forEach(row => {
      const columns = Object.keys(row)

      // 分离inputs和label列
      const inputsColumns = columns.filter(col => col.startsWith('inputs_'))
      const labelColumns = columns.filter(col => col.startsWith('label_'))

      const inputs: any = {}
      const label: any = {}

      // 处理inputs列（新格式：content + format）
      if (inputsColumns.length > 0) {
        inputsColumns.forEach(col => {
          const variableName = col.replace('inputs_', '') // 去掉前缀获取变量名
          inputs[variableName] = {
            content: row[col] || '',
            format: 'PlainText',
          }
        })
      }

      // 处理label列（新格式：content + format）
      if (labelColumns.length > 0) {
        labelColumns.forEach(col => {
          const variableName = col.replace('label_', '') // 去掉前缀获取变量名
          label[variableName] = {
            content: row[col] || '',
            format: 'PlainText',
          }
        })
      }

      // 只有当有inputs和label数据时才创建测试用例
      if (Object.keys(inputs).length > 0 && Object.keys(label).length > 0) {
        const caseData = {
          inputs: inputs,
          label: label,
        }

        testCases.push({
          id: id++,
          messages: JSON.stringify(caseData, null, 2),
        })
      }
    })

    return testCases
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 检查文件类型
    const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    const isCsv = file.name.endsWith('.csv')

    if (!isExcel && !isCsv) {
      showSnackbar(t('prompts.optimizeEditPage.messages.fileFormatError'), 'error')
      // 重置文件输入框，允许重新选择文件
      event.target.value = ''
      return
    }

    try {
      let jsonData: any[]

      if (isCsv) {
        // 处理CSV文件
        const text = await file.text()
        const workbook = XLSX.read(text, { type: 'string' })
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]
        jsonData = XLSX.utils.sheet_to_json(worksheet)
      } else {
        // 处理Excel文件
        const arrayBuffer = await file.arrayBuffer()
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })

        // 获取第一个工作表
        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]

        // 转换为JSON数据
        jsonData = XLSX.utils.sheet_to_json(worksheet)
      }

      // 验证数据格式
      const validation = validateExcelFormat(jsonData)
      if (!validation.isValid) {
        showSnackbar(t('prompts.optimizeEditPage.messages.datasetFormatError', { error: validation.errorMessage }), 'error')
        // 重置文件输入框，允许重新选择文件
        event.target.value = ''
        return
      }

      // 转换数据格式
      const convertedData = convertExcelToTestCases(jsonData)

      if (convertedData.length === 0) {
        showSnackbar(t('prompts.optimizeEditPage.messages.noValidData'), 'warning')
        // 重置文件输入框，允许重新选择文件
        event.target.value = ''
        return
      }

      // 检查用例数量限制
      if (convertedData.length > MAX_TEST_CASES) {
        showSnackbar(t('prompts.optimizeEditPage.messages.uploadExceedsLimit', { count: convertedData.length, max: MAX_TEST_CASES }), 'error')
        // 重置文件输入框，允许重新选择文件
        event.target.value = ''
        return
      }

      // 如果当前已有用例，询问用户是追加还是替换
      if (testCases.length > 0) {
        setPendingExcelData(convertedData)
        setUploadConfirmOpen(true)
      } else {
        // 直接替换
        setTestCasesWithAutoSave(convertedData)
        // 替换用例后跳转到第一页
        setTestCasePage(0)
        showSnackbar(t('prompts.optimizeEditPage.testCases.importSuccess', { count: convertedData.length }), 'success')
      }
    } catch (error) {
      console.error('文件解析失败:', error)
      showSnackbar(t('prompts.optimizeEditPage.messages.fileParseFailed'), 'error')
    }

    // 重置文件输入
    event.target.value = ''
  }

  // 处理上传确认对话框
  const handleUploadConfirm = () => {
    if (uploadMode === 'append') {
      // 追加模式：检查总数量限制
      const totalCount = testCases.length + pendingExcelData.length
      if (totalCount > MAX_TEST_CASES) {
        showSnackbar(
          t('prompts.optimizeEditPage.messages.appendExceedsLimit', {
            current: testCases.length,
            adding: pendingExcelData.length,
            total: totalCount,
            max: MAX_TEST_CASES,
          }),
          'error',
        )
        return
      }

      // 生成新的ID并添加到现有用例
      const maxId = Math.max(...testCases.map(tc => tc.id), 0)
      const updatedData = pendingExcelData.map((tc, index) => ({
        ...tc,
        id: maxId + index + 1,
      }))
      setTestCasesWithAutoSave([...testCases, ...updatedData])
      showSnackbar(`成功追加${pendingExcelData.length}个用例`, 'success')
    } else {
      // 替换模式：直接替换所有用例
      setTestCasesWithAutoSave(pendingExcelData)
      // 替换用例后跳转到第一页
      setTestCasePage(0)
      showSnackbar(`成功替换为${pendingExcelData.length}个用例`, 'success')
    }

    setUploadConfirmOpen(false)
    setPendingExcelData([])
  }

  const handleUploadCancel = () => {
    setUploadConfirmOpen(false)
    setPendingExcelData([])
  }

  const handleCopyPrompt = async (text: string) => {
    try {
      await copyToClipboard(text, setSnackbar, t('prompts.optimizeEditPage.messages.copiedToClipboard'))
    } catch (error) {
      console.error('复制失败:', error)
    }
  }

  const handleShowDetail = (type: 'original' | 'optimized', iterationRound: number = 0) => {
    setDetailDialogType(type)
    setDetailDialogIterationRound(iterationRound)
    setDetailDialogPageNum(1) // 重置为第一页
    setEvaluateCases([]) // 清空之前的数据，避免显示旧数据
    setDetailDialogOpen(true)
  }

  const handleApplyOptimization = () => {
    if (!editorPromptId || !currentOptimizedPrompt) {
      console.error('Missing editorPromptId or currentOptimizedPrompt')
      return
    }

    const optimizedData = {
      content: currentOptimizedPrompt,
      fromOptimization: true,
    }

    sessionStorage.setItem('optimizedPromptData', JSON.stringify(optimizedData))

    navigate(`/dashboard/prompts/${editorPromptId}`)
  }

  // 获取评测数据（从API返回的数据转换为表格显示格式）
  const getEvaluationData = () => {
    if (!evaluateCases || evaluateCases.length === 0) {
      return []
    }

    return evaluateCases.map(evalCase => {
      // 用户输入：直接展示原始JSON
      const userInput = JSON.stringify(evalCase.case.inputs, null, 2)

      // 参照回答：优先展示tool_calls，如果为空则展示output
      let referenceAnswer = ''
      const labelToolCalls = (evalCase.case.label as any)?.tool_calls
      if (labelToolCalls && Array.isArray(labelToolCalls) && labelToolCalls.length > 0) {
        // 如果有tool_calls，只取第一个，删除id、type、index字段后展示JSON
        const firstToolCall = labelToolCalls[0]
        const cleaned: any = { ...firstToolCall }
        // 删除可能存在的字段
        if ('id' in cleaned) delete cleaned.id
        if ('type' in cleaned) delete cleaned.type
        if ('index' in cleaned) delete cleaned.index
        referenceAnswer = JSON.stringify(cleaned, null, 2)
      } else {
        // 否则展示output
        referenceAnswer = evalCase.case.label?.output || ''
      }

      // 模型回答：优先展示tool_calls，如果为空则展示output
      let modelAnswer = ''
      if (evalCase.answer.tool_calls && evalCase.answer.tool_calls.length > 0) {
        // 如果有tool_calls，只取第一个，删除id、type、index字段后展示JSON
        const firstToolCall = evalCase.answer.tool_calls[0]
        const cleaned: any = { ...firstToolCall }
        // 删除可能存在的字段
        if ('id' in cleaned) delete cleaned.id
        if ('type' in cleaned) delete cleaned.type
        if ('index' in cleaned) delete cleaned.index
        modelAnswer = JSON.stringify(cleaned, null, 2)
      } else {
        // 否则展示output
        modelAnswer = evalCase.answer.output || ''
      }

      // 模型评分
      const score = Math.round(evalCase.score * 100) // 将0-1的分数转换为0-100

      // 评分原因
      const reason = evalCase.reason || ''

      return {
        userInput,
        modelAnswer,
        referenceAnswer,
        score,
        reason,
      }
    })
  }

  // 获取当前显示的提示词
  const currentOptimizedPrompt = useMemo(() => {
    if (!optimizedPrompt || optimizedVersions.length === 0) return ''
    return optimizedVersions[currentOptimizedVersion] || ''
  }, [currentOptimizedVersion, optimizedPrompt, optimizedVersions])

  return (
    <div
      className={`w-full bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40 ${isNewDashboard ? 'py-6' : ''}`}
      style={{ height: '100%', overflowX: 'auto' }}
    >
      {/* 页面容器 */}
      <div style={{ margin: '0 auto', minWidth: '1100px', height: '100%' }}>
        {/* 页面头部 */}
        <div
          className="flex items-center bg-white/60 backdrop-blur-sm border border-gray-200/60 shadow-sm"
          style={{
            padding: 'clamp(0.5rem, 0.6vw, 0.875rem)',
            minHeight: 'clamp(3.5rem, 4.5vh, 4rem)',
            minWidth: 'fit-content',
            width: '100%',
          }}
        >
          <IconButton
            onClick={handleBack}
            className="hover:bg-gray-100/80 transition-colors duration-200"
            sx={{
              width: 'clamp(1.75rem, 2vw, 2.25rem)',
              height: 'clamp(1.75rem, 2vw, 2.25rem)',
              '&:hover': {
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                transform: 'translateX(-2px)',
              },
              transition: 'all 0.2s ease',
            }}
          >
            <ArrowLeft
              className="text-gray-600"
              style={{
                width: 'clamp(0.875rem, 1vw, 1.125rem)',
                height: 'clamp(0.875rem, 1vw, 1.125rem)',
              }}
            />
          </IconButton>
          <div
            className="flex items-center flex-1 min-w-0"
            style={{
              gap: 'clamp(0.375rem, 0.5vw, 0.5rem)',
              marginLeft: 'clamp(0.5rem, 0.8vw, 0.875rem)',
            }}
          >
            <div className="min-w-0" style={{ maxWidth: '50%', flex: '0 1 auto' }}>
              <ConditionalTooltip title={isEditMode ? taskName || t('prompts.optimizeEditPage.common.editTask') : t('prompts.optimizeEditPage.common.newTask')}>
                <h1
                  className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent truncate"
                  style={{
                    fontSize: 'clamp(0.875rem, 0.85vw, 1.125rem)',
                    lineHeight: 1.5,
                  }}
                >
                  {isEditMode ? taskName || t('prompts.optimizeEditPage.common.editTask') : t('prompts.optimizeEditPage.common.newTask')}
                </h1>
              </ConditionalTooltip>
              <ConditionalTooltip
                title={
                  isEditMode
                    ? description || t('prompts.optimizeEditPage.basicInfo.editDescription')
                    : t('prompts.optimizeEditPage.basicInfo.createDescription')
                }
              >
                <p
                  className="text-gray-600 truncate"
                  style={{
                    fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                    marginTop: 'clamp(0.125rem, 0.1vh, 0.1875rem)',
                    lineHeight: 1.6,
                  }}
                >
                  {isEditMode
                    ? description || t('prompts.optimizeEditPage.basicInfo.editDescription')
                    : t('prompts.optimizeEditPage.basicInfo.createDescription')}
                </p>
              </ConditionalTooltip>
            </div>
          </div>

          <div
            className="flex items-center"
            style={{
              gap: 'clamp(0.5rem, 1vw, 1rem)',
            }}
          >
            {/* 自动保存状态指示器 */}
            <div
              className="flex items-center text-gray-500"
              style={{
                gap: 'clamp(0.375rem, 0.7vw, 0.625rem)',
              }}
            >
              {isSavingDraft ? (
                <>
                  <CircularProgress
                    size={16}
                    className="text-blue-600"
                    sx={{
                      width: 'clamp(0.875rem, 1vw, 1rem) !important',
                      height: 'clamp(0.875rem, 1vw, 1rem) !important',
                    }}
                  />
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {t('prompts.optimizeEditPage.common.autoSaving')}
                  </Typography>
                </>
              ) : lastSavedTime ? (
                <>
                  <CheckCircle
                    style={{
                      width: 'clamp(0.875rem, 1vw, 1rem)',
                      height: 'clamp(0.875rem, 1vw, 1rem)',
                    }}
                    className="text-green-500"
                  />
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {t('prompts.optimizeEditPage.common.saved')} {lastSavedTime.toLocaleTimeString()}
                  </Typography>
                </>
              ) : (
                <Typography
                  variant="body2"
                  className="text-gray-400"
                  sx={{
                    fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {t('prompts.optimizeEditPage.common.autoSaveHint')}
                </Typography>
              )}
            </div>
            <Button
              variant="contained"
              startIcon={
                isCreatingJob ? (
                  <CircularProgress
                    sx={{
                      width: 'clamp(0.75rem, 0.75vw, 0.9375rem) !important',
                      height: 'clamp(0.75rem, 0.75vw, 0.9375rem) !important',
                      color: 'white',
                    }}
                  />
                ) : (
                  <Play style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />
                )
              }
              onClick={handleStartOptimization}
              disabled={isCreatingJob}
              sx={{
                background: isCreatingJob ? 'linear-gradient(135deg, #9ca3af 0%, #6b7280 100%)' : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)',
                },
                '&:disabled': {
                  background: 'linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%)',
                  color: '#6b7280',
                },
                transition: 'all 0.2s ease',
                borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                textTransform: 'none',
                fontWeight: 600,
                boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)',
              }}
            >
              {isCreatingJob ? t('prompts.optimizeEditPage.common.creating') : t('prompts.optimizeEditPage.startOptimization')}
            </Button>
          </div>
        </div>

        {/* 主体内容 - 三列布局 */}
        <div className="resizable-columns-container flex" style={{ minWidth: '1100px', height: contentHeight }}>
          {/* Column 1: 基本信息 */}
          <div
            style={{
              width: `${visibleModules.actualWidths[0]}%`,
              minWidth: '320px',
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
              overflowY: 'auto',
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
            }}
            className="flex flex-col h-full"
          >
            {/* 隐藏滚动条（Webkit） */}
            <style>{`.basic-info-scroll::-webkit-scrollbar { display: none; }`}</style>
            <Card className="h-full shadow-sm border-0 bg-white/60 backdrop-blur-sm flex flex-col" sx={{ borderRadius: 0 }}>
              <CardContent
                className="flex-1 flex flex-col overflow-hidden"
                sx={{
                  padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                }}
              >
                <div
                  className="flex items-center justify-between"
                  style={{
                    marginBottom: 'clamp(0.375rem, 1.5vh, 1rem)',
                  }}
                >
                  <div
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                    }}
                  >
                    <div
                      className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-sm"
                      style={{
                        padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                      }}
                    >
                      <FileText
                        className="text-white"
                        style={{
                          width: 'clamp(0.5rem, 1vw, 1rem)',
                          height: 'clamp(0.5rem, 1vw, 1rem)',
                        }}
                      />
                    </div>
                    <Typography
                      variant="h6"
                      className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                      sx={{
                        fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                        lineHeight: 1.3,
                      }}
                    >
                      {t('prompts.optimizeEditPage.basicInfo.title')}
                    </Typography>
                  </div>

                  {/* 展开其他模块的按钮 */}
                  <div
                    className="flex items-center"
                    style={{
                      gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                    }}
                  >
                    {moduleCollapsed.optimizationConfig && (
                      <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.expand')}>
                        <IconButton
                          size="small"
                          onClick={() => toggleModuleCollapse('optimizationConfig')}
                          className="text-gray-400 hover:text-blue-600"
                          sx={{
                            width: 'clamp(1.25rem, 2.5vw, 2rem)',
                            height: 'clamp(1.25rem, 2.5vw, 2rem)',
                            '&:hover': {
                              backgroundColor: '#eff6ff',
                            },
                          }}
                        >
                          <Settings
                            style={{
                              width: 'clamp(0.625rem, 1.2vw, 1rem)',
                              height: 'clamp(0.625rem, 1.2vw, 1rem)',
                            }}
                          />
                        </IconButton>
                      </Tooltip>
                    )}

                    {moduleCollapsed.optimizationResult && (
                      <Tooltip title={t('prompts.optimizeEditPage.optimizationResult.expand')}>
                        <IconButton
                          size="small"
                          onClick={() => toggleModuleCollapse('optimizationResult')}
                          className="text-gray-400 hover:text-blue-600"
                          sx={{
                            width: 'clamp(1.25rem, 2.5vw, 2rem)',
                            height: 'clamp(1.25rem, 2.5vw, 2rem)',
                            '&:hover': {
                              backgroundColor: '#eff6ff',
                            },
                          }}
                        >
                          <BarChart
                            style={{
                              width: 'clamp(0.625rem, 1.2vw, 1rem)',
                              height: 'clamp(0.625rem, 1.2vw, 1rem)',
                            }}
                          />
                        </IconButton>
                      </Tooltip>
                    )}
                  </div>
                </div>
                {/* 基本信息主体内容：单独做一个可滚动区域，隐藏滚动条 */}
                <div
                  className="flex-1 flex flex-col basic-info-scroll"
                  style={{
                    overflowY: 'auto',
                    scrollbarWidth: 'none',
                    msOverflowStyle: 'none',
                    gap: 'clamp(0.5rem, 1.5vw, 1rem)',
                  }}
                >
                  {/* 任务信息配置 */}
                  <div
                    className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60 flex-shrink-0"
                    style={{
                      padding: 'clamp(0.5rem, 1.5vw, 1rem)',
                      gap: 'clamp(0.5rem, 1.5vw, 1rem)',
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                  >
                    <Typography
                      variant="subtitle1"
                      className="font-bold text-gray-800 flex items-center flex-shrink-0"
                      style={{
                        marginBottom: 'clamp(0.375rem, 1vh, 0.75rem)',
                        gap: 'clamp(0.375rem, 0.75vw, 0.75rem)',
                      }}
                      sx={{
                        fontSize: 'clamp(0.75rem, 1vw, 1rem)',
                        lineHeight: 1.4,
                      }}
                    >
                      <Settings
                        className="text-blue-600"
                        style={{
                          width: 'clamp(0.875rem, 1.2vw, 1.25rem)',
                          height: 'clamp(0.875rem, 1.2vw, 1.25rem)',
                        }}
                      />
                      <span>{t('prompts.optimizeEditPage.basicInfo.taskInfo')}</span>
                    </Typography>
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'clamp(0.5rem, 1vw, 0.75rem)',
                      }}
                    >
                      {/* 提示词选择下拉框 */}
                      {!isEditMode && (
                        <Autocomplete
                          fullWidth
                          size="small"
                          value={selectedPrompt}
                          onChange={(event, newValue) => handlePromptSelect(newValue)}
                          options={promptList}
                          loading={promptListLoading}
                          getOptionLabel={option => `${option.prompt_key} - ${option.name}`}
                          renderOption={(props, option) => (
                            <li {...props}>
                              <div>
                                <Typography
                                  variant="body2"
                                  fontWeight="medium"
                                  sx={{
                                    fontSize: 'clamp(0.7rem, 1.5vw, 0.875rem)',
                                  }}
                                >
                                  {option.prompt_key}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  sx={{
                                    fontSize: 'clamp(0.6rem, 1.25vw, 0.75rem)',
                                  }}
                                >
                                  {option.name}
                                </Typography>
                              </div>
                            </li>
                          )}
                          renderInput={params => (
                            <TextField
                              {...params}
                              label={t('prompts.optimizeEditPage.basicInfo.selectPrompt')}
                              placeholder={t('prompts.optimizeEditPage.basicInfo.selectPromptPlaceholder')}
                              className="bg-white"
                              sx={{
                                '& .MuiInputLabel-root': {
                                  fontSize: 'clamp(0.65rem, 1.5vw, 0.875rem)',
                                },
                                '& .MuiOutlinedInput-root': {
                                  '& input': {
                                    fontSize: 'clamp(0.7rem, 1.5vw, 0.875rem)',
                                  },
                                },
                              }}
                              InputProps={{
                                ...params.InputProps,
                                endAdornment: (
                                  <>
                                    {promptListLoading ? <CircularProgress color="inherit" size={20} /> : null}
                                    {params.InputProps.endAdornment}
                                  </>
                                ),
                              }}
                            />
                          )}
                        />
                      )}

                      <TextField
                        fullWidth
                        label={t('prompts.optimizeEditPage.basicInfo.taskName')}
                        value={taskName}
                        onChange={e => setTaskNameWithAutoSave(e.target.value)}
                        placeholder={t('prompts.optimizeEditPage.basicInfo.taskNamePlaceholder')}
                        required
                        size="small"
                        className="bg-white"
                        inputProps={{ maxLength: 32 }}
                        sx={{
                          '& .MuiInputLabel-root': {
                            fontSize: 'clamp(0.65rem, 1.5vw, 0.875rem)',
                          },
                          '& .MuiOutlinedInput-root': {
                            position: 'relative',
                            '& input': {
                              paddingRight: '60px',
                              fontSize: 'clamp(0.7rem, 1.5vw, 0.875rem)',
                            },
                          },
                        }}
                        InputProps={{
                          endAdornment: (
                            <Box sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                              <Typography
                                variant="caption"
                                sx={{ color: taskName.length >= 32 ? '#ef4444' : '#6b7280', fontSize: 'clamp(0.6rem, 1.25vw, 0.75rem)' }}
                              >
                                {taskName.length}/32
                              </Typography>
                            </Box>
                          ),
                        }}
                      />

                      <TextField
                        fullWidth
                        label={t('prompts.optimizeEditPage.basicInfo.taskDescription')}
                        value={description}
                        onChange={e => setDescriptionWithAutoSave(e.target.value)}
                        placeholder={t('prompts.optimizeEditPage.basicInfo.taskDescriptionPlaceholder')}
                        size="small"
                        multiline
                        rows={3}
                        className="bg-white"
                        inputProps={{ maxLength: 256 }}
                        sx={{
                          '& .MuiInputLabel-root': {
                            fontSize: 'clamp(0.65rem, 1.5vw, 0.875rem)',
                          },
                          '& .MuiOutlinedInput-root': {
                            position: 'relative',
                            '& textarea': {
                              paddingRight: '60px',
                              marginBottom: '10px',
                              fontSize: 'clamp(0.7rem, 1.5vw, 0.875rem)',
                            },
                          },
                        }}
                        InputProps={{
                          endAdornment: (
                            <Box sx={{ position: 'absolute', right: 8, bottom: 0, pointerEvents: 'none' }}>
                              <Typography
                                variant="caption"
                                sx={{ color: description.length >= 256 ? '#ef4444' : '#6b7280', fontSize: 'clamp(0.6rem, 1.25vw, 0.75rem)' }}
                              >
                                {description.length}/256
                              </Typography>
                            </Box>
                          ),
                        }}
                      />
                    </div>
                  </div>

                  <Divider className="flex-shrink-0" />

                  {/* Original Prompt */}
                  <div
                    className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60 flex flex-col flex-shrink-0"
                    style={{
                      padding: 'clamp(0.5rem, 1.5vw, 1rem)',
                    }}
                  >
                    <Typography
                      variant="subtitle1"
                      className="font-bold text-gray-800 flex items-center flex-shrink-0 relative"
                      style={{
                        marginBottom: 'clamp(0.375rem, 1vh, 0.75rem)',
                        gap: 'clamp(0.375rem, 0.75vw, 0.75rem)',
                      }}
                      sx={{
                        fontSize: 'clamp(0.75rem, 1vw, 1rem)',
                        lineHeight: 1.4,
                      }}
                    >
                      <Zap
                        className="text-indigo-600"
                        style={{
                          width: 'clamp(0.875rem, 1.2vw, 1.25rem)',
                          height: 'clamp(0.875rem, 1.2vw, 1.25rem)',
                        }}
                      />
                      <span>{t('prompts.optimizeEditPage.basicInfo.originalPrompt')}</span>
                      <span
                        className="text-gray-700"
                        style={{
                          marginLeft: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                        }}
                      >
                        *
                      </span>
                    </Typography>
                    <div style={{ height: 'clamp(0.5rem, 1vh, 1rem)' }}></div>
                    <div
                      className="flex flex-col"
                      style={{
                        minHeight: 'clamp(400px, 50vh, 660px)',
                      }}
                    >
                      <FormattedPromptEditor
                        fullWidth
                        placeholder={t('prompts.optimizeEditPage.basicInfo.originalPromptPlaceholder')}
                        value={originalPrompt}
                        onChange={value => setOriginalPromptWithAutoSave(value)}
                        className="bg-white"
                        sx={{
                          flex: 1,
                          minHeight: 'clamp(200px, 25vh, 350px)',
                          '& .cm-editor': {
                            height: '100%',
                            minHeight: 'clamp(200px, 25vh, 350px)',
                          },
                          '& .cm-scroller': {
                            overflow: 'auto',
                          },
                          '& .cm-content': {
                            overflow: 'auto',
                          },
                        }}
                      />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 第一个拖动分界线 - 当优化配置显示时显示 */}
          {!moduleCollapsed.optimizationConfig && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 0 ? 'from-blue-500 to-blue-600 shadow-sm' : ''
              }`}
              onMouseDown={handleColumnMouseDown(0)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-sm border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* 基本信息和优化结果之间的分界线 - 当优化配置收起但优化结果显示时显示 */}
          {moduleCollapsed.optimizationConfig && !moduleCollapsed.optimizationResult && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 0 ? 'from-blue-500 to-blue-600 shadow-sm' : ''
              }`}
              onMouseDown={handleColumnMouseDown(0)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-sm border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* Column 2: 优化配置 */}
          {!moduleCollapsed.optimizationConfig && (
            <div
              style={{
                width: `${visibleModules.actualWidths[1]}%`,
                minWidth: '360px',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                overflowY: 'auto',
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
              }}
              className="flex flex-col h-full"
            >
              <Card className="h-full shadow-sm border-0 bg-white/60 backdrop-blur-sm flex flex-col" sx={{ borderRadius: 0 }}>
                <CardContent
                  className="flex-1 flex flex-col overflow-hidden min-h-0"
                  sx={{
                    padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                  }}
                >
                  <div
                    className="flex items-center justify-between"
                    style={{
                      marginBottom: 'clamp(0.1rem, 0.25vh, 0.2rem)',
                    }}
                  >
                    <div
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                      }}
                    >
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg shadow-sm"
                        style={{
                          padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                        }}
                      >
                        <Settings
                          className="text-white"
                          style={{
                            width: 'clamp(0.5rem, 1vw, 1rem)',
                            height: 'clamp(0.5rem, 1vw, 1rem)',
                          }}
                        />
                      </div>
                      <Typography
                        variant="h6"
                        className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                        sx={{
                          fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                          lineHeight: 1.3,
                        }}
                      >
                        {t('prompts.optimizeEditPage.optimizationConfig.title')}
                      </Typography>
                    </div>
                    <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.collapse')}>
                      <IconButton
                        size="small"
                        onClick={() => toggleModuleCollapse('optimizationConfig')}
                        className="text-gray-400 hover:text-gray-600"
                        sx={{
                          width: 'clamp(1.25rem, 2.5vw, 2rem)',
                          height: 'clamp(1.25rem, 2.5vw, 2rem)',
                        }}
                      >
                        <ChevronUp
                          style={{
                            width: 'clamp(0.625rem, 1.2vw, 1rem)',
                            height: 'clamp(0.625rem, 1.2vw, 1rem)',
                          }}
                        />
                      </IconButton>
                    </Tooltip>
                  </div>
                  {/* 优化结果主体内容：单独做一个可滚动区域，隐藏滚动条 */}
                  <style>{`.optimization-result-scroll::-webkit-scrollbar { display: none; }`}</style>
                  <div
                    className="flex-1 flex flex-col optimization-result-scroll min-h-0"
                    style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                  >
                    {/* Tab标签 */}
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                      <Tabs
                        value={optimizationConfigTab}
                        onChange={(e, newValue) => setOptimizationConfigTab(newValue)}
                        aria-label={t('prompts.optimizeEditPage.optimizationConfig.title')}
                        className="bg-white/60 rounded-t-lg"
                        variant="scrollable"
                        scrollButtons="auto"
                        allowScrollButtonsMobile
                        sx={{
                          minHeight: 'clamp(2rem, 5.5vh, 2.75rem)',
                          height: 'clamp(2rem, 5.5vh, 2.75rem)',
                          '& .MuiTabs-flexContainer': {
                            height: '100%',
                          },
                          '& .MuiTab-root': {
                            fontSize: 'clamp(0.625rem, 1.5vw, 0.8125rem)',
                            padding: 'clamp(0.3rem, 1vw, 0.6rem) clamp(0.375rem, 1.5vw, 0.75rem)',
                            minHeight: 'clamp(2rem, 5.5vh, 2.75rem)',
                          },
                          '& .MuiTabs-scroller': {
                            overflowX: 'auto',
                            scrollbarWidth: 'none',
                            msOverflowStyle: 'none',
                            '&::-webkit-scrollbar': {
                              display: 'none',
                            },
                          },
                        }}
                      >
                        <Tab
                          label={
                            <div
                              className="flex items-center"
                              style={{
                                gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                              }}
                            >
                              <FileText
                                style={{
                                  width: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                  height: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationConfig.testCasesConfig')}</span>
                              <Chip
                                label={testCases.length}
                                size="small"
                                className="bg-blue-100 text-blue-700"
                                sx={{
                                  fontSize: 'clamp(0.5rem, 1.2vw, 0.6875rem)',
                                  height: 'clamp(0.875rem, 2vh, 1.125rem)',
                                }}
                              />
                            </div>
                          }
                        />
                        <Tab
                          label={
                            <div
                              className="flex items-center"
                              style={{
                                gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                              }}
                            >
                              <Brain
                                style={{
                                  width: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                  height: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationConfig.optimizationStrategy')}</span>
                            </div>
                          }
                        />
                        <Tab
                          label={
                            <div
                              className="flex items-center"
                              style={{
                                gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                              }}
                            >
                              <BarChart
                                style={{
                                  width: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                  height: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationConfig.evaluationCriteria')}</span>
                            </div>
                          }
                        />
                        <Tab
                          label={
                            <div
                              className="flex items-center"
                              style={{
                                gap: 'clamp(0.25rem, 0.5vw, 0.375rem)',
                              }}
                            >
                              <Code
                                style={{
                                  width: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                  height: 'clamp(0.625rem, 1.5vw, 0.875rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationConfig.toolSettings')}</span>
                              <Chip
                                label={tools.length}
                                size="small"
                                className="bg-green-100 text-green-700"
                                sx={{
                                  fontSize: 'clamp(0.5rem, 1.2vw, 0.6875rem)',
                                  height: 'clamp(0.875rem, 2vh, 1.125rem)',
                                }}
                              />
                            </div>
                          }
                        />
                      </Tabs>
                    </Box>

                    {/* Tab内容区域 */}
                    <div
                      className="flex-1 bg-gradient-to-r from-gray-50/50 to-slate-50/50 border border-gray-100/60 border-t-0 rounded-b-lg"
                      style={{
                        overflowY: 'auto',
                        scrollbarWidth: 'none',
                        msOverflowStyle: 'none',
                        padding: 'clamp(0.25rem, 1vw, 1rem)',
                      }}
                    >
                      {/* 隐藏滚动条（Webkit） */}
                      <style>{`
                      .optimization-tab-scroll::-webkit-scrollbar { display: none; }
                    `}</style>
                      {/* 用例集配置 Tab */}
                      <div
                        role="tabpanel"
                        hidden={optimizationConfigTab !== 0}
                        className="h-full optimization-tab-scroll"
                        style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                      >
                        {optimizationConfigTab === 0 && (
                          <div
                            className="h-full flex flex-col optimization-tab-scroll"
                            style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                          >
                            <div
                              className="flex flex-col"
                              style={{
                                gap: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                              }}
                            >
                              {/* 操作按钮 */}
                              <div
                                className="flex flex-shrink-0 items-center flex-wrap"
                                style={{
                                  gap: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                }}
                              >
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={
                                    <Plus
                                      style={{
                                        width: 'clamp(0.5rem, 1vw, 1rem)',
                                        height: 'clamp(0.5rem, 1vw, 1rem)',
                                      }}
                                    />
                                  }
                                  onClick={handleAddCase}
                                  disabled={testCases.length >= MAX_TEST_CASES}
                                  className="border-blue-300 text-blue-700 whitespace-nowrap"
                                  sx={{
                                    whiteSpace: 'nowrap',
                                    minWidth: 'auto',
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                    padding: 'clamp(0.125rem, 0.4vw, 0.375rem) clamp(0.25rem, 0.8vw, 0.75rem)',
                                    minHeight: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  }}
                                >
                                  {t('prompts.optimizeEditPage.testCases.add')}
                                </Button>
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={
                                    <Upload
                                      style={{
                                        width: 'clamp(0.5rem, 1vw, 1rem)',
                                        height: 'clamp(0.5rem, 1vw, 1rem)',
                                      }}
                                    />
                                  }
                                  component="label"
                                  className="border-blue-300 text-blue-700 whitespace-nowrap"
                                  sx={{
                                    whiteSpace: 'nowrap',
                                    minWidth: 'auto',
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                    padding: 'clamp(0.125rem, 0.4vw, 0.375rem) clamp(0.25rem, 0.8vw, 0.75rem)',
                                    minHeight: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  }}
                                >
                                  {t('prompts.optimizeEditPage.common.uploadFile')}
                                  <input type="file" hidden accept=".xlsx,.xls,.csv" onChange={handleFileUpload} />
                                </Button>
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={
                                    <Trash
                                      style={{
                                        width: 'clamp(0.5rem, 1vw, 1rem)',
                                        height: 'clamp(0.5rem, 1vw, 1rem)',
                                      }}
                                    />
                                  }
                                  onClick={handleClearCases}
                                  className="border-red-300 text-red-700 hover:bg-red-50 whitespace-nowrap"
                                  disabled={testCases.length === 0}
                                  sx={{
                                    whiteSpace: 'nowrap',
                                    minWidth: 'auto',
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                    padding: 'clamp(0.125rem, 0.4vw, 0.375rem) clamp(0.25rem, 0.8vw, 0.75rem)',
                                    minHeight: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  }}
                                >
                                  {t('prompts.optimizeEditPage.testCases.clear')}
                                </Button>
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={
                                    <Download
                                      style={{
                                        width: 'clamp(0.5rem, 1vw, 1rem)',
                                        height: 'clamp(0.5rem, 1vw, 1rem)',
                                      }}
                                    />
                                  }
                                  onClick={handleDownloadSample}
                                  className="border-green-300 text-green-700 hover:bg-green-50 whitespace-nowrap"
                                  sx={{
                                    whiteSpace: 'nowrap',
                                    minWidth: 'auto',
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                    padding: 'clamp(0.125rem, 0.4vw, 0.375rem) clamp(0.25rem, 0.8vw, 0.75rem)',
                                    minHeight: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  }}
                                >
                                  {t('prompts.optimizeEditPage.testCases.downloadExample')}
                                </Button>
                                {/* 用例数量显示 */}
                                <div
                                  className="ml-auto flex items-center flex-shrink-0"
                                  style={{
                                    gap: 'clamp(0.125rem, 0.3vw, 0.5rem)',
                                  }}
                                >
                                  <Typography
                                    variant="body2"
                                    className="font-medium text-gray-600 whitespace-nowrap"
                                    sx={{
                                      fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                    }}
                                  >
                                    {t('prompts.optimizeEditPage.testCases.count', {
                                      max: MAX_TEST_CASES,
                                    })}
                                  </Typography>
                                </div>
                              </div>

                              {/* 用例表格 */}
                              <div
                                className="flex flex-col"
                                style={{
                                  minHeight: 'clamp(200px, 30vh, 300px)',
                                }}
                              >
                                <TableContainer
                                  className="bg-white rounded border border-gray-200"
                                  style={{
                                    overflowX: 'auto',
                                    overflowY: 'auto',
                                    minHeight: 'clamp(200px, 30vh, 300px)',
                                    width: '100%',
                                  }}
                                >
                                  <Table size="small" stickyHeader sx={{ minWidth: 'clamp(300px, 50vw, 400px)' }}>
                                    <TableHead>
                                      <TableRow>
                                        <TableCell
                                          width="60"
                                          className="bg-gray-50 font-medium"
                                          sx={{
                                            minWidth: 'clamp(40px, 8vw, 60px)',
                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                            padding: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                          }}
                                        >
                                          编号
                                        </TableCell>
                                        <TableCell
                                          className="bg-gray-50 font-medium"
                                          sx={{
                                            minWidth: 'clamp(150px, 25vw, 200px)',
                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                            padding: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                          }}
                                        >
                                          用例
                                        </TableCell>
                                        <TableCell
                                          width="80"
                                          align="center"
                                          className="bg-gray-50 font-medium"
                                          sx={{
                                            minWidth: 'clamp(80px, 15vw, 120px)',
                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                            padding: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                          }}
                                        >
                                          {t('prompts.optimizeEditPage.testCases.actions')}
                                        </TableCell>
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {testCases
                                        .slice(testCasePage * testCaseRowsPerPage, testCasePage * testCaseRowsPerPage + testCaseRowsPerPage)
                                        .map(testCase => (
                                          <TableRow key={testCase.id} hover>
                                            <TableCell
                                              sx={{
                                                fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                                padding: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                              }}
                                            >
                                              {testCase.id}
                                            </TableCell>
                                            <TableCell
                                              className="cursor-pointer hover:bg-gray-50"
                                              onClick={() => handleViewCase(testCase)}
                                              sx={{
                                                fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                                padding: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                              }}
                                            >
                                              <div
                                                className="max-w-none overflow-hidden"
                                                style={{
                                                  minWidth: 'clamp(150px, 25vw, 200px)',
                                                }}
                                              >
                                                {(() => {
                                                  const formattedCase = formatTestCaseForDisplay(testCase)
                                                  const isLongContent = formattedCase.length > 200
                                                  const displayContent = isLongContent ? formattedCase.substring(0, 200) + '...' : formattedCase

                                                  return isLongContent ? (
                                                    <Tooltip
                                                      title={
                                                        <pre
                                                          className="whitespace-pre-wrap font-mono overflow-auto"
                                                          style={{
                                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                                            maxWidth: 'clamp(200px, 40vw, 400px)',
                                                            maxHeight: 'clamp(200px, 50vh, 400px)',
                                                          }}
                                                        >
                                                          {formattedCase}
                                                        </pre>
                                                      }
                                                      placement="top-start"
                                                      arrow
                                                    >
                                                      <pre
                                                        className="whitespace-pre-wrap font-mono text-gray-600 break-all"
                                                        style={{
                                                          fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                                        }}
                                                      >
                                                        {displayContent}
                                                      </pre>
                                                    </Tooltip>
                                                  ) : (
                                                    <pre
                                                      className="whitespace-pre-wrap font-mono text-gray-600 break-all"
                                                      style={{
                                                        fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                                      }}
                                                    >
                                                      {displayContent}
                                                    </pre>
                                                  )
                                                })()}
                                              </div>
                                            </TableCell>
                                            <TableCell align="center" sx={{ padding: 'clamp(0.25rem, 0.5vw, 0.5rem)' }}>
                                              <Box
                                                className="flex justify-center"
                                                style={{
                                                  gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                                }}
                                              >
                                                <IconButton
                                                  size="small"
                                                  onClick={() => handleViewCase(testCase)}
                                                  title={t('prompts.optimizeEditPage.testCases.view')}
                                                  sx={{
                                                    padding: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                                    width: 'clamp(1rem, 2vw, 1.5rem)',
                                                    height: 'clamp(1rem, 2vw, 1.5rem)',
                                                  }}
                                                >
                                                  <Info
                                                    className="text-green-600"
                                                    style={{
                                                      width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                      height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                    }}
                                                  />
                                                </IconButton>
                                                <IconButton
                                                  size="small"
                                                  onClick={() => handleEditCase(testCase)}
                                                  title={t('prompts.optimizeEditPage.testCases.edit')}
                                                  sx={{
                                                    padding: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                                    width: 'clamp(1rem, 2vw, 1.5rem)',
                                                    height: 'clamp(1rem, 2vw, 1.5rem)',
                                                  }}
                                                >
                                                  <Edit
                                                    className="text-blue-600"
                                                    style={{
                                                      width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                      height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                    }}
                                                  />
                                                </IconButton>
                                                <IconButton
                                                  size="small"
                                                  onClick={() => {
                                                    const content = formatTestCaseForDisplay(testCase)
                                                    copyToClipboard(content, snackbar => {
                                                      showSnackbar(snackbar.message, snackbar.severity)
                                                    })
                                                  }}
                                                  title={t('prompts.optimizeEditPage.testCases.copy')}
                                                  sx={{
                                                    padding: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                                    width: 'clamp(1rem, 2vw, 1.5rem)',
                                                    height: 'clamp(1rem, 2vw, 1.5rem)',
                                                  }}
                                                >
                                                  <Copy
                                                    className="text-purple-600"
                                                    style={{
                                                      width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                      height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                    }}
                                                  />
                                                </IconButton>
                                                <IconButton
                                                  size="small"
                                                  onClick={() => handleDeleteCase(testCase.id)}
                                                  title={t('prompts.optimizeEditPage.testCases.delete')}
                                                  sx={{
                                                    padding: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                                    width: 'clamp(1rem, 2vw, 1.5rem)',
                                                    height: 'clamp(1rem, 2vw, 1.5rem)',
                                                  }}
                                                >
                                                  <Trash2
                                                    className="text-red-600"
                                                    style={{
                                                      width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                      height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                    }}
                                                  />
                                                </IconButton>
                                              </Box>
                                            </TableCell>
                                          </TableRow>
                                        ))}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              </div>

                              {/* 分页控件 */}
                              <div
                                className="flex items-center justify-end flex-shrink-0 border-t"
                                style={{
                                  paddingTop: 'clamp(0.25rem, 1vw, 1rem)',
                                }}
                              >
                                <div
                                  className="flex items-center flex-wrap justify-end"
                                  style={{
                                    gap: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                  }}
                                >
                                  {/* 每页显示条数 */}
                                  <div className="flex items-center whitespace-nowrap">
                                    <Typography
                                      variant="body2"
                                      className="text-gray-700"
                                      sx={{
                                        fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                      }}
                                    >
                                      {t('prompts.optimizeEditPage.pagination.itemsPerPage')}
                                    </Typography>
                                    <select
                                      value={testCaseRowsPerPage}
                                      onChange={e => {
                                        setTestCaseRowsPerPage(parseInt(e.target.value, 10))
                                        setTestCasePage(0)
                                      }}
                                      className="border border-gray-300 rounded bg-white"
                                      style={{
                                        fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                        padding: 'clamp(0.125rem, 0.3vw, 0.25rem) clamp(0.25rem, 0.5vw, 0.5rem)',
                                        margin: '0 clamp(0.125rem, 0.3vw, 0.25rem)',
                                      }}
                                    >
                                      <option value={5}>5</option>
                                      <option value={10}>10</option>
                                      <option value={15}>15</option>
                                      <option value={20}>20</option>
                                    </select>
                                    <Typography
                                      variant="body2"
                                      className="text-gray-700"
                                      sx={{
                                        fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                      }}
                                    >
                                      {t('prompts.optimizeEditPage.pagination.items')}
                                    </Typography>
                                  </div>

                                  {/* 总条数 */}
                                  <div className="flex items-center whitespace-nowrap">
                                    <Typography
                                      variant="body2"
                                      className="text-gray-700"
                                      sx={{
                                        fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                      }}
                                    >
                                      {t('prompts.optimizeEditPage.pagination.total', { count: testCases.length })}
                                    </Typography>
                                  </div>

                                  {/* 分页按钮和页码 */}
                                  <div
                                    className="flex items-center flex-shrink-0"
                                    style={{
                                      gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                    }}
                                  >
                                    <Button
                                      size="small"
                                      onClick={handleFirstPage}
                                      disabled={testCasePage === 0}
                                      className="min-w-0 p-0"
                                      sx={{
                                        width: 'clamp(1rem, 2vw, 1.5625rem)',
                                        height: 'clamp(1rem, 2vw, 1.5625rem)',
                                        minWidth: 'clamp(1rem, 2vw, 1.5625rem)',
                                      }}
                                      title={t('prompts.optimizeEditPage.pagination.firstPage')}
                                    >
                                      <ChevronsLeft
                                        style={{
                                          width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                          height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                        }}
                                      />
                                    </Button>
                                    <Button
                                      size="small"
                                      onClick={handlePrevPage}
                                      disabled={testCasePage === 0}
                                      className="min-w-0 p-0"
                                      sx={{
                                        width: 'clamp(1rem, 2vw, 1.5625rem)',
                                        height: 'clamp(1rem, 2vw, 1.5625rem)',
                                        minWidth: 'clamp(1rem, 2vw, 1.5625rem)',
                                      }}
                                      title={t('prompts.optimizeEditPage.pagination.previousPage')}
                                    >
                                      <ChevronLeft
                                        style={{
                                          width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                          height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                        }}
                                      />
                                    </Button>

                                    <div
                                      className="flex items-center text-gray-700 whitespace-nowrap"
                                      style={{
                                        margin: '0 clamp(0.125rem, 0.3vw, 0.25rem)',
                                        gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                      }}
                                    >
                                      <Typography
                                        variant="body2"
                                        sx={{
                                          fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.common.page')}
                                      </Typography>
                                      <input
                                        type="text"
                                        value={currentPageInput}
                                        onChange={handlePageInputChange}
                                        onKeyPress={handlePageInputKeyPress}
                                        onBlur={handlePageInputBlur}
                                        className="text-center border border-gray-300 rounded bg-white"
                                        style={{
                                          width: 'clamp(1.5rem, 3vw, 2rem)',
                                          fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                          padding: 'clamp(0.125rem, 0.3vw, 0.25rem) clamp(0.25rem, 0.5vw, 0.5rem)',
                                        }}
                                      />
                                      <Typography
                                        variant="body2"
                                        sx={{
                                          fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.common.of', { total: totalPages })}
                                      </Typography>
                                    </div>

                                    <Button
                                      size="small"
                                      onClick={handleNextPage}
                                      disabled={testCasePage >= totalPages - 1}
                                      className="min-w-0 p-0"
                                      sx={{
                                        width: 'clamp(1rem, 2vw, 1.5625rem)',
                                        height: 'clamp(1rem, 2vw, 1.5625rem)',
                                        minWidth: 'clamp(1rem, 2vw, 1.5625rem)',
                                      }}
                                      title={t('prompts.optimizeEditPage.pagination.nextPage')}
                                    >
                                      <ChevronRight
                                        style={{
                                          width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                          height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                        }}
                                      />
                                    </Button>
                                    <Button
                                      size="small"
                                      onClick={handleLastPage}
                                      disabled={testCasePage >= totalPages - 1}
                                      className="min-w-0 p-0"
                                      sx={{
                                        width: 'clamp(1rem, 2vw, 1.5625rem)',
                                        height: 'clamp(1rem, 2vw, 1.5625rem)',
                                        minWidth: 'clamp(1rem, 2vw, 1.5625rem)',
                                      }}
                                      title="跳转到尾页"
                                    >
                                      <ChevronsRight
                                        style={{
                                          width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                          height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                        }}
                                      />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 优化策略配置 Tab */}
                      <div
                        role="tabpanel"
                        hidden={optimizationConfigTab !== 1}
                        className="h-full optimization-tab-scroll"
                        style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                      >
                        {optimizationConfigTab === 1 && (
                          <div className="h-full flex flex-col">
                            <div
                              className="optimization-tab-scroll"
                              style={{
                                overflowY: 'auto',
                                scrollbarWidth: 'none',
                                msOverflowStyle: 'none',
                                gap: 'clamp(0.25rem, 1vw, 1rem)',
                                display: 'flex',
                                flexDirection: 'column',
                              }}
                            >
                              {/* 优化参数 */}
                              <div
                                className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60"
                                style={{
                                  padding: 'clamp(0.25rem, 1vw, 1rem)',
                                }}
                              >
                                <Typography
                                  variant="subtitle2"
                                  className="font-bold text-gray-800 flex items-center"
                                  sx={{
                                    fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                    marginBottom: 'clamp(0.25rem, 0.75vw, 0.5rem)',
                                    gap: 'clamp(0.25rem, 0.5vw, 0.75rem)',
                                  }}
                                >
                                  <Target
                                    className="text-blue-600"
                                    style={{
                                      width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                      height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                    }}
                                  />
                                  <span>优化参数</span>
                                </Typography>
                                <div style={{ height: 'clamp(0.25rem, 1vw, 1rem)' }}></div>
                                <div
                                  style={{
                                    gap: 'clamp(0.25rem, 1vw, 1rem)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                  }}
                                >
                                  {/* 示例个数 */}
                                  <SliderField
                                    label={t('prompts.optimizeEditPage.optimizationConfig.exampleCount')}
                                    tooltip={t('prompts.optimizeEditPage.optimizationConfig.exampleCountTooltip')}
                                    value={exampleCount}
                                    onChange={setExampleCountWithAutoSave}
                                    min={0}
                                    max={Math.min(testCases.length, 20)}
                                    disabled={testCases.length === 0}
                                    minLabel="0"
                                    maxLabel={Math.min(testCases.length, 20).toString()}
                                    allowZero={true}
                                  />

                                  {/* 目标准确率 */}
                                  <SliderField
                                    label={t('prompts.optimizeEditPage.optimizationConfig.targetAccuracy')}
                                    tooltip={t('prompts.optimizeEditPage.optimizationConfig.targetAccuracyTooltip')}
                                    value={targetAccuracy}
                                    onChange={setTargetAccuracyWithAutoSave}
                                    min={0}
                                    max={100}
                                    minLabel="0%"
                                    maxLabel="100%"
                                    valueLabelFormat={value => `${value}%`}
                                    inputEndAdornment={
                                      <span
                                        className="text-gray-500"
                                        style={{
                                          fontSize: 'clamp(0.5rem, 1.25vw, 0.65rem)',
                                        }}
                                      >
                                        %
                                      </span>
                                    }
                                  />

                                  {/* 优化轮次 */}
                                  <SliderField
                                    label={t('prompts.optimizeEditPage.optimizationConfig.maxRounds')}
                                    tooltip={t('prompts.optimizeEditPage.optimizationConfig.maxRoundsTooltip')}
                                    value={maxRounds}
                                    onChange={setMaxRoundsWithAutoSave}
                                    min={1}
                                    max={20}
                                  />

                                  {/* 最大并发数 */}
                                  <SliderField
                                    label={t('prompts.optimizeEditPage.optimizationConfig.llmParallel')}
                                    tooltip={t('prompts.optimizeEditPage.optimizationConfig.llmParallelTooltip')}
                                    value={llmParallel}
                                    onChange={setLlmParallelWithAutoSave}
                                    min={1}
                                    max={20}
                                  />
                                </div>
                              </div>

                              {/* 分割线 */}
                              <div
                                className="border-t border-gray-200"
                                style={{
                                  marginTop: 'clamp(0.25rem, 1vw, 1rem)',
                                  marginBottom: 'clamp(0.25rem, 1vw, 1rem)',
                                }}
                              ></div>

                              {/* 模型配置 */}
                              <div
                                className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60"
                                style={{
                                  padding: 'clamp(0.25rem, 1vw, 1rem)',
                                }}
                              >
                                <Typography
                                  variant="subtitle2"
                                  className="font-bold text-gray-800 flex items-center"
                                  sx={{
                                    fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                    marginBottom: 'clamp(0.25rem, 0.75vw, 0.5rem)',
                                    gap: 'clamp(0.25rem, 0.5vw, 0.75rem)',
                                  }}
                                >
                                  <Settings
                                    className="text-blue-600"
                                    style={{
                                      width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                      height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                    }}
                                  />
                                  <span>{t('prompts.optimizeEditPage.optimizationConfig.modelConfig')}</span>
                                </Typography>
                                <div style={{ height: 'clamp(0.25rem, 1vw, 1rem)' }}></div>
                                <div
                                  style={{
                                    gap: 'clamp(0.25rem, 1vw, 1rem)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                  }}
                                >
                                  {/* 优化模型 */}
                                  <div>
                                    <div
                                      className="flex items-center"
                                      style={{
                                        gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                        marginBottom: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                      }}
                                    >
                                      <Typography
                                        variant="subtitle2"
                                        className="text-gray-700"
                                        sx={{
                                          fontSize: 'clamp(0.625rem, 1vw, 0.875rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.optimizationConfig.optimizeModel')}
                                      </Typography>
                                      <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.optimizeModelTooltip')}>
                                        <IconButton
                                          size="small"
                                          className="text-gray-400 hover:text-gray-600 p-0"
                                          sx={{
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <HelpCircle
                                            style={{
                                              width: 'clamp(0.5rem, 1vw, 1rem)',
                                              height: 'clamp(0.5rem, 1vw, 1rem)',
                                            }}
                                          />
                                        </IconButton>
                                      </Tooltip>
                                    </div>
                                    <ModelSelector
                                      availableModels={models}
                                      selectedModel={selectedOptimizeModel}
                                      onModelChange={model => {
                                        if (model) {
                                          handleModelChange(model.openModel.name, 'optimize')
                                        }
                                      }}
                                      modelsLoading={modelsLoading}
                                      placeholder="请选择模型"
                                    />

                                    {/* 优化模型参数配置 */}
                                    {selectedOptimizeModel && (
                                      <div style={{ marginTop: 'clamp(0.25rem, 0.75vw, 0.75rem)' }}>
                                        <ModelParameterEditor
                                          selectedModel={selectedOptimizeModel}
                                          modelConfig={optimizeModelParams}
                                          onModelConfigChange={setOptimizeModelParamsWithAutoSave}
                                        />
                                      </div>
                                    )}
                                  </div>

                                  {/* 运行模型 */}
                                  <div>
                                    <div
                                      className="flex items-center"
                                      style={{
                                        gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                        marginBottom: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                      }}
                                    >
                                      <Typography
                                        variant="subtitle2"
                                        className="text-gray-700"
                                        sx={{
                                          fontSize: 'clamp(0.625rem, 1vw, 0.875rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.optimizationConfig.runModel')}
                                      </Typography>
                                      <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.runModelTooltip')}>
                                        <IconButton
                                          size="small"
                                          className="text-gray-400 hover:text-gray-600 p-0"
                                          sx={{
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <HelpCircle
                                            style={{
                                              width: 'clamp(0.5rem, 1vw, 1rem)',
                                              height: 'clamp(0.5rem, 1vw, 1rem)',
                                            }}
                                          />
                                        </IconButton>
                                      </Tooltip>
                                    </div>
                                    <ModelSelector
                                      availableModels={models}
                                      selectedModel={selectedRunModel}
                                      onModelChange={model => {
                                        if (model) {
                                          handleModelChange(model.openModel.name, 'run')
                                        }
                                      }}
                                      modelsLoading={modelsLoading}
                                      placeholder="请选择模型"
                                    />

                                    {/* 运行模型参数配置 */}
                                    {selectedRunModel && (
                                      <div style={{ marginTop: 'clamp(0.25rem, 0.75vw, 0.75rem)' }}>
                                        <ModelParameterEditor
                                          selectedModel={selectedRunModel}
                                          modelConfig={runModelParams}
                                          onModelConfigChange={setRunModelParamsWithAutoSave}
                                        />
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 评价标准配置 Tab */}
                      <div
                        role="tabpanel"
                        hidden={optimizationConfigTab !== 2}
                        className="h-full optimization-tab-scroll"
                        style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                      >
                        {optimizationConfigTab === 2 && (
                          <div
                            className="flex flex-col"
                            style={{
                              gap: 'clamp(0.125rem, 0.3vw, 0.25rem)',
                            }}
                          >
                            {/* 评价类型选择 */}
                            <div
                              className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60"
                              style={{
                                padding: 'clamp(0.25rem, 1vw, 1rem)',
                              }}
                            >
                              <Typography
                                variant="subtitle2"
                                className="font-bold text-gray-800 flex items-center"
                                sx={{
                                  fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                  marginBottom: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                                  gap: 'clamp(0.25rem, 0.5vw, 0.75rem)',
                                }}
                              >
                                <Settings
                                  className="text-blue-600"
                                  style={{
                                    width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                    height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                  }}
                                />
                                <span>{t('prompts.optimizeEditPage.optimizationConfig.evaluationType')}</span>
                              </Typography>
                              <div style={{ height: 'clamp(0.25rem, 1vw, 1rem)' }}></div>
                              <RadioGroup
                                row
                                value={evaluationType}
                                onChange={e => setEvaluationTypeWithAutoSave(e.target.value)}
                                sx={{
                                  gap: 'clamp(0.5rem, 1.5vw, 1.5rem)',
                                }}
                              >
                                <FormControlLabel
                                  value="objective"
                                  control={<Radio size="small" />}
                                  label={
                                    <div
                                      className="flex items-center"
                                      style={{
                                        gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                      }}
                                    >
                                      <Typography
                                        variant="subtitle2"
                                        className="text-gray-700"
                                        sx={{
                                          fontSize: 'clamp(0.625rem, 1vw, 0.875rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.evaluationType.objective')}
                                      </Typography>
                                      <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.objectiveTooltip')}>
                                        <IconButton
                                          size="small"
                                          className="p-0"
                                          sx={{
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <HelpCircle
                                            className="text-gray-400"
                                            style={{
                                              width: 'clamp(0.5rem, 1vw, 1rem)',
                                              height: 'clamp(0.5rem, 1vw, 1rem)',
                                            }}
                                          />
                                        </IconButton>
                                      </Tooltip>
                                    </div>
                                  }
                                />
                                <FormControlLabel
                                  value="subjective"
                                  control={<Radio size="small" />}
                                  label={
                                    <div
                                      className="flex items-center"
                                      style={{
                                        gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                      }}
                                    >
                                      <Typography
                                        variant="subtitle2"
                                        className="text-gray-700"
                                        sx={{
                                          fontSize: 'clamp(0.625rem, 1vw, 0.875rem)',
                                        }}
                                      >
                                        {t('prompts.optimizeEditPage.evaluationType.subjective')}
                                      </Typography>
                                      <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.subjectiveTooltip')}>
                                        <IconButton
                                          size="small"
                                          className="p-0"
                                          sx={{
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <HelpCircle
                                            className="text-gray-400"
                                            style={{
                                              width: 'clamp(0.5rem, 1vw, 1rem)',
                                              height: 'clamp(0.5rem, 1vw, 1rem)',
                                            }}
                                          />
                                        </IconButton>
                                      </Tooltip>
                                    </div>
                                  }
                                />
                              </RadioGroup>
                            </div>

                            {/* 分割线 */}
                            <div
                              className="border-t border-gray-200"
                              style={{
                                marginTop: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                marginBottom: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                              }}
                            ></div>

                            {/* 评价标准 */}
                            <div
                              className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60 flex flex-col flex-shrink-0"
                              style={{
                                minHeight: 'clamp(250px, 40vh, 350px)',
                                padding: 'clamp(0.25rem, 1vw, 1rem)',
                              }}
                            >
                              <div
                                className="flex items-center justify-between flex-shrink-0"
                                style={{
                                  marginBottom: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                                }}
                              >
                                <div
                                  className="flex items-center"
                                  style={{
                                    gap: 'clamp(0.25rem, 0.5vw, 0.75rem)',
                                  }}
                                >
                                  <Typography
                                    variant="subtitle2"
                                    className="font-bold text-gray-800 flex items-center"
                                    sx={{
                                      fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                      gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                    }}
                                  >
                                    <BarChart
                                      className="text-blue-600"
                                      style={{
                                        width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                        height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                      }}
                                    />
                                    <span>{t('prompts.optimizeEditPage.optimizationConfig.evaluationCriteriaLabel')}</span>
                                  </Typography>
                                  <Tooltip
                                    title={t('prompts.optimizeEditPage.optimizationConfig.evaluationCriteriaTooltip', {
                                      type:
                                        evaluationType === 'objective'
                                          ? t('prompts.optimizeEditPage.evaluationType.objective')
                                          : t('prompts.optimizeEditPage.evaluationType.subjective'),
                                    })}
                                  >
                                    <IconButton
                                      size="small"
                                      className="text-gray-400 hover:text-gray-600 p-0"
                                      sx={{
                                        width: 'clamp(1rem, 2vw, 1.5rem)',
                                        height: 'clamp(1rem, 2vw, 1.5rem)',
                                      }}
                                    >
                                      <HelpCircle
                                        style={{
                                          width: 'clamp(0.5rem, 1vw, 1rem)',
                                          height: 'clamp(0.5rem, 1vw, 1rem)',
                                        }}
                                      />
                                    </IconButton>
                                  </Tooltip>
                                </div>
                              </div>
                              <div
                                className="flex flex-col"
                                style={{
                                  minHeight: 'clamp(200px, 30vh, 300px)',
                                }}
                              >
                                <TextField
                                  fullWidth
                                  multiline
                                  rows={12}
                                  value={evaluationCriteria}
                                  onChange={e => setEvaluationCriteriaWithAutoSave(e.target.value)}
                                  placeholder={
                                    evaluationType === 'objective'
                                      ? t('prompts.optimizeEditPage.optimizationConfig.objectiveCriteriaPlaceholder')
                                      : t('prompts.optimizeEditPage.optimizationConfig.subjectiveCriteriaPlaceholder')
                                  }
                                  size="small"
                                  className="bg-white"
                                  sx={{
                                    '& .MuiInputBase-root': {
                                      alignItems: 'flex-start',
                                      fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                    },
                                    '& .MuiInputBase-input': {
                                      overflow: 'auto !important',
                                      padding: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                                    },
                                  }}
                                />
                              </div>
                            </div>

                            {/* 分割线 */}
                            <div
                              className="border-t border-gray-200"
                              style={{
                                marginTop: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                marginBottom: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                              }}
                            ></div>

                            {/* 背景知识 */}
                            <div
                              className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60 flex flex-col flex-shrink-0"
                              style={{
                                minHeight: 'clamp(250px, 40vh, 350px)',
                                padding: 'clamp(0.25rem, 1vw, 1rem)',
                              }}
                            >
                              <div
                                className="flex items-center flex-shrink-0"
                                style={{
                                  gap: 'clamp(0.25rem, 0.5vw, 0.75rem)',
                                  marginBottom: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                                }}
                              >
                                <Typography
                                  variant="subtitle2"
                                  className="font-bold text-gray-800 flex items-center"
                                  sx={{
                                    fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                    gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                  }}
                                >
                                  <Info
                                    className="text-blue-600"
                                    style={{
                                      width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                      height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                    }}
                                  />
                                  <span>{t('prompts.optimizeEditPage.optimizationConfig.backgroundKnowledge')}</span>
                                </Typography>
                                <Tooltip title={t('prompts.optimizeEditPage.optimizationConfig.backgroundKnowledgeTooltip')}>
                                  <IconButton
                                    size="small"
                                    className="text-gray-400 hover:text-gray-600 p-0"
                                    sx={{
                                      width: 'clamp(1rem, 2vw, 1.5rem)',
                                      height: 'clamp(1rem, 2vw, 1.5rem)',
                                    }}
                                  >
                                    <HelpCircle
                                      style={{
                                        width: 'clamp(0.5rem, 1vw, 1rem)',
                                        height: 'clamp(0.5rem, 1vw, 1rem)',
                                      }}
                                    />
                                  </IconButton>
                                </Tooltip>
                              </div>
                              <div
                                className="flex flex-col"
                                style={{
                                  minHeight: 'clamp(200px, 30vh, 300px)',
                                }}
                              >
                                <TextField
                                  fullWidth
                                  multiline
                                  rows={12}
                                  value={backgroundKnowledge}
                                  onChange={e => setBackgroundKnowledgeWithAutoSave(e.target.value)}
                                  placeholder={t('prompts.optimizeEditPage.optimizationConfig.backgroundKnowledgePlaceholder')}
                                  size="small"
                                  className="bg-white"
                                  sx={{
                                    '& .MuiInputBase-root': {
                                      alignItems: 'flex-start',
                                      fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                    },
                                    '& .MuiInputBase-input': {
                                      overflow: 'auto !important',
                                      padding: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                                    },
                                  }}
                                />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 工具设置配置 Tab */}
                      <div
                        role="tabpanel"
                        hidden={optimizationConfigTab !== 3}
                        className="h-full optimization-tab-scroll"
                        style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                      >
                        {optimizationConfigTab === 3 && (
                          <div className="h-full optimization-tab-scroll" style={{ overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                            <ToolSettingsPanel
                              tools={tools}
                              toolsEnabled={toolsEnabled}
                              onToolsChange={handleToolsChange}
                              onToolsEnabledChange={handleToolsEnabledChange}
                              onAddTool={handleAddTool}
                              onEditTool={handleEditTool}
                              onDeleteTool={handleDeleteTool}
                              onHasUnsavedChanges={handleToolHasUnsavedChanges}
                              onTriggerAutoSave={handleToolTriggerAutoSave}
                              enableAutoSave={true}
                              isReadOnly={false}
                              showDefaultValue={false}
                              showToolFunctionHint={false}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 第二个拖动分界线 - 当优化配置显示且优化结果也显示时显示 */}
          {!moduleCollapsed.optimizationConfig && (
            <div
              className={`w-1 bg-gradient-to-b from-gray-200/60 to-gray-300/60 hover:from-blue-400 hover:to-blue-500 cursor-col-resize transition-all duration-300 relative group ${
                isDraggingColumn === 1 ? 'from-blue-500 to-blue-600 shadow-sm' : ''
              }`}
              onMouseDown={handleColumnMouseDown(1)}
            >
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 bg-white/90 backdrop-blur-sm rounded-lg shadow-sm border border-gray-200/60">
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full mr-0.5"></div>
                <div className="w-0.5 h-6 bg-gradient-to-b from-gray-400 to-gray-500 rounded-full ml-0.5"></div>
              </div>
            </div>
          )}

          {/* Column 3: 优化结果 */}
          {!moduleCollapsed.optimizationResult && (
            <div
              style={{
                width: `${visibleModules.actualWidths[2]}%`,
                minWidth: '320px',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
              }}
              className="flex flex-col h-full"
            >
              <Card className="h-full shadow-sm border-0 bg-white/60 backdrop-blur-sm flex flex-col" sx={{ borderRadius: 0 }}>
                <CardContent
                  className="flex-1 flex flex-col overflow-hidden min-h-0"
                  sx={{
                    padding: 'clamp(0.2rem, 1vw, 1.5rem) !important',
                  }}
                >
                  <div
                    className="flex items-center justify-between flex-shrink-0"
                    style={{
                      marginBottom: 'clamp(0.375rem, 1.5vh, 1rem)',
                    }}
                  >
                    <div
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.5vw, 0.625rem)',
                      }}
                    >
                      <div
                        className="bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg shadow-sm"
                        style={{
                          padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                        }}
                      >
                        <BarChart
                          className="text-white"
                          style={{
                            width: 'clamp(0.5rem, 1vw, 1rem)',
                            height: 'clamp(0.5rem, 1vw, 1rem)',
                          }}
                        />
                      </div>
                      <Typography
                        variant="h6"
                        className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
                        sx={{
                          fontSize: 'clamp(0.625rem, 1.2vw, 1.125rem)',
                          lineHeight: 1.3,
                        }}
                      >
                        {t('prompts.optimizeEditPage.optimizationResult.title')}
                      </Typography>
                    </div>

                    {/* 收起按钮 */}
                    <Tooltip title={t('prompts.optimizeEditPage.optimizationResult.collapse')}>
                      <IconButton
                        size="small"
                        onClick={() => toggleModuleCollapse('optimizationResult')}
                        className="text-gray-400 hover:text-gray-600"
                        sx={{
                          width: 'clamp(1.25rem, 2.5vw, 2rem)',
                          height: 'clamp(1.25rem, 2.5vw, 2rem)',
                        }}
                      >
                        <ChevronUp
                          style={{
                            width: 'clamp(0.625rem, 1.2vw, 1rem)',
                            height: 'clamp(0.625rem, 1.2vw, 1rem)',
                          }}
                        />
                      </IconButton>
                    </Tooltip>
                  </div>
                  {/* 优化结果主体内容：单独做一个可滚动区域，隐藏滚动条 */}
                  <style>{`.optimization-result-scroll::-webkit-scrollbar { display: none; }`}</style>
                  <div
                    className="flex-1 flex flex-col optimization-result-scroll min-h-0"
                    style={{
                      overflowY: 'auto',
                      scrollbarWidth: 'none',
                      msOverflowStyle: 'none',
                    }}
                  >
                    {/* 错误信息卡片 - 当任务失败时显示 */}
                    {taskStatus === 'failed' && (
                      <div
                        className="flex-shrink-0"
                        style={{
                          marginBottom: 'clamp(0.25rem, 1vw, 1rem)',
                        }}
                      >
                        <Card
                          sx={{
                            backgroundColor: '#fef2f2',
                            border: '1px solid #fecaca',
                            borderRadius: 'clamp(0.5rem, 1.5vw, 0.75rem)',
                          }}
                        >
                          <CardContent
                            sx={{
                              padding: 'clamp(0.25rem, 1vw, 1rem) !important',
                            }}
                          >
                            <div
                              className="flex items-start"
                              style={{
                                gap: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                              }}
                            >
                              <div
                                className="flex-shrink-0"
                                style={{
                                  marginTop: 'clamp(0.0625rem, 0.125vw, 0.125rem)',
                                }}
                              >
                                <X
                                  className="text-red-600"
                                  style={{
                                    width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                    height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                  }}
                                />
                              </div>
                              <div className="flex-1">
                                <Typography
                                  variant="subtitle1"
                                  className="font-bold text-red-800"
                                  sx={{
                                    fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                    marginBottom: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                  }}
                                >
                                  任务执行失败
                                </Typography>
                                <Typography
                                  variant="body2"
                                  className="text-red-700 whitespace-pre-wrap break-words"
                                  sx={{
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                  }}
                                >
                                  {errorMsg ? `失败原因：${errorMsg}` : '暂无失败原因'}
                                </Typography>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    )}
                    {optimizationHistory && optimizationHistory.length > 0 ? (
                      <div
                        className="flex flex-col"
                        style={{
                          gap: 'clamp(0.25rem, 1vw, 1rem)',
                        }}
                      >
                        {/* 优化评分趋势 */}
                        <div
                          className="bg-gradient-to-r from-gray-50/50 to-slate-50/50 rounded-xl border border-gray-100/60 flex-shrink-0"
                          style={{
                            padding: 'clamp(0.25rem, 1vw, 1rem)',
                          }}
                        >
                          <div
                            className="flex items-center justify-between"
                            style={{
                              marginBottom: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                            }}
                          >
                            <Typography
                              variant="subtitle1"
                              className="font-bold text-gray-800 flex items-center"
                              sx={{
                                fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                gap: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                              }}
                            >
                              <TrendingUp
                                className="text-amber-600"
                                style={{
                                  width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                  height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationResult.scoreTrend')}</span>
                            </Typography>
                            <IconButton
                              size="small"
                              onClick={() => setIsChartFullscreen(true)}
                              className="text-gray-500 hover:text-blue-600"
                              sx={{
                                width: 'clamp(1.25rem, 2.5vw, 2rem)',
                                height: 'clamp(1.25rem, 2.5vw, 2rem)',
                              }}
                            >
                              <Maximize2
                                style={{
                                  width: 'clamp(0.5rem, 1vw, 1rem)',
                                  height: 'clamp(0.5rem, 1vw, 1rem)',
                                }}
                              />
                            </IconButton>
                          </div>
                          <Box
                            className="bg-white rounded"
                            sx={{
                              height: 'clamp(120px, 20vh, 180px)',
                              width: '100%',
                              minWidth: 0,
                              minHeight: 'clamp(120px, 20vh, 180px)',
                              padding: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                            }}
                          >
                            {optimizationHistory && optimizationHistory.length > 0 ? (
                              <ResponsiveContainer width="100%" height="100%" minHeight={120}>
                                <LineChart
                                  data={optimizationHistory.map(item => ({
                                    round: t('prompts.optimizeEditPage.optimizationConfig.round', { round: item.round }),
                                    score: item.score,
                                  }))}
                                  margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
                                >
                                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                                  <XAxis dataKey="round" tick={{ fontSize: 'clamp(8px, 1.5vw, 12px)' }} stroke="#666" />
                                  <YAxis domain={[0, 100]} tick={{ fontSize: 'clamp(8px, 1.5vw, 12px)' }} stroke="#666" />
                                  <RechartsTooltip
                                    contentStyle={{
                                      backgroundColor: 'white',
                                      border: '1px solid #e0e0e0',
                                      borderRadius: '4px',
                                      fontSize: 'clamp(10px, 1.5vw, 12px)',
                                    }}
                                  />
                                  <Line
                                    type="monotone"
                                    dataKey="score"
                                    stroke="#2196f3"
                                    strokeWidth={2}
                                    dot={{ fill: '#2196f3', strokeWidth: 2, r: 4 }}
                                    activeDot={{ r: 6 }}
                                    connectNulls={false}
                                  />
                                </LineChart>
                              </ResponsiveContainer>
                            ) : (
                              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                                <Typography
                                  variant="body2"
                                  color="text.secondary"
                                  sx={{
                                    fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                  }}
                                >
                                  暂无数据
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        </div>

                        <Divider className="flex-shrink-0" />

                        {/* 提示词对比 */}
                        <div
                          className="bg-gradient-to-r from-slate-50/50 to-gray-50/50 rounded-xl border border-slate-100/60 flex flex-col flex-shrink-0"
                          style={{
                            padding: 'clamp(0.25rem, 1vw, 1rem)',
                          }}
                        >
                          <div
                            className="flex items-center justify-between flex-shrink-0"
                            style={{
                              marginBottom: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                            }}
                          >
                            <Typography
                              variant="subtitle1"
                              className="font-bold text-gray-800 flex items-center"
                              sx={{
                                fontSize: 'clamp(0.625rem, 1.1vw, 0.875rem)',
                                gap: 'clamp(0.25rem, 0.75vw, 0.75rem)',
                              }}
                            >
                              <Zap
                                className="text-amber-600"
                                style={{
                                  width: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                  height: 'clamp(0.75rem, 1.5vw, 1.25rem)',
                                }}
                              />
                              <span>{t('prompts.optimizeEditPage.optimizationResult.promptComparison')}</span>
                            </Typography>
                            <Box
                              className="flex items-center"
                              style={{
                                gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                              }}
                            >
                              <IconButton
                                size="small"
                                onClick={() => {
                                  // 循环切换：如果在第一轮，切换到最后一轮
                                  if (currentOptimizedVersion === 0) {
                                    setCurrentOptimizedVersion(optimizedVersions.length - 1)
                                  } else {
                                    setCurrentOptimizedVersion(currentOptimizedVersion - 1)
                                  }
                                }}
                                disabled={optimizedVersions.length <= 1}
                                sx={{
                                  width: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  height: 'clamp(1.25rem, 2.5vw, 2rem)',
                                }}
                              >
                                <ChevronLeft
                                  style={{
                                    width: 'clamp(0.5rem, 1vw, 1rem)',
                                    height: 'clamp(0.5rem, 1vw, 1rem)',
                                  }}
                                />
                              </IconButton>
                              <Typography
                                variant="caption"
                                className="text-gray-600"
                                sx={{
                                  fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                  padding: '0 clamp(0.125rem, 0.5vw, 0.5rem)',
                                }}
                              >
                                {t('prompts.optimizeEditPage.optimizationConfig.currentRound', {
                                  current: currentOptimizedVersion + 1,
                                  total: optimizedVersions.length,
                                })}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => {
                                  // 循环切换：如果在最后一轮，切换到第一轮
                                  if (currentOptimizedVersion >= optimizedVersions.length - 1) {
                                    setCurrentOptimizedVersion(0)
                                  } else {
                                    setCurrentOptimizedVersion(currentOptimizedVersion + 1)
                                  }
                                }}
                                disabled={optimizedVersions.length <= 1}
                                sx={{
                                  width: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  height: 'clamp(1.25rem, 2.5vw, 2rem)',
                                }}
                              >
                                <ChevronRight
                                  style={{
                                    width: 'clamp(0.5rem, 1vw, 1rem)',
                                    height: 'clamp(0.5rem, 1vw, 1rem)',
                                  }}
                                />
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={() => setIsComparisonFullscreen(true)}
                                className="text-gray-500 hover:text-blue-600"
                                sx={{
                                  width: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  height: 'clamp(1.25rem, 2.5vw, 2rem)',
                                  marginLeft: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                }}
                              >
                                <Maximize2
                                  style={{
                                    width: 'clamp(0.5rem, 1vw, 1rem)',
                                    height: 'clamp(0.5rem, 1vw, 1rem)',
                                  }}
                                />
                              </IconButton>
                            </Box>
                          </div>

                          <div
                            className="flex flex-col"
                            style={{
                              minHeight: 'clamp(300px, 50vh, 400px)',
                            }}
                          >
                            <Card variant="outlined" className="bg-white overflow-hidden flex flex-col">
                              {/* 标题栏 */}
                              <Box className="bg-gray-100 border-b flex-shrink-0">
                                <div className="flex w-full">
                                  {/* 左侧：原始提示词 - 50% */}
                                  <div className="w-1/2 border-r border-gray-300">
                                    <Box
                                      className="flex flex-wrap items-center"
                                      sx={{
                                        padding: 'clamp(0.25rem, 0.75vw, 0.75rem) clamp(0.25rem, 1vw, 1rem)',
                                        gap: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                      }}
                                    >
                                      <div
                                        className="flex items-center flex-wrap"
                                        style={{
                                          gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                          flex: '1 1 auto',
                                          minWidth: 0,
                                        }}
                                      >
                                        <Typography
                                          variant="subtitle2"
                                          className="font-semibold text-gray-700"
                                          sx={{
                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                            whiteSpace: 'nowrap',
                                          }}
                                        >
                                          {t('prompts.optimizeEditPage.optimizationResult.originalPrompt')}
                                        </Typography>
                                        {/* 显示第0轮的分数标签 */}
                                        {(() => {
                                          // 从原始history数据中找到第0轮的分数
                                          const roundZero = optimizationHistory.find(h => h.round === 0)
                                          if (roundZero && typeof roundZero.score === 'number') {
                                            return (
                                              <Chip
                                                label={`${roundZero.score.toFixed(2)}%`}
                                                size="small"
                                                className="bg-gray-100 text-gray-700 font-medium flex-shrink-0"
                                                sx={{
                                                  fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                  height: 'clamp(1rem, 2vw, 1.5rem)',
                                                }}
                                              />
                                            )
                                          }
                                          return null
                                        })()}
                                      </div>
                                      <Box
                                        className="flex flex-shrink-0"
                                        style={{
                                          gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                        }}
                                      >
                                        <IconButton
                                          size="small"
                                          onClick={() => handleCopyPrompt(originalPrompt)}
                                          sx={{
                                            color: '#6b7280',
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <Copy
                                            style={{
                                              width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                              height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                            }}
                                          />
                                        </IconButton>
                                        {true && (
                                          <IconButton
                                            size="small"
                                            onClick={() => handleShowDetail('original', 0)}
                                            sx={{
                                              color: '#6b7280',
                                              width: 'clamp(1rem, 2vw, 1.5rem)',
                                              height: 'clamp(1rem, 2vw, 1.5rem)',
                                            }}
                                          >
                                            <Info
                                              style={{
                                                width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                              }}
                                            />
                                          </IconButton>
                                        )}
                                      </Box>
                                    </Box>
                                  </div>

                                  {/* 右侧：优化结果 - 50% */}
                                  <div className="w-1/2">
                                    <Box
                                      className="flex flex-wrap items-center"
                                      sx={{
                                        padding: 'clamp(0.25rem, 0.75vw, 0.75rem) clamp(0.25rem, 1vw, 1rem)',
                                        gap: 'clamp(0.25rem, 0.5vw, 0.5rem)',
                                      }}
                                    >
                                      <div
                                        className="flex items-center flex-wrap"
                                        style={{
                                          gap: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                                          flex: '1 1 auto',
                                          minWidth: 0,
                                        }}
                                      >
                                        <Typography
                                          variant="subtitle2"
                                          className="font-semibold text-gray-700"
                                          sx={{
                                            fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                                            whiteSpace: 'nowrap',
                                          }}
                                        >
                                          {t('prompts.optimizeEditPage.optimizationConfig.roundResult', { round: currentOptimizedVersion + 1 })}
                                        </Typography>
                                        {/* 显示当前轮次的分数 */}
                                        {(() => {
                                          // 找到对应轮次的分数（轮次 = 索引 + 1）
                                          const currentRound = currentOptimizedVersion + 1
                                          const roundData = optimizationHistory.find(h => h.round === currentRound)
                                          if (roundData && typeof roundData.score === 'number') {
                                            return (
                                              <Chip
                                                label={`${roundData.score.toFixed(2)}%`}
                                                size="small"
                                                className="bg-blue-100 text-blue-700 font-medium flex-shrink-0"
                                                sx={{
                                                  fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                  height: 'clamp(1rem, 2vw, 1.5rem)',
                                                }}
                                              />
                                            )
                                          }
                                          return null
                                        })()}
                                        {(() => {
                                          // 检查是否是最优轮次（轮次 = 索引 + 1）
                                          const currentRound = currentOptimizedVersion + 1
                                          if (bestIteration === currentRound) {
                                            return (
                                              <Chip
                                                label={t('prompts.optimizeEditPage.optimizationResult.best')}
                                                size="small"
                                                className="flex-shrink-0"
                                                style={{
                                                  backgroundColor: '#10b981',
                                                  color: 'white',
                                                  fontWeight: 'medium',
                                                  fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                  height: 'clamp(1rem, 2vw, 1.5rem)',
                                                }}
                                              />
                                            )
                                          }
                                          return null
                                        })()}
                                      </div>
                                      <Box
                                        className="flex flex-shrink-0"
                                        style={{
                                          gap: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                        }}
                                      >
                                        {fromEditor && (
                                          <Button
                                            size="small"
                                            variant="contained"
                                            startIcon={
                                              <Check
                                                style={{
                                                  width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                  height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                }}
                                              />
                                            }
                                            onClick={handleApplyOptimization}
                                            sx={{
                                              backgroundColor: '#10b981',
                                              '&:hover': { backgroundColor: '#059669' },
                                              marginRight: 'clamp(0.125rem, 0.25vw, 0.25rem)',
                                              fontSize: 'clamp(0.5rem, 0.9vw, 0.75rem)',
                                              padding: 'clamp(0.125rem, 0.4vw, 0.375rem) clamp(0.25rem, 0.8vw, 0.75rem)',
                                              minHeight: 'clamp(1.25rem, 2.5vw, 2rem)',
                                            }}
                                          >
                                            应用
                                          </Button>
                                        )}
                                        <IconButton
                                          size="small"
                                          onClick={() => handleCopyPrompt(currentOptimizedPrompt)}
                                          sx={{
                                            color: '#6b7280',
                                            width: 'clamp(1rem, 2vw, 1.5rem)',
                                            height: 'clamp(1rem, 2vw, 1.5rem)',
                                          }}
                                        >
                                          <Copy
                                            style={{
                                              width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                              height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                            }}
                                          />
                                        </IconButton>
                                        {true && (
                                          <IconButton
                                            size="small"
                                            onClick={() => handleShowDetail('optimized', currentOptimizedVersion + 1)}
                                            sx={{
                                              color: '#059669',
                                              width: 'clamp(1rem, 2vw, 1.5rem)',
                                              height: 'clamp(1rem, 2vw, 1.5rem)',
                                            }}
                                          >
                                            <Info
                                              style={{
                                                width: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                                height: 'clamp(0.5rem, 0.8vw, 0.75rem)',
                                              }}
                                            />
                                          </IconButton>
                                        )}
                                      </Box>
                                    </Box>
                                  </div>
                                </div>
                              </Box>

                              {/* Diff 内容区 */}
                              <Box
                                className="flex-1 overflow-auto"
                                style={{
                                  minHeight: 'clamp(400px, 60vh, 580px)',
                                }}
                              >
                                <DiffViewer oldContent={historicalOriginalPrompt} newContent={currentOptimizedPrompt} />
                              </Box>
                            </Card>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 flex items-center justify-center">
                        <div className="text-center">
                          <BarChart
                            className="text-blue-300 mx-auto"
                            style={{
                              width: 'clamp(2rem, 8vw, 4rem)',
                              height: 'clamp(2rem, 8vw, 4rem)',
                              marginBottom: 'clamp(0.25rem, 1vw, 1rem)',
                            }}
                          />
                          <Typography
                            variant="h6"
                            className="text-gray-500"
                            sx={{
                              fontSize: 'clamp(0.75rem, 1.5vw, 1.125rem)',
                              marginBottom: 'clamp(0.125rem, 0.5vw, 0.5rem)',
                            }}
                          >
                            {t('prompts.optimizeEditPage.optimizationResult.noResult')}
                          </Typography>
                          <Typography
                            variant="body2"
                            className="text-gray-400"
                            sx={{
                              fontSize: 'clamp(0.5rem, 0.9vw, 0.875rem)',
                            }}
                          >
                            {taskStatus ? getStatusMessage(taskStatus) : t('prompts.optimizeEditPage.optimizationResult.completeConfigFirst')}
                          </Typography>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* 编辑用例抽屉 */}
        <Drawer
          anchor="right"
          open={editDialogOpen}
          onClose={() => setEditDialogOpen(false)}
          PaperProps={{
            sx: {
              width: '800px',
              maxWidth: '90vw',
              padding: 0,
            },
          }}
        >
          <div className="h-full flex flex-col bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
            {/* 头部 */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200/60 bg-white/60 backdrop-blur-sm">
              <div className="flex items-center space-x-4">
                <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl shadow-sm">
                  <Edit className="w-5 h-5 text-white" />
                </div>
                <div>
                  <Typography variant="h6" className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                    {isViewMode ? t('prompts.optimizeEditPage.testCaseDialog.view') : t('prompts.optimizeEditPage.testCaseDialog.edit')}
                  </Typography>
                  <div className="flex items-center space-x-2 mt-1">
                    <Typography variant="body2" className="text-gray-600">
                      {t('prompts.optimizeEditPage.testCaseDialog.caseId', { id: currentTestCase?.id })}
                    </Typography>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <IconButton
                  size="small"
                  onClick={() => setEditDialogOpen(false)}
                  sx={{
                    color: '#6b7280',
                    '&:hover': {
                      color: '#ef4444',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    },
                  }}
                >
                  <X className="w-4 h-4" />
                </IconButton>
              </div>
            </div>
            {/* 编辑表单 */}
            <div className="flex-1 p-6 space-y-6 overflow-y-auto">
              {testCaseDetails.map((detail, index) => (
                <div key={detail.id} className="bg-white/60 backdrop-blur-sm border border-gray-200/60 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between p-4 border-b border-gray-200/60 bg-gradient-to-r from-blue-50/50 to-indigo-50/50">
                    <div className="flex items-center space-x-3">
                      <Typography variant="subtitle1" className="font-semibold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        {t('prompts.optimizeEditPage.testCaseDialog.messageNumber', { number: index + 1 })}
                      </Typography>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Chip
                        label={detail.role}
                        size="small"
                        sx={{
                          backgroundColor: detail.role === 'inputs' ? '#dbeafe' : '#f0fdf4',
                          color: detail.role === 'inputs' ? '#1d4ed8' : '#15803d',
                          fontWeight: 500,
                          fontSize: '12px',
                          borderRadius: '6px',
                        }}
                      />
                      {!isViewMode && (
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteDetailRow(detail.id)}
                          sx={{
                            color: '#6b7280',
                            '&:hover': {
                              color: '#ef4444',
                              backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            },
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </IconButton>
                      )}
                    </div>
                  </div>
                  <div className="p-4 space-y-4">
                    {/* 字段类型显示 */}
                    <div>
                      <Typography variant="body2" className="text-gray-700 mb-2 font-medium">
                        字段类型
                      </Typography>
                      <TextField
                        value={detail.role}
                        size="small"
                        fullWidth
                        disabled={true}
                        sx={{
                          backgroundColor: '#f9fafb',
                          borderRadius: '8px',
                          '& .MuiOutlinedInput-root': {
                            borderRadius: '8px',
                            '& fieldset': {
                              borderColor: '#e5e7eb',
                            },
                            '&.Mui-disabled': {
                              backgroundColor: '#f9fafb',
                              '& fieldset': {
                                borderColor: '#e5e7eb',
                              },
                            },
                          },
                          '& .MuiInputBase-input.Mui-disabled': {
                            WebkitTextFillColor: '#6b7280',
                          },
                        }}
                      />
                    </div>

                    {/* 字段名称输入 */}
                    <div>
                      <Typography variant="body2" className="text-gray-700 mb-2 font-medium">
                        字段名称
                      </Typography>
                      {detail.role === 'label' ? (
                        <Select
                          value={detail.variableName || ''}
                          onChange={e => handleUpdateDetail(detail.id, 'variableName', e.target.value)}
                          size="small"
                          fullWidth
                          disabled={isViewMode}
                          displayEmpty
                          sx={{
                            backgroundColor: 'white',
                            borderRadius: '8px',
                            '& .MuiOutlinedInput-notchedOutline': {
                              borderColor: '#e5e7eb',
                            },
                            '&:hover .MuiOutlinedInput-notchedOutline': {
                              borderColor: isViewMode ? '#e5e7eb' : '#3b82f6',
                            },
                            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                              borderColor: isViewMode ? '#e5e7eb' : '#3b82f6',
                            },
                          }}
                        >
                          <MenuItem value="output">output</MenuItem>
                          <MenuItem value="tool_calls">tool_calls</MenuItem>
                        </Select>
                      ) : (
                        <TextField
                          value={detail.variableName || ''}
                          onChange={e => handleUpdateDetail(detail.id, 'variableName', e.target.value)}
                          size="small"
                          fullWidth
                          disabled={true}
                          placeholder="请输入字段名称"
                          sx={{
                            backgroundColor: '#f9fafb',
                            borderRadius: '8px',
                            '& .MuiOutlinedInput-root': {
                              borderRadius: '8px',
                              '& fieldset': {
                                borderColor: '#e5e7eb',
                              },
                              '&.Mui-disabled': {
                                backgroundColor: '#f9fafb',
                                '& fieldset': {
                                  borderColor: '#e5e7eb',
                                },
                              },
                            },
                            '& .MuiInputBase-input.Mui-disabled': {
                              WebkitTextFillColor: '#6b7280',
                            },
                          }}
                        />
                      )}
                    </div>

                    {/* 字段值输入 */}
                    <div>
                      <FieldEditor
                        label="字段值"
                        value={detail.content}
                        fieldType={detail.contentType || 'PlainText'}
                        placeholder="请输入字段值"
                        maxLength={2000}
                        showCharCount={true}
                        disabled={isViewMode}
                        allowedTypes={['PlainText', 'Code', 'JSON', 'Markdown']}
                        onValueChange={value => handleUpdateDetail(detail.id, 'content', value)}
                        onTypeChange={type => handleUpdateDetail(detail.id, 'contentType', type)}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 底部按钮 */}
            <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200/60 bg-white/60 backdrop-blur-sm">
              <Button
                variant="outlined"
                onClick={() => setEditDialogOpen(false)}
                sx={{
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                  '&:hover': {
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.05)',
                    color: '#ef4444',
                  },
                  borderRadius: '8px',
                  textTransform: 'none',
                  fontWeight: 500,
                  minWidth: '100px',
                }}
              >
                {isViewMode ? t('prompts.optimizeEditPage.testCaseDialog.close') : t('prompts.optimizeEditPage.testCaseDialog.cancel')}
              </Button>
              {isViewMode ? (
                <Button
                  variant="contained"
                  onClick={handleSwitchToEditMode}
                  startIcon={<Edit className="w-4 h-4" />}
                  sx={{
                    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)',
                      transform: 'translateY(-1px)',
                      boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
                    },
                    transition: 'all 0.2s ease',
                    borderRadius: '8px',
                    textTransform: 'none',
                    fontWeight: 600,
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                    minWidth: '100px',
                  }}
                >
                  {t('prompts.optimizeEditPage.testCaseDialog.editButton')}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  onClick={handleSaveEdit}
                  startIcon={<CheckCircle className="w-4 h-4" />}
                  sx={{
                    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)',
                      transform: 'translateY(-1px)',
                      boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
                    },
                    transition: 'all 0.2s ease',
                    borderRadius: '8px',
                    textTransform: 'none',
                    fontWeight: 600,
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                    minWidth: '100px',
                  }}
                >
                  {t('prompts.optimizeEditPage.testCaseDialog.save')}
                </Button>
              )}
            </div>
          </div>
        </Drawer>

        {/* 查看用例对话框 */}
        <Dialog open={viewDialogOpen} onClose={() => setViewDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>
            <Box className="flex items-center justify-between">
              <Typography variant="h6">{t('prompts.optimizeEditPage.testCaseDialog.view')}</Typography>
              <IconButton onClick={() => setViewDialogOpen(false)} size="small">
                <X className="w-5 h-5" />
              </IconButton>
            </Box>
          </DialogTitle>
          <DialogContent>
            <Box className="mt-2">
              <TableContainer className="border border-gray-200 rounded">
                <Table size="small">
                  <TableHead>
                    <TableRow className="bg-gray-50">
                      <TableCell width="60" className="font-medium">
                        {t('prompts.optimizeEditPage.testCaseDialog.sequenceNumberColumn')}
                      </TableCell>
                      <TableCell width="120" className="font-medium">
                        {t('prompts.optimizeEditPage.testCaseDialog.roleColumn')}
                      </TableCell>
                      <TableCell className="font-medium">{t('prompts.optimizeEditPage.testCaseDialog.contentColumn')}</TableCell>
                      <TableCell className="font-medium">{t('prompts.optimizeEditPage.testCaseDialog.variableColumn')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {testCaseDetails.map((detail, index) => (
                      <TableRow key={detail.id}>
                        <TableCell>{index + 1}</TableCell>
                        <TableCell>
                          <Chip label={detail.role} size="small" color={detail.role === 'inputs' ? 'primary' : 'default'} />
                        </TableCell>
                        <TableCell>{detail.content}</TableCell>
                        <TableCell>{detail.variableName}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setViewDialogOpen(false)} variant="contained">
              {t('prompts.optimizeEditPage.testCaseDialog.close')}
            </Button>
          </DialogActions>
        </Dialog>

        {/* 详情对话框 */}
        <EvaluationDetailDialog
          open={detailDialogOpen}
          onClose={() => {
            setDetailDialogOpen(false)
            setEvaluateCases([]) // 关闭对话框时清空数据
          }}
          type={detailDialogType}
          loading={jobHistoryLoading}
          evaluationData={getEvaluationData()}
          evaluateCases={evaluateCases}
          pageNum={detailDialogPageNum}
          pageSize={detailDialogPageSize}
          onPageChange={page => {
            setDetailDialogPageNum(page)
          }}
          onPageSizeChange={size => {
            setDetailDialogPageSize(size)
            setDetailDialogPageNum(1) // 重置为第一页
          }}
        />

        {/* 清空确认对话框 */}
        <Dialog
          open={clearConfirmOpen}
          onClose={() => setClearConfirmOpen(false)}
          aria-labelledby="clear-dialog-title"
          aria-describedby="clear-dialog-description"
        >
          <DialogTitle id="clear-dialog-title">{t('prompts.optimizeEditPage.clearDialog.title')}</DialogTitle>
          <DialogContent>
            <DialogContentText id="clear-dialog-description">{t('prompts.optimizeEditPage.clearDialog.message')}</DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setClearConfirmOpen(false)} color="primary">
              {t('prompts.optimizeEditPage.clearDialog.cancel')}
            </Button>
            <Button onClick={handleConfirmClear} color="error" variant="contained">
              {t('prompts.optimizeEditPage.clearDialog.confirm')}
            </Button>
          </DialogActions>
        </Dialog>

        {/* 上传确认对话框 */}
        <Dialog
          open={uploadConfirmOpen}
          onClose={handleUploadCancel}
          aria-labelledby="upload-confirm-dialog-title"
          aria-describedby="upload-confirm-dialog-description"
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle id="upload-confirm-dialog-title">{t('prompts.optimizeEditPage.uploadDialog.title')}</DialogTitle>
          <DialogContent>
            <DialogContentText id="upload-confirm-dialog-description" className="mb-4">
              {t('prompts.optimizeEditPage.uploadDialog.message', { existing: testCases.length, new: pendingExcelData.length })}
            </DialogContentText>

            <RadioGroup value={uploadMode} onChange={e => setUploadMode(e.target.value as 'append' | 'replace')}>
              <FormControlLabel
                value="append"
                control={<Radio />}
                label={
                  <div>
                    <div className="font-medium">{t('prompts.optimizeEditPage.uploadDialog.append')}</div>
                    <div className="text-sm text-gray-600">
                      {t('prompts.optimizeEditPage.uploadDialog.appendDescription', {
                        existing: testCases.length,
                        new: pendingExcelData.length,
                        total: testCases.length + pendingExcelData.length,
                      })}
                    </div>
                  </div>
                }
              />
              <FormControlLabel
                value="replace"
                control={<Radio />}
                label={
                  <div>
                    <div className="font-medium">{t('prompts.optimizeEditPage.uploadDialog.replace')}</div>
                    <div className="text-sm text-gray-600">
                      {t('prompts.optimizeEditPage.uploadDialog.replaceDescription', { existing: testCases.length, new: pendingExcelData.length })}
                    </div>
                  </div>
                }
              />
            </RadioGroup>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleUploadCancel} color="primary">
              {t('prompts.optimizeEditPage.uploadDialog.cancel')}
            </Button>
            <Button onClick={handleUploadConfirm} color="primary" variant="contained">
              {t('prompts.optimizeEditPage.uploadDialog.confirm')}
            </Button>
          </DialogActions>
        </Dialog>

        {/* 优化评分趋势全屏对话框 */}
        <Dialog
          open={isChartFullscreen}
          onClose={() => setIsChartFullscreen(false)}
          maxWidth={false}
          fullWidth
          PaperProps={{
            sx: {
              width: '95vw',
              height: '90vh',
              maxWidth: 'none',
              maxHeight: 'none',
            },
          }}
        >
          <DialogTitle>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-blue-600" />
                <Typography variant="h6">{t('prompts.optimizeEditPage.optimizationResult.scoreTrend')}</Typography>
              </div>
              <IconButton onClick={() => setIsChartFullscreen(false)} size="small">
                <Minimize2 className="w-5 h-5" />
              </IconButton>
            </div>
          </DialogTitle>
          <DialogContent sx={{ p: 3, height: 'calc(100% - 64px)' }}>
            <Box sx={{ width: '100%', height: '100%', minHeight: '500px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={optimizationHistory.map(item => ({
                    round: `第${item.round}轮`,
                    score: item.score,
                  }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="round" tick={{ fontSize: 14 }} stroke="#666" />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 14 }} stroke="#666" />
                  <RechartsTooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e0e0e0',
                      borderRadius: '4px',
                      fontSize: '14px',
                    }}
                  />
                  <Line type="monotone" dataKey="score" stroke="#2196f3" strokeWidth={3} dot={{ fill: '#2196f3', strokeWidth: 2, r: 6 }} activeDot={{ r: 8 }} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </DialogContent>
        </Dialog>

        {/* 提示词对比全屏对话框 */}
        <Dialog
          open={isComparisonFullscreen}
          onClose={() => setIsComparisonFullscreen(false)}
          maxWidth={false}
          fullWidth
          PaperProps={{
            sx: {
              width: '95vw',
              height: '90vh',
              maxWidth: 'none',
              maxHeight: 'none',
            },
          }}
        >
          <DialogTitle>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <GitCompare className="w-5 h-5 mr-2 text-blue-600" />
                <Typography variant="h6">{t('prompts.optimizeEditPage.optimizationResult.promptComparison')}</Typography>
              </div>
              <div className="flex items-center gap-2">
                <Box className="flex items-center gap-1">
                  <IconButton
                    size="small"
                    onClick={() => {
                      if (currentOptimizedVersion === 0) {
                        setCurrentOptimizedVersion(optimizedVersions.length - 1)
                      } else {
                        setCurrentOptimizedVersion(currentOptimizedVersion - 1)
                      }
                    }}
                    disabled={optimizedVersions.length <= 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </IconButton>
                  <Typography variant="body2" className="text-gray-600 px-2">
                    {t('prompts.optimizeEditPage.optimizationConfig.currentRound', { current: currentOptimizedVersion + 1, total: optimizedVersions.length })}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => {
                      if (currentOptimizedVersion >= optimizedVersions.length - 1) {
                        setCurrentOptimizedVersion(0)
                      } else {
                        setCurrentOptimizedVersion(currentOptimizedVersion + 1)
                      }
                    }}
                    disabled={optimizedVersions.length <= 1}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </IconButton>
                </Box>
                <IconButton onClick={() => setIsComparisonFullscreen(false)} size="small">
                  <Minimize2 className="w-5 h-5" />
                </IconButton>
              </div>
            </div>
          </DialogTitle>
          <DialogContent sx={{ p: 3, height: 'calc(100% - 64px)' }}>
            <Card variant="outlined" className="bg-white overflow-hidden h-full flex flex-col">
              {/* 标题栏 */}
              <Box className="bg-gray-100 border-b flex-shrink-0">
                <div className="flex w-full">
                  {/* 左侧：原始提示词 - 50% */}
                  <div className="w-1/2 border-r border-gray-300">
                    <Box className="px-4 py-3 flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Typography variant="subtitle2" className="font-semibold text-gray-700">
                          {t('prompts.optimizeEditPage.optimizationResult.originalPrompt')}
                        </Typography>
                        {/* 显示第0轮的分数标签 */}
                        {(() => {
                          // 从原始history数据中找到第0轮的分数
                          const roundZero = optimizationHistory.find(h => h.round === 0)
                          if (roundZero && typeof roundZero.score === 'number') {
                            return <Chip label={`${roundZero.score.toFixed(2)}%`} size="small" className="bg-gray-100 text-gray-700 font-medium" />
                          }
                          return null
                        })()}
                      </div>
                      <Box className="flex gap-1">
                        <IconButton size="small" onClick={() => handleCopyPrompt(originalPrompt)} sx={{ color: '#6b7280' }}>
                          <Copy className="w-3 h-3" />
                        </IconButton>
                        {true && (
                          <IconButton size="small" onClick={() => handleShowDetail('original', 0)} sx={{ color: '#6b7280' }}>
                            <Info className="w-3 h-3" />
                          </IconButton>
                        )}
                      </Box>
                    </Box>
                  </div>

                  {/* 右侧：优化结果 - 50% */}
                  <div className="w-1/2">
                    <Box className="px-4 py-3 flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Typography variant="subtitle2" className="font-semibold text-gray-700">
                          {t('prompts.optimizeEditPage.optimizationConfig.roundResult', { round: currentOptimizedVersion + 1 })}
                        </Typography>
                        {/* 显示当前轮次的分数 */}
                        {(() => {
                          // 找到对应轮次的分数（轮次 = 索引 + 1）
                          const currentRound = currentOptimizedVersion + 1
                          const roundData = optimizationHistory.find(h => h.round === currentRound)
                          if (roundData && typeof roundData.score === 'number') {
                            return <Chip label={`${roundData.score.toFixed(2)}%`} size="small" className="bg-blue-100 text-blue-700 font-medium" />
                          }
                          return null
                        })()}
                        {(() => {
                          // 检查是否是最优轮次（轮次 = 索引 + 1）
                          const currentRound = currentOptimizedVersion + 1
                          if (bestIteration === currentRound) {
                            return (
                              <Chip
                                label={t('prompts.optimizeEditPage.optimizationResult.best')}
                                size="small"
                                style={{ backgroundColor: '#10b981', color: 'white', fontWeight: 'medium' }}
                              />
                            )
                          }
                          return null
                        })()}
                      </div>
                      <Box className="flex gap-1">
                        <IconButton size="small" onClick={() => handleCopyPrompt(currentOptimizedPrompt)} sx={{ color: '#6b7280' }}>
                          <Copy className="w-3 h-3" />
                        </IconButton>
                        {true && (
                          <IconButton size="small" onClick={() => handleShowDetail('optimized', currentOptimizedVersion + 1)} sx={{ color: '#6b7280' }}>
                            <Info className="w-3 h-3" />
                          </IconButton>
                        )}
                      </Box>
                    </Box>
                  </div>
                </div>
              </Box>

              {/* Diff 内容区 */}
              <Box className="flex-1 overflow-auto">
                <DiffViewer oldContent={historicalOriginalPrompt} newContent={currentOptimizedPrompt} />
              </Box>
            </Card>
          </DialogContent>
        </Dialog>

        {/* 工具编辑对话框 */}
        <ToolEditDialog
          open={toolEditDialogOpen}
          editingTool={editingTool}
          onClose={handleToolEditDialogClose}
          onSave={handleToolEditDialogSave}
          onToolChange={handleEditingToolChange}
          showDefaultValue={false}
        />
      </div>
      {/* Snackbar提示 */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} anchorOrigin={{ vertical: 'top', horizontal: 'center' }} />
    </div>
  )
}

export default PromptOptimizeEditPage
