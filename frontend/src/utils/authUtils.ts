/**
 * 认证相关工具函数
 */

interface AuthStorage {
  state?: {
    token?: string
    expiresAt?: number
  }
}

/**
 * 从 localStorage 的 auth-storage 中获取认证 token
 *
 * @returns 认证 token，如果不存在或解析失败则返回 null
 *
 * @example
 * ```ts
 * const token = getAuthToken()
 * if (!token) {
 *   // 处理未登录情况
 * }
 * ```
 */
export function getAuthToken(): string | null {
  try {
    const authStorage = localStorage.getItem('auth-storage')
    if (!authStorage) return null

    const authData = JSON.parse(authStorage) as AuthStorage
    return authData.state?.token || null
  } catch (e) {
    console.error('[authUtils] Failed to parse auth-storage:', e)
    return null
  }
}

/**
 * 检查 token 是否即将过期（如果有过期时间）
 *
 * 提前 5 分钟认为即将过期
 *
 * @returns token 是否即将过期或不存在
 */
export function isTokenExpiring(): boolean {
  try {
    const authStorage = localStorage.getItem('auth-storage')
    if (!authStorage) return true

    const authData = JSON.parse(authStorage) as AuthStorage
    const expiresAt = authData.state?.expiresAt

    if (!expiresAt) return false

    // 提前 5 分钟认为即将过期
    return Date.now() > expiresAt - 5 * 60 * 1000
  } catch (e) {
    console.error('[authUtils] Failed to check token expiry:', e)
    return true
  }
}

/**
 * 清除认证信息
 *
 * @example
 * ```ts
 * clearAuth()
 * ```
 */
export function clearAuth(): void {
  try {
    localStorage.removeItem('auth-storage')
  } catch (e) {
    console.warn('[authUtils] Failed to clear auth:', e)
  }
}

/**
 * 设置请求的 Authorization 头
 *
 * @param headers - 请求头对象
 * @param token - 认证 token（可选，如果不提供则自动获取）
 *
 * @example
 * ```ts
 * const headers: Record<string, string> = {}
 * setAuthHeader(headers)
 * // 或
 * setAuthHeader(headers, 'custom-token')
 * ```
 */
export function setAuthHeader(headers: Record<string, string>, token?: string): void {
  const authToken = token || getAuthToken()
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
}

/**
 * 创建带认证的请求配置
 *
 * @param additionalHeaders - 额外的请求头
 * @returns 包含 Authorization 的请求头对象
 *
 * @example
 * ```ts
 * const config = createAuthConfig({ 'Content-Type': 'application/json' })
 * axios.post('/api/endpoint', data, { headers: config })
 * ```
 */
export function createAuthConfig(additionalHeaders?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = additionalHeaders ? { ...additionalHeaders } : {}
  setAuthHeader(headers)
  return headers
}
