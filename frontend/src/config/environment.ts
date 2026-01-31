/// <reference types="vite/client" />

// Environment Configuration with Vite integration
console.log('环境变量:', import.meta.env.VITE_API_BASE_URL, import.meta.env.VITE_PLUGIN_SERVICE_URL)
export const ENV_CONFIG = {
  // API Configuration
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  API_TIMEOUT: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  API_MAX_RETRIES: parseInt(import.meta.env.VITE_API_MAX_RETRIES || '3'),

  // Workflow Service Configuration
  DEFAULT_SPACE_ID: import.meta.env.VITE_DEFAULT_SPACE_ID || '0',
  DEFAULT_USER_ID: 'demo_user_id',

  // Prompt Configuration
  DEFAULT_PROMPT_VERSION: '0.0.1',

  // Development Configuration
  IS_DEV: import.meta.env.DEV || import.meta.env.VITE_IS_DEV === 'true',
  IS_PROD: import.meta.env.PROD || import.meta.env.VITE_IS_PROD === 'true',
  IS_TEST: import.meta.env.VITE_IS_TEST === 'true',

  // Vite built-in environment variables
  MODE: import.meta.env.MODE,
  BASE_URL: import.meta.env.BASE_URL,
  APP_VERSION: import.meta.env.__APP_VERSION__,
  BUILD_TIME: import.meta.env.__BUILD_TIME__,

  // Plugin Service Configuration
  PLUGIN_SERVICE_URL: import.meta.env.VITE_PLUGIN_SERVICE_URL || '',
  PLUGIN_CONFIG_PATH: import.meta.env.VITE_PLUGIN_CONFIG_PATH || '/config.json',

  // Login Page Configuration
  VITE_ENABLE_NEW_AUTH: import.meta.env.VITE_ENABLE_NEW_AUTH === 'True',
}
