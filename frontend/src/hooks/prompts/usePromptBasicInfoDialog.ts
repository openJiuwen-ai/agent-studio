import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { PromptService, ApiError } from '@test-agentstudio/api-client'

// 基本信息类型定义
interface BasicInfo {
  key: string
  name: string
  description: string
  tags: string[]
  isPublic: boolean
}

// Prompt 状态类型定义
interface PromptState {
  key: string
  name: string
  description: string
  category: string
  content: string
  tags: string[]
  isPublic: boolean
  language: string
}

// 复制提示词数据类型定义
interface CopyPromptData {
  key: string
  name: string
  description: string
  tags: string[]
  isPublic: boolean
  version: string
}

// 版本数据类型定义
interface VersionData {
  id: string
  version: string
  content: string
  parameters: any[]
  modelConfig: any
  createdAt: string
  isActive: boolean
  isDraft?: boolean
  description: string
  author: string
  baseVersion: string
  associations: {
    relationObjs: any[]
  }
  performance: {
    usage: number
    rating: number
    successRate: number
  }
}

// Hook 参数接口
interface UsePromptBasicInfoDialogProps {
  id?: string
  isNew?: boolean
  workspaceId?: string
  userId?: string
  // 外部状态和函数
  prompt: PromptState
  setPrompt: (prompt: PromptState | ((prev: PromptState) => PromptState)) => void
  setLoading: (loading: boolean) => void
  setHasUnsavedChanges: (hasChanges: boolean) => void
  // 复制功能相关
  selectedVersion?: string | null
  getDisplayVersions?: () => VersionData[]
  // Snackbar 函数
  showSnackbar: (message: string, severity?: 'success' | 'error' | 'warning' | 'info', duration?: number) => void
  setSnackbar: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void
}

// Hook 返回值接口
interface UsePromptBasicInfoDialogReturn {
  // 状态
  editInfoDialogOpen: boolean
  createCopyDialogOpen: boolean
  copyPromptData: CopyPromptData | null

  // 设置函数
  setEditInfoDialogOpen: (open: boolean) => void
  setCreateCopyDialogOpen: (open: boolean) => void
  setCopyPromptData: (data: CopyPromptData | null) => void

  // 操作函数
  handleOpenEditInfoDialog: () => Promise<void>
  handleSaveBasicInfo: (basicInfo: BasicInfo) => Promise<void>
  handleCreateCopy: () => Promise<void>
  handleConfirmCreateCopy: (basicInfo: BasicInfo) => Promise<void>
}

