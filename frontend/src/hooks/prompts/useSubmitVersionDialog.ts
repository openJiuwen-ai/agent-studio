import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { PromptService, ApiError } from '@test-agentstudio/api-client'
import { ENV_CONFIG } from '@/config/environment'
import { validateVersionNumber } from '@/utils/prompts/utils'

interface UseSubmitVersionDialogProps {
  id?: string
  workspaceId?: string
  userId?: string
  isNew?: boolean
  // 外部状态和函数
  prompt: any
  parameters: any[]
  modelConfig: any
  versionDescription: string
  setVersionDescription: (desc: string) => void
  setVersionNumberInitialized: (initialized: boolean) => void
  setLastSavedTime: (time: Date) => void
  setHasUnsavedChanges: (hasChanges: boolean) => void
  setDraftSavedTime: (time: Date | null) => void
  setIsDraftEdited: (edited: boolean) => void
  setVersionHistoryOpen: (open: boolean) => void
  setLatestVersion: (version: string) => void
  setIsLoadingFromAPI: (loading: boolean) => void
  loadPromptDetailToPage: (promptDetailData: any, isNewPromptScenario?: boolean) => Promise<void>
  loadDebugContext?: () => Promise<void> // 加载调试上下文的函数（可选）
  // Snackbar 函数
  showSnackbar: (message: string, severity?: 'success' | 'error' | 'warning' | 'info', duration?: number) => void
  setSnackbar: (snackbar: { open: boolean; message: string; severity: 'success' | 'error' | 'warning' | 'info' }) => void
}

interface UseSubmitVersionDialogReturn {
  // 状态
  submitVersionDialogOpen: boolean
  submitVersionStep: number
  promptCommitData: any
  promptDraftData: any
  versionNumber: string
  versionNumberError: string

  // 设置函数
  setPromptCommitData: (data: any) => void
  setPromptDraftData: (data: any) => void
  setVersionNumber: (version: string) => void
  setVersionNumberError: (error: string) => void

  // 操作函数
  handleSubmitVersion: () => Promise<void>
  handleCloseSubmitVersionDialog: () => void
  handleNextStep: () => void
  handlePrevStep: () => void
  handleConfirmSubmitVersion: () => Promise<void>
}

export const useSubmitVersionDialog = ({
  id,
  workspaceId,
  userId,
  isNew,
  prompt,
  parameters,
  modelConfig,
  versionDescription,
  setVersionDescription,
  setVersionNumberInitialized,
  setLastSavedTime,
  setHasUnsavedChanges,
  setDraftSavedTime,
  setIsDraftEdited,
  setVersionHistoryOpen,
  setLatestVersion,
  setIsLoadingFromAPI,
  loadPromptDetailToPage,
  loadDebugContext,
  showSnackbar,
  setSnackbar,
}: UseSubmitVersionDialogProps): UseSubmitVersionDialogReturn => {
  const { t } = useTranslation()
  // 状态管理
  const [submitVersionDialogOpen, setSubmitVersionDialogOpen] = useState(false)
  const [submitVersionStep, setSubmitVersionStep] = useState(0)
  const [promptCommitData, setPromptCommitData] = useState<any>(null)
  const [promptDraftData, setPromptDraftData] = useState<any>(null)
  const [versionNumber, setVersionNumber] = useState('')
  const [versionNumberError, setVersionNumberError] = useState('')

  // 处理提交版本
  const handleSubmitVersion = useCallback(async () => {
    try {
      console.log('点击提交新版本，开始获取prompt详情')

      // 调用获取prompt详情API
      const detailResponse = await PromptService.getPromptDetail(id!, {
        withCommit: true,
        commitVersion: '', // 空字符串表示获取最新commit版本
        withDraft: true,
        withDefaultConfig: true,
        workspaceId: workspaceId,
      })

      if (detailResponse.code === 0 && detailResponse.prompt?.[0]) {
        const promptDetail = detailResponse.prompt[0]
        console.log('获取prompt详情成功:', promptDetail)

        // 更新prompt_commit和prompt_draft数据用于版本比较
        if (promptDetail.prompt_commit) {
          setPromptCommitData(promptDetail.prompt_commit.detail)
          console.log('设置prompt_commit数据:', promptDetail.prompt_commit.detail)
        }

        if (promptDetail.prompt_draft) {
          setPromptDraftData(promptDetail.prompt_draft.detail)
          console.log('设置prompt_draft数据:', promptDetail.prompt_draft.detail)
        }

        // 打开版本提交对话框
        setSubmitVersionDialogOpen(true)
        // 如果有prompt_commit数据，显示版本差异比较；否则直接跳到确认版本信息步骤
        const initialStep = promptDetail.prompt_commit ? 0 : 1
        setSubmitVersionStep(initialStep)
        console.log('提交版本对话框打开，初始步骤:', initialStep, 'prompt_commit数据:', promptDetail.prompt_commit ? '存在' : '不存在')

        // 重置版本号为基于最新版本的自动生成值
        const latestVersion = promptDetail.prompt_basic?.latest_version

        if (latestVersion) {
          // 解析版本号，最后一位加1
          const versionMatch = latestVersion.match(/^v?(\d+)\.(\d+)\.(\d+)$/)
          if (versionMatch) {
            const [, major, minor, patch] = versionMatch
            const newPatch = parseInt(patch) + 1
            const newVersionNumber = `${major}.${minor}.${newPatch}`
            setVersionNumber(newVersionNumber)
            setVersionNumberError(validateVersionNumber(newVersionNumber))
            console.log('基于API返回的最新版本生成新版本号:', latestVersion, '->', newVersionNumber)
          } else {
            const newVersionNumber = ENV_CONFIG.DEFAULT_PROMPT_VERSION
            setVersionNumber(newVersionNumber)
            setVersionNumberError(validateVersionNumber(newVersionNumber))
            console.log('最新版本格式无法解析，使用默认版本号:', newVersionNumber)
          }
        } else {
          const newVersionNumber = ENV_CONFIG.DEFAULT_PROMPT_VERSION
          setVersionNumber(newVersionNumber)
          setVersionNumberError(validateVersionNumber(newVersionNumber))
          console.log('未找到最新版本信息，使用默认版本号:', newVersionNumber)
        }
      } else {
        console.error('获取prompt详情失败:', detailResponse.msg)
        setSnackbar({
          open: true,
          message: detailResponse.msg || t('hooks.prompts.useSubmitVersionDialog.getPromptDetailFailed'),
          severity: 'error',
        })
      }
    } catch (error) {
      console.error('获取prompt详情API调用失败:', error)
      setSnackbar({
        open: true,
        message: t('hooks.prompts.useSubmitVersionDialog.getPromptDetailFailed'),
        severity: 'error',
      })
    }
  }, [id, workspaceId, t, setSnackbar])

  // 关闭提交版本对话框
  const handleCloseSubmitVersionDialog = useCallback(() => {
    setSubmitVersionDialogOpen(false)
    setSubmitVersionStep(0)
  }, [])

  // 重置版本对话框状态（用于提交成功后）
  const resetVersionDialogState = useCallback(() => {
    setSubmitVersionDialogOpen(false)
    setSubmitVersionStep(0)
    setVersionNumber('') // 清空版本号，为下次提交准备
  }, [])

  // 下一步
  const handleNextStep = useCallback(() => {
    // 如果有prompt_commit数据，从步骤0到步骤1；否则不应该调用这个函数
    setSubmitVersionStep(1)
  }, [])

  // 上一步
  const handlePrevStep = useCallback(() => {
    // 如果有prompt_commit数据，从步骤1回到步骤0；否则不应该调用这个函数
    setSubmitVersionStep(0)
  }, [])

  // 确认提交版本
  const handleConfirmSubmitVersion = useCallback(async () => {
    if (!id || isNew) {
      showSnackbar(t('hooks.prompts.useSubmitVersionDialog.cannotSubmitPromptNotSaved'), 'error')
      return
    }

    if (!versionNumber.trim()) {
      showSnackbar(t('hooks.prompts.useSubmitVersionDialog.versionNumberRequired'), 'error')
      return
    }

    try {
      // 调用提交版本API
      const response = await PromptService.commitVersion(id!, workspaceId!, {
        commit_version: versionNumber.replace('v', ''), // Remove 'v' prefix if present
        commit_description: versionDescription,
      })

      if (response.code === 0) {
        // 提交成功
        resetVersionDialogState() // 重置版本对话框状态
        setVersionDescription('') // 清空版本描述
        setVersionNumberInitialized(false) // 重置初始化标志
        setLastSavedTime(new Date())
        setHasUnsavedChanges(false) // 重置未保存状态，这样会显示"已提交"状态
        setDraftSavedTime(null) // 清除草稿保存时间，因为已经提交了新版本
        setIsDraftEdited(false) // 提交后草稿状态变为未编辑
        setVersionHistoryOpen(false) // 关闭版本历史页签
        showSnackbar(t('hooks.prompts.useSubmitVersionDialog.submitSuccess'), 'success')

        // 提交成功后，重新获取prompt详情并用prompt_draft部分填充页面
        try {
          console.log('提交成功后重新加载prompt详情')
          const detailResponse = await PromptService.getPromptDetail(id!, {
            withCommit: true,
            commitVersion: '', // 空字符串表示不获取特定commit版本
            withDraft: true,
            withDefaultConfig: true,
            workspaceId: workspaceId,
          })

          if (detailResponse.code === 0 && detailResponse.prompt?.[0]) {
            const promptDetail = detailResponse.prompt[0]

            // 更新最新版本号
            if (promptDetail.prompt_basic?.latest_version) {
              setLatestVersion(promptDetail.prompt_basic.latest_version)
              console.log('提交后更新最新版本号:', promptDetail.prompt_basic.latest_version)
            }

            // 如果有draft数据，重新填充页面
            if (promptDetail.prompt_draft) {
              const draftData = promptDetail.prompt_draft.detail
              console.log('使用prompt_draft数据重新填充页面:', draftData)

              // 检查新的草稿编辑状态
              const newIsDraftEdited = promptDetail.prompt_draft.draft_info?.is_draft_edited || false
              setIsDraftEdited(newIsDraftEdited)
              console.log('提交后更新草稿编辑状态:', newIsDraftEdited)

              // 设置加载标志，防止自动保存
              setIsLoadingFromAPI(true)

              // 使用相同的函数填充编辑器数据
              await loadPromptDetailToPage(draftData)

              // 延迟重置加载标志，确保状态更新完成
              setTimeout(async () => {
                setIsLoadingFromAPI(false)
                console.log('✅ [SUBMIT-VERSION] 提交后页面数据重新填充完成，重置加载标志')

                // 提交成功后，加载调试上下文
                if (loadDebugContext) {
                  try {
                    console.log('🔍 [SUBMIT-VERSION] 提交成功后开始加载调试上下文')
                    await loadDebugContext()
                    console.log('✅ [SUBMIT-VERSION] 提交成功后调试上下文加载完成')
                  } catch (error) {
                    console.error('❌ [SUBMIT-VERSION] 提交成功后加载调试上下文失败:', error)
                    showSnackbar(t('hooks.prompts.useSubmitVersionDialog.loadDebugContextFailed'), 'error')
                  }
                } else {
                  console.warn('⚠️ [SUBMIT-VERSION] loadDebugContext 函数未提供，跳过调试上下文加载')
                }
              }, 500)
            }
          } else {
            console.log('提交后获取prompt详情数据失败:', detailResponse.msg)
            showSnackbar(detailResponse.msg || t('hooks.prompts.useSubmitVersionDialog.reloadAfterSubmitFailed'), 'error')
          }
        } catch (error) {
          console.error('提交后重新加载数据失败:', error)
          showSnackbar(t('hooks.prompts.useSubmitVersionDialog.reloadAfterSubmitFailed'), 'error')
        }
      } else {
        // 提交失败（这个分支实际上不会被执行，因为API service会抛出异常）
        const errorMessage = response.msg && response.msg.trim() ? response.msg : t('hooks.prompts.useSubmitVersionDialog.submitNewVersionFailed')
        showSnackbar(errorMessage, 'error')
      }
    } catch (error) {
      console.error('提交版本失败:', error)

      // 检查是否是ApiError，如果是则显示具体的错误信息
      if (error instanceof ApiError) {
        console.log('ApiError详细信息:', {
          message: error.message,
          code: error.code,
          response: error.response,
        })

        // 显示API返回的具体错误信息，优先使用 response.msg
        const errorMessage = error.response?.msg || error.response?.message || error.message || t('hooks.prompts.useSubmitVersionDialog.submitNewVersionFailed')
        showSnackbar(errorMessage, 'error')
      } else if (error instanceof Error) {
        // 其他类型的错误（网络错误等）
        showSnackbar(error.message || t('hooks.prompts.useSubmitVersionDialog.submitNewVersionFailed'), 'error')
      } else {
        // 未知错误类型
        showSnackbar(t('hooks.prompts.useSubmitVersionDialog.submitNewVersionFailed'), 'error')
      }
    }
  }, [
    id,
    isNew,
    versionNumber,
    versionDescription,
    userId,
    prompt,
    parameters,
    modelConfig,
    workspaceId,
    setVersionDescription,
    setVersionNumberInitialized,
    setLastSavedTime,
    setHasUnsavedChanges,
    setDraftSavedTime,
    setIsDraftEdited,
    setVersionHistoryOpen,
    setLatestVersion,
    setIsLoadingFromAPI,
    loadPromptDetailToPage,
    loadDebugContext,
    resetVersionDialogState,
    t,
    showSnackbar,
    setSnackbar,
  ])

  return {
    // 状态
    submitVersionDialogOpen,
    submitVersionStep,
    promptCommitData,
    promptDraftData,
    versionNumber,
    versionNumberError,

    // 设置函数
    setPromptCommitData,
    setPromptDraftData,
    setVersionNumber,
    setVersionNumberError,

    // 操作函数
    handleSubmitVersion,
    handleCloseSubmitVersionDialog,
    handleNextStep,
    handlePrevStep,
    handleConfirmSubmitVersion,
  }
}
