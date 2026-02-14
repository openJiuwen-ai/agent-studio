/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useMemo } from 'react'

import { IJsonSchema, useTypeManager, JsonSchemaTypeManager } from '@flowgram.ai/json-schema'
import { Cascader, Icon, IconButton } from '@douyinfe/semi-ui'
import { IconFile, IconImage, IconVideo, IconMusic, IconBook, IconCode, IconArchive } from '@douyinfe/semi-icons'

import { createInjectMaterial } from '../../'

export interface TypeSelectorProps {
  value?: Partial<IJsonSchema>
  onChange?: (value?: Partial<IJsonSchema>) => void
  readonly?: boolean
  /**
   * @deprecated use readonly instead
   */
  disabled?: boolean
  style?: React.CSSProperties
  /** Types to exclude from the type selector */
  excludeTypes?: string[]
  /** Whether to exclude array type as array item (nested arrays) */
  excludeNestedArray?: boolean
}

const labelStyle: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 5 }

// File subtypes - must match file.tsx FILE_SUBTYPES
const FILE_SUBTYPES = [
  { type: 'default', label: 'Default', icon: React.createElement(IconFile, { size: '14px' }) },
  { type: 'image', label: 'Image', icon: React.createElement(IconImage, { size: '14px' }) },
  { type: 'svg', label: 'Svg', icon: React.createElement(IconImage, { size: '14px' }) },
  { type: 'audio', label: 'Audio', icon: React.createElement(IconMusic, { size: '14px' }) },
  { type: 'video', label: 'Video', icon: React.createElement(IconVideo, { size: '14px' }) },
  { type: 'voice', label: 'Voice', icon: React.createElement(IconMusic, { size: '14px' }) },
  { type: 'doc', label: 'Doc', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'ppt', label: 'PPT', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'excel', label: 'Excel', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'txt', label: 'Txt', icon: React.createElement(IconBook, { size: '14px' }) },
  { type: 'code', label: 'Code', icon: React.createElement(IconCode, { size: '14px' }) },
  { type: 'zip', label: 'Zip', icon: React.createElement(IconArchive, { size: '14px' }) },
] as const

export const getTypeSelectValue = (value?: Partial<IJsonSchema>): string[] | undefined => {
  if (value?.type === 'array' && value?.items) {
    return [value.type, ...(getTypeSelectValue(value.items) || [])]
  }

  if (value?.type === 'file' && value?.fileType) {
    return [value.type, value.fileType]
  }

  return value?.type ? [value.type] : undefined
}

export const parseTypeSelectValue = (value?: string[]): Partial<IJsonSchema> | undefined => {
  const [type, ...subTypes] = value || []

  if (type === 'array') {
    return { type: 'array', items: parseTypeSelectValue(subTypes) }
  }

  if (type === 'file') {
    return { type: 'file', fileType: subTypes[0] || 'default' }
  }

  return { type }
}

export function TypeSelector(props: TypeSelectorProps) {
  const { value, onChange, readonly, disabled, style, excludeTypes, excludeNestedArray } = props

  const selectValue = useMemo(() => getTypeSelectValue(value), [value])

  const typeManager = useTypeManager() as JsonSchemaTypeManager

  const icon = typeManager.getDisplayIcon(value || {})

  const options = useMemo(
    () =>
      typeManager
        .getTypeRegistriesWithParentType()
        .filter(_type => !excludeTypes?.includes(_type.type))
        .map(_type => {
          const isArray = _type.type === 'array'
          const isFile = _type.type === 'file'

          return {
            label: (
              <div style={labelStyle}>
                <Icon size="small" svg={_type.icon} />
                {typeManager.getTypeBySchema(_type)?.label || _type.type}
              </div>
            ),
            value: _type.type,
            children: isArray
              ? typeManager
                  .getTypeRegistriesWithParentType('array')
                  .filter(_type => {
                    if (excludeTypes?.includes(_type.type)) return false
                    if (excludeNestedArray && _type.type === 'array') return false
                    // Exclude object, file, and date-time from array subtypes
                    if (['object', 'file', 'date-time'].includes(_type.type)) return false
                    return true
                  })
                  .map(_type => ({
                    label: (
                      <div style={labelStyle}>
                        <Icon
                          size="small"
                          svg={typeManager.getDisplayIcon({
                            type: 'array',
                            items: { type: _type.type },
                          })}
                        />
                        {typeManager.getTypeBySchema(_type)?.label || _type.type}
                      </div>
                    ),
                    value: _type.type,
                  }))
              : isFile
                ? FILE_SUBTYPES.map(subtype => ({
                    label: (
                      <div style={labelStyle}>
                        {subtype.icon}
                        {subtype.label}
                      </div>
                    ),
                    value: subtype.type,
                  }))
                : [],
          }
        }),
    [excludeTypes, excludeNestedArray],
  )

  const isDisabled = readonly || disabled

  return (
    <Cascader
      disabled={isDisabled}
      size="small"
      triggerRender={() => (
        <IconButton
          size="small"
          style={{
            ...(isDisabled ? { pointerEvents: 'none' } : {}),
            ...(style || {}),
          }}
          disabled={isDisabled}
          icon={icon}
        />
      )}
      treeData={options}
      value={selectValue}
      leafOnly={true}
      onChange={value => {
        onChange?.(parseTypeSelectValue(value as string[]))
      }}
    />
  )
}

TypeSelector.renderKey = 'type-selector-render-key'
export const InjectTypeSelector = createInjectMaterial(TypeSelector)
