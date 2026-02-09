import type { SnackbarMessage } from '@/Common/UnifiedSnackbar'
import type { NavigateFunction } from 'react-router-dom'
import type { RelationObj } from '@test-agentstudio/api-client'
import i18n from '@/i18n'

// 版本号格式验证函数
export const validateVersionNumber = (version: string): string => {
  if (!version) {
    return i18n.t('utils.prompts.utils.validateVersionNumber.empty')
  }

  // 检查版本号格式：主版本.次版本.修订版本
  const versionRegex = /^(\d+)\.(\d+)\.(\d+)$/
  if (!versionRegex.test(version)) {
    return i18n.t('utils.prompts.utils.validateVersionNumber.invalidFormat')
  }

  return '' // 无错误
}

// 时间格式化函数 - 格式化为标准显示格式
export const formatDateTime = (timestamp: number | string | Date): string => {
  try {
    let date: Date

    if (typeof timestamp === 'number') {
      // 如果是Unix时间戳，检查是否需要乘以1000
      if (timestamp < 10000000000) {
        // 小于10位数，说明是秒级时间戳，需要乘以1000
        date = new Date(timestamp * 1000)
      } else {
        // 大于等于10位数，说明是毫秒级时间戳
        date = new Date(timestamp)
      }
    } else if (typeof timestamp === 'string') {
      date = new Date(timestamp)
    } else {
      date = timestamp
    }

    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return i18n.t('utils.prompts.utils.formatDateTime.invalidTime')
    }

    // 直接格式化，不进行时区转换（API返回的时间已经是UTC+8）
    return date
      .toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
      .replace(/\//g, '-')
  } catch (error) {
    console.error('时间格式化失败:', error, '原始时间戳:', timestamp)
    return i18n.t('utils.prompts.utils.formatDateTime.formatError')
  }
}

// 草稿时间格式化函数 - 如果是今天则只显示时分秒，否则显示完整日期时间
export const formatDraftDateTime = (timestamp: number | string | Date): string => {
  try {
    let date: Date

    if (typeof timestamp === 'number') {
      // 如果是Unix时间戳，检查是否需要乘以1000
      if (timestamp < 10000000000) {
        // 小于10位数，说明是秒级时间戳，需要乘以1000
        date = new Date(timestamp * 1000)
      } else {
        // 大于等于10位数，说明是毫秒级时间戳
        date = new Date(timestamp)
      }
    } else if (typeof timestamp === 'string') {
      date = new Date(timestamp)
    } else {
      date = timestamp
    }

    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return i18n.t('utils.prompts.utils.formatDateTime.invalidTime')
    }

    // 判断是否为今天
    const now = new Date()
    const isToday = date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()

    if (isToday) {
      // 如果是今天，只显示时分秒
      return date.toLocaleString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } else {
      // 如果不是今天，显示完整的年月日时分秒
      return date
        .toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
        .replace(/\//g, '-')
    }
  } catch (error) {
    console.error('草稿时间格式化失败:', error, '原始时间戳:', timestamp)
    return i18n.t('utils.prompts.utils.formatDateTime.formatError')
  }
}

/**
 * 生成唯一的消息ID
 * 格式：时间戳 + 随机数
 * @returns 唯一的消息ID字符串
 */
export const messageId = (): string => {
  const date = new Date()
  const randomSuffix = Math.random().toString(36).substr(2, 9) // 生成9位随机字符串
  return date.getTime() + randomSuffix
}

/**
 * 通用的复制到剪贴板函数
 * @param text 要复制的文本内容
 * @param setSnackbar Snackbar状态设置函数
 * @param successMessage 成功消息
 */
