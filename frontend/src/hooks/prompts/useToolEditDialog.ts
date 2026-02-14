import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import type { EditingTool } from '@/components/Prompts'
import type { ComparisonGroupData } from '@/types/promptType'

interface ToolContext {
  groupId: number | undefined // undefined为主页面，0为基准组，>=1为对照组
}

interface UseToolEditDialogProps {
  tools: any[]
  setTools: (tools: any[]) => void
  toolsEnabled: boolean
  comparisonGroupsData: ComparisonGroupData[]
  setComparisonGroupsData: React.Dispatch<React.SetStateAction<ComparisonGroupData[]>>
  showSnackbar: (message: string, severity: 'success' | 'error' | 'warning' | 'info') => void
  setHasUnsavedChanges: (hasChanges: boolean) => void
  triggerAutoSave: (data?: any) => void
}

export const useToolEditDialog = ({
  tools,
  setTools,
  toolsEnabled,
  comparisonGroupsData,
  setComparisonGroupsData,
  showSnackbar,
  setHasUnsavedChanges,
  triggerAutoSave,
}: UseToolEditDialogProps) => {
  const { t } = useTranslation()
  // 工具编辑相关状态
  const [editingTool, setEditingTool] = useState<EditingTool | null>(null)
  const [toolDialogOpen, setToolDialogOpen] = useState(false)
  const [currentToolContext, setCurrentToolContext] = useState<ToolContext>({ groupId: undefined })

  // 统一的工具添加函数 - 支持主页面和对比模式
  const handleAddTool = useCallback((groupId?: number) => {
    // 初始化编辑工具状态
    setEditingTool({
      id: '',
      name: '',
      description: '',
      parameters: [],
      defaultValue: '',
      fieldType: 'PlainText' as const,
    })

    // 根据参数设置上下文 - 统一使用 {groupId} 格式
    setCurrentToolContext({ groupId })
    if (groupId !== undefined) {
      console.log(
        `🔧 [ADD-TOOL] ${groupId === 0 ? t('hooks.prompts.useToolEditDialog.addToolContextBaseGroup', { groupId }) : t('hooks.prompts.useToolEditDialog.addToolContextControlGroup', { groupId })}`,
      )
    } else {
      console.log(`🔧 [ADD-TOOL] ${t('hooks.prompts.useToolEditDialog.addToolContextMain')}`)
    }

    setToolDialogOpen(true)
    console.log(`🔧 [ADD-TOOL] ${t('hooks.prompts.useToolEditDialog.toolDialogOpened')}`)
  }, [t])

  // 工具编辑函数
  const handleEditTool = useCallback((tool: any, context?: 'main' | 'base' | number | { type: 'control'; groupId: number }) => {
    // 将Tool转换为EditingTool格式，保留parametersJsonSchema和parametersMode（参考PromptOptimizeEditPage的逻辑）
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
    console.log(`🔧 [EDIT-TOOL] ${t('hooks.prompts.useToolEditDialog.editToolParametersMode', { name: tool.name })}`, tool.parametersMode)
    setEditingTool(editingTool)

    // 统一转换为新的格式 {groupId}
    let groupId: number | undefined
    if (context === 'main' || context === undefined) {
      groupId = undefined // 主页面
    } else if (context === 'base' || context === 0) {
      groupId = 0 // 基准组
    } else if (typeof context === 'number' && context > 0) {
      groupId = context // 对照组
    } else if (typeof context === 'object' && context.type === 'control') {
      groupId = context.groupId // 对照组（对象格式）
    } else {
      groupId = undefined // 默认主页面
    }

    setCurrentToolContext({ groupId })
    console.log(`🔧 [EDIT-TOOL] ${t('hooks.prompts.useToolEditDialog.editToolContextSet')}`, { groupId })
    setToolDialogOpen(true)
  }, [t])

  // 工具删除函数
  const handleDeleteTool = useCallback(
    (toolId: string) => {
      const newTools = tools.filter(tool => tool.id !== toolId)
      setTools(newTools)
      showSnackbar(t('hooks.prompts.useToolEditDialog.toolDeleteSuccess'), 'success')

      // 使用更新后的工具列表触发自动保存
      setHasUnsavedChanges(true)
      triggerAutoSave({
        tools: newTools,
        toolsEnabled: toolsEnabled,
      })
    },
    [tools, setTools, toolsEnabled, showSnackbar, setHasUnsavedChanges, triggerAutoSave, t],
  )

  // 工具保存函数 - 接收ToolEditDialog传递的updatedTool（包含parametersJsonSchema）
  const handleSaveTool = useCallback(
    (updatedTool?: EditingTool) => {
      // 如果传入了updatedTool，使用它（来自ToolEditDialog的onSave回调）
      // 否则使用当前的editingTool（向后兼容）
      const toolToProcess = updatedTool || editingTool
      if (!toolToProcess) {
        return
      }

      if (!toolToProcess.name.trim()) {
        showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameRequired'), 'error')
        return
      }

      // 确保 toolToSave 包含所有必要的字段，特别是 parameters、parametersJsonSchema 和 parametersMode
      const toolToSave = toolToProcess.id
        ? {
            ...toolToProcess,
            // 确保包含更新后的 parameters、parametersJsonSchema 和 parametersMode
            parameters: toolToProcess.parameters || [],
            parametersJsonSchema: toolToProcess.parametersJsonSchema,
            parametersMode: toolToProcess.parametersMode, // 保留参数模式
          }
        : {
            ...toolToProcess,
            id: `tool_${Date.now()}`,
            // 确保包含更新后的 parameters、parametersJsonSchema 和 parametersMode
            parameters: toolToProcess.parameters || [],
            parametersJsonSchema: toolToProcess.parametersJsonSchema,
            parametersMode: toolToProcess.parametersMode, // 保留参数模式
          }

      // 根据当前上下文决定更新哪个工具列表
      const { groupId: contextGroupId } = currentToolContext
      let updatedTools = tools

      // 判断是新增还是编辑：检查原始工具是否有id（空字符串或undefined表示新增）
      const isNewTool = !toolToProcess.id || toolToProcess.id.trim() === ''

      // 工具名称重复检查函数
      const checkToolNameDuplicate = (toolList: any[], toolName: string, excludeToolId?: string): boolean => {
        return toolList.some(tool => {
          // 编辑模式下，排除当前编辑的工具本身
          if (excludeToolId && tool.id === excludeToolId) {
            return false
          }
          // 比较工具名称（区分大小写）
          return tool.name.trim() === toolName.trim()
        })
      }

      if (contextGroupId === undefined) {
        // 主页面工具
        // 检查工具名称是否重复
        if (isNewTool) {
          // 新增工具：检查名称是否已存在
          if (checkToolNameDuplicate(tools, toolToSave.name)) {
            showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameExists'), 'error')
            return
          }
          // 新增工具：添加到列表
          updatedTools = [...tools, toolToSave]
        } else {
          // 编辑工具：检查名称是否与其他工具重复（排除当前编辑的工具）
          if (checkToolNameDuplicate(tools, toolToSave.name, toolToSave.id)) {
            showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameExists'), 'error')
            return
          }
          // 编辑工具：更新列表中对应的工具
          const existingIndex = tools.findIndex(tool => tool.id === toolToSave.id)
          if (existingIndex >= 0) {
            updatedTools = tools.map(tool => (tool.id === toolToSave.id ? toolToSave : tool))
          } else {
            // 如果找不到，作为新增处理（兜底逻辑）
            // 但需要检查名称是否重复
            if (checkToolNameDuplicate(tools, toolToSave.name)) {
              showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameExists'), 'error')
              return
            }
            updatedTools = [...tools, toolToSave]
          }
        }
        setTools(updatedTools)

        // 主页面工具操作：先更新状态，然后触发自动保存
        setHasUnsavedChanges(true)
        console.log('🔧 [TOOL-SAVE]', t('hooks.prompts.useToolEditDialog.toolSaveTriggerLog'), updatedTools?.length, updatedTools?.map((toolItem: any) => ({ name: toolItem.name, defaultValue: toolItem.defaultValue })))
        triggerAutoSave({
          tools: updatedTools,
          toolsEnabled: toolsEnabled,
        })
      } else {
        // 对比模式工具（基准组或对照组）
        const groupType = contextGroupId === 0 ? '基准组' : '对照组'

        // 获取当前组的工具列表
        const currentGroup = comparisonGroupsData.find(g => g.id === contextGroupId)
        const groupTools = currentGroup?.tools || []

        // 检查工具名称是否重复
        if (isNewTool) {
          // 新增工具：检查名称是否已存在
          if (checkToolNameDuplicate(groupTools, toolToSave.name)) {
            showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameExists'), 'error')
            return
          }
        } else {
          // 编辑工具：检查名称是否与其他工具重复（排除当前编辑的工具）
          if (checkToolNameDuplicate(groupTools, toolToSave.name, toolToSave.id)) {
            showSnackbar(t('hooks.prompts.useToolEditDialog.toolNameExists'), 'error')
            return
          }
        }

        // 计算更新后的工具列表
        const currentGroupTools = groupTools
        let updatedGroupTools: any[]

        if (isNewTool) {
          // 新增工具：添加到列表
          updatedGroupTools = [...currentGroupTools, toolToSave]
        } else {
          // 编辑工具：更新列表中对应的工具
          const existingIndex = currentGroupTools.findIndex(tool => tool.id === toolToSave.id)
          if (existingIndex >= 0) {
            updatedGroupTools = currentGroupTools.map(tool => (tool.id === toolToSave.id ? toolToSave : tool))
          } else {
            // 如果找不到，作为新增处理（兜底逻辑）
            updatedGroupTools = [...currentGroupTools, toolToSave]
          }
        }

        // 计算更新后的 groups 数据
        const updatedGroups = comparisonGroupsData.map(group => {
          if (group.id === contextGroupId) {
            return { ...group, tools: updatedGroupTools }
          }
          return group
        })

        setComparisonGroupsData(updatedGroups)

        // 在对比模式下，使用更新后的 groups 数据触发自动保存
        setHasUnsavedChanges(true)
        triggerAutoSave({
          comparisonGroups: updatedGroups,
        })
      }

      setToolDialogOpen(false)
      setEditingTool(null)

      setCurrentToolContext({ groupId: undefined }) // 重置为默认上下文（主页面）
      showSnackbar(t('hooks.prompts.useToolEditDialog.toolSaveSuccess'), 'success')
    },
    [
      editingTool,
      currentToolContext,
      tools,
      setTools,
      comparisonGroupsData,
      setComparisonGroupsData,
      toolsEnabled,
      setHasUnsavedChanges,
      triggerAutoSave,
      showSnackbar,
      t,
    ],
  )

  // 关闭工具对话框
  const handleCloseToolDialog = useCallback(() => {
    setToolDialogOpen(false)
    setEditingTool(null)
  }, [])

  return {
    // 状态
    editingTool,
    setEditingTool,
    toolDialogOpen,
    currentToolContext,

    // 函数
    handleAddTool,
    handleEditTool,
    handleDeleteTool,
    handleSaveTool,
    handleCloseToolDialog,
  }
}
