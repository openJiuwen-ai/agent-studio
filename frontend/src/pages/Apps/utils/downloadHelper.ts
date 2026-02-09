/**
 * 文件下载工具
 */

/**
 * 下载文本文件
 *
 * @param content - 文件内容
 * @param filename - 文件名
 * @param mimeType - MIME 类型，默认为 text/markdown
 */
export function downloadTextFile(
  content: string,
  filename: string,
  mimeType: string = 'text/markdown'
): void {
  try {
    // 创建 Blob 对象
    const blob = new Blob([content], { type: mimeType })

    // 创建临时 URL
    const url = URL.createObjectURL(blob)

    // 创建下载链接
    const link = document.createElement('a')
    link.href = url
    link.download = filename

    // 触发下载
    document.body.appendChild(link)
    link.click()

    // 清理资源
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('[downloadHelper] 下载文件失败:', error)
    throw new Error('下载文件失败')
  }
}

/**
 * 从 Base64 字符串下载文件
 *
 * @param base64Content - Base64 编码的文件内容
 * @param filename - 文件名
 * @param mimeType - MIME 类型（默认 application/octet-stream）
 */
export function downloadBase64File(
  base64Content: string,
  filename: string,
  mimeType: string = 'application/octet-stream'
): void {
  try {
    // 解码 Base64
    const binaryString = atob(base64Content)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }

    // 创建 Blob 对象
    const blob = new Blob([bytes], { type: mimeType })

    // 创建临时 URL
    const url = URL.createObjectURL(blob)

    // 创建下载链接
    const link = document.createElement('a')
    link.href = url
    link.download = filename

    // 触发下载
    document.body.appendChild(link)
    link.click()

    // 清理资源
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('[downloadHelper] 下载 Base64 文件失败:', error)
    throw new Error('下载文件失败')
  }
}

/**
 * 将字符串编码为 Base64（支持 UTF-8）
 *
 * 使用 encodeURIComponent 处理 UTF-8 字符，确保中文等字符正确编码
 *
 * @param content - 要编码的字符串
 * @returns Base64 编码的字符串
 */
export function encodeToBase64(content: string): string {
  try {
    // 使用 encodeURIComponent 处理 UTF-8 字符
    return btoa(encodeURIComponent(content).replace(/%([0-9A-F]{2})/g, (_match, p1) => {
      return String.fromCharCode(Number('0x' + p1))
    }))
  } catch (error) {
    console.error('[downloadHelper] Base64 编码失败:', error)
    throw new Error('Base64 编码失败')
  }
}

/**
 * 异步编码大文件为 Base64（使用分块处理）
 *
 * 将内容分块编码，避免大文件阻塞主线程
 * 每处理一块后会让出主线程，保持 UI 响应性
 *
 * @param content - 要编码的字符串
 * @param chunkSize - 每块大小（字符数），默认 1MB
 * @returns Promise<Base64 编码的字符串>
 *
 * @example
 * ```ts
 * // 对大文件使用异步编码
 * const largeContent = '...' // 大文件内容
 * const base64 = await encodeToBase64Async(largeContent)
 * ```
 */
export async function encodeToBase64Async(content: string, chunkSize = 1024 * 1024): Promise<string> {
  return new Promise((resolve, reject) => {
    try {
      // 先进行 UTF-8 编码预处理
      const utf8Encoded = encodeURIComponent(content)

      // 计算总长度
      const totalLength = utf8Encoded.length
      let result = ''
      let offset = 0

      const encodeChunk = () => {
        // 计算当前块的结束位置
        const end = Math.min(offset + chunkSize, totalLength)
        const chunk = utf8Encoded.slice(offset, end)

        // 编码当前块
        const encodedChunk = chunk.replace(/%([0-9A-F]{2})/g, (_match, p1) => {
          return String.fromCharCode(Number('0x' + p1))
        })

        result += btoa(encodedChunk)
        offset = end

        // 如果还有剩余内容，继续处理
        if (offset < totalLength) {
          // 让出主线程，避免阻塞
          setTimeout(encodeChunk, 0)
        } else {
          // 完成
          resolve(result)
        }
      }

      // 开始编码
      encodeChunk()
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * 生成带时间戳的文件名
 *
 * @param baseName - 基础文件名
 * @param extension - 文件扩展名（默认 .md）
 * @returns 带时间戳的文件名（如：报告_2025-01-06_1930.md）
 */
export function generateTimestampedFilename(
  baseName: string,
  extension: string = '.md'
): string {
  const date = new Date()
  const dateStr = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`
  const timeStr = `${date.getHours().toString().padStart(2, '0')}${date.getMinutes().toString().padStart(2, '0')}`

  return `${baseName}_${dateStr}_${timeStr}${extension}`
}