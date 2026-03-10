import React, { useState, useEffect } from 'react'
import { X, Plus, Search, Edit, Trash2, Save, XCircle, CheckCircle, Palette } from 'lucide-react'
import { getTagStyleInfo, colorOptions } from '../../utils/tagUtils'

// Add custom CSS for animations
const styles = `
  @keyframes fade-in {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes scale-in {
    from {
      transform: scale(0.95);
      opacity: 0;
    }
    to {
      transform: scale(1);
      opacity: 1;
    }
  }

  @keyframes pulse-ring {
    0% {
      transform: scale(0.95);
      box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
    }
    70% {
      transform: scale(1);
      box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
    }
    100% {
      transform: scale(0.95);
      box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
    }
  }

  .animate-fade-in {
    animation: fade-in 0.2s ease-out;
  }

  .animate-scale-in {
    animation: scale-in 0.15s ease-out;
  }

  .animate-pulse-ring {
    animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  .color-hover {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .color-hover:hover {
    transform: scale(1.1);
    box-shadow: var(--workflow-shadow-node);
  }

  /* 响应式布局优化 */
  @media (max-width: 640px) {
    .color-picker-mobile {
      width: calc(100vw - 2rem) !important;
      max-width: 100% !important;
      right: 1rem !important;
      left: 1rem !important;
    }

    .mobile-grid {
      grid-template-columns: repeat(6, 1fr) !important;
    }

    .mobile-palette-grid {
      grid-template-columns: repeat(4, 1fr) !important;
    }

    .mobile-custom-grid {
      grid-template-columns: repeat(6, 1fr) !important;
    }
  }

  /* 颜色选择器增强动画 */
  .color-ripple {
    position: relative;
    overflow: hidden;
  }

  .color-ripple::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
  }

  .color-ripple:active::before {
    width: 100px;
    height: 100px;
  }

  /* 平滑滚动 */
  .smooth-scroll {
    scroll-behavior: smooth;
    scrollbar-width: thin;
    scrollbar-color: #E5E7EB #F9FAFB;
  }

  .smooth-scroll::-webkit-scrollbar {
    width: 6px;
  }

  .smooth-scroll::-webkit-scrollbar-track {
    background: #F9FAFB;
    border-radius: 3px;
  }

  .smooth-scroll::-webkit-scrollbar-thumb {
    background: #E5E7EB;
    border-radius: 3px;
  }

  .smooth-scroll::-webkit-scrollbar-thumb:hover {
    background: #D1D5DB;
  }

  /* 标签限制提示动画 */
  @keyframes slide-down {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
    20%, 40%, 60%, 80% { transform: translateX(2px); }
  }

  .animate-slide-down {
    animation: slide-down 0.3s ease-out;
  }

  .animate-shake {
    animation: shake 0.5s ease-in-out;
  }

  .tag-limit-alert {
    backdrop-filter: blur(4px);
  }
`

// Inject styles into document head
if (typeof document !== 'undefined' && !document.getElementById('tag-modal-styles')) {
  const styleSheet = document.createElement('style')
  styleSheet.id = 'tag-modal-styles'
  styleSheet.textContent = styles
  document.head.appendChild(styleSheet)
}
import {
  useTags,
  useCreateTag,
  useUpdateTag,
  useDeleteTag,
  useSearchTags,
  type Tag,
  type TagCreate,
  type TagUpdate,
  type TagUpdateRequest,
  type TagListRequest,
  type TagSearchRequest,
} from '@test-agentstudio/api-client'

interface TagManagementModalProps {
  isOpen: boolean
  onClose: () => void
  spaceId: string
  selectedTags: Tag[]
  onTagsChange: (tags: Tag[]) => void
  maxTags?: number
  title?: string
}

const TagManagementModal: React.FC<TagManagementModalProps> = ({ isOpen, onClose, spaceId, selectedTags, onTagsChange, maxTags = 3, title = '标签管理' }) => {
  // DFX: 模态框初始化日志
  if (isOpen) {
    console.log('[DFX:TagModal] 初始化', {
      spaceId,
      selectedTagsCount: selectedTags.length,
      maxTags,
      title,
    })
  }

  const [searchTerm, setSearchTerm] = useState('')
  const [editingTag, setEditingTag] = useState<Tag | null>(null)
  const [newTagName, setNewTagName] = useState('')
  const [selectedColor, setSelectedColor] = useState<string>('#3B82F6') // 默认蓝色
  const [creatingNew, setCreatingNew] = useState(false)
  const [tempSelectedTags, setTempSelectedTags] = useState<Tag[]>(selectedTags)
  const [showColorPicker, setShowColorPicker] = useState(false)

  // DFX: 标签选择状态同步
  useEffect(() => {
    if (selectedTags.length !== tempSelectedTags.length) {
      console.log('[DFX:TagModal] 同步选择状态', {
        from: tempSelectedTags.length,
        to: selectedTags.length,
      })
      setTempSelectedTags(selectedTags)
    }
  }, [selectedTags])

  // 获取标签列表
  const tagsRequest: TagListRequest = {
    space_id: spaceId,
    is_active: true,
    page: 1,
    page_size: 100,
  }
  const { data: tagsResponse, isLoading: tagsLoading, refetch } = useTags(tagsRequest)

  // 搜索标签
  const searchRequest: TagSearchRequest = {
    space_id: spaceId,
    search_pattern: searchTerm,
    is_active: true,
    page: 1,
    page_size: 50,
  }
  const { data: searchResponse } = useSearchTags(searchRequest, searchTerm.trim().length > 0)

  // 标签操作hooks
  const createTagMutation = useCreateTag()
  const updateTagMutation = useUpdateTag()
  const deleteTagMutation = useDeleteTag()

  // DFX: 搜索状态监控
  useEffect(() => {
    if (searchTerm && searchResponse) {
      console.log('[DFX:TagModal] 搜索结果', {
        searchTerm,
        resultCount: searchResponse?.data?.length || 0,
      })
    }
  }, [searchTerm, searchResponse])

  // DFX: 标签列表加载监控
  useEffect(() => {
    if (!searchTerm && tagsResponse) {
      console.log('[DFX:TagModal] 标签列表加载', {
        count: tagsResponse?.data?.tags?.length || 0,
      })
    }
  }, [searchTerm, tagsResponse])

  // DFX: 可用标签列表 - 优化性能，使用记忆化
  const availableTags = React.useMemo(() => {
    const tags = searchTerm.trim().length > 0 ? searchResponse?.data || [] : tagsResponse?.data?.tags || []
    console.log('[DFX:TagModal] 计算可用标签', {
      searchTerm,
      count: tags.length,
      source: searchTerm ? 'search' : 'normal',
    })
    return tags
  }, [searchTerm, searchResponse, tagsResponse])

  // DFX: 未选择的标签 - 优化性能，使用记忆化
  const unselectedTags = React.useMemo(() => {
    const filtered = availableTags.filter(tag => !tempSelectedTags.some(selected => selected.primary_id === tag.primary_id))
    console.log('[DFX:TagModal] 计算未选择标签', {
      totalAvailable: availableTags.length,
      selectedCount: tempSelectedTags.length,
      unselectedCount: filtered.length,
    })
    return filtered
  }, [availableTags, tempSelectedTags])

  // DFX: 标签选择处理
  const handleTagSelect = (tag: Tag) => {
    console.log('[DFX:TagModal] 选择标签', {
      tag: tag.tag_name,
      currentCount: tempSelectedTags.length,
      maxTags,
    })

    if (tempSelectedTags.length >= maxTags) {
      console.log('[DFX:TagModal] 达到标签限制', maxTags)
      setShowLimitAlert(true)
      // 3秒后自动隐藏提示
      setTimeout(() => setShowLimitAlert(false), 3000)
      return
    }

    const newSelectedTags = [...tempSelectedTags, tag]
    setTempSelectedTags(newSelectedTags)
  }

  // DFX: 标签移除处理
  const handleTagRemove = (tag: Tag) => {
    console.log('[DFX:TagModal] 移除标签', {
      tag: tag.tag_name,
      fromCount: tempSelectedTags.length,
      toCount: tempSelectedTags.length - 1,
    })

    const newSelectedTags = tempSelectedTags.filter(t => t.primary_id !== tag.primary_id)
    setTempSelectedTags(newSelectedTags)
  }

  // DFX: 开始创建新标签
  const handleStartCreate = () => {
    console.log('[DFX:TagModal] 开始创建新标签')
    setCreatingNew(true)
    setNewTagName('')
    setSelectedColor(colorOptions[0].hex) // 重置为默认颜色
    setEditingTag(null)
  }

  // DFX: 创建新标签
  const handleCreateTag = async () => {
    if (!newTagName.trim()) {
      console.log('[DFX:TagModal] 创建失败: 标签名称为空')
      return
    }

    const tagName = newTagName.trim()
    console.log('[DFX:TagModal] 创建新标签', { tagName, spaceId, color: selectedColor })

    try {
      const request = {
        tag: {
          space_id: spaceId,
          tag_name: tagName,
          is_active: true,
          tag_color: selectedColor,
        },
      }

      const response = await createTagMutation.mutateAsync(request)

      if (response.code === 200) {
        console.log('[DFX:TagModal] 创建成功', { tagName, color: selectedColor })
        setCreatingNew(false)
        setNewTagName('')
        setSelectedColor(colorOptions[0].hex) // 重置为默认颜色
        refetch()
      } else {
        console.error('[DFX:TagModal] 创建失败', response.message)
        alert(`创建标签失败: ${response.message || '未知错误'}`)
      }
    } catch (error: any) {
      console.error('[DFX:TagModal] 创建异常', error)
      let errorMessage = '创建标签失败，请稍后重试'
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.message) {
        errorMessage = error.message
      }
      alert(errorMessage)
    }
  }

  // DFX: 开始编辑标签
  const handleStartEdit = (tag: Tag) => {
    console.log('[DFX:TagModal] 开始编辑标签', {
      tag: tag.tag_name,
      tagId: tag.primary_id,
      currentColor: tag.tag_color,
    })
    setEditingTag(tag)
    setNewTagName(tag.tag_name)
    setSelectedColor(tag.tag_color || colorOptions[0].hex) // 使用标签现有颜色或默认颜色
    setCreatingNew(false)
  }

  // 更新标签
  const handleUpdateTag = async () => {
    if (!editingTag || !newTagName.trim()) return

    try {
      const updateRequest: TagUpdateRequest = {
        tag_data: {
          tag_name: newTagName.trim(),
          is_active: true,
          tag_color: selectedColor,
        },
        query: {
          primary_id: editingTag.primary_id,
        },
      }

      const response = await updateTagMutation.mutateAsync({
        tagId: editingTag.primary_id,
        request: updateRequest,
      })

      if (response.code === 200) {
        console.log('[DFX:TagModal] 更新成功', { tagName: newTagName.trim(), color: selectedColor })
        setEditingTag(null)
        setNewTagName('')
        setSelectedColor(colorOptions[0].hex) // 重置为默认颜色
        refetch()
      } else {
        alert(`更新标签失败: ${response.message || '未知错误'}`)
      }
    } catch (error: any) {
      let errorMessage = '更新标签失败，请稍后重试'
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.message) {
        errorMessage = error.message
      }
      alert(errorMessage)
    }
  }

  // 删除标签
  const handleDeleteTag = async (tag: Tag) => {
    if (!confirm(`确定要删除标签"${tag.tag_name}"吗？删除后将无法恢复。`)) {
      return
    }

    try {
      const response = await deleteTagMutation.mutateAsync({
        spaceId: spaceId,
        tagName: tag.tag_name,
      })

      if (response.code === 200) {
        // 如果删除的标签在已选列表中，也需要移除
        if (tempSelectedTags.some(t => t.primary_id === tag.primary_id)) {
          handleTagRemove(tag)
        }
        refetch()
      } else {
        alert(`删除标签失败: ${response.message || '未知错误'}`)
      }
    } catch (error: any) {
      console.error('删除标签失败:', error)
      let errorMessage = '删除标签失败，请稍后重试'
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.response?.data?.detail?.[0]?.msg) {
        errorMessage = error.response.data.detail[0].msg
      } else if (error.message) {
        errorMessage = error.message
      }
      alert(errorMessage)
    }
  }

  // DFX: 取消编辑/创建
  const handleCancel = () => {
    console.log('[DFX:TagModal] 取消操作', {
      wasEditing: editingTag !== null,
      wasCreating: creatingNew,
    })
    setEditingTag(null)
    setCreatingNew(false)
    setNewTagName('')
  }

  // 色调板 - 按色系分组
  const colorPalette = [
    {
      name: '蓝色系',
      colors: ['#1E40AF', '#2563EB', '#3B82F6', '#60A5FA', '#93BBFC', '#BFDBFE'],
    },
    {
      name: '绿色系',
      colors: ['#14532D', '#15803D', '#16A34A', '#22C55E', '#4ADE80', '#86EFAC'],
    },
    {
      name: '紫色系',
      colors: ['#581C87', '#7C3AED', '#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE'],
    },
    {
      name: '红色系',
      colors: ['#7F1D1D', '#B91C1C', '#EF4444', '#F87171', '#FCA5A5', '#FECACA'],
    },
    {
      name: '橙色系',
      colors: ['#7C2D12', '#C2410C', '#F97316', '#FB923C', '#FDBA74', '#FED7AA'],
    },
    {
      name: '灰色系',
      colors: ['#1F2937', '#374151', '#4B5563', '#6B7280', '#9CA3AF', '#D1D5DB'],
    },
  ]

  // 自定义颜色状态
  const [customColor, setCustomColor] = useState<string>('#3B82F6')
  const [activeTab, setActiveTab] = useState<'preset' | 'palette' | 'custom'>('preset')
  const [showLimitAlert, setShowLimitAlert] = useState<boolean>(false)

  // 键盘快捷键支持
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      // Escape 键关闭模态框或颜色选择器
      if (e.key === 'Escape') {
        if (showColorPicker) {
          closeColorPicker()
        } else if (creatingNew || editingTag) {
          handleCancel()
        } else {
          onClose()
        }
        return
      }

      // Enter 键确认操作（仅在颜色选择器激活时）
      if (e.key === 'Enter' && showColorPicker) {
        if (activeTab === 'custom') {
          handleColorSelect(customColor)
        }
        return
      }

      // Tab 键切换颜色选择器标签页
      if (e.key === 'Tab' && showColorPicker && e.ctrlKey) {
        e.preventDefault()
        const tabs: Array<'preset' | 'palette' | 'custom'> = ['preset', 'palette', 'custom']
        const currentIndex = tabs.indexOf(activeTab)
        const nextIndex = (currentIndex + 1) % tabs.length
        setActiveTab(tabs[nextIndex])
        return
      }

      // 数字键快速切换标签页
      if (showColorPicker && e.key >= '1' && e.key <= '3') {
        const tabIndex = parseInt(e.key) - 1
        const tabs: Array<'preset' | 'palette' | 'custom'> = ['preset', 'palette', 'custom']
        if (tabIndex < tabs.length) {
          setActiveTab(tabs[tabIndex])
        }
        return
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, showColorPicker, activeTab, creatingNew, editingTag, customColor])

  // 颜色选择处理函数
  const handleColorSelect = (color: string) => {
    setSelectedColor(color)
    setShowColorPicker(false)
  }

  // 自定义颜色处理
  const handleCustomColorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const color = e.target.value
    setCustomColor(color)
    setSelectedColor(color)
  }

  // 关闭颜色选择器
  const closeColorPicker = () => {
    setShowColorPicker(false)
    setActiveTab('preset')
  }

  if (!isOpen) return null

  return (
    <>
      {/* 标签数量限制提示 */}
      {showLimitAlert && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-[60]">
          <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 shadow-sm animate-slide-down tag-limit-alert">
            <div className="flex items-center space-x-2">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-amber-800">每个工作流最多只能设置 3 个标签</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
          {/* 头部 */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">{title}</h2>
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 已选择标签 */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">
                已选择的标签 ({tempSelectedTags.length}/{maxTags})
              </h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {tempSelectedTags.map(tag => {
                const styleInfo = getTagStyleInfo(tag)
                console.log('[DFX:TagManagementModal] 已选标签样式渲染', {
                  tagId: tag.primary_id,
                  tagName: tag.tag_name,
                  isDarkBackground: !!styleInfo.style.textShadow,
                })
                return (
                  <div
                    key={tag.primary_id}
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${styleInfo.className}`}
                    style={styleInfo.style}
                  >
                    <span>{tag.tag_name}</span>
                    <button onClick={() => handleTagRemove(tag)} className="ml-2 hover:text-red-600 transition-colors">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                )
              })}
              {tempSelectedTags.length === 0 && <span className="text-gray-500 text-sm">暂未选择标签</span>}
            </div>
          </div>

          {/* 搜索和创建 */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center gap-4 mb-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索标签..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300"
                />
              </div>
              <button
                onClick={handleStartCreate}
                className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                disabled={creatingNew || editingTag !== null}
              >
                <Plus className="w-4 h-4" />
                <span>新建标签</span>
              </button>
            </div>

            {/* 创建/编辑表单 */}
            {(creatingNew || editingTag) && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="space-y-4">
                  {/* 标签名称输入 */}
                  <div className="flex items-center gap-4">
                    <input
                      type="text"
                      placeholder="输入标签名称..."
                      value={newTagName}
                      onChange={e => setNewTagName(e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-300"
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          if (creatingNew) handleCreateTag()
                          else if (editingTag) handleUpdateTag()
                        } else if (e.key === 'Escape') {
                          handleCancel()
                        }
                      }}
                      autoFocus
                    />
                  </div>

                  {/* 颜色选择器 */}
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium text-gray-700 w-20">标签颜色:</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowColorPicker(!showColorPicker)}
                        className="flex items-center space-x-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <div className="w-4 h-4 rounded-full border border-gray-300" style={{ backgroundColor: selectedColor }} />
                        <span className="text-sm text-gray-600">{colorOptions.find(opt => opt.hex === selectedColor)?.name || '自定义'}</span>
                        <Palette className="w-4 h-4 text-gray-400" />
                      </button>

                      {showColorPicker && (
                        <div className="absolute z-10 bg-white border border-gray-200 rounded-lg shadow-xl p-4 mt-12 w-80 animate-fade-in color-picker-mobile">
                          {/* 关闭按钮 */}
                          <div className="flex justify-between items-center mb-3">
                            <h4 className="text-sm font-semibold text-gray-800">选择标签颜色</h4>
                            <button onClick={closeColorPicker} className="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors">
                              <X className="w-4 h-4" />
                            </button>
                          </div>

                          {/* 标签页导航 */}
                          <div className="flex space-x-1 mb-3 bg-gray-100 p-1 rounded-lg">
                            <button
                              onClick={() => setActiveTab('preset')}
                              className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                                activeTab === 'preset'
                                  ? 'bg-white text-blue-600 shadow-sm transform scale-105'
                                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                              }`}
                            >
                              预设
                            </button>
                            <button
                              onClick={() => setActiveTab('palette')}
                              className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                                activeTab === 'palette'
                                  ? 'bg-white text-blue-600 shadow-sm transform scale-105'
                                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                              }`}
                            >
                              色板
                            </button>
                            <button
                              onClick={() => setActiveTab('custom')}
                              className={`flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                                activeTab === 'custom'
                                  ? 'bg-white text-blue-600 shadow-sm transform scale-105'
                                  : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                              }`}
                            >
                              自定义
                            </button>
                          </div>

                          {/* 标签页内容 */}
                          <div className="max-h-64 overflow-y-auto smooth-scroll">
                            {/* 预设颜色标签页 */}
                            {activeTab === 'preset' && (
                              <div>
                                <div className="grid grid-cols-6 gap-2">
                                  {colorOptions.map(color => (
                                    <button
                                      key={color.hex}
                                      onClick={() => handleColorSelect(color.hex)}
                                      className={`w-8 h-8 rounded-full border-2 color-hover color-ripple ${
                                        selectedColor === color.hex
                                          ? 'border-gray-800 scale-110 ring-2 ring-offset-2 ring-gray-300 animate-pulse-ring'
                                          : 'border-gray-300'
                                      }`}
                                      style={{ backgroundColor: color.hex }}
                                      title={color.name}
                                    />
                                  ))}
                                </div>
                                <p className="text-xs text-gray-500 mt-2">点击选择预设颜色</p>
                              </div>
                            )}

                            {/* 色调板标签页 */}
                            {activeTab === 'palette' && (
                              <div className="space-y-3">
                                {colorPalette.map(palette => (
                                  <div key={palette.name}>
                                    <h5 className="text-xs font-medium text-gray-700 mb-2">{palette.name}</h5>
                                    <div className="flex gap-1">
                                      {palette.colors.map((color, index) => (
                                        <button
                                          key={`${palette.name}-${index}`}
                                          onClick={() => handleColorSelect(color)}
                                          className={`w-6 h-6 rounded border-2 transition-all hover:scale-110 ${
                                            selectedColor === color
                                              ? 'border-gray-800 scale-110 ring-2 ring-offset-1 ring-gray-300'
                                              : 'border-gray-300 hover:border-gray-500'
                                          }`}
                                          style={{ backgroundColor: color }}
                                          title={`${palette.name} 色调 ${index + 1}`}
                                        />
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* 自定义颜色标签页 */}
                            {activeTab === 'custom' && (
                              <div className="space-y-3">
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-full border-2 border-gray-300" style={{ backgroundColor: customColor }} />
                                  <input
                                    type="color"
                                    value={customColor}
                                    onChange={handleCustomColorChange}
                                    className="w-12 h-8 p-0 border-0 bg-transparent cursor-pointer"
                                  />
                                  <input
                                    type="text"
                                    value={customColor}
                                    onChange={handleCustomColorChange}
                                    className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded"
                                    placeholder="#000000"
                                  />
                                </div>

                                {/* 常用自定义颜色 */}
                                <div>
                                  <h5 className="text-xs font-medium text-gray-700 mb-2">常用颜色</h5>
                                  <div className="grid grid-cols-8 gap-1">
                                    {[
                                      '#FF6B6B',
                                      '#4ECDC4',
                                      '#45B7D1',
                                      '#96CEB4',
                                      '#FFEAA7',
                                      '#DDA0DD',
                                      '#98D8C8',
                                      '#F7DC6F',
                                      '#BB8FCE',
                                      '#85C1E9',
                                      '#F8C471',
                                      '#82E0AA',
                                      '#F1948A',
                                      '#85C1E9',
                                      '#D7BDE2',
                                      '#A9DFBF',
                                    ].map(color => (
                                      <button
                                        key={color}
                                        onClick={() => handleColorSelect(color)}
                                        className={`w-6 h-6 rounded border transition-all hover:scale-110 ${
                                          selectedColor === color
                                            ? 'border-gray-800 scale-110 ring-2 ring-offset-1 ring-gray-300'
                                            : 'border-gray-300 hover:border-gray-500'
                                        }`}
                                        style={{ backgroundColor: color }}
                                      />
                                    ))}
                                  </div>
                                </div>

                                <button
                                  onClick={() => handleColorSelect(customColor)}
                                  className="w-full py-2 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                  使用此颜色
                                </button>
                              </div>
                            )}
                          </div>

                          {/* 当前选择的颜色预览 */}
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-gray-600">当前选择:</span>
                              <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-full border-2 border-gray-300" style={{ backgroundColor: selectedColor }} />
                                <span className="text-xs font-mono text-gray-700">{selectedColor}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      onClick={handleCancel}
                      className="flex items-center space-x-1 bg-gray-600 text-white px-3 py-2 rounded-lg hover:bg-gray-700 transition-colors"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>取消</span>
                    </button>
                    <button
                      onClick={creatingNew ? handleCreateTag : handleUpdateTag}
                      className="flex items-center space-x-1 bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 transition-colors"
                      disabled={!newTagName.trim()}
                    >
                      <Save className="w-4 h-4" />
                      <span>{creatingNew ? '创建' : '保存'}</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 标签列表 */}
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800">可选标签 ({unselectedTags.length})</h3>
            </div>

            {tagsLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">加载标签中...</p>
              </div>
            ) : unselectedTags.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-gray-200 rounded-full mx-auto mb-4 flex items-center justify-center">
                  <span className="text-2xl text-gray-400">#</span>
                </div>
                <p className="text-gray-500">{searchTerm ? '没有找到匹配的标签' : '暂无可用标签'}</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {unselectedTags.map(tag => {
                  const styleInfo = getTagStyleInfo(tag)
                  console.log('[DFX:TagManagementModal] 未选标签样式渲染', {
                    tagId: tag.primary_id,
                    tagName: tag.tag_name,
                    isDarkBackground: !!styleInfo.style.textShadow,
                  })
                  return (
                    <div
                      key={tag.primary_id}
                      onClick={() => handleTagSelect(tag)}
                      className={`p-3 border rounded-lg hover:bg-gray-50 transition-colors cursor-pointer ${styleInfo.className}`}
                      style={styleInfo.style}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <span className="font-medium truncate">{tag.tag_name}</span>
                          {tag.usage_count > 0 && <span className="text-xs opacity-75">({tag.usage_count})</span>}
                        </div>
                        <div className="flex items-center space-x-1 flex-shrink-0">
                          <button
                            onClick={e => {
                              e.stopPropagation()
                              handleStartEdit(tag)
                            }}
                            className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                            title="编辑标签"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={e => {
                              e.stopPropagation()
                              handleDeleteTag(tag)
                            }}
                            className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                            title="删除标签"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* 底部操作 */}
          <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
            <div className="text-sm text-gray-600">
              已选择 {tempSelectedTags.length} / {maxTags} 个标签
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => {
                  setTempSelectedTags(selectedTags)
                  onClose()
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => {
                  // 立即调用onTagsChange，让父组件处理API调用和状态更新
                  onTagsChange(tempSelectedTags)
                  // 立即关闭模态框，提供即时反馈
                  onClose()
                }}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
              >
                <span>完成</span>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin-slow opacity-0 group-hover:opacity-100"></div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default TagManagementModal
