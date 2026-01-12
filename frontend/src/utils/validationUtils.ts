/**
 * 工具路径校验函数
 */

/**
 * 校验工具路径是否符合规范
 * 规则：必须以"/"开头，且只能包含英文、数字、下划线、连字符和斜杠
 * @param path 待校验的路径
 * @returns 校验结果和错误信息
 */
export const validateToolPath = (path: string): { isValid: boolean; error: string } => {
  // 检查是否为空
  if (!path || path.trim() === '') {
    return {
      isValid: false,
      error: '工具路径不能为空',
    }
  }

  // 检查是否以"/"开头
  if (!path.startsWith('/')) {
    return {
      isValid: false,
      error: '工具路径必须以"/"开头',
    }
  }

  // 检查是否以斜杠结尾（除了根路径 "/"）
  if (path.length > 1 && path.endsWith('/')) {
    return {
      isValid: false,
      error: '工具路径不能以斜杠(/)结尾',
    }
  }

  // 检查是否只包含英文、数字、下划线、连字符和斜杠
  const validPathRegex = /^\/[a-zA-Z0-9\-_/]*$/
  if (!validPathRegex.test(path)) {
    return {
      isValid: false,
      error: '工具路径只能包含英文、数字、下划线(_)、连字符(-)和斜杠(/)',
    }
  }

  // 检查是否包含连续的斜杠
  if (path.includes('//')) {
    return {
      isValid: false,
      error: '工具路径不能包含连续的斜杠(//)',
    }
  }

  // 检查路径长度（可选）
  if (path.length > 255) {
    return {
      isValid: false,
      error: '工具路径长度不能超过255个字符',
    }
  }

  return {
    isValid: true,
    error: '',
  }
}

/**
 * 实时校验工具路径（用于输入时的即时反馈）
 * @param path 待校验的路径
 * @returns 错误信息字符串，如果校验通过返回空字符串
 */
export const validateToolPathRealtime = (path: string): string => {
  const result = validateToolPath(path)
  return result.error
}

/**
 * 常见路径示例（用于帮助提示）
 */
export const TOOL_PATH_EXAMPLES = ['/api/users', '/weather/query', '/user/profile', '/data/search', '/v1/auth/login', '/files/upload', '/notifications/send']

/**
 * 生成路径提示信息
 * @returns 路径格式说明
 */
export const getPathHelpText = (): string => {
  return '路径必须以"/"开头，只能包含英文、数字、下划线(_)、连字符(-)和斜杠(/)，例如：/api/users'
}

/**
 * 校验HTTP/HTTPS URL格式
 * @param url 待校验的URL
 * @returns 校验结果和错误信息
 */
export const validateHttpUrl = (url: string): { isValid: boolean; error: string } => {
  // 检查是否为空
  if (!url || url.trim() === '') {
    return {
      isValid: false,
      error: '服务地址不能为空',
    }
  }

  const trimmedUrl = url.trim()

  // 检查是否以http://
  if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
    return {
      isValid: false,
      error: '服务地址必须以http://',
    }
  }

  try {
    // 使用URL构造函数进行基本格式校验
    const urlObj = new URL(trimmedUrl)

    // 检查协议是否为http或https
    if (urlObj.protocol !== 'http:' && urlObj.protocol !== 'https:') {
      return {
        isValid: false,
        error: '仅支持http://和https://协议',
      }
    }

    // 检查域名是否有效
    if (!urlObj.hostname) {
      return {
        isValid: false,
        error: '请输入有效的域名或IP地址',
      }
    }

    // 检查端口号是否有效（如果指定了端口）
    if (urlObj.port && (parseInt(urlObj.port) < 1 || parseInt(urlObj.port) > 65535)) {
      return {
        isValid: false,
        error: '端口号必须在1-65535之间',
      }
    }

    return {
      isValid: true,
      error: '',
    }
  } catch (error) {
    return {
      isValid: false,
      error: '请输入有效的URL格式，例如：http://api.example.com',
    }
  }
}

/**
 * 实时校验HTTP URL（用于输入时的即时反馈）
 * @param url 待校验的URL
 * @returns 错误信息字符串，如果校验通过返回空字符串
 */
export const validateHttpUrlRealtime = (url: string): string => {
  const result = validateHttpUrl(url)
  return result.error
}

/**
 * 生成URL提示信息
 * @returns URL格式说明
 */
export const getHttpUrlHelpText = (): string => {
  return '服务地址必须以http://或https://开头，例如：http://api.example.com'
}
