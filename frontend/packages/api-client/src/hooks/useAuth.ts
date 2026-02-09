import { useMutation, useQuery, useQueryClient } from 'react-query'
import AuthService from '../services/authService'
import { LoginRequest, ResetPasswordRequest } from '../types'
import { generateLetterAvatar } from '../../../../src/utils/avatar'

// 认证状态管理接口
export interface AuthStateManager {
  login?: (user: any, token: string, refreshToken?: string) => void
  logout?: () => void
  updateToken?: (token: string) => void
}

const store_response_msg = (response, authStateManager?: AuthStateManager) => {
  const user = {
    id: response.data.user.user_id_str,
    username: response.data.user.username,
    email: response.data.user.email,
    avatar: response.data.user.avatar_url || generateLetterAvatar(response.data.user.username || response.data.user.email),
    role: response.data.user.role_type as unknown as 'admin' | 'user' | 'developer',
    permissions: response.data.user.role_type === 1 ? ['read', 'write'] : ['read', 'write', 'admin'],
  }

  if (authStateManager?.login) {
    authStateManager.login(user, response.data.access_token, response.data.refresh_token)
  }
}

// 认证相关的React Query hooks
// 用户登录
export const useLogin = (authStateManager?: AuthStateManager) => {
  const queryClient = useQueryClient()

  return useMutation((credentials: LoginRequest) => AuthService.login(credentials), {
    onSuccess: (response, variables, context) => {
      console.log('🔐 [useLogin] Login response received:', { code: response.code, hasData: !!response.data })
      if (response.code === 200 && response.data) {
        console.log('response is ', response)

        // 登录成功，更新认证状态
        store_response_msg(response, authStateManager)
        // 清除相关查询缓存
        queryClient.clear()
        // 重新获取用户资料
        queryClient.invalidateQueries(['user', 'profile'])

        console.log('✅ [useLogin] Login successful, user state updated')
      } else {
        console.log('❌ [useLogin] Login failed, but onSuccess was triggered - code:', response.code)
        // 这里不应该触发认证状态更新，让调用方处理错误
      }
    },
    onError: error => {
      console.error('❌ [useLogin] Login failed:', error)
    },
  })
}

export const useLoginWithPwd = (authStateManager?: AuthStateManager) => {
  const queryClient = useQueryClient()

  return useMutation((credentials: LoginRequest) => AuthService.loginWithPassword(credentials), {
    onSuccess: (response) => {
      if (response.code === 200 && response.data) {

        // 登录成功，更新认证状态
        store_response_msg(response, authStateManager)
        // 清除相关查询缓存
        queryClient.clear()
        // 重新获取用户资料
        queryClient.invalidateQueries(['user', 'profile'])

        console.log('✅ [useLogin] Login successful, user state updated')
      } else {
        console.log('❌ [useLogin] Login failed, but onSuccess was triggered - code:', response.code)
      }
    },
    onError: error => {
      console.error('❌ [useLogin] Login failed:', error)
    },
  })
}


// 用户注册
export const useRegister = (authStateManager?: AuthStateManager) => {
  const queryClient = useQueryClient()

  return useMutation((userData: { username: string; password: string; verifyCode: string; grant_type: string }) => AuthService.register(userData), {
    onSuccess: (response) => {
      if (response.code === 200 && response.data) {
        // 登录成功，更新认证状态
        store_response_msg(response, authStateManager)
        // 清除相关查询缓存
        queryClient.clear()
        // 重新获取用户资料
        queryClient.invalidateQueries(['user', 'profile'])
        console.log('✅ [useRegister] Register successful, user state updated')
      } else {
        console.log('❌ [useRegister] Register failed, but onSuccess was triggered - code:', response.code)
      }
    },
    onError: error => {
      console.error('❌ [useRegister] Register failed:', error)
    },
  })
}

// 用户登出
export const useLogout = (authStateManager?: AuthStateManager) => {
  const queryClient = useQueryClient()

  return useMutation(() => AuthService.logout(), {
    onSuccess: () => {
      // 登出成功，清除认证状态
      if (authStateManager?.logout) {
        authStateManager.logout()
      }

      // 清除所有查询缓存
      queryClient.clear()
    },
    onError: error => {
      console.error('登出失败:', error)
      // 即使API调用失败，也要清除本地状态
      if (authStateManager?.logout) {
        authStateManager.logout()
      }
      queryClient.clear()
    },
  })
}

// 获取用户资料
export const useGetProfile = () => {
  return useQuery(['user', 'profile'], () => AuthService.getProfile(), {
    staleTime: 5 * 60 * 1000, // 5分钟内不重新获取
    cacheTime: 10 * 60 * 1000, // 缓存10分钟
    retry: 2,
    retryDelay: 1000,
    onError: error => {
      console.error('获取用户资料失败:', error)
    },
  })
}

// 更新用户资料
export const useUpdateProfile = () => {
  const queryClient = useQueryClient()

  return useMutation(
    (
      userData: Partial<{
        id: string
        username: string
        email: string
        firstName?: string
        lastName?: string
        avatar?: string
        role: 'admin' | 'user' | 'developer'
        permissions: string[]
      }>,
    ) => AuthService.updateProfile(userData),
    {
      onSuccess: response => {
        if (response.success && response.data) {
          // 更新成功后，更新缓存中的用户资料
          queryClient.setQueryData(['user', 'profile'], response)

          // 重新获取用户资料
          queryClient.invalidateQueries(['user', 'profile'])
        }
      },
      onError: error => {
        console.error('更新用户资料失败:', error)
      },
    },
  )
}

// 修改密码
export const useChangePassword = () => {
  return useMutation((passwordData: { newPassword: string; confirmPassword: string; userId: string }) => AuthService.changePassword(passwordData), {
    onError: error => {
      console.error('修改密码失败:', error)
    },
  })
}

// 发送验证码
export const useSendCode = () => {
  return useMutation((email:string) => AuthService.sendCode(email), {
    onSuccess: () => {
      console.error('Send code success.')
    },
    onError: error => {
      console.error('Send code failed:', error)
    }
  })
}


// 忘记密码--发送验证码
export const useForgotPassword = () => {
  return useMutation((email: string) => AuthService.forgotPassword(email), {
    onSuccess: () => {
      console.log('Get code success.')
    },
    onError: error => {
      console.error('Get code failed:', error)
    },
  })
}


// 重置密码
export const useResetPassword = () => {
  return useMutation((request: ResetPasswordRequest)=>AuthService.resetPassword(request), {
    onSuccess: () => {
      console.log('Reset password success.')
    },
    onError: error => {
      console.error('Reset password failed:', error)
    }
  })
}


// 验证token有效性
export const useValidateToken = () => {
  return useQuery(['auth', 'validate'], () => AuthService.validateToken(), {
    staleTime: 1 * 60 * 1000, // 1分钟内不重新验证
    cacheTime: 2 * 60 * 1000, // 缓存2分钟
    retry: 1,
    retryDelay: 2000,
    onError: error => {
      console.error('Token验证失败:', error)
    },
  })
}

// 检查用户权限
export const useCheckPermission = (permission: string) => {
  return useQuery(['auth', 'permission', permission], () => AuthService.checkPermission(), {
    staleTime: 5 * 60 * 1000, // 5分钟内不重新检查
    cacheTime: 10 * 60 * 1000, // 缓存10分钟
    retry: 1,
    retryDelay: 1000,
    onError: error => {
      console.error('权限检查失败:', error)
    },
  })
}

// 获取用户角色
export const useUserRole = () => {
  return useQuery(['auth', 'role'], () => AuthService.getUserRole(), {
    staleTime: 5 * 60 * 1000, // 5分钟内不重新获取
    cacheTime: 10 * 60 * 1000, // 缓存10分钟
    retry: 1,
    retryDelay: 1000,
    onError: error => {
      console.error('获取用户角色失败:', error)
    },
  })
}

// 验证邮箱
export const useVerifyEmail = () => {
  return useMutation((token: string) => AuthService.verifyEmail(token), {
    onSuccess: () => {
      // 邮箱验证成功后，可以重新获取用户资料
      // 这里可以根据需要添加逻辑
    },
    onError: error => {
      console.error('邮箱验证失败:', error)
    },
  })
}

// 重新发送验证邮件
export const useResendVerificationEmail = () => {
  return useMutation((email: string) => AuthService.resendVerificationEmail(email), {
    onError: error => {
      console.error('重新发送验证邮件失败:', error)
    },
  })
}