export const copyToClipboard = async (
  text: string,
  setSnackbar: (snackbar: SnackbarMessage) => void,
  successMessage: string = i18n.t('utils.prompts.utils.copyToClipboard.defaultSuccess'),
): Promise<void> => {
  if (!text) {
    console.error('复制内容为空')
    setSnackbar({ open: true, message: i18n.t('utils.prompts.utils.copyToClipboard.emptyContent'), severity: 'error' })
    return
  }

  // 检查是否在对话框或抽屉环境中
  const isInDialog = document.querySelector('[role="dialog"]') || document.querySelector('.MuiDialog-root') || document.querySelector('[data-testid="dialog"]')
  const isInDrawer = document.querySelector('.MuiDrawer-root') || document.querySelector('[role="presentation"]')
  const isInModal = isInDialog || isInDrawer

  // 验证复制是否成功的函数
  const verifyClipboard = async (expectedText: string, execCommandSuccess: boolean = false): Promise<boolean> => {
    // 添加短暂延迟确保复制操作完成
    await new Promise(resolve => setTimeout(resolve, 100))

    try {
      if (navigator.clipboard && navigator.clipboard.readText && window.isSecureContext) {
        const clipboardText = await navigator.clipboard.readText()

        // 比较内容是否完全一致
        const isEqual = clipboardText === expectedText
        if (!isEqual) {
          // 如果 execCommand 返回成功，即使验证不匹配也信任 execCommand 的结果
          // 因为可能是换行符、编码等细微差异导致的验证失败，但实际复制已成功
          if (execCommandSuccess) {
            return true
          }
        }
        return isEqual
      }
    } catch (error) {
      // 在 HTTPS 环境下，readText() 可能因权限问题失败
      // 如果 execCommand 返回成功，应该信任 execCommand 的结果
      if (execCommandSuccess) {
        return true
      }
    }

    // 如果无法使用 Clipboard API 验证，但 execCommand 返回成功，则假设复制成功
    if (execCommandSuccess) {
      return true
    }

    return false
  }

  // 专门用于模态环境（对话框/抽屉）的复制方法
  const copyInDialog = async (text: string): Promise<void> => {
    // 创建一个临时的可编辑区域
    const tempDiv = document.createElement('div')
    tempDiv.contentEditable = 'true'
    tempDiv.innerHTML = text.replace(/\n/g, '<br>') // 将换行符转换为HTML换行
    tempDiv.style.position = 'fixed'
    tempDiv.style.left = '-9999px'
    tempDiv.style.top = '0'
    tempDiv.style.opacity = '0'
    tempDiv.style.pointerEvents = 'none'
    tempDiv.style.zIndex = '999999'
    tempDiv.style.width = '1px'
    tempDiv.style.height = '1px'

    document.body.appendChild(tempDiv)

    // 声明 selection 变量在 try 块外部，确保 finally 块可以访问
    let selection: Selection | null = null

    try {
      // 选择所有内容
      const range = document.createRange()
      range.selectNodeContents(tempDiv)
      selection = window.getSelection()
      selection?.removeAllRanges()
      selection?.addRange(range)

      // 执行复制
      const success = document.execCommand('copy')

      if (success) {
        setSnackbar({ open: true, message: successMessage, severity: 'success' })
      } else {
        fallbackCopy()
      }
    } finally {
      // 清理
      selection?.removeAllRanges()
      if (document.body.contains(tempDiv)) {
        document.body.removeChild(tempDiv)
      }
    }
  }

  try {
    // 方法1: 优先使用现代的 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text)

        // 验证复制是否真的成功
        const isVerified = await verifyClipboard(text)
        if (isVerified) {
          setSnackbar({ open: true, message: successMessage, severity: 'success' })
          return
        }
      } catch (clipboardError) {
        // 继续使用传统方法
      }
    }

    // 如果在模态环境中，使用特殊的复制方法
    if (isInModal) {
      await copyInDialog(text)
      return
    }

    // 方法2: 使用传统的 document.execCommand 方法（确保保持换行符）
    const textarea = document.createElement('textarea')
    textarea.value = text // 使用 value 属性确保保持换行符

    // 设置样式使其不可见但仍然可以被选中
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    textarea.style.opacity = '0'
    textarea.style.pointerEvents = 'none'
    textarea.style.tabIndex = '-1'
    textarea.style.zIndex = '999999' // 提高z-index确保在所有对话框之上
    textarea.setAttribute('readonly', '')

    // 将textarea添加到body而不是对话框内，确保它能获得焦点
    document.body.appendChild(textarea)

    try {
      // 选择文本
      textarea.focus() // 添加focus调用以确保元素获得焦点
      textarea.select()
      textarea.setSelectionRange(0, text.length)

      // 执行复制命令
      const successful = document.execCommand('copy')

      if (successful) {
        // 验证复制是否真的成功
        const isVerified = await verifyClipboard(text, successful)
        if (isVerified) {
          setSnackbar({ open: true, message: successMessage, severity: 'success' })
          return
        } else {
          await fallbackCopy()
        }
      } else {
        await fallbackCopy()
      }
    } finally {
      // 清理DOM元素
      if (document.body.contains(textarea)) {
        document.body.removeChild(textarea)
      }
    }
  } catch (err) {
    console.error('复制操作异常:', err)
    await fallbackCopy()
  }

  // 方法3: 最后的备用方案
  async function fallbackCopy() {
    try {
      // 使用textarea而不是div来保持换行符
      const textarea = document.createElement('textarea')
      textarea.value = text // 使用value而不是innerHTML来保持换行符
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      textarea.style.top = '0'
      textarea.style.opacity = '0'
      textarea.style.pointerEvents = 'none'
      textarea.style.tabIndex = '-1'
      textarea.style.zIndex = '999999' // 提高z-index确保在所有对话框之上
      textarea.setAttribute('readonly', '')

      document.body.appendChild(textarea)

      try {
        // 选择所有文本
        textarea.focus()
        textarea.select()
        textarea.setSelectionRange(0, text.length)

        // 尝试复制
        const success = document.execCommand('copy')

        if (success) {
          // 验证复制是否真的成功
          const isVerified = await verifyClipboard(text, success)
          if (isVerified) {
            setSnackbar({ open: true, message: successMessage, severity: 'success' })
          } else {
            setSnackbar({
              open: true,
              message: i18n.t('utils.prompts.utils.copyToClipboard.autoCopyFailed'),
              severity: 'error',
            })
          }
        } else {
          setSnackbar({
            open: true,
            message: i18n.t('prompts.utils.copyToClipboard.autoCopyFailed'),
            severity: 'error',
          })
        }
      } finally {
        // 清理DOM元素
        if (document.body.contains(textarea)) {
          document.body.removeChild(textarea)
        }
      }
    } catch (fallbackErr) {
      console.error('备用复制方法也失败:', fallbackErr)
      setSnackbar({
        open: true,
        message: i18n.t('utils.prompts.utils.copyToClipboard.copyUnavailable'),
        severity: 'error',
      })
    }
  }
}

