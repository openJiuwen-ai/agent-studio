import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUpdateAgent, useCopyAgent, AgentService } from '@test-agentstudio/api-client'
import { useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/useAuthStore'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { DeleteDialogState, Agent } from '../components/types'
import { EditingState } from '@/components/Common/common-grid'

export interface SnackbarHelpers {
  showSuccess: (message: string, duration?: number) => void
  showError: (message: string, duration?: number) => void
  showWarning?: (message: string, duration?: number) => void
}

interface ImportConflict {
  isOpen: boolean
  agentName: string
  data: any
  isZip?: boolean
}

export function useAgentActions(refetchAgents?: () => void, snackbarHelpers?: SnackbarHelpers) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccess, showError, showWarning } = snackbarHelpers || { showSuccess: () => {}, showError: () => {}, showWarning: () => {} }
  const { user } = useAuthStore()

  const { mutate: updateAgent, isLoading: isUpdating } = useUpdateAgent()
  const { mutate: copyAgent, isLoading: isCopying } = useCopyAgent()

  // Delete states
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState>({
    isOpen: false,
    agentId: '',
    agentName: '',
  })
  const [isDeleting, setIsDeleting] = useState(false)

  // Import states
  const [isImporting, setIsImporting] = useState(false)
  const [importConflict, setImportConflict] = useState<ImportConflict | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Editing states
  const [editingState, setEditingState] = useState<EditingState>({
    id: null,
    field: null,
    value: '',
    isEditing: false,
  })
  const [savingAgentId, setSavingAgentId] = useState<string | null>(null)

  const refreshCache = async () => {
    await queryClient.invalidateQueries({
      queryKey: ['agents', 'api', 'list'],
      exact: false,
    })
    await queryClient.invalidateQueries({
      queryKey: ['agents', 'search'],
      exact: false,
    })
    if (refetchAgents) {
      await refetchAgents()
    }
  }

  const handleDelete = (agent: Agent) => {
    setDeleteDialog({ isOpen: true, agentId: agent.agent_id, agentName: agent.agent_name })
  }

  const closeDeleteDialog = () => {
    setDeleteDialog({ isOpen: false, agentId: '', agentName: '' })
  }

  const confirmDelete = async () => {
    if (!deleteDialog.agentId) return

    setIsDeleting(true)
    try {
      const response = await AgentService.deleteAgent({
        space_id: getDefaultSpaceId(),
        agent_id: deleteDialog.agentId,
      })

      if (response.code === 200) {
        await refreshCache()
        showSuccess(t('common.messages.agentDeleteSuccess'))
        closeDeleteDialog()
      } else {
        console.error('删除智能体失败:', response)
        showError(`${t('common.messages.agentDeleteFailed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (err) {
      const error = err as Error
      console.error('删除智能体异常:', error)
      showError(`${t('common.messages.agentDeleteFailed')}: ${error.message || t('common.messages.unknownError')}`)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleCopy = (agent: Agent) => {
    copyAgent(
      {
        space_id: user?.spaceId || getDefaultSpaceId(),
        agent_id: agent.agent_id,
      },
      {
        onSuccess: response => {
          if (response.code === 200) {
            refreshCache()
            showSuccess(`${t('common.messages.agentCopySuccess')}: "${agent.agent_name}"`)
          } else {
            showError(`${t('common.messages.agentCopyFailed')}: ${response.message || t('common.messages.unknownError')}`)
          }
        },
        onError: err => {
          const error = err as Error
          console.error('复制智能体失败:', error)
          showError(`${t('common.messages.agentCopyFailed')}: ${error.message || t('common.messages.unknownError')}`)
        },
      },
    )
  }

  const handleExport = async (agent: Agent) => {
    try {
      const response = await AgentService.exportAgent({
        space_id: user?.spaceId || getDefaultSpaceId(),
        agent_id: agent.agent_id,
      })

      if (response.isBlob) {
        // 处理二进制文件(ZIP)下载
        const url = window.URL.createObjectURL(response.blob)
        const a = document.createElement('a')
        a.href = url
        a.download = response.filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess(t('agents.agentList.messages.exportSuccess'))
      } else if (response.code === 200 && response.data) {
        // 处理JSON下载
        // 格式化时间戳 YYYYMMDDHHmmss
        const now = new Date()
        const timestamp = now.getFullYear().toString() +
          (now.getMonth() + 1).toString().padStart(2, '0') +
          now.getDate().toString().padStart(2, '0') +
          now.getHours().toString().padStart(2, '0') +
          now.getMinutes().toString().padStart(2, '0') +
          now.getSeconds().toString().padStart(2, '0')
        
        // 使用导出数据中的 agent 名称，如果没有则使用传入的 agent 名称
        const exportName = response.data.agent?.agent_name || agent.agent_name || 'agent'
        const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        // 使用短横线连接，保持一致性
        a.download = `${exportName}-export-${timestamp}.json`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        showSuccess(t('agents.agentList.messages.exportSuccess'))
      } else {
        showError(`${t('common.messages.agentExportFailed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error) {
      console.error('Agent export exception:', error)
      showError(`${t('common.messages.agentExportException')}: ${error instanceof Error ? error.message : t('common.messages.unknownError')}`)
    }
  }

  // 发布管理函数
  const handlePublish = (agent: Agent) => {
    navigate(`/dashboard/agents/${agent.agent_id}/publish`)
  }

  const executeImport = async (importData: any, overwrite: boolean) => {
    try {
      setIsImporting(true)
      const response = await AgentService.importAgent({
        space_id: user?.spaceId || getDefaultSpaceId(),
        import_data: importData,
        overwrite: overwrite,
      })

      if (response.code === 200) {
        const warnings = response.data?.warnings
        if (warnings && Array.isArray(warnings) && warnings.length > 0 && showWarning) {
          const warningMsg = warnings.join('; ')
          showWarning(`${t('common.messages.agentImportWarning')}: ${warningMsg}`, 10000)
        } else {
          showSuccess(overwrite ? t('common.messages.agentImportOverwriteSuccess') : t('common.messages.agentImportSuccess'))
        }

        await refreshCache()
        setImportConflict(null)
      } else {
        showError(`${t('common.messages.agentImportFailed')}: ${response.message || t('common.messages.unknownError')}`)
      }
    } catch (error) {
      console.error('Import exception:', error)
      showError(`${t('common.messages.agentImportException')}: ${error instanceof Error ? error.message : t('common.messages.agentImportFileParseError')}`)
    } finally {
      setIsImporting(false)
    }
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 检查文件类型
    const isZip = file.name.endsWith('.zip') || file.type.includes('zip') || file.type.includes('compressed')
    const isJson = file.name.endsWith('.json') || file.type.includes('json')

    if (!isZip && !isJson) {
      event.target.value = ''
      showError('无效的文件格式，请选择 .json 或 .zip 文件')
      return
    }

    event.target.value = ''

    const reader = new FileReader()
    reader.onload = async e => {
      try {
        let importData: any

        if (isZip) {
          // 读取ZIP文件中的JSON配置
          const arrayBuffer = e.target?.result as ArrayBuffer
          const zip = new (await import('jszip')).default()
          const zipContent = await zip.loadAsync(arrayBuffer)

          // 查找配置文件
          let configFile: any = null
          for (const filename of Object.keys(zipContent.files)) {
            if (filename.endsWith('.json') && filename.includes('-export-')) {
              configFile = zipContent.files[filename]
              break
            }
          }

          // 如果没找到带-export-的，找第一个JSON文件
          if (!configFile) {
            for (const filename of Object.keys(zipContent.files)) {
              if (filename.endsWith('.json')) {
                configFile = zipContent.files[filename]
                break
              }
            }
          }

          if (!configFile) {
            throw new Error('ZIP文件中未找到配置文件')
          }

          const jsonContent = await configFile.async('text')
          importData = JSON.parse(jsonContent)
        } else {
          // JSON文件直接解析
          const content = e.target?.result as string
          importData = JSON.parse(content)
        }

        if (!importData.agent || !importData.dependencies) {
          throw new Error(t('common.messages.agentImportInvalidFormat'))
        }

        const agentId = importData.agent.agent_id
        const spaceId = user?.spaceId || getDefaultSpaceId()

        try {
          const checkRes = await AgentService.getAgentDetail({
            space_id: spaceId,
            agent_id: agentId,
          })

          if (checkRes.code === 200) {
            setImportConflict({
              isOpen: true,
              agentName: importData.agent.agent_name,
              data: isZip ? file : importData,
            })
          } else {
            executeImport(isZip ? file : importData, false)
          }
        } catch (err) {
          executeImport(isZip ? file : importData, false)
        }
      } catch (error) {
        console.error('File parse exception:', error)
        showError(`${t('common.messages.agentFileParseException')}: ${error instanceof Error ? error.message : t('common.messages.unknownError')}`)
      }
    }

    if (isZip) {
      reader.readAsArrayBuffer(file)
    } else {
      reader.readAsText(file)
    }
  }

  const closeImportConflict = () => {
    setImportConflict(null)
  }

  // Editing functions
  const startEditing = (agent: Agent, field: 'name' | 'description') => {
    setEditingState({
      id: agent.agent_id,
      field,
      value: field === 'name' ? agent.agent_name : agent.description || '',
      isEditing: true,
    })

    setTimeout(() => {
      const inputElement = document.getElementById(`edit-input-${agent.agent_id}-${field}`)
      if (inputElement) {
        inputElement.focus()
        if (inputElement instanceof HTMLInputElement || inputElement instanceof HTMLTextAreaElement) {
          inputElement.select()
        }
      }
    }, 100)
  }

  const cancelEditing = () => {
    setEditingState({
      id: null,
      field: null,
      value: '',
      isEditing: false,
    })
  }

  const saveEdit = (agentId: string, icon: string, agentType: string, agentName: string, agentDescription: string): void => {
    setSavingAgentId(agentId)

    updateAgent(
      {
        agent_id: agentId,
        agent_name: editingState.field === 'name' ? editingState.value : agentName,
        space_id: user?.spaceId || getDefaultSpaceId(),
        description: editingState.field === 'description' ? editingState.value : agentDescription,
        icon: icon,
        agent_type: agentType,
      },
      {
        onSuccess: (response) => {
          if (response.code === 200) {
            showSuccess(t('common.messages.agentUpdateSuccess'))
            cancelEditing()
          } else {
            showError(`${t('common.messages.error')}: ${response.message || t('common.messages.unknownError')}`)
          }
          setSavingAgentId(null)
        },
        onError: (error) => {
          const err = error as Error
          console.error('更新智能体失败:', err)
          showError(`${t('common.messages.error')}: ${err.message || t('common.messages.unknownError')}`)
          setSavingAgentId(null)
        },
      },
    )
  }

  const updateValue = (value: string) => {
    setEditingState((prev) => ({ ...prev, value }))
  }

  // 处理保存编辑（从 agent 对象中获取 icon 和 agent_type）
  const handleSaveEdit = useCallback(
    (agent: Agent) => {
      saveEdit(agent.agent_id, agent.icon || '🤖', agent.agent_type || 'react', agent.agent_name, agent.description)
    },
    [saveEdit],
  )

  return {
    // Delete
    deleteDialog,
    setDeleteDialog,
    closeDeleteDialog,
    isDeleting,
    handleDelete,
    confirmDelete,

    // Copy
    isCopying,
    handleCopy,

    // Export
    handleExport,

    // Publish
    handlePublish,

    // Import
    isImporting,
    importConflict,
    fileInputRef,
    handleImportClick,
    handleFileChange,
    executeImport,
    closeImportConflict,

    // Editing
    editingState,
    savingAgentId,
    startEditing,
    cancelEditing,
    saveEdit,
    handleSaveEdit,
    updateValue,

    // Common
    isUpdating,
    updateAgent,
    refreshCache,
  }
}
