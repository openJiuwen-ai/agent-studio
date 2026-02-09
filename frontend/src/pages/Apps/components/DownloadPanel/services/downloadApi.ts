/**
 * Download API 服务层
 * 封装所有报告下载相关的 API 调用
 */

import axios from 'axios'
import { encodeToBase64 } from '@/pages/Apps/utils/downloadHelper'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { getAuthToken } from '@/utils/authUtils'
import { showNotification } from '@/utils/notifications'

/** API 错误类型 */
export interface ApiError {
  response?: { status: number }
  code?: string
  message?: string
}

/** 报告转换响应 */
interface ConvertReportResponse {
  code: number
  convert_content?: string
  msg?: string
}

/**
 * Download API 服务类
 */
export class DownloadApiService {
  /**
   * 转换报告格式
   * @param markdownContent - Markdown 格式的报告内容
   * @param format - 目标格式 ('html' | 'docx')
   * @param t - 翻译函数
   * @returns 转换后的内容（Base64 编码），失败返回 null
   */
  static async convertFormat(
    markdownContent: string,
    format: 'html' | 'docx',
    t: (key: string, params?: Record<string, unknown>) => string
  ): Promise<string | null> {
    try {
      // 获取 spaceId
      const spaceId = getDefaultSpaceId()
      if (!spaceId) {
        console.error('[DownloadApi] 无法获取 spaceId')
        showNotification(t('apps.errors.unableToGetSpaceId'), 'error')
        return null
      }

      // 获取认证 token
      const token = getAuthToken()
      if (!token) {
        console.error('[DownloadApi] 无法获取认证 token')
        showNotification(t('apps.errors.unableToGetAuthToken'), 'error')
        return null
      }

      // 将 markdown 内容编码为 base64
      const base64Markdown = encodeToBase64(markdownContent)

      // 调用后端 API
      const response = await axios.post<ConvertReportResponse>(
        '/api/v1/agent/deepsearch/reports/convert',
        {
          space_id: spaceId,
          report_content: base64Markdown,
          convert_type: format,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      // 处理响应
      if (response.data?.code === 200 && response.data?.convert_content) {
        return response.data.convert_content
      } else {
        console.error('[DownloadApi] 转换失败:', response.data)
        const errorMsg = response.data?.msg || t('apps.errors.unknownError')
        showNotification(`${t('apps.errors.reportConvertFailed')}: ${errorMsg}`, 'error')
        return null
      }
    } catch (error: unknown) {
      const err = error as ApiError
      console.error('[DownloadApi] 转换请求失败:', error)

      // 细化错误处理
      if (err.response?.status === 401) {
        showNotification(t('apps.auth.sessionExpired'), 'error')
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        showNotification(t('apps.errors.requestTimeout'), 'warning')
      } else if (err.message?.includes('Network') || err.code === 'ERR_NETWORK') {
        showNotification(t('apps.errors.networkError'), 'error')
      } else {
        showNotification(t('apps.errors.reportRequestFailed'), 'error')
      }
      return null
    }
  }
}

/** 单例实例 */
export const downloadApiService = new DownloadApiService()
