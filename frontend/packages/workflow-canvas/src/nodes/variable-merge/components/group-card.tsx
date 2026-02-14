/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from 'react'
import { Tooltip, IconButton, Input } from '@douyinfe/semi-ui'
import { Info, Minus, Plus } from 'lucide-react'

import { VariableSelector, VariableSelectorProvider, TypeSelector, DisplaySchemaTag } from '../../../form-materials'
import { cn } from '../../../utils/cn'
import { DraggableList } from '../../../form-components/draggable-list'
import { useTranslation } from '../../../i18n'
import {
  GroupCardWrapper,
  GroupHeader,
  GroupInfo,
  GroupName,
  GroupMeta,
  InfoIcon,
  DeleteGroupButton,
  EmptyVariables,
  EmptyContent,
  EmptyIcon as EmptyIconStyled,
  EmptyText,
} from './styles'

interface Group {
  name: string
  type?: string
  items: string[]
}

interface GroupCardProps {
  group: Group
  groupIndex: number
  groupsLength: number
  onUpdate: (index: number, updatedGroup: Group) => void
  onDelete: (index: number) => void
  availableVariables: any[]
  inferVariableType: (variableName: string, availableVariables: any[]) => string
  getGroupType: (group: Group) => string
  readOnly?: boolean
}

