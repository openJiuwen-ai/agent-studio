import type { Tool, ToolParameter } from '@/types/promptType'
import i18n from '@/i18n'

/**
 * API工具格式（agentTools 或 tools）
 */
export interface ApiTool {
  type: 'function'
  function: {
    name: string
    description: string
    parameters: any // JSON Schema 对象或字符串
    parameters_mode?: 'visual' | 'json' // 参数模式：visual（可视化）或 json（JSON配置）
    parameters_format?: 'visual' | 'json' // 兼容旧字段名
  }
}

/**
 * 将JSON Schema类型映射到UI类型
 */
const mapJsonSchemaTypeToUIType = (prop: any): string => {
  switch (prop.type) {
    case 'integer':
      return 'Integer'
    case 'number':
      return 'Number'
    case 'boolean':
      return 'Boolean'
    case 'object':
      return 'Object'
    case 'array':
      if (prop.items) {
        switch (prop.items.type) {
          case 'string':
            return 'Array<String>'
          case 'integer':
            return 'Array<Integer>'
          case 'number':
            return 'Array<Number>'
          case 'boolean':
            return 'Array<Boolean>'
          case 'object':
            return 'Array<Object>'
          default:
            return 'Array<String>'
        }
      }
      return 'Array<String>'
    default:
      return 'String'
  }
}

/**
 * 将UI类型映射到JSON Schema类型
 */
const mapUITypeToJsonSchema = (param: ToolParameter): any => {
  let jsonType = 'string'
  let schema: any = {}

  switch (param.type) {
    case 'Integer':
      jsonType = 'integer'
      break
    case 'Number':
      jsonType = 'number'
      break
    case 'Boolean':
      jsonType = 'boolean'
      break
    case 'Object':
      jsonType = 'object'
      break
    case 'Array<String>':
      jsonType = 'array'
      schema = {
        type: jsonType,
        items: { type: 'string' },
        description: param.description,
      }
      return schema
    case 'Array<Integer>':
      jsonType = 'array'
      schema = {
        type: jsonType,
        items: { type: 'integer' },
        description: param.description,
      }
      return schema
    case 'Array<Number>':
      jsonType = 'array'
      schema = {
        type: jsonType,
        items: { type: 'number' },
        description: param.description,
      }
      return schema
    case 'Array<Boolean>':
      jsonType = 'array'
      schema = {
        type: jsonType,
        items: { type: 'boolean' },
        description: param.description,
      }
      return schema
    case 'Array<Object>':
      jsonType = 'array'
      schema = {
        type: jsonType,
        items: { type: 'object' },
        description: param.description,
      }
      return schema
    default:
      jsonType = 'string'
  }

  schema = {
    type: jsonType,
    description: param.description,
  }

  // 如果有枚举值，添加enum属性
  if (param.enum && param.enum.length > 0) {
    schema.enum = param.enum
  }

  return schema
}

/**
 * 从parameters生成基本的JSON Schema
 */
const generateBasicJsonSchema = (parameters: ToolParameter[]): string => {
  try {
    const basicSchema = {
      type: 'object',
      properties: parameters.reduce((acc, param) => {
        acc[param.name] = mapUITypeToJsonSchema(param)
        return acc
      }, {} as any),
      required: parameters.filter(p => p.required).map(p => p.name),
      additionalProperties: false,
    }
    return JSON.stringify(basicSchema, null, 2)
  } catch (error) {
    console.error(i18n.t('utils.prompts.utils.toolFormatConverter.generateJsonSchemaFailed'), error)
    return ''
  }
}

/**
 * 将API工具格式（agentTools 或 tools）转换为前端Tool格式
 * @param apiTools API返回的工具数组（agentTools 或 tools）
 * @param startIndex 起始索引，用于生成工具ID
 * @returns 转换后的前端Tool数组
 */
export const convertApiToolsToFrontendTools = (apiTools: ApiTool[], startIndex: number = 0): Tool[] => {
  return apiTools.map((apiTool, index) => {
    const func = apiTool.function
    const parameters: ToolParameter[] = []

    // 保存原始的JSON Schema，用于保留高级特性（enum、format、嵌套对象等）
    let parametersJsonSchema: string | undefined = undefined
    if (func.parameters) {
      try {
        // 确保parameters是一个有效的JSON Schema对象
        if (typeof func.parameters === 'object' && func.parameters !== null) {
          // 如果已经有完整的JSON Schema结构，直接使用
          if (func.parameters.type === 'object' || func.parameters.properties) {
            parametersJsonSchema = JSON.stringify(func.parameters, null, 2)
          } else {
            // 如果格式不完整，构建一个基本的JSON Schema
            const basicSchema = {
              type: 'object',
              properties: func.parameters.properties || {},
              required: func.parameters.required || [],
              additionalProperties: false,
            }
            parametersJsonSchema = JSON.stringify(basicSchema, null, 2)
          }
        } else if (typeof func.parameters === 'string') {
          // 如果是字符串，尝试解析
          try {
            const parsed = JSON.parse(func.parameters)
            if (parsed && typeof parsed === 'object') {
              parametersJsonSchema = JSON.stringify(parsed, null, 2)
            }
          } catch (parseError) {
            console.error(`🛠️ [convertApiToolsToFrontendTools] ${i18n.t('utils.prompts.utils.toolFormatConverter.tool')} ${func.name} - ${i18n.t('utils.prompts.utils.toolFormatConverter.parseStringFailed')}:`, parseError)
            // 解析失败，忽略
          }
        } else {
          // 如果parameters不是对象，尝试转换为JSON
          parametersJsonSchema = JSON.stringify(func.parameters, null, 2)
        }
      } catch (error) {
        console.error(`🛠️ [convertApiToolsToFrontendTools] ${i18n.t('utils.prompts.utils.toolFormatConverter.tool')} ${func.name} - ${i18n.t('utils.prompts.utils.toolFormatConverter.saveJsonSchemaFailed')}:`, error)
        // 如果保存失败，会在后面从parameters生成
      }
    }

    // 解析parameters，生成UI参数列表
    if (func.parameters) {
      let parsedParams: any

      // 处理字符串格式的parameters
      if (typeof func.parameters === 'string') {
        try {
          parsedParams = JSON.parse(func.parameters)
        } catch (parseError) {
          console.error(`🛠️ [convertApiToolsToFrontendTools] ${i18n.t('utils.prompts.utils.toolFormatConverter.tool')} ${func.name} - ${i18n.t('utils.prompts.utils.toolFormatConverter.parseFailed')}:`, parseError)
          parsedParams = null
        }
      } else {
        parsedParams = func.parameters
      }

      // 如果是JSON Schema格式（有type和properties）
      // 需要检查是否是完整的JSON Schema对象（有type: 'object'和properties）
      const hasProperties = parsedParams && typeof parsedParams === 'object' && parsedParams.properties
      const propertiesIsObject = hasProperties && typeof parsedParams.properties === 'object'
      const hasPropertiesKeys = propertiesIsObject && Object.keys(parsedParams.properties).length > 0

      if (parsedParams && typeof parsedParams === 'object' && hasProperties && propertiesIsObject && hasPropertiesKeys) {
        // 新格式：JSON Schema对象，从properties中提取参数
        Object.keys(parsedParams.properties).forEach(key => {
          const prop = parsedParams.properties[key]
          const uiType = mapJsonSchemaTypeToUIType(prop)

          parameters.push({
            name: key,
            type: uiType,
            description: prop.description || '',
            required: parsedParams.required?.includes(key) || false,
            enum: prop.enum || undefined,
          })
        })
      } else if (parsedParams && typeof parsedParams === 'object') {
        // 旧格式：直接是参数对象（不是JSON Schema格式）
        // 需要排除JSON Schema的顶层属性（type, properties, required, additionalProperties）
        const schemaTopLevelKeys = ['type', 'properties', 'required', 'additionalProperties']
        Object.entries(parsedParams).forEach(([paramName, paramConfig]: [string, any]) => {
          // 跳过JSON Schema的顶层属性
          if (schemaTopLevelKeys.includes(paramName)) {
            return
          }
          const uiType = mapJsonSchemaTypeToUIType(paramConfig)
          parameters.push({
            name: paramName,
            type: uiType,
            description: paramConfig.description || '',
            required: paramConfig.required === 'true' || paramConfig.required === true,
            enum: paramConfig.enum || undefined,
          })
        })
      }
    }

    // 如果没有保存JSON Schema，但从parameters生成了一个，则从parameters生成基本的JSON Schema
    if (!parametersJsonSchema && parameters.length > 0) {
      parametersJsonSchema = generateBasicJsonSchema(parameters)
    }

    // 读取参数模式，优先使用 parameters_mode，如果没有则使用 parameters_format，默认 visual
    const parametersMode = (func.parameters_mode || func.parameters_format || 'visual') as 'visual' | 'json'

    return {
      id: `tool_${startIndex + index + 1}`,
      name: func.name,
      description: func.description || '',
      parameters,
      fieldType: 'JSON' as const,
      parametersJsonSchema, // 保存原始JSON Schema，保留所有高级特性
      parametersMode, // 保存参数模式
    }
  })
}

/**
 * 将前端Tool格式转换为API工具格式（agentTools 或 tools）
 * @param tools 前端Tool数组
 * @returns 转换后的API工具数组
 */
export const convertFrontendToolsToApiTools = (tools: Tool[]): ApiTool[] => {
  return tools.map(tool => {
    // 获取参数模式，默认为 visual
    const parametersMode = tool.parametersMode || 'visual'

    // 如果工具有保存的JSON Schema，直接使用它（保留所有高级特性，如嵌套对象、数组、枚举等）
    if (tool.parametersJsonSchema && tool.parametersJsonSchema.trim()) {
      try {
        const jsonSchema = JSON.parse(tool.parametersJsonSchema)
        const apiTool = {
          type: 'function' as const,
          function: {
            name: tool.name,
            description: tool.description,
            parameters: jsonSchema,
            parameters_mode: parametersMode,
          },
        }
        return apiTool
      } catch (error) {
        console.error(i18n.t('utils.prompts.utils.toolFormatConverter.parseToolJsonSchemaFailed'), error)
        // 如果解析失败，回退到使用parameters转换
      }
    }

    // 如果没有JSON Schema或解析失败，使用parameters转换（兼容旧数据）
    const apiTool = {
      type: 'function' as const,
      function: {
        name: tool.name,
        description: tool.description,
        parameters: {
          type: 'object',
          properties: tool.parameters.reduce((acc, param) => {
            acc[param.name] = mapUITypeToJsonSchema(param)
            return acc
          }, {} as any),
          required: tool.parameters.filter(p => p.required).map(p => p.name),
          additionalProperties: false,
        },
        parameters_mode: parametersMode,
      },
    }
    return apiTool
  })
}
