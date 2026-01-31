import { ENV_CONFIG } from '@/config/environment.ts'

const LOGIN_PAGE_WITHOUT_PWD = '/login' as const
const LOGIN_PAGE_WITH_PWD = '/user_login' as const

export const getLoginPagePath = () => {
  const enable_pwd = ENV_CONFIG.VITE_ENABLE_NEW_AUTH
  return enable_pwd ? LOGIN_PAGE_WITH_PWD : LOGIN_PAGE_WITHOUT_PWD
}
