import React, { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next'
import {
  AuthService,
  ResetPasswordRequest,
  useForgotPassword,
  useLoginWithPwd,
  useRegister,
  useResetPassword,
  useSendCode,
  useUserSpaces,
} from '@test-agentstudio/api-client'
import { useAuthStore } from '@/stores/useAuthStore.ts'
import { generateLetterAvatar } from '@/utils/avatar.ts'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import LanguageDropdown from '@/components/Common/LanguageDropdown.tsx'

interface FormData {
  username: string // 邮箱字段（所有界面都有）
  password?: string // 密码字段（登录/注册界面）
  confirmPassword?: string // 确认密码字段（注册界面）
  newPassword?: string // 新密码字段（忘记密码界面）
  verifyCode?: string // 验证码字段（注册/忘记密码界面）
}

interface LoginInfo {
  remainingAttempts: number,
  isLocked: boolean,
  lockEndTime: number
}

const PASSWORD_MIN_LENGTH = 6
const PASSWORD_MAX_LENGTH = 20

const validatePasswordStrength = (value?: string) => {
  if (!value) return true
  const hasDigit = /\d/.test(value)
  const hasLower = /[a-z]/.test(value)
  const hasUpper = /[A-Z]/.test(value)
  const hasSpecial = /[^\w]/.test(value)
  const classCount = [hasDigit, hasLower, hasUpper, hasSpecial].filter(Boolean).length
  if (classCount < 2) {
    return '密码需包含数字/小写字母/大写字母/特殊字符中至少 2 种'
  }
  return true
}

const accountLockStorage = {
  // 最大存储条数
  MAX_STORAGE_COUNT: 20,

  // 获取指定账户的锁定信息
  getAccountLockInfo: (email:string) => {
    if (!email) return null
    const key = `account_lock_${email}`
    const stored = localStorage.getItem(key)
    return stored ? JSON.parse(stored) : null
  },

  // 保存指定账户的锁定信息
  saveAccountLockInfo: (email:string, data:LoginInfo) => {
    if (!email) return
    // 先清理过期数据
    accountLockStorage.cleanExpiredLockInfo();
    // 判断是否超过存储最大条数
    accountLockStorage.limitStorageCount();

    const key = `account_lock_${email}`;
    localStorage.setItem(key, JSON.stringify({
      ...data,
      updateTime: new Date().getTime() // 记录最后更新时间，用于清理
    }));
  },

  // 清理所有已过期的锁定信息
  cleanExpiredLockInfo: () => {
    const now = new Date().getTime();
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('account_lock_')) {
        const stored = localStorage.getItem(key);
        if (stored) {
          const lockInfo = JSON.parse(stored);
          if (lockInfo.isLocked && lockInfo.lockEndTime < now) {
            localStorage.removeItem(key);
          }
        }
      }
    });
  },

  // 根据key获取更新时间
  readUpdateTime:(key:string) => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw)?.updateTime ?? 0 : 0;
    } catch {
      return 0;
    }
  },

  // 限制存储数量，超过则删除最早更新的
  limitStorageCount: () => {
    const lockKeys = Object.keys(localStorage)
      .filter(key => key.startsWith('account_lock_'))
      .map(key => ({
        key,
        updateTime: accountLockStorage.readUpdateTime(key)
      }))
      .sort((a, b) => a.updateTime - b.updateTime); // 按更新时间升序

    if (lockKeys.length > accountLockStorage.MAX_STORAGE_COUNT) {
      // 删除超出数量的最早数据
      const keysToDelete = lockKeys.slice(0, lockKeys.length - accountLockStorage.MAX_STORAGE_COUNT);
      keysToDelete.forEach(item => localStorage.removeItem(item.key));
    }
  },

  // 清除指定账户的锁定信息
  clearAccountLockInfo: (email:string) => {
    if (!email) return
    const key = `account_lock_${email}`
    localStorage.removeItem(key)
  },
}

