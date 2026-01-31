import { getApiClient } from '../utils/apiClientFactory'
import { createApiClientInstance, TokenProvider } from '../client'
import { API_ENDPOINTS } from '../config'
import {
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  ChangePasswordRequest,
  User,
  UserInfo,
  UserInfoWithTag,
  ApiResponse,
  ResetPasswordRequest,
} from '../types'

// 认证服务
export class AuthService {
  // 用户登录（不需要密码，如果用户名不存在会自动注册）
  static async login(credentials: LoginRequest): Promise<LoginResponse> {
    const apiClient = getApiClient()
    // 将对象转换为URL编码的字符串
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    // password字段仍然需要传递（OAuth2PasswordRequestForm要求），但后端不再验证
    formData.append('password', credentials.password || '')
    formData.append('grant_type', credentials.grant_type || 'password')

    // 设置请求配置，指定Content-Type为application/x-www-form-urlencoded
    // 后端现在直接返回data对象，不再包含code和message包装
    const response = await apiClient.post<{ access_token: string; refresh_token: string; token_type: string; user: UserInfo }>(
      API_ENDPOINTS.AUTH.LOGIN,
      formData.toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      },
    )

    // 保持返回类型兼容，构造LoginResponse格式
    return {
      data: {
        access_token: response.data.access_token,
        refresh_token: response.data.refresh_token,
        token_type: response.data.token_type,
        user: response.data.user,
      },
      code: 200, // 默认成功状态码
      message: 'Login successful', // 默认成功消息
    }
  }

  // 带密码的登录
  static async loginWithPassword(credentials: LoginRequest): Promise<LoginResponse> {
    const apiClient = getApiClient()
    // 将对象转换为URL编码的字符串
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password || '')
    formData.append('grant_type', credentials.grant_type || 'password')

    const response = await apiClient.post<{
      code: number,
      message: string
      data: { access_token: string; refresh_token: string; token_type: string; user: UserInfo }
    }>(API_ENDPOINTS.AUTH.LOGIN, formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  }


  // 用户注册
  static async register(userData: { username: string; password: string; verifyCode: string; grant_type: string }): Promise<LoginResponse> {
    const apiClient = getApiClient()
    // 将对象转换为URL编码的字符串
    const formData = new URLSearchParams()
    formData.append('username', userData.username)
    formData.append('password', userData.password)
    formData.append('verifyCode', userData.verifyCode)
    formData.append('grant_type', userData.grant_type || 'password')

    const response = await apiClient.post<{
      code: number,
      message: string
      data: { access_token: string; refresh_token: string; token_type: string; user: UserInfo
      }
    }>(
      API_ENDPOINTS.AUTH.REGISTER,
      {
        email: userData.username,
        password: userData.password,
        code: userData.verifyCode,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )
    return response.data
  }

  // 发送验证码
  static async sendCode(email: string): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ApiResponse<{ message: string }>>(
      API_ENDPOINTS.AUTH.SEND_CODE,
      { email: email },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )
    return response.data
  }

  // 用户登出
  static async logout(): Promise<ApiResponse<null>> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ApiResponse<null>>(API_ENDPOINTS.AUTH.LOGOUT)
    return response.data
  }

  // 刷新访问token
  static async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    const request: RefreshTokenRequest = { refreshToken }
    const apiClient = getApiClient()
    const response = await apiClient.post<RefreshTokenResponse>(API_ENDPOINTS.AUTH.REFRESH, request)
    return response.data
  }

  // 获取用户资料
  static async getProfile(): Promise<ApiResponse<UserInfoWithTag>> {
    const apiClient = getApiClient()
    const response = await apiClient.get<ApiResponse<UserInfoWithTag>>(API_ENDPOINTS.USERS.DETAIL)
    return response.data
  }

  // 更新用户资料
  static async updateProfile(userData: Partial<User>): Promise<ApiResponse<User>> {
    const apiClient = getApiClient()
    const response = await apiClient.put<ApiResponse<User>>(API_ENDPOINTS.USERS.UPDATE, userData)
    return response.data
  }

  // 修改密码
  static async changePassword(passwordData: ChangePasswordRequest & { userId: string }): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.put<ApiResponse<{ message: string }>>(API_ENDPOINTS.USERS.UPDATE.replace(':id', passwordData.userId), {
      password: passwordData.newPassword,
    })
    return response.data
  }

  // 验证token有效性
  static async validateToken(): Promise<ApiResponse<{ valid: boolean; expiresAt?: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.get<ApiResponse<{ valid: boolean; expiresAt?: string }>>(API_ENDPOINTS.AUTH.VERIFY_ACCESS_TOKEN)
    return response.data
  }

  // 安全验证token有效性（不触发重定向）
  static async validateTokenSafely(): Promise<ApiResponse<{ valid: boolean; expiresAt?: string }>> {
    // 创建一个临时的API客户端实例，不包含认证状态更新器，避免重定向
    const tempApiClient = createApiClientInstance(
      () => localStorage.getItem('access_token'), // 直接从localStorage获取token
      undefined, // 不传递authStateUpdater，避免401时自动重定向
    )
    const response = await tempApiClient.get<ApiResponse<{ valid: boolean; expiresAt?: string }>>(API_ENDPOINTS.AUTH.VERIFY_ACCESS_TOKEN)
    return response.data
  }

  // 检查用户权限
  static async checkPermission(): Promise<ApiResponse<{ hasPermission: boolean }>> {
    const apiClient = getApiClient()
    const response = await apiClient.get<ApiResponse<{ hasPermission: boolean }>>(API_ENDPOINTS.USERS.DETAIL)
    return response.data
  }

  // 获取用户角色
  static async getUserRole(): Promise<ApiResponse<{ role: string; permissions: string[] }>> {
    const apiClient = getApiClient()
    const response = await apiClient.get<ApiResponse<{ role: string; permissions: string[] }>>(API_ENDPOINTS.USERS.DETAIL)
    return response.data
  }

  // 忘记密码
  static async forgotPassword(email: string): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ApiResponse<{ message: string }>>(
      API_ENDPOINTS.AUTH.FORGOT_PASSWORD,
      { email: email },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )
    return response.data
    /*return {
      data: {
        message: respons_msg
      },
      code: 200, // 默认成功状态码
      message: 'VerifyCode send successful', // 默认成功消息
    }*/
  }

  // 重置密码
  static async resetPassword(request: ResetPasswordRequest): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()

    const response = await apiClient.post<ApiResponse<{ message: string }>>(
      API_ENDPOINTS.AUTH.RESET_PASSWORD,
      {
        email: request.email,
        code: request.code,
        new_password: request.new_pwd
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      },
    )
    return response.data
  }

  // 验证邮箱
  static async verifyEmail(token: string): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/auth/verify-email', { token })
    return response.data
  }

  // 重新发送验证邮件
  static async resendVerificationEmail(email: string): Promise<ApiResponse<{ message: string }>> {
    const apiClient = getApiClient()
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/auth/resend-verification', { email })
    return response.data
  }
}

// 导出认证服务实例
export default AuthService
