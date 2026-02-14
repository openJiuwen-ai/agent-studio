/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { JsonSchemaUtils } from '@flowgram.ai/json-schema'

export const getVariableTypes = (availableVariables: any[]): Record<string, string> => {
  const variableTypes: Record<string, string> = {}

  availableVariables.forEach(variable => {
    if (variable?.key) {
      variableTypes[variable.key] = inferTypeFromAST(variable.type)
    }
  })

  return variableTypes
}

export const inferVariableType = (variablePath: string, availableVariables: any[]): string => {
  const pathParts = variablePath.split('.')
  const rootVariableName = pathParts[0]

  const rootVariable = availableVariables?.find(v => v.key === rootVariableName)

  if (!rootVariable) {
    return 'string'
  }

  if (pathParts.length === 1) {
    return inferTypeFromAST(rootVariable.type)
  }

  let currentType = rootVariable.type

  if (currentType.constructor && currentType.constructor.name === 'ObjectType' && typeof currentType.getByKeyPath === 'function') {
    try {
      const remainingPath = pathParts.slice(1)

      const property = currentType.getByKeyPath(remainingPath)
      if (property) {
        return inferTypeFromAST(property.type)
      } else {
        return 'string'
      }
    } catch (error) {
    }
  }

  for (let i = 1; i < pathParts.length; i++) {
    const propertyName = pathParts[i]

    const isObjectType = checkIfObjectType(currentType)
    const properties = getPropertiesFromType(currentType)

    if (!isObjectType || !properties) {
      return 'string'
    }

    let property = null

    if (Array.isArray(properties)) {
      property = properties.find((prop: any) => prop.key === propertyName)
    } else if (typeof properties === 'object') {
      const propertyType = properties[propertyName]
      if (propertyType) {
        property = {
          key: propertyName,
          type: propertyType,
        }
      }
    }

    if (!property) {
      return 'string'
    }

    currentType = property.type
  }

  return inferTypeFromAST(currentType)
}

export const checkIfObjectType = (type: any): boolean => {
  if (!type) return false

  if (type.kind === 'Object') return true

  if (type.type === 'object') return true

  if (type.constructor && type.constructor.name === 'ObjectType') return true

  if (type.type === 'object' && (type.properties || typeof type.getProperties === 'function')) return true

  return false
}
export const getPropertiesFromType = (type: any): any => {
  if (!type) return null

  if (type.properties) {
    return type.properties
  }

  if (typeof type.getProperties === 'function') {
    try {
      const result = type.getProperties()
      return result
    } catch (error) {
    }
  }

  if (type.constructor && type.constructor.name === 'ObjectType') {
    if (type.properties && Array.isArray(type.properties)) {
      return type.properties
    }

    if (type.propertyTable && type.propertyTable instanceof Map) {
      const propertiesArray = Array.from(type.propertyTable.values())
      return propertiesArray
    }
  }

  return null
}

export const inferTypeFromAST = (ast: any): string => {
  if (!ast) {
    return 'string'
  }

  if (ast.type && typeof ast.type === 'string') {
    const typeValue = ast.type
    if (['date-time', 'file', 'string', 'number', 'integer', 'boolean', 'array', 'map'].includes(typeValue)) {
      return typeValue
    }
    if (typeValue === 'object' && ast.properties) {
      return 'object'
    }
    return typeValue
  }

  if (ast.kind) {
    const kindToTypeMap: Record<string, string> = {
      String: 'string',
      Number: 'number',
      Integer: 'integer',
      Boolean: 'boolean',
      Object: 'object',
      Array: 'array',
      Map: 'map',
      CustomType: 'object',
      Any: 'object',
      Union: 'object',
    }

    if (ast.kind === 'CustomType' && ast.typeName) {
      return ast.typeName
    }

    const resultType = kindToTypeMap[ast.kind] || 'string'
    return resultType
  }

  if (ast.flags !== undefined || ast._version !== undefined) {
    if (checkIfObjectType(ast)) {
      return 'object'
    }
  }

  if (ast.type) {
    if (typeof ast.type === 'string') {
      return ast.type
    }

    if (ast.type.kind) {
      return inferTypeFromAST(ast.type)
    }
  }

  try {
    const inferredSchema = JsonSchemaUtils.astToSchema(ast, { drilldownObject: false })
    const resultType = inferredSchema?.type || 'string'
    return resultType
  } catch (error) {
    return 'string'
  }
}
