/**
 * DeepSearch Template Service
 * 深度搜索模板服务
 */

import { getApiClient } from '../utils/apiClientFactory'

// ==================== 类型定义 ====================

/**
 * 报告模板
 */
export interface ReportTemplate {
  template_id: number
  template_name: string
  template_desc: string
  create_time: string
}

/**
 * 模板列表响应
 */
export interface TemplateListResponse {
  code: number
  msg: string
  data: ReportTemplate[]
}

/**
 * 模板导入请求
 */
export interface TemplateImportRequest {
  space_id: string
  file_name: string
  file_stream: string // Base64 编码的文件内容
  is_template: boolean
  template_name: string
  template_desc: string
  model_config_id: number
}

/**
 * 模板导入响应
 */
export interface TemplateImportResponse {
  code: number
  msg: string
  template_id?: number
}

/**
 * 模板删除响应
 */
export interface TemplateDeleteResponse {
  code: number
  msg: string
}

/**
 * 模板内容响应
 */
export interface TemplateContentResponse {
  code: number
  msg: string
  template_content: string
}

/**
 * 心跳检测响应类型
 */
export interface HeartbeatResponse {
  status: 'available' | 'unavailable'
  message: string
}

// ==================== 工具函数 ====================

/**
 * 将文件转换为 Base64 编码
 * @param file - 要转换的文件
 * @returns Promise<Base64字符串>
 */
export const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // 移除 data URL 前缀，只保留 Base64 编码部分
      const base64 = result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }
    reader.readAsDataURL(file)
  })
}

// ==================== 模板服务 ====================

/**
 * DeepSearch 模板服务
 */
export const deepsearchTemplateService = {
  /**
   * 获取模板列表
   * @param spaceId - 用户空间ID
   * @returns 模板列表
   */
  async listTemplates(spaceId: string): Promise<ReportTemplate[]> {
    const client = getApiClient()
    const response = await client.get<TemplateListResponse>(
      `/agent/deepsearch/template/${spaceId}`
    )
    return response.data.data
  },

  /**
   * 导入/上传模板
   * @param spaceId - 用户空间ID
   * @param file - 模板文件
   * @param templateName - 模板名称
   * @param templateDesc - 模板描述
   * @param modelConfigId - 模型配置ID
   * @param isTemplate - 是否为模板（true）或示例报告（false）
   * @returns 新创建的模板ID
   */
  async importTemplate(
    spaceId: string,
    file: File,
    templateName: string,
    templateDesc: string,
    modelConfigId: number,
    isTemplate: boolean = true
  ): Promise<number> {
    const client = getApiClient()

    // 将文件转换为 Base64
    const fileStream = await fileToBase64(file)

    const request: TemplateImportRequest = {
      space_id: spaceId,
      file_name: file.name,
      file_stream: fileStream,
      is_template: isTemplate,
      template_name: templateName,
      template_desc: templateDesc,
      model_config_id: modelConfigId
    }

    const response = await client.post<TemplateImportResponse>(
      '/agent/deepsearch/template',
      request
    )

    if (response.data.template_id === undefined) {
      throw new Error(response.data.msg || '上传模板失败')
    }

    return response.data.template_id
  },

  /**
   * 删除模板
   * @param spaceId - 用户空间ID
   * @param templateId - 模板ID
   */
  async deleteTemplate(spaceId: string, templateId: number): Promise<void> {
    const client = getApiClient()
    await client.delete<TemplateDeleteResponse>(
      `/agent/deepsearch/template/${spaceId}/${templateId}`
    )
  },

  /**
   * 获取模板内容
   * @param spaceId - 用户空间ID
   * @param templateId - 模板ID
   * @returns Base64 编码的模板内容
   */
  async getTemplateContent(
    spaceId: string,
    templateId: number
  ): Promise<string> {
    const client = getApiClient()
    const response = await client.get<TemplateContentResponse>(
      `/agent/deepsearch/template/${spaceId}/${templateId}`
    )
    return response.data.template_content
  }
}

/**
 * DeepSearch 心跳检测服务
 */
export const deepsearchHeartbeatService = {
  /**
   * 检查 DeepSearch 服务是否可用
   * 通过 Agent Studio 后端接口查询 DeepSearch 服务状态
   * @returns 心跳检测结果
   */
  async checkHeartbeat(): Promise<HeartbeatResponse> {
    const client = getApiClient()
    const response = await client.get<{status: string, message: string}>(
      '/agent/deepsearch/heartbeat'
    )
    return response.data
  }
}
