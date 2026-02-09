/**
 * Blob URL 管理器
 * 用于处理推理图谱的 Base64 编码内容与 Blob URL 之间的转换和生命周期管理
 */

/**
 * 将 Base64 编码的 HTML 内容转换为 Blob URL
 */
function base64ToBlobUrl(base64Content: string): string {
  // 解码 Base64
  const binaryString = atob(base64Content)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }

  // 解码为 HTML 内容
  const decoder = new TextDecoder()
  const htmlContent = decoder.decode(bytes)

  // 创建 Blob
  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' })

  // 创建并返回 Blob URL
  return URL.createObjectURL(blob)
}

/**
 * 释放 Blob URL 内存
 */
function revokeBlobUrl(blobUrl: string): void {
  URL.revokeObjectURL(blobUrl)
}

/**
 * Blob URL 管理器
 * 提供 Blob URL 生命周期管理功能
 */
export class BlobUrlManager {
  private currentUrl: string | null = null

  /**
   * 设置新的 Blob URL，自动清理旧的 URL
   */
  set(base64Content: string): string {
    this.clear()
    this.currentUrl = base64ToBlobUrl(base64Content)
    return this.currentUrl
  }

  /**
   * 获取当前 Blob URL
   */
  get(): string | null {
    return this.currentUrl
  }

  /**
   * 清理当前 Blob URL
   */
  clear(): void {
    if (this.currentUrl) {
      revokeBlobUrl(this.currentUrl)
      this.currentUrl = null
    }
  }

  /**
   * 销毁管理器，清理资源
   */
  destroy(): void {
    this.clear()
  }
}