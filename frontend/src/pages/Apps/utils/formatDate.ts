/**
 * 日期格式化工具函数
 *
 * @description
 * 提供日期格式化和相对时间计算功能
 * 支持错误处理、时区感知、可访问性和国际化
 */

/**
 * 时间单位配置（用于相对时间计算）
 */
const TIME_UNITS = {
  minute: 60,
  hour: 60 * 60,
  day: 60 * 60 * 24,
  week: 60 * 60 * 24 * 7,
  month: 60 * 60 * 24 * 30,
  year: 60 * 60 * 24 * 365,
} as const

/**
 * 相对时间标签键
 */
const RELATIVE_TIME_LABEL_KEYS = {
  just_now: 'justNow',
  seconds: 'secondsAgo',
  minutes: 'minutesAgo',
  hours: 'hoursAgo',
  days: 'daysAgo',
  weeks: 'weeksAgo',
  months: 'monthsAgo',
  years: 'yearsAgo',
} as const

/**
 * 验证日期字符串是否有效
 * @param value 待验证的值
 * @returns 是否为有效的日期字符串
 */
function isValidDateString(value: unknown): value is string {
  if (typeof value !== 'string' || !value.trim()) return false

  const date = new Date(value)
  return !isNaN(date.getTime())
}

/**
 * 格式化报告创建时间（紧凑格式，国际化）
 * @param isoString ISO 格式的时间字符串
 * @param locale 区域设置 (如 'zh-CN', 'en-US')
 * @returns 格式化后的时间字符串 (如 "1月6日 19:30" 或 "Jan 6, 19:30")
 *
 * @example
 * formatReportDate("2025-01-06T19:30:45Z", 'zh-CN') // "1月6日 19:30"
 * formatReportDate("2025-01-06T19:30:45Z", 'en-US') // "Jan 6, 19:30"
 */
export function formatReportDate(isoString: string, locale: string = 'zh-CN'): string {
  if (!isValidDateString(isoString)) {
    console.warn('[formatReportDate] Invalid date string:', isoString)
    // Return a marker that will be translated by the caller
    return '__UNKNOWN_TIME__'
  }

  const date = new Date(isoString)
  return date.toLocaleString(locale, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * 格式化完整日期时间（国际化）
 * @param isoString ISO 格式的时间字符串
 * @param locale 区域设置 (如 'zh-CN', 'en-US')
 * @returns 格式化后的完整时间字符串
 *
 * @example
 * formatFullDateTime("2025-01-06T19:30:45Z", 'zh-CN') // "2025年1月6日 19:30:45"
 * formatFullDateTime("2025-01-06T19:30:45Z", 'en-US') // "January 6, 2025, 7:30:45 PM"
 */
export function formatFullDateTime(isoString: string, locale: string = 'zh-CN'): string {
  if (!isValidDateString(isoString)) {
    console.warn('[formatFullDateTime] Invalid date string:', isoString)
    return '__UNKNOWN_TIME__'
  }

  const date = new Date(isoString)
  return date.toLocaleString(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 获取相对时间描述（国际化版本）
 * @param isoString ISO 格式的时间字符串
 * @param t 翻译函数
 * @param locale 区域设置 (如 'zh-CN', 'en-US')
 * @returns 相对时间字符串
 *
 * @example
 * getRelativeTime("2025-01-06T19:30:45Z", t, 'zh-CN') // "5分钟前"
 * getRelativeTime("2025-01-06T19:30:45Z", t, 'en-US') // "5m ago"
 *
 * @accessibility
 * 返回的相对时间应该配合 datetime 属性使用：
 * <time datetime="2025-01-06T19:30:45Z">5分钟前</time>
 */
export function getRelativeTime(isoString: string, t: (key: string) => string, locale: string = 'zh-CN'): string {
  if (!isValidDateString(isoString)) {
    console.warn('[getRelativeTime] Invalid date string:', isoString)
    return t('apps.time.unknown')
  }

  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)

  // 处理未来时间（时钟偏差）
  if (diffSecs < 0) {
    return formatReportDate(isoString, locale)
  }

  // 刚刚（1分钟内）
  if (diffSecs < TIME_UNITS.minute) {
    return t(`apps.time.${RELATIVE_TIME_LABEL_KEYS.just_now}`)
  }

  // 分钟
  if (diffSecs < TIME_UNITS.hour) {
    const mins = Math.floor(diffSecs / TIME_UNITS.minute)
    return `${mins}${t(`apps.time.${RELATIVE_TIME_LABEL_KEYS.minutes}`)}`
  }

  // 小时
  if (diffSecs < TIME_UNITS.day) {
    const hours = Math.floor(diffSecs / TIME_UNITS.hour)
    return `${hours}${t(`apps.time.${RELATIVE_TIME_LABEL_KEYS.hours}`)}`
  }

  // 天（7天内）
  if (diffSecs < TIME_UNITS.week) {
    const days = Math.floor(diffSecs / TIME_UNITS.day)
    return `${days}${t(`apps.time.${RELATIVE_TIME_LABEL_KEYS.days}`)}`
  }

  // 超过一周，返回具体日期
  return formatReportDate(isoString, locale)
}

/**
 * 获取带机器可读属性的相对时间（用于可访问性，国际化版本）
 * @param isoString ISO 格式的时间字符串
 * @param t 翻译函数
 * @param locale 区域设置 (如 'zh-CN', 'en-US')
 * @returns 包含显示文本和 datetime 属性的对象
 *
 * @example
 * const { displayText, datetime } = getAccessibleRelativeTime("2025-01-06T19:30:45Z", t, 'zh-CN')
 * // { displayText: "5分钟前", datetime: "2025-01-06T19:30:45.000Z" }
 *
 * // 在 React 中使用：
 * <time dateTime={datetime} aria-label={datetime}>{displayText}</time>
 */
export function getAccessibleRelativeTime(isoString: string, t: (key: string) => string, locale: string = 'zh-CN'): {
  displayText: string
  datetime: string
} {
  if (!isValidDateString(isoString)) {
    return { displayText: t('apps.time.unknown'), datetime: '' }
  }

  return {
    displayText: getRelativeTime(isoString, t, locale),
    datetime: new Date(isoString).toISOString(),
  }
}

/**
 * 检查日期是否为今天
 * @param isoString ISO 格式的时间字符串
 * @returns 是否为今天
 */
export function isToday(isoString: string): boolean {
  if (!isValidDateString(isoString)) return false

  const date = new Date(isoString)
  const today = new Date()

  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  )
}

/**
 * 检查日期是否为本周
 * @param isoString ISO 格式的时间字符串
 * @returns 是否为本周
 */
export function isThisWeek(isoString: string): boolean {
  if (!isValidDateString(isoString)) return false

  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / TIME_UNITS.day)

  return diffDays >= 0 && diffDays < 7
}
