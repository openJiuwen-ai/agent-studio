/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

export interface HttpRetryConfig {
  enabled: boolean
  maxRetries: number
  retryOnStatusCodes: number[]
  retryDelayMs: number
  backoffType: 'fixed' | 'linear' | 'exponential'
}

export interface HttpRateLimitConfig {
  enabled: boolean
  requestsPerUnit: number
  unit: 'second' | 'minute' | 'hour'
}

export interface HttpAuthenticationConfig {
  authType: 'none' | 'basic' | 'bearer' | 'api_key'
  username?: string
  password?: string
  token?: string
  apiKey?: string
  apiKeyLocation?: 'header' | 'query' | 'body'
  apiKeyParamName?: string
}

export interface HttpBodyConfig {
  contentType: 'application/json' | 'application/x-www-form-urlencoded' | 'multipart/form-data' | 'text/plain' | 'application/octet-stream'
  content?: any
}

export interface HttpResponseConfig {
  responseFormat: 'auto' | 'json' | 'text' | 'binary'
  successStatusCodes: number[]
  failureStatusCodes: number[]
  responseMode: 'full' | 'on-success' | 'on-error'
  dataProperty?: string
}

export interface HttpAdvancedConfig {
  followRedirects: boolean
  ignoreSslIssues: boolean
  proxyUrl?: string
  timeout: number
  retry: HttpRetryConfig
  rateLimit: HttpRateLimitConfig
}

export interface HttpRequestParam {
  url: any  // BaseValue type
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS'
  headers?: Record<string, any>  // key-value pairs
  queryParams?: Record<string, any>  // key-value pairs
  body?: HttpBodyConfig
  auth: HttpAuthenticationConfig
  response: HttpResponseConfig
  advanced: HttpAdvancedConfig
}

export interface HttpRequestNodeData {
  title: string
  inputs: {
    httpRequestParam: HttpRequestParam
    inputParameters?: Record<string, any>
  }
  outputs: {
    type: 'object'
    properties: {
      statusCode: { type: 'integer'; description: string }
      headers: { type: 'object'; description: string }
      body: { type: 'string'; description: string }
      url: { type: 'string'; description: string }
      ok: { type: 'boolean'; description: string }
    }
    required: string[]
  }
  exceptionConfig: {
    retryTimes: number
    timeoutSeconds: number
    processType: 'break' | 'return_content' | 'execute_exception_step'
    returnContent?: Record<string, any>
    executeStep?: {
      defaultStep: string
      errorStep: string
    }
  }
}
