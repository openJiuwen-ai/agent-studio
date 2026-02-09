import React from 'react'
import { AlertTriangle, Info, Trash2, Clock, HardDrive, X } from 'lucide-react'

/**
 * 对话限制和删除确认对话框
 * 用于：
 * 1. 对话数量达到上限时的警告
 * 2. 存储空间接近上限时的警告
 * 3. 删除对话前的确认（显示详细信息）
 */

export type DialogType = 'count-warning' | 'storage-warning' | 'delete-confirm'

export interface ConversationLimitDialogProps {
  open: boolean
  type: DialogType
  // 对话数量警告
  currentCount?: number
  maxCount?: number
  oldestConversation?: {
    id: string
    title: string
    createdAt: number
  }
  // 存储空间警告
  currentSize?: number
  maxSize?: number
  warningThreshold?: number // 警告阈值（字节）
  // 删除原因
  deleteReason?: string
  deleteDetails?: string
  // 回调
  onConfirm: () => void
  onCancel: () => void
}

const ConversationLimitDialog: React.FC<ConversationLimitDialogProps> = ({
  open,
  type,
  currentCount = 0,
  maxCount = 25,
  oldestConversation,
  currentSize = 0,
  maxSize = 500 * 1024 * 1024,
  warningThreshold = 1 * 1024 * 1024, // 默认 1MB
  deleteReason = '',
  deleteDetails = '',
  onConfirm,
  onCancel,
}) => {
  if (!open) return null

  // 格式化字节大小
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 格式化时间
  const formatTime = (timestamp: number): string => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // 根据类型渲染内容
  const renderContent = () => {
    switch (type) {
      case 'count-warning':
        return (
          <div className="space-y-4">
            {/* 警告图标 */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-orange-600" />
              </div>
            </div>

            {/* 标题 */}
            <h3 className="text-xl font-bold text-gray-900 text-center">
              对话数量已达上限
            </h3>

            {/* 警告信息 */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <p className="text-gray-700 text-center">
                当前已有 <span className="font-bold text-orange-600">{currentCount}</span> 个对话，
                已达最大数量限制 <span className="font-bold text-orange-600">{maxCount}</span> 个。
              </p>
            </div>

            {/* 最旧的对话信息 */}
            {oldestConversation && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">
                  再新建对话将删除最旧的对话：
                </p>
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {oldestConversation.title}
                    </p>
                    <p className="text-sm text-gray-500">
                      创建时间：{formatTime(oldestConversation.createdAt)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 确认提示 */}
            <p className="text-sm text-gray-600 text-center">
              是否继续新建对话？<br />
              <span className="text-red-600">最旧的对话将被永久删除</span>
            </p>
          </div>
        )

      case 'storage-warning': {
        // 计算剩余空间
        const remainingSize = maxSize - currentSize
        const remainingInMB = (remainingSize / (1024 * 1024)).toFixed(2)
        const warningThresholdInMB = (warningThreshold / (1024 * 1024)).toFixed(0)

        return (
          <div className="space-y-4">
            {/* 警告图标 */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                <HardDrive className="w-8 h-8 text-blue-600" />
              </div>
            </div>

            {/* 标题 */}
            <h3 className="text-xl font-bold text-gray-900 text-center">
              存储空间即将达到上限
            </h3>

            {/* 警告信息 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-gray-700 text-center">
                当前历史数据大小：<span className="font-bold text-blue-600">{formatBytes(currentSize)}</span>
              </p>
              <p className="text-sm text-gray-600 text-center mt-2">
                剩余空间约 <span className="font-bold text-blue-600">{remainingInMB} MB</span>
              </p>
            </div>

            {/* 提示信息 */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Info className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-gray-700">
                  当存储空间超过 <span className="font-bold text-yellow-600">{formatBytes(maxSize - warningThreshold)}</span> 时，
                  系统将自动删除最旧的对话以释放空间。
                </p>
              </div>
            </div>
          </div>
        )
      }

      case 'delete-confirm':
        return (
          <div className="space-y-4">
            {/* 删除图标 */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                <Trash2 className="w-8 h-8 text-red-600" />
              </div>
            </div>

            {/* 标题 */}
            <h3 className="text-xl font-bold text-gray-900 text-center">
              需要删除历史对话
            </h3>

            {/* 删除原因 */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">删除原因：</p>
              <p className="font-medium text-red-700">{deleteReason}</p>
            </div>

            {/* 详细信息 */}
            {deleteDetails && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-600 whitespace-pre-line">{deleteDetails}</p>
              </div>
            )}

            {/* 要删除的对话信息 */}
            {oldestConversation && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">将被删除的对话：</p>
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">
                      {oldestConversation.title}
                    </p>
                    <p className="text-sm text-gray-500">
                      创建时间：{formatTime(oldestConversation.createdAt)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 确认提示 */}
            <p className="text-sm text-red-600 text-center font-medium">
              ⚠️ 此操作将永久删除该对话，无法恢复
            </p>
          </div>
        )
    }
  }

  // 按钮文本
  const getButtonTexts = () => {
    switch (type) {
      case 'count-warning':
        return {
          cancel: '取消',
          confirm: '继续新建（删除旧对话）',
        }
      case 'storage-warning':
        return {
          cancel: '我知道了',
          confirm: '好的',
        }
      case 'delete-confirm':
        return {
          cancel: '取消（不保存）',
          confirm: '确认删除',
        }
      default:
        return {
          cancel: '取消',
          confirm: '确定',
        }
    }
  }

  const buttonTexts = getButtonTexts()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full mx-4 transform transition-all">
        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Content */}
        {renderContent()}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 mt-6">
          <button
            onClick={onCancel}
            className="flex-1 px-6 py-3 border-2 border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-all"
          >
            {buttonTexts.cancel}
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-6 py-3 rounded-xl font-medium transition-all ${
              type === 'delete-confirm'
                ? 'bg-red-600 text-white hover:bg-red-700'
                : type === 'storage-warning'
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-orange-600 text-white hover:bg-orange-700'
            }`}
          >
            {buttonTexts.confirm}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConversationLimitDialog
