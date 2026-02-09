/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { useMemo, useState } from 'react'

import { IJsonSchema } from '@flowgram.ai/json-schema'
import { Button, Checkbox, IconButton } from '@douyinfe/semi-ui'
import { IconExpand, IconShrink, IconPlus, IconChevronDown, IconChevronRight, IconMinus } from '@douyinfe/semi-icons'

import { InjectTypeSelector, BlurInput } from '../../'
import { useTranslation } from '../../../i18n'

import { ConfigType, PropertyValueType } from './types'
import { IconAddChildren } from './icon'
import { usePropertiesEdit } from './hooks'
import { DefaultValue } from './default-value'

import './styles.css'

const DEFAULT = { type: 'object' }

export function JsonSchemaEditor(props: {
  value?: IJsonSchema
  onChange?: (value: IJsonSchema) => void
  config?: ConfigType
  className?: string
  readonly?: boolean
  showAddButton?: boolean
  /** 不可变的字段，这些字段整行不可编辑 */
  defaultFields?: string[]
  /** 最少属性数量限制 */
  minProperties?: number
  expandable?: boolean
  /** 变量名称最大字节长度 */
  maxNameBytes?: number
}) {
  const { value = DEFAULT, config = {}, onChange: onChangeProps, readonly, showAddButton = true, defaultFields, minProperties = 0, expandable = false, maxNameBytes } = props
  const { t } = useTranslation()
  const [error, setError] = useState<string>()
  const { propertyList, onAddProperty, onRemoveProperty, onEditProperty } = usePropertiesEdit(value, onChangeProps)

  // 包装 onEditProperty 以处理重复参数错误
  const handleEditProperty = (key: number, nextValue: PropertyValueType) => {
    setError(undefined) // 清除之前的错误
    const result = onEditProperty(key, nextValue)

    if (result && !result.shouldUpdate) {
      setError(result.error || t('workflowCanvas.formMaterials.editor.duplicateParameterName'))
    }
  }

  // 包装 onAddProperty 以检查重复参数名
  const handleAddProperty = () => {
    const hasEmptyName = propertyList.some(item => !item.name || item.name.trim() === '')
    if (hasEmptyName) {
      setError(t('workflowCanvas.formMaterials.editor.completeCurrentParameterFirst'))
      return
    }
    setError(undefined)
    onAddProperty()
  }

  return (
    <div className="gedit-m-json-schema-editor-container">
      {/* 显示错误信息 */}
      {error && (
        <div
          style={{
            marginTop: 8,
            marginLeft: 16,
            marginRight: 16,
            padding: '8px 12px',
            backgroundColor: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: 4,
            color: '#ff4d4f',
            fontSize: 12,
          }}
        >
          {error}
        </div>
      )}
      <div className="gedit-m-json-schema-editor-tree-items">
        {propertyList.map(_property => (
          <PropertyEdit
            readonly={readonly}
            key={_property.key}
            value={_property}
            config={config}
            showAddButton={showAddButton}
            defaultFields={defaultFields}
            minProperties={minProperties}
            propertyListLength={propertyList.length}
            expandable={expandable}
            maxNameBytes={maxNameBytes}
            onChange={_v => {
              handleEditProperty(_property.key!, _v)
            }}
            onRemove={() => {
              // 检查字段是否在 defaultFields 中，如果是则不允许删除
              if (defaultFields?.includes(_property.name || '')) {
                return
              }
              // 检查是否达到最少属性数量限制
              if (propertyList.length <= minProperties) {
                return
              }
              onRemoveProperty(_property.key!)
            }}
          />
        ))}
      </div>
      {showAddButton && (
        <Button disabled={readonly} size="small" style={{ marginTop: 10, marginLeft: 16 }} icon={<IconPlus />} onClick={handleAddProperty}>
          {config?.addButtonText ?? ''}
        </Button>
      )}
    </div>
  )
}

function PropertyEdit(props: {
  value?: PropertyValueType
  config?: ConfigType
  onChange?: (value: PropertyValueType) => void
  onRemove?: () => void
  readonly?: boolean
  $isLast?: boolean
  $level?: number
  showAddButton?: boolean
  defaultFields?: string[]
  minProperties?: number
  propertyListLength?: number
  expandable?: boolean
  onError?: (error: string) => void
  maxNameBytes?: number
}) {
  const {
    value,
    config,
    readonly,
    $level = 0,
    onChange: onChangeProps,
    onRemove,
    $isLast,
    showAddButton = true,
    defaultFields,
    minProperties = 0,
    propertyListLength = 0,
    expandable,
    onError,
    maxNameBytes,
  } = props

  const { t } = useTranslation()
  const [expand, setExpand] = useState(false)
  const [collapse, setCollapse] = useState(false)

  const { name, type, items, default: defaultValue, description, isPropertyRequired } = value || {}

  const typeSelectorValue = useMemo(() => ({ type, items }), [type, items])

  const { propertyList, canAddField, onAddProperty, onRemoveProperty, onEditProperty } = usePropertiesEdit(value, onChangeProps)

  // 判断字段是否被锁定
  const isFieldLocked = useMemo(() => {
    return readonly || defaultFields?.includes(name || '') || false
  }, [readonly, defaultFields, name])

  const onChange = (key: string, _value: any) => {
    // 如果是修改 name 字段，检查重复
    if (key === 'name' && _value) {
      // 注意：这里我们无法直接检查重复，因为需要在父组件中进行
      // 我们将检查逻辑保留在 usePropertiesEdit 的 onEditProperty 中
    }
    onChangeProps?.({
      ...(value || {}),
      [key]: _value,
    })
  }

  // 包装错误处理
  const handleError = (error: string) => {
    if (onError) {
      onError(error)
    } else {
      console.error('PropertyEdit Error:', error)
    }
  }

  const showCollapse = canAddField && propertyList.length > 0

  return (
    <>
      <div
        className={`gedit-m-json-schema-editor-tree-item-left ${$level > 0 ? 'show-line' : ''} ${$isLast ? 'is-last' : ''} ${
          showCollapse ? 'show-collapse' : ''
        }`}
      >
        {showCollapse && (
          <div className="gedit-m-json-schema-editor-collapse-trigger" onClick={() => setCollapse(_collapse => !_collapse)}>
            {collapse ? <IconChevronDown size="small" /> : <IconChevronRight size="small" />}
          </div>
        )}
      </div>
      <div className="gedit-m-json-schema-editor-tree-item-right">
        <div className="gedit-m-json-schema-editor-tree-item-main">
          <div className="gedit-m-json-schema-editor-row">
            <div className="gedit-m-json-schema-editor-name">
              <BlurInput
                disabled={isFieldLocked}
                placeholder={config?.placeholder ?? t('workflowCanvas.formMaterials.editor.inputVariableName')}
                size="small"
                value={name}
                validateVariable={true}
                maxBytes={maxNameBytes}
                onChange={value => onChange('name', value)}
              />
            </div>
            <div className="gedit-m-json-schema-editor-type">
              <InjectTypeSelector
                value={typeSelectorValue}
                readonly={isFieldLocked}
                excludeTypes={config?.excludeTypes}
                excludeNestedArray={config?.excludeNestedArray}
                onChange={_value => {
                  // Check if type has changed, if so reset default value
                  const hasTypeChanged = _value.type !== type || JSON.stringify(_value.items) !== JSON.stringify(items)

                  onChangeProps?.({
                    ...(value || {}),
                    ..._value,
                    // Reset default value when type changes
                    ...(hasTypeChanged ? { default: undefined } : {}),
                  })
                }}
              />
            </div>
            <div className="gedit-m-json-schema-editor-required">
              <Checkbox disabled={isFieldLocked} checked={isPropertyRequired} onChange={e => onChange('isPropertyRequired', e.target.checked)} />
            </div>

            <div className="gedit-m-json-schema-editor-actions">
              {expandable && (
                <IconButton
                  disabled={isFieldLocked}
                  size="small"
                  theme="borderless"
                  icon={expand ? <IconShrink size="small" /> : <IconExpand size="small" />}
                  onClick={() => {
                    setExpand(_expand => !_expand)
                  }}
                />
              )}
              {canAddField && showAddButton && (
                <IconButton
                  disabled={isFieldLocked}
                  size="small"
                  theme="borderless"
                  icon={<IconAddChildren />}
                  onClick={() => {
                    onAddProperty()
                    setCollapse(true)
                  }}
                />
              )}
              <IconButton
                disabled={isFieldLocked || propertyListLength <= minProperties}
                size="small"
                theme="borderless"
                icon={<IconMinus size="small" />}
                onClick={onRemove}
              />
            </div>
          </div>
          {expandable && expand && (
            <div className="gedit-m-json-schema-editor-expand-detail">
              <div className="gedit-m-json-schema-editor-label">{config?.descTitle ?? t('workflowCanvas.formMaterials.editor.description')}</div>
              <BlurInput
                disabled={isFieldLocked}
                size="small"
                value={description}
                onChange={value => onChange('description', value)}
                placeholder={config?.descPlaceholder ?? t('workflowCanvas.formMaterials.editor.helpLLMUnderstandProperty')}
                maxBytes={config?.maxDescBytes}
              />
              {$level === 0 && config?.showDefaultValue !== false && (
                <>
                  <div className="gedit-m-json-schema-editor-label" style={{ marginTop: 10 }}>
                    {config?.defaultValueTitle ?? t('workflowCanvas.formMaterials.editor.defaultValue')}
                  </div>
                  <div className="gedit-m-json-schema-editor-default-value-wrapper">
                    <DefaultValue
                      value={defaultValue}
                      schema={value}
                      placeholder={config?.defaultValuePlaceholder ?? t('workflowCanvas.formMaterials.editor.defaultValue')}
                      onChange={value => onChange('default', value)}
                      locked={isFieldLocked}
                    />
                  </div>
                </>
              )}
            </div>
          )}
        </div>
        {showCollapse && (
          <div className={`gedit-m-json-schema-editor-collapsible ${collapse ? 'collapse' : ''}`}>
            <div className="gedit-m-json-schema-editor-tree-items shrink">
              {propertyList.map((_property, index) => (
                <PropertyEdit
                  readonly={readonly}
                  key={_property.key}
                  value={_property}
                  config={config}
                  showAddButton={showAddButton}
                  defaultFields={defaultFields}
                  minProperties={minProperties}
                  propertyListLength={propertyList.length}
                  $level={$level + 1}
                  expandable={expandable}
                  maxNameBytes={maxNameBytes}
                  onChange={_v => {
                    const result = onEditProperty(_property.key!, _v)
                    if (result && !result.shouldUpdate) {
                      handleError(result.error || t('workflowCanvas.formMaterials.editor.duplicateParameterName'))
                    }
                  }}
                  onRemove={() => {
                    if (defaultFields?.includes(_property.name || '')) {
                      return
                    }
                    if (propertyList.length <= minProperties) {
                      return
                    }
                    onRemoveProperty(_property.key!)
                  }}
                  $isLast={index === propertyList.length - 1}
                  onError={handleError}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
