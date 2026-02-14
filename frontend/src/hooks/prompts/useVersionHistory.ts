import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { PromptService } from '@test-agentstudio/api-client'
import { useUnifiedSnackbar } from '@/Common/UnifiedSnackbar'
import { formatDraftDateTime } from '@/utils/prompts/utils'
import type { PromptParameter, PromptMessage, Model, ModelConfig, ChatMessage } from '@/types/promptType'

// 版本历史相关的类型定义
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

interface LoadVersionResult {
  success: boolean
  message: string
}

// Hook 参数接口
interface UseVersionHistoryProps {
  id?: string
  isNew?: boolean
  workspaceId?: string
  userId?: string
  // 外部状态
  isDraftEdited: boolean
  draftSavedTime: Date | null
  selectedVersion: string | null
  availableModels: Model[]
  selectedModel: Model | null
  // 外部状态设置函数
  setSelectedVersion: (version: string | null) => void
  setPromptMessages: (messages: PromptMessage[] | ((prev: PromptMessage[]) => PromptMessage[])) => void
  setPrompt: (prompt: any | ((prev: any) => any)) => void
  setHasUnsavedChanges: (hasChanges: boolean) => void
  setMessageInputValues: (values: { [key: string]: string }) => void
  setParameters: (params: PromptParameter[] | ((prev: PromptParameter[]) => PromptParameter[])) => void
  setTools: (tools: any[] | ((prev: any[]) => any[])) => void
  setToolsEnabled: (enabled: boolean) => void
  setSelectedModel: (model: Model | null) => void
  setModelConfig: (config: ModelConfig | ((prev: ModelConfig) => ModelConfig)) => void
  setIsLoadingFromAPI: (loading: boolean) => void
  setTemplateEngine: (engine: 'normal' | 'jinja2') => void
  setChatMessages: (messages: ChatMessage[]) => void
  setCompletedMessages: (messages: Set<number>) => void
  setLastSavedTime: (time: Date) => void
  setIsDraftEdited: (edited: boolean) => void
  // 外部函数
  loadPromptDetailToPage: (promptDetailData: any, isNewPromptScenario?: boolean) => Promise<void>
  loadDebugContext?: () => Promise<void>
}

// Hook 返回值接口
interface UseVersionHistoryReturn {
  // 状态
  versionHistoryOpen: boolean
  setVersionHistoryOpen: React.Dispatch<React.SetStateAction<boolean>>
  versionListLoading: boolean
  setApiVersionList: React.Dispatch<React.SetStateAction<any[]>>
  revertConfirmOpen: boolean
  setRevertConfirmOpen: (open: boolean) => void
  // 操作函数
  handleOpenVersionHistory: () => Promise<void>
  getDisplayVersions: () => VersionData[]
  handleSelectVersion: (versionId: string) => Promise<void>
  loadVersionDataToEditor: (version: string, source?: string) => Promise<LoadVersionResult>
  handleRollbackToVersion: () => void
  handleConfirmRevert: () => Promise<void>
}

