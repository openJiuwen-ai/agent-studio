/**
 * 用户偏好检测 Hooks
 *
 * @description
 * 提供跨组件共享的用户偏好检测功能
 * - 动画偏好检测
 * - 媒体查询监听
 * - 移动端检测
 */

import { useMemo, useState, useEffect } from 'react'

/**
 * 检测用户是否偏好减少动画
 * @returns 是否偏好减少动画
 */
export function useReducedMotion(): boolean {
  return useMemo(() => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])
}

/**
 * 监听媒体查询变化
 * @param query - 媒体查询字符串
 * @returns 是否匹配媒体查询
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    window.matchMedia(query).matches
  )

  useEffect(() => {
    const mediaQuery = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)

    // 现代浏览器使用 addEventListener
    mediaQuery.addEventListener('change', handler)

    return () => {
      mediaQuery.removeEventListener('change', handler)
    }
  }, [query])

  return matches
}

/**
 * 检测是否为移动端设备
 * @param breakpoint - 断点宽度 (默认 768px)
 * @returns 是否为移动端
 */
export function useIsMobile(breakpoint: number = 768): boolean {
  return useMediaQuery(`(max-width: ${breakpoint}px)`)
}