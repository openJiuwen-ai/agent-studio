import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Upload, ArrowLeft, ArrowRight, Check, FileText, HelpCircle, AlertTriangle, Play, Loader2, CheckCircle, Info } from 'lucide-react'
import { Tooltip } from '@mui/material'
import { KnowledgeBase } from '@/types/knowledgeBase'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { useModels, useTestModel, ProcessDocumentsRequest } from '@test-agentstudio/api-client'

interface AddDocumentDialogProps {
  open: boolean
  knowledgeBase: KnowledgeBase
  onClose: () => void
  onSuccess: (processingDocIds?: string[]) => void // 传递正在处理的文档ID列表
  onDocumentUploaded?: () => void // 新增：当文档上传成功后关闭时触发
}

interface FormData {
  parsingStrategy: string
  segmentationStrategy: string
  maxTokens: number
  chunkOverlapPercent: number
  enableGraphEnhancement: boolean
  llmModelId: number | string | null
}

const AddDocumentDialog: React.FC<AddDocumentDialogProps> = ({ open, knowledgeBase, onClose, onSuccess, onDocumentUploaded }) => {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const { showSuccess, showError } = useUnifiedSnackbar()

  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [uploadedFileIds, setUploadedFileIds] = useState<string[]>([])
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [documentsProcessed, setDocumentsProcessed] = useState(false) // 标记文档是否已被处理（索引）
  const [showInvalidFileDialog, setShowInvalidFileDialog] = useState(false) // 显示无效文件类型提示弹窗
  const [invalidFiles, setInvalidFiles] = useState<string[]>([]) // 无效文件列表
  const [showInvalidFileNameLengthDialog, setShowInvalidFileNameLengthDialog] = useState(false) // 显示文件名过长提示弹窗
  const [invalidFileNameLengthFiles, setInvalidFileNameLengthFiles] = useState<string[]>([]) // 文件名过长的文件列表
  const [invalidFilesWithLongName, setInvalidFilesWithLongName] = useState<string[]>([]) // 既是不支持的文件类型，又有过长文件名的文件列表
  const [showOversizedFileDialog, setShowOversizedFileDialog] = useState(false) // 显示文件过大提示弹窗
  const [oversizedFiles, setOversizedFiles] = useState<Array<{ name: string; size: number }>>([]) // 文件过大的文件列表（包含文件名和大小）
  const uploadedFileIdsRef = useRef<string[]>([]) // 用于在清理函数中访问最新的 uploadedFileIds
  const documentsProcessedRef = useRef<boolean>(false) // 用于在清理函数中访问最新的 documentsProcessed
  const uploadedFilesHashRef = useRef<string>('') // 用于记录已上传文件的哈希值，判断文件列表是否变化
  const fileToDocIdMapRef = useRef<Map<string, string>>(new Map()) // 文件名到 doc_id 的映射关系
  const deletingDocIdsRef = useRef<Set<string>>(new Set()) // 正在删除的文档ID集合，防止重复删除
  const [formData, setFormData] = useState<FormData>({
    parsingStrategy: '1', // "1"=快速解析
    segmentationStrategy: '1', // "1"=自动分段，"2"=自定义
    maxTokens: 512, // 默认512
    chunkOverlapPercent: 10, // 默认10
    enableGraphEnhancement: false, // 默认不启用图增强
    llmModelId: null, // 默认不选择模型
  })

  // 获取模型列表
  const {
    data: modelsData,
    isLoading: modelsLoading,
    error: modelsError,
  } = useModels({
    spaceId: user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID,
    is_active: true,
    size: 100,
    sort_by: 'update_time',
    sort_order: 'desc',
  })

  // 模型列表（转换为简单的 {id, name} 格式）
  const modelsList =
    modelsData?.items?.map(model => ({
      id: parseInt(model.id),
      name: String(model.name || ''),
    })) || []

  // 测试模型
  const testModelMutation = useTestModel()
  const [isTestingModel, setIsTestingModel] = useState(false)
  const [modelTestPassed, setModelTestPassed] = useState(false)
  const [testedModelId, setTestedModelId] = useState<number | null>(null) // 记录已测试通过的模型ID

  // 当模型选择改变时，重置测试状态
  useEffect(() => {
    if (formData.llmModelId !== testedModelId) {
      setModelTestPassed(false)
    }
  }, [formData.llmModelId, testedModelId])

  // 测试LLM模型
  const handleTestModel = async () => {
    if (!formData.llmModelId) {
      showError('请先选择LLM模型')
      return
    }

    setIsTestingModel(true)
    try {
      await testModelMutation.mutateAsync({
        id: String(formData.llmModelId),
        prompt: '你好，请用一句话介绍自己',
        spaceId: spaceId,
      })
      setModelTestPassed(true)
      setTestedModelId(Number(formData.llmModelId))
      showSuccess('模型测试成功！')
    } catch (error: any) {
      setModelTestPassed(false)
      const errorMessage = error?.response?.data?.detail || error?.message || '模型测试失败'
      showError(`模型测试失败: ${errorMessage}`)
    } finally {
      setIsTestingModel(false)
    }
  }

  const totalSteps = 2
  const spaceId = user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID

  const getFileKey = (file: File): string => `${file.name}-${file.size}-${file.lastModified}`

  const generateFilesHash = (files: File[]): string => (files.length === 0 ? '' : files.map(getFileKey).join('|'))

  const updateUploadedIds = () => {
    const currentUploadedIds = Array.from(fileToDocIdMapRef.current.values())
    setUploadedFileIds(currentUploadedIds)
    uploadedFileIdsRef.current = currentUploadedIds
  }

  const addFilesToSelection = (validFiles: File[]) => {
    setSelectedFiles(prev => {
      // 获取已存在文件的键集合
      const existingKeys = new Set(prev.map(file => getFileKey(file)))

      // 过滤掉已存在的文件
      const newFilesToAdd = validFiles.filter(file => !existingKeys.has(getFileKey(file)))

      // 如果没有新文件要添加，直接返回原列表
      if (newFilesToAdd.length === 0) {
        return prev
      }

      // 合并新文件到现有列表
      const newFiles = [...prev, ...newFilesToAdd]
      if (generateFilesHash(newFiles) !== uploadedFilesHashRef.current) {
        uploadedFilesHashRef.current = ''
        updateUploadedIds()
      }
      return newFiles
    })
  }

  const resetForm = () => {
    setCurrentStep(1)
    setSelectedFiles([])
    setUploadedFileIds([])
    setDocumentsProcessed(false)
    setIsTransitioning(false)
    uploadedFileIdsRef.current = []
    documentsProcessedRef.current = false
    uploadedFilesHashRef.current = ''
    fileToDocIdMapRef.current = new Map()
    setFormData({
      parsingStrategy: '1',
      segmentationStrategy: '1',
      maxTokens: 512,
      chunkOverlapPercent: 10,
      enableGraphEnhancement: false,
      llmModelId: null,
    })
  }

  const deleteUnprocessedDocuments = async (docIds: string[]) => {
    if (docIds.length === 0) return

    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

      const statusResponse = await KnowledgeBaseService.getDocumentStatus({
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        doc_id_list: docIds,
      })

      if (statusResponse.code === 200 && statusResponse.data?.items) {
        const documentsToDelete = statusResponse.data.items
          .filter(item => {
            if (!item.doc_id) return false
            const status = item.status?.toLowerCase()
            return status === 'uploading' || status === 'uploaded'
          })
          .map(item => item.doc_id!)
          .filter((id): id is string => !!id)

        if (documentsToDelete.length > 0) {
          await KnowledgeBaseService.deleteDocuments({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            document_ids: documentsToDelete,
          })
        }
      }
    } catch (error) {
      console.error('[AddDocumentDialog] Error deleting unprocessed documents:', error)
    }
  }

  const handleClose = () => {
    if (uploadedFileIds.length > 0 && onDocumentUploaded) {
      onDocumentUploaded()
    }
    resetForm()
    onClose()
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const ALLOWED_FILE_TYPES = ['.pdf', '.docx', '.txt', '.md']
  const MAX_DOCUMENT_NAME_LENGTH = 100
  const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB in bytes
  const MAX_FILE_SIZE_LABEL = '50MB' // 与 MAX_FILE_SIZE 一致，用于界面展示与国际化

  const validateFileType = (file: File): boolean => {
    const fileName = file.name.toLowerCase()
    const lastDotIndex = fileName.lastIndexOf('.')
    if (lastDotIndex === -1 || lastDotIndex === fileName.length - 1) {
      return false
    }
    return ALLOWED_FILE_TYPES.includes(fileName.substring(lastDotIndex))
  }

  // 验证文件名长度（不含后缀）
  const validateFileNameLength = (fileName: string): { valid: boolean; nameWithoutExt: string } => {
    const lastDotIndex = fileName.lastIndexOf('.')
    let nameWithoutExt: string
    if (lastDotIndex === -1 || lastDotIndex === fileName.length - 1) {
      nameWithoutExt = fileName
    } else {
      nameWithoutExt = fileName.substring(0, lastDotIndex)
    }
    return {
      valid: nameWithoutExt.length <= MAX_DOCUMENT_NAME_LENGTH,
      nameWithoutExt,
    }
  }

  const processFiles = (files: File[]) => {
    const validFiles: File[] = []
    const invalidFilesList: string[] = []
    const invalidFileNameLengthList: string[] = []
    const invalidFilesWithLongNameList: string[] = []
    const oversizedFilesList: Array<{ name: string; size: number }> = []

    // 获取当前已选择文件的键集合，用于去重
    const existingFileKeys = new Set(selectedFiles.map(file => getFileKey(file)))

    files.forEach(file => {
      const fileKey = getFileKey(file)

      // 检查文件是否已经存在于已选择的文件列表中
      if (existingFileKeys.has(fileKey)) {
        // 文件已存在，跳过（不显示错误，静默忽略）
        return
      }

      // 先检查文件类型
      const isInvalidType = !validateFileType(file)
      // 检查文件名长度（不含后缀）
      const lengthCheck = validateFileNameLength(file.name)
      const isInvalidLength = !lengthCheck.valid
      // 检查文件大小
      const isOversized = file.size > MAX_FILE_SIZE

      if (isInvalidType) {
        // 文件类型不支持
        invalidFilesList.push(file.name)
        // 如果文件名也过长，记录到 invalidFilesWithLongNameList
        if (isInvalidLength) {
          invalidFilesWithLongNameList.push(file.name)
        }
        return
      }

      // 文件类型支持，检查文件大小
      if (isOversized) {
        oversizedFilesList.push({ name: file.name, size: file.size })
        return
      }

      // 文件类型和大小都通过，再检查文件名长度
      if (isInvalidLength) {
        invalidFileNameLengthList.push(file.name)
        return
      }

      // 文件类型、大小和长度都通过，添加到有效文件列表
      validFiles.push(file)
      // 同时更新已存在文件的键集合，避免同一批文件中的重复
      existingFileKeys.add(fileKey)
    })

    // 显示无效文件类型弹窗
    if (invalidFilesList.length > 0) {
      setInvalidFiles(invalidFilesList)
      setInvalidFilesWithLongName(invalidFilesWithLongNameList)
      setShowInvalidFileDialog(true)
    }

    // 显示文件过大弹窗
    if (oversizedFilesList.length > 0) {
      setOversizedFiles(oversizedFilesList)
      setShowOversizedFileDialog(true)
    }

    // 显示文件名过长弹窗（仅针对文件类型支持但文件名过长的文件）
    if (invalidFileNameLengthList.length > 0) {
      setInvalidFileNameLengthFiles(invalidFileNameLengthList)
      setShowInvalidFileNameLengthDialog(true)
    }

    // 如果有有效文件，添加到选择列表
    if (validFiles.length > 0) {
      addFilesToSelection(validFiles)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFiles(Array.from(e.dataTransfer.files) as File[])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFiles(Array.from(e.target.files) as File[])
      e.target.value = ''
    }
  }

  const deleteDocumentIfNeeded = async (docId: string, fileName: string) => {
    // 如果该文档正在删除中，直接返回，防止重复删除
    if (deletingDocIdsRef.current.has(docId)) {
      console.log(`[AddDocumentDialog] Document ${docId} is already being deleted, skipping...`)
      return
    }

    // 标记为正在删除
    deletingDocIdsRef.current.add(docId)

    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

      const statusResponse = await KnowledgeBaseService.getDocumentStatus({
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        doc_id_list: [docId],
      })

      if (statusResponse.code === 200 && statusResponse.data?.items) {
        const docStatus = statusResponse.data.items.find(item => item.doc_id === docId)
        if (docStatus) {
          const status = docStatus.status?.toLowerCase()
          if (status === 'uploading' || status === 'uploaded') {
            try {
              await KnowledgeBaseService.deleteDocuments({
                space_id: spaceId,
                kb_id: knowledgeBase.id,
                document_ids: [docId],
              })
            } catch (deleteError: any) {
              // 如果文档已经被删除（404），不视为错误，静默处理
              const errorMessage = deleteError?.response?.data?.message || deleteError?.message || ''
              if (errorMessage.includes('not found') || errorMessage.includes('不存在')) {
                console.log(`[AddDocumentDialog] Document ${docId} already deleted, ignoring...`)
              } else {
                throw deleteError
              }
            }
          }
        }
      }
    } catch (error) {
      console.error(`[AddDocumentDialog] Failed to delete document for file ${fileName}:`, error)
    } finally {
      // 从正在删除的集合中移除
      deletingDocIdsRef.current.delete(docId)
    }
  }

  const removeFile = async (index: number) => {
    const fileToRemove = selectedFiles[index]
    if (!fileToRemove) {
      return // 文件不存在，直接返回
    }

    const fileKey = getFileKey(fileToRemove)
    const docIdToDelete = fileToDocIdMapRef.current.get(fileKey)

    // 如果该文档正在删除中，直接返回，防止重复删除
    if (docIdToDelete && deletingDocIdsRef.current.has(docIdToDelete)) {
      console.log(`[AddDocumentDialog] Document ${docIdToDelete} is already being deleted, skipping...`)
      return
    }

    // 先从映射中删除，防止快速双击时重复获取
    if (docIdToDelete) {
      fileToDocIdMapRef.current.delete(fileKey)
    }

    // 立即更新文件列表，提供即时反馈
    setSelectedFiles(prev => {
      const newFiles = prev.filter((_, i) => i !== index)
      if (newFiles.length === 0) {
        setUploadedFileIds([])
        uploadedFileIdsRef.current = []
        uploadedFilesHashRef.current = ''
        fileToDocIdMapRef.current = new Map()
      } else {
        if (docIdToDelete) {
          setUploadedFileIds(prev => prev.filter(id => id !== docIdToDelete))
          uploadedFileIdsRef.current = uploadedFileIdsRef.current.filter(id => id !== docIdToDelete)
        }
        uploadedFilesHashRef.current = generateFilesHash(newFiles)
      }
      return newFiles
    })

    // 异步删除文档（如果存在）
    if (docIdToDelete) {
      // 不等待删除完成，避免阻塞UI
      deleteDocumentIfNeeded(docIdToDelete, fileToRemove.name).catch(error => {
        console.error(`[AddDocumentDialog] Error deleting document ${docIdToDelete}:`, error)
      })
    }
  }

  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) {
      showError(t('knowledgeBases.addDocument.noFilesSelected'))
      return false
    }

    const filesToUpload = selectedFiles.filter(file => !fileToDocIdMapRef.current.has(getFileKey(file)))

    if (filesToUpload.length === 0) {
      updateUploadedIds()
      uploadedFilesHashRef.current = generateFilesHash(selectedFiles)
      showSuccess(t('knowledgeBases.addDocument.allFilesAlreadyUploaded') || '所有文件已上传')
      return true
    }

    setIsLoading(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

      const response = await KnowledgeBaseService.uploadFiles({
        files: filesToUpload,
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        metadata: JSON.stringify({ uploadTime: new Date().toISOString() }),
      })

      if (response && response.code === 200) {
        try {
          // Safely parse response data
          let documents: any[] = []
          if (response.data) {
            if (Array.isArray(response.data)) {
              documents = response.data
            } else if (typeof response.data === 'object' && response.data !== null) {
              const dataObj = response.data as any
              documents = Array.isArray(dataObj.documents) ? dataObj.documents : []
            }
          }

          // Extract doc IDs safely
          documents.forEach((doc: any, index: number) => {
            if (index < filesToUpload.length && doc) {
              const file = filesToUpload[index]
              const docId = doc.id || doc.doc_id
              if (docId && typeof docId === 'string') {
                fileToDocIdMapRef.current.set(getFileKey(file), docId)
              }
            }
          })

          updateUploadedIds()
          setDocumentsProcessed(false)
          documentsProcessedRef.current = false
          uploadedFilesHashRef.current = generateFilesHash(selectedFiles)

          showSuccess(t('knowledgeBases.addDocument.uploadSuccess'))
          return true
        } catch (parseError) {
          console.error('Error parsing upload response:', parseError)
          showError(t('knowledgeBases.addDocument.uploadFailed') || '上传成功但解析响应失败')
          return false
        }
      } else {
        const errorMsg = response?.message || t('knowledgeBases.addDocument.uploadFailed') || '上传失败'
        showError(errorMsg)
        return false
      }
    } catch (error) {
      console.error('Upload failed:', error)
      showError(t('knowledgeBases.addDocument.uploadFailed') || '上传失败')
      return false
    } finally {
      setIsLoading(false)
    }
  }

  // 设置文件参数
  const handleFileSettings = async () => {
    // 从 fileToDocIdMapRef 获取当前已上传文件的 doc_id
    const currentUploadedIds = Array.from(fileToDocIdMapRef.current.values())
    if (currentUploadedIds.length === 0) {
      showError(t('knowledgeBases.addDocument.noUploadedFiles'))
      return
    }

    // 验证：如果启用了图增强，必须选择模型
    if (formData.enableGraphEnhancement && !formData.llmModelId) {
      showError(t('knowledgeBases.addDocument.modelRequired') || '启用图增强需要选择LLM模型')
      return
    }

    setIsLoading(true)
    try {
      const { KnowledgeBaseService } = await import('@test-agentstudio/api-client')

      const processRequest: ProcessDocumentsRequest = {
        space_id: spaceId,
        kb_id: knowledgeBase.id,
        doc_id_list: currentUploadedIds,
        parsing_strategy: {
          strategy_type: formData.parsingStrategy,
          strategy_config: {},
        },
        segmentation_strategy: {
          strategy_type: formData.segmentationStrategy,
          strategy_config: {
            max_tokens: formData.maxTokens,
            chunk_overlap_percent: formData.chunkOverlapPercent,
          },
        },
        indexing_strategy: {
          enable_graph_enhancement: formData.enableGraphEnhancement,
          llm_model_id: formData.enableGraphEnhancement && formData.llmModelId ? Number(formData.llmModelId) : undefined,
        },
      }

      const response = await KnowledgeBaseService.processDocuments(processRequest)

      if (response.code === 200) {
        // 标记文档已处理（索引已开始）
        setDocumentsProcessed(true)
        documentsProcessedRef.current = true
        // 更新 uploadedFileIds
        setUploadedFileIds(currentUploadedIds)
        uploadedFileIdsRef.current = currentUploadedIds
        showSuccess(t('knowledgeBases.addDocument.settingsSuccess'))
        onSuccess(currentUploadedIds) // 传递正在处理的文档ID列表
      } else {
        showError(response.message || t('knowledgeBases.addDocument.settingsFailed'))
      }
    } catch (error) {
      console.error('Settings failed:', error)
      showError(t('knowledgeBases.addDocument.settingsFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleNext = async () => {
    // Prevent multiple simultaneous calls
    if (isLoading) {
      return
    }

    try {
      if (currentStep === 1) {
        if (selectedFiles.length === 0) {
          showError(t('knowledgeBases.addDocument.noFilesSelected'))
          return
        }

        const allFilesUploaded = selectedFiles.every(file => fileToDocIdMapRef.current.has(getFileKey(file)))

        if (allFilesUploaded) {
          updateUploadedIds()
          uploadedFilesHashRef.current = generateFilesHash(selectedFiles)
          // Set transitioning state to prevent button changes during transition
          setIsTransitioning(true)
          // Use double requestAnimationFrame to ensure all DOM updates are complete
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              setCurrentStep(2)
              // Clear transitioning state after a short delay
              setTimeout(() => setIsTransitioning(false), 100)
            })
          })
        } else {
          const success = await handleUploadFiles()
          if (success) {
            // Verify we have doc IDs before advancing
            const currentUploadedIds = Array.from(fileToDocIdMapRef.current.values())
            if (currentUploadedIds.length > 0) {
              // Set transitioning state to prevent button changes during transition
              setIsTransitioning(true)
              // Use double requestAnimationFrame to ensure all DOM updates are complete
              requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                  setCurrentStep(2)
                  // Clear transitioning state after a short delay
                  setTimeout(() => setIsTransitioning(false), 100)
                })
              })
            } else {
              showError(t('knowledgeBases.addDocument.uploadFailed') || '上传成功但无法获取文档ID，请重试')
            }
          }
        }
      } else if (currentStep === 2) {
        await handleFileSettings()
      }
    } catch (error) {
      console.error('handleNext error:', error)
      showError(t('knowledgeBases.addDocument.uploadFailed') || `操作失败: ${error instanceof Error ? error.message : String(error)}`)
    }
  }

  const handlePrevious = () => {
    setCurrentStep(1)
  }

  const handleCloseWithCleanup = async () => {
    if (uploadedFileIdsRef.current.length > 0 && !documentsProcessedRef.current) {
      await deleteUnprocessedDocuments(uploadedFileIdsRef.current)
    }
    handleClose()
  }

  useEffect(() => {
    uploadedFileIdsRef.current = uploadedFileIds
    documentsProcessedRef.current = documentsProcessed
  }, [uploadedFileIds, documentsProcessed])

  // 页面刷新时清理未处理的文档
  useEffect(() => {
    if (!open) return

    const cleanupDocuments = () => {
      // 从 fileToDocIdMapRef 获取所有已上传的文档ID（更可靠，不依赖状态更新）
      const allUploadedDocIds = Array.from(fileToDocIdMapRef.current.values())

      // 只在有未处理的文档时才执行清理
      if (allUploadedDocIds.length > 0 && !documentsProcessedRef.current) {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
        const token = localStorage.getItem('access_token')

        // 直接删除文档（不先查询状态，因为我们已经知道这些文档是未处理的）
        fetch(`${apiBaseUrl}/knowledge-base/documents/delete`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            space_id: spaceId,
            kb_id: knowledgeBase.id,
            document_ids: allUploadedDocIds,
          }),
          keepalive: true, // 允许在页面卸载后继续发送请求
        }).catch(() => {
          // 静默处理错误，不影响用户体验
        })
      }
    }

    const handlePageHide = () => cleanupDocuments()
    const handleBeforeUnload = () => cleanupDocuments()

    window.addEventListener('pagehide', handlePageHide)
    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('pagehide', handlePageHide)
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [open, knowledgeBase.id, spaceId])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={handleCloseWithCleanup}></div>

        <div className="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-xl font-semibold text-gray-900">{t('knowledgeBases.addDocument.title')}</h2>
            <button onClick={handleCloseWithCleanup} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* 步骤指示器 */}
          <div className="px-6 py-4 border-b">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full ${
                    currentStep >= 1 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > 1 ? <Check className="w-4 h-4" /> : '1'}
                </div>
                <div className={`ml-3 ${currentStep >= 1 ? 'text-blue-600' : 'text-gray-500'} font-medium`}>{t('knowledgeBases.addDocument.steps.upload')}</div>
              </div>
              <div className="flex-1 h-1 mx-4 bg-gray-200">
                <div
                  className={`h-1 ${currentStep > 1 ? 'bg-blue-500' : 'bg-transparent'} transition-colors`}
                  style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
                />
              </div>
              <div className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full ${
                    currentStep >= 2 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > 2 ? <Check className="w-4 h-4" /> : '2'}
                </div>
                <div className={`ml-3 ${currentStep >= 2 ? 'text-blue-600' : 'text-gray-500'} font-medium`}>
                  {t('knowledgeBases.addDocument.steps.settings')}
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 max-h-[60vh] overflow-y-auto">
            {currentStep === 1 && (
              <div key="step-1">
                <p className="text-gray-600 mb-6">{t('knowledgeBases.addDocument.uploadDescription')}</p>

                {/* 文件上传区域 */}
                <div
                  className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                    dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <div className="text-sm text-gray-600 mb-2">{t('knowledgeBases.addDocument.dragAndDrop')}</div>
                  <div className="text-xs text-gray-500 mb-2">{t('knowledgeBases.addDocument.supportedFormats')}</div>
                  <div className="text-xs text-orange-600 mb-4 font-medium">{t('knowledgeBases.addDocument.fileSizeLimit', { size: MAX_FILE_SIZE_LABEL })}</div>
                  <input type="file" multiple onChange={handleFileChange} accept=".pdf,.docx,.txt,.md" className="hidden" id="file-upload" />
                  <label
                    htmlFor="file-upload"
                    className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 cursor-pointer inline-block"
                  >
                    {t('knowledgeBases.addDocument.selectFiles')}
                  </label>
                </div>

                {/* 已选择的文件列表 */}
                {selectedFiles.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">{t('knowledgeBases.addDocument.selectedFiles')}</h3>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {selectedFiles.map((file, index) => {
                        const isUploaded = fileToDocIdMapRef.current.has(getFileKey(file))
                        return (
                          <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                            <div className="flex items-center space-x-3">
                              <FileText className="w-5 h-5 text-gray-400" />
                              <div>
                                <div className="text-sm font-medium text-gray-900 truncate max-w-xs md:max-w-sm lg:max-w-md" title={file.name}>
                                  {file.name}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : `${(file.size / 1024).toFixed(2)} KB`}
                                  {isUploaded && <span className="ml-2 text-green-600">✓ {t('document.uploaded') || '已上传'}</span>}
                                </div>
                              </div>
                            </div>
                            <button type="button" onClick={() => removeFile(index)} className="text-red-500 hover:text-red-700">
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        )
                      })}
                    </div>
                    {selectedFiles.length > 0 && selectedFiles.every(file => fileToDocIdMapRef.current.has(getFileKey(file))) && (
                      <div className="mt-2 text-xs text-green-600">{t('document.allFilesUploaded') || '所有文件已上传，可直接进入下一步'}</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {currentStep === 2 && (
              <div key="step-2">
                <p className="text-gray-600 mb-6">{t('knowledgeBases.addDocument.settingsDescription')}</p>

                <div className="space-y-6">
                  {/* 解析策略 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t('knowledgeBases.addDocument.parsingStrategy')}</label>
                    <select
                      value={formData.parsingStrategy}
                      onChange={e => setFormData(prev => ({ ...prev, parsingStrategy: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">{t('knowledgeBases.addDocument.quickParsing')}</option>
                    </select>
                  </div>

                  {/* 分段策略 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t('knowledgeBases.addDocument.segmentationStrategy')}</label>
                    <select
                      value={formData.segmentationStrategy}
                      onChange={e => setFormData(prev => ({ ...prev, segmentationStrategy: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">{t('knowledgeBases.addDocument.autoSegmentation')}</option>
                      <option value="2">{t('knowledgeBases.addDocument.customSegmentation')}</option>
                    </select>

                    {formData.segmentationStrategy === '2' && (
                      <div className="mt-4 space-y-4 p-4 bg-gray-50 rounded-lg">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">最大Token数 (16-1024)</label>
                          <input
                            type="text"
                            value={formData.maxTokens === -1 ? '' : formData.maxTokens}
                            onChange={e => {
                              const inputValue = e.target.value
                              // 允许用户清空输入框
                              if (inputValue === '') {
                                setFormData(prev => ({ ...prev, maxTokens: -1 as any }))
                                return
                              }
                              // 只允许数字输入（不允许负号）
                              if (/^\d*$/.test(inputValue)) {
                                const value = parseInt(inputValue)
                                if (!isNaN(value)) {
                                  // 允许输入任何数字，不进行范围限制
                                  setFormData(prev => ({ ...prev, maxTokens: value }))
                                }
                              }
                            }}
                            onBlur={e => {
                              const inputValue = e.target.value
                              if (inputValue === '') {
                                // 如果为空，设置为最小值
                                setFormData(prev => ({ ...prev, maxTokens: 16 }))
                                return
                              }
                              const value = parseInt(inputValue)
                              if (isNaN(value) || value < 16) {
                                setFormData(prev => ({ ...prev, maxTokens: 16 }))
                              } else if (value > 1024) {
                                setFormData(prev => ({ ...prev, maxTokens: 1024 }))
                              }
                            }}
                            min={16}
                            max={1024}
                            step={1}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">分段重叠百分比 (0-50)</label>
                          <input
                            type="text"
                            value={formData.chunkOverlapPercent === -1 ? '' : formData.chunkOverlapPercent}
                            onChange={e => {
                              const inputValue = e.target.value
                              // 允许用户清空输入框
                              if (inputValue === '') {
                                setFormData(prev => ({ ...prev, chunkOverlapPercent: -1 as any }))
                                return
                              }
                              // 只允许数字输入（不允许负号）
                              if (/^\d*$/.test(inputValue)) {
                                const value = parseInt(inputValue)
                                if (!isNaN(value)) {
                                  // 允许输入任何数字，不进行范围限制
                                  setFormData(prev => ({ ...prev, chunkOverlapPercent: value }))
                                }
                              }
                            }}
                            onBlur={e => {
                              const inputValue = e.target.value
                              if (inputValue === '') {
                                // 如果为空，设置为最小值
                                setFormData(prev => ({ ...prev, chunkOverlapPercent: 0 }))
                                return
                              }
                              const value = parseInt(inputValue)
                              if (isNaN(value) || value < 0) {
                                setFormData(prev => ({ ...prev, chunkOverlapPercent: 0 }))
                              } else if (value > 50) {
                                setFormData(prev => ({ ...prev, chunkOverlapPercent: 50 }))
                              }
                            }}
                            onKeyDown={e => {
                              // 处理上下键，防止在边界时继续变化
                              if (e.key === 'ArrowUp') {
                                e.preventDefault()
                                setFormData(prev => ({
                                  ...prev,
                                  chunkOverlapPercent: Math.min(50, prev.chunkOverlapPercent + 1),
                                }))
                              } else if (e.key === 'ArrowDown') {
                                e.preventDefault()
                                setFormData(prev => ({
                                  ...prev,
                                  chunkOverlapPercent: Math.max(0, prev.chunkOverlapPercent - 1),
                                }))
                              }
                            }}
                            step="1"
                            min="0"
                            max="50"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 图增强配置 */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="enableGraphEnhancement"
                          checked={formData.enableGraphEnhancement}
                          onChange={e => setFormData(prev => ({ ...prev, enableGraphEnhancement: e.target.checked }))}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <label htmlFor="enableGraphEnhancement" className="text-sm font-medium text-gray-700 cursor-pointer flex items-center space-x-2">
                          <span>{t('knowledgeBases.addDocument.enableGraphEnhancement')}</span>
                          <Tooltip
                            title={
                              t('knowledgeBases.addDocument.enableGraphEnhancementTooltip') ||
                              '图增强检索开启可以获取更好的检索效果，但是会增加耗时以及消耗额外的大模型token。'
                            }
                            arrow
                            placement="top"
                          >
                            <HelpCircle className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" />
                          </Tooltip>
                        </label>
                      </div>
                    </div>

                    {/* 勾选文档图构建后自动展示的提示：紧贴该行下方，与小问号悬停提示互不干扰 */}
                    {formData.enableGraphEnhancement && (
                      <div
                        className="flex items-start gap-2 px-3 py-2 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800"
                        role="status"
                        aria-live="polite"
                      >
                        <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                        <span>
                          {t('knowledgeBases.addDocument.enableGraphEnhancementTooltip') ||
                            '构建文档图可以获取更好的检索效果，但是会增加耗时以及消耗额外的大模型token。'}
                        </span>
                      </div>
                    )}

                    {/* 模型选择器 - 仅在启用图增强时显示 */}
                    {formData.enableGraphEnhancement && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {t('knowledgeBases.addDocument.selectLLMModel') || '选择LLM模型'}
                          <span className="text-red-500 ml-1">*</span>
                        </label>
                        <div className="flex items-center gap-2">
                          <select
                            value={formData.llmModelId || ''}
                            onChange={e => setFormData(prev => ({ ...prev, llmModelId: e.target.value ? Number(e.target.value) : null }))}
                            className={`flex-1 min-w-0 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                              modelTestPassed && formData.llmModelId === testedModelId ? 'border-green-500 bg-green-50' : 'border-gray-300'
                            }`}
                            style={!formData.llmModelId ? { color: '#9ca3af' } : {}}
                            disabled={modelsLoading || isTestingModel}
                          >
                            <option value="" disabled hidden style={{ color: '#9ca3af' }}>
                              {t('knowledgeBases.addDocument.selectModelPlaceholder') || '请选择模型'}
                            </option>
                            {modelsList.map(model => (
                              <option key={model.id} value={model.id} style={{ color: '#111827' }}>
                                {model.name}
                              </option>
                            ))}
                          </select>
                          {/* 测试按钮 */}
                          <Tooltip title={modelTestPassed && formData.llmModelId === testedModelId ? '测试已通过' : '测试模型连接'}>
                            <span>
                              <button
                                type="button"
                                onClick={handleTestModel}
                                disabled={!formData.llmModelId || isTestingModel}
                                className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg transition-all duration-200 ${
                                  modelTestPassed && formData.llmModelId === testedModelId
                                    ? 'text-green-600 bg-green-50 hover:bg-green-100'
                                    : !formData.llmModelId || isTestingModel
                                      ? 'text-gray-400 bg-gray-100 cursor-not-allowed'
                                      : 'text-blue-600 hover:text-blue-700 hover:bg-blue-50'
                                }`}
                              >
                                {isTestingModel ? (
                                  <Loader2 className="w-5 h-5 animate-spin" />
                                ) : modelTestPassed && formData.llmModelId === testedModelId ? (
                                  <CheckCircle className="w-5 h-5" />
                                ) : (
                                  <Play className="w-5 h-5" />
                                )}
                              </button>
                            </span>
                          </Tooltip>
                        </div>
                        {modelsLoading && <p className="mt-1 text-xs text-gray-500">{t('common.loading') || '加载中...'}</p>}
                        {!!modelsError && <p className="mt-1 text-xs text-red-500">{t('knowledgeBases.addDocument.loadModelsFailed') || '加载模型列表失败'}</p>}
                        {formData.enableGraphEnhancement && !formData.llmModelId && (
                          <p className="mt-1 text-xs text-amber-600">{t('knowledgeBases.addDocument.modelRequired') || '启用图增强需要选择LLM模型'}</p>
                        )}
                        {formData.llmModelId && !modelTestPassed && <p className="mt-1 text-xs text-amber-600">请点击测试按钮验证模型可用性</p>}
                        {modelTestPassed && formData.llmModelId === testedModelId && (
                          <p className="mt-1 text-xs text-green-600 flex items-center">
                            <CheckCircle className="w-3 h-3 mr-1" />
                            模型测试通过
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 底部按钮 */}
          <div className="flex items-center justify-between p-6 border-t bg-gray-50">
            <button type="button" onClick={handleCloseWithCleanup} className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white">
              {t('common.cancel')}
            </button>

            <div className="flex items-center space-x-2">
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={handlePrevious}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-white flex items-center"
                >
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  {t('common.buttons.previous')}
                </button>
              )}

              <button
                type="button"
                onClick={handleNext}
                disabled={
                  isLoading ||
                  isTransitioning ||
                  (currentStep === 1 && selectedFiles.length === 0) ||
                  (currentStep === 2 && formData.enableGraphEnhancement && (!formData.llmModelId || !modelTestPassed))
                }
                className={`px-4 py-2 rounded-lg flex items-center ${
                  currentStep === 2
                    ? formData.enableGraphEnhancement && (!formData.llmModelId || !modelTestPassed)
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                    : selectedFiles.length > 0
                      ? 'bg-blue-500 text-white hover:bg-blue-600'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                } disabled:opacity-50`}
              >
                {isLoading ? (
                  <span key="loading-text">{t('common.saving')}</span>
                ) : (
                  <span key="next-text" className="flex items-center">
                    {t('common.buttons.next')}
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 无效文件类型提示弹窗 */}
      {showInvalidFileDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => setShowInvalidFileDialog(false)} />

          {/* Modal */}
          <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
            {/* Close button */}
            <button onClick={() => setShowInvalidFileDialog(false)} className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 transition-colors">
              <X className="w-6 h-6" />
            </button>

            {/* Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-orange-600" />
              </div>
            </div>

            {/* Content */}
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">不支持的文件类型</h3>
              <div className="text-left text-gray-600 text-base leading-relaxed space-y-3">
                <p>以下文件类型不支持上传：</p>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <ul className="list-disc list-inside space-y-1">
                    {invalidFiles.map((fileName, index) => (
                      <li key={index} className="text-gray-800 font-medium text-sm">
                        <span className="truncate block max-w-full" title={fileName}>
                          {fileName}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <p className="text-gray-600">
                  仅支持以下格式：<span className="font-semibold text-blue-600">{ALLOWED_FILE_TYPES.join('、')}</span>
                </p>
                {invalidFilesWithLongName.length > 0 && (
                  <p className="text-gray-600 mt-2">
                    文件名长度不能超过 <span className="font-semibold text-blue-600">{MAX_DOCUMENT_NAME_LENGTH}</span> 个字符
                  </p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-center">
              <button
                onClick={() => setShowInvalidFileDialog(false)}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 文件名过长提示弹窗 */}
      {showInvalidFileNameLengthDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => setShowInvalidFileNameLengthDialog(false)} />

          {/* Modal */}
          <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
            {/* Close button */}
            <button
              onClick={() => setShowInvalidFileNameLengthDialog(false)}
              className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>

            {/* Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-orange-600" />
              </div>
            </div>

            {/* Content */}
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">文件名过长</h3>
              <div className="text-left text-gray-600 text-base leading-relaxed space-y-3">
                <p>以下文件的名称过长（最多 {MAX_DOCUMENT_NAME_LENGTH} 个字符）：</p>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <ul className="list-disc list-inside space-y-1">
                    {invalidFileNameLengthFiles.map((fileName, index) => {
                      const lengthCheck = validateFileNameLength(fileName)
                      return (
                        <li key={index} className="text-gray-800 font-medium text-sm flex items-start gap-2">
                          <span className="truncate flex-1 min-w-0" title={fileName}>
                            {fileName}
                          </span>
                          <span className="text-red-600 flex-shrink-0">({lengthCheck.nameWithoutExt.length} 个字符)</span>
                        </li>
                      )
                    })}
                  </ul>
                </div>
                <p className="text-gray-600">
                  请将文件名缩短至 <span className="font-semibold text-blue-600">{MAX_DOCUMENT_NAME_LENGTH}</span> 个字符以内后重新上传。
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-center">
              <button
                onClick={() => setShowInvalidFileNameLengthDialog(false)}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 文件过大提示弹窗 */}
      {showOversizedFileDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={() => setShowOversizedFileDialog(false)} />

          {/* Modal */}
          <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 transform transition-all">
            {/* Close button */}
            <button onClick={() => setShowOversizedFileDialog(false)} className="absolute top-6 right-6 text-gray-400 hover:text-gray-600 transition-colors">
              <X className="w-6 h-6" />
            </button>

            {/* Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-orange-600" />
              </div>
            </div>

            {/* Content */}
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">{t('knowledgeBases.addDocument.oversizedTitle')}</h3>
              <div className="text-left text-gray-600 text-base leading-relaxed space-y-3">
                <p>{t('knowledgeBases.addDocument.filesExceedLimit', { size: MAX_FILE_SIZE_LABEL })}</p>
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <ul className="list-disc list-inside space-y-1">
                    {oversizedFiles.map((fileInfo, index) => {
                      const fileSizeMB = (fileInfo.size / (1024 * 1024)).toFixed(2)
                      return (
                        <li key={index} className="text-gray-800 font-medium text-sm flex items-start gap-2">
                          <span className="truncate flex-1 min-w-0" title={fileInfo.name}>
                            {fileInfo.name}
                          </span>
                          <span className="text-red-600 flex-shrink-0">({fileSizeMB} MB)</span>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-center">
              <button
                onClick={() => setShowOversizedFileDialog(false)}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AddDocumentDialog
