/**
 * 标准 JSON Schema 子集
 * @see https://json-schema.org/
 */
export interface JsonSchema {
  type?: 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array' | 'null'
  description?: string
  /** object 类型的属性定义 */
  properties?: Record<string, JsonSchema>
  /** object 类型的必填属性名列表 */
  required?: string[]
  /** array 类型的元素 schema */
  items?: JsonSchema
  example?: unknown
  default?: unknown
}
