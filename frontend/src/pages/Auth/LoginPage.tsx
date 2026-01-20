import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../stores/useAuthStore'
import { Loader2 } from 'lucide-react'
import { useLogin, useUserSpaces, AuthService } from '@test-agentstudio/api-client'
import { generateLetterAvatar } from '../../utils/avatar'
import LanguageDropdown from '../../components/Common/LanguageDropdown'

interface LoginForm {
  username: string
  grant_type: string
}

const LoginPage: React.FC = () => {
  const { t, i18n } = useTranslation()
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const navigate = useNavigate()
  const { login, isAuthenticated, token } = useAuthStore()
  
  // 根据当前语言环境选择图片
  const loginImage = i18n.language.startsWith('zh') ? '/login-page.png' : '/login-page-en.png'

  // 使用hooks，传递认证状态管理器
  const loginMutation = useLogin({ login })
  const userSpacesQuery = useUserSpaces({ enabled: false }) // 初始禁用，避免401错误

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    setValue,
    getValues, // 添加getValues的解构
    reset,
  } = useForm<LoginForm>()

  // 检查认证状态和token有效性
  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        // 检查本地存储的token
        const storedToken = localStorage.getItem('access_token')
        const zustandToken = token

        const currentToken = storedToken || zustandToken

        // 如果没有token，直接显示登录页面
        if (!currentToken) {
          console.log('🔐 [LoginPage] No token found, showing login page')
          setIsCheckingAuth(false)
          return
        }

        // 如果已经通过Zustand认证，直接跳转到dashboard
        if (isAuthenticated) {
          console.log('🔐 [LoginPage] User already authenticated, redirecting to dashboard')
          navigate('/dashboard', { replace: true })
          return
        }

        // 如果有token但Zustand状态未认证，验证token有效性
        console.log('🔐 [LoginPage] Token found, validating...')
        try {
          // 使用安全验证方法，避免在登录页面触发重定向
          const response = await AuthService.validateTokenSafely()

          if (response.data.valid) {
            console.log('✅ [LoginPage] Token is valid, redirecting to dashboard')
            // 从localStorage恢复用户状态
            const storedUser = localStorage.getItem('auth-storage')
            if (storedUser) {
              try {
                const authData = JSON.parse(storedUser)
                if (authData.state?.user && authData.state?.token) {
                  login(authData.state.user, authData.state.token, authData.state.refreshToken)

                  // 重启token自动刷新
                  const { startTokenRenewal } = useAuthStore.getState()
                  startTokenRenewal()
                }
              } catch (parseError) {
                console.warn('⚠️ [LoginPage] Failed to parse stored auth data:', parseError)
              }
            }
            navigate('/dashboard', { replace: true })
          } else {
            console.log('❌ [LoginPage] Token is invalid, showing login page')
            // 清除无效的token
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            localStorage.removeItem('token_type')
            localStorage.removeItem('auth-storage') // 也清除存储的用户状态
            setIsCheckingAuth(false)
          }
        } catch (validationError) {
          console.warn('⚠️ [LoginPage] Token validation failed:', validationError)
          // Token验证失败，清除无效token并显示登录页面
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('token_type')
          localStorage.removeItem('auth-storage') // 也清除存储的用户状态
          setIsCheckingAuth(false)
        }
      } catch (error) {
        console.error('❌ [LoginPage] Authentication check failed:', error)
        setIsCheckingAuth(false)
      }
    }

    checkAuthentication()
  }, [isAuthenticated, token, login, navigate])

  // 页面加载时检查是否有保存的凭据
  // useEffect(() => {
  //   const savedEmail = localStorage.getItem('rememberedEmail')
  //   const savedPassword = localStorage.getItem('rememberedPassword')
  //   const savedRemember = localStorage.getItem('rememberMe')

  //   if (savedEmail && savedRemember === 'true') {
  //     setValue('username', savedEmail)
  //     setRememberMe(true)
  //   }
  //   if (savedPassword && savedRemember === 'true') {
  //     setValue('password', savedPassword)
  //   }
  // }, [setValue])

  // 处理登录（如果用户名不存在会自动注册）
  const handleLogin = async (data: LoginForm) => {
    const loginRequest = {
      username: data.username,
      password: '', // 不需要密码，传递空字符串
      grant_type: 'password',
    }

    try {
      // 使用hook进行登录（后端会自动判断是登录还是注册）
      const response = await loginMutation.mutateAsync(loginRequest)

      // 验证登录响应是否成功
      if (!response || response.code !== 200 || !response.data) {
        setError('root', {
          type: 'manual',
          message: (response as any)?.message || t('auth.login.loginFailed'),
        })
        console.error('Login failed: Invalid response', response)
        return // 不执行导航，停留在登录页面
      }

      // 从response中获取用户信息和token
      const userInfo = response.data.user
      const accessToken = response.data.access_token
      const refreshToken = response.data.refresh_token
      const tokenType = response.data.token_type

      // 验证必要的数据是否存在
      if (!userInfo || !accessToken) {
        setError('root', {
          type: 'manual',
          message: t('auth.login.loginFailed'),
        })
        console.error('Login failed: Missing user data or token')
        return // 不执行导航，停留在登录页面
      }

      // 使用响应数据登录
      login(
        {
          id: userInfo.user_id_str || '',
          username: userInfo.username || data.username,
          email: userInfo.email || data.username,
          avatar: userInfo.avatar_url || generateLetterAvatar(userInfo.username || userInfo.email),
          role: userInfo.role_type === 1 ? 'developer' : 'admin',
          permissions: userInfo.role_type === 1 ? ['read', 'write'] : ['read', 'write', 'admin'],
          spaceId: '',
        },
        accessToken,
        refreshToken,
      )

      // 保存token到localStorage
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)
      localStorage.setItem('token_type', tokenType)

      // 调用space接口获取空间列表
      let spaceId = ''
      try {
        // 确保token已经设置，延迟一小段时间
        await new Promise(resolve => setTimeout(resolve, 500))
        const spaceResponse = await userSpacesQuery.refetch()
        if (spaceResponse.data?.data && spaceResponse.data.data.space_list && spaceResponse.data.data.space_list.length > 0) {
          spaceId = spaceResponse.data.data.space_list[0].space_id
          localStorage.setItem('selectedSpaceId', spaceId)
          console.log('获取到的第一个空间ID:', spaceId)

          // 更新用户的spaceId
          const { updateUser } = useAuthStore.getState()
          updateUser({ spaceId })
        }
      } catch (spaceError) {
        console.error('获取空间列表错误:', spaceError)
        // 即使获取空间失败，也继续登录流程
      }

      // 保存凭据（如果勾选了记住我）
      // if (rememberMe) {
      //   localStorage.setItem('rememberedEmail', data.username)
      //   localStorage.setItem('rememberedPassword', data.password)
      //   localStorage.setItem('rememberMe', 'true')
      // } else {
      //   localStorage.removeItem('rememberedEmail')
      //   localStorage.removeItem('rememberedPassword')
      //   localStorage.removeItem('rememberMe')
      // }

      // 启动 token 自动刷新
      const { startTokenRenewal } = useAuthStore.getState()
      startTokenRenewal()

      // 只有在所有步骤都成功后才导航到仪表板
      console.log('✅ Login successful, navigating to dashboard')
      navigate('/dashboard')
    } catch (error) {
      const err: any = error
      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message
      setError('root', {
        type: 'manual',
        message: backendDetail || err?.message || t('auth.login.loginFailed'),
      })
      console.error('Login error:', error)
      // 确保在错误情况下不执行导航
    }
  }

  // 处理表单提交（回车键触发登录）
  const onFormSubmit = (data: LoginForm) => {
    handleLogin(data)
  }

  // 点击隐私条例触发相关事件
  const handleCustomLinkClick = (e: React.MouseEvent, type: string) => {
    e.stopPropagation()
    e.preventDefault()
  }

  // 显示加载状态 while checking authentication
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <div className="flex justify-center">
              <div className="w-16 h-16 flex items-center justify-center">
                <img src="/jiuwen-logo.svg" width={64} height={64} alt="Jiuwen Logo" />
              </div>
            </div>
            <div className="mt-6 flex items-center justify-center space-x-2">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span className="text-lg text-gray-600">{t('auth.login.loggingIn')}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col py-12 px-4 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between">
        <div className="flex w-48">
          <div className="w-8 h-8 mr-2">
            <img src="/jiuwen-logo.svg" width={64} height={64} alt="Jiuwen Logo" />
          </div>
          <div className="text-xl font-[800] item-end mt-2">openJiuwen</div>
        </div>
        {/* <LanguageDropdown /> */}
      </div>
      <div className="w-full flex justify-center flex-1 items-center">
        <div className="flex items-center justify-center h-full">
          {/* Jiuwen image */}
          <div className="w-[60%] max-w-[600px] h-[500px] mr-8">
            <div className="w-[100%] h-[100%]">
              <img src={loginImage} alt="Jiuwen" className="w-full h-full object-contain" />
            </div>
          </div>

          <div className="w-[400px] space-y-8 flex flex-col h-[466px] rounded-xl shadow-xl px-8 py-8">
            <div className="font-[600] text-xl">{t('auth.login.formTitle')}</div>
            {/* Login Form */}
            <form className="space-y-6 flex-1" onSubmit={handleSubmit(onFormSubmit)}>
              <div className="space-y-4">
                <div>
                  <input
                    {...register('username', {
                      required: t('auth.login.usernamePlaceholder'),
                      maxLength: {
                        value: 50,
                        message: '邮箱长度不能超过50个字符',
                      },
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: t('auth.login.invalidEmailFormat'),
                      },
                    })}
                    maxLength={50}
                    type="text"
                    id="username"
                    className="input-field w-full"
                    placeholder={t('auth.login.usernamePlaceholder')}
                  />
                  <p className="mt-1 text-sm text-red-600">{errors.username ? errors.username.message : ''}</p>
                </div>
              </div>

              {errors.root && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-600">{errors.root.message}</p>
                </div>
              )}

              <div>
                <button
                  type="submit"
                  disabled={loginMutation.isLoading}
                  className="w-full btn-primary py-3 text-base font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loginMutation.isLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>{t('auth.login.loggingIn')}</span>
                    </div>
                  ) : (
                    t('auth.login.loginButton')
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
