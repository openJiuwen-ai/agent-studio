import React, { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { ArrowLeft, Settings, Upload, FileText, ChevronLeft, ChevronRight, Edit, Trash2, Save, X, RefreshCw, CheckSquare, Square, AlertCircle, CloudUpload } from 'lucide-react'
import {
  KnowledgeBase,
  DocumentItem,
  GetDocumentsListRequest,
  UpdateDocumentRequest,
  DeleteDocumentsRequest,
  GetDocumentStatusRequest,
  DocumentStatusItem,
} from '@/types/knowledgeBase'
import { useAuthStore } from '@/stores/useAuthStore'
import { useKnowledgeBaseStore } from '@/stores/useKnowledgeBaseStore'
import { ENV_CONFIG } from '@/config/environment'
import UnifiedSnackbar, { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import AddDocumentDialog from './components/AddDocumentDialog'
import AddWeblinkDialog from './components/AddWeblinkDialog'
import SyncToDeepSearchDialog from './components/SyncToDeepSearchDialog'
import { DocumentErrorMessageCell, getStatusErrorMessage } from './components/DocumentErrorMessageCell'
import { KnowledgeBaseEditorCellTooltip } from './components/KnowledgeBaseEditorCellTooltip'

const KnowledgeBaseEditorPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const { user } = useAuthStore()
  const { snackbar, showSuccess, showError, closeSnackbar } = useUnifiedSnackbar()
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [totalDocuments, setTotalDocuments] = useState(0)
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(false)
  const [currentRequestPage, setCurrentRequestPage] = useState<number | null>(null) // 防止重复调用
  const [editingDocumentId, setEditingDocumentId] = useState<string | null>(null)
  const [editingDocumentName, setEditingDocumentName] = useState('')
  const [editingDocumentExtension, setEditingDocumentExtension] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)
  const MAX_DOCUMENT_NAME_LENGTH = 100
  const [documentStatuses, setDocumentStatuses] = useState<Record<string, DocumentStatusItem>>({})
  const [refreshingStatuses, setRefreshingStatuses] = useState<Set<string>>(new Set())
  const [isRefreshingAllStatuses, setIsRefreshingAllStatuses] = useState(false)
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true)

  // 删除确认对话框状态
  const [deleteDialog, setDeleteDialog] = useState({
    isOpen: false,
    documentId: '',
    documentName: '',
  })
  const [isDeletingDocument, setIsDeletingDocument] = useState(false)

  // 批量选择状态
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<Set<string>>(new Set())
  const [batchDeleteDialog, setBatchDeleteDialog] = useState({
    isOpen: false,
    count: 0,
  })
  const [isBatchDeleting, setIsBatchDeleting] = useState(false)

  // 文档处理状态
  const [processingDocIds, setProcessingDocIds] = useState<string[]>([])

  // 用于存储 documentStatuses 的引用
  const documentStatusesRef = React.useRef<Record<string, DocumentStatusItem>>({})
  
  // 同步 documentStatuses 到 ref
  React.useEffect(() => {
    documentStatusesRef.current = documentStatuses
  }, [documentStatuses])

  // 用于存储当前文档列表的引用，用于判断新文档是否在第一页
  const documentsRef = React.useRef<DocumentItem[]>([])
  
  // 同步 documents 到 ref
  React.useEffect(() => {
    documentsRef.current = documents
  }, [documents])

  // 从路由状态获取知识库数据，如果没有则从状态管理中获取
  const stateKnowledgeBase = location.state?.knowledgeBase as KnowledgeBase
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(stateKnowledgeBase || null)
  const isWeblink = knowledgeBase?.type === 'weblink'
  const [isLoadingKnowledgeBase, setIsLoadingKnowledgeBase] = useState(false)

  // 如果路由状态中没有数据，尝试从状态管理中获取
  const { knowledgeBases, fetchKnowledgeBases } = useKnowledgeBaseStore()

  // 使用 ref 来跟踪当前加载的 id，避免重复加载
  const loadingIdRef = React.useRef<string | null>(null)

  React.useEffect(() => {
    // 如果已经有知识库数据且 id 匹配，不需要重新加载
    if (knowledgeBase && knowledgeBase.id === id) {
      return
    }

    // 如果有 state 中的知识库数据且 id 匹配，直接使用
    if (stateKnowledgeBase && stateKnowledgeBase.id === id) {
      setKnowledgeBase(stateKnowledgeBase)
      loadingIdRef.current = id
      return
    }

    // 如果没有 id，无法加载
    if (!id || id === 'undefined') {
      return
    }

    // 如果正在加载相同的 id，避免重复加载
    if (loadingIdRef.current === id && isLoadingKnowledgeBase) {
      return
    }

    // 标记为正在加载
    loadingIdRef.current = id
    setIsLoadingKnowledgeBase(true)

    // 先从状态管理中查找
    const foundKb = knowledgeBases.find(kb => kb.id === id)
    if (foundKb) {
      setKnowledgeBase(foundKb)
      setIsLoadingKnowledgeBase(false)
      return
    }

    // 如果状态管理中也没有，尝试获取知识库列表
    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
    fetchKnowledgeBases(spaceId, 1, 100)
      .then(() => {
        // 获取后再查找
        const { knowledgeBases: updatedKnowledgeBases } = useKnowledgeBaseStore.getState()
        const targetKb = updatedKnowledgeBases.find(kb => kb.id === id)
        if (targetKb) {
          setKnowledgeBase(targetKb)
        } else {
          showError(t('knowledgeBases.settings.notFound'))
          // 设置 knowledgeBase 为 null，避免无限循环
          setKnowledgeBase(null)
        }
        setIsLoadingKnowledgeBase(false)
      })
      .catch(error => {
        console.error('Failed to fetch knowledge base:', error)
        showError(t('knowledgeBases.settings.fetchError'))
        // 设置 knowledgeBase 为 null，避免无限循环
        setKnowledgeBase(null)
        setIsLoadingKnowledgeBase(false)
      })
  }, [id]) // 只依赖 id，当 id 变化时重新加载

  // 用于防止 fetchDocuments 并发执行的锁（按页面索引）
  const fetchDocumentsLockRef = React.useRef<Map<number, Promise<{ items: DocumentItem[]; total: number; page: number } | null>>>(new Map())

  // 获取文档列表
  const fetchDocuments = async (page: number = 1, skipStatusFetch: boolean = false): Promise<{ items: DocumentItem[]; total: number; page: number } | null> => {
    if (!knowledgeBase || !knowledgeBase.id) {
      return null
    }

    if (isDocumentsLoading && currentRequestPage === page) {
      return null
    }

    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
    if (!spaceId) {
      return null
    }

    // 检查是否有相同页面的请求正在进行
    const existingRequest = fetchDocumentsLockRef.current.get(page)
    if (existingRequest) {
      try {
        await existingRequest
      } catch (error) {
        // 忽略错误，让调用方处理
      }
      return null
    }

    // 创建新的请求并加锁
    const requestPromise = (async () => {
      setCurrentRequestPage(page)
      setIsDocumentsLoading(true)
      
      try {
        const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

        let result: { items: DocumentItem[]; total: number; page: number }
        if (knowledgeBase.type === 'weblink') {
          const weblinkResponse = await KnowledgeBaseService.getWeblinksList({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            page,
            size: pageSize,
          })
          result = {
            items: weblinkResponse.data.items as DocumentItem[],
            total: weblinkResponse.data.total,
            page: weblinkResponse.data.page,
          }
          setDocuments(result.items)
          setTotalDocuments(result.total)
          setCurrentPage(result.page)
          if (!skipStatusFetch && result.items.length > 0) {
            const ids = result.items.map(item => item.id)
            fetchDocumentStatuses(ids, true).catch(() => {})
          }
        } else {
        const request: GetDocumentsListRequest = {
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          page,
          size: pageSize,
        }

        const response = await KnowledgeBaseService.getDocumentsList(request)
        result = {
          items: response.data.items,
          total: response.data.total,
          page: response.data.page,
        }
        // 先设置文档列表，立即显示
        setDocuments(result.items)
        setTotalDocuments(result.total)
        setCurrentPage(result.page)
        
        // 只有在不跳过状态查询时才查询当前页文档的状态
        if (!skipStatusFetch) {
          const docIds = result.items.map(doc => doc.id)
          if (docIds.length > 0) {
            fetchDocumentStatuses(docIds, true).catch(error => {
              console.error(`[fetchDocuments] ⚠️  页面 ${page} 状态查询失败:`, error)
            })
          }
        }
        }

        // 返回响应数据，供调用方使用
        return result
      } catch (error) {
        // 不显示错误提示，因为没有文档是正常情况
        throw error // 重新抛出错误，让调用方知道请求失败
      } finally {
        // 清除加载状态
        setIsDocumentsLoading(false)
        setCurrentRequestPage(null)
        // 清除锁
        fetchDocumentsLockRef.current.delete(page)
      }
    })()

    // 保存请求Promise到锁中
    fetchDocumentsLockRef.current.set(page, requestPromise)

    try {
      return await requestPromise
    } catch (error) {
      // 错误已经在内部处理，这里只做清理
      return null
    }
  }

  // 用于防止 fetchAllDocumentIds 并发执行的锁
  const fetchAllDocumentIdsLockRef = React.useRef<Promise<{ allDocIds: string[]; firstPageItems: DocumentItem[]; total: number }> | null>(null)

  // 获取所有文档的ID（通过分页查询）
  // 返回：{ allDocIds: string[], firstPageItems: DocumentItem[], total: number }
  // 优化：使用并行请求提高性能，避免顺序请求导致的排队延迟
  // 添加请求锁，防止并发请求导致的阻塞
  const fetchAllDocumentIds = async (): Promise<{ allDocIds: string[]; firstPageItems: DocumentItem[]; total: number }> => {
    if (!knowledgeBase || !knowledgeBase.id) return { allDocIds: [], firstPageItems: [], total: 0 }

    const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
    if (!spaceId) return { allDocIds: [], firstPageItems: [], total: 0 }

    // 如果已经有正在进行的请求，直接返回该请求的结果
    if (fetchAllDocumentIdsLockRef.current) {
      return fetchAllDocumentIdsLockRef.current
    }

    // 创建新的请求并加锁
    const requestPromise = (async () => {
      try {
        const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

        const allDocIds: string[] = []
        let firstPageItems: DocumentItem[] = []
        let total = 0
        const size = 100 // 每页获取100个，减少请求次数

        // 步骤1: 先获取第一页，获取总数和第一页数据
        if (knowledgeBase.type === 'weblink') {
          const firstPageResponse = await KnowledgeBaseService.getWeblinksList({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            page: 1,
            size,
          })
          total = firstPageResponse.data.total
          firstPageItems = firstPageResponse.data.items.slice(0, pageSize) as DocumentItem[]
          allDocIds.push(...firstPageResponse.data.items.map((doc: { id: string }) => doc.id))
          if (total <= size) {
            return { allDocIds, firstPageItems, total }
          }
          const totalPages = Math.ceil(total / size)
          const remainingPages = Array.from({ length: totalPages - 1 }, (_, i) => i + 2)
          for (let i = 0; i < remainingPages.length; i += 3) {
            const batch = remainingPages.slice(i, i + 3)
            const batchResponses = await Promise.all(
              batch.map(p =>
                KnowledgeBaseService.getWeblinksList({
                  space_id: spaceId,
                  kb_id: knowledgeBase.id,
                  page: p,
                  size,
                })
              )
            )
            batchResponses.forEach(r => {
              r.data.items.forEach((item: { id: string }) => allDocIds.push(item.id))
            })
          }
          return { allDocIds, firstPageItems, total }
        }

        const firstPageRequest: GetDocumentsListRequest = {
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          page: 1,
          size,
        }

        const firstPageResponse = await KnowledgeBaseService.getDocumentsList(firstPageRequest)
        total = firstPageResponse.data.total
        firstPageItems = firstPageResponse.data.items.slice(0, pageSize)
        const firstPageDocIds = firstPageResponse.data.items.map((doc: DocumentItem) => doc.id)
        allDocIds.push(...firstPageDocIds)

        // 如果只有一页，直接返回
        if (total <= size) {
          return { allDocIds, firstPageItems, total }
        }

        // 步骤2: 计算需要获取的总页数
        const totalPages = Math.ceil(total / size)

        // 步骤3: 并行获取剩余页面（分批并行，避免一次性并发太多请求）
        const BATCH_SIZE = 3 // 每批最多3个并发请求，避免服务器压力过大
        const remainingPages = Array.from({ length: totalPages - 1 }, (_, i) => i + 2) // 从第2页开始

        for (let i = 0; i < remainingPages.length; i += BATCH_SIZE) {
          const batch = remainingPages.slice(i, i + BATCH_SIZE)

          // 并行请求当前批次
          const batchPromises = batch.map(p => {
            const request: GetDocumentsListRequest = {
              space_id: spaceId,
              kb_id: knowledgeBase.id,
              page: p,
              size,
            }
            return KnowledgeBaseService.getDocumentsList(request)
          })

          try {
            const batchResponses = await Promise.all(batchPromises)

          // 处理批次结果
          batchResponses.forEach((response) => {
            const docIds = response.data.items.map((doc: DocumentItem) => doc.id)
            allDocIds.push(...docIds)
          })
          } catch (error) {
            console.error(`[fetchAllDocumentIds] 批次 ${Math.floor(i / BATCH_SIZE) + 1} 失败:`, error)
            // 批次失败时，继续处理下一批次，而不是完全失败
          }
        }

        return { allDocIds, firstPageItems, total }
      } catch (error) {
        console.error('[fetchAllDocumentIds] 获取文档ID失败:', error)
        return { allDocIds: [], firstPageItems: [], total: 0 }
      } finally {
        // 请求完成后释放锁
        fetchAllDocumentIdsLockRef.current = null
      }
    })()

    // 保存请求Promise到锁中
    fetchAllDocumentIdsLockRef.current = requestPromise

    return requestPromise
  }

  // 查询文档/链接状态
  // refreshNames: 仅 weblink 有效，为 true 时从 URL 解析标题并更新（初次加载/刷新按钮）
  const fetchDocumentStatuses = async (
    docIds: string[],
    mergeWithExisting: boolean = true,
    refreshNames: boolean = false,
  ) => {
    if (!knowledgeBase || docIds.length === 0) return

    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
      let response: { data: { items: DocumentStatusItem[] } }
      if (knowledgeBase.type === 'weblink') {
        response = await KnowledgeBaseService.getWeblinkStatus({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          weblink_id_list: docIds,
          refresh_names: refreshNames,
        })
      } else {
        response = await KnowledgeBaseService.getDocumentStatus({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          doc_id_list: docIds,
        })
      }

      // 将状态数据转换为以文档/链接ID为键的对象
      const statusMap: Record<string, DocumentStatusItem> = {}
      response.data.items.forEach(statusItem => {
        const id = statusItem.id || (statusItem as any).doc_id
        if (id) {
          statusMap[id] = { ...statusItem, doc_id: statusItem.id || (statusItem as any).doc_id }
        }
      })

      if (mergeWithExisting) {
        setDocumentStatuses(prev => ({ ...prev, ...statusMap }))
      } else {
        setDocumentStatuses(statusMap)
      }
      // weblink 且有 refreshNames 时，同步更新列表中的名称
      if (knowledgeBase.type === 'weblink' && refreshNames && response.data?.items) {
        setDocuments(docs =>
          docs.map(d => {
            const s = statusMap[d.id]
            return s?.name ? { ...d, name: s.name } : d
          }),
        )
      }
    } catch (error) {
      console.error('Failed to fetch document statuses:', error)
    }
  }

  // 当知识库数据加载完成后，先获取第一页显示，然后后台获取全量数据，最后查询状态
  useEffect(() => {
    if (knowledgeBase) {
      // 设置加载状态，避免显示"暂无文档"
      setIsDocumentsLoading(true)
      
      // 优化：延迟一小段时间，确保 token 刷新完成后再发起请求
      const timer = setTimeout(() => {
        // 步骤1: 先获取第一页（使用 pageSize），立即显示
        // 跳过状态查询，因为后续会获取全量状态
        fetchDocuments(1, true)
          .then(() => {
            // 步骤2: 异步获取所有文档ID（在后台，不影响显示）
            fetchAllDocumentIds()
              .then(({ allDocIds }) => {
                // 步骤3: 查询所有文档的状态（包括第一页），更新首页状态栏
                if (allDocIds.length > 0) {
                  // 初次加载 / 重新打开 tab 时刷新名称（仅 weblink）
                  fetchDocumentStatuses(allDocIds, false, knowledgeBase?.type === 'weblink').catch(
                    error => console.error('Failed to fetch document statuses:', error),
                  )
                }
              })
              .catch(error => {
                console.error('Failed to fetch all document IDs:', error)
              })
          })
          .catch(error => {
            console.error('Failed to fetch first page:', error)
            setIsDocumentsLoading(false)
          })
      }, 100) // 延迟100ms，确保 token 刷新完成
      
      return () => {
        clearTimeout(timer)
      }
    }
  }, [knowledgeBase?.id, user?.spaceId]) // 只依赖ID和spaceId，避免重复调用

  // 自动刷新非最终状态的文档状态
  useEffect(() => {
    if (!autoRefreshEnabled || !knowledgeBase) return

    let cancelled = false

    const refreshLoop = async () => {
      while (!cancelled) {
        await new Promise(r => setTimeout(r, 10000))
        if (cancelled) break

        try {
          const existingStatuses = documentStatusesRef.current
          const processingDocIds = Object.keys(existingStatuses).filter(docId => {
            const status = existingStatuses[docId]?.status?.toLowerCase()
            return status && status !== 'indexed' && status !== 'failed' && status !== 'deleted'
          })

          if (processingDocIds.length > 0) {
            // 有正在处理的文档，只刷新它们的状态
            await fetchDocumentStatuses(processingDocIds, true)
          } else if (Object.keys(existingStatuses).length === 0) {
            // 只在没有状态数据时才获取所有文档ID
            // 注意：由于 fetchAllDocumentIds 有锁机制，不会重复请求
            try {
              const result = await fetchAllDocumentIds()
              if (result.allDocIds.length > 0) {
                await fetchDocumentStatuses(result.allDocIds, false)
              }
            } catch (error) {
              console.error('[refreshLoop] ❌ fetchAllDocumentIds failed:', error)
              // 失败时不阻塞，继续下一次循环
            }
          }
        } catch (error) {
          console.error(t('knowledgeBases.editor.autoRefreshError'), error)
        }
      }
    }

    refreshLoop()

    return () => { cancelled = true }
  }, [autoRefreshEnabled, knowledgeBase?.id, user?.spaceId])

  const handleBack = () => {
    navigate('/dashboard/knowledge-bases')
  }

  const handleAddDocument = () => {
    setShowAddDialog(true)
  }

  const totalPages = useMemo(() => {
    return Math.ceil(totalDocuments / pageSize)
  }, [totalDocuments, pageSize])

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchDocuments(newPage)
    }
  }

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize)
    setCurrentPage(1) // 重置到第一页
    // 由于pageSize变化，需要重新获取数据
  }

  // 当页面大小改变时，重新获取数据
  React.useEffect(() => {
    // 只有在 knowledgeBase 已加载且 pageSize 变化时才重新获取数据
    // 避免在初始加载时重复请求（初始加载时已经通过 fetchAllDocumentIds 获取了数据）
    if (knowledgeBase && totalDocuments > 0) {
      fetchDocuments(currentPage)
    }
  }, [pageSize]) // 当pageSize变化时重新获取数据

  // 刷新单个文档状态
  const handleRefreshSingleStatus = async (documentId: string) => {
    if (!knowledgeBase || refreshingStatuses.has(documentId)) return

    setRefreshingStatuses(prev => new Set(prev).add(documentId))
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

      const response = knowledgeBase.type === 'weblink'
        ? await KnowledgeBaseService.getWeblinkStatus({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            weblink_id_list: [documentId],
            refresh_names: true,
          })
        : await KnowledgeBaseService.getDocumentStatus({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            doc_id_list: [documentId],
          })

      if (response.data?.items?.length > 0) {
        const item = response.data.items[0]
        const statusMap = { [documentId]: { ...item, doc_id: item.id || (item as any).doc_id } }
        setDocumentStatuses(prev => ({ ...prev, ...statusMap }))
        if (isWeblink && item?.name) {
          setDocuments(docs => docs.map(d => (d.id === documentId ? { ...d, name: item.name! } : d)))
        }
      }

      showSuccess(isWeblink ? t('knowledgeBases.editor.refreshSuccessWeblink') : t('knowledgeBases.editor.refreshSuccess'))
    } catch (error) {
      console.error('Failed to refresh document status:', error)
      showError(isWeblink ? t('knowledgeBases.editor.refreshFailedWeblink') : t('knowledgeBases.editor.refreshFailed'))
    } finally {
      setRefreshingStatuses(prev => {
        const newSet = new Set(prev)
        newSet.delete(documentId)
        return newSet
      })
    }
  }

  // 刷新所有文档状态
  const handleRefreshAllStatuses = async () => {
    if (!knowledgeBase || documents.length === 0 || isRefreshingAllStatuses) return

    setIsRefreshingAllStatuses(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
      const docIds = documents.map(doc => doc.id)

      const response = knowledgeBase.type === 'weblink'
        ? await KnowledgeBaseService.getWeblinkStatus({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            weblink_id_list: docIds,
            refresh_names: true,
          })
        : await KnowledgeBaseService.getDocumentStatus({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            doc_id_list: docIds,
          })

      if (response.data?.items) {
        const statusMap: Record<string, DocumentStatusItem> = {}
        response.data.items.forEach(statusItem => {
          const id = statusItem.id || (statusItem as any).doc_id
          if (id) {
            statusMap[id] = { ...statusItem, doc_id: statusItem.id || (statusItem as any).doc_id }
          }
        })
        setDocumentStatuses(prev => ({ ...prev, ...statusMap }))
        if (isWeblink) {
          setDocuments(docs =>
            docs.map(d => {
              const s = statusMap[d.id]
              return s?.name ? { ...d, name: s.name } : d
            }),
          )
        }
      }

      showSuccess(isWeblink ? t('knowledgeBases.editor.refreshAllSuccessWeblink') : t('knowledgeBases.editor.refreshAllSuccess'))
    } catch (error) {
      console.error('Failed to refresh all document statuses:', error)
      showError(isWeblink ? t('knowledgeBases.editor.refreshAllFailedWeblink') : t('knowledgeBases.editor.refreshAllFailed'))
    } finally {
      setIsRefreshingAllStatuses(false)
    }
  }

  // 状态显示组件
  const StatusBadge = ({ status, documentId, enableGraphEnhancement }: { status: string; documentId: string; enableGraphEnhancement?: boolean }) => {
    const getStatusColor = (status: string) => {
      switch (status.toLowerCase()) {
        case 'uploading':
          return 'bg-purple-100 text-purple-800'
        case 'uploaded':
          return 'bg-yellow-100 text-yellow-800'
        case 'processing':
          return 'bg-blue-100 text-blue-800'
        case 'indexing':
          return 'bg-indigo-100 text-indigo-800'
        case 'indexed':
          return 'bg-green-100 text-green-800'
        case 'failed':
          return 'bg-red-100 text-red-800'
        case 'deleted':
          return 'bg-gray-100 text-gray-600'
        case 'unknown':
        case 'querying':
          return 'bg-gray-100 text-gray-600'
        default:
          return 'bg-gray-100 text-gray-800'
      }
    }

    const getStatusText = (status: string) => {
      switch (status.toLowerCase()) {
        case 'uploading':
          return t('knowledgeBases.editor.status.uploading')
        case 'uploaded':
          return t('knowledgeBases.editor.status.uploaded')
        case 'processing':
          return t('knowledgeBases.editor.status.processing')
        case 'indexing':
          return t('knowledgeBases.editor.status.indexing')
        case 'indexed':
          return t('knowledgeBases.editor.status.indexed')
        case 'failed':
          return t('knowledgeBases.editor.status.failed')
        case 'deleted':
          return t('knowledgeBases.editor.status.deleted')
        case 'unknown':
          return t('knowledgeBases.editor.status.querying')
        default:
          return status
      }
    }

    const isAutoRefreshing =
      autoRefreshEnabled &&
      status.toLowerCase() !== 'indexed' &&
      status.toLowerCase() !== 'failed' &&
      status.toLowerCase() !== 'deleted' &&
      status.toLowerCase() !== 'unknown'

    return (
      <div className="flex items-center space-x-2">
        <span className={`px-2 py-1 text-xs rounded-full font-medium ${getStatusColor(status)}`}>{getStatusText(status)}</span>
        {enableGraphEnhancement && <span className="px-2 py-1 text-xs rounded-full font-medium bg-blue-50 text-blue-600">{t('knowledgeBases.editor.graphEnhancement')}</span>}
        {isAutoRefreshing && <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>}
      </div>
    )
  }

  // 分离文件名和扩展名
  const splitFileName = (fullName: string): { name: string; extension: string } => {
    const lastDotIndex = fullName.lastIndexOf('.')
    if (lastDotIndex === -1 || lastDotIndex === fullName.length - 1) {
      // 没有扩展名或点号在最后
      return { name: fullName, extension: '' }
    }
    return {
      name: fullName.substring(0, lastDotIndex),
      extension: fullName.substring(lastDotIndex),
    }
  }

  // 开始编辑文档名称（weblink 名称常为完整 URL，含多个点号，不能按「扩展名」拆分）
  const handleEditDocument = (document: DocumentItem) => {
    if (isWeblink) {
      setEditingDocumentId(document.id)
      setEditingDocumentName(document.name)
      setEditingDocumentExtension('')
      return
    }
    const { name, extension } = splitFileName(document.name)
    setEditingDocumentId(document.id)
    setEditingDocumentName(name)
    setEditingDocumentExtension(extension)
  }

  // 保存文档名称
  const handleSaveDocumentName = async (documentId: string) => {
    if (!knowledgeBase || !editingDocumentName.trim()) return

    // 文档：主文件名长度；weblink：整段 URL
    if (editingDocumentName.trim().length > MAX_DOCUMENT_NAME_LENGTH) {
      showError(
        isWeblink
          ? t('knowledgeBases.editor.nameMaxLengthWeblink', { max: MAX_DOCUMENT_NAME_LENGTH })
          : t('knowledgeBases.editor.nameMaxLength', { max: MAX_DOCUMENT_NAME_LENGTH })
      )
      return
    }

    // 文档类型：主名 + 扩展名；weblink：整段为显示名（常为 URL）
    const fullName = isWeblink
      ? editingDocumentName.trim()
      : editingDocumentName.trim() + editingDocumentExtension

    setIsUpdating(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

      if (knowledgeBase.type === 'weblink') {
        await KnowledgeBaseService.updateWeblink({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          weblink_id: documentId,
          weblink_name: fullName,
        })
      } else {
        const request: UpdateDocumentRequest = {
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          document_id: documentId,
          document_name: fullName,
        }
        await KnowledgeBaseService.updateDocument(request)
      }

      // 更新本地状态
      setDocuments(docs => docs.map(doc => (doc.id === documentId ? { ...doc, name: fullName } : doc)))

      setEditingDocumentId(null)
      setEditingDocumentName('')
      setEditingDocumentExtension('')
      showSuccess(isWeblink ? t('knowledgeBases.editor.updateSuccessWeblink') : t('knowledgeBases.editor.updateSuccess'))
    } catch (error) {
      console.error('Failed to update document:', error)
      showError(isWeblink ? t('knowledgeBases.editor.updateFailedWeblink') : t('knowledgeBases.editor.updateFailed'))
    } finally {
      setIsUpdating(false)
    }
  }

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingDocumentId(null)
    setEditingDocumentName('')
    setEditingDocumentExtension('')
  }

  // 打开删除确认对话框
  const handleOpenDeleteDialog = (documentId: string, documentName: string) => {
    setDeleteDialog({
      isOpen: true,
      documentId,
      documentName,
    })
  }

  // 关闭删除确认对话框
  const handleCloseDeleteDialog = () => {
    setDeleteDialog({
      isOpen: false,
      documentId: '',
      documentName: '',
    })
  }

  // 确认删除文档
  const confirmDeleteDocument = async () => {
    if (!knowledgeBase || !deleteDialog.documentId) return

    setIsDeletingDocument(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

      if (knowledgeBase.type === 'weblink') {
        await KnowledgeBaseService.deleteWeblinks({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          weblink_ids: [deleteDialog.documentId],
        })
      } else {
        const request: DeleteDocumentsRequest = {
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          document_ids: [deleteDialog.documentId],
        }
        await KnowledgeBaseService.deleteDocuments(request)
      }

      showSuccess(isWeblink ? t('knowledgeBases.editor.deleteSuccessWeblink') : t('knowledgeBases.editor.deleteSuccess'))

      // 保存删除前的页码
      const pageBeforeDelete = currentPage
      
      // 刷新文档列表，确保数据同步
      const result = await fetchDocuments(pageBeforeDelete)
      
      // 如果当前页没有文档了，且不是第一页，则跳转到前一页
      if (result && result.items.length === 0 && pageBeforeDelete > 1) {
        const previousPage = pageBeforeDelete - 1
        await fetchDocuments(previousPage)
      }
    } catch (error) {
      console.error('Failed to delete document:', error)
      showError(isWeblink ? t('knowledgeBases.editor.deleteFailedWeblink') : t('knowledgeBases.editor.deleteFailed'))
    } finally {
      setIsDeletingDocument(false)
      handleCloseDeleteDialog()
    }
  }

  // 批量选择相关函数
  const handleSelectDocument = (documentId: string) => {
    setSelectedDocumentIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(documentId)) {
        newSet.delete(documentId)
      } else {
        newSet.add(documentId)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    if (selectedDocumentIds.size === documents.length) {
      // 如果已全选，则取消全选
      setSelectedDocumentIds(new Set())
    } else {
      // 全选当前页所有文档
      setSelectedDocumentIds(new Set(documents.map(doc => doc.id)))
    }
  }

  const isAllSelected = documents.length > 0 && selectedDocumentIds.size === documents.length
  const isPartialSelected = selectedDocumentIds.size > 0 && selectedDocumentIds.size < documents.length

  // 打开批量删除确认对话框
  const handleOpenBatchDeleteDialog = () => {
    if (selectedDocumentIds.size === 0) return
    setBatchDeleteDialog({
      isOpen: true,
      count: selectedDocumentIds.size,
    })
  }

  // 关闭批量删除确认对话框
  const handleCloseBatchDeleteDialog = () => {
    setBatchDeleteDialog({
      isOpen: false,
      count: 0,
    })
  }

  // 确认批量删除
  const confirmBatchDelete = async () => {
    if (!knowledgeBase || selectedDocumentIds.size === 0) return

    setIsBatchDeleting(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')
      const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

      if (knowledgeBase.type === 'weblink') {
        await KnowledgeBaseService.deleteWeblinks({
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          weblink_ids: Array.from(selectedDocumentIds),
        })
      } else {
        const request: DeleteDocumentsRequest = {
          space_id: spaceId,
          kb_id: knowledgeBase.id,
          document_ids: Array.from(selectedDocumentIds),
        }
        await KnowledgeBaseService.deleteDocuments(request)
      }

      const deletedCount = selectedDocumentIds.size

      // 清空选中列表
      setSelectedDocumentIds(new Set())

      showSuccess(
        isWeblink
          ? t('knowledgeBases.editor.batchDeleteSuccessWeblink', { count: deletedCount })
          : t('knowledgeBases.editor.batchDeleteSuccess', { count: deletedCount })
      )

      // 保存删除前的页码
      const pageBeforeDelete = currentPage
      
      // 刷新文档列表，确保数据同步
      const result = await fetchDocuments(pageBeforeDelete)
      
      // 如果当前页没有文档了，且不是第一页，则跳转到前一页
      if (result && result.items.length === 0 && pageBeforeDelete > 1) {
        const previousPage = pageBeforeDelete - 1
        await fetchDocuments(previousPage)
      }
    } catch (error) {
      console.error('Failed to batch delete documents:', error)
      showError(isWeblink ? t('knowledgeBases.editor.batchDeleteFailedWeblink') : t('knowledgeBases.editor.batchDeleteFailed'))
    } finally {
      setIsBatchDeleting(false)
      handleCloseBatchDeleteDialog()
    }
  }

  // 当文档列表变化时，清除无效的选中项
  useEffect(() => {
    const validIds = new Set(documents.map(doc => doc.id))
    setSelectedDocumentIds(prev => {
      const newSet = new Set<string>()
      prev.forEach(id => {
        if (validIds.has(id)) {
          newSet.add(id)
        }
      })
      return newSet
    })
  }, [documents])

  // 基于所有文档的状态检测正在处理的文档（不仅仅是当前页）
  useEffect(() => {
    if (Object.keys(documentStatuses).length === 0) return

    // 基于所有文档的状态，找出正在处理中的文档（状态不是 indexed、failed、deleted）
    const processingDocIdsList: string[] = []
    Object.keys(documentStatuses).forEach(docId => {
      const status = documentStatuses[docId]?.status?.toLowerCase()
      if (status && status !== 'indexed' && status !== 'failed' && status !== 'deleted') {
        processingDocIdsList.push(docId)
      }
    })

    // 更新处理中的文档列表（完全替换，基于所有文档的状态）
    setProcessingDocIds(processingDocIdsList)
  }, [documentStatuses])

  // 处理知识库不存在的情况
  if (isLoadingKnowledgeBase) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">{t('knowledgeBases.editor.loading')}</p>
        </div>
      </div>
    )
  }

  // 如果知识库不存在，显示错误信息
  if (!knowledgeBase) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md px-4">
          <AlertCircle className="mx-auto w-12 h-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">{t('knowledgeBases.settings.notFound')}</h2>
          <p className="text-gray-600 mb-6">{t('knowledgeBases.settings.fetchError')}</p>
          <button 
            onClick={() => navigate('/dashboard/knowledge-bases')} 
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center mx-auto"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t('common.buttons.back')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-6">
      {/* 头部导航 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button onClick={handleBack} className="flex items-center text-gray-600 hover:text-gray-900 mr-4">
                <ArrowLeft className="w-5 h-5 mr-2" />
                {t('common.buttons.back')}
              </button>
              <div className="flex items-center min-w-0 flex-1">
                <Edit className="w-5 h-5 mr-2 text-gray-500 flex-shrink-0" />
                <h1 className="text-xl font-semibold text-gray-900 flex items-center min-w-0" title={knowledgeBase.name}>
                  <span className="truncate max-w-[300px]">
                    {knowledgeBase.name.length > 30 ? `${knowledgeBase.name.substring(0, 30)}...` : knowledgeBase.name}
                  </span>
                  <span className="ml-2 flex-shrink-0">- {t('knowledgeBases.edit.title')}</span>
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={handleAddDocument} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center">
                <Upload className="w-4 h-4 mr-2" />
                {isWeblink ? t('knowledgeBases.addWeblink.addButton') || '添加链接' : t('knowledgeBases.settings.addDocument')}
              </button>
              {!(knowledgeBase.ds_kb_id && knowledgeBase.id === knowledgeBase.ds_kb_id) && (
                <button
                  onClick={() => setShowSyncDialog(true)}
                  className="px-4 py-2 border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50 flex items-center"
                >
                  <CloudUpload className="w-4 h-4 mr-2" />
                  {t('knowledgeBases.syncToDeepSearch.button')}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 文档处理中提示 */}
        {processingDocIds.length > 0 && (
          <div className="mb-6 bg-white rounded-lg shadow p-4">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-gray-700">
                {isWeblink
                  ? t('knowledgeBases.editor.processingWeblinks', { count: processingDocIds.length })
                  : t('knowledgeBases.editor.processing', { count: processingDocIds.length })}
              </span>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <div className="space-y-6">
            {/* 文档列表 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <h2 className="text-lg font-medium text-gray-900">
                    {isWeblink ? t('knowledgeBases.editor.weblinkList') : t('knowledgeBases.editor.documentList')}
                  </h2>
                  {autoRefreshEnabled && processingDocIds.length > 0 && (
                    <div className="flex items-center text-sm text-green-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                      {isWeblink ? t('knowledgeBases.editor.autoRefreshWeblinks') : t('knowledgeBases.editor.autoRefresh')}
                    </div>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  {selectedDocumentIds.size > 0 && (
                    <button
                      onClick={handleOpenBatchDeleteDialog}
                      className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 flex items-center text-sm"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      {t('knowledgeBases.editor.deleteSelected', { count: selectedDocumentIds.size })}
                    </button>
                  )}
                  <button
                    onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                    disabled={processingDocIds.length === 0}
                    className={`px-3 py-2 rounded-lg flex items-center text-sm ${
                      processingDocIds.length === 0
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : autoRefreshEnabled
                        ? 'bg-gray-500 text-white hover:bg-gray-600'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                    }`}
                    title={
                      processingDocIds.length === 0
                        ? (isWeblink ? t('knowledgeBases.editor.noAutoRefreshHintWeblinks') : t('knowledgeBases.editor.noAutoRefreshHint'))
                        : ''
                    }
                  >
                    {autoRefreshEnabled
                      ? (isWeblink ? t('knowledgeBases.editor.stopAutoRefreshWeblinks') : t('knowledgeBases.editor.stopAutoRefresh'))
                      : (isWeblink ? t('knowledgeBases.editor.startAutoRefreshWeblinks') : t('knowledgeBases.editor.startAutoRefresh'))}
                  </button>
                  <button
                    onClick={handleRefreshAllStatuses}
                    disabled={documents.length === 0 || isRefreshingAllStatuses}
                    className="px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshingAllStatuses ? 'animate-spin' : ''}`} />
                    {isRefreshingAllStatuses ? t('knowledgeBases.editor.refreshing') : t('knowledgeBases.editor.refreshStatus')}
                  </button>
                </div>
              </div>

              {isDocumentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  <span className="ml-2 text-gray-600">
                    {isWeblink ? t('knowledgeBases.editor.loadingWeblinks') : t('knowledgeBases.editor.loadingDocuments')}
                  </span>
                </div>
              ) : documents.length === 0 ? (
                  <div className="text-center py-8">
                  <FileText className="mx-auto w-12 h-12 text-gray-300 mb-4" />
                  <p className="text-gray-500 mb-4">
                    {isWeblink ? t('knowledgeBases.editor.noWeblinks') : t('knowledgeBases.editor.noDocuments')}
                  </p>
                  <div className="flex items-center justify-center gap-2">
                    <button onClick={handleAddDocument} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center">
                      <Upload className="w-4 h-4 mr-2" />
                      {isWeblink ? t('knowledgeBases.editor.addWeblink') : t('knowledgeBases.editor.addDocument')}
                    </button>
                    {!(knowledgeBase.ds_kb_id && knowledgeBase.id === knowledgeBase.ds_kb_id) && (
                      <button
                        onClick={() => setShowSyncDialog(true)}
                        className="px-4 py-2 border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50 flex items-center"
                      >
                        <CloudUpload className="w-4 h-4 mr-2" />
                        {t('knowledgeBases.syncToDeepSearch.button')}
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="border border-gray-200 rounded-lg max-w-full overflow-x-auto">
                    <table className="w-full min-w-[72rem] table-fixed divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12 align-middle shrink-0">
                            <button
                              onClick={handleSelectAll}
                              className="flex items-center justify-center p-1 rounded hover:bg-gray-200 transition-colors"
                              title={isAllSelected ? t('knowledgeBases.editor.deselectAll') : t('knowledgeBases.editor.selectAll')}
                            >
                              {isAllSelected ? (
                                <CheckSquare className="w-5 h-5 text-blue-600" />
                              ) : isPartialSelected ? (
                                <div className="w-5 h-5 border-2 border-blue-600 rounded flex items-center justify-center bg-blue-600">
                                  <div className="w-2.5 h-0.5 bg-white"></div>
                                </div>
                              ) : (
                                <Square className="w-5 h-5 text-gray-400" />
                              )}
                            </button>
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-0 w-[30%] align-middle">
                            {isWeblink ? t('knowledgeBases.editor.weblinkName') : t('knowledgeBases.editor.documentName')}
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40 align-middle">
                            {t('knowledgeBases.settings.status')}
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-44 whitespace-nowrap align-middle">
                            {t('knowledgeBases.editor.createdAt')}
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[12.5rem] w-[26%] align-top">
                            {t('knowledgeBases.settings.errorInfo')}
                          </th>
                          <th className="px-6 py-3 pr-7 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[8.5rem] min-w-[8.5rem] whitespace-nowrap align-middle">
                            {t('knowledgeBases.editor.actions')}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {documents.map(doc => (
                          <tr key={doc.id} className={`hover:bg-gray-50 ${selectedDocumentIds.has(doc.id) ? 'bg-blue-50' : ''}`}>
                            <td className="px-4 py-4 whitespace-nowrap w-12 align-middle">
                              <button
                                onClick={() => handleSelectDocument(doc.id)}
                                className="flex items-center justify-center p-1 rounded hover:bg-gray-200 transition-colors"
                              >
                                {selectedDocumentIds.has(doc.id) ? (
                                  <CheckSquare className="w-5 h-5 text-blue-600" />
                                ) : (
                                  <Square className="w-5 h-5 text-gray-400" />
                                )}
                              </button>
                            </td>
                            <td className="px-6 py-4 min-w-0 align-middle">
                              <div className="flex items-center min-w-0">
                                <FileText className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" />
                                {editingDocumentId === doc.id ? (
                                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                                    <div className="flex-1 flex items-center space-x-2 min-w-0">
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2 min-w-0">
                                          <input
                                            type="text"
                                            value={editingDocumentName}
                                            onChange={e => {
                                              const newValue = e.target.value
                                              // 限制输入长度
                                              if (newValue.length <= MAX_DOCUMENT_NAME_LENGTH) {
                                                setEditingDocumentName(newValue)
                                              }
                                            }}
                                            onKeyDown={e => {
                                              if (e.key === 'Enter') {
                                                handleSaveDocumentName(doc.id)
                                              } else if (e.key === 'Escape') {
                                                handleCancelEdit()
                                              }
                                            }}
                                            maxLength={MAX_DOCUMENT_NAME_LENGTH}
                                            className={`min-w-0 flex-1 max-w-full px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                                              editingDocumentName.length >= MAX_DOCUMENT_NAME_LENGTH ? 'border-red-500 focus:ring-red-500' : 'border-gray-300'
                                            }`}
                                            autoFocus
                                          />
                                          {editingDocumentExtension && (
                                            <span className="text-sm text-gray-500 px-2 py-1 bg-gray-100 rounded border border-gray-300">
                                              {editingDocumentExtension}
                                            </span>
                                          )}
                                        </div>
                                        <div className="flex items-center justify-between mt-1">
                                          <span
                                            className={`text-xs ${editingDocumentName.length >= MAX_DOCUMENT_NAME_LENGTH ? 'text-red-500' : 'text-gray-500'}`}
                                          >
                                            {editingDocumentName.length}/{MAX_DOCUMENT_NAME_LENGTH}
                                          </span>
                                            {editingDocumentName.length >= MAX_DOCUMENT_NAME_LENGTH && (
                                            <span className="text-xs text-red-500">{t('knowledgeBases.editor.maxLengthReached')}</span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                    <button
                                      onClick={() => handleSaveDocumentName(doc.id)}
                                      disabled={isUpdating || !editingDocumentName.trim() || editingDocumentName.length > MAX_DOCUMENT_NAME_LENGTH}
                                      className="p-1 text-green-600 hover:text-green-800 disabled:opacity-50"
                                    >
                                      <Save className="w-4 h-4" />
                                    </button>
                                    <button onClick={handleCancelEdit} className="p-1 text-gray-500 hover:text-gray-700">
                                      <X className="w-4 h-4" />
                                    </button>
                                  </div>
                                ) : (
                                  <KnowledgeBaseEditorCellTooltip title={doc.name}>
                                    <span
                                      onClick={() => handleEditDocument(doc)}
                                      className="text-sm font-medium text-gray-900 cursor-pointer hover:text-blue-600 min-w-0 flex-1 truncate block"
                                    >
                                      {doc.name}
                                    </span>
                                  </KnowledgeBaseEditorCellTooltip>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm align-middle">
                              <StatusBadge
                                status={documentStatuses[doc.id]?.status || 'unknown'}
                                documentId={doc.id}
                                enableGraphEnhancement={documentStatuses[doc.id]?.enable_graph_enhancement}
                              />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 align-middle">
                              {doc.created_at || '-'}
                            </td>
                            <td className="px-6 py-4 text-sm min-w-[12.5rem] align-top">
                              <DocumentErrorMessageCell
                                message={getStatusErrorMessage(documentStatuses[doc.id])}
                              />
                            </td>
                            <td className="px-6 py-4 pr-7 whitespace-nowrap text-sm align-middle">
                              <div className="flex items-center justify-start gap-2">
                                <button
                                  onClick={() => handleEditDocument(doc)}
                                  className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
                                  disabled={editingDocumentId !== null || isUpdating}
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleRefreshSingleStatus(doc.id)}
                                  className="text-green-600 hover:text-green-800 disabled:opacity-50"
                                  disabled={refreshingStatuses.has(doc.id)}
                                  title={isWeblink ? t('knowledgeBases.editor.refreshDocumentStatusWeblink') : t('knowledgeBases.editor.refreshDocumentStatus')}
                                >
                                  <RefreshCw className={`w-4 h-4 ${refreshingStatuses.has(doc.id) ? 'animate-spin' : ''}`} />
                                </button>
                                <button
                                  onClick={() => handleOpenDeleteDialog(doc.id, doc.name)}
                                  className="text-red-600 hover:text-red-800 disabled:opacity-50"
                                  disabled={editingDocumentId !== null || isUpdating}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 分页 */}
                  {!isDocumentsLoading && (
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-600">{t('common.pagination.pageSize')}:</span>
                        <select
                          value={pageSize}
                          onChange={e => {
                            handlePageSizeChange(Number(e.target.value))
                          }}
                          className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300 shadow-sm pagination-select"
                        >
                          <option value={10}>10{t('common.pagination.items')}</option>
                          <option value={20}>20{t('common.pagination.items')}</option>
                          <option value={50}>50{t('common.pagination.items')}</option>
                          <option value={100}>100{t('common.pagination.items')}</option>
                        </select>
                        <span className="text-sm text-gray-600">{t('common.pagination.total', { total: totalDocuments })}</span>
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
                            let pageNum: number
                            if (totalPages <= 5) {
                              pageNum = i + 1
                            } else if (currentPage <= 3) {
                              pageNum = i + 1
                            } else if (currentPage >= totalPages - 2) {
                              pageNum = totalPages - 4 + i
                            } else {
                              pageNum = currentPage - 2 + i
                            }

                            return (
                              <button
                                key={i}
                                onClick={() => handlePageChange(pageNum)}
                                className={`w-10 h-10 rounded-lg ${currentPage === pageNum ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
                              >
                                {pageNum}
                              </button>
                            )
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
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 同步至 Deep Search 对话框 */}
      {showSyncDialog && knowledgeBase && (
        <SyncToDeepSearchDialog
          open={showSyncDialog}
          knowledgeBase={knowledgeBase}
          onClose={() => setShowSyncDialog(false)}
          onSuccess={() => {
            setShowSyncDialog(false)
            showSuccess(t('knowledgeBases.syncToDeepSearch.success'))
            setCurrentPage(1)
            fetchDocuments(1).catch(console.error)
          }}
          onAbort={() => {
            const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
            if (!id) return
            fetchKnowledgeBases(spaceId, 1, 100)
              .then(() => {
                const { knowledgeBases: list } = useKnowledgeBaseStore.getState()
                const kb = list.find(k => k.id === id)
                if (kb) setKnowledgeBase(kb)
              })
              .catch(console.error)
          }}
        />
      )}

      {/* 添加文档/链接对话框 */}
      {showAddDialog && knowledgeBase && (
        isWeblink ? (
        <AddWeblinkDialog
          open={showAddDialog}
          knowledgeBase={knowledgeBase}
          existingWeblinkCount={totalDocuments}
          onClose={() => setShowAddDialog(false)}
          onWeblinksAdded={() => {
            setCurrentPage(1)
            fetchDocuments(1).catch(() => {})
          }}
          onSuccess={async (weblinkIds?: string[]) => {
            setShowAddDialog(false)
            showSuccess(isWeblink ? t('knowledgeBases.settings.linkAdded') : t('knowledgeBases.settings.documentAdded'))
            setCurrentPage(1)
            fetchDocuments(1).then(() => {
              if (weblinkIds && weblinkIds.length > 0) {
                setTimeout(() => {
                  const currentPageDocIds = new Set(documentsRef.current.map(doc => doc.id))
                  const newIdsNotInPage = weblinkIds.filter(id => !currentPageDocIds.has(id))
                  if (newIdsNotInPage.length > 0) {
                    fetchDocumentStatuses(newIdsNotInPage, true).catch(() => {})
                  }
                }, 100)
              }
            }).catch(() => {})
          }}
        />
      ) : (
        <AddDocumentDialog
          open={showAddDialog}
          knowledgeBase={knowledgeBase}
          onClose={() => setShowAddDialog(false)}
          onDocumentUploaded={() => {
            // 如果用户在上传文件后关闭对话框，也需要刷新文档列表
            // 注意：如果 onSuccess 也会被调用，这里可能会有重复请求
            // 但 fetchDocuments 内部有防重复调用的保护，所以不会有问题
            // 上传文档后重置到第一页
            setCurrentPage(1)
            // 不等待完成，避免阻塞UI
            fetchDocuments(1).catch(error => {
              console.error('Failed to fetch documents after upload:', error)
            })
          }}
          onSuccess={async (docIds?: string[]) => {
            setShowAddDialog(false)
            showSuccess(isWeblink ? t('knowledgeBases.settings.linkAdded') : t('knowledgeBases.settings.documentAdded'))
            // 上传文档/添加链接后重置到第一页
            setCurrentPage(1)
            
            // 优化：直接使用 fetchDocuments(1) 获取第一页数据，避免遍历所有页面
            // fetchAllDocumentIds 会遍历所有页面获取所有文档ID，当文档数量很多时非常慢
            // 添加文档后只需要刷新第一页即可，大大提升性能
            
            // 先获取文档列表（不等待状态查询）
            // fetchDocuments 内部会自动查询当前页文档的状态，避免重复查询
            fetchDocuments(1).then(() => {
              // fetchDocuments 完成后，检查新上传的文档是否在第一页
              // 如果不在第一页，需要单独查询它们的状态
              if (docIds && docIds.length > 0) {
                // 使用 setTimeout 确保文档列表状态已经更新
                setTimeout(() => {
                  // 使用 ref 获取最新的文档列表，避免闭包陷阱
                  const currentPageDocIds = new Set(documentsRef.current.map(doc => doc.id))
                  const newDocIdsNotInPage = docIds.filter(id => !currentPageDocIds.has(id))
                  
                  // 只查询不在当前页的新文档的状态
                  // 如果新文档在第一页，fetchDocuments 已经查询过了，避免重复查询
                  if (newDocIdsNotInPage.length > 0) {
                    fetchDocumentStatuses(newDocIdsNotInPage, true).catch(error => {
                      console.error('Failed to fetch new document statuses:', error)
                    })
                  }
                }, 100)
              }
            }).catch(error => {
              console.error('Failed to fetch documents:', error)
            })
          }}
        />
      )
      )}

      {/* 删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={handleCloseDeleteDialog}
        onConfirm={confirmDeleteDocument}
        title={isWeblink ? t('knowledgeBases.editor.deleteTitleWeblink') : t('knowledgeBases.editor.deleteTitle')}
        message={
          isWeblink
            ? t('knowledgeBases.editor.deleteMessageWeblink', { name: deleteDialog.documentName })
            : t('knowledgeBases.editor.deleteMessage', { name: deleteDialog.documentName })
        }
        confirmButtonText={t('knowledgeBases.editor.deleteDocument')}
        cancelButtonText="取消"
        isLoading={isDeletingDocument}
        iconType="danger"
      />

      {/* 批量删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={batchDeleteDialog.isOpen}
        onClose={handleCloseBatchDeleteDialog}
        onConfirm={confirmBatchDelete}
        title={isWeblink ? t('knowledgeBases.editor.batchDeleteTitleWeblink') : t('knowledgeBases.editor.batchDeleteTitle')}
        message={
          isWeblink
            ? t('knowledgeBases.editor.batchDeleteMessageWeblink', { count: batchDeleteDialog.count })
            : t('knowledgeBases.editor.batchDeleteMessage', { count: batchDeleteDialog.count })
        }
        confirmButtonText={
          isWeblink
            ? t('knowledgeBases.editor.batchDeleteButtonWeblink', { count: batchDeleteDialog.count })
            : t('knowledgeBases.editor.batchDeleteButton', { count: batchDeleteDialog.count })
        }
        cancelButtonText="取消"
        isLoading={isBatchDeleting}
        iconType="danger"
      />

      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </div>
  )
}

export default KnowledgeBaseEditorPage
