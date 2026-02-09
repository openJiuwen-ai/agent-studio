import React, { useState, useEffect, useRef } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  IconButton,
  Tooltip,
  Box,
  Tabs,
  Tab,
  Snackbar,
  Alert,
} from '@mui/material'
import { useTranslation } from 'react-i18next'
import { Code, X, Trash2, Plus, Eye, ChevronDown, ChevronRight, Layers } from 'lucide-react'
import FieldEditor from './FieldEditor'
import JsonEditor from './JsonEditor'
import { ToolParameter } from '@/types/promptType'

// 数据类型常量 - 与 ColumnConfigCard 保持一致
const DATA_TYPES = {
  STRING: 'String',
  INTEGER: 'Integer',
  NUMBER: 'Number',
  BOOLEAN: 'Boolean',
  OBJECT: 'Object',
  ARRAY_STRING: 'Array<String>',
  ARRAY_INTEGER: 'Array<Integer>',
  ARRAY_NUMBER: 'Array<Number>',
  ARRAY_BOOLEAN: 'Array<Boolean>',
  ARRAY_OBJECT: 'Array<Object>',
} as const

// 工具接口
export interface EditingTool {
  id: string
  name: string
  description: string
  defaultValue?: string
  fieldType?: 'PlainText' | 'JSON'
  parameters: ToolParameter[]
  parametersJsonSchema?: string // 保存原始的JSON Schema，用于保留高级特性（enum、format等）
  parametersMode?: 'visual' | 'json' // 参数模式：visual（可视化）或 json（JSON配置）
}

// 组件Props接口
export interface ToolEditDialogProps {
  open: boolean
  editingTool: EditingTool | null
  onClose: () => void
  onSave: (updatedTool: EditingTool) => void // 接收更新后的工具对象
  onToolChange: (tool: EditingTool | null) => void
  showDefaultValue?: boolean
}

const ToolEditDialog: React.FC<ToolEditDialogProps> = ({ open, editingTool, onClose, onSave, onToolChange, showDefaultValue = true }) => {
  const { t } = useTranslation()

  // 参数配置相关状态
  const [parametersExpanded, setParametersExpanded] = useState(true)
  const [parametersMode, setParametersMode] = useState<'visual' | 'json'>('visual')
  const [parametersJsonSchema, setParametersJsonSchema] = useState<string>('')
  const [originalJsonSchema, setOriginalJsonSchema] = useState<string>('') // 保存从JSON切换到可视化时的原始JSON
  const [visualParametersModified, setVisualParametersModified] = useState(false) // 标记可视化参数是否被修改

  // Snackbar 状态
  const [snackbarOpen, setSnackbarOpen] = useState(false)
  const [snackbarMessage, setSnackbarMessage] = useState('')

  // 确认对话框状态
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [confirmDialogMessage, setConfirmDialogMessage] = useState('')
  const [pendingMode, setPendingMode] = useState<'visual' | 'json' | null>(null)

  // 使用 ref 跟踪是否已经初始化过，避免在用户编辑时重复初始化
  const initializedRef = useRef<{ toolId: string | null; open: boolean }>({ toolId: null, open: false })

  // 当对话框打开或editingTool变化时，如果它有parametersJsonSchema，加载它
  useEffect(() => {
    // 只有当对话框打开且有editingTool时才初始化
    if (!open || !editingTool) {
      // 对话框关闭时，重置状态和初始化标记
      if (!open) {
        setParametersMode('visual')
        setParametersJsonSchema('')
        setOriginalJsonSchema('')
        setVisualParametersModified(false)
        initializedRef.current = { toolId: null, open: false }
      }
      return
    }

    // 检查是否需要初始化：只在对话框刚打开或工具ID变化时初始化
    const shouldInitialize =
      !initializedRef.current.open || // 对话框刚打开
      initializedRef.current.toolId !== editingTool.id // 工具ID变化

    if (!shouldInitialize) {
      return // 如果已经初始化过且工具ID没变，不重新初始化（避免覆盖用户编辑）
    }

    // 标记为已初始化
    initializedRef.current = { toolId: editingTool.id, open: true }

    // 重置修改标记（每次打开对话框时重置）
    setVisualParametersModified(false)

    // 优先使用工具保存的参数模式，如果没有则根据是否有JSON Schema判断
    console.log('🔧 [ToolEditDialog] 初始化参数模式:', {
      toolName: editingTool.name,
      parametersMode: editingTool.parametersMode,
      hasJsonSchema: !!(editingTool.parametersJsonSchema && editingTool.parametersJsonSchema.trim()),
    })

    if (editingTool.parametersMode) {
      console.log(`🔧 [ToolEditDialog] 使用工具保存的参数模式: ${editingTool.parametersMode}`)
      setParametersMode(editingTool.parametersMode)
    } else if (editingTool.parametersJsonSchema && editingTool.parametersJsonSchema.trim()) {
      // 如果工具有JSON Schema但没有保存模式，默认使用JSON模式
      console.log('🔧 [ToolEditDialog] 工具没有保存参数模式，但有JSON Schema，使用JSON模式')
      setParametersMode('json')
    } else {
      // 如果没有JSON Schema，使用可视化模式
      console.log('🔧 [ToolEditDialog] 工具没有保存参数模式，也没有JSON Schema，使用可视化模式')
      setParametersMode('visual')
    }

    // 检查是否有parametersJsonSchema
    if (editingTool.parametersJsonSchema && editingTool.parametersJsonSchema.trim()) {
      setParametersJsonSchema(editingTool.parametersJsonSchema)
      setOriginalJsonSchema(editingTool.parametersJsonSchema)
    } else {
      setParametersJsonSchema('')
      setOriginalJsonSchema('')
    }
  }, [open, editingTool?.id]) // 只在对话框打开或工具ID变化时重新初始化，移除对 parametersJsonSchema 的依赖

  // 添加参数
  const handleAddParameter = () => {
    if (!editingTool) return
    setVisualParametersModified(true) // 标记可视化参数已被修改
    onToolChange({
      ...editingTool,
      parameters: [
        ...editingTool.parameters,
        {
          name: '',
          type: DATA_TYPES.STRING,
          description: '',
          required: false,
        },
      ],
    })
  }

  // 删除参数
  const handleRemoveParameter = (index: number) => {
    if (!editingTool) return
    setVisualParametersModified(true) // 标记可视化参数已被修改
    onToolChange({
      ...editingTool,
      parameters: editingTool.parameters.filter((_, i) => i !== index),
    })
  }

  // 修改参数
  const handleToolParameterChange = (index: number, field: string, value: string | boolean) => {
    if (!editingTool) return
    setVisualParametersModified(true) // 标记可视化参数已被修改
    onToolChange({
      ...editingTool,
      parameters: editingTool.parameters.map((param, i) => (i === index ? { ...param, [field]: value } : param)),
    })
  }

  // 获取参数名称的错误信息
  const getParameterNameError = (paramName: string, currentIndex: number): string => {
    if (!paramName.trim()) return ''

    // 检查格式（只能包含英文字母、数字、下划线、连字符，必须以英文字母开头）
    const namePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
    if (!namePattern.test(paramName.trim())) {
      return t('components.prompts.toolEditDialog.parameterNameFormatError')
    }

    // 检查重复
    const otherParams = editingTool?.parameters.filter((_, i) => i !== currentIndex) || []
    if (otherParams.some(p => p.name.trim() === paramName.trim())) {
      return t('components.prompts.toolEditDialog.parameterNameDuplicateError')
    }

    return ''
  }

  // 检查是否有验证错误，用于禁用保存按钮
  const hasValidationErrors = (): boolean => {
    if (!editingTool) return true

    // 检查工具名称
    const toolName = editingTool.name || ''
    if (!toolName.trim()) return true

    const toolNamePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
    if (!toolNamePattern.test(toolName.trim())) return true

    // 工具描述允许为空，不需要检查

    // 检查参数
    for (let i = 0; i < editingTool.parameters.length; i++) {
      const param = editingTool.parameters[i]

      // 检查参数名称
      if (!param.name.trim()) return true
      if (getParameterNameError(param.name, i)) return true

      // 参数描述允许为空，不需要检查
    }

    return false
  }

  // 验证工具参数格式
  const validateToolParameters = (parameters: ToolParameter[]): string | null => {
    // 1. 验证参数数量
    if (parameters.length > 50) {
      return t('components.prompts.toolEditDialog.validation.tooManyParameters', { count: parameters.length })
    }

    // 2. 验证参数名称重复
    const paramNames = parameters.map(p => p.name.trim()).filter(name => name)
    const duplicateNames = paramNames.filter((name, index) => paramNames.indexOf(name) !== index)
    if (duplicateNames.length > 0) {
      return t('components.prompts.toolEditDialog.validation.duplicateParameterNames', { names: duplicateNames.join(', ') })
    }

    // 3. 逐个验证参数
    for (let i = 0; i < parameters.length; i++) {
      const param = parameters[i]
      const paramIndex = i + 1

      // 验证参数名称
      if (!param.name || !param.name.trim()) {
        return t('components.prompts.toolEditDialog.validation.parameterNameEmpty', { index: paramIndex })
      }

      // 验证参数名称格式（只能包含英文字母、数字、下划线、连字符，必须以英文字母开头）
      const namePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
      if (!namePattern.test(param.name.trim())) {
        return t('components.prompts.toolEditDialog.validation.parameterNameFormatInvalid', { name: param.name })
      }

      // 验证参数名称长度
      if (param.name.length > 100) {
        return t('components.prompts.toolEditDialog.validation.parameterNameTooLong', { name: param.name, length: param.name.length })
      }

      // 验证参数类型
      const validTypes = Object.values(DATA_TYPES) as string[]
      if (!validTypes.includes(param.type)) {
        return t('components.prompts.toolEditDialog.validation.parameterTypeInvalid', { name: param.name, type: param.type })
      }

      // 验证参数描述长度（允许为空）
      if (param.description && param.description.length > 500) {
        return t('components.prompts.toolEditDialog.validation.parameterDescriptionTooLong', { name: param.name, length: param.description.length })
      }

      // 验证必填字段的逻辑性
      if (param.required === undefined || param.required === null) {
        return t('components.prompts.toolEditDialog.validation.parameterRequiredNotSpecified', { name: param.name })
      }
    }

    return null
  }

  // 验证JSON Schema格式
  const validateJsonSchema = (jsonSchemaStr: string): string | null => {
    try {
      const schema = JSON.parse(jsonSchemaStr)

      // 验证根级别结构
      if (typeof schema !== 'object' || schema === null) {
        return t('components.prompts.toolEditDialog.validation.jsonSchemaMustBeObject')
      }

      if (schema.type !== 'object') {
        return t('components.prompts.toolEditDialog.validation.jsonSchemaRootTypeMustBeObject')
      }

      // 允许空的 properties 对象（删除所有参数的情况）
      if (schema.properties === undefined || schema.properties === null) {
        return t('components.prompts.toolEditDialog.validation.jsonSchemaMustHaveProperties')
      }
      if (typeof schema.properties !== 'object') {
        return t('components.prompts.toolEditDialog.validation.jsonSchemaPropertiesMustBeObject')
      }

      // 验证properties中的每个属性
      const properties = schema.properties
      for (const [propName, propDef] of Object.entries(properties)) {
        if (typeof propDef !== 'object' || propDef === null) {
          return t('components.prompts.toolEditDialog.validation.propertyDefinitionMustBeObject', { name: propName })
        }

        const prop = propDef as Record<string, unknown>

        // 验证type字段
        if (!prop.type) {
          return t('components.prompts.toolEditDialog.validation.propertyMissingType', { name: propName })
        }

        const validJsonTypes = ['string', 'number', 'integer', 'boolean', 'array', 'object']

        // type必须是单个字符串
        if (typeof prop.type !== 'string' || !validJsonTypes.includes(prop.type)) {
          return t('components.prompts.toolEditDialog.validation.propertyTypeInvalid', { name: propName, type: prop.type, validTypes: validJsonTypes.join(', ') })
        }

        // 验证数组类型的items
        if (prop.type === 'array') {
          if (!prop.items || typeof prop.items !== 'object') {
            return t('components.prompts.toolEditDialog.validation.arrayPropertyMustHaveItems', { name: propName })
          }

          const items = prop.items as Record<string, unknown>
          const validItemTypes = ['string', 'number', 'integer', 'boolean', 'object']
          if (!items.type || !validItemTypes.includes(items.type as string)) {
            return t('components.prompts.toolEditDialog.validation.arrayPropertyItemsTypeInvalid', { name: propName, validTypes: validItemTypes.join(', ') })
          }
        }

        // 验证description字段
        if (prop.description && typeof prop.description !== 'string') {
          return t('components.prompts.toolEditDialog.validation.propertyDescriptionMustBeString', { name: propName })
        }

        // 验证通用约束关键字

        // 验证enum约束（适用于所有类型）
        if (prop.enum !== undefined) {
          if (!Array.isArray(prop.enum)) {
            return t('components.prompts.toolEditDialog.validation.propertyEnumMustBeArray', { name: propName })
          }
          if (prop.enum.length === 0) {
            return t('components.prompts.toolEditDialog.validation.propertyEnumCannotBeEmpty', { name: propName })
          }

          // 验证enum值与类型的一致性
          const propType = prop.type as string
          for (let i = 0; i < prop.enum.length; i++) {
            const enumValue = prop.enum[i] as unknown
            if (!validateEnumValueType(enumValue, propType)) {
              return t('components.prompts.toolEditDialog.validation.propertyEnumValueTypeMismatch', { name: propName, value: String(enumValue), type: propType })
            }
          }

          // 检查enum值是否有重复
          const uniqueValues = new Set(prop.enum)
          if (uniqueValues.size !== prop.enum.length) {
            return t('components.prompts.toolEditDialog.validation.propertyEnumValuesDuplicate', { name: propName })
          }
        }

        // 验证类型特定的约束关键字
        const propType = prop.type as string

        // 判断类型
        const hasStringType = propType === 'string'
        const hasNumberType = propType === 'number' || propType === 'integer'
        const hasIntegerType = propType === 'integer'
        const hasBooleanType = propType === 'boolean'
        const hasArrayType = propType === 'array'
        const hasObjectType = propType === 'object'

        // 验证string类型的约束
        if (hasStringType) {
          if (prop.minLength !== undefined && (typeof prop.minLength !== 'number' || prop.minLength < 0)) {
            return t('components.prompts.toolEditDialog.validation.propertyMinLengthMustBeNonNegative', { name: propName })
          }
          if (prop.maxLength !== undefined && (typeof prop.maxLength !== 'number' || prop.maxLength < 0)) {
            return t('components.prompts.toolEditDialog.validation.propertyMaxLengthMustBeNonNegative', { name: propName })
          }
          if (prop.minLength !== undefined && prop.maxLength !== undefined && prop.minLength > prop.maxLength) {
            return t('components.prompts.toolEditDialog.validation.propertyMinLengthCannotExceedMaxLength', { name: propName })
          }
          if (prop.pattern !== undefined && typeof prop.pattern !== 'string') {
            return t('components.prompts.toolEditDialog.validation.propertyPatternMustBeString', { name: propName })
          }

          // 增强的format验证
          if (prop.format !== undefined) {
            if (typeof prop.format !== 'string') {
              return t('components.prompts.toolEditDialog.validation.propertyFormatMustBeString', { name: propName })
            }
            const validFormats = [
              'date',
              'date-time',
              'time',
              'duration',
              'email',
              'idn-email',
              'hostname',
              'idn-hostname',
              'ipv4',
              'ipv6',
              'uri',
              'uri-reference',
              'uri-template',
              'iri',
              'iri-reference',
              'uuid',
              'regex',
              'json-pointer',
              'relative-json-pointer',
            ]
            if (!validFormats.includes(prop.format)) {
              return t('components.prompts.toolEditDialog.validation.propertyFormatInvalid', { name: propName, format: prop.format, validFormats: validFormats.join(', ') })
            }
          }
        }

        // 验证number和integer类型的约束
        if (hasNumberType) {
          if (prop.minimum !== undefined && typeof prop.minimum !== 'number') {
            return t('components.prompts.toolEditDialog.validation.propertyMinimumMustBeNumber', { name: propName })
          }
          if (prop.maximum !== undefined && typeof prop.maximum !== 'number') {
            return t('components.prompts.toolEditDialog.validation.propertyMaximumMustBeNumber', { name: propName })
          }
          if (prop.exclusiveMinimum !== undefined && typeof prop.exclusiveMinimum !== 'number') {
            return t('components.prompts.toolEditDialog.validation.propertyExclusiveMinimumMustBeNumber', { name: propName })
          }
          if (prop.exclusiveMaximum !== undefined && typeof prop.exclusiveMaximum !== 'number') {
            return t('components.prompts.toolEditDialog.validation.propertyExclusiveMaximumMustBeNumber', { name: propName })
          }

          // 验证边界值的逻辑关系
          if (prop.minimum !== undefined && prop.maximum !== undefined && prop.minimum > prop.maximum) {
            return t('components.prompts.toolEditDialog.validation.propertyMinimumCannotExceedMaximum', { name: propName })
          }
          if (prop.exclusiveMinimum !== undefined && prop.exclusiveMaximum !== undefined && prop.exclusiveMinimum >= prop.exclusiveMaximum) {
            return t('components.prompts.toolEditDialog.validation.propertyExclusiveMinimumMustBeLessThanExclusiveMaximum', { name: propName })
          }
          if (prop.minimum !== undefined && prop.exclusiveMaximum !== undefined && prop.minimum >= prop.exclusiveMaximum) {
            return t('components.prompts.toolEditDialog.validation.propertyMinimumCannotExceedExclusiveMaximum', { name: propName })
          }
          if (prop.exclusiveMinimum !== undefined && prop.maximum !== undefined && prop.exclusiveMinimum >= prop.maximum) {
            return t('components.prompts.toolEditDialog.validation.propertyExclusiveMinimumMustBeLessThanMaximum', { name: propName })
          }

          if (prop.multipleOf !== undefined && (typeof prop.multipleOf !== 'number' || prop.multipleOf <= 0)) {
            return t('components.prompts.toolEditDialog.validation.propertyMultipleOfMustBePositive', { name: propName })
          }

          if (hasIntegerType) {
            if (prop.minimum !== undefined && !Number.isInteger(prop.minimum)) {
              return t('components.prompts.toolEditDialog.validation.integerPropertyMinimumMustBeInteger', { name: propName })
            }
            if (prop.maximum !== undefined && !Number.isInteger(prop.maximum)) {
              return t('components.prompts.toolEditDialog.validation.integerPropertyMaximumMustBeInteger', { name: propName })
            }
            if (prop.exclusiveMinimum !== undefined && !Number.isInteger(prop.exclusiveMinimum)) {
              return t('components.prompts.toolEditDialog.validation.integerPropertyExclusiveMinimumMustBeInteger', { name: propName })
            }
            if (prop.exclusiveMaximum !== undefined && !Number.isInteger(prop.exclusiveMaximum)) {
              return t('components.prompts.toolEditDialog.validation.integerPropertyExclusiveMaximumMustBeInteger', { name: propName })
            }
            if (prop.multipleOf !== undefined && !Number.isInteger(prop.multipleOf)) {
              return t('components.prompts.toolEditDialog.validation.integerPropertyMultipleOfMustBeInteger', { name: propName })
            }
          }
        }

        // 验证boolean类型的约束
        if (hasBooleanType) {
          // 只有当类型仅为boolean时，enum才只能包含boolean值
          if (prop.enum && prop.enum.some((val: unknown) => typeof val !== 'boolean')) {
            return t('components.prompts.toolEditDialog.validation.booleanPropertyEnumMustBeBoolean', { name: propName })
          }
        }

        // 验证array类型的约束
        if (hasArrayType) {
          if (prop.minItems !== undefined && (typeof prop.minItems !== 'number' || prop.minItems < 0 || !Number.isInteger(prop.minItems))) {
            return t('components.prompts.toolEditDialog.validation.propertyMinItemsMustBeNonNegativeInteger', { name: propName })
          }
          if (prop.maxItems !== undefined && (typeof prop.maxItems !== 'number' || prop.maxItems < 0 || !Number.isInteger(prop.maxItems))) {
            return t('components.prompts.toolEditDialog.validation.propertyMaxItemsMustBeNonNegativeInteger', { name: propName })
          }
          if (prop.minItems !== undefined && prop.maxItems !== undefined && prop.minItems > prop.maxItems) {
            return t('components.prompts.toolEditDialog.validation.propertyMinItemsCannotExceedMaxItems', { name: propName })
          }
          if (prop.uniqueItems !== undefined && typeof prop.uniqueItems !== 'boolean') {
            return t('components.prompts.toolEditDialog.validation.propertyUniqueItemsMustBeBoolean', { name: propName })
          }

          // 验证additionalItems（如果存在items数组的话）
          if (prop.additionalItems !== undefined && typeof prop.additionalItems !== 'boolean' && typeof prop.additionalItems !== 'object') {
            return t('components.prompts.toolEditDialog.validation.propertyAdditionalItemsMustBeBooleanOrObject', { name: propName })
          }
        }

        // 验证object类型的约束
        if (hasObjectType) {
          if (prop.properties && typeof prop.properties !== 'object') {
            return t('components.prompts.toolEditDialog.validation.objectPropertyPropertiesMustBeObject', { name: propName })
          }
          if (prop.required && !Array.isArray(prop.required)) {
            return t('components.prompts.toolEditDialog.validation.objectPropertyRequiredMustBeArray', { name: propName })
          }
          if (prop.additionalProperties !== undefined && typeof prop.additionalProperties !== 'boolean' && typeof prop.additionalProperties !== 'object') {
            return t('components.prompts.toolEditDialog.validation.objectPropertyAdditionalPropertiesMustBeBooleanOrObject', { name: propName })
          }
          if (prop.minProperties !== undefined && (typeof prop.minProperties !== 'number' || prop.minProperties < 0 || !Number.isInteger(prop.minProperties))) {
            return t('components.prompts.toolEditDialog.validation.propertyMinPropertiesMustBeNonNegativeInteger', { name: propName })
          }
          if (prop.maxProperties !== undefined && (typeof prop.maxProperties !== 'number' || prop.maxProperties < 0 || !Number.isInteger(prop.maxProperties))) {
            return t('components.prompts.toolEditDialog.validation.propertyMaxPropertiesMustBeNonNegativeInteger', { name: propName })
          }
          if (prop.minProperties !== undefined && prop.maxProperties !== undefined && prop.minProperties > prop.maxProperties) {
            return t('components.prompts.toolEditDialog.validation.propertyMinPropertiesCannotExceedMaxProperties', { name: propName })
          }
          if (prop.patternProperties && typeof prop.patternProperties !== 'object') {
            return t('components.prompts.toolEditDialog.validation.objectPropertyPatternPropertiesMustBeObject', { name: propName })
          }

          // 验证patternProperties中的正则表达式
          if (prop.patternProperties) {
            for (const pattern of Object.keys(prop.patternProperties)) {
              try {
                new RegExp(pattern)
              } catch (error) {
                return t('components.prompts.toolEditDialog.validation.objectPropertyPatternPropertiesInvalidRegex', { name: propName, pattern })
              }
            }
          }

          // 验证dependencies（如果存在）
          if (prop.dependencies && typeof prop.dependencies !== 'object') {
            return t('components.prompts.toolEditDialog.validation.objectPropertyDependenciesMustBeObject', { name: propName })
          }
        }
      }

      // 验证required字段
      if (schema.required && !Array.isArray(schema.required)) {
        return t('components.prompts.toolEditDialog.validation.jsonSchemaRequiredMustBeArray')
      }

      if (schema.required) {
        for (const requiredProp of schema.required) {
          if (typeof requiredProp !== 'string') {
            return t('components.prompts.toolEditDialog.validation.jsonSchemaRequiredElementsMustBeString')
          }
          if (!properties[requiredProp]) {
            return t('components.prompts.toolEditDialog.validation.jsonSchemaRequiredPropertyNotFound', { name: requiredProp })
          }
        }
      }

      return null
    } catch (error) {
      return t('components.prompts.toolEditDialog.validation.jsonFormatError', { error: error instanceof Error ? error.message : t('common.messages.unknownError') })
    }
  }

  // 验证enum值类型的辅助函数
  const validateEnumValueType = (value: unknown, expectedType: string): boolean => {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string'
      case 'number':
        return typeof value === 'number' && !isNaN(value)
      case 'integer':
        return typeof value === 'number' && Number.isInteger(value)
      case 'boolean':
        return typeof value === 'boolean'
      default:
        return true // 对于object和array类型，暂时允许任何值
    }
  }

  // 切换参数配置模式（带确认对话框）
  const handleToggleParametersMode = (mode: 'visual' | 'json') => {
    // 如果切换到相同模式，直接返回
    if (mode === parametersMode) return

    // 设置待切换的模式
    setPendingMode(mode)

    // 根据切换方向设置提示信息
    if (mode === 'json') {
      // 从可视化配置切换到JSON配置
      setConfirmDialogMessage(t('components.prompts.toolEditDialog.switchToJsonMessage'))
    } else {
      // 从JSON模式切换到可视化配置
      setConfirmDialogMessage(t('components.prompts.toolEditDialog.switchToVisualMessage'))
    }

    // 显示确认对话框
    setConfirmDialogOpen(true)
  }

  // 确认切换模式
  const handleConfirmModeSwitch = () => {
    if (!pendingMode) return

    const mode = pendingMode

    if (mode === 'visual' && parametersJsonSchema) {
      // 从JSON模式切换到可视化模式时，保存原始JSON并解析为参数（不做格式校验）
      setOriginalJsonSchema(parametersJsonSchema) // 保存原始JSON
      setVisualParametersModified(false) // 重置修改标记
      try {
        const parameters = convertJsonSchemaToParameters(parametersJsonSchema)
        onToolChange({
          ...editingTool!,
          parameters,
        })
      } catch (error) {
        console.error('JSON Schema解析失败:', error)
        // 解析失败时仍然切换模式，但保持原有参数
      }
    } else if (mode === 'json' && editingTool) {
      // 从可视化模式切换到JSON模式时
      if (visualParametersModified || !originalJsonSchema) {
        // 如果可视化参数被修改过，或者没有原始JSON，则将当前参数转换为JSON Schema
        const jsonSchema = convertParametersToJsonSchema(editingTool.parameters)
        setParametersJsonSchema(jsonSchema)
      } else {
        // 如果可视化参数没有被修改，则恢复原始JSON
        setParametersJsonSchema(originalJsonSchema)
      }
    }

    setParametersMode(mode)
    setConfirmDialogOpen(false)
    setPendingMode(null)
  }

  // 取消切换模式
  const handleCancelModeSwitch = () => {
    setConfirmDialogOpen(false)
    setPendingMode(null)
  }

  // 将参数转换为JSON Schema
  const convertParametersToJsonSchema = (parameters: ToolParameter[]): string => {
    const properties: Record<string, any> = {}
    const required: string[] = []

    // 类型映射：从 UI 显示类型到 JSON Schema 类型
    const typeMapping: Record<string, string> = {
      [DATA_TYPES.STRING]: 'string',
      [DATA_TYPES.INTEGER]: 'integer',
      [DATA_TYPES.NUMBER]: 'number',
      [DATA_TYPES.BOOLEAN]: 'boolean',
      [DATA_TYPES.OBJECT]: 'object',
      [DATA_TYPES.ARRAY_STRING]: 'array',
      [DATA_TYPES.ARRAY_INTEGER]: 'array',
      [DATA_TYPES.ARRAY_NUMBER]: 'array',
      [DATA_TYPES.ARRAY_BOOLEAN]: 'array',
      [DATA_TYPES.ARRAY_OBJECT]: 'array',
    }

    parameters.forEach(param => {
      const jsonSchemaType = typeMapping[param.type] || 'string'
      const property: any = {
        type: jsonSchemaType,
        description: param.description,
      }

      // 如果是数组类型，添加 items 属性
      if (param.type.startsWith('Array<')) {
        // 提取数组元素类型，例如从 'Array<String>' 提取 'String'
        const itemTypeStr = param.type.replace('Array<', '').replace('>', '')
        // 构造完整的 DATA_TYPES 键，例如 'String' -> DATA_TYPES.STRING
        const itemTypeKey = DATA_TYPES[itemTypeStr.toUpperCase() as keyof typeof DATA_TYPES]
        const itemJsonType = typeMapping[itemTypeKey] || 'string'
        property.items = { type: itemJsonType }
      }

      properties[param.name] = property
      if (param.required) {
        required.push(param.name)
      }
    })

    const schema = {
      type: 'object',
      properties,
      required,
      additionalProperties: false,
    }

    return JSON.stringify(schema, null, 2)
  }

  // 将JSON Schema转换为参数
  const convertJsonSchemaToParameters = (jsonSchema: string): ToolParameter[] => {
    const schema = JSON.parse(jsonSchema)
    const parameters: ToolParameter[] = []

    // 反向类型映射：从 JSON Schema 类型到 UI 显示类型
    const reverseTypeMapping: Record<string, keyof typeof DATA_TYPES> = {
      string: 'STRING',
      integer: 'INTEGER',
      number: 'NUMBER',
      boolean: 'BOOLEAN',
      object: 'STRING', // object 类型映射为 STRING（因为可视化配置不支持 object 类型）
    }

    if (schema.properties) {
      Object.keys(schema.properties).forEach(key => {
        const prop = schema.properties[key]
        let uiType = DATA_TYPES[reverseTypeMapping[prop.type] || 'STRING']

        // 如果是数组类型，根据 items 确定具体的数组类型
        if (prop.type === 'array' && prop.items) {
          const items = prop.items as Record<string, unknown>
          const itemType = items.type as string
          switch (itemType) {
            case 'string':
              uiType = DATA_TYPES.ARRAY_STRING
              break
            case 'integer':
              uiType = DATA_TYPES.ARRAY_INTEGER
              break
            case 'number':
              uiType = DATA_TYPES.ARRAY_NUMBER
              break
            case 'boolean':
              uiType = DATA_TYPES.ARRAY_BOOLEAN
              break
            case 'object':
              // object 类型映射为 ARRAY_STRING（因为可视化配置不支持 Array<Object> 类型）
              uiType = DATA_TYPES.ARRAY_STRING
              break
            default:
              uiType = DATA_TYPES.ARRAY_STRING
          }
        }

        parameters.push({
          name: key,
          type: uiType,
          description: (prop.description as string) || '',
          required: schema.required?.includes(key) || false,
        })
      })
    }

    return parameters
  }

  // 更新JSON Schema
  const handleUpdateJsonSchema = (value: string) => {
    setParametersJsonSchema(value)
  }

  // 处理保存操作
  const handleSave = () => {
    if (!editingTool) return

    // 验证工具基本信息
    if (!editingTool.name || !editingTool.name.trim()) {
      setSnackbarMessage(t('components.prompts.toolEditDialog.toolNameEmpty'))
      setSnackbarOpen(true)
      return
    }

    if (editingTool.name.length > 100) {
      setSnackbarMessage(t('components.prompts.toolEditDialog.toolNameTooLong', { length: editingTool.name.length }))
      setSnackbarOpen(true)
      return
    }

    if (editingTool.description && editingTool.description.length > 1000) {
      setSnackbarMessage(t('components.prompts.toolEditDialog.toolDescriptionTooLong', { length: editingTool.description.length }))
      setSnackbarOpen(true)
      return
    }

    // 验证工具名称格式（只能包含英文字母、数字、下划线、连字符，必须以英文字母开头）
    const toolNamePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
    if (!toolNamePattern.test(editingTool.name.trim())) {
      setSnackbarMessage(t('components.prompts.toolEditDialog.toolNameFormatError'))
      setSnackbarOpen(true)
      return
    }

    // 构建更新后的工具对象
    let updatedTool: EditingTool = { ...editingTool }

    // 如果当前是JSON模式，需要先验证并转换参数
    // 注意：即使 parametersJsonSchema 是空字符串，也应该处理（表示删除所有参数）
    if (parametersMode === 'json') {
      if (!parametersJsonSchema || parametersJsonSchema.trim() === '') {
        // JSON Schema 为空，表示删除所有参数
        updatedTool = {
          ...editingTool,
          parameters: [],
          parametersJsonSchema: undefined, // 清空 JSON Schema
          parametersMode: 'json', // 保存参数模式
        }
        onToolChange(updatedTool)
      } else {
        // 验证JSON Schema格式
        const jsonValidationError = validateJsonSchema(parametersJsonSchema)
        if (jsonValidationError) {
          console.error('❌ [ToolEditDialog] JSON Schema验证失败:', jsonValidationError)
          setSnackbarMessage(t('components.prompts.toolEditDialog.jsonSchemaValidationError', { error: jsonValidationError }))
          setSnackbarOpen(true)
          return // 不保存
        }

        try {
          const parameters = convertJsonSchemaToParameters(parametersJsonSchema)
          const validationError = validateToolParameters(parameters)

          if (validationError) {
            console.error('❌ [ToolEditDialog] 参数验证失败:', validationError)
            setSnackbarMessage(t('components.prompts.toolEditDialog.parameterValidationFailed', { error: validationError }))
            setSnackbarOpen(true)
            return // 不保存
          }

          // 更新工具参数，同时保存原始的JSON Schema
          updatedTool = {
            ...editingTool,
            parameters,
            parametersJsonSchema: parametersJsonSchema, // 保存原始JSON Schema，保留高级特性
            parametersMode: 'json', // 保存参数模式
          }

          // 同时更新状态
          onToolChange(updatedTool)
        } catch (error) {
          console.error('JSON Schema解析失败:', error)
          setSnackbarMessage(t('components.prompts.toolEditDialog.jsonSchemaParseError', { error: error instanceof Error ? error.message : t('common.messages.unknownError') }))
          setSnackbarOpen(true)
          return // 不保存
        }
      }
    } else {
      // 可视化模式下验证当前参数
      const validationError = validateToolParameters(editingTool.parameters)
      if (validationError) {
        console.error('❌ [ToolEditDialog] 参数验证失败:', validationError)
        setSnackbarMessage(t('components.prompts.toolEditDialog.parameterValidationFailed', { error: validationError }))
        setSnackbarOpen(true)
        return // 不保存
      }

      // 可视化模式下，根据是否修改参数来决定是否保留JSON Schema
      if (editingTool.parametersJsonSchema) {
        if (visualParametersModified) {
          // 如果可视化参数被修改过，清除JSON Schema（因为参数已改变，JSON Schema可能不匹配）
          updatedTool = {
            ...editingTool,
            parameters: editingTool.parameters || [], // 明确包含更新后的 parameters
            parametersJsonSchema: undefined,
            parametersMode: 'visual', // 保存参数模式
          }
          onToolChange(updatedTool)
        } else {
          // 如果可视化参数没有被修改，保留原始的JSON Schema（优先使用原始JSON Schema）
          // 这样即使切换到可视化模式查看，保存时仍然使用原始的JSON Schema
          updatedTool = {
            ...editingTool,
            parameters: editingTool.parameters || [], // 明确包含更新后的 parameters
            parametersJsonSchema: editingTool.parametersJsonSchema, // 保留原始JSON Schema
            parametersMode: 'visual', // 保存参数模式
          }
        }
      } else {
        // 如果没有 JSON Schema，确保包含当前的 parameters
        updatedTool = {
          ...editingTool,
          parameters: editingTool.parameters || [], // 明确包含更新后的 parameters
          parametersMode: 'visual', // 保存参数模式
        }
      }
    }

    // 验证通过，执行保存，传递更新后的工具对象
    onSave(updatedTool)
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Code className="w-5 h-5 text-green-600" />
            <Typography variant="h6" className="text-gray-800">
              {editingTool?.id ? t('components.prompts.toolEditDialog.editTitle') : t('components.prompts.toolEditDialog.addTitle')}
            </Typography>
          </div>
          <IconButton size="small" onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </IconButton>
        </div>
      </DialogTitle>

      <DialogContent className="p-6">
        <div className="space-y-6">
          {/* 工具基本信息 */}
          <div className="space-y-4">
            <Typography variant="h6" className="text-gray-800 font-semibold">
              {t('components.prompts.toolEditDialog.toolInfo')}
            </Typography>

            <div className="space-y-3">
              {(() => {
                const toolName = editingTool?.name || ''
                const toolNamePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
                const hasNameError = Boolean(toolName.trim() && !toolNamePattern.test(toolName.trim()))
                const nameErrorMessage = hasNameError ? t('components.prompts.toolEditDialog.toolNameFormatError') : ''

                return (
                  <TextField
                    fullWidth
                    label={t('components.prompts.toolEditDialog.toolName')}
                    value={toolName}
                    onChange={e => onToolChange(editingTool ? { ...editingTool, name: e.target.value } : null)}
                    placeholder={t('components.prompts.toolEditDialog.toolNamePlaceholder')}
                    className="bg-white/80"
                    required
                    error={hasNameError}
                    helperText={nameErrorMessage || undefined}
                    inputProps={{ maxLength: 100 }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        position: 'relative',
                        '& input': {
                          paddingRight: '60px',
                        },
                      },
                    }}
                    InputProps={{
                      endAdornment: (
                        <div style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                          <Typography variant="caption" sx={{ color: (editingTool?.name?.length || 0) >= 100 ? '#ef4444' : '#6b7280', fontSize: '0.75rem' }}>
                            {editingTool?.name?.length || 0}/100
                          </Typography>
                        </div>
                      ),
                    }}
                  />
                )
              })()}

              <TextField
                fullWidth
                multiline
                rows={3}
                label={t('components.prompts.toolEditDialog.toolDescription')}
                value={editingTool?.description || ''}
                onChange={e => onToolChange(editingTool ? { ...editingTool, description: e.target.value } : null)}
                placeholder={t('components.prompts.toolEditDialog.toolDescriptionPlaceholder')}
                className="bg-white/80"
                error={false}
                helperText={undefined}
                inputProps={{ maxLength: 1000 }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    position: 'relative',
                    '& textarea': {
                      paddingRight: '60px',
                      paddingBottom: '24px',
                    },
                  },
                }}
                InputProps={{
                  endAdornment: (
                    <div style={{ position: 'absolute', right: 8, bottom: 0, pointerEvents: 'none' }}>
                      <Typography
                        variant="caption"
                        sx={{ color: (editingTool?.description?.length || 0) >= 1000 ? '#ef4444' : '#6b7280', fontSize: '0.75rem' }}
                      >
                        {editingTool?.description?.length || 0}/1000
                      </Typography>
                    </div>
                  ),
                }}
              />
            </div>
          </div>

          {/* 工具参数 */}
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center">
                <Typography variant="h6" className="text-gray-800 font-semibold">
                  {t('components.prompts.toolEditDialog.toolParameters')}
                </Typography>
                <IconButton
                  onClick={() => setParametersExpanded(!parametersExpanded)}
                  size="small"
                  className="ml-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  sx={{ borderRadius: 1 }}
                >
                  {parametersExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </IconButton>
              </div>
            </div>

            {parametersExpanded && (
              <div className="border border-gray-200 rounded-lg shadow-sm p-4">
                {/* 配置模式切换 */}
                <Box className="mb-2">
                  <Tabs
                    value={parametersMode}
                    onChange={(_, value: 'visual' | 'json') => handleToggleParametersMode(value)}
                    className="border-b border-gray-200"
                    sx={{
                      minHeight: 'auto',
                      '& .MuiTabs-flexContainer': {
                        minHeight: 'auto',
                      },
                      '& .MuiTab-root': {
                        minHeight: '40px',
                        padding: '6px 12px',
                        fontSize: '0.95rem',
                      },
                      '& .MuiTabs-indicator': {
                        height: '2px',
                      },
                    }}
                  >
                    <Tab label={t('components.prompts.toolEditDialog.visualConfig')} value="visual" icon={<Eye className="w-4 h-4" />} iconPosition="start" />
                    <Tab label={t('components.prompts.toolEditDialog.jsonConfig')} value="json" icon={<Code className="w-4 h-4" />} iconPosition="start" />
                  </Tabs>
                </Box>

                {/* 可视化配置模式 */}
                {parametersMode === 'visual' && (
                  <Box>
                    <div className="space-y-3">
                      {editingTool?.parameters.map((param, index) => (
                        <Paper key={index} elevation={1} className="p-4 bg-white/80 border border-green-200">
                          <div className="space-y-3">
                            <div className="flex flex-col md:flex-row items-start md:items-center gap-[5px]">
                              <div className="relative flex-[3] min-w-0">
                                {(() => {
                                  const nameError = getParameterNameError(param.name, index)
                                  return (
                                    <TextField
                                      size="small"
                                      label={t('components.prompts.toolEditDialog.parameterName')}
                                      value={param.name}
                                      onChange={e => handleToolParameterChange(index, 'name', e.target.value)}
                                      placeholder={t('components.prompts.toolEditDialog.parameterNamePlaceholder')}
                                      className="bg-white/60 w-full"
                                      error={!!nameError}
                                      helperText={nameError}
                                      sx={{
                                        minWidth: '225px',
                                        '& .MuiOutlinedInput-input': {
                                          paddingRight: '60px',
                                        },
                                      }}
                                      inputProps={{ maxLength: 100 }}
                                    />
                                  )
                                })()}
                                <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500">{param.name.length}/100</div>
                              </div>

                              <FormControl size="small" className="bg-white/60 flex-[1] min-w-0" sx={{ minWidth: '140px', maxWidth: '180px' }}>
                                <InputLabel>{t('components.prompts.toolEditDialog.parameterType')}</InputLabel>
                                <Select
                                  value={param.type}
                                  onChange={e => handleToolParameterChange(index, 'type', e.target.value)}
                                  label={t('components.prompts.toolEditDialog.parameterType')}
                                >
                                  <MenuItem value={DATA_TYPES.STRING}>
                                    <span>String</span>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.INTEGER}>
                                    <span>Integer</span>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.NUMBER}>
                                    <span>Number</span>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.BOOLEAN}>
                                    <span>Boolean</span>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.ARRAY_STRING}>
                                    <div className="flex items-center space-x-2">
                                      <Layers className="w-4 h-4 text-purple-600" />
                                      <span>Array&lt;String&gt;</span>
                                    </div>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.ARRAY_INTEGER}>
                                    <div className="flex items-center space-x-2">
                                      <Layers className="w-4 h-4 text-purple-600" />
                                      <span>Array&lt;Integer&gt;</span>
                                    </div>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.ARRAY_NUMBER}>
                                    <div className="flex items-center space-x-2">
                                      <Layers className="w-4 h-4 text-purple-600" />
                                      <span>Array&lt;Number&gt;</span>
                                    </div>
                                  </MenuItem>
                                  <MenuItem value={DATA_TYPES.ARRAY_BOOLEAN}>
                                    <div className="flex items-center space-x-2">
                                      <Layers className="w-4 h-4 text-purple-600" />
                                      <span>Array&lt;Boolean&gt;</span>
                                    </div>
                                  </MenuItem>
                                </Select>
                              </FormControl>

                              <div className="flex items-center shrink-0">
                                <FormControlLabel
                                  control={
                                    <Switch
                                      checked={param.required}
                                      onChange={e => handleToolParameterChange(index, 'required', e.target.checked)}
                                      color="primary"
                                    />
                                  }
                                  label={t('components.prompts.toolEditDialog.required')}
                                  className="m-0"
                                />
                              </div>

                              <div className="flex items-center shrink-0">
                                <Tooltip title={t('components.prompts.toolEditDialog.delete')} arrow>
                                  <IconButton size="small" onClick={() => handleRemoveParameter(index)} className="text-red-500 hover:text-red-700">
                                    <Trash2 className="w-4 h-4" />
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </div>

                            <div className="relative">
                              <TextField
                                fullWidth
                                size="small"
                                label={t('components.prompts.toolEditDialog.parameterDescription')}
                                value={param.description}
                                onChange={e => handleToolParameterChange(index, 'description', e.target.value)}
                                placeholder={t('components.prompts.toolEditDialog.parameterDescriptionPlaceholder')}
                                className="bg-white/60"
                                error={false}
                                helperText={undefined}
                                sx={{
                                  '& .MuiOutlinedInput-input': {
                                    paddingRight: '60px',
                                  },
                                }}
                                inputProps={{ maxLength: 500 }}
                              />
                              <div className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-500">{param.description.length}/500</div>
                            </div>
                          </div>
                        </Paper>
                      ))}

                      {editingTool?.parameters.length === 0 && (
                        <div className="text-center py-6 text-gray-500 border-2 border-dashed border-green-200 rounded-lg">
                          <Code className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                          <p>{t('components.prompts.toolEditDialog.noParameters')}</p>
                          <p className="text-sm">{t('components.prompts.toolEditDialog.clickToAddParameter')}</p>
                        </div>
                      )}
                    </div>

                    {/* 添加参数按钮 */}
                    <div className="mt-3 flex justify-center">
                      <Button
                        startIcon={<Plus className="w-4 h-4" />}
                        onClick={handleAddParameter}
                        size="small"
                        variant="outlined"
                        className="border-green-300 text-green-600 hover:bg-green-50"
                      >
                        {t('components.prompts.toolEditDialog.addParameter')}
                      </Button>
                    </div>
                  </Box>
                )}

                {/* JSON配置模式 */}
                {parametersMode === 'json' && (
                  <Box>
                    <JsonEditor
                      value={parametersJsonSchema}
                      onChange={handleUpdateJsonSchema}
                      placeholder={t('components.prompts.toolEditDialog.jsonSchemaPlaceholder')}
                      minHeight={200}
                      maxHeight={400}
                    />
                  </Box>
                )}
              </div>
            )}
          </div>

          {/* 默认模拟值设置 */}
          {showDefaultValue && (
            <div className="space-y-4">
              <FieldEditor
                label={t('components.prompts.toolEditDialog.defaultMockValue')}
                labelClassName="text-gray-800 font-semibold"
                labelVariant="h6"
                value={editingTool?.defaultValue || ''}
                fieldType={editingTool?.fieldType || 'PlainText'}
                allowedTypes={['PlainText', 'JSON']}
                placeholder={t('components.prompts.toolEditDialog.defaultMockValuePlaceholder')}
                onValueChange={value => onToolChange(editingTool ? { ...editingTool, defaultValue: value } : null)}
                onTypeChange={type => onToolChange(editingTool ? { ...editingTool, fieldType: type as 'PlainText' | 'JSON' } : null)}
                showCharCount={false}
              />
            </div>
          )}
        </div>
      </DialogContent>

      <DialogActions className="p-4 bg-gray-50">
        <Button
          onClick={handleSave}
          variant="contained"
          className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
          disabled={hasValidationErrors()}
        >
          {t('components.prompts.toolEditDialog.saveTool')}
        </Button>
      </DialogActions>

      {/* Snackbar for validation errors */}
      <Snackbar open={snackbarOpen} autoHideDuration={6000} onClose={() => setSnackbarOpen(false)} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <Alert onClose={() => setSnackbarOpen(false)} severity="error" sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>

      {/* 切换模式确认对话框 */}
      <Dialog
        open={confirmDialogOpen}
        onClose={handleCancelModeSwitch}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: '12px',
            boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1)',
          },
        }}
      >
        <DialogTitle className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-green-200 px-6 py-4">
          <div className="flex items-center space-x-2">
            <Code className="w-5 h-5 text-green-600" />
            <Typography variant="h6" className="text-gray-800 font-semibold">
              {t('components.prompts.toolEditDialog.confirmSwitchModeTitle')}
            </Typography>
          </div>
        </DialogTitle>
        <DialogContent className="px-6 py-6">
          <Box sx={{ marginTop: '24px' }}>
            <Typography variant="body1" className="text-gray-700 leading-relaxed">
              {confirmDialogMessage}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions className="px-6 py-4 bg-gray-50 gap-3">
          <Button
            onClick={handleCancelModeSwitch}
            variant="outlined"
            className="border-gray-300 text-gray-700 hover:bg-gray-100 hover:border-gray-400 min-w-[80px]"
          >
            {t('components.prompts.toolEditDialog.cancel')}
          </Button>
          <Button
            onClick={handleConfirmModeSwitch}
            variant="contained"
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 min-w-[100px] shadow-sm hover:shadow-sm transition-shadow"
          >
            {t('components.prompts.toolEditDialog.confirmSwitch')}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  )
}

export default ToolEditDialog
