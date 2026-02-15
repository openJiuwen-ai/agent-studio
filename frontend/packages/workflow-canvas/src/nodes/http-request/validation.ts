/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

/**
 * Validate URL format
 */
export const validateUrl = (url: string): string | null => {
  if (!url || url.trim() === '') {
    return 'URL is required'
  }

  // Allow variable placeholders like {{variable}}
  const hasVariables = /\{\{[^}]+\}\}/.test(url)
  if (hasVariables) {
    return null // Valid if it contains variables
  }

  // Basic URL validation
  try {
    const urlObj = new URL(url)
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return 'URL must use HTTP or HTTPS protocol'
    }
    return null
  } catch {
    return 'Invalid URL format'
  }
}

/**
 * Validate authentication configuration
 */
export const validateAuth = (auth: any): string | null => {
  if (auth.authType === 'basic') {
    if (!auth.username) {
      return 'Username is required for Basic authentication'
    }
    if (!auth.password) {
      return 'Password is required for Basic authentication'
    }
  } else if (auth.authType === 'bearer') {
    if (!auth.token) {
      return 'Token is required for Bearer authentication'
    }
  } else if (auth.authType === 'api_key') {
    if (!auth.apiKey) {
      return 'API Key is required for API Key authentication'
    }
    if (!auth.apiKeyParamName) {
      return 'Parameter name is required for API Key authentication'
    }
  }
  return null
}

/**
 * Validate retry configuration
 */
export const validateRetry = (retry: any): string | null => {
  if (retry.enabled) {
    if (retry.maxRetries < 0 || retry.maxRetries > 10) {
      return 'Max retries must be between 0 and 10'
    }
    if (retry.retryDelayMs < 0) {
      return 'Retry delay must be a positive number'
    }
  }
  return null
}

/**
 * Validate rate limit configuration
 */
export const validateRateLimit = (rateLimit: any): string | null => {
  if (rateLimit.enabled) {
    if (rateLimit.requestsPerUnit <= 0) {
      return 'Requests per unit must be greater than 0'
    }
  }
  return null
}

/**
 * Validate timeout
 */
export const validateTimeout = (timeout: number): string | null => {
  if (timeout < 1 || timeout > 300) {
    return 'Timeout must be between 1 and 300 seconds'
  }
  return null
}

/**
 * Validate HTTP method for body
 */
export const validateMethodForBody = (method: string, hasBody: boolean): string | null => {
  const methodsWithoutBody = ['GET', 'HEAD', 'OPTIONS']
  if (methodsWithoutBody.includes(method) && hasBody) {
    return `${method} requests should not have a body`
  }
  return null
}