export const GroupCard: React.FC<GroupCardProps> = ({
  group,
  groupIndex,
  groupsLength,
  onUpdate,
  onDelete,
  availableVariables,
  inferVariableType,
  getGroupType,
  readOnly = false,
}) => {
  const { t } = useTranslation()
  const [isEditingName, setIsEditingName] = useState(false)
  const [editingName, setEditingName] = useState(group.name)

  const handleNameUpdate = (newName: string) => {
    if (newName.trim() && newName !== group.name) {
      const updatedGroup = { ...group, name: newName.trim() }
      onUpdate(groupIndex, updatedGroup)
    }
    setIsEditingName(false)
  }

  const getCurrentGroupSelectedVariables = () => {
    const selectedVars = new Set<string>()
    group.items.forEach(item => {
      if (item && item.trim()) {
        selectedVars.add(item)
      }
    })
    return selectedVars
  }

  const handleVariableChange = (itemIndex: number, val: string[]) => {
    const newItems = [...group.items]
    const selectedVariable = val?.join('.') || ''
    newItems[itemIndex] = selectedVariable

    const updatedGroup = { ...group, items: newItems }
    if (itemIndex === 0) {
      updatedGroup.type = inferVariableType(selectedVariable, availableVariables)
    }

    onUpdate(groupIndex, updatedGroup)
  }

  const handleDeleteVariable = (itemIndex: number) => {
    let newItems = group.items.filter((_, i) => i !== itemIndex)

    if (newItems.length === 0) {
      newItems = ['']
    }

    const updatedGroup = { ...group, items: newItems }

    if (itemIndex === 0 && newItems.length > 0 && newItems[0]) {
      updatedGroup.type = inferVariableType(newItems[0], availableVariables)
    }

    onUpdate(groupIndex, updatedGroup)
  }

  const handleAddVariable = () => {
    const newItems = [...group.items, '']
    onUpdate(groupIndex, { ...group, items: newItems })
  }

  const handleVariablesChange = (newItems: string[]) => {
    const updatedGroup = { ...group, items: newItems }

    if (newItems.length > 0 && newItems[0] !== group.items[0]) {
      updatedGroup.type = inferVariableType(newItems[0], availableVariables)
    }

    onUpdate(groupIndex, updatedGroup)
  }

  const createSchemaFilter = (groupType: string) => {
    if (group.items.length === 0) {
      return {}
    }
    return { type: groupType as any, extra: { weak: true } }
  }

  const isGroupEmpty = group.items.length === 0 || group.items.every(item => !item || item.trim() === '')

  const getGroupSchema = () => ({
    type: group.type || 'string',
  })

  const renderVariableItem = (item: string, index: number, _provided: any) => {
    if (isGroupEmpty) {
      return (
        <VariableSelectorProvider>
          <VariableSelector value={item ? [item] : []} onChange={(val?: string[]) => handleVariableChange(index, val || [])} style={{ width: '100%' }} />
        </VariableSelectorProvider>
      )
    }
    const schemaFilter = createSchemaFilter(getGroupType(group))

    const currentGroupSelectedVars = getCurrentGroupSelectedVariables()
    const currentVar = group.items[index]

    const filteredVars = new Set(currentGroupSelectedVars)
    if (currentVar && currentVar.trim()) {
      filteredVars.delete(currentVar)
    }

    const skipVariable = (variable: any) => {
      if (!variable || !variable.key) {
        return false
      }

      const getVariableKeyString = (variable: any): string => {
        if (variable.keyPath && Array.isArray(variable.keyPath) && variable.keyPath.length > 0) {
          return variable.keyPath.map((_key, idx) => (_key === '[0]' || idx === 0 ? _key : `.${_key}`)).join('')
        }
        return variable.key
      }

      const currentVariableKey = getVariableKeyString(variable)

      for (const selectedVar of filteredVars) {
        if (selectedVar === currentVariableKey) {
          return true
        }
      }

      return false
    }

    return (
      <VariableSelectorProvider skipVariable={skipVariable} includeSchema={schemaFilter}>
        <VariableSelector value={item ? [item] : []} onChange={(val?: string[]) => handleVariableChange(index, val || [])} style={{ width: '100%' }} />
      </VariableSelectorProvider>
    )
  }

  return (
    <GroupCardWrapper className={cn(readOnly && 'read-only')}>
      <GroupHeader>
        <GroupInfo>
          {isEditingName && !readOnly ? (
            <Input
              value={editingName}
              onChange={setEditingName}
              onBlur={() => handleNameUpdate(editingName)}
              onKeyDown={e => {
                if (e.key === 'Escape') {
                  setIsEditingName(false)
                  setEditingName(group.name)
                }
              }}
              size="small"
              style={{
                width: '120px',
                fontSize: '12px',
                fontWeight: '500',
                height: '20px',
              }}
              maxLength={20}
              autoFocus
            />
          ) : (
            <GroupName
              onClick={() => {
                if (!readOnly) {
                  setIsEditingName(true)
                  setEditingName(group.name)
                }
              }}
              style={{ cursor: readOnly ? 'default' : 'pointer' }}
            >
              {group.name}
            </GroupName>
          )}

          <GroupMeta>
            {isGroupEmpty && !readOnly ? (
              <TypeSelector
                value={{ type: group.type || 'string' }}
                onChange={value => {
                  const updatedGroup = { ...group, type: value?.type || 'string' }
                  onUpdate(groupIndex, updatedGroup)
                }}
              />
            ) : (
              <DisplaySchemaTag value={getGroupSchema()} />
            )}

            <Tooltip content={t('workflowCanvas.nodes.variableMerge.tooltipType')}>
              <InfoIcon as="span">
                <Info size={14} />
              </InfoIcon>
            </Tooltip>
          </GroupMeta>
        </GroupInfo>

        {!readOnly && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <IconButton
              size="small"
              icon={<Plus size={14} />}
              onClick={handleAddVariable}
              theme="borderless"
              style={{
                width: '20px',
                height: '20px',
                color: '#999999',
              }}
            />

            <DeleteGroupButton as="span" style={{ cursor: groupsLength > 1 ? 'pointer' : 'not-allowed' }}>
              <IconButton
                size="small"
                icon={<Minus size={14} />}
                onClick={() => groupsLength > 1 && onDelete(groupIndex)}
                disabled={groupsLength <= 1}
                style={{
                  width: '20px',
                  height: '20px',
                  color: groupsLength > 1 ? '#999999' : '#cccccc',
                  cursor: groupsLength > 1 ? 'pointer' : 'not-allowed',
                }}
              />
            </DeleteGroupButton>
          </div>
        )}
      </GroupHeader>

      <DraggableList
        items={group.items}
        onChange={handleVariablesChange}
        renderItem={renderVariableItem}
        onDelete={handleDeleteVariable}
        readOnly={readOnly}
        showDragHandle={true}
        canDelete={true}
        canAdd={false}
        isDragDisabled={index => group.items.length <= 1}
        isDeleteDisabled={index => group.items.length <= 1}
      />

      {group.items.length === 0 && (
        <EmptyVariables>
          <EmptyContent>
            <EmptyIconStyled>
              <Plus size={16} />
            </EmptyIconStyled>
            <EmptyText>{t('workflowCanvas.nodes.variableMerge.noVariables')}</EmptyText>
          </EmptyContent>
        </EmptyVariables>
      )}
    </GroupCardWrapper>
  )
}