export const useVersionHistory = ({
  id,
  isNew,
  workspaceId,
  userId,
  isDraftEdited,
  draftSavedTime,
  selectedVersion,
  availableModels,
  selectedModel,
  setSelectedVersion,
  setPromptMessages,
  setPrompt,
  setHasUnsavedChanges,
  setMessageInputValues,
  setParameters,
  setTools,
  setToolsEnabled,
  setSelectedModel,
  setModelConfig,
  setIsLoadingFromAPI,
  setTemplateEngine,
  setChatMessages,
  setCompletedMessages,
  setLastSavedTime,
  setIsDraftEdited,
  loadPromptDetailToPage,
  loadDebugContext,
}: UseVersionHistoryProps): UseVersionHistoryReturn => {
  const { t } = useTranslation()
  const { setSnackbar } = useUnifiedSnackbar()

  // 版本历史面板状态
  const [versionHistoryOpen, setVersionHistoryOpen] = useState(false)
  const [versionListLoading, setVersionListLoading] = useState(false)
  const [apiVersionList, setApiVersionList] = useState<any[]>([])

  // 还原确认对话框状态
  const [revertConfirmOpen, setRevertConfirmOpen] = useState(false)

  // 打开/关闭版本历史面板
  const handleOpenVersionHistory = useCallback(async () => {
    // 切换版本历史面板的开关状态
    const newVersionHistoryOpen = !versionHistoryOpen
    setVersionHistoryOpen(newVersionHistoryOpen)

    // 如果是关闭面板，清除选中的版本
    if (!newVersionHistoryOpen) {
      setSelectedVersion(null)
      return
    }

    // 如果是打开面板，重置选中的版本并加载数据
    setSelectedVersion(null)

    // 如果提示词尚未保存，不调用API
    if (!id || isNew) {
      console.log('提示词尚未保存，使用本地版本数据')
      return
    }

    // 调用API获取版本列表
    setVersionListLoading(true)
    try {
      const response = await PromptService.getVersionList(id, workspaceId!, { page_size: 20 })

      if (response.code === 0) {
        // 成功获取版本列表
        setApiVersionList(response.prompt_commit_infos)
        console.log('✅ [VERSION-LIST] 版本列表获取成功:', response.prompt_commit_infos)
        console.log(
          '🔍 [VERSION-LIST] 第一个版本的提交人信息:',
          response.prompt_commit_infos[0]
            ? {
                version: response.prompt_commit_infos[0].version,
                committed_by: response.prompt_commit_infos[0].committed_by,
                committed_by_name: response.prompt_commit_infos[0].committed_by_name,
              }
            : '无版本数据',
        )
      } else {
        // API返回错误
        const errorMessage = response.msg || '获取版本列表失败'
        setSnackbar({ open: true, message: errorMessage, severity: 'error' })
        console.error('获取版本列表失败:', response)
      }
    } catch (error) {
      console.error('获取版本列表API调用失败:', error)
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.getVersionListFailed'), severity: 'error' })
    } finally {
      setVersionListLoading(false)
    }
  }, [versionHistoryOpen, id, isNew, setSelectedVersion, setSnackbar, t])

  // 获取显示用的版本列表（根据is_draft_edited决定是否包含当前草稿）
  const getDisplayVersions = useCallback((): VersionData[] => {
    const versions: VersionData[] = []

    // 只有当有未提交的草稿时，才添加当前草稿到列表顶部
    if (isDraftEdited) {
      versions.push({
        id: 'current-draft',
        version: t('components.prompts.versionHistory.currentDraft'),
        content: '',
        parameters: [],
        modelConfig: {
          model: '',
          temperature: 0.7,
          maxTokens: 1000,
          topP: 1.0,
          frequencyPenalty: 0.0,
          presencePenalty: 0.0,
          stopSequences: [],
        },
        createdAt: draftSavedTime ? draftSavedTime.toISOString() : new Date().toISOString(),
        isActive: false,
        isDraft: true,
        description: draftSavedTime
          ? t('components.prompts.versionHistory.draftSavedAt', { time: formatDraftDateTime(draftSavedTime) })
          : t('components.prompts.versionHistory.currentDraft'),
        author: t('components.prompts.versionHistory.currentUser'),
        baseVersion: '',
        associations: {
          relationObjs: [],
        },
        performance: {
          usage: 0,
          rating: 0,
          successRate: 0,
        },
      })
    }

    // 添加API版本数据
    apiVersionList.forEach((apiVersion, index) => {
      const authorName = apiVersion.committed_by_name || apiVersion.committed_by

      versions.push({
        id: `api-${apiVersion.version}`,
        version: apiVersion.version,
        content: '', // API数据中没有content，使用空字符串
        parameters: [], // API数据中没有parameters，使用空数组
        modelConfig: {
          model: 'gpt-4',
          temperature: 0.7,
          maxTokens: 1000,
          topP: 1.0,
          frequencyPenalty: 0.0,
          presencePenalty: 0.0,
          stopSequences: [],
        },
        createdAt:
          typeof apiVersion.committed_at === 'number' && apiVersion.committed_at < 10000000000
            ? new Date(apiVersion.committed_at * 1000).toISOString()
            : new Date(apiVersion.committed_at).toISOString(), // 智能处理时间戳格式
        isActive: index === 0, // 假设第一个版本是当前活跃版本
        isDraft: false,
        description: apiVersion.description,
        author: authorName,
        baseVersion: apiVersion.base_version,
        associations: {
          relationObjs: apiVersion.relation_obj || [],
        },
        performance: {
          usage: 0,
          rating: 0,
          successRate: 0,
        },
      })
    })

    // 按照提交时间从最近到最远排序
    // 草稿如果存在，始终显示在最顶部，其他版本按时间排序
    const sortedVersions = versions.sort((a, b) => {
      // 草稿始终在最前面
      if (a.isDraft) return -1
      if (b.isDraft) return 1

      // 其他版本按创建时间降序排序（最新的在前）
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    })

    return sortedVersions
  }, [isDraftEdited, draftSavedTime, apiVersionList, t])

  // 根据版本号加载版本数据到编辑区域的统一函数
  const loadVersionDataToEditor = useCallback(
    async (version: string, source = 'manual'): Promise<LoadVersionResult> => {
      console.log(`🔄 [LOAD-VERSION-DATA] 开始加载版本 ${version} 数据，来源: ${source}`)

      try {
        // 直接调用API获取指定版本的详情
        const versionResponse = await PromptService.getPromptDetail(id!, {
          withCommit: true,
          commitVersion: version,
          withDraft: false,
          withDefaultConfig: false,
          workspaceId: workspaceId,
        })

        if (versionResponse.code === 0) {
          const promptDetail = versionResponse.prompt && versionResponse.prompt.length > 0 ? versionResponse.prompt[0] : null
          const commitData = promptDetail?.prompt_commit?.detail

          if (commitData) {
            console.log('✅ [LOAD-VERSION-DATA] 成功获取版本详情，开始填充数据')

            // 临时设置加载标志，防止自动变量检测干扰和自动保存
            setIsLoadingFromAPI(true)

            // 使用 loadPromptDetailToPage 填充数据到页面
            await loadPromptDetailToPage(commitData, false)
            console.log('✅ [LOAD-VERSION-DATA] 使用 loadPromptDetailToPage 填充数据完成')

            // 同步到prompt.content（不触发自动保存，因为isLoadingFromAPI已设置）
            if (commitData.prompt_template?.messages) {
              const messages = commitData.prompt_template.messages
              const combinedContent = messages.map((m: any) => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n')
              // 直接更新prompt状态，不通过handlePromptChange避免触发自动保存
              setPrompt((prev: any) => ({ ...prev, content: combinedContent }))
              setHasUnsavedChanges(true)
              console.log('✅ [LOAD-VERSION-DATA] 同步到prompt.content（跳过自动保存）')
            }

            // 设置选中版本
            setSelectedVersion(`api-${version}`)

            // 标记为有未保存的更改
            setHasUnsavedChanges(true)

            // 延迟重置加载标志，确保状态更新完成
            setTimeout(() => {
              setIsLoadingFromAPI(false)
              console.log('✅ [LOAD-VERSION-DATA] 版本数据加载完成，重置加载标志')
            }, 500)

            console.log('🎉 [LOAD-VERSION-DATA] 版本加载完成，版本:', version)
            return { success: true, message: t('components.prompts.promptEditPage.loadVersionSuccessWithVersion', { version }) }
          } else {
            console.error('❌ [LOAD-VERSION-DATA] 版本数据不存在')
            return { success: false, message: t('components.prompts.promptEditPage.versionDataNotFound') }
          }
        } else {
          console.error('❌ [LOAD-VERSION-DATA] 获取版本详情失败:', versionResponse.msg)
          return { success: false, message: versionResponse.msg || t('components.prompts.promptEditPage.getVersionDetailFailed') }
        }
      } catch (error) {
        console.error('❌ [LOAD-VERSION-DATA] 版本加载异常:', error)
        return { success: false, message: t('components.prompts.promptEditPage.versionLoadFailedRetry') }
      }
    },
    [
      id,
      workspaceId,
      availableModels,
      selectedModel,
      setTemplateEngine,
      setPromptMessages,
      setIsLoadingFromAPI,
      setPrompt,
      setHasUnsavedChanges,
      setMessageInputValues,
      setParameters,
      setTools,
      setToolsEnabled,
      setSelectedModel,
      setModelConfig,
      setSelectedVersion,
      t,
    ],
  )

  // 处理版本选择
  const handleSelectVersion = useCallback(
    async (versionId: string) => {
      setSelectedVersion(versionId)

      // 获取选中的版本数据
      const displayVersions = getDisplayVersions()
      const selectedVersionData = displayVersions.find(v => v.id === versionId)
      if (!selectedVersionData) return

      // 如果没有prompt ID，无法调用API
      if (!id || isNew) {
        console.log('提示词尚未保存，无法获取版本详情')
        return
      }

      try {
        // 如果选中的是当前草稿
        if (versionId === 'current-draft') {
          console.log('加载当前草稿')
          const response = await PromptService.getPromptDetail(id!, {
            withCommit: true,
            commitVersion: '', // 空字符串表示不获取特定commit版本
            withDraft: true,
            withDefaultConfig: true,
            workspaceId: workspaceId,
          })

          if (response.code === 0 && response.prompt?.[0]?.prompt_draft) {
            const draftData = response.prompt[0].prompt_draft.detail

            // 设置加载标志，防止自动保存
            setIsLoadingFromAPI(true)

            // 使用 prompt_draft 数据填充编辑器
            await loadPromptDetailToPage(draftData)

            // 延迟重置加载标志，确保状态更新完成
            setTimeout(() => {
              setIsLoadingFromAPI(false)
              console.log('✅ [SELECT-VERSION] 草稿数据加载完成，重置加载标志')
            }, 500)

            // 加载调试上下文数据（使用统一的 loadDebugContext 函数）
            if (loadDebugContext) {
              await loadDebugContext()
            }

            setSnackbar({
              open: true,
              message: t('components.prompts.promptEditPage.loadDraftSuccess'),
              severity: 'success',
            })
          } else {
            setSnackbar({ open: true, message: t('components.prompts.promptEditPage.getDraftFailed'), severity: 'error' })
          }
          return
        }

        // 使用统一的版本加载函数
        console.log('使用统一函数加载版本:', selectedVersionData.version)
        // loadVersionDataToEditor 内部已经设置了 isLoadingFromAPI 标志，这里不需要重复设置
        const result = await loadVersionDataToEditor(selectedVersionData.version, 'handleSelectVersion')

        if (!result.success) {
          setSnackbar({
            open: true,
            message: result.message,
            severity: 'error',
          })
          return
        }

        // 加载调试上下文数据（使用统一的 loadDebugContext 函数）
        if (loadDebugContext) {
          await loadDebugContext()
        }

        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.addResultMessageToEditor', { message: result.message }),
          severity: 'success',
        })
      } catch (error) {
        console.error('获取版本详情失败:', error)
        setSnackbar({
          open: true,
          message: t('components.prompts.promptEditPage.getVersionDetailFailed'),
          severity: 'error',
        })
      }
    },
    [
      id,
      isNew,
      workspaceId,
      userId,
      getDisplayVersions,
      setSelectedVersion,
      setIsLoadingFromAPI,
      loadPromptDetailToPage,
      setChatMessages,
      setCompletedMessages,
      setParameters,
      setTools,
      loadVersionDataToEditor,
      setSnackbar,
      t,
    ],
  )

  // 处理还原版本按钮点击
  const handleRollbackToVersion = useCallback(() => {
    if (!selectedVersion) return

    const displayVersions = getDisplayVersions()
    const selectedVersionData = displayVersions.find(v => v.id === selectedVersion)
    if (!selectedVersionData) return

    if (!id || isNew) {
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.cannotRevertNotSaved'), severity: 'error' })
      return
    }

    // 显示确认弹窗
    setRevertConfirmOpen(true)
  }, [selectedVersion, getDisplayVersions, id, isNew, setSnackbar, t])

  // 确认还原版本
  const handleConfirmRevert = useCallback(async () => {
    if (!selectedVersion) return

    const displayVersions = getDisplayVersions()
    const selectedVersionData = displayVersions.find(v => v.id === selectedVersion)
    if (!selectedVersionData) return

    try {
      setRevertConfirmOpen(false)

      // 调用从版本中恢复API
      const response = await PromptService.revertToVersion(id!, workspaceId!, {
        commit_version_reverting_from: selectedVersionData.version,
      })

      if (response.code === 0) {
        // API调用成功，重新获取prompt详情以获取最新的draft数据
        const promptDetailResponse = await PromptService.getPromptDetail(id!, {
          withDraft: true,
          withDefaultConfig: true,
          withCommit: false,
          workspaceId: workspaceId,
        })

        if (promptDetailResponse.code === 0 && promptDetailResponse.prompt?.[0]?.prompt_draft) {
          const draftData = promptDetailResponse.prompt[0].prompt_draft.detail

          // 设置加载标志，防止自动保存
          setIsLoadingFromAPI(true)

          // 使用通用函数加载 prompt_draft 数据到编辑器
          await loadPromptDetailToPage(draftData)

          // 加载调试上下文（如果提供了该函数）
          if (loadDebugContext) {
            try {
              console.log('🔍 [REVERT-VERSION] 开始加载调试上下文')
              await loadDebugContext()
              console.log('✅ [REVERT-VERSION] 调试上下文加载完成')
            } catch (error) {
              console.error('❌ [REVERT-VERSION] 加载调试上下文失败:', error)
              // 调试上下文加载失败不影响主流程，只记录错误
            }
          }

          // 延迟重置加载标志，确保状态更新完成
          setTimeout(() => {
            setIsLoadingFromAPI(false)
            console.log('✅ [REVERT-VERSION] 还原版本数据加载完成，重置加载标志')
          }, 500)

          setLastSavedTime(new Date())
          setHasUnsavedChanges(false)
          setIsDraftEdited(true) // 还原版本后标记为有未提交的更改
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.revertSuccess'), severity: 'success' })
        } else {
          setSnackbar({ open: true, message: t('components.prompts.promptEditPage.getRevertedDataFailed'), severity: 'error' })
        }
      } else {
        // API调用失败
        const errorMessage = response.msg || t('components.prompts.promptEditPage.revertFailed')
        setSnackbar({ open: true, message: errorMessage, severity: 'error' })
      }
    } catch (error) {
      console.error(t('components.prompts.promptEditPage.revertFailed'), error)
      setSnackbar({ open: true, message: t('components.prompts.promptEditPage.revertFailed'), severity: 'error' })
    }
  }, [
    selectedVersion,
    getDisplayVersions,
    id,
    userId,
    workspaceId,
    setIsLoadingFromAPI,
    loadPromptDetailToPage,
    loadDebugContext,
    setLastSavedTime,
    setHasUnsavedChanges,
    setIsDraftEdited,
    setSnackbar,
    t,
  ])

  return {
    // 状态
    versionHistoryOpen,
    setVersionHistoryOpen,
    versionListLoading,
    setApiVersionList,
    revertConfirmOpen,
    setRevertConfirmOpen,
    // 操作函数
    handleOpenVersionHistory,
    getDisplayVersions,
    handleSelectVersion,
    loadVersionDataToEditor,
    handleRollbackToVersion,
    handleConfirmRevert,
  }
}
