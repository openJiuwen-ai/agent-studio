import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import {
  Dialog,
  DialogTitle as MuiDialogTitle,
  DialogContent as MuiDialogContent,
  DialogActions as MuiDialogActions,
  Button,
  Typography,
  Card,
  CardContent,
  Chip,
  IconButton,
  CircularProgress,
  Box,
  Divider,
  Tooltip,
} from '@mui/material'
import { History, Calendar, User, FileText, CheckCircle, Clock, X, Info, Trash2, Check } from 'lucide-react'
import { usePluginPublishList, usePluginPublishDelete } from '@test-agentstudio/api-client'
import { PluginService } from '@test-agentstudio/api-client'
import type { PluginPublishInfo } from '@test-agentstudio/api-client'

interface PluginVersionHistoryProps {
  open: boolean
  onClose: () => void
  pluginId: string
  spaceId: string
  pluginName: string
}

const PluginVersionHistory: React.FC<PluginVersionHistoryProps> = ({ open, onClose, pluginId, spaceId, pluginName }) => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)

  // 删除相关状态
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [versionToDelete, setVersionToDelete] = useState<PluginPublishInfo | null>(null)

  // 选择相关状态 - 仅用于显示加载状态
  const [selectingVersion, setSelectingVersion] = useState<string | null>(null)

  // 删除插件发布版本的 hook
  const deletePluginPublish = usePluginPublishDelete()

  // 获取插件发布历史列表
  const {
    data: versionListData,
    isLoading,
    error,
    refetch,
  } = usePluginPublishList(
    {
      space_id: spaceId,
      plugin_id: pluginId,
    },
    {
      enabled: open && !!pluginId && !!spaceId,
    },
  )

  const versions = versionListData?.data?.plugin_infos || []
  const totalVersions = versionListData?.data?.plugin_infos?.length || 0

  // 重置页码当对话框打开时
  useEffect(() => {
    if (open) {
      setPage(1)
      refetch()
    }
  }, [open, refetch])

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch (error) {
      return dateString
    }
  }

  const getPluginTypeLabel = (type: number) => {
    return type === 1 ? (t('plugins.types.cloud') || '云侧插件') : (t('plugins.types.ide') || '本地插件')
  }

  const handleRetry = () => {
    refetch()
  }

  // 删除相关的处理函数
  const handleDeleteClick = (version: PluginPublishInfo) => {
    setVersionToDelete(version)
    setDeleteConfirmOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!versionToDelete || !spaceId || !pluginId) return

    try {
      const deleteRequest = {
        space_id: spaceId,
        plugin_id: pluginId,
        plugin_version: versionToDelete.plugin_version || '1.0.0',
      }

      await deletePluginPublish.mutateAsync(deleteRequest)

      // 删除成功后刷新列表
      refetch()
      setDeleteConfirmOpen(false)
      setVersionToDelete(null)
    } catch (error) {
      console.error('删除版本失败:', error)
    }
  }

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false)
    setVersionToDelete(null)
  }

  // 选择版本的处理函数 - 直接导航到版本页面并关闭对话框
  const handleSelectVersion = async (version: PluginPublishInfo) => {
    if (!spaceId || !pluginId) return

    const versionStr = version.plugin_version || '1.0.0'
    setSelectingVersion(versionStr)

    try {
      // 直接导航到插件版本页面，无需先获取版本信息
      // 因为PluginVersionPage会自己获取数据
      navigate(`/dashboard/plugins/${pluginId}/${versionStr}`)
      console.log(`导航到插件版本页面: /dashboard/plugins/${pluginId}/${versionStr}`)

      // 导航成功后立即关闭对话框
      setTimeout(() => {
        onClose()
      }, 100) // 添加短暂延迟确保导航开始
    } catch (error) {
      console.error('导航失败:', error)
    } finally {
      setSelectingVersion(null)
    }
  }

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: '12px',
            minHeight: '500px',
          },
        }}
      >
        {/* 标题栏 */}
        <MuiDialogTitle className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 flex-1 min-w-0">
              <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <History className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0 overflow-hidden">
                <Typography variant="h6" className="font-bold text-gray-900">
                  {t('plugins.versionHistory.title') || '插件版本历史'}
                </Typography>
                <Typography variant="body2" className="text-gray-600 truncate">
                  {pluginName}
                </Typography>
              </div>
            </div>
            <IconButton size="small" onClick={onClose} className="text-gray-600 hover:bg-gray-50">
              <X className="w-4 h-4" />
            </IconButton>
          </div>
        </MuiDialogTitle>

        {/* 内容区 */}
        <MuiDialogContent className="p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <CircularProgress size={40} className="mb-4" />
                <Typography variant="body2" color="text.secondary">
                  {t('plugins.versionHistory.loading') || '加载中...'}
                </Typography>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                  <Info className="w-8 h-8 text-red-500" />
                </div>
                <Typography variant="h6" className="mb-2 text-gray-900">
                  {t('plugins.loadFailed') || '加载失败'}
                </Typography>
                <Typography variant="body2" color="text.secondary" className="mb-4">
                  {t('plugins.versionHistory.loadError') || '无法加载插件版本历史，请稍后重试'}
                </Typography>
                <Button variant="outlined" onClick={handleRetry}>
                  {t('plugins.actions.retry') || '重试'}
                </Button>
              </div>
            </div>
          ) : versions.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                  <History className="w-8 h-8 text-gray-400" />
                </div>
                <Typography variant="h6" className="mb-2 text-gray-900">
                  {t('plugins.versionHistory.noVersions') || '暂无版本历史'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('plugins.versionHistory.noVersionsDescription') || '该插件还没有发布过任何版本'}
                </Typography>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 版本统计 */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <Chip icon={<Calendar className="w-3 h-3" />} label={t('plugins.versionHistory.versionCount', { count: totalVersions }) || `共 ${totalVersions} 个版本`} size="small" className="bg-blue-100 text-blue-700" />
                  <Chip label={getPluginTypeLabel(versions[0]?.plugin_type || 1)} size="small" className="bg-gray-100 text-gray-700" />
                </div>
              </div>

              {/* 版本列表 */}
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {versions.map((version: PluginPublishInfo, index: number) => {
                  return (
                    <Card
                      key={`${version.plugin_version || index}-${index}`}
                      className="border transition-colors duration-200 border-gray-200 hover:border-blue-300"
                      elevation={0}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3 flex-1 min-w-0">
                            <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                              <FileText className="w-4 h-4 text-blue-600" />
                            </div>
                            <div className="min-w-0 overflow-hidden">
                              <div className="flex items-center space-x-2">
                                <Typography variant="subtitle1" className="font-semibold text-gray-900">
                                  {version.plugin_version || '1.0.0'}
                                </Typography>
                                {version.published && (
                                  <Chip
                                    icon={<CheckCircle className="w-3 h-3" />}
                                    label={t('plugins.status.published') || '已发布'}
                                    size="small"
                                    className="bg-green-100 text-green-700 text-xs"
                                  />
                                )}
                              </div>
                              <Typography variant="body2" color="text.secondary" className="truncate">
                                {version.name}
                              </Typography>
                            </div>
                          </div>

                          <div className="flex items-center space-x-2">
                            {/* 选择按钮 */}
                            <Tooltip title={t('plugins.actions.viewDetails') || '查看版本详情'} arrow>
                              <IconButton
                                size="small"
                                onClick={() => handleSelectVersion(version)}
                                className="text-blue-500 hover:text-blue-700 hover:bg-blue-50"
                                disabled={selectingVersion === (version.plugin_version || '1.0.0')}
                              >
                                {selectingVersion === (version.plugin_version || '1.0.0') ? (
                                  <CircularProgress size={16} className="text-blue-500" />
                                ) : (
                                  <Check className="w-4 h-4" />
                                )}
                              </IconButton>
                            </Tooltip>

                            {/* 删除按钮 */}
                            <Tooltip title={t('plugins.actions.deleteVersion') || '删除版本'} arrow>
                              <IconButton
                                size="small"
                                onClick={() => handleDeleteClick(version)}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                disabled={deletePluginPublish.isLoading}
                              >
                                <Trash2 className="w-4 h-4" />
                              </IconButton>
                            </Tooltip>
                          </div>
                        </div>

                        {/* 版本描述 */}
                        {version.desc && (
                          <div className="mb-3">
                            <Typography variant="body2" className="text-gray-700 overflow-hidden break-words line-clamp-2" title={version.desc}>
                              {version.desc}
                            </Typography>
                          </div>
                        )}

                        {/* 版本详情 */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                          <div className="flex items-center space-x-2">
                            <User className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-600">{t('plugins.versionHistory.pluginType') || '插件类型'}:</span>
                            <span className="font-medium">{getPluginTypeLabel(version.plugin_type)}</span>
                          </div>

                          {version.url && (
                            <div className="flex items-center space-x-2">
                              <FileText className="w-4 h-4 text-gray-400" />
                              <span className="text-gray-600">URL:</span>
                              <Tooltip title={version.url} arrow>
                                <span className="font-medium truncate max-w-[150px]">{version.url}</span>
                              </Tooltip>
                            </div>
                          )}

                          <div className="flex items-center space-x-2">
                            <History className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-600">{t('plugins.versionHistory.toolCount') || '工具数量'}:</span>
                            <span className="font-medium">{version.tools?.length || 0}</span>
                          </div>

                          {version.icon_uri && (
                            <div className="flex items-center space-x-2">
                              <span className="text-gray-600">{t('plugins.versionHistory.icon') || '图标'}:</span>
                              <span className="text-lg">{version.icon_uri}</span>
                            </div>
                          )}
                        </div>

                        {version.version_desc && (
                          <>
                            <Divider className="my-3" />
                            <div>
                              <Typography variant="body2" className="text-gray-600 mb-1">
                                {t('plugins.versionHistory.description') || '版本说明'}:
                              </Typography>
                              <Typography variant="body2" className="text-gray-800 bg-gray-50 p-2 rounded whitespace-normal break-words">
                                {version.version_desc}
                              </Typography>
                            </div>
                          </>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}
        </MuiDialogContent>

        {/* 底部操作区 */}
        <MuiDialogActions className="bg-gray-50 px-6 py-4 border-t border-gray-200">
          <Button onClick={onClose} variant="outlined" className="text-gray-600 hover:text-gray-700 border-gray-300">
            {t('common.buttons.close') || '关闭'}
          </Button>
        </MuiDialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={handleDeleteCancel}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: '12px',
          },
        }}
      >
        <MuiDialogTitle className="bg-red-50 border-b border-red-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <Trash2 className="w-4 h-4 text-white" />
            </div>
            <div>
              <Typography variant="h6" className="font-bold text-gray-900">
                {t('plugins.versionHistory.confirmDeleteTitle') || '确认删除版本'}
              </Typography>
              <Typography variant="body2" className="text-gray-600">
                {t('plugins.versionHistory.irreversibleAction') || '此操作不可撤销'}
              </Typography>
            </div>
          </div>
        </MuiDialogTitle>

        <MuiDialogContent className="p-6">
          <div className="space-y-4">
            <Typography variant="body1" className="text-gray-800">
              {t('plugins.versionHistory.confirmDeleteTitle') || '确定要删除以下版本吗？'}
            </Typography>

            {versionToDelete && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <Typography variant="subtitle2" className="font-semibold text-gray-900">
                      {t('plugins.versionHistory.version') || '版本'}: {versionToDelete.plugin_version || '1.0.0'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {versionToDelete.name}
                    </Typography>
                    {versionToDelete.version_desc && (
                      <Typography variant="body2" className="text-gray-600 mt-1">
                        {t('plugins.versionHistory.versionDescription') || '说明'}: {versionToDelete.version_desc}
                      </Typography>
                    )}
                  </div>
                  {versionToDelete.published && (
                    <Chip icon={<CheckCircle className="w-3 h-3" />} label={t('plugins.basicInfo.published') || '已发布'} size="small" className="bg-green-100 text-green-700" />
                  )}
                </div>
              </div>
            )}

            <Typography variant="body2" className="text-red-600">
              ⚠️ {t('plugins.versionHistory.deleteIrreversibleAction') || '删除后，该版本的所有相关数据将被永久删除，无法恢复'}
            </Typography>
          </div>
        </MuiDialogContent>

        <MuiDialogActions className="bg-gray-50 px-6 py-4 border-t border-gray-200">
          <Button
            onClick={handleDeleteCancel}
            variant="outlined"
            className="text-gray-600 hover:text-gray-700 border-gray-300"
            disabled={deletePluginPublish.isLoading}
          >
            {t('common.buttons.cancel') || '取消'}
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            variant="contained"
            className="bg-red-500 hover:bg-red-600 text-white"
            disabled={deletePluginPublish.isLoading}
            startIcon={deletePluginPublish.isLoading ? <CircularProgress size={16} /> : <Trash2 className="w-4 h-4" />}
          >
            {deletePluginPublish.isLoading ? t('plugins.tools.deleteDialog.deleting') || '删除中...' : t('plugins.tools.deleteDialog.confirm') || '确认删除'}
          </Button>
        </MuiDialogActions>
      </Dialog>
    </>
  )
}

export default PluginVersionHistory