export const usePromptBasicInfoDialog = ({
  id,
  isNew,
  workspaceId,
  userId,
  prompt,
  setPrompt,
  setLoading,
  setHasUnsavedChanges,
  selectedVersion,
  getDisplayVersions,
  showSnackbar,
  setSnackbar,
}: UsePromptBasicInfoDialogProps): UsePromptBasicInfoDialogReturn => {
  const { t } = useTranslation()

  // 状态管理
  const [editInfoDialogOpen, setEditInfoDialogOpen] = useState(false)
  const [createCopyDialogOpen, setCreateCopyDialogOpen] = useState(false)
  const [copyPromptData, setCopyPromptData] = useState<CopyPromptData | null>(null)

  // 打开编辑基本信息对话框
  const handleOpenEditInfoDialog = useCallback(async () => {
    console.log('handleOpenEditInfoDialog 被调用，参数：', { id, isNew })

    if (!id || isNew) {
      console.log('直接打开对话框，原因：', {
        noId: !id,
        isNew,
        idValue: id,
      })
      setEditInfoDialogOpen(true)
      return
    }

    try {
      setLoading(true)
      console.log('开始调用 API 获取提示词详情，ID:', id)

      // 调用API获取提示词详情
      const response = await PromptService.getPromptDetail(id, {
        withCommit: true,
        withDraft: true,
        withDefaultConfig: true,
        workspaceId: workspaceId,
      })

      console.log('API 响应:', response)

      if (response.code === 0 && response.prompt && response.prompt.length > 0) {
        const promptDetail = response.prompt[0]
        const promptBasic = promptDetail.prompt_basic

        // 更新prompt状态，显示从API获取的最新数据
        setPrompt(prev => ({
          ...prev,
          key: promptDetail.prompt_key,
          name: promptBasic.display_name,
          description: promptBasic.description,
        }))

        console.log('获取到的提示词详情:', {
          prompt_key: promptDetail.prompt_key,
          display_name: promptBasic.display_name,
          description: promptBasic.description,
        })

        setEditInfoDialogOpen(true)
      } else {
        setSnackbar({
          open: true,
          message: response.msg || t('components.prompts.promptEditPage.getPromptDetailFailedFallback'),
          severity: 'error',
        })
      }
    } catch (error) {
      console.error('获取提示词详情失败:', error)
      setSnackbar({
        open: true,
        message: t('components.prompts.promptEditPage.getPromptDetailFailed'),
        severity: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [id, isNew, workspaceId, setPrompt, setLoading, setSnackbar, t])

  // 保存提示词基本信息
  const handleSaveBasicInfo = useCallback(
    async (basicInfo: BasicInfo) => {
      try {
        setLoading(true)

        // 调用API保存基本信息（需要携带 workspaceId）
        const response = await PromptService.editPromptBasicInfo(id!, workspaceId || '', {
          prompt_name: basicInfo.name,
          prompt_description: basicInfo.description,
        })

        if (response.code === 0) {
          // 更新本地状态
          setPrompt(prev => ({
            ...prev,
            name: basicInfo.name,
            description: basicInfo.description,
            tags: basicInfo.tags,
            isPublic: basicInfo.isPublic,
          }))

          showSnackbar(t('components.prompts.promptEditPage.saveBasicInfoSuccess'), 'success')
          setEditInfoDialogOpen(false)
          setHasUnsavedChanges(false)
        } else {
          setSnackbar({
            open: true,
            message: response.msg || t('components.prompts.promptEditPage.saveFailedFallback'),
            severity: 'error',
          })
        }
      } catch (error) {
        console.error('保存提示词基本信息失败:', error)
        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.saveFailed'),
          severity: 'error',
        })
      } finally {
        setLoading(false)
      }
    },
    [id, setPrompt, setLoading, setEditInfoDialogOpen, setHasUnsavedChanges, showSnackbar, setSnackbar, t],
  )

  // 处理创建副本
  const handleCreateCopy = useCallback(async () => {
    if (!selectedVersion) return

    if (!getDisplayVersions) {
      console.error('getDisplayVersions function is not provided')
      setSnackbar({
        open: true,
        message: t('components.prompts.promptEditPage.getDisplayVersionsNotProvided'),
        severity: 'error',
      })
      return
    }

    const displayVersions = getDisplayVersions()
    const selectedVersionData = displayVersions.find(v => v.id === selectedVersion)
    if (!selectedVersionData) return

    // 如果没有prompt ID，无法调用API
    if (!id || isNew) {
      console.log(t('components.prompts.promptEditPage.promptNotSavedCannotCopy'))
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.cannotCreateCopyNotSaved'), severity: 'error' })
      return
    }

    // 准备副本的默认数据
    const defaultCopyData: CopyPromptData = {
      key: `${prompt.key}_copy`,
      name: `${prompt.name}_copy`,
      description: prompt.description,
      tags: [...prompt.tags],
      isPublic: prompt.isPublic,
      version: selectedVersionData.version,
    }

    setCopyPromptData(defaultCopyData)
    setCreateCopyDialogOpen(true)
  }, [selectedVersion, getDisplayVersions, id, isNew, prompt, t, setSnackbar])

  // 处理创建副本确认
  const handleConfirmCreateCopy = useCallback(
    async (basicInfo: BasicInfo) => {
      if (!copyPromptData || !id) return

      try {
        console.log('开始克隆提示词:', { promptId: id, version: copyPromptData.version, basicInfo })

        const cloneRequest = {
          user_id: userId || '',
          workspace_id: workspaceId || '',
          commit_version: copyPromptData.version,
          cloned_prompt_name: basicInfo.name,
          cloned_prompt_key: basicInfo.key,
          cloned_prompt_description: basicInfo.description,
        }

        const response = await PromptService.clonePrompt(id, cloneRequest)

        if (response.code === 0) {
          setCreateCopyDialogOpen(false)
          setCopyPromptData(null)
          setSnackbar({
            open: true,
            message: t('components.prompts.promptEditPage.clonePromptSuccessWithVersion', { version: copyPromptData.version }),
            severity: 'success',
          })

          // 跳转到新的提示词编辑页面
          setTimeout(() => {
            // 使用 window.location.href 强制刷新页面，避免保留旧页面的状态
            window.location.href = `/dashboard/prompts/${response.cloned_prompt_id}`
          }, 1000)
        } else {
          const errorMessage = response.msg || t('components.prompts.promptEditPage.createCopyFailed')
          setSnackbar({
            open: true,
            message: errorMessage,
            severity: 'error',
          })
        }
      } catch (error: any) {
        console.error('克隆提示词失败:', error)

        // 处理 API 错误，显示具体的错误信息
        if (error instanceof ApiError) {
          const errorMsg = error.response?.msg || error.response?.message || error.message || t('components.prompts.promptEditPage.createCopyFailed')
          showSnackbar(errorMsg, 'error')
        } else if (error instanceof Error) {
          showSnackbar(error.message || t('components.prompts.promptEditPage.createCopyFailed'), 'error')
        } else {
          showSnackbar(t('components.prompts.promptEditPage.createCopyFailed'), 'error')
        }
      }
    },
    [copyPromptData, id, userId, workspaceId, t, showSnackbar],
  )

  return {
    // 状态
    editInfoDialogOpen,
    createCopyDialogOpen,
    copyPromptData,

    // 设置函数
    setEditInfoDialogOpen,
    setCreateCopyDialogOpen,
    setCopyPromptData,

    // 操作函数
    handleOpenEditInfoDialog,
    handleSaveBasicInfo,
    handleCreateCopy,
    handleConfirmCreateCopy,
  }
}