/**
 * 处理关联对象跳转
 * @param relationObj 关联对象信息
 * @param workspaceId 工作空间ID
 * @param navigate 导航函数
 */
export const handleRelationObjNavigate = (relationObj: RelationObj, workspaceId: string, navigate: NavigateFunction) => {
  // 根据对象类型跳转到对应页面
  if (relationObj.obj_type_name === 'WORKFLOW') {
    // 工作流ID格式：workflowId&nodeId
    const parts = relationObj.obj_id.split('&')
    const workflowId = parts[0]
    const nodeId = parts[1] || ''

    // 构建工作流编辑器URL
    const url = `/dashboard/workflows/editor/${workflowId}?spaceId=${workspaceId}${nodeId ? `&nodeId=${nodeId}` : ''}`
    navigate(url)
  } else {
    const objTypeMap: { [key: string]: string } = {
      AGENT: 'agents',
      APP: 'apps',
    }
    const routePath = objTypeMap[relationObj.obj_type_name] || 'agents'
    navigate(`/dashboard/${routePath}/${relationObj.obj_id}`)
  }
}

/**
 * 处理输入框的 Enter 键事件
 * - Enter: 发送消息
 * - Shift+Enter: 换行（使用默认行为）
 * - Ctrl+Enter: 换行（手动插入换行符）
 * - Alt+Enter: 换行（手动插入换行符）
 * @param isReadOnlyMode 是否为只读模式
 * @param onInputChange 输入内容变化回调函数
 * @param onSend 发送消息回调函数
 * @returns 键盘事件处理函数
 */
export const handleInputEnterKey = (
  isReadOnlyMode: boolean,
  onInputChange: (value: string) => void,
  onSend: () => void,
): React.KeyboardEventHandler => {
  return (e: React.KeyboardEvent) => {
    if (isReadOnlyMode) {
      return
    }
    if (e.key === 'Enter') {
      // Shift+Enter 使用默认行为换行
      if (e.shiftKey) {
        return
      }
      // Ctrl+Enter 或 Alt+Enter 手动插入换行
      if (e.ctrlKey || e.altKey) {
        e.preventDefault()
        const target = e.target as HTMLTextAreaElement
        const start = target.selectionStart
        const end = target.selectionEnd
        const value = target.value
        const newValue = value.substring(0, start) + '\n' + value.substring(end)
        onInputChange(newValue)
        // 设置光标位置到换行符后面
        setTimeout(() => {
          target.selectionStart = target.selectionEnd = start + 1
        }, 0)
        return
      }
      // 单独 Enter 发送消息
      e.preventDefault()
      onSend()
    }
  }
}