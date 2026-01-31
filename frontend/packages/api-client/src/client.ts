import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { API_CONFIG, HTTP_STATUS, ERROR_TYPES, API_ENDPOINTS } from './config'
import { ErrorResponse, GenericApiResponse } from './types'
import { getLoginPagePath } from '../../../src/Common/LoginPage'

// API错误类
export class ApiError extends Error {
  constructor(
    public message: string,
    public code?: number,
    public response?: any,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// 认证 token 获取函数类型
export type TokenProvider = () => string | null

// 认证状态更新函数类型
export type AuthStateUpdater = {
  logout: () => void
  updateToken?: (token: string) => void
  getRefreshToken?: () => string | null
}

// 刷新token的函数
const renewToken = async (authStateUpdater: AuthStateUpdater): Promise<string | null> => {
  try {
    // 获取refresh token
    const refreshToken = authStateUpdater.getRefreshToken?.()
    if (!refreshToken) {
      console.warn('⚠️ No refresh token available - logging out')

      // 自动登出并跳转到登录页
      console.log('🚪 [Token Renewal] Logging out due to missing refresh token')
      authStateUpdater.logout()

      // 强制跳转到登录页
      if (typeof window !== 'undefined') {
        console.log('🔄 [Token Renewal] Redirecting to login page...')
        window.location.href = getLoginPagePath()
      }

      return null
    }

    // 创建不带认证的临时客户端用于刷新token
    const refreshClient = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    })

    // 发送刷新token请求
    const response = await refreshClient.post(API_ENDPOINTS.AUTH.REFRESH, {
      refreshToken,
    })

    console.debug('✅ Token refresh response:', response.status)

    if (response.data && response.data.success !== false && response.data.data) {
      const newToken = response.data.data.token || response.data.data.access_token
      if (newToken) {
        return newToken
      }
    }

    console.warn('⚠️ Invalid refresh token response format')
    return null
  } catch (error) {
    console.error('❌ Token refresh request failed:', error)
    throw error
  }
}

// 语言获取函数类型
export type LanguageProvider = () => string | null

// 创建axios实例
const createApiClient = (
  tokenProvider?: TokenProvider,
  authStateUpdater?: AuthStateUpdater,
  languageProvider?: LanguageProvider
): AxiosInstance => {
  const client = axios.create({
    baseURL: API_CONFIG.BASE_URL,
    timeout: API_CONFIG.TIMEOUT,
    headers: API_CONFIG.HEADERS,
  })

  // 请求拦截器
  client.interceptors.request.use(
    config => {
      // 添加认证token
      if (tokenProvider) {
        const token = tokenProvider()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        } else {
          console.debug('⚠️ Request Interceptor: No token available')
        }
      } else {
        console.log('⚠️ Request Interceptor: No token provider available')
      }

      // 添加Accept-Language header
      if (languageProvider) {
        const language = languageProvider()
        if (language) {
          config.headers['Accept-Language'] = language
        }
      }

      // 添加请求ID用于追踪
      config.headers['X-Request-ID'] = generateRequestId()

      // 开发环境日志
      if (API_CONFIG.IS_DEV) {
        console.debug('🚀 API Request:', {
          method: config.method?.toUpperCase(),
          url: config.url,
          data: config.data,
          headers: config.headers,
        })
      }

      return config
    },
    error => {
      console.error('❌ Request Interceptor Error:', error)
      return Promise.reject(error)
    },
  )

  // 响应拦截器
  client.interceptors.response.use(
    (response: AxiosResponse<GenericApiResponse>) => {
      // 开发环境日志
      if (API_CONFIG.IS_DEV) {
        console.debug('✅ API Response:', {
          status: response.status,
          url: response.config.url,
          data: response.data,
        })
      }

      // 检查业务层面的成功状态
      // 如果响应有success字段，检查它；如果没有，检查HTTP状态码和code字段
      const responseData = response.data
      if (responseData) {
        // 如果有success字段且为false，则拒绝
        if (Object.prototype.hasOwnProperty.call(responseData, 'success') && responseData.success === false) {
          const error = new ApiError(
            responseData.message || responseData.msg || 'API请求失败',
            typeof responseData.code === 'number' ? responseData.code : Number(responseData.code) || undefined,
            responseData,
          )
          return Promise.reject(error)
        }

        // 如果有code字段且不是200或0，则拒绝
        if (
          Object.prototype.hasOwnProperty.call(responseData, 'code') &&
          responseData.code !== 200 &&
          responseData.code !== '200' &&
          responseData.code !== 0 &&
          responseData.code !== '0'
        ) {
          const error = new ApiError(
            responseData.message || responseData.msg || 'API请求失败',
            typeof responseData.code === 'number' ? responseData.code : Number(responseData.code) || undefined,
            responseData,
          )
          return Promise.reject(error)
        }
      }

      return response
    },
    async (error: AxiosError<ErrorResponse>) => {
      // 开发环境日志
      if (API_CONFIG.IS_DEV) {
        console.error('❌ API Response Error:', {
          status: error.response?.status,
          url: error.config?.url,
          data: error.response?.data,
          message: error.message,
        })
      }

      // 检查是否是登录相关的请求
      const isLoginRequest = error.config?.url?.includes('/auth/login')

      // 处理401未授权错误
      if (error.response?.status === HTTP_STATUS.UNAUTHORIZED) {
        // 如果是登录请求失败，直接拒绝，不要尝试刷新token
        if (isLoginRequest) {
          console.log('🔐 Login failed - Authentication rejected (401)')
          return Promise.reject(createApiError(error, ERROR_TYPES.AUTH))
        }

        // 其他401错误才尝试刷新token
        if (authStateUpdater) {
          try {
            // 尝试刷新token
            const newToken = await renewToken(authStateUpdater)
            if (newToken) {
              // 更新token
              authStateUpdater.updateToken?.(newToken)
              // 重试原请求
              if (error.config) {
                error.config.headers.Authorization = `Bearer ${newToken}`
                return client.request(error.config)
              }
            }
          } catch (refreshError) {
            console.error('❌ Token refresh failed:', refreshError)
            // 刷新失败，清除认证状态并跳转到登录页
            authStateUpdater.logout()
            // 强制跳转到登录页
            if (typeof window !== 'undefined') {
              window.location.href = getLoginPagePath()
            }
            return Promise.reject(createApiError(error, ERROR_TYPES.AUTH))
          }
        } else {
          // 没有authStateUpdater时，直接跳转到登录页
          if (typeof window !== 'undefined') {
            window.location.href = getLoginPagePath()
          }
        }
      }

      // 处理其他HTTP错误
      const apiErr = createApiError(error, ERROR_TYPES.UNKNOWN) as ApiError & { response?: { data?: any; status?: number } }
      const dataOnly = apiErr?.response?.data as any

      // 安全地提取错误消息，确保始终是字符串
      let msg: string = apiErr.message || '请求错误'
      if (dataOnly) {
        if (typeof dataOnly.message === 'string') {
          msg = dataOnly.message
        } else if (typeof dataOnly.msg === 'string') {
          msg = dataOnly.msg
        } else if (dataOnly.detail) {
          // 处理 detail 可能是数组或对象的情况
          if (Array.isArray(dataOnly.detail)) {
            // 如果是数组，提取第一个错误消息或转换为字符串
            const firstError = dataOnly.detail[0]
            if (firstError && typeof firstError === 'object') {
              msg = firstError.msg || firstError.message || '数据验证失败'
            } else if (typeof firstError === 'string') {
              msg = firstError
            } else {
              msg = '数据验证失败'
            }
          } else if (typeof dataOnly.detail === 'string') {
            msg = dataOnly.detail
          } else if (typeof dataOnly.detail === 'object') {
            msg = (dataOnly.detail as any).msg || (dataOnly.detail as any).message || '数据验证失败'
          }
        }
      }

      try {
        // 现在404的接口没有处理为空数组，这里过滤掉404错误
        if (typeof window !== 'undefined' && apiErr?.response?.status !== HTTP_STATUS.NOT_FOUND) {
          window.dispatchEvent(
            new CustomEvent('global-snackbar', {
              detail: { status: apiErr?.response?.status, message: msg, severity: 'error', duration: 3000 },
            }),
          )
        }
      } catch {
        // 忽略全局通知错误
      }
      return Promise.reject(apiErr)
    },
  )

  return client
}

// 创建API错误
const createApiError = (error: AxiosError<ErrorResponse>, type: string): Error => {
  const apiError = new Error()

  if (error.response) {
    // 服务器响应了错误状态码
    const { status, data } = error.response

    apiError.name = 'ApiError'

    // 优先使用后端返回的详细错误信息
    let detailedMessage = ''
    const dataWithDetail = data as any

    // 检查是否有详细的错误信息
    if (dataWithDetail?.detail) {
      if (Array.isArray(dataWithDetail.detail)) {
        // 如果是数组，提取所有错误信息
        const errorMessages = dataWithDetail.detail.map((err: any) => {
          if (typeof err === 'object' && err !== null) {
            return err.msg || err.message || '数据验证失败'
          }
          return String(err)
        })
        detailedMessage = errorMessages.join(', ')
      } else if (typeof dataWithDetail.detail === 'string') {
        detailedMessage = dataWithDetail.detail
      } else if (typeof dataWithDetail.detail === 'object') {
        detailedMessage = dataWithDetail.detail.msg || dataWithDetail.detail.message || '数据验证失败'
      }
    } else if (data?.message) {
      detailedMessage = data.message
    } else if (data?.msg) {
      detailedMessage = data.msg
    }

    // 构建最终的错误消息
    if (detailedMessage) {
      apiError.message = detailedMessage
    } else {
      apiError.message = `HTTP ${status}: ${getHttpStatusText(status)}`
    }

    // 添加额外信息
    ;(apiError as any).status = status
    ;(apiError as any).code = data?.code
    ;(apiError as any).type = type
    ;(apiError as any).details = data?.details
    ;(apiError as any).validationErrors = data?.validationErrors
    // 保留完整的 Axios 响应对象，便于业务层访问 headers、config、data 等原始信息
    ;(apiError as any).response = error.response
  } else if (error.request) {
    // 请求已发出但没有收到响应
    apiError.name = 'NetworkError'
    apiError.message = '网络请求失败，请检查网络连接'
    ;(apiError as any).type = ERROR_TYPES.NETWORK
  } else {
    // 请求配置出错
    apiError.name = 'RequestError'
    apiError.message = error.message || '请求配置错误'
    ;(apiError as any).type = ERROR_TYPES.UNKNOWN
  }

  return apiError
}

// 获取HTTP状态码文本
const getHttpStatusText = (status: number): string => {
  const statusTexts: Record<number, string> = {
    [HTTP_STATUS.BAD_REQUEST]: '请求参数错误',
    [HTTP_STATUS.UNAUTHORIZED]: '未授权访问',
    [HTTP_STATUS.FORBIDDEN]: '禁止访问',
    [HTTP_STATUS.NOT_FOUND]: '资源不存在',
    [HTTP_STATUS.CONFLICT]: '资源冲突',
    [HTTP_STATUS.UNPROCESSABLE_ENTITY]: '请求数据验证失败',
    [HTTP_STATUS.INTERNAL_SERVER_ERROR]: '服务器内部错误',
    [HTTP_STATUS.BAD_GATEWAY]: '网关错误',
    [HTTP_STATUS.SERVICE_UNAVAILABLE]: '服务不可用',
  }
  return statusTexts[status] || '未知错误'
}

// 生成请求ID
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// Token renewal timer reference
let tokenRenewalTimer: NodeJS.Timeout | null = null

// 启动定时token刷新
export const startTokenRenewal = (authStateUpdater: AuthStateUpdater, intervalMs: number = 60000) => {
  console.log(`🔄 Starting automatic token renewal timer (interval: ${intervalMs}ms)`)
  // 清除现有定时器
  if (tokenRenewalTimer) {
    clearInterval(tokenRenewalTimer)
    tokenRenewalTimer = null
  }

  // 立即执行一次
  performTokenRenewal(authStateUpdater)

  // 设置定时器
  tokenRenewalTimer = setInterval(() => {
    performTokenRenewal(authStateUpdater)
  }, intervalMs)
}

// 停止定时token刷新
export const stopTokenRenewal = () => {
  if (tokenRenewalTimer) {
    console.log('⏹️ Stopping automatic token renewal timer')
    clearInterval(tokenRenewalTimer)
    tokenRenewalTimer = null
  }
}

// 执行token刷新
const performTokenRenewal = async (authStateUpdater: AuthStateUpdater) => {
  try {
    console.log('🔄 [Token Renewal] Starting automatic token refresh...')

    const newToken = await renewToken(authStateUpdater)

    if (newToken) {
      authStateUpdater.updateToken?.(newToken)
    } else {
      console.warn('⚠️ [Token Renewal] Token refresh failed - no new token returned')

      // 自动登出并跳转到登录页
      console.log('🚪 [Token Renewal] Logging out due to token refresh failure')
      authStateUpdater.logout()

      // 强制跳转到登录页
      if (typeof window !== 'undefined') {
        console.log('🔄 [Token Renewal] Redirecting to login page...')
        window.location.href = getLoginPagePath()
      }
    }
  } catch (error) {
    console.error('❌ [Token Renewal] Automatic token refresh failed:', error)

    // 自动登出并跳转到登录页
    console.log('🚪 [Token Renewal] Logging out due to token refresh failure')
    authStateUpdater.logout()

    // 强制跳转到登录页
    if (typeof window !== 'undefined') {
      console.log('🔄 [Token Renewal] Redirecting to login page...')
      window.location.href = getLoginPagePath()
    }
  }
}

// 创建API客户端实例的工厂函数
export const createApiClientInstance = (
  tokenProvider?: TokenProvider,
  authStateUpdater?: AuthStateUpdater,
  languageProvider?: LanguageProvider
) => {
  return createApiClient(tokenProvider, authStateUpdater, languageProvider)
}

// 默认的API客户端实例（不包含认证）
export const apiClient = createApiClient()

// 导出axios类型，方便使用
export type { AxiosRequestConfig, AxiosResponse, AxiosError }

// 通用请求方法
export const apiRequest = {
  // GET请求
  get: <T = any>(url: string, config?: AxiosRequestConfig) => apiClient.get<T>(url, config).then(response => response.data),

  // POST请求
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => apiClient.post<T>(url, data, config).then(response => response.data),

  // PUT请求
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => apiClient.put<T>(url, data, config).then(response => response.data),

  // PATCH请求
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => apiClient.patch<T>(url, data, config).then(response => response.data),

  // DELETE请求
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => apiClient.delete<T>(url, config).then(response => response.data),

  // 文件上传
  upload: <T = any>(url: string, formData: FormData, config?: AxiosRequestConfig) =>
    apiClient
      .post<T>(url, formData, {
        ...config,
        headers: {
          ...config?.headers,
          'Content-Type': 'multipart/form-data',
        },
      })
      .then(response => response.data),

  // 文件下载
  download: (url: string, filename?: string, config?: AxiosRequestConfig) =>
    apiClient
      .get(url, {
        ...config,
        responseType: 'blob',
      })
      .then(response => {
        const blob = new Blob([response.data])
        const downloadUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = filename || 'download'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(downloadUrl)
        return response
      }),

  // 流式请求（Server-Sent Events 或自定义流式响应）
  stream: async <T = any>(
    url: string,
    data?: any,
    options?: {
      onData?: (data: T) => void
      onError?: (error: string) => void
      onComplete?: () => void
      parseData?: (line: string) => T | null
      abortController?: AbortController
    },
  ): Promise<void> => {
    const { onData, onError, onComplete, parseData, abortController } = options || {}

    try {
      // 构建完整 URL
      const fullUrl = url.startsWith('http') ? url : `${API_CONFIG.BASE_URL}${url}`

      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          ...API_CONFIG.HEADERS,
        },
        body: data ? JSON.stringify(data) : undefined,
        signal: abortController?.signal,
      })

      if (!response.ok) {
        // 尝试读取响应体中的错误信息
        let errorMessage = `HTTP error! status: ${response.status}`
        try {
          // 对于流式响应，尝试读取响应体
          const responseText = await response.text()
          if (responseText) {
            try {
              const errorData = JSON.parse(responseText)
              // 优先使用 error、message 或 msg 字段
              const detailedError = errorData.error || errorData.message || errorData.msg
              if (detailedError) {
                errorMessage = detailedError
              } else if (errorData.code) {
                errorMessage = `错误 ${errorData.code}: ${errorData.message || errorData.msg || errorMessage}`
              }
            } catch (e) {
              // 如果不是JSON，使用原始文本（如果不太长）
              if (responseText.length < 500) {
                errorMessage = responseText
              }
            }
          }
        } catch (e) {
          // 如果读取响应体失败，使用默认错误信息
          console.warn('无法读取错误响应体:', e)
        }
        throw new Error(errorMessage)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      let buffer = ''
      let isReading = true

      while (isReading) {
        // 检查是否被取消
        if (abortController?.signal.aborted) {
          console.log('🛑 [apiRequest.stream] 流式请求被取消')
          reader.cancel()
          return
        }

        const { done, value } = await reader.read()

        if (done) {
          // 处理剩余的 buffer 数据（最后一行）
          if (buffer.trim() || parseData) {
            try {
              let parsedData: T | null = null

              if (parseData) {
                // 使用自定义解析函数处理最后一行
                parsedData = parseData(buffer)
              } else {
                // 默认解析逻辑处理最后一行
                const trimmedBuffer = buffer.trim()
                if (trimmedBuffer.startsWith('data: ')) {
                  const jsonStr = trimmedBuffer.substring(6)
                  parsedData = JSON.parse(jsonStr) as T
                } else {
                  parsedData = JSON.parse(trimmedBuffer) as T
                }
              }

              if (parsedData && onData) {
                onData(parsedData)
              }
            } catch (e) {
              console.error('Failed to parse final buffer data:', buffer, e)
              // 如果不是JSON格式，可能是纯文本
              const trimmedBuffer = buffer.trim()
              if (onData && !trimmedBuffer.startsWith('data:') && !trimmedBuffer.startsWith('{')) {
                onData(trimmedBuffer as unknown as T)
              }
            }
          }

          if (onComplete) onComplete()
          isReading = false
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        // 保留最后一行（可能不完整）
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmedLine = line.trim()
          // 如果有自定义解析函数，传递原始行（包括空行）
          // 否则只处理非空行
          if (trimmedLine || parseData) {
            try {
              let parsedData: T | null = null

              if (parseData) {
                // 使用自定义解析函数，传递原始行
                parsedData = parseData(line)
              } else {
                // 默认解析逻辑
                if (trimmedLine.startsWith('data: ')) {
                  // 处理 Server-Sent Events 格式
                  const jsonStr = trimmedLine.substring(6)
                  parsedData = JSON.parse(jsonStr) as T
                } else {
                  // 尝试直接解析为JSON
                  parsedData = JSON.parse(trimmedLine) as T
                }
              }

              if (parsedData && onData) {
                onData(parsedData)
              }
            } catch (e) {
              console.error('Failed to parse stream data:', trimmedLine, e)
              // 如果不是JSON格式，可能是纯文本
              if (onData && !trimmedLine.startsWith('data:') && !trimmedLine.startsWith('{')) {
                onData(trimmedLine as unknown as T)
              }
            }
          }
        }
      }
    } catch (error) {
      // 检查是否是 AbortError（用户主动取消）
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('🛑 [apiRequest.stream] 流式请求被取消')
        return
      }

      console.error('Stream request error:', error)
      if (onError) {
        onError(error instanceof Error ? error.message : '流式请求失败')
      }
    }
  },
}

// 工具函数
export const apiUtils = {
  // 构建查询字符串
  buildQueryString: (params: Record<string, any>): string => {
    const searchParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(item => searchParams.append(key, String(item)))
        } else {
          searchParams.append(key, String(value))
        }
      }
    })

    return searchParams.toString()
  },

  // 构建URL参数
  buildUrl: (baseUrl: string, params?: Record<string, any>): string => {
    if (!params) return baseUrl

    const queryString = apiUtils.buildQueryString(params)
    return queryString ? `${baseUrl}?${queryString}` : baseUrl
  },

  // 替换URL中的参数占位符
  replaceUrlParams: (url: string, params: Record<string, string | number>): string => {
    let result = url

    Object.entries(params).forEach(([key, value]) => {
      result = result.replace(`:${key}`, String(value))
    })

    return result
  },

  // 延迟函数
  delay: (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms)),

  // 重试函数
  retry: async <T>(fn: () => Promise<T>, maxRetries: number = API_CONFIG.MAX_RETRIES, delay: number = API_CONFIG.RETRY_DELAY): Promise<T> => {
    try {
      return await fn()
    } catch (error) {
      if (maxRetries > 0) {
        await apiUtils.delay(delay)
        return apiUtils.retry(fn, maxRetries - 1, delay * 2)
      }
      throw error
    }
  },
}
