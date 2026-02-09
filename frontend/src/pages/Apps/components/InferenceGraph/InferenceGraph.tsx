/**
 * InferenceGraph 组件
 *
 * @description
 * 完全独立的推理图管理组件
 * - 接收 inferMessages 数据
 * - 使用全局单例 InferenceGraphManager 管理状态
 * - 渲染 GraphModal
 */

import React, { useEffect } from 'react'
import { GraphModal } from './GraphModal'
import { useGraphModal } from './useGraphModal'
import { InferenceGraphManager } from './InferenceGraphManager'
import type { InferenceGraphProps } from './types'

/**
 * InferenceGraph 组件
 *
 * @description
 * - 使用全局单例注册数据和打开方法
 * - InferenceLink 通过单例访问并打开推理图
 * - 支持多实例，通过 instanceId 区分不同报告
 */
export const InferenceGraph: React.FC<InferenceGraphProps> = ({
  inferMessages = [],
  instanceId,
  className = '',
}) => {
  // 使用 useGraphModal 管理 modal 状态
  const graphModal = useGraphModal()

  /**
   * 挂载时注册到全局单例
   * 卸载时清理并关闭模态框
   */
  useEffect(() => {
    // 注册数据和打开方法，使用 instanceId 区分不同实例
    InferenceGraphManager.register(instanceId, inferMessages, graphModal.open)

    // 卸载时清理
    return () => {
      InferenceGraphManager.unregister(instanceId)
      // 关闭模态框，防止切换报告时模态框仍然显示
      graphModal.close()
    }
  }, [instanceId, inferMessages, graphModal.open, graphModal.close])

  return (
    <GraphModal
      show={graphModal.isOpen}
      blobUrl={graphModal.blobUrl}
      closeButtonRef={graphModal.closeButtonRef}
      onClose={graphModal.close}
      onOpenInNewTab={graphModal.openInNewTab}
      className={className}
    />
  )
}