import React, { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useQueryClient } from 'react-query'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../../stores/useAuthStore'
import { ENV_CONFIG } from '../../config/environment'
import { ArrowLeft, Save, Plus, Trash2, Settings, Code, FileText, RotateCcw, CheckCircle, XCircle, Check } from 'lucide-react'
import { validateToolPath, getPathHelpText } from '../../utils/validationUtils'
import { copyToClipboard } from '../../utils/prompts/utils'
import {
  Card,
  Typography,
  TextField,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  Tabs,
  Tab,
  Chip,
  CircularProgress,
  Switch,
  FormControlLabel,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
} from '@mui/material'
import { ParameterTypeSelector } from './components/ParameterTypeSelector'
import { PythonCodeEditor, TypeScriptCodeEditor } from '../../../packages/workflow-canvas/src/form-materials/components/code-editor'
// Import the base-editor styles for the code editors to work properly
import '../../../packages/workflow-canvas/src/form-materials/components/base-editor/styles.css'
import {
  usePluginUpdateApi,
  usePluginUpdateCode,
  usePluginGetApi,
  usePluginDeleteApi,
  usePluginGetCode,
  usePluginDeleteCode,
  useExecutePlugin,
  usePlugin,
  ParamSendMethod,
  Priority,
} from '@test-agentstudio/api-client'

interface ToolParameter {
  id: string
  name: string
  description: string
  type: string
  method: number
  is_required?: boolean
  is_runtime?: boolean
  value?: string
  priority?: numbe
}

interface HeaderConfig {
  key: string
  value: string
}

interface Tool {
  tool_id: string
  name: string
  description: string
  path?: string
  method?: number
  language?: string
  code?: string
  input_parameters: ToolParameter[]
  output_parameters: ToolParameter[]
  headers: HeaderConfig[]
  available?: boolean
}

type ParameterValue = string | number | boolean | string[] | object | undefined

interface CodeTemplate {
  language: 'javascript' | 'python'
  name: string
  description: string
  template: string
}

const codeTemplates: CodeTemplate[] = [
  {
    language: 'python',
    name: 'Basic Function',
    description: 'Simple data processing function',
    template: `def add_test(a: int, b: int):
  return a + b

def main(args: Args):
  a = args.params['add1']
  b = args.params['add2']
  c = add_test(a, b)

  return {'res': c}`,
  },
  {
    language: 'javascript',
    name: 'Basic Function',
    description: 'Simple data processing function',
    template: `function main() {
  /**
   * 主要处理函数
   */
  // 在这里编写您的JavaScript代码
  const result = {
    message: "Hello World!",
    status: "success",
    timestamp: new Date().toISOString()
  };

  return result;
}

// 导出主函数
module.exports = { main };

// 如果直接运行此文件
if (require.main === module) {
  console.log(main());
}`,
  },
]

interface TestExecutionResult {
  timestamp: string
  execution_success: boolean
  error_code: number | null
  error_message: string | null
  output: unknown
  raw_response: unknown
  parse_error?: string
  raw_buffer?: string
}

const ToolConfigurationPage: React.FC = () => {
  const { t } = useTranslation()
  const { plugin_id, tool_id } = useParams<{ plugin_id: string; tool_id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const [tool, setTool] = useState<Tool | null>(null)
  const [tabValue, setTabValue] = useState('basic')
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error' | 'info' | 'warning',
  })
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [testResults, setTestResults] = useState('')
  const [testError, setTestError] = useState('')
  const [testParameters, setTestParameters] = useState<Record<string, string>>({})
  const [testParameterErrors, setTestParameterErrors] = useState<Record<string, string>>({})
  const [isTestRunning, setIsTestRunning] = useState(false)
  // Code editor state for code tools
  const [codeLanguage, setCodeLanguage] = useState<'javascript' | 'python'>('python')
  const [codeContent, setCodeContent] = useState('')
  // Path validation state
  const [pathError, setPathError] = useState<string>('')
  // Template state
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [showTemplates, setShowTemplates] = useState(false)

  // Get plugin type and navigation info from URL params or state
  const urlParams = new URLSearchParams(location.search)
  const source = location.state?.source || urlParams.get('source')
  const agentId = location.state?.agentId || urlParams.get('agentId')
  const pluginType = location.state?.pluginType || 'api'
  const fromPublishVersion = location.state?.fromPublishVersion || false
  const publishVersion = location.state?.publishVersion || null
  const toolsData = location.state?.toolsData || null // Tools data from publish info
  const isReadOnly = fromPublishVersion // Disable editing when from published version

  // Parameter dialogs
  const [isInputDialogOpen, setIsInputDialogOpen] = useState(false)
  const [isOutputDialogOpen, setIsOutputDialogOpen] = useState(false)
  const [editingParameter, setEditingParameter] = useState<ToolParameter | null>(null)
  const [parameterForm, setParameterForm] = useState({
    name: '',
    description: '',
    type: 'string',
    method: ParamSendMethod.NONE,
    is_required: false,
    is_runtime: true,
    value: '',
    priority: Priority.TOOL,
  })
  const { user } = useAuthStore()
  const queryClient = useQueryClient()

  // Space ID calculation
  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }
  const spaceId = location.state?.spaceId || urlParams.get('spaceId') || getDefaultSpaceId()

  const updatePluginApiMutation = pluginType === 'code' ? usePluginUpdateCode() : usePluginUpdateApi()
  const deletePluginApiMutation = pluginType === 'code' ? usePluginDeleteCode() : usePluginDeleteApi()
  const executePluginMutation = useExecutePlugin()

  // Setup API request for fetching tool data
  const apiRequest =
    plugin_id && tool_id
      ? {
          space_id: spaceId,
          plugin_id,
          tool_id,
          plugin_version: undefined,
        }
      : null

  // Create mock API data from toolsData when available (from publish version)
  // Use useMemo to prevent creating new object on every render
  const mockApiData = useMemo(() => {
    if (!toolsData || !Array.isArray(toolsData)) {
      return null
    }

    const targetTool = toolsData.find(tool => tool.tool_id === tool_id)
    if (!targetTool) {
      return null
    }

    const dataKey = pluginType === 'code' ? 'code_info' : 'api_info'

    return {
      code: 200,
      data: {
        [dataKey]: [targetTool],
        total: 1,
      },
    }
  }, [toolsData, tool_id, pluginType])

  // Use different API hooks based on plugin type, but skip if we have toolsData
  const shouldFetchApi = !toolsData && !!apiRequest
  const { data: apiData, isLoading: isLoadingApi, error: apiError } = pluginType === 'code'
    ? usePluginGetCode(shouldFetchApi ? apiRequest! : ({} as any), { enabled: shouldFetchApi })
    : usePluginGetApi(shouldFetchApi ? apiRequest! : ({} as any), { enabled: shouldFetchApi })

  // Use mock data if available, otherwise use API data
  const effectiveApiData = mockApiData || apiData

  // Fetch plugin info to get plugin-level request_params
  const pluginGetRequest =
    plugin_id && spaceId
      ? {
          space_id: spaceId,
          plugin_id,
          plugin_version: undefined,
        }
      : null
  const { data: pluginData } = usePlugin(pluginGetRequest!)

  // Transform API data to Tool interface when data is loaded
  useEffect(() => {
    const dataKey = pluginType === 'code' ? 'code_info' : 'api_info'

    if (effectiveApiData?.code === 200 && effectiveApiData?.data?.[dataKey] && Array.isArray(effectiveApiData.data[dataKey])) {
      const infoArray = effectiveApiData.data[dataKey]

      // Find the specific API info by tool_id from the URL parameters
      const targetApiInfo = infoArray.find(info => info.tool_id === tool_id)

      if (!targetApiInfo) {
        setSnackbar({
          open: true,
          message: t('plugins.toolConfig.notFound', '未找到ID为 {{toolId}} 的工具配置', { toolId: tool_id }),
          severity: 'error',
        })
        return
      }

      // Transform API response to Tool interface
      const transformedTool: Tool = {
        tool_id: targetApiInfo.tool_id,
        name: targetApiInfo.name || '未命名工具',
        description: targetApiInfo.desc || t('plugins.toolConfig.noDescription'),
        ...(pluginType === 'code'
          ? {
              language: targetApiInfo.language || 'python',
              code: targetApiInfo.code || '',
            }
          : {
              path: targetApiInfo.path || '',
              method: targetApiInfo.method || 1,
            }),
        input_parameters:
          targetApiInfo.request_params?.map(param => ({
            id: Math.random().toString(36).substr(2, 9),
            name: param.name,
            description: param.desc || '',
            type: mapNumberToString(param.type),
            method: param.method ?? ParamSendMethod.NONE,
            is_required: param.is_required,
            is_runtime: param.is_runtime,
            value: param.value || '',
            priority: param.priority ?? Priority.TOOL,
          })) || [],
        output_parameters:
          targetApiInfo.response_params?.map(param => ({
            id: Math.random().toString(36).substr(2, 9),
            name: param.name,
            description: param.desc || '',
            type: mapNumberToString(param.type),
          })) || [],
        headers:
          targetApiInfo.headers?.map(header => ({
            key: header.name,
            value: header.value,
          })) || [],
        available: targetApiInfo.available,
      }

      setTool(transformedTool)

      // Initialize code editor state for code tools
      if (pluginType === 'code') {
        setCodeLanguage((transformedTool.language as 'javascript' | 'python') || 'python')
        setCodeContent(transformedTool.code || '')
      }
    } else if (effectiveApiData && effectiveApiData?.code !== 200) {
      // API returned an error
      setSnackbar({
        open: true,
        message: `${t('plugins.config.loadFailed', '加载工具配置失败：{{message}}')}: ${effectiveApiData?.message || t('plugins.errors.unknownError', '未知错误')}`,
        severity: 'error',
      })
    } else if (effectiveApiData && (!effectiveApiData?.data?.[dataKey] || !Array.isArray(effectiveApiData.data[dataKey]))) {
      // API returned success but no valid data
      setSnackbar({
        open: true,
        message: t('plugins.toolConfig.pluginDataNotLoaded', '工具配置数据为空或格式错误，请检查工具是否存在'),
        severity: 'warning',
      })
    }
  // Use stable dependencies: only re-run when data content actually changes
  }, [mockApiData !== null ? JSON.stringify(mockApiData) : apiData, tool_id, pluginType, t])

  // Handle API errors
  useEffect(() => {
    if (apiError) {
      console.error(t('plugins.toolConfig.loadFailed', '获取工具配置失败'), apiError)
      setSnackbar({
        open: true,
        message: t('plugins.toolConfig.loadFailedRetry', '获取工具配置失败，请稍后重试'),
        severity: 'error',
      })
    }
  }, [apiError])

  const getMethodString = (methodNumber: number): string => {
    const methodMap: Record<number, string> = {
      1: 'GET',
      2: 'POST',
      3: 'PUT',
      4: 'DELETE',
      5: 'PATCH',
    }
    return methodMap[methodNumber] || 'UNKNOWN'
  }

  const mapTypeToNumber = (type: string): number => {
    const typeMap: Record<string, number> = {
      string: 1,
      int: 2,
      float: 3,
      boolean: 4,
      object: 5,
      array_string: 6,
      array_int: 7,
      array_float: 8,
      array_boolean: 9,
      // Legacy support for old generic types
      number: 2, // Default to int for backward compatibility
      array: 6, // Default to string array for backward compatibility
    }
    return typeMap[type] || 1
  }

  const mapNumberToString = (typeNumber: number): string => {
    const typeMap: Record<number, string> = {
      1: 'string',
      2: 'int',
      3: 'float',
      4: 'boolean',
      5: 'object',
      6: 'array_string',
      7: 'array_int',
      8: 'array_float',
      9: 'array_boolean',
    }
    return typeMap[typeNumber] || 'string'
  }

  const convertParameterToCorrectType = (value: string, type: string): ParameterValue => {
    if (value === '' || value === null || value === undefined) {
      return undefined
    }

    switch (type) {
      case 'int': {
        const intValue = parseInt(value, 10)
        return isNaN(intValue) ? 0 : intValue
      }
      case 'float': {
        const floatValue = parseFloat(value)
        return isNaN(floatValue) ? 0.0 : floatValue
      }
      case 'number': {
        // Legacy support - treat as float
        const numValue = parseFloat(value)
        return isNaN(numValue) ? 0 : numValue
      }
      case 'boolean':
        return value.toLowerCase() === 'true' || value === '1'
      case 'array_string':
      case 'array_int':
      case 'array_float':
      case 'array_boolean':
      case 'array': {
        // Legacy 'array' support - treat as string array
        try {
          return JSON.parse(value)
        } catch {
          return value
            .split(',')
            .map(item => item.trim())
            .filter(item => item.length > 0)
        }
      }
      case 'object':
        try {
          return JSON.parse(value)
        } catch {
          return { raw: value }
        }
      case 'string':
      default:
        return value
    }
  }

  const getTypedTestParameters = (): Record<string, ParameterValue> => {
    const typedParameters: Record<string, ParameterValue> = {}

    // Get tool parameter names to filter out plugin parameters with the same name
    const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])

    // First, add plugin-level parameters with their default values if not provided
    // Exclude plugin parameters that have the same name as tool parameters
    if (pluginData?.data?.plugin_info?.request_params) {
      pluginData.data.plugin_info.request_params.forEach(param => {
        // Skip this plugin parameter if there's a tool parameter with the same name
        if (toolParamNames.has(param.name)) {
          return
        }

        // 如果是非运行时参数(is_runtime为false)，使用默认值；否则使用用户输入或默认值
        const stringValue = param.is_runtime === false ? param.value || '' : testParameters[`plugin_${param.name}`] || param.value || ''
        const typeString = typeof param.type === 'number' ? mapNumberToString(param.type) : param.type
        typedParameters[param.name] = convertParameterToCorrectType(stringValue, typeString)
      })
    }

    // Then, add tool-level parameters (which will override plugin params with same name if any)
    if (tool?.input_parameters) {
      tool.input_parameters.forEach(param => {
        // 如果是非运行时参数(is_runtime为false)，使用默认值；否则使用用户输入
        const stringValue = param.is_runtime === false ? param.value || '' : testParameters[`tool_${param.name}`] || ''
        typedParameters[param.name] = convertParameterToCorrectType(stringValue, param.type)
      })
    }

    return typedParameters
  }

  const extractOutputParameterValues = (testResults: TestExecutionResult): Record<string, unknown> => {
    const outputValues: Record<string, unknown> = {}

    if (!tool?.output_parameters || !testResults.output) {
      return outputValues
    }

    // Try to extract from results.output first, then from raw_response if needed
    const sourceData = testResults.output || testResults.raw_response

    if (typeof sourceData !== 'object' || sourceData === null) {
      return outputValues
    }

    // For each configured output parameter, extract the value from the test results
    tool.output_parameters.forEach(param => {
      const paramName = param.name
      let value: unknown = null

      // Try to get the value using the parameter name
      if (sourceData && typeof sourceData === 'object' && paramName in sourceData) {
        value = (sourceData as Record<string, unknown>)[paramName]
      } else {
        // Try nested path extraction for complex objects
        value = extractNestedValue(sourceData, paramName)
      }

      outputValues[paramName] = value
    })

    return outputValues
  }

  const extractNestedValue = (obj: unknown, path: string): unknown => {
    if (typeof obj !== 'object' || obj === null) {
      return null
    }

    // Try direct property access first
    if (path in (obj as Record<string, unknown>)) {
      return (obj as Record<string, unknown>)[path]
    }

    // Try dot notation for nested paths
    const pathParts = path.split('.')
    let current: unknown = obj

    for (const part of pathParts) {
      if (typeof current !== 'object' || current === null || !(part in (current as Record<string, unknown>))) {
        return null
      }
      current = (current as Record<string, unknown>)[part]
    }

    return current
  }

  const formatOutputValue = (value: unknown, paramType: string): string => {
    if (value === null || value === undefined) {
      return 'undefined'
    }

    switch (paramType) {
      case 'string':
        return String(value)
      case 'number':
        return typeof value === 'number' ? value.toString() : 'invalid number'
      case 'boolean':
        return typeof value === 'boolean' ? value.toString() : 'invalid boolean'
      case 'array':
        try {
          return JSON.stringify(value, null, 2)
        } catch {
          return t('plugins.toolConfig.arrayParseError', 'array parse error')
        }
      case 'object':
        try {
          return JSON.stringify(value, null, 2)
        } catch {
          return t('plugins.toolConfig.objectParseError', 'object parse error')
        }
      default:
        return String(value)
    }
  }

  // 校验路径
  const validatePath = (path: string) => {
    const validation = validateToolPath(path)
    setPathError(validation.error)
    return validation.isValid
  }

  // 处理路径变化
  const handlePathChange = (path: string) => {
    if (tool) {
      const updatedTool = { ...tool, path }
      setTool(updatedTool)

      // 校验路径
      if (path.trim()) {
        validatePath(path)
      } else {
        setPathError('')
      }
    }
  }

  const getMethodLabel = (method: string | number): string => {
    const methodNum = typeof method === 'string' ? parseInt(method) : method
    switch (methodNum) {
      case 0:
        return 'None'
      case 1:
        return 'Header'
      case 2:
        return 'Query'
      case 3:
        return 'Body'
      default:
        return 'None'
    }
  }

  const convertToolToApiRequest = (tool: Tool) => {
    const convertParams = (params: ToolParameter[]) =>
      params.map(param => ({
        name: param.name,
        desc: param.description,
        type: mapTypeToNumber(param.type),
        is_required: param.is_required ?? false,
        value: param.value || '',
        is_runtime: param.is_runtime ?? false,
        method: parseInt(param.method) || ParamSendMethod.NONE,
        priority: Priority.TOOL,
      }))

    if (pluginType === 'code') {
      return {
        space_id: getDefaultSpaceId(),
        plugin_id: plugin_id || '',
        tool_id: tool.tool_id,
        name: tool.name,
        desc: tool.description,
        language: tool.language || 'python',
        code: tool.code || '',
        plugin_version: '',
        request_params: convertParams(tool.input_parameters),
        response_params: convertParams(tool.output_parameters),
        headers: tool.headers
          .filter(header => header.key.trim() !== '' || header.value.trim() !== '')
          .map(header => ({
            name: header.key,
            value: header.value,
          })),
      }
    } else {
      return {
        space_id: getDefaultSpaceId(),
        plugin_id: plugin_id || '',
        tool_id: tool.tool_id,
        name: tool.name,
        desc: tool.description,
        path: tool.path,
        method: tool.method,
        plugin_version: '',
        request_params: convertParams(tool.input_parameters),
        response_params: convertParams(tool.output_parameters),
        headers: tool.headers
          .filter(header => header.key.trim() !== '' || header.value.trim() !== '')
          .map(header => ({
            name: header.key,
            value: header.value,
          })),
      }
    }
  }

  const handleParameterFormChange = (field: keyof typeof parameterForm, value: string | boolean) => {
    setParameterForm(prev => {
      const newState = {
        ...prev,
        [field]: value,
      }
      // When is_runtime is set to true (非运行时参数 unchecked), clear the value
      if (field === 'is_runtime' && value === true) {
        newState.value = ''
      }
      return newState
    })
  }

  const openParameterDialog = (parameter: ToolParameter | null = null, isInput: boolean) => {
    setEditingParameter(parameter)
    if (parameter) {
      setParameterForm({
        name: parameter.name,
        description: parameter.description,
        type: parameter.type,
        method: parameter.method,
        is_required: isInput ? parameter.is_required || false : false,
        is_runtime: isInput ? (pluginType === 'code' ? true : parameter.is_runtime || false) : false,
        value: isInput ? parameter.value || '' : '',
        priority: parameter.priority ?? Priority.TOOL,
      })
    } else {
      setParameterForm({
        name: '',
        description: '',
        type: 'string',
        method: ParamSendMethod.NONE,
        is_required: false,
        is_runtime: true,
        value: '',
        priority: Priority.TOOL,
      })
    }
    if (isInput) {
      setIsInputDialogOpen(true)
    } else {
      setIsOutputDialogOpen(true)
    }
  }

  const handleSaveParameter = async (isInput: boolean) => {
    if (!parameterForm.name.trim() || !parameterForm.description.trim()) {
      setSnackbar({ open: true, message: t('plugins.toolConfig.fillNameAndDescription', '请填写参数名称和描述'), severity: 'error' })
      return
    }

    if (isInput && !parameterForm.is_runtime && !parameterForm.value.trim()) {
      setSnackbar({ open: true, message: t('plugins.toolConfig.nonRuntimeNeedsDefaultValue', '非运行时参数必须设置默认值'), severity: 'error' })
      return
    }

    const newParameter: ToolParameter = {
      id: editingParameter?.id || Date.now().toString(),
      name: parameterForm.name.trim(),
      description: parameterForm.description.trim(),
      type: parameterForm.type,
      method: parameterForm.method,
      is_required: parameterForm.is_required,
      is_runtime: isInput ? (pluginType === 'code' ? true : parameterForm.is_runtime) : undefined,
      value: isInput ? parameterForm.value : undefined,
      priority: isInput ? parameterForm.priority : undefined,
    }

    if (tool) {
      const updatedTool = { ...tool }
      if (isInput) {
        if (editingParameter) {
          updatedTool.input_parameters = updatedTool.input_parameters.map(p => (p.id === editingParameter.id ? newParameter : p))
        } else {
          updatedTool.input_parameters = [...updatedTool.input_parameters, newParameter]
        }
      } else {
        if (editingParameter) {
          updatedTool.output_parameters = updatedTool.output_parameters.map(p => (p.id === editingParameter.id ? newParameter : p))
        } else {
          updatedTool.output_parameters = [...updatedTool.output_parameters, newParameter]
        }
      }
      setTool(updatedTool)

      // 自动调用update_api接口保存参数更改
      try {
        const apiRequest = convertToolToApiRequest(updatedTool)
        console.log(`${t('plugins.toolConfig.autoSaveConfig', '自动保存参数配置')}:`, apiRequest)

        const response = await updatePluginApiMutation.mutateAsync(apiRequest)

        if (response.code === 200) {
          setSnackbar({
            open: true,
            message: editingParameter ? t('plugins.toolConfig.saveSuccess', '参数更新并保存成功') : t('plugins.toolConfig.createSuccess', '参数创建并保存成功'),
            severity: 'success',
          })
          setPathError('') // 清空路径错误
        } else {
          setSnackbar({
            open: true,
            message: editingParameter
              ? t('plugins.toolConfig.saveFailed', '参数更新成功但保存失败: {{message}}', {
                  message: response.message || t('plugins.errors.unknownError', '未知错误'),
                })
              : t('plugins.toolConfig.createFailed', '参数创建成功但保存失败: {{message}}', {
                  message: response.message || t('plugins.errors.unknownError', '未知错误'),
                }),
            severity: 'warning',
          })
        }
      } catch (error: unknown) {
        console.error(`${t('plugins.toolConfig.saveFailedRetry', '保存参数配置失败')}:`, error)
        const errorMessage = error?.response?.data?.message || error?.message || t('plugins.toolConfig.saveFailedRetry', '保存参数配置失败，请稍后重试')
        setSnackbar({
          open: true,
          message: editingParameter
            ? t('plugins.toolConfig.saveFailed', '参数更新成功但保存失败: {{message}}', { message: errorMessage })
            : t('plugins.toolConfig.createFailed', '参数创建成功但保存失败: {{message}}', { message: errorMessage }),
          severity: 'warning',
        })
      }
    }

    if (isInput) {
      setIsInputDialogOpen(false)
    } else {
      setIsOutputDialogOpen(false)
    }
  }

  const handleDeleteParameter = async (parameterId: string, isInput: boolean) => {
    if (tool) {
      const updatedTool = { ...tool }
      if (isInput) {
        updatedTool.input_parameters = updatedTool.input_parameters.filter(p => p.id !== parameterId)
      } else {
        updatedTool.output_parameters = updatedTool.output_parameters.filter(p => p.id !== parameterId)
      }
      setTool(updatedTool)

      // 自动调用update_api接口保存参数更改
      try {
        const apiRequest = convertToolToApiRequest(updatedTool)
        console.log(`${t('plugins.toolConfig.autoSaveDelete', '自动保存参数删除')}:`, apiRequest)

        const response = await updatePluginApiMutation.mutateAsync(apiRequest)

        if (response.code === 200) {
          setSnackbar({ open: true, message: t('plugins.toolConfig.autoSaveDeleteSuccess', '参数删除并保存成功'), severity: 'success' })
          setPathError('') // 清空路径错误
        } else {
          setSnackbar({
            open: true,
            message: t('plugins.toolConfig.autoSaveDeleteFailed', '参数删除成功但保存失败: {{message}}', {
              message: response.message || t('plugins.errors.unknownError', '未知错误'),
            }),
            severity: 'warning',
          })
        }
      } catch (error: unknown) {
        console.error(`${t('plugins.toolConfig.autoSaveDeleteFailedLog', '保存参数删除失败')}:`, error)
        const errorMessage = error?.response?.data?.message || error?.message || '保存参数删除失败，请稍后重试'
        setSnackbar({
          open: true,
          message: t('plugins.toolConfig.autoSaveDeleteFailed', '参数删除成功但保存失败: {{message}}', { message: errorMessage }),
          severity: 'warning',
        })
      }
    }
  }

  const handleCodeLanguageChange = (language: 'javascript' | 'python') => {
    setCodeLanguage(language)
    if (tool) {
      const updatedTool = { ...tool, language }
      setTool(updatedTool)
    }
  }

  const handleRuntimeLanguageChange = (language: 'python' | 'javascript' | 'nodejs') => {
    // Normalize language value: nodejs -> javascript for code editor
    const normalizedLanguage = language === 'nodejs' ? 'javascript' : language
    setCodeLanguage(normalizedLanguage as 'javascript' | 'python')
    if (tool) {
      const updatedTool = { ...tool, language: normalizedLanguage }
      setTool(updatedTool)
    }
  }

  const handleCodeChange = (code: string) => {
    setCodeContent(code)
    if (tool) {
      const updatedTool = { ...tool, code }
      setTool(updatedTool)
    }
  }

  const handleHeaderChange = (index: number, field: 'key' | 'value', value: string) => {
    if (tool) {
      const updatedTool = { ...tool }
      updatedTool.headers[index] = { ...updatedTool.headers[index], [field]: value }
      setTool(updatedTool)
    }
  }

  const handleAddHeader = () => {
    if (tool) {
      const updatedTool = { ...tool }
      updatedTool.headers = [...updatedTool.headers, { key: '', value: '' }]
      setTool(updatedTool)
    }
  }

  const handleRemoveHeader = (index: number) => {
    if (tool) {
      const updatedTool = { ...tool }
      updatedTool.headers = updatedTool.headers.filter((_, i) => i !== index)
      setTool(updatedTool)
      // Save after deletion
      handleSaveSingleHeader(index)
    }
  }

  const handleSaveSingleHeader = async (index: number) => {
    if (!tool) return

    try {
      const apiRequest = convertToolToApiRequest(tool)
      console.log(`Saving header row ${index}:`, apiRequest)

      const response = await updatePluginApiMutation.mutateAsync(apiRequest)

      if (response.code === 200) {
        setSnackbar({
          open: true,
          message: t('plugins.toolConfig.headerSaveSuccess', '请求头保存成功'),
          severity: 'success',
        })
        setPathError('')
      } else {
        setSnackbar({
          open: true,
          message: t('plugins.toolConfig.headerSaveFailed', '保存失败: {{message}}', {
            message: response.message || t('plugins.errors.unknownError', '未知错误'),
          }),
          severity: 'error',
        })
      }
    } catch (error: unknown) {
      console.error('保存请求头失败:', error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.toolConfig.headerSaveFailedRetry', '保存请求头失败，请稍后重试')
      setSnackbar({ open: true, message: errorMessage, severity: 'error' })
    }
  }

  const handleSaveTool = async () => {
    if (!tool?.name?.trim()) {
      setSnackbar({ open: true, message: t('plugins.toolConfig.nameRequired', '名称不能为空'), severity: 'warning' })
      return
    }
    if (!tool || !plugin_id) return

    // 对API工具进行路径校验
    if (pluginType === 'api' && tool.path) {
      const pathValidation = validateToolPath(tool.path)
      if (!pathValidation.isValid) {
        setSnackbar({ open: true, message: pathValidation.error, severity: 'error' })
        setPathError(pathValidation.error)
        return
      }
    }

    try {
      const apiRequest = convertToolToApiRequest(tool)
      console.log('Saving tool configuration:', apiRequest)

      const response = await updatePluginApiMutation.mutateAsync(apiRequest)

      if (response.code === 200) {
        setSnackbar({ open: true, message: t('plugins.tools.config.saveSuccess', '工具配置保存成功'), severity: 'success' })
        setPathError('') // 清空路径错误
      } else {
        setSnackbar({
          open: true,
          message: t('plugins.tools.config.saveFailed', '保存失败: {{message}}', { message: response.message || t('plugins.errors.unknownError', '未知错误') }),
          severity: 'error',
        })
      }
    } catch (error: unknown) {
      console.error(`${t('plugins.tools.config.saveFailedLog', '保存工具配置失败')}:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.tools.config.saveFailedRetry', '保存工具配置失败，请稍后重试')
      setSnackbar({ open: true, message: errorMessage, severity: 'error' })
    }
  }

  const handleDeleteTool = async () => {
    if (!tool || !plugin_id) return

    try {
      const deleteRequest = {
        space_id: getDefaultSpaceId(),
        plugin_id,
        tool_id: tool.tool_id,
      }

      const response = await deletePluginApiMutation.mutateAsync(deleteRequest)

      if (response.code === 200) {
        setSnackbar({ open: true, message: t('plugins.tools.deleteSuccess', '工具删除成功'), severity: 'success' })
        // 立即返回插件页面，避免不必要的 API 调用
        handleBackNavigation()
      } else {
        setSnackbar({
          open: true,
          message: `删除失败: ${response.message || '未知错误'}`,
          severity: 'error',
        })
      }
    } catch (error: unknown) {
      console.error(`${t('plugins.tools.config.deleteFailedLog', '删除工具失败')}:`, error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.tools.deleteFailedRetry', '删除工具失败，请稍后重试')
      setSnackbar({ open: true, message: errorMessage, severity: 'error' })
    } finally {
      setDeleteDialogOpen(false)
    }
  }

  const handleTestConnection = () => {
    // 打开测试对话框
    setTestDialogOpen(true)
    setTestResults('')
    setTestError('')

    // 初始化参数值 - 只初始化运行时参数(is_runtime: true 或 undefined)
    const initialParams: Record<string, string> = {}

    // Get tool parameter names to filter out plugin parameters with the same name
    const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])

    // 初始化插件级参数 - 排除与工具参数同名的参数
    if (pluginData?.data?.plugin_info?.request_params) {
      pluginData.data.plugin_info.request_params.forEach(param => {
        // Skip plugin parameters that have the same name as tool parameters
        if (param.is_runtime !== false && !toolParamNames.has(param.name)) {
          const typeString = typeof param.type === 'number' ? mapNumberToString(param.type) : param.type
          // 布尔类型参数默认为false，其他为空字符串
          initialParams[`plugin_${param.name}`] = typeString === 'boolean' ? 'false' : ''
        }
      })
    }

    // 初始化工具级参数
    if (tool?.input_parameters) {
      tool.input_parameters.forEach(param => {
        if (param.is_runtime !== false) {
          // 布尔类型参数默认为false，其他为空字符串
          initialParams[`tool_${param.name}`] = param.type === 'boolean' ? 'false' : ''
        }
      })
    }

    setTestParameters(initialParams)
  }

  const handleTestParameterChange = (paramName: string, value: string, paramType: 'plugin' | 'tool', fieldType?: string) => {
    const key = `${paramType}_${paramName}`
    setTestParameters(prev => ({
      ...prev,
      [key]: value,
    }))

    if (fieldType === 'int' || fieldType === 'float' || fieldType === 'object' || fieldType === 'array_int' || fieldType === 'array_float') {
      const error = validateTestParameterValue(value, fieldType)
      setTestParameterErrors(prev => ({
        ...prev,
        [key]: error,
      }))
    } else {
      setTestParameterErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors[key]
        return newErrors
      })
    }
  }

  const validateTestParameterValue = (value: string, type: string): string => {
    if (!value || value.trim() === '') return ''

    const trimmedValue = value.trim()

    if (type === 'int') {
      if (!/^-?\d+$/.test(trimmedValue)) return '请输入有效的整数'
    } else if (type === 'float') {
      const num = Number(trimmedValue)
      if (isNaN(num)) return '请输入有效的数字'
    } else if (type === 'object') {
      try {
        const parsed = JSON.parse(trimmedValue)
        if (typeof parsed !== 'object' || Array.isArray(parsed) || parsed === null) {
          return '请输入有效的JSON对象格式，例如: {"key":"value"}'
        }
      } catch (e) {
        return '请输入有效的JSON格式，例如: {"key":"value"}'
      }
    } else if (type === 'array_int') {
      try {
        const parsed = JSON.parse(trimmedValue)
        if (!Array.isArray(parsed)) {
          return '请输入有效的数组格式，例如: [1,2,3]'
        }
        if (parsed.length > 0) {
          const allIntegers = parsed.every((item: unknown) => Number.isInteger(item))
          if (!allIntegers) {
            return '数组中的所有元素必须是整数，例如: [1,2,3]'
          }
        }
      } catch (e) {
        return '请输入有效的JSON数组格式，例如: [1,2,3]'
      }
    } else if (type === 'array_float') {
      try {
        const parsed = JSON.parse(trimmedValue)
        if (!Array.isArray(parsed)) {
          return '请输入有效的数组格式，例如: [1.5,2.3,3.14]'
        }
        if (parsed.length > 0) {
          const allNumbers = parsed.every((item: unknown) => typeof item === 'number' && !isNaN(item))
          if (!allNumbers) {
            return '数组中的所有元素必须是数字，例如: [1.5,2.3,3.14]'
          }
        }
      } catch (e) {
        return '请输入有效的JSON数组格式，例如: [1.5,2.3,3.14]'
      }
    }

    return ''
  }

  const validateRequiredParameters = (): { isValid: boolean; missingParams: string[] } => {
    const missing: string[] = []

    // Check for validation errors first
    const hasValidationErrors = Object.values(testParameterErrors).some(error => error !== '')
    if (hasValidationErrors) {
      return {
        isValid: false,
        missingParams: [],
      }
    }

    // Get tool parameter names to filter out plugin parameters with the same name
    const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])

    // Check plugin-level required runtime parameters (excluding those with same name as tool parameters)
    pluginData?.data?.plugin_info?.request_params
      ?.filter(p => p.is_runtime !== false && p.is_required && !toolParamNames.has(p.name))
      ?.forEach(param => {
        const paramValue = testParameters[`plugin_${param.name}`]
        if (!paramValue || paramValue.trim() === '') {
          missing.push(`${param.name} (插件参数)`)
        }
      })

    // Check tool-level required runtime parameters
    tool?.input_parameters
      ?.filter(p => p.is_runtime !== false && p.is_required)
      ?.forEach(param => {
        const paramValue = testParameters[`tool_${param.name}`]
        if (!paramValue || paramValue.trim() === '') {
          missing.push(`${param.name} (工具参数)`)
        }
      })

    return {
      isValid: missing.length === 0,
      missingParams: missing,
    }
  }

  const handleExecuteTest = async () => {
    if (!tool || !plugin_id) return

    setIsTestRunning(true)
    setTestResults('')
    setTestError('')

    try {
      // 构建PluginExecuteRequest
      const executeRequest = {
        id: '',
        version: '',
        space_id: getDefaultSpaceId(),
        plugin_id: plugin_id,
        tool_id: tool.tool_id,
        inputs: getTypedTestParameters(),
      }

      console.log(t('plugins.toolConfig.testConnection', '执行插件测试'), executeRequest)

      // 执行插件 - 简化执行逻辑，移除未使用的onEvent
      await executePluginMutation.mutateAsync({
        request: executeRequest,
        onEvent: undefined, // 不使用onEvent，因为它永远不会被执行
        onError: error => {
          console.error(t('plugins.toolConfig.testConnectionError', '插件执行错误', { message: error || t('plugins.errors.unknownError', '未知错误') }))
          setTestError(
            t('plugins.toolConfig.testConnectionError', '插件执行错误: {{message}}', {
              message: error.message || t('plugins.errors.unknownError', '未知错误'),
            }),
          )
        },
        onComplete: (buffer: string) => {
          // console.log(t('plugins.toolConfig.testConnectionSuccess', '测试执行成功'), buffer)
          // setSnackbar({ open: true, message: t('plugins.toolConfig.testConnectionSuccess', '测试执行成功'), severity: 'success' })

          try {
            // 解析buffer获取最终结果数据
            const bufferData = JSON.parse(buffer)

            // 根据提供的buffer格式解析结果
            // buffer格式: {"data":{"type":"plugin","payload":{"error_code":0,"error_message":"success","output":{...}},"code":200,"message":"Executed successfully"}}
            const finalResults: TestExecutionResult = {
              timestamp: new Date().toISOString(),
              execution_success: false,
              error_code: null,
              error_message: null,
              output: null,
              raw_response: bufferData,
            }

            if (bufferData.code === 200 && bufferData.data) {
              finalResults.error_code = bufferData.data.payload?.error_code ?? null
              finalResults.error_message = bufferData.data.payload?.error_message || null
              finalResults.output = bufferData.data.payload?.output || null
              // 根据error_message判断执行是否成功
 	          finalResults.execution_success = bufferData.data.payload?.error_message === 'success'

              // 如果执行成功，立即更新工具状态为启用
              if (bufferData.data.payload?.error_message === 'success' && tool) {
                // 更新本地工具状态
                setTool(prev => prev ? { ...prev, available: true } : prev)

                // 乐观更新React Query缓存
                const queryKey = pluginType === 'code' ? ['pluginCodeList', spaceId, plugin_id] : ['pluginApiList', spaceId, plugin_id]

                queryClient.setQueryData(queryKey, (oldData: any) => {
                  if (!oldData || oldData.code !== 200) return oldData

                  const dataKey = pluginType === 'code' ? 'code_info' : 'api_info'
                  const updatedList = oldData.data[dataKey].map((item: any) =>
                    item.tool_id === tool_id ? { ...item, available: true } : item
                  )

                  return {
                    ...oldData,
                    data: {
                      ...oldData.data,
                      [dataKey]: updatedList,
                    },
                  }
                })

                // 也更新单个工具的缓存
                const singleQueryKey = pluginType === 'code' ? ['pluginCode', spaceId, plugin_id, tool_id] : ['pluginApi', spaceId, plugin_id, tool_id]
                queryClient.setQueryData(singleQueryKey, (oldData: any) => {
                  if (!oldData || oldData.code !== 200) return oldData

                  const dataKey = pluginType === 'code' ? 'code_info' : 'api_info'
                  return {
                    ...oldData,
                    data: {
                      ...oldData.data,
                      [dataKey]: oldData.data[dataKey].map((item: any) =>
                        item.tool_id === tool_id ? { ...item, available: true } : item
                      ),
                    },
                  }
                })

                console.log('工具状态已更新为启用')
              }
            } else {
              // 错误响应
              finalResults.execution_success = false
              finalResults.error_code = bufferData.code || 500
              finalResults.error_message = bufferData.message || 'Unknown error'
            }

            setTestResults(JSON.stringify(finalResults, null, 2))
          } catch (parseError) {
            console.error('解析执行结果失败:', parseError)
            // 如果解析失败，显示原始buffer内容
            setTestResults(
              JSON.stringify(
                {
                  timestamp: new Date().toISOString(),
                  execution_success: false,
                  error_message: t('plugins.toolConfig.testConnectionResultError', '无法解析执行结果'),
                  raw_buffer: buffer,
                  parse_error: parseError.message,
                },
                null,
                2,
              ),
            )
          }
        },
        timeout: undefined, // 移除超时限制
      })
    } catch (error: unknown) {
      console.error('测试执行失败:', error)
      const errorMessage = error?.response?.data?.message || error?.message || t('plugins.toolConfig.testConnectionFailed', '测试执行失败，请检查参数配置')
      setTestError(errorMessage)
      setSnackbar({ open: true, message: errorMessage, severity: 'error' })
    } finally {
      setIsTestRunning(false)
    }
  }

  // Template handling functions
  const availableTemplates = codeTemplates.filter(template => template.language === (tool?.language || 'python'))

  const handleTemplateSelect = (templateName: string) => {
    const template = codeTemplates.find(t => t.name === templateName && t.language === (tool?.language || 'python'))
    if (template) {
      setCodeContent(template.template)
      setSelectedTemplate(templateName)
      if (tool) {
        const updatedTool = { ...tool, code: template.template }
        setTool(updatedTool)
      }
    }
  }

  const handleResetCode = () => {
    setCodeContent('')
    setSelectedTemplate('')
    if (tool) {
      const updatedTool = { ...tool, code: '' }
      setTool(updatedTool)
    }
  }

  const handleBackNavigation = () => {
    if (source === 'agent') {
      // 从智能体配置页面跳转过来的，返回到智能体页面
      if (agentId) {
        navigate(`/dashboard/agents/${agentId}`)
      } else {
        navigate('/dashboard/agents')
      }
    } else if (fromPublishVersion && publishVersion) {
      // 从插件发布版本页面跳转过来的，返回到插件版本页面
      navigate(`/dashboard/plugins/${plugin_id}/${publishVersion}`)
    } else {
      // 从插件管理页面跳转过来的，返回到插件配置页面
      navigate(`/dashboard/plugins/${plugin_id}`)
    }
  }

  // Don't show loading if we have toolsData (data is already available from publish version)
  const isLoadingEffective = isLoadingApi && !toolsData

  if (isLoadingEffective) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <CircularProgress size={48} className="mb-4" />
          <Typography variant="body1" color="text.secondary">
            {t('plugins.toolConfig.loading', '正在加载工具配置...')}
          </Typography>
        </div>
      </div>
    )
  }

  if (!tool) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Typography variant="h6" className="mb-2">
            {t('plugins.toolConfig.toolNotFound', '工具未找到')}
          </Typography>
          <Typography variant="body2" color="text.secondary" className="mb-4">
            {t('plugins.toolConfig.checkToolId', '请检查工具ID是否正确')}
          </Typography>
          <Button variant="contained" onClick={() => navigate(`/dashboard/plugins/${plugin_id}`)}>
            {t('plugins.toolConfig.returnPluginConfig', '返回插件配置')}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4">
            <Button variant="outlined" startIcon={<ArrowLeft className="w-4 h-4" />} onClick={handleBackNavigation} className="mb-4">
              {source === 'agent' ? t('plugins.toolConfig.returnAgentConfig', '返回智能体配置') : t('plugins.toolConfig.returnPluginConfig', '返回插件配置')}
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Typography variant="h4" className="font-bold text-gray-900 mb-2">
                {tool.name}
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {tool.description}
              </Typography>
              <div className="flex items-center space-x-4 mt-2">
                <Chip
                  label={tool.available ? t('plugins.actions.enable', '启用') : t('plugins.actions.disable', '禁用')}
                  size="small"
                  color={tool.available ? 'success' : 'default'}
                  icon={tool.available ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                />
                {pluginType === 'code' ? (
                  <>
                    <Chip label={`${t('plugins.toolConfig.language', '语言')}: ${tool.language || 'python'}`} size="small" />
                    <Chip label={t('plugins.toolConfig.codeTool', '代码工具')} size="small" variant="outlined" />
                  </>
                ) : (
                  <>
                    <Chip label={`${t('plugins.toolConfig.method', '方法')}: ${getMethodString(tool.method || 1)}`} size="small" />
                    <Chip
                      label={`${t('plugins.toolConfig.path', '路径')}: ${tool.path || ''}`}
                      size="small"
                      variant="outlined"
                      sx={{
                        maxWidth: '80ch',
                        '& .MuiChip-label': {
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: 'calc(70ch - 24px)',
                        },
                      }}
                    />
                  </>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outlined"
                color="error"
                startIcon={<Trash2 className="w-4 h-4" />}
                onClick={() => setDeleteDialogOpen(true)}
                disabled={deletePluginApiMutation.isPending || isReadOnly}
              >
                {deletePluginApiMutation.isPending ? t('plugins.actions.deleting', '删除中...') : t('plugins.actions.deleteTool', '删除工具')}
              </Button>
              <Button
                variant="contained"
                startIcon={updatePluginApiMutation.isPending ? <CircularProgress size={16} /> : <Save className="w-4 h-4" />}
                onClick={handleSaveTool}
                disabled={updatePluginApiMutation.isPending || !tool.name.trim() || !tool.description.trim() || isReadOnly}
              >
                {updatePluginApiMutation.isPending ? t('plugins.actions.saving', '保存中...') : t('plugins.actions.saveConfig', '保存配置')}
              </Button>
            </div>
          </div>
        </div>

        {/* Configuration Tabs */}
        <Card className="p-6">
          <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)} className="mb-6">
            <Tab label={t('plugins.tools.tabs.basic')} value="basic" />
            <Tab label={t('plugins.tools.tabs.input')} value="input" />
            <Tab label={t('plugins.tools.tabs.output')} value="output" />
            {pluginType === 'api' && <Tab label={t('plugins.tools.tabs.headersConfig')} value="headers" />}
            {pluginType === 'code' && <Tab label={t('plugins.tools.tabs.code')} value="code" />}
            <Tab label={t('plugins.tools.tabs.test')} value="test" />
          </Tabs>

          {/* Basic Info Tab */}
          {tabValue === 'basic' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Typography variant="subtitle2" className="mb-2">
                    {t('plugins.tools.name', '工具名称')}
                  </Typography>
                  <TextField
                    fullWidth
                    value={tool.name}
                    onChange={e => setTool({ ...tool, name: e.target.value })}
                    placeholder={t('plugins.tools.namePlaceholder', '请输入工具名称...')}
                    helperText={t('plugins.tools.nameHelper', '建议使用简洁明了的名称 ({{count}}/128)', { count: tool.name.length })}
                    inputProps={{ maxLength: 128 }}
                    disabled={isReadOnly}
                  />
                </div>
                {pluginType === 'code' ? (
                  <div>
                    <Typography variant="subtitle2" className="mb-2">
                      {t('plugins.pluginConfig.runtimeEnvironment', '运行时环境')}
                    </Typography>
                    <FormControl fullWidth>
                      <Select value={tool.language || 'python'} onChange={e => handleRuntimeLanguageChange(e.target.value as 'python' | 'javascript' | 'nodejs')} disabled={isReadOnly}>
                        <MenuItem value="python">Python 3</MenuItem>
                        <MenuItem value="javascript">Node.js</MenuItem>
                      </Select>
                    </FormControl>
                  </div>
                ) : (
                  <div>
                    <Typography variant="subtitle2" className="mb-2">
                      {t('plugins.pluginConfig.method', '请求方法')}
                    </Typography>
                    <FormControl fullWidth>
                      <Select value={tool.method} onChange={e => setTool({ ...tool, method: e.target.value as number })} disabled={isReadOnly}>
                        <MenuItem value={1}>GET</MenuItem>
                        <MenuItem value={2}>POST</MenuItem>
                      </Select>
                    </FormControl>
                  </div>
                )}
              </div>
              {pluginType === 'code' ? (
                <div>
                  <Typography variant="subtitle2" className="mb-2">
                    {t('plugins.pluginConfig.runtimeConfig', 'IDE运行时配置')}
                  </Typography>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <div className="flex items-center space-x-2">
                      <Code className="w-5 h-5 text-blue-600" />
                      <Typography variant="body2" className="font-medium">
                        {t('plugins.pluginConfig.codeEnvironment', '代码执行环境')}
                      </Typography>
                    </div>
                    <Typography variant="body2" color="text.secondary" className="ml-7">
                      {t('plugins.toolConfig.codeEnvironmentHelper', '支持Python 3和Node.js运行时环境，提供完整的代码编辑和调试功能')}
                    </Typography>
                    <div className="flex items-center space-x-2 mt-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <Typography variant="body2" color="text.secondary">
                        {t('plugins.toolConfig.autoDependencyManagement', '自动依赖管理：系统会自动安装所需的依赖包')}
                      </Typography>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <Typography variant="body2" color="text.secondary">
                        {t('plugins.toolConfig.securitySandbox', '安全沙箱：代码在隔离环境中执行，确保安全性')}
                      </Typography>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <Typography variant="body2" color="text.secondary">
                        {t('plugins.toolConfig.realTimeMonitoring', '实时监控：提供代码执行状态和错误日志')}
                      </Typography>
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <Typography variant="subtitle2" className="mb-2">
                    {t('plugins.toolConfig.apiPath', 'API路径')}
                  </Typography>
                  <TextField
                    fullWidth
                    value={tool.path}
                    onChange={e => handlePathChange(e.target.value)}
                    placeholder={t('plugins.toolConfig.apiPathPlaceholder', '请输入API路径...')}
                    helperText={
                      pathError || t('plugins.toolConfig.apiPathHelper', '例如：/api/users/:id，必须以/开头，只能包含英文、数字、下划线、连字符和斜杠')
                    }
                    error={!!pathError}
                    InputProps={{
                      sx: {
                        '& .MuiInputBase-input': {
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: 'calc(70ch + 20px)',
                        },
                      },
                    }}
                    disabled={isReadOnly}
                  />
                </div>
              )}
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  {t('plugins.toolConfig.toolDescription', '工具描述')}
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  value={tool.description}
                  onChange={e => setTool({ ...tool, description: e.target.value })}
                  placeholder={t('plugins.toolConfig.toolDescriptionPlaceholder', '请输入工具描述...')}
                  helperText={t('plugins.toolConfig.toolDescriptionHelper', '详细描述工具的功能、用途和参数 ({{count}}/256)', {
                    count: tool.description.length,
                  })}
                  inputProps={{ maxLength: 256 }}
                  disabled={isReadOnly}
                />
              </div>
            </div>
          )}

          {/* Input Parameters Tab */}
          {tabValue === 'input' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">{t('plugins.toolConfig.inputParameters', '输入参数配置')}</Typography>
                <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => openParameterDialog(null, true)} disabled={isReadOnly}>
                  {t('plugins.toolConfig.addInputParameter', '添加输入参数')}
                </Button>
              </div>

              {tool.input_parameters.length === 0 ? (
                <div className="bg-gray-50 rounded-lg p-8 text-center">
                  <Typography variant="body1" color="text.secondary">
                    {t('plugins.toolConfig.noInputParameters', '暂无输入参数')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" className="mt-1">
                    {t('plugins.toolConfig.addInputParametersHint', '点击"添加输入参数"开始配置')}
                  </Typography>
                </div>
              ) : (
                <div className="space-y-4">
                  {tool.input_parameters.map(param => (
                    <Card key={param.id} className="p-4 border border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-4">
                            <Typography variant="subtitle1" className="font-medium">
                              {param.name}
                            </Typography>
                            <Chip label={param.type} size="small" />
                            {pluginType === 'api' && <Chip label={getMethodLabel(param.method)} size="small" variant="outlined" />}
                            {param.is_required && <Chip label={t('plugins.toolConfig.required')} size="small" color="error" variant="outlined" />}
                          </div>
                          <Typography variant="body2" color="text.secondary" className="mt-1">
                            {param.description}
                          </Typography>
                          {param.value && (
                            <Typography variant="caption" color="text.secondary" className="mt-1">
                              {t('plugins.toolConfig.defaultValueLabel')} {param.value}
                            </Typography>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <IconButton size="small" onClick={() => openParameterDialog(param, true)} title={t('plugins.toolConfig.editParameter', '编辑参数')} disabled={isReadOnly}>
                            <Settings className="w-4 h-4" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteParameter(param.id, true)}
                            title={t('plugins.toolConfig.deleteParameter', '删除参数')}
                            disabled={isReadOnly}
                          >
                            <Trash2 className="w-4 h-4" />
                          </IconButton>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Output Parameters Tab */}
          {tabValue === 'output' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">{t('plugins.toolConfig.outputParameters', '输出参数配置')}</Typography>
                <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={() => openParameterDialog(null, false)} disabled={isReadOnly}>
                  {t('plugins.toolConfig.addOutputParameter', '添加输出参数')}
                </Button>
              </div>

              {tool.output_parameters.length === 0 ? (
                <div className="bg-gray-50 rounded-lg p-8 text-center">
                  <Typography variant="body1" color="text.secondary">
                    {t('plugins.toolConfig.noOutputParameters', '暂无输出参数')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" className="mt-1">
                    {t('plugins.toolConfig.addOutputParametersHint', '点击"添加输出参数"开始配置')}
                  </Typography>
                </div>
              ) : (
                <div className="space-y-4">
                  {tool.output_parameters.map(param => (
                    <Card key={param.id} className="p-4 border border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-4">
                            <Typography variant="subtitle1" className="font-medium">
                              {param.name}
                            </Typography>
                            <Chip label={param.type} size="small" />
                            {param.is_required && <Chip label={t('plugins.toolConfig.required')} size="small" color="error" variant="outlined" />}
                          </div>
                          <Typography variant="body2" color="text.secondary" className="mt-1">
                            {param.description}
                          </Typography>
                          {param.value && (
                            <Typography variant="caption" color="text.secondary" className="mt-1">
                              {t('plugins.toolConfig.defaultValueLabel')} {param.value}
                            </Typography>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          <IconButton size="small" onClick={() => openParameterDialog(param, false)} title={t('plugins.toolConfig.editParameter', '编辑参数')} disabled={isReadOnly}>
                            <Settings className="w-4 h-4" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteParameter(param.id, false)}
                            title={t('plugins.toolConfig.deleteParameter', '删除参数')}
                            disabled={isReadOnly}
                          >
                            <Trash2 className="w-4 h-4" />
                          </IconButton>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Headers Configuration Tab - Only for API Tools */}
          {tabValue === 'headers' && pluginType === 'api' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">{t('plugins.toolConfig.headers', '请求头配置')}</Typography>
                <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={handleAddHeader} disabled={isReadOnly}>
                  {t('plugins.toolConfig.addHeader', '添加请求头')}
                </Button>
              </div>

              <div className="space-y-4">
                {/* Header Row */}
                {tool.headers.length > 0 && (
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 bg-gray-50 rounded-lg border-b">
                    <div className="col-span-5 text-sm font-medium text-gray-700">Key</div>
                    <div className="col-span-5 text-sm font-medium text-gray-700">Value</div>
                    <div className="col-span-2 text-sm font-medium text-gray-700">操作</div>
                  </div>
                )}

                {tool.headers.length === 0 ? (
                  <div className="bg-gray-50 rounded-lg p-6 text-center">
                    <Typography variant="body2" color="text.secondary" className="mb-2">
                      暂无请求头配置
                    </Typography>
                    <Button variant="outlined" startIcon={<Plus className="w-4 h-4" />} onClick={handleAddHeader}>
                      添加请求头
                    </Button>
                  </div>
                ) : (
                  tool.headers.map((header, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2 items-center p-4 border border-gray-200 rounded-lg">
                    <div className="col-span-5">
                      <TextField
                        value={header.key}
                        onChange={e => handleHeaderChange(index, 'key', e.target.value)}
                        size="small"
                        fullWidth
                        placeholder={t('plugins.tools.headers.keyPlaceholder')}
                        disabled={isReadOnly}
                      />
                    </div>
                    <div className="col-span-5">
                      <TextField
                        value={header.value}
                        onChange={e => handleHeaderChange(index, 'value', e.target.value)}
                        size="small"
                        fullWidth
                        placeholder={t('plugins.tools.headers.valuePlaceholder')}
                        disabled={isReadOnly}
                      />
                    </div>
                    <div className="col-span-2 flex justify-center gap-1">
                      <IconButton
                        size="small"
                        onClick={() => handleSaveSingleHeader(index)}
                        title="保存此行"
                        disabled={isReadOnly || updatePluginApiMutation.isLoading}
                        color="success"
                      >
                        <Check className="w-4 h-4" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveHeader(index)}
                        color="error"
                        title="删除此行"
                        disabled={isReadOnly}
                      >
                        <Trash2 className="w-4 h-4" />
                      </IconButton>
                    </div>
                  </div>
                ))
                )}
              </div>
            </div>
          )}

          {/* Code Editor Tab - Only for Code Tools */}
          {tabValue === 'code' && pluginType === 'code' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">代码编辑器</Typography>
                <div className="flex items-center space-x-2">
                  <Chip label={` ${t('plugins.toolConfig.language', '语言')}: ${tool.language === 'javascript' ? 'JavaScript' : 'Python'}`} size="small" />
                  <Chip label={t('plugins.toolConfig.syntaxHighlight', '语法高亮')} size="small" variant="outlined" />
                  {selectedTemplate && (
                    <Chip label={`${t('plugins.toolConfig.template', '模板')}: ${selectedTemplate}`} size="small" variant="outlined" className="text-xs" />
                  )}
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Code className="w-5 h-5 text-blue-600" />
                    <Typography variant="body2" className="font-medium">
                      {t('plugins.pluginConfig.codeEditor', '代码编辑环境')}
                    </Typography>
                  </div>
                  <div className="flex items-center space-x-3">
                    {availableTemplates.length > 0 && (
                      <Button variant="outlined" size="small" onClick={() => setShowTemplates(!showTemplates)} startIcon={<FileText className="w-4 h-4" />} disabled={isReadOnly}>
                        {t('plugins.pluginConfig.codeTemplates', '模板')}
                      </Button>
                    )}
                    <Button variant="outlined" size="small" onClick={handleResetCode} startIcon={<RotateCcw className="w-4 h-4" />} disabled={isReadOnly}>
                      {t('plugins.pluginConfig.resetCode', '重置代码')}
                    </Button>
                  </div>
                </div>

                {/* Template Selection */}
                {showTemplates && availableTemplates.length > 0 && (
                  <div className="bg-white border border-gray-200 rounded-lg p-4">
                    <Typography variant="subtitle2" className="mb-3 flex items-center">
                      <FileText className="w-4 h-4 mr-2" />
                      {t('plugins.pluginConfig.selectCodeTemplate', '选择代码模板')}
                    </Typography>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {availableTemplates.map(template => (
                        <div
                          key={template.name}
                          className={`p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
                            selectedTemplate === template.name
                              ? 'border-blue-500 bg-blue-50 shadow-sm'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                          }`}
                          onClick={() => handleTemplateSelect(template.name)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <Typography variant="body2" className="font-medium">
                              {template.name}
                            </Typography>
                            <Chip label={(tool?.language || 'python') === 'javascript' ? 'JS' : 'PY'} size="small" color={(tool?.language || 'python') === 'javascript' ? 'success' : 'info'} />
                          </div>
                          <Typography variant="body2" className="text-gray-600 text-sm">
                            {template.description}
                          </Typography>
                        </div>
                      ))}
                    </div>

                    <div className="mt-3 flex justify-end">
                      <Button size="small" onClick={() => setShowTemplates(false)}>
                        {t('common.buttons.close', '关闭')}
                      </Button>
                    </div>
                  </div>
                )}

                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  {/* Code editor based on runtime language - no selector here */}
                  <div className="bg-gray-50 border-b border-gray-200 p-3">
                    <Typography variant="body2" className="text-gray-600">
                      {t('plugins.pluginConfig.programmingLanguage', '编程语言')}: <span className="font-medium">{tool.language === 'javascript' ? 'JavaScript' : 'Python'}</span>
                    </Typography>
                  </div>

                  {/* Code editor based on language */}
                  <div className="flex-1" style={{ height: '700px', minHeight: '500px' }}>
                    {(tool.language || 'python') === 'python' ? (
                      <PythonCodeEditor
                        value={tool.code || ''}
                        onChange={handleCodeChange}
                        theme="light"
                        minHeight={500}
                        maxHeight={700}
                        lineNumbers={true}
                        foldGutter={true}
                        style={{ height: '100%' }}
                      />
                    ) : (
                      <TypeScriptCodeEditor
                        value={tool.code || ''}
                        onChange={handleCodeChange}
                        theme="light"
                        minHeight={500}
                        maxHeight={700}
                        lineNumbers={true}
                        foldGutter={true}
                        style={{ height: '100%' }}
                      />
                    )}
                  </div>
                </div>

                {/* Usage Tips */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <Typography variant="subtitle2" className="mb-2 text-blue-900">
                    {t('plugins.pluginConfig.usageTips', '💡 使用提示')}
                  </Typography>
                  <div className="space-y-1 text-sm text-blue-800">
                    {(tool.language || 'python') === 'python' ? (
                      <>
                        <div>
                          • {t('plugins.pluginConfig.pythonTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main</code>{' '}
                          {t('plugins.pluginConfig.pythonTips2', '函数作为入口点')}
                        </div>
                        <div>• {t('plugins.pluginConfig.pythonTips3', '使用标准库函数，避免依赖需要额外安装的包')}</div>
                        <div>• {t('plugins.pluginConfig.pythonTips4', '返回JSON序列化的数据结构，便于API调用')}</div>
                      </>
                    ) : (
                      <>
                        <div>
                          • {t('plugins.pluginConfig.jsTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main</code>{' '}
                          {t('plugins.pluginConfig.jsTips2', '函数作为入口点')}
                        </div>
                        <div>• {t('plugins.pluginConfig.jsTips3', '使用CommonJS模块系统（require/module.exports')}）</div>
                        <div>• {t('plugins.pluginConfig.jsTips4', '避免使用ES6模块语法，除非项目支持')}</div>
                        <div>• {t('plugins.pluginConfig.jsTips5', '返回JSON序列化的数据结构，便于API调用')}</div>
                      </>
                    )}
                    <div>• {t('plugins.pluginConfig.templateTips', '• 使用模板可以快速开始开发')}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Testing Tab */}
          {tabValue === 'test' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Typography variant="h6">{t('plugins.tools.test.toolTest', '工具测试')}</Typography>
                <Button variant="contained" onClick={handleTestConnection} startIcon={<Settings className="w-4 h-4" />}>
                  {t('plugins.tools.test.startTest', '开始测试')}
                </Button>
              </div>

              <Card className="p-6 border border-gray-200">
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      {pluginType === 'code' ? <Code className="w-4 h-4 text-blue-600" /> : <Settings className="w-4 h-4 text-blue-600" />}
                    </div>
                    <div>
                      <Typography variant="subtitle1" className="font-medium">
                        {pluginType === 'code' ? t('plugins.toolConfig.codeToolTest', '代码工具测试') : t('plugins.toolConfig.apiToolTest', 'API工具测试')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {pluginType === 'code'
                          ? t('plugins.toolConfig.testCodeConfig', '测试代码配置是否正确，验证代码执行是否可用')
                          : t('plugins.toolConfig.testApiConfig', '测试工具配置是否正确，验证API调用是否可用')}
                      </Typography>
                    </div>
                  </div>

                  <div className="ml-11 space-y-3">
                    {pluginType === 'code' ? (
                      <>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.pluginConfig.runtimeEnvironment', '运行时环境')}: {tool.language === 'javascript' ? 'Node.js' : (tool.language === 'python' ? 'Python 3' : 'Python')}
                          </Typography>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.toolConfig.codeLength', '代码长度')}: {tool.code?.length || 0} {t('plugins.toolConfig.characterCount', '字符')}
                          </Typography>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.toolConfig.inputParametersName', '输入参数')}: {tool.input_parameters.length} {t('plugins.toolConfig.number', '个')}
                          </Typography>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '70ch',
                            }}
                          >
                            {t('plugins.toolConfig.apiPath', 'API路径')}: {tool.path}
                          </Typography>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.pluginConfig.method', '请求方法')}: {getMethodString(tool.method)}
                          </Typography>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.toolConfig.inputParametersName', '输入参数')}: {tool.input_parameters.length} {t('plugins.toolConfig.number', '个')}
                          </Typography>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <Typography variant="body2" color="text.secondary">
                            {t('plugins.toolConfig.headers', '请求头配置')}: {tool.headers.length} {t('plugins.toolConfig.number', '个')}
                          </Typography>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <Typography variant="body2" color="text.secondary" className="mb-2">
                      {pluginType === 'code'
                        ? t('plugins.toolConfig.testCodeConfigHelper', '点击"开始测试"按钮打开代码测试对话框，可以测试代码执行并查看输出结果')
                        : t('plugins.toolConfig.testApiConfigHelper', '点击"开始测试"按钮打开测试对话框，填写参数并查看API调用返回结果')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {pluginType === 'code'
                        ? t('plugins.toolConfig.apiTestResultHelper', '系统将在隔离环境中执行代码，提供执行状态和错误日志')
                        : t('plugins.toolConfig.apiTestParameterHelper', '左侧填写测试参数，右侧查看API调用返回结果')}
                    </Typography>
                  </div>
                </div>
              </Card>
            </div>
          )}
        </Card>
      </div>

      {/* Parameter Dialog */}
      <Dialog
        open={isInputDialogOpen || isOutputDialogOpen}
        onClose={() => {
          setIsInputDialogOpen(false)
          setIsOutputDialogOpen(false)
          setEditingParameter(null)
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editingParameter ? t('plugins.toolConfig.editParameter', '编辑参数') : t('plugins.toolConfig.addParameter', '添加参数')}
          {isInputDialogOpen ? ` (${t('plugins.toolConfig.inputParameter', '输入')})` : ` (${t('plugins.toolConfig.outputParameter', '输出')})`}
        </DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <Typography variant="subtitle2">
                  {t('plugins.toolConfig.parameterName', '参数名称')} <span className="text-red-500 ml-1">*</span>
                </Typography>
                {isInputDialogOpen && (
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="is_required"
                      checked={parameterForm.is_required}
                      onChange={e => handleParameterFormChange('is_required', e.target.checked)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 cursor-pointer"
                    />
                    <label htmlFor="is_required" className="text-sm font-medium text-gray-700 cursor-pointer whitespace-nowrap">
                      {t('plugins.toolConfig.isRequired', '必选参数')}
                    </label>
                  </div>
                )}
              </div>
              <TextField
                fullWidth
                value={parameterForm.name}
                onChange={e => handleParameterFormChange('name', e.target.value)}
                placeholder={t('plugins.toolConfig.parameterNameHelper', '请输入参数名称...')}
                helperText={`${t('plugins.toolConfig.parameterName', '参数名称')} (${parameterForm.name.length}/128)`}
                inputProps={{ maxLength: 128 }}
              />
            </div>
            <div>
              <Typography variant="subtitle2" className="mb-2">
                {t('plugins.toolConfig.parameterDescription', '参数描述')} <span className="text-red-500 ml-1">*</span>
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={2}
                value={parameterForm.description}
                onChange={e => handleParameterFormChange('description', e.target.value)}
                placeholder={t('plugins.toolConfig.parameterDescriptionHelper', '请输入参数描述...')}
                helperText={`${t('plugins.toolConfig.parameterDescription', '参数描述')} (${parameterForm.description.length}/256)`}
                inputProps={{ maxLength: 256 }}
              />
            </div>
            {isInputDialogOpen ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Typography variant="subtitle2" className="mb-2">
                    {t('plugins.toolConfig.parameterType', '参数类型')}
                  </Typography>
                  <ParameterTypeSelector
                    value={parameterForm.type}
                    onChange={(value) => handleParameterFormChange('type', value)}
                  />
                </div>
                {pluginType === 'api' && (
                  <div>
                    <Typography variant="subtitle2" className="mb-2">
                      {t('plugins.toolConfig.transferMethod', '传入方法')}
                    </Typography>
                    <FormControl fullWidth>
                      <Select value={parameterForm.method} onChange={e => handleParameterFormChange('method', e.target.value)}>
                        <MenuItem value={1}>{t('plugins.toolConfig.headerParam')}</MenuItem>
                        <MenuItem value={2}>{t('plugins.toolConfig.queryParameter')}</MenuItem>
                        {tool.method !== 1 && <MenuItem value={3}>{t('plugins.toolConfig.bodyParameter')}</MenuItem>}
                      </Select>
                    </FormControl>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <Typography variant="subtitle2" className="mb-2">
                  {t('plugins.toolConfig.parameterType', '参数类型')}
                </Typography>
                <ParameterTypeSelector
                  value={parameterForm.type}
                  onChange={(value) => handleParameterFormChange('type', value)}
                />
              </div>
            )}
            {isInputDialogOpen && (
              <>
                {pluginType === 'api' && (
                  <div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="is_runtime"
                        checked={!parameterForm.is_runtime}
                        onChange={e => handleParameterFormChange('is_runtime', !e.target.checked)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <label htmlFor="is_runtime" className="text-sm font-medium text-gray-700 cursor-pointer">
                        {t('plugins.paramConfig.nonRuntimeParam')}
                      </label>
                    </div>
                    <Typography variant="caption" className="text-gray-500 mt-1 block">
                      {t('plugins.paramConfig.nonRuntimeParamHelper')}
                    </Typography>
                  </div>
                )}
                {!parameterForm.is_runtime && (
                  <div>
                    <Typography variant="subtitle2" className="mb-2">
                      {t('plugins.toolConfig.defaultValueLabel')} <span className="text-red-500 ml-1">*</span>
                    </Typography>
                    {(() => {
                      const isBooleanType = String(parameterForm.type) === 'boolean'
                      return isBooleanType ? (
                        <div className="flex items-center space-x-2">
                          <Typography variant="body2" className="text-gray-600">
                            {parameterForm.value === 'true' || parameterForm.value === true ? 'True' : 'False'}
                          </Typography>
                          <Switch
                            checked={parameterForm.value === 'true' || parameterForm.value === true}
                            onChange={e => handleParameterFormChange('value', e.target.checked ? 'true' : 'false')}
                            color="primary"
                          />
                        </div>
                      ) : (
                        <TextField
                          fullWidth
                          value={parameterForm.value}
                          onChange={e => handleParameterFormChange('value', e.target.value)}
                          placeholder={t('plugins.toolConfig.enterDefaultValue')}
                          helperText={t('plugins.paramConfig.nonRuntimeParamDefaultValue')}
                          required
                        />
                      )
                    })()}
                  </div>
                )}
              </>
            )}
          </div>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setIsInputDialogOpen(false)
              setIsOutputDialogOpen(false)
              setEditingParameter(null)
            }}
          >
            {t('common.buttons.cancel', '取消')}
          </Button>
          <Button variant="contained" onClick={() => handleSaveParameter(isInputDialogOpen)}>
            {editingParameter ? t('common.buttons.update', '更新') : t('common.buttons.add', '添加')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('plugins.tools.deleteDialog.title', '确认删除工具')}</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <Typography variant="body1">{t('plugins.tools.deleteDialog.content', { name: tool?.name })}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t('plugins.tools.deleteDialog.warning', '此操作不可撤销，删除后所有相关配置将被永久移除。')}
            </Typography>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deletePluginApiMutation.isPending}>
            {t('common.buttons.cancel', '取消')}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteTool}
            disabled={deletePluginApiMutation.isPending}
            startIcon={deletePluginApiMutation.isPending ? <CircularProgress size={16} /> : <Trash2 className="w-4 h-4" />}
          >
            {deletePluginApiMutation.isPending ? t('common.buttons.deleting', '删除中...') : t('plugins.tools.deleteDialog.confirm', '确认删除')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Dialog */}
      <Dialog
        open={testDialogOpen}
        onClose={() => setTestDialogOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { minHeight: '600px' },
        }}
      >
        <DialogTitle>
          <div className="flex items-center justify-between">
            <span>
              {t('plugins.toolConfig.testTool', '测试工具')}: {tool?.name}
            </span>
          </div>
        </DialogTitle>
        <DialogContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
            {/* Left Side - Test Parameters */}
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Typography variant="h6">{t('plugins.toolConfig.testParameters', '测试参数')}</Typography>
                <Typography variant="body2" color="text.secondary">
                  ({t('plugins.toolConfig.testParametersHelper', '根据工具配置填写测试参数')})
                </Typography>
              </div>

              <div className="space-y-6">
                {/* Plugin-level Parameters - 只显示运行时参数，且排除与工具参数同名的参数 */}
                {pluginData?.data?.plugin_info?.request_params && (() => {
                  const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])
                  const visiblePluginParams = pluginData.data.plugin_info.request_params.filter(p =>
                    p.is_runtime !== false && !toolParamNames.has(p.name)
                  )
                  return visiblePluginParams.length > 0
                })() && (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Typography variant="subtitle1" className="font-medium text-blue-600">
                        {t('plugins.toolConfig.pluginParams', '插件参数')}
                      </Typography>
                      <Chip label={`${(() => {
                        const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])
                        return pluginData.data.plugin_info.request_params.filter(p =>
                          p.is_runtime !== false && !toolParamNames.has(p.name)
                        ).length
                      })()}`} size="small" color="primary" />
                    </div>
                    {pluginData.data.plugin_info.request_params
                      .filter(p => {
                        const toolParamNames = new Set(tool?.input_parameters?.map(p => p.name) || [])
                        return p.is_runtime !== false && !toolParamNames.has(p.name)
                      })
                      .map((param, index) => {
                        const typeString = typeof param.type === 'number' ? mapNumberToString(param.type) : param.type
                        const paramValue = testParameters[`plugin_${param.name}`] || ''
                        const isRequiredAndEmpty = param.is_required && (!paramValue || paramValue.trim() === '')
                        const validationError = testParameterErrors[`plugin_${param.name}`] || ''
                        const hasError = isRequiredAndEmpty || !!validationError
                        return (
                          <div
                            key={`plugin-param-${index}`}
                            className={`space-y-2 p-3 rounded-lg border ${hasError ? 'bg-red-50 border-red-300' : 'bg-blue-50 border-blue-200'}`}
                          >
                            <div className="flex items-center space-x-2">
                              <Typography variant="subtitle2" className={`font-medium ${hasError ? 'text-red-700' : ''}`}>
                                {param.name}
                                {param.is_required && <span className="text-red-500 ml-1">*</span>}
                              </Typography>
                              <Chip label={typeString} size="small" variant="outlined" color="primary" />
                              {param.is_required && <Chip label={t('plugins.toolConfig.required')} size="small" color="error" variant="outlined" />}
                            </div>
                            <Typography variant="body2" color="text.secondary" className="text-sm">
                              {param.desc || t('plugins.toolConfig.noDescription')}
                            </Typography>
                            {typeString === 'boolean' ? (
                              <FormControlLabel
                                control={
                                  <Switch
                                    checked={paramValue === 'true'}
                                    onChange={e => handleTestParameterChange(param.name, e.target.checked.toString(), 'plugin')}
                                    color="primary"
                                  />
                                }
                                label={paramValue === 'true' ? 'TRUE' : 'FALSE'}
                              />
                            ) : (
                              <TextField
                                fullWidth
                                size="small"
                                value={paramValue}
                                onChange={e => handleTestParameterChange(param.name, e.target.value, 'plugin', typeString)}
                                placeholder={t('plugins.toolConfig.enterParamName', { name: param.name })}
                                multiline={typeString === 'object'}
                                rows={typeString === 'object' ? 3 : 1}
                                error={hasError}
                                helperText={validationError || (isRequiredAndEmpty ? t('plugins.toolConfig.thisRequiredField') : '')}
                              />
                            )}
                          </div>
                        )
                      })}
                  </div>
                )}

                {/* Tool-level Parameters - 只显示运行时参数 */}
                {tool?.input_parameters && tool.input_parameters.filter(p => p.is_runtime !== false).length > 0 && (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Typography variant="subtitle1" className="font-medium text-green-600">
                        {t('plugins.toolConfig.toolParams', '工具参数')}
                      </Typography>
                      <Chip label={`${tool.input_parameters.filter(p => p.is_runtime !== false).length}`} size="small" color="success" />
                    </div>
                    {tool.input_parameters
                      .filter(p => p.is_runtime !== false)
                      .map(param => {
                        const paramValue = testParameters[`tool_${param.name}`] || ''
                        const isRequiredAndEmpty = param.is_required && (!paramValue || paramValue.trim() === '')
                        const validationError = testParameterErrors[`tool_${param.name}`] || ''
                        const hasError = isRequiredAndEmpty || !!validationError
                        return (
                          <div
                            key={param.id}
                            className={`space-y-2 p-3 rounded-lg border ${hasError ? 'bg-red-50 border-red-300' : 'bg-green-50 border-green-200'}`}
                          >
                            <div className="flex items-center space-x-2">
                              <Typography variant="subtitle2" className={`font-medium ${hasError ? 'text-red-700' : ''}`}>
                                {param.name}
                                {param.is_required && <span className="text-red-500 ml-1">*</span>}
                              </Typography>
                              <Chip label={param.type} size="small" variant="outlined" color="success" />
                              {param.is_required && <Chip label={t('plugins.toolConfig.required')} size="small" color="error" variant="outlined" />}
                            </div>
                            <Typography variant="body2" color="text.secondary" className="text-sm">
                              {param.description}
                            </Typography>
                            {param.type === 'boolean' ? (
                              <FormControlLabel
                                control={
                                  <Switch
                                    checked={paramValue === 'true'}
                                    onChange={e => handleTestParameterChange(param.name, e.target.checked.toString(), 'tool')}
                                    color="primary"
                                  />
                                }
                                label={paramValue === 'true' ? 'TRUE' : 'FALSE'}
                              />
                            ) : (
                              <TextField
                                fullWidth
                                size="small"
                                value={paramValue}
                                onChange={e => handleTestParameterChange(param.name, e.target.value, 'tool', param.type)}
                                placeholder={t('plugins.toolConfig.enterParamName', { name: param.name })}
                                multiline={param.type === 'object'}
                                rows={param.type === 'object' ? 3 : 1}
                                error={hasError}
                                helperText={validationError || (isRequiredAndEmpty ? t('plugins.toolConfig.thisRequiredField') : '')}
                              />
                            )}
                          </div>
                        )
                      })}
                  </div>
                )}

                {/* No parameters message */}
                {(!pluginData?.data?.plugin_info?.request_params || pluginData.data.plugin_info.request_params.length === 0) &&
                  (!tool?.input_parameters || tool.input_parameters.length === 0) && (
                    <div className="bg-gray-50 rounded-lg p-6 text-center">
                      <Typography variant="body1" color="text.secondary">
                        {t('plugins.toolConfig.noInputParams', '该工具没有输入参数')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t('plugins.toolConfig.canExecuteTest', '可以直接执行测试')}
                      </Typography>
                    </div>
                  )}
              </div>

              <div className="pt-4 border-t space-y-3">
                {(() => {
                  const { isValid, missingParams } = validateRequiredParameters()
                  return (
                    <>
                      {!isValid && missingParams.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <Typography variant="body2" color="error" className="font-medium">
                            {t('plugins.toolConfig.missingRequiredParams', '缺少必填参数')}
                          </Typography>
                          <Typography variant="caption" color="error">
                            {t('plugins.toolConfig.pleaseFillRequiredParams', '请填写以下必填参数')}: {missingParams.join(', ')}
                          </Typography>
                        </div>
                      )}
                      <Button
                        variant="contained"
                        onClick={handleExecuteTest}
                        disabled={isTestRunning || executePluginMutation.isPending || !isValid}
                        fullWidth
                        startIcon={isTestRunning || executePluginMutation.isPending ? <CircularProgress size={16} /> : <Settings className="w-4 h-4" />}
                      >
                        {isTestRunning || executePluginMutation.isPending
                          ? t('plugins.tools.test.executing', '执行中...')
                          : t('plugins.tools.test.executeTest', '执行测试')}
                      </Button>
                    </>
                  )
                })()}
              </div>
            </div>

            {/* Right Side - Test Results */}
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Typography variant="h6">{t('plugins.tools.test.testResults')}</Typography>
                <Typography variant="body2" color="text.secondary">
                  ({t('plugins.toolConfig.apiCallReturn', 'API调用返回')})
                </Typography>
              </div>

              {testError ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <Typography variant="body1" color="error" className="font-medium">
                    {t('plugins.toolConfig.testFailed', '测试失败')}
                  </Typography>
                  <Typography variant="body2" color="error">
                    {testError}
                  </Typography>
                </div>
              ) : testResults ? (
                <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
                  {(() => {
                    try {
                      const results = JSON.parse(testResults)
                      return (
                        <div className="space-y-4">
                          {/* 执行状态 */}
                          <div className="flex items-center space-x-2">
                            <div className={`w-3 h-3 rounded-full ${results.execution_success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                            <Typography variant="subtitle2" className="font-medium">
                              {t('plugins.toolConfig.executionStatus', '执行状态')}: {results.execution_success ? 'success' : 'error'}
                            </Typography>
                            {results.error_code !== null && (
                              <Chip
                                label={`${t('plugins.toolConfig.errorCode', '错误码')}: ${results.error_code}`}
                                size="small"
                                variant={results.error_message === 'success' ? 'outlined' : 'filled'}
                                color={results.error_message === 'success' ? 'success' : 'error'}
                              />
                            )}
                          </div>

                          {/* 错误信息 */}
                          {results.error_message && (
                            <div className={`p-3 rounded border ${results.execution_success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                              <Typography variant="body2" className="font-medium mb-1">
                                {t('plugins.toolConfig.executionMessage', '执行消息')}:
                              </Typography>
                              <Typography variant="body2" className={results.execution_success ? 'text-green-800' : 'text-red-800'}>
                                {results.error_message}
                              </Typography>
                            </div>
                          )}

                          {/* 结构化输出参数显示 */}
                          {tool?.output_parameters && tool.output_parameters.length > 0 && (
                            <div className="bg-blue-50 border border-blue-200 rounded p-3">
                              <Typography variant="subtitle2" className="font-medium text-blue-800 mb-3">
                                {t('plugins.toolConfig.outputResult', '📊 输出参数结果')}
                              </Typography>
                              <div className="space-y-3">
                                {(() => {
                                  const outputValues = extractOutputParameterValues(results)
                                  return tool.output_parameters.map(param => (
                                    <div key={param.id} className="bg-white rounded p-3 border border-blue-100">
                                      <div className="flex items-center justify-between mb-1">
                                        <Typography variant="body2" className="font-medium text-gray-700">
                                          {param.name}
                                        </Typography>
                                        <Chip label={param.type} size="small" variant="outlined" />
                                      </div>
                                      <Typography variant="body2" color="text.secondary" className="mb-2 text-sm">
                                        {param.description}
                                      </Typography>
                                      <div className="bg-gray-50 rounded p-2 border border-gray-200">
                                        <Typography variant="body2" className="font-mono text-sm break-all">
                                          {formatOutputValue(outputValues[param.name], param.type)}
                                        </Typography>
                                      </div>
                                    </div>
                                  ))
                                })()}
                              </div>
                            </div>
                          )}

                          {/* 原始输出结果 */}
                          {results.output && (
                            <details className="text-sm">
                              <summary className="cursor-pointer text-blue-600 hover:text-blue-800 font-medium mb-2">
                                {t('plugins.toolConfig.viewRawOutput', '📄 查看完整原始输出')}
                              </summary>
                              <div className="bg-white border border-gray-200 rounded p-3 mt-2">
                                <pre className="text-sm text-gray-800 whitespace-pre-wrap bg-gray-100 p-2 rounded">
                                  {JSON.stringify(results.output, null, 2)}
                                </pre>
                              </div>
                            </details>
                          )}

                          {/* 原始响应（仅在有错误或调试时显示） */}
                          {results.raw_response && !results.execution_success && (
                            <details className="text-sm">
                              <summary className="cursor-pointer text-blue-600 hover:text-blue-800">
                                {t('plugins.toolConfig.viewRawResponse', '查看原始响应数据')}
                              </summary>
                              <pre className="text-xs text-gray-600 mt-2 whitespace-pre-wrap bg-gray-100 p-2 rounded">
                                {JSON.stringify(results.raw_response, null, 2)}
                              </pre>
                            </details>
                          )}

                          {/* 解析错误信息 */}
                          {results.parse_error && (
                            <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                              <Typography variant="body2" className="font-medium text-yellow-800 mb-1">
                                {t('plugins.toolConfig.parseError', '解析错误:')}
                              </Typography>
                              <Typography variant="body2" className="text-yellow-700">
                                {results.parse_error}
                              </Typography>
                              {results.raw_buffer && (
                                <details className="text-sm mt-2">
                                  <summary className="cursor-pointer text-yellow-600 hover:text-yellow-800">
                                    {t('plugins.toolConfig.viewRawData', '查看原始数据')}
                                  </summary>
                                  <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap bg-yellow-50 p-2 rounded">{results.raw_buffer}</pre>
                                </details>
                              )}
                            </div>
                          )}

                          {/* 执行时间戳 */}
                          {results.timestamp && (
                            <div className="text-xs text-gray-500 border-t pt-2">
                              {t('plugins.toolConfig.executionTime', '执行时间:')} {new Date(results.timestamp).toLocaleString('zh-CN')}
                            </div>
                          )}
                        </div>
                      )
                    } catch {
                      // 如果JSON解析失败，直接显示原始文本
                      return (
                        <div className="space-y-2">
                          <Typography variant="body2" color="error">
                            {t('plugins.toolConfig.resultParseFailed', '结果解析失败，显示原始数据')}:
                          </Typography>
                          <pre className="text-sm text-gray-800 whitespace-pre-wrap bg-red-50 p-2 rounded border border-red-200">{testResults}</pre>
                        </div>
                      )
                    }
                  })()}
                </div>
              ) : (
                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <Typography variant="body1" color="text.secondary">
                    {t('plugins.toolConfig.noResults', '暂无测试结果')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t('plugins.toolConfig.fillParamsHint', '填写参数后点击"执行测试"查看结果')}
                  </Typography>
                </div>
              )}

              <div className="pt-4 border-t space-y-2">
                <Typography variant="subtitle2" className="font-medium">
                  {t('plugins.toolConfig.testInfo', '测试信息')}
                </Typography>
                <div className="space-y-1 text-sm text-gray-600">
                  <Typography
                    component="div"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '70ch',
                    }}
                  >
                    {t('plugins.tools.test.apiPath', 'API路径')}: {tool?.path}
                  </Typography>
                  <div>
                    {t('plugins.tools.test.requestMethod', '请求方法')}: {tool && getMethodString(tool.method)}
                  </div>
                  <div>
                    {t('plugins.tools.test.testTime', '测试时间')}: {new Date().toLocaleString('zh-CN')}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialogOpen(false)}>{t('common.buttons.close', '关闭')}</Button>
          {testResults && (
            <Button
              variant="outlined"
              onClick={() => {
                copyToClipboard(testResults, setSnackbar, t('plugins.toolConfig.resultCopied'))
              }}
            >
              {t('plugins.toolConfig.copyResult', '复制结果')}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={2000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  )
}

export default ToolConfigurationPage
