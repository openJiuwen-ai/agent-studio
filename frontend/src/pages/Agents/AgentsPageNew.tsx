import React, { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AgentSortBy } from '@test-agentstudio/api-client'
import { Plus, Upload } from 'lucide-react'
import DeleteConfirmationDialog from '../../components/Common/DeleteConfirmationDialog'
import UnifiedSnackbar, { useUnifiedSnackbar } from '../../Common/UnifiedSnackbar'
import { CircularProgress } from '@mui/material'
import { CommonPageLayout } from '../../components/Common/common-page'
import { useAgentActions } from './hooks/useAgentActions'
import { useAgentListData } from './hooks/useAgentListData'
import { ImportConflictDialog } from './components/ImportConflictDialog'
import { AgentGridView } from './components/AgentGridView'
import { AgentTableView } from './components/AgentTableView'
import { SearchInput } from '@/components/Common/common-page'

const AgentsPage: React.FC = () => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { snackbar, showSuccess, showError, showWarning, closeSnackbar } = useUnifiedSnackbar()

  // ==================== 数据获取 ====================
  const {
    modelsData,
    modelsLoading,
    availableModelNames,
    agents,
    total,
    isLoading,
    error,
    refetch,
    viewType,
    sortBy,
    sortOrder,
    pagerState,
    searchTerm,
    debouncedSearchTerm,
    setSearchTerm,
    setViewType,
    setSortBy,
    setSortOrder,
    setPagerState,
    handleFetchTableData,
  } = useAgentListData()

  // ==================== Agent 操作 ====================
  const {
    deleteDialog,
    closeDeleteDialog,
    isDeleting,
    handleDelete,
    confirmDelete,
    handleCopy,
    handleExport,
    handlePublish,
    isImporting,
    importConflict,
    fileInputRef,
    handleImportClick,
    handleFileChange,
    executeImport,
    closeImportConflict,
    editingState,
    savingAgentId,
    startEditing,
    cancelEditing,
    handleSaveEdit,
    updateValue,
  } = useAgentActions(
    refetch,
    {
      showSuccess,
      showError,
      showWarning,
    },
  )

  // ==================== 渲染函数 ====================
  // 网格视图组件
  const gridView = useMemo(
    () => (
      <AgentGridView
        agents={agents}
        searchTerm={debouncedSearchTerm}
        editingState={editingState}
        savingAgentId={savingAgentId}
        onEdit={startEditing}
        onUpdateValue={updateValue}
        onSaveEdit={handleSaveEdit}
        onCancelEdit={cancelEditing}
        onCopy={handleCopy}
        onDelete={handleDelete}
        onExport={handleExport}
        onPublish={handlePublish}
        availableModelNames={availableModelNames}
        modelsLoading={modelsLoading}
      />
    ),
    [
      agents,
      debouncedSearchTerm,
      editingState,
      savingAgentId,
      startEditing,
      updateValue,
      handleSaveEdit,
      cancelEditing,
      handleCopy,
      handleDelete,
      handleExport,
      handlePublish,
      availableModelNames,
      modelsLoading,
    ],
  )

  // 表格视图组件
  const tableView = useMemo(
    () => (
      <AgentTableView
        agents={agents}
        loading={isLoading}
        searchTerm={debouncedSearchTerm}
        availableModelNames={availableModelNames}
        modelsData={modelsData}
        modelsLoading={modelsLoading}
        onCopy={handleCopy}
        onExport={handleExport}
        onDelete={handleDelete}
        onPublish={handlePublish}
        onFetchData={handleFetchTableData}
        onSortChange={handleFetchTableData}
        defaultSort={{ field: sortBy, order: sortOrder || 'desc' }}
      />
    ),
    [
      agents,
      isLoading,
      debouncedSearchTerm,
      availableModelNames,
      modelsData,
      modelsLoading,
      handleCopy,
      handleExport,
      handleDelete,
      handlePublish,
      handleFetchTableData,
      sortBy,
      sortOrder,
    ],
  )

  // 工具栏左侧（搜索 + 排序）
  const toolbarLeft = useMemo(
    () => (
      <>
        <SearchInput
          searchTerm={searchTerm}
          placeholder={t('agents.agentList.searchPlaceholder')}
          onChange={setSearchTerm}
        />
        {/* 排序选择器 - 仅在网格视图显示 */}
        {viewType === 'grid' && (
          <>
            <select
              value={sortBy || AgentSortBy.update_time}
              onChange={e => setSortBy(e.target.value as any)}
              className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm focus:outline-none focus:border-[#3b82f6] focus:ring-1 focus:ring-[#3b82f6] transition-colors"
            >
              <option value={AgentSortBy.name}>{t('agents.agentList.sortByName')}</option>
              <option value={AgentSortBy.create_time}>{t('agents.agentList.sortByCreated')}</option>
              <option value={AgentSortBy.update_time}>{t('agents.agentList.sortByUpdated')}</option>
            </select>
            <button
              onClick={() => setSortOrder((sortOrder === 'asc' ? 'desc' : 'asc') as any)}
              className="h-8 w-8 bg-white border border-[#e5e7eb] text-[#6b7280] hover:text-[#374151] hover:bg-[#f9fafb] hover:border-[#d1d5db] rounded-[4px] transition-colors flex items-center justify-center"
            >
              {sortOrder === 'asc' ? <span className="text-sm">↑</span> : <span className="text-sm">↓</span>}
            </button>
          </>
        )}
      </>
    ),
    [searchTerm, setSearchTerm, viewType, sortBy, setSortBy, sortOrder, setSortOrder, t],
  )

  // 工具栏右侧（导入 + 新建）
  const toolbarRight = useMemo(
    () => (
      <>
        {/* 导入按钮 */}
        <button
          className="h-8 px-3 bg-white border border-[#e5e7eb] text-[#1f2937] rounded-[4px] text-sm font-medium hover:bg-[#f9fafb] hover:border-[#d1d5db] transition-colors flex items-center space-x-2"
          onClick={handleImportClick}
          disabled={isImporting}
        >
          {isImporting ? <CircularProgress size={16} /> : <Upload className="w-4 h-4" />}
          <span>{isImporting ? t('agents.importing') : t('agents.import')}</span>
        </button>
        {/* 新建按钮 */}
        <button
          className="btn-primary h-8 flex items-center gap-2 text-sm px-4"
          onClick={() => navigate('/dashboard/agents/new')}
        >
          <Plus className="w-4 h-4" />
          <span>{t('agents.createAgent')}</span>
        </button>
      </>
    ),
    [isImporting, handleImportClick, navigate, t],
  )

  return (
    <>
      <input type="file" ref={fileInputRef} className="hidden" accept=".json,.zip" onChange={handleFileChange} />

      <CommonPageLayout
        title={t('agents.projectDevelopment')}
        viewType={viewType}
        onViewTypeChange={setViewType}
        pager={{
          total,
          currentPage: pagerState.page,
          pageSize: pagerState.pageSize,
          pageSizeOptions: [20, 60, 100, 200],
        }}
        onPagerChange={(page, pageSize) => {
          setPagerState({ page, pageSize })
        }}
        loading={isLoading}
        error={error}
        gridView={gridView}
        tableView={tableView}
        toolbarLeft={toolbarLeft}
        toolbarRight={toolbarRight}
      />

      {/* 删除确认对话框 */}
      <DeleteConfirmationDialog
        isOpen={deleteDialog.isOpen}
        onClose={closeDeleteDialog}
        onConfirm={confirmDelete}
        itemType="agent"
        itemName={deleteDialog.agentName}
        isLoading={isDeleting}
      />

      {/* 导入冲突确认对话框 */}
      <ImportConflictDialog
        isOpen={importConflict?.isOpen || false}
        agentName={importConflict?.agentName || ''}
        isLoading={isImporting}
        onOverwrite={() => executeImport(importConflict!.data, true)}
        onCreateCopy={() => executeImport(importConflict!.data, false)}
        onCancel={closeImportConflict}
      />

      {/* Unified Snackbar */}
      <UnifiedSnackbar snackbar={snackbar} onClose={closeSnackbar} />
    </>
  )
}

export default AgentsPage