const UserLoginPage: React.FC = () => {
  const MAX_ATTEMPT_NUM = 5

  // 状态管理：当前激活的标签（login/register/forgot）、倒计时、倒计时状态
  const [activeTab, setActiveTab] = useState('login')
  const [countdown, setCountdown] = useState(0)
  const [isCountdownActive, setIsCountdownActive] = useState(false)

  // 账户剩余尝试次数，最多尝试5次
  const [remainingAttempts, setRemainingAttempts] = useState(MAX_ATTEMPT_NUM)
  // 账户是否被锁定
  const [isAccountLocked, setIsAccountLocked] = useState(false)
  // 账户锁定计时
  const [lockCountdown, setLockCountdown] = useState(0)
  // 登录错误信息
  const [loginError, setLoginError] = useState('')
  // 通用错误状态，用于注册/忘记密码场景
  const [commonError, setCommonError] = useState('')
  // 是否在认证
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  // 重置成功提示 + 定时器（用于自动消失）
  const [successMsg, setSuccessMsg] = useState('')
  // 锁定定时器引用
  const lockTimerRef = useRef<number | null>(null);
  // 锁定用户引用
  const lockedEmailRef = useRef<string>('');

  const successMsgTimer = useRef<NodeJS.Timeout | null>(null)
  // 上下文信息
  const { login, isAuthenticated, token } = useAuthStore()
  // 导航
  const navigate = useNavigate()
  // 使用hooks，传递认证状态管理器
  const loginMutation = useLoginWithPwd({ login })
  // register hook， 注册成功后，会直接跳转，会存储用户信息
  const registerMutation = useRegister({ login })
  // 发送验证码
  const sendCodeMutation = useSendCode()
  // 忘记密码-- 发送验证码
  const forgotPasswordMutation = useForgotPassword()
  // 重置密码
  const resetPasswordMutation = useResetPassword()
  // 获取用户空间
  const userSpacesQuery = useUserSpaces({ enabled: false }) // 初始禁用，避免401错误

  const { t, i18n } = useTranslation()
  // 根据当前语言环境选择图片
  const loginImage = i18n.language.startsWith('zh') ? '/login-page.png' : '/login-page-en.png'
  // 表单配置 - 根据不同标签使用不同的验证规则
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    clearErrors,
    setError,
    getValues,
    watch,
    reset,
  } = useForm<FormData>({
    mode: 'onChange',
    defaultValues: {
      username: '',
      password: '',
      confirmPassword: '',
      newPassword: '',
      verifyCode: '',
    },
  })

  // 监听当前输入的邮箱
  const currentEmail = watch('username', '')

  // 切换标签时清空所有错误状态
  useEffect(() => {
    setLoginError('')
    setCommonError('')
    clearErrors()
    setCountdown(0)
    setIsCountdownActive(false)
  }, [activeTab, clearErrors])

  // 账户锁定倒计时
  // 账户锁定倒计时（终极修复版）
  useEffect(() => {
    // 只有锁定状态为true时才执行
    if (!isAccountLocked) return

    // 只从ref读取锁定邮箱（不再读currentEmail）
    const targetEmail = lockedEmailRef.current
    if (!targetEmail || lockCountdown <= 0) return

    // 先清除残留定时器
    if (lockTimerRef.current) {
      clearInterval(lockTimerRef.current)
    }

    // 启动一次定时器，直到倒计时结束才停止
    lockTimerRef.current = window.setInterval(() => {
      setLockCountdown(prev => {
        // 倒计时结束
        if (prev <= 1) {
          setIsAccountLocked(false)
          setRemainingAttempts(MAX_ATTEMPT_NUM)
          accountLockStorage.clearAccountLockInfo(targetEmail)
          lockedEmailRef.current = '' // 清空ref
          clearInterval(lockTimerRef.current!)
          lockTimerRef.current = null
          return 0
        }

        // 每10秒存储一次（用固定的targetEmail）
        if (prev % 10 === 0) {
          const loginInfo: LoginInfo = {
            remainingAttempts: 0,
            isLocked: true,
            lockEndTime: new Date().getTime() + (prev - 1) * 1000,
          }
          console.log('🟢 存储锁定信息', { targetEmail, prev, lockEndTime: loginInfo.lockEndTime })
          accountLockStorage.saveAccountLockInfo(targetEmail, loginInfo)
        }

        return prev - 1
      })
    }, 1000)

    // 组件卸载/锁定状态解除时清除定时器
    return () => {
      if (lockTimerRef.current) {
        clearInterval(lockTimerRef.current)
        lockTimerRef.current = null
      }
    }
  }, [isAccountLocked])

  // 防抖定时器 ref（用于控制执行时机，最小改动）
  const emailChangeTimer = useRef<number | null>(null)

  // 仅当页面初始化/邮箱切换且该邮箱有锁定记录时，加载本地存储
  useEffect(() => {
    // 页面初始化时先清理所有过期数据
    if (remainingAttempts == MAX_ATTEMPT_NUM && !currentEmail) {
      accountLockStorage.cleanExpiredLockInfo()
    }

    // 核心优化：防抖处理 - 清除之前的定时器，500ms后执行
    if (emailChangeTimer.current) {
      clearTimeout(emailChangeTimer.current)
    }

    emailChangeTimer.current = window.setTimeout(() => {
      const loadLockInfo = () => {
        if (!currentEmail) {
          setRemainingAttempts(MAX_ATTEMPT_NUM)
          setIsAccountLocked(false)
          setLockCountdown(0)
          setLoginError('')
          clearErrors('root')
          return
        }
        const lockInfo = accountLockStorage.getAccountLockInfo(currentEmail)
        // 有锁定记录，判断是否过期
        const now = new Date().getTime()
        if (lockInfo && lockInfo.isLocked && lockInfo.lockEndTime > now) {
          // 仍在锁定中，加载状态
          const remainingSeconds = Math.floor((lockInfo.lockEndTime - now) / 1000)
          setIsAccountLocked(true)
          setLockCountdown(remainingSeconds)
          setRemainingAttempts(0)
          setLoginError('')
          clearErrors('root')
        } else {
          // 锁定已过期，清理记录并重置（条件更新）
          if (isAccountLocked || remainingAttempts === 0) {
            setIsAccountLocked(false)
            setLockCountdown(0)
            setRemainingAttempts(MAX_ATTEMPT_NUM)
          }
          accountLockStorage.clearAccountLockInfo(currentEmail)
        }
      }
      loadLockInfo()
    }, 500) // 500ms 防抖
    // 组件卸载时清除定时器
    return () => {
      if (emailChangeTimer.current) {
        clearTimeout(emailChangeTimer.current)
      }
    }
  }, [currentEmail, setError])

  // 清理定时器， 防止内容泄露
  useEffect(() => {
    return () => {
      if (successMsgTimer.current) {
        clearTimeout(successMsgTimer.current)
      }
    }
  }, [])

  // 倒计时逻辑
  useEffect(() => {
    let timer: number
    if (isCountdownActive && countdown > 0) {
      timer = window.setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            setIsCountdownActive(false)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }
    // 清除定时器，避免内存泄漏
    return () => clearInterval(timer)
  }, [isCountdownActive, countdown])

  // 获取验证码处理函数
  const handleGetVerifyCode = async () => {
    // 获取当前表单值
    const { username, password, confirmPassword } = getValues()
    // 账号密码都已经输入，才能获取验证码
    const isValid = username && password && confirmPassword && password === confirmPassword

    if (!isValid) return
    try {
      clearErrors('root')
      // 清空旧的通用错误
      setCommonError('')

      const response = await sendCodeMutation.mutateAsync(username)

      // 先判断失败场景
      if (!response || response.code !== 200 || !response.data) {
        const errorMsg = (response as any)?.message || t('auth.register.sendCodeFailed')
        // 同时设置root错误和通用错误
        setError('root', {
          type: 'manual',
          message: errorMsg,
        })
        setCommonError(errorMsg)
        return
      }

      // 只有成功才设置倒计时
      setCountdown(60)
      setIsCountdownActive(true)
    } catch (error) {
      // 捕获网络错误、请求异常等情况
      const err: any = error
      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message || err?.message
      const errorMsg = backendDetail || t('auth.register.sendCodeFailed')
      // 异常时也设置通用错误
      setError('root', {
        type: 'manual',
        message: errorMsg,
      })
      setCommonError(errorMsg)
    }
  }

  // 忘记密码--获取验证码
  const handleForgotPassword = async () => {
    // 获取当前表单值
    const { username, newPassword } = getValues()
    // 用户名和密码不为空才能获取验证码
    const isValid = username && newPassword
    if (!isValid) return

    // 记密码获取验证码添加错误处理
    try {
      clearErrors('root')
      setCommonError('')

      const response = await forgotPasswordMutation.mutateAsync(username)

      //  发送验证码失败
      if (!response || response.code !== 200 || !response.data) {
        const errorMsg = (response as any)?.message || t('auth.forgotPassword.sendCodeFailed')
        setError('root', {
          type: 'manual',
          message: errorMsg,
        })
        setCommonError(errorMsg)
        return
      }

      // 开始倒计时
      setCountdown(60)
      setIsCountdownActive(true)
    } catch (error) {
      const err: any = error
      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message || err?.message
      const errorMsg = backendDetail || t('auth.forgotPassword.sendCodeFailed')
      setError('root', {
        type: 'manual',
        message: errorMsg,
      })
      setCommonError(errorMsg)
    }
  }

  const removeLocalCache = () => {
    // 清除无效的token
    localStorage.removeItem('token_type')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('access_token')
    localStorage.removeItem('auth-storage')
  }

  // 使用 ref 追踪认证检查状态，避免重复执行导致无限循环
  const authCheckInProgress = useRef(false)

  //
  useEffect(() => {
    // 防止重复执行认证检查
    if (authCheckInProgress.current) {
      return
    }

    const checkAuthentication = async () => {
      // 标记正在进行认证检查
      authCheckInProgress.current = true

      try {
        // 检查本地存储的token
        const zustandToken = token
        const storedToken = localStorage.getItem('access_token')
        const currentToken = storedToken || zustandToken
        // 如果没有token，直接显示登录页面
        if (!currentToken) {
          setIsCheckingAuth(false)
          authCheckInProgress.current = false
          return
        }
        // 如果已经通过Zustand认证，直接跳转到dashboard
        if (isAuthenticated) {
          navigate('/dashboard', { replace: true })
          setIsCheckingAuth(false)
          authCheckInProgress.current = false
          return
        }
        // 有token但是未认证状态
        try {
          // 使用安全验证方法，避免在登录页面触发重定向
          const response = await AuthService.validateTokenSafely()

          if (response.data && response.data.valid) {
            // 重启token自动刷新
            const { startTokenRenewal } = useAuthStore.getState()
            startTokenRenewal()
            navigate('/dashboard', { replace: true })
            setIsCheckingAuth(false)
          } else {
            console.log('[LoginPage] Token is invalid, showing login page')
            removeLocalCache()
            setIsCheckingAuth(false)
          }
        } catch (validationError) {
          console.warn('⚠️ [LoginPage] Token validation failed:', validationError)
          // Token验证失败，清除无效token并显示登录页面
          removeLocalCache()
          setIsCheckingAuth(false)
        }
      } catch (error) {
        console.error('[LoginPage] Authentication check failed:', error)
        setIsCheckingAuth(false)
      } finally {
        authCheckInProgress.current = false
      }
    }
    checkAuthentication()
  }, [isAuthenticated, token, navigate])

  // 封装通用的登录/注册成功处理函数（抽离出来，避免重复代码）
  const handleAuthSuccess = async (userInfo: any, accessToken: string, refreshToken: string, tokenType: string) => {
    try {
      // 步骤1：把用户信息存储到内存（和登录逻辑一致）
      login(
        {
          id: userInfo.user_id_str || '',
          username: userInfo.username || '',
          email: userInfo.email || '',
          avatar: userInfo.avatar_url || generateLetterAvatar(userInfo.username || userInfo.email),
          role: userInfo.role_type === 1 ? 'developer' : 'admin',
          permissions: userInfo.role_type === 1 ? ['read', 'write'] : ['read', 'write', 'admin'],
          spaceId: '',
        },
        accessToken,
        refreshToken,
      )

      // 步骤2：保存token到localStorage（持久化）
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)
      localStorage.setItem('token_type', tokenType)

      // 调用space接口获取空间列表（和登录逻辑一致）
      let spaceId = ''
      try {
        await new Promise(resolve => setTimeout(resolve, 500)) // 确保token生效
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
        // 即使获取空间失败，不阻断登录/注册流程
      }

      // 启动 token 自动刷新
      const { startTokenRenewal } = useAuthStore.getState()
      startTokenRenewal()

      // 跳转到功能页面（注册/登录统一跳转到仪表盘）
      console.log('✅ Auth successful, navigating to dashboard')
      return true
    } catch (error) {
      console.error('Auth success handler error:', error)
      // 即使处理过程出错，仍尝试跳转（保证用户能进入功能页）
      return false
    }
  }

  useEffect(() => {
    if (remainingAttempts === 0 && currentEmail && !isAccountLocked) {
      const lockSeconds = 30 * 60 // 1800
      const lockEndTime = new Date().getTime() + lockSeconds * 1000
      lockedEmailRef.current = currentEmail;
      // 先校验本地存储，避免重复写入
      const existingLockInfo = accountLockStorage.getAccountLockInfo(currentEmail)
      if (!existingLockInfo || !existingLockInfo.isLocked || existingLockInfo.lockEndTime < new Date().getTime()) {
        // 强制更新内存状态
        setLockCountdown(lockSeconds)
        setIsAccountLocked(true)
        setLoginError('')
        clearErrors('root')

        // 强制持久化到localStorage（覆盖旧数据）
        accountLockStorage.saveAccountLockInfo(currentEmail, {
          remainingAttempts: 0,
          isLocked: true,
          lockEndTime: lockEndTime,
        })
        // 触发一次状态更新，确保定时器感知到锁定状态
        setLockCountdown(prev => prev)

        // 兜底：立即重新读取localStorage，确认写入成功
        setTimeout(() => {
          const savedLockInfo = accountLockStorage.getAccountLockInfo(currentEmail)
          console.log('1234567: 确认本地存储写入结果', savedLockInfo)
        }, 100)
      }
    }
  }, [remainingAttempts, currentEmail, isAccountLocked, setError])

  const handleLogin = async (data: FormData, currentRemainingAttempts: number) => {
    const loginRequest = {
      username: data.username,
      password: data.password ?? '',
      grant_type: 'password',
    }

    try {
      // 使用hook进行登录（后端会自动判断是登录还是注册）
      const response = await loginMutation.mutateAsync(loginRequest)

      if (!response || response.code !== 200 || !response.data) {
        const newAttempts = currentRemainingAttempts - 1
        if (newAttempts <= 0) {
          return false
        }

        setError('root', {
          type: 'manual',
          message: (response as any)?.message || t('auth.login.loginFailed'),
        })
        console.error('Login failed: Invalid response', response)
        return false
      }

      // 登录成功，返回的用户信息，token信息， 这些信息用于后继的跳转
      const userInfo = response.data.user
      const accessToken = response.data.access_token
      const refreshToken = response.data.refresh_token
      const tokenType = response.data.token_type

      // 验证必要的数据是否存在
      if (!userInfo || !accessToken) {
        const newAttempts = currentRemainingAttempts - 1
        if (newAttempts <= 0) return false
        setError('root', {
          type: 'manual',
          message: t('auth.login.loginFailed'),
        })
        console.error('Login failed: Missing user data or token')
        return false
      }

      await handleAuthSuccess(userInfo, accessToken, refreshToken, tokenType)
      return true
    } catch (error) {
      const err: any = error
      const newAttempts = currentRemainingAttempts - 1
      if (newAttempts <= 0) {
        return false
      }

      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message
      setError('root', {
        type: 'manual',
        message: backendDetail || err?.message || t('auth.login.loginFailed'),
      })
      console.error('Login error:', error)
      return false
    }
  }

  // 注册
  const handleRegister = async (data: FormData) => {
    const registerRequest = {
      username: data.username,
      password: data.password ?? '',
      verifyCode: data.verifyCode ?? '',
      grant_type: 'password',
    }
    try {
      // 注册前清空通用错误
      setCommonError('')
      const response = await registerMutation.mutateAsync(registerRequest)
      //  注册失败
      if (!response || response.code !== 200 || !response.data) {
        const errorMsg = (response as any)?.message || t('auth.register.registerFailed')
        setError('root', {
          type: 'manual',
          message: errorMsg,
        })
        setCommonError(errorMsg)
        console.error('Register failed: Invalid response', response)
        return false
      }

      // 注册成功，返回的用户信息，token信息， 这些信息用于后继的跳转
      const userInfo = response.data.user
      const accessToken = response.data.access_token
      const refreshToken = response.data.refresh_token
      const tokenType = response.data.token_type

      // 验证必要的数据是否存在
      if (!userInfo || !accessToken) {
        const errorMsg = t('auth.register.registerFailed')
        setError('root', {
          type: 'manual',
          message: errorMsg,
        })
        setCommonError(errorMsg)
        console.error('Register failed: Missing user data or token')
        return false
      }

      await handleAuthSuccess(userInfo, accessToken, refreshToken, tokenType)
      return true
    } catch (error) {
      const err: any = error
      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message
      const errorMsg = backendDetail || err?.message || t('auth.register.registerFailed')
      setError('root', {
        type: 'manual',
        message: errorMsg,
      })
      setCommonError(errorMsg)
      console.error('Register error:', error)
      return false
    }
  }

  const handleResetPassword = async (data: FormData) => {
    const resetReq: ResetPasswordRequest = {
      email: data.username,
      new_pwd: data.newPassword ?? '',
      code: data.verifyCode ?? '',
    }

    try {
      // 🔴 重置密码前清空通用错误
      setCommonError('')
      const response = await resetPasswordMutation.mutateAsync(resetReq)
      if (!response || response.code !== 200 || !response.data) {
        const errorMsg = (response as any)?.message || t('auth.forgotPassword.resetFailed')
        setError('root', {
          type: 'manual',
          message: errorMsg,
        })
        setCommonError(errorMsg)
        console.error('Register failed: Invalid response', response)
        return false
      }
      return true
    } catch (error) {
      const err: any = error
      const backendDetail = err?.response?.data?.detail || err?.response?.data?.message
      const errorMsg = backendDetail || err?.message || t('auth.forgotPassword.resetFailed')
      setError('root', {
        type: 'manual',
        message: errorMsg,
      })
      setCommonError(errorMsg)
      console.error('Reset password error:', error)
      return false
    }
  }

  // 表单提交处理
  const onFormSubmit = (data: FormData) => {
    // 注册逻辑
    const username = data.username
    const password = data.password
    const verifyCode = data.verifyCode
    const newPassword = data.newPassword

    switch (activeTab) {
      case 'login':
        if (!username || isAccountLocked)
          // 如果账户是锁定状态，不能登录
          return
        handleLogin(data, remainingAttempts).then(loginSuccess => {
          if (loginSuccess) {
            // 登录成功，清理该邮箱的锁定信息
            setRemainingAttempts(MAX_ATTEMPT_NUM)
            setIsAccountLocked(false)
            setLockCountdown(0)
            accountLockStorage.clearAccountLockInfo(username)
            // 成功跳转到面板
            navigate('/dashboard')
          } else {
            // 1. 内存中更新剩余次数
            if (!isAccountLocked) {
              const newAttempts = remainingAttempts - 1
              setRemainingAttempts(newAttempts)

              if (newAttempts > 0) {

                accountLockStorage.saveAccountLockInfo(username, {
                  remainingAttempts: newAttempts,
                  isLocked: false,
                  lockEndTime: 0,
                })
                setLoginError(t('auth.login.loginFailed'))
              } else {
                setLoginError('')
              }
            }
          }
        })
        break
      case 'register':
        console.log('注册提交:', data)
        // 注册逻辑
        if (!username || !password || !verifyCode)
          // 信息不全，不能注册
          return
        handleRegister(data).then(registerSuccess => {
          if (registerSuccess) {
            navigate('/dashboard')
          } else {
            console.error('Register failed.')
            return
          }
        })
        break
      case 'forgot':
        console.log('忘记密码提交:', data)
        if (!username || !newPassword || !verifyCode)
          // 信息不全，不能重置密码
          return
        handleResetPassword(data).then(resetPwdRs => {
          if (resetPwdRs) {
            setActiveTab('login')
            reset()
            setSuccessMsg(t('auth.forgotPassword.resetSuccess'))
            // 3秒后自动清空提示
            if (successMsgTimer.current) clearTimeout(successMsgTimer.current)
            successMsgTimer.current = setTimeout(() => {
              setSuccessMsg('')
            }, 3000)
            // 清空错误提示
            setLoginError('')
            setCommonError('')
          } else {
            console.log('Reset password failed.')
          }
        })
        // 重置密码逻辑
        break
      default:
        break
    }
  }

  // 格式化倒计时为 时:分:秒
  const formatCountdown = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // 判断获取验证码按钮是否可点击
  const isVerifyCodeBtnDisabled = () => {
    const { username, password, confirmPassword, newPassword } = getValues()
    // 倒计时中禁用，或输入不完整禁用
    if (isCountdownActive) return true

    if (activeTab === 'register') {
      return !username || !password || !confirmPassword || password !== confirmPassword
    } else if (activeTab === 'forgot') {
      return !username || !newPassword
    }
    return true
  }

  // 输入框样式
  const inputFieldClass = 'w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
  // 主按钮样式（登录/注册/忘记密码提交按钮）
  const btnPrimaryClass =
    'w-full text-base font-medium btn-login disabled:cursor-not-allowed'
  // 链接样式
  const linkClass = 'text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-sm'

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
        <LanguageDropdown />
      </div>
      <div className="w-full flex justify-center flex-1 items-center">
        <div className="flex items-center justify-center h-full">
          {/* 左侧图片 */}
          <div className="w-[60%] max-w-[600px] h-[500px] mr-8 hidden lg:block">
            <div className="w-[100%] h-[100%]">
              <img src={loginImage} alt="Jiuwen" className="w-full h-full object-contain" />
            </div>
          </div>

          {/* 右侧表单区域 */}
          <div className="w-full max-w-[400px] space-y-8 flex flex-col h-auto rounded-xl shadow-xl px-8 py-8">
            {/* 标题 */}
            <div className="font-[600] text-xl">
              {activeTab === 'login' && t('auth.login.title')}
              {activeTab === 'register' && t('auth.register.title')}
              {activeTab === 'forgot' && t('auth.forgotPassword.title')}
            </div>

            {activeTab === 'login' && currentEmail && (
              <div className="text-sm">
                {remainingAttempts === 0 || isAccountLocked ? (
                  <p className="text-red-600 font-medium">
                    {t('auth.login.lockedMessage', {
                      time: lockCountdown > 0 ? formatCountdown(lockCountdown) : '00:30:00',
                    })}
                  </p>
                ) : remainingAttempts !== MAX_ATTEMPT_NUM ? (
                  <p className="text-gray-500">{t('auth.login.remainingAttempts', { count: remainingAttempts })}</p>
                ) : null}
              </div>
            )}

            {/* 通用错误提示 - 注册/忘记密码场景显示 */}
            {commonError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-600">{commonError}</p>
              </div>
            )}

            {/* 表单区域 */}
            <form className="space-y-6 flex-1" onSubmit={handleSubmit(onFormSubmit)}>
              {/* 邮箱输入框（所有界面都有） */}
              <div>
                <input
                  {...register('username', {
                    required: t('auth.login.usernamePlaceholder'),
                    maxLength: {
                      value: 50,
                      message: t('auth.common.maxEmailLength'),
                    },
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: t('auth.common.invalidEmailFormat'),
                    },
                  })}
                  maxLength={50}
                  type="email"
                  id="email"
                  className={inputFieldClass}
                  placeholder={t('auth.login.usernamePlaceholder')}
                />
                <p className="mt-1 text-sm text-red-600">{errors.username?.message}</p>
              </div>

              {/* 密码输入框 - 登录/注册显示密码，忘记密码显示新密码 */}
              <div>
                <input
                  {...register(activeTab === 'forgot' ? 'newPassword' : 'password', {
                    required:
                      activeTab === 'login'
                        ? t('auth.login.passwordPlaceholder')
                        : activeTab === 'register'
                          ? t('auth.register.passwordPlaceholder')
                          : t('auth.forgotPassword.newPasswordPlaceholder'),
                    minLength: {
                      value: PASSWORD_MIN_LENGTH,
                      message: t('auth.common.minPasswordLength'),
                    },
                    maxLength: {
                      value: PASSWORD_MAX_LENGTH,
                      message: t('auth.common.maxPasswordLength'),
                    },
                    validate: validatePasswordStrength,
                  })}
                  type="password"
                  id={activeTab === 'forgot' ? 'newPassword' : 'password'}
                  className={inputFieldClass}
                  placeholder={
                    activeTab === 'login'
                      ? t('auth.login.passwordPlaceholder')
                      : activeTab === 'register'
                        ? t('auth.register.passwordPlaceholder')
                        : t('auth.forgotPassword.newPasswordPlaceholder')
                  }
                />
                <p className="mt-1 text-sm text-red-600">{errors.password?.message || errors.newPassword?.message}</p>
              </div>

              {activeTab === 'register' && (
                <div>
                  <input
                    {...register('confirmPassword', {
                      required: t('auth.register.confirmPasswordRequired'),
                      minLength: {
                        value: PASSWORD_MIN_LENGTH,
                        message: t('auth.common.minPasswordLength'),
                      },
                      maxLength: {
                        value: PASSWORD_MAX_LENGTH,
                        message: t('auth.common.maxPasswordLength'),
                      },
                      validate: value =>
                        value === getValues('password') || t('auth.register.passwordsNotMatch'),
                    })}
                    type="password"
                    id="confirmPassword"
                    className={inputFieldClass}
                    placeholder={t('auth.register.confirmPasswordPlaceholder')}
                  />
                  <p className="mt-1 text-sm text-red-600">{errors.confirmPassword?.message}</p>
                </div>
              )}

              {/* 验证码输入框 - 注册/忘记密码显示 */}
              {(activeTab === 'register' || activeTab === 'forgot') && (
                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      {...register('verifyCode', {
                        required: t(activeTab === 'register' ? 'auth.register.verificationCodePlaceholder' : 'auth.forgotPassword.verificationCodePlaceholder'),
                        pattern: {
                          value: /^\d{6}$/,
                          message: t('auth.common.invalidCode'),
                        },
                      })}
                      type="text"
                      id="verifyCode"
                      className={inputFieldClass}
                      placeholder={
                        activeTab === 'register' ? t('auth.register.verificationCodePlaceholder') : t('auth.forgotPassword.verificationCodePlaceholder')
                      }
                    />
                    <p className="mt-1 text-sm text-red-600">{errors.verifyCode?.message}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (activeTab === 'forgot') {
                        handleForgotPassword()
                      } else if (activeTab === 'register') {
                        handleGetVerifyCode()
                      }
                    }}
                    disabled={isVerifyCodeBtnDisabled()}
                    className="whitespace-nowrap px-4 py-3 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCountdownActive ? `${countdown}s` : t('auth.register.getVerificationCode')}
                  </button>
                </div>
              )}
              {/* reset password 成功提示 */}
              {successMsg && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-600">{successMsg}</p>
                </div>
              )}
              {/* 锁定时不显示登录错误 */}
              {!isAccountLocked && remainingAttempts !== 0 && loginError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-600">{loginError}</p>
                </div>
              )}

              {/* 移除根错误的显示条件限制，只在登录场景显示 */}
              {activeTab === 'login' && !isAccountLocked && remainingAttempts !== 0 && errors.root && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-600">{errors.root.message}</p>
                </div>
              )}

              {/* 提交按钮 */}
              <div>
                <button
                  type="submit"
                  disabled={(activeTab === 'login' && isAccountLocked) || !isDirty || (activeTab !== 'login' && !getValues('verifyCode'))}
                  className={btnPrimaryClass}
                >
                  {activeTab === 'login' && t('auth.login.loginButton')}
                  {activeTab === 'register' && t('auth.register.submit')}
                  {activeTab === 'forgot' && t('auth.forgotPassword.submit')}
                </button>
              </div>
            </form>

            {/* 底部链接 */}
            <div className="flex flex-col space-y-2 text-center">
              {/* 忘记密码链接 - 仅登录界面显示 */}
              {activeTab === 'login' && (
                <span
                  className={linkClass}
                  onClick={() => {
                    reset()
                    setActiveTab('forgot')
                  }}
                >
                  {t('auth.login.forgotPassword')}
                </span>
              )}

              {/* 切换登录/注册链接 */}
              <span>
                {activeTab === 'login' && (
                  <>
                    {t('auth.login.registerLink')}{' '}
                    <span
                      className={linkClass}
                      onClick={() => {
                        reset()
                        setActiveTab('register')
                      }}
                    >
                      {t('auth.register.registerNow')}
                    </span>
                  </>
                )}
                {activeTab === 'register' && (
                  <>
                    <span
                      className={linkClass}
                      onClick={() => {
                        reset()
                        setActiveTab('login')
                      }}
                    >
                      {t('auth.register.loginLink')}{' '}
                    </span>
                  </>
                )}
                {activeTab === 'forgot' && (
                  <span
                    className={linkClass}
                    onClick={() => {
                      reset()
                      setActiveTab('login')
                    }}
                  >
                    {t('auth.forgotPassword.loginLink')}
                  </span>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
export default UserLoginPage