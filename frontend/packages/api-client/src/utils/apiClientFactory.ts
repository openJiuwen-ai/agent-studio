import { createApiClientInstance, TokenProvider, AuthStateUpdater, LanguageProvider } from '../client'
import { AxiosInstance } from 'axios'
import { getLoginPagePath } from '../../../../src/Common/LoginPage'
import { API_CONFIG } from '../config'

// 全局token提供者
let globalTokenProvider: TokenProvider | null = null
let globalAuthStateUpdater: AuthStateUpdater | null = null
let globalLanguageProvider: LanguageProvider | null = null
let globalApiClient: AxiosInstance | null = null
let isInitialized: boolean = false

// 设置全局token提供者
export const setGlobalTokenProvider = (
  tokenProvider: TokenProvider,
  authStateUpdater: AuthStateUpdater,
  languageProvider?: LanguageProvider
) => {
  try {
    const currentToken = tokenProvider()

    // 检查token是否真的变化了
    const previousToken = globalTokenProvider ? globalTokenProvider() : null
    const tokenChanged = previousToken !== currentToken
    const providerChanged = globalTokenProvider !== tokenProvider || globalAuthStateUpdater !== authStateUpdater

    // 更新全局引用
    globalTokenProvider = tokenProvider
    globalAuthStateUpdater = authStateUpdater
    if (languageProvider) {
      globalLanguageProvider = languageProvider
    }

    // 只有在必要时才重新创建API客户端
    if (tokenChanged || !globalApiClient || providerChanged) {
      globalApiClient = createApiClientInstance(globalTokenProvider, globalAuthStateUpdater, globalLanguageProvider || undefined)
      isInitialized = true
    }
  } catch (error) {
    console.error('Failed to set global token provider:', error)
    throw error
  }
}

// 获取带token的API客户端
export const getApiClient = (): AxiosInstance => {
  if (!globalApiClient) {
    if (!globalTokenProvider || !globalAuthStateUpdater) {
      const storedToken = localStorage.getItem('access_token')
      if (storedToken) {
        globalTokenProvider = () => localStorage.getItem('access_token') || ''
        globalAuthStateUpdater = {
          logout: () => {
            localStorage.removeItem('access_token')
            window.location.href = getLoginPagePath()
          },
          updateToken: (newToken: string) => {
            localStorage.setItem('access_token', newToken)
          },
        }
      } else {
        globalTokenProvider = () => ''
        globalAuthStateUpdater = {
          logout: () => {},
          updateToken: () => {},
        }
      }
    }
    globalApiClient = createApiClientInstance(globalTokenProvider, globalAuthStateUpdater, globalLanguageProvider || undefined)
    isInitialized = true
  }
  return globalApiClient
}

// 检查API客户端是否已初始化
export const isApiClientInitialized = (): boolean => {
  return isInitialized && !!globalApiClient && !!globalTokenProvider && !!globalAuthStateUpdater
}

// 等待API客户端初始化完成
export const waitForApiClientInitialization = (timeout: number = 3000): Promise<void> => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    const checkInitialization = () => {
      if (isApiClientInitialized()) {
        resolve()
      } else if (Date.now() - startTime > timeout) {
        reject(new Error('API client initialization timeout'))
      } else {
        setTimeout(checkInitialization, 50)
      }
    }

    checkInitialization()
  })
}

// 获取token
export const getToken = () => {
  if (!globalTokenProvider) {
    return null
  }
  return globalTokenProvider()
}

// 获取当前语言（带权重）
export const getAcceptLanguage = (): string => {
  if (!globalLanguageProvider) {
    return 'zh-CN;q=1.0, en-US;q=0.5'
  }
  const language = globalLanguageProvider()
  if (language === 'en-US') {
    return 'en-US;q=1.0, zh-CN;q=0.5'
  } else if (language === 'zh-CN') {
    return 'zh-CN;q=1.0, en-US;q=0.5'
  }
  return language
}

/** 流式请求选项 */
export interface StreamOptions<T = any> {
  onData?: (data: T) => void
  onError?: (error: string) => void
  onComplete?: () => void
  parseData?: (line: string) => T | null
  abortController?: AbortController
}

/**
 * 流式请求（Server-Sent Events 或自定义流式响应），内部自动带 Authorization，避免与 client 循环依赖
 */
export async function stream<T = any>(
  url: string,
  data?: any,
  options?: StreamOptions<T>,
): Promise<void> {
  const { onData, onError, onComplete, parseData, abortController } = options || {}

  try {
    const fullUrl = url.startsWith('http') ? url : `${API_CONFIG.BASE_URL}${url}`
    const token = getToken()

    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        ...API_CONFIG.HEADERS,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: data ? JSON.stringify(data) : undefined,
      signal: abortController?.signal,
    })

    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`
      try {
        const responseText = await response.text()
        if (responseText) {
          try {
            const errorData = JSON.parse(responseText)
            const detailedError = errorData.error || errorData.message || errorData.msg
            if (detailedError) {
              errorMessage = detailedError
            } else if (errorData.code) {
              errorMessage = `error ${errorData.code}: ${errorData.message || errorData.msg || errorMessage}`
            }
          } catch (e) {
            if (responseText.length < 500) {
              errorMessage = responseText
            }
          }
        }
      } catch (e) {
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
      if (abortController?.signal.aborted) {
        console.log('🛑 [stream] 流式请求被取消')
        reader.cancel()
        return
      }

      const { done, value } = await reader.read()

      if (done) {
        if (buffer.trim() || parseData) {
          try {
            let parsedData: T | null = null
            if (parseData) {
              parsedData = parseData(buffer)
            } else {
              const trimmedBuffer = buffer.trim()
              if (trimmedBuffer.startsWith('data: ')) {
                parsedData = JSON.parse(trimmedBuffer.substring(6)) as T
              } else {
                parsedData = JSON.parse(trimmedBuffer) as T
              }
            }
            if (parsedData && onData) onData(parsedData)
          } catch (e) {
            console.error('Failed to parse final buffer data:', buffer, e)
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
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmedLine = line.trim()
        if (trimmedLine || parseData) {
          try {
            let parsedData: T | null = null
            if (parseData) {
              parsedData = parseData(line)
            } else {
              if (trimmedLine.startsWith('data: ')) {
                parsedData = JSON.parse(trimmedLine.substring(6)) as T
              } else {
                parsedData = JSON.parse(trimmedLine) as T
              }
            }
            if (parsedData && onData) onData(parsedData)
          } catch (e) {
            console.error('Failed to parse stream data:', trimmedLine, e)
            if (onData && !trimmedLine.startsWith('data:') && !trimmedLine.startsWith('{')) {
              onData(trimmedLine as unknown as T)
            }
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.log('🛑 [stream] 流式请求被取消')
      return
    }
    console.error('Stream request error:', error)
    if (onError) {
      onError(error instanceof Error ? error.message : '流式请求失败')
    }
  }
}
