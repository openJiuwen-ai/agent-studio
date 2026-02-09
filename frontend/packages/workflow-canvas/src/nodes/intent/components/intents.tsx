/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */
import { useLayoutEffect, useCallback } from 'react'
import { Input, Tag } from '@douyinfe/semi-ui'
import { Field, WorkflowNodePortsData } from '@flowgram.ai/free-layout-editor'
import { Plus } from 'lucide-react'
import { useTranslation } from '../../../i18n'

import { FormItem } from '../../../form-components'
import { DraggableList } from '../../../form-components/draggable-list'
import { useIsSidebar, useNodeRenderContext } from '../../../hooks'
import { IntentOption, normalizeIntents, generateIntentId, getIntentPortId } from './utils'
import { OtherIntentContainer, OtherIntentText, AddIntentButton, Spacer, PortContainer } from './styles'

interface IntentsProps {
  readOnly?: boolean
}

/**
 * 意图显示组件 - 支持警告样式
 */
interface IntentDisplayProps {
  label: string
  content: string
  isWarning?: boolean
}

const IntentDisplay: React.FC<IntentDisplayProps> = ({ label, content, isWarning = false }) => {
  return (
    <div style={{ padding: '4px', width: '100%', minHeight: '20px', fontSize: '12px', lineHeight: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ color: '#999', fontWeight: '500', flexShrink: 0, lineHeight: '16px', minWidth: '30px' }}>{label}</span>
      {isWarning ? (
        <Tag
          color="amber"
          size="small"
          style={{
            fontSize: '10px',
            lineHeight: '14px',
            padding: '1px 6px',
            margin: 0,
            borderRadius: '4px',
          }}
        >
          {content}
        </Tag>
      ) : (
        <span
          style={{
            color: '#333',
            flex: 1,
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            wordBreak: 'break-word',
            overflowWrap: 'break-word',
            lineHeight: '16px',
          }}
        >
          {content}
        </span>
      )}
    </div>
  )
}

/**
 * 意图识别节点的意图匹配组件
 */
export const Intents: React.FC<IntentsProps> = ({ readOnly = false }) => {
  const { t } = useTranslation()
  const isSidebar = useIsSidebar()
  const { node } = useNodeRenderContext()

  // 统一的端口更新函数
  const updatePorts = useCallback(() => {
    setTimeout(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    }, 0)
  }, [node])

  // 添加动态端口更新效果
  useLayoutEffect(() => {
    window.requestAnimationFrame(() => {
      const portsData = node.getData<WorkflowNodePortsData>(WorkflowNodePortsData)
      if (portsData) {
        portsData.updateDynamicPorts()
      }
    })
  }, [node, isSidebar])

  return (
    <>
      {/* 渲染动态输出端口 */}
      <Field<any[]> name="inputs.intents">
        {({ field }) => {
          const safeIntents = normalizeIntents(field.value)

          return (
            <>
              {/* 渲染动态输出端口 - 与FormDisplay对齐 */}
              <div className="relative">
                {safeIntents.map((intent: IntentOption, index: number) => (
                  // eslint-disable-next-line react/jsx-key
                  <PortContainer style={{ top: `${8 + index * 28}px` }} data-port-id={getIntentPortId(intent, index)} data-port-type="output" />
                ))}

                {/* 渲染"其他意图"的端口 */}
                <PortContainer style={{ top: `${8 + safeIntents.length * 28}px` }} data-port-id="0" data-port-type="output" />
              </div>
            </>
          )
        }}
      </Field>

      {isSidebar && (
        <FormItem name={t('workflowCanvas.intent.matching')} vertical>
          <Field<any[]> name="inputs.intents">
            {({ field }) => {
              const safeIntents = normalizeIntents(field.value)

              // 添加新意图
              const handleAddIntent = () => {
                const newIntent: IntentOption = {
                  name: '',
                  id: generateIntentId(),
                }
                field.onChange([...safeIntents, newIntent])
                updatePorts()
              }

              // 删除意图
              const handleDeleteIntent = (index: number) => {
                field.onChange(safeIntents.filter((_, i) => i !== index))
                updatePorts()
              }

              // 更新意图
              const handleUpdateIntent = (index: number, updates: Partial<IntentOption>) => {
                field.onChange(safeIntents.map((intent, i) => (i === index ? { ...intent, ...updates } : intent)))
              }

              // 意图列表变更处理（包括拖拽排序）
              const handleIntentsChange = (newIntents: IntentOption[]) => {
                field.onChange(newIntents)
                updatePorts()
              }

              // 渲染单个意图项
              const renderIntentItem = (intent: IntentOption, index: number, provided: any) => {
                return (
                  <div style={{ display: 'flex', flex: 1, height: '28px', alignItems: 'center' }}>
                    {/* 意图输入框 */}
                    <Input
                      value={intent.name}
                      onChange={(value: any) => {
                        handleUpdateIntent(index, { name: value })
                      }}
                      placeholder={t('workflowCanvas.intent.enterIntentDescription')}
                      style={{ flex: 1, height: '28px' }}
                      disabled={readOnly}
                    />
                  </div>
                )
              }

              return (
                <div>
                  <DraggableList
                    items={safeIntents}
                    onChange={handleIntentsChange}
                    renderItem={renderIntentItem}
                    onDelete={handleDeleteIntent}
                    readOnly={readOnly}
                    showDragHandle={true} // 总是显示拖拽句柄
                    canDelete={true} // 总是显示删除按钮，但禁用状态由组件内部控制
                    canAdd={false}
                    addButtonLabel=""
                    itemIdKey="id"
                    onAdd={handleAddIntent}
                    isDragDisabled={index => safeIntents.length <= 1} // 只有一个意图时禁用拖拽
                    isDeleteDisabled={index => safeIntents.length <= 1} // 只有一个意图时禁用删除
                  />

                  {/* "其他"选项 */}
                  <OtherIntentContainer>
                    <Spacer />
                    <OtherIntentText>{t('workflowCanvas.intent.otherIntent')}</OtherIntentText>
                  </OtherIntentContainer>

                  {/* 添加意图按钮 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', padding: '4px 8px', marginTop: '1px' }}>
                    <Spacer />
                    <AddIntentButton icon={<Plus size={16} />} onClick={handleAddIntent} disabled={readOnly} size="small" theme="borderless" />
                  </div>
                </div>
              )
            }}
          </Field>
        </FormItem>
      )}

      {!isSidebar && (
        <Field<any[]> name="inputs.intents">
          {({ field }) => {
            const safeIntents = normalizeIntents(field.value)

            return (
              <>
                {safeIntents.map((intent: IntentOption, index: number) => (
                  <IntentDisplay
                    key={intent.id || index}
                    label={t('workflowCanvas.intent.option')}
                    content={intent.name || t('workflowCanvas.intent.notConfigured')}
                    isWarning={!intent.name || intent.name.trim() === ''}
                  />
                ))}
                <IntentDisplay label={t('workflowCanvas.intent.otherIntent')} content="" />
              </>
            )
          }}
        </Field>
      )}
    </>
  )
}
