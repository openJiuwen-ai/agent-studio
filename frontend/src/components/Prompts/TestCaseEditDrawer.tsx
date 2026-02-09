import React from 'react'
import { useTranslation } from 'react-i18next'
import {
  Drawer,
  Typography,
  IconButton,
  TextField,
  Select,
  MenuItem,
  Button,
  Chip,
} from '@mui/material'
import { X, Edit, Trash2, CheckCircle } from 'lucide-react'
import FieldEditor, { type FieldType } from './FieldEditor'

export interface TestCaseDetail {
  id: number
  role: 'inputs' | 'label'
  content: string
  variableName?: string
  contentType?: FieldType
}

interface TestCaseEditDrawerProps {
  open: boolean
  onClose: () => void
  isViewMode: boolean
  currentTestCase: { id: number } | null
  testCaseDetails: TestCaseDetail[]
  onUpdateDetail: (id: number, field: string, value: string | FieldType) => void
  onDeleteDetailRow: (id: number) => void
  onSaveEdit: () => void
  onSwitchToEditMode: () => void
}

const TestCaseEditDrawer: React.FC<TestCaseEditDrawerProps> = ({
  open,
  onClose,
  isViewMode,
  currentTestCase,
  testCaseDetails,
  onUpdateDetail,
  onDeleteDetailRow,
  onSaveEdit,
  onSwitchToEditMode,
}) => {
  const { t } = useTranslation()

  const handleUpdateDetail = (id: number, field: string, value: string | FieldType) => {
    onUpdateDetail(id, field, value)
  }

  const handleDeleteDetailRow = (id: number) => {
    onDeleteDetailRow(id)
  }

  const handleSaveEdit = () => {
    onSaveEdit()
  }

  const handleSwitchToEditMode = () => {
    onSwitchToEditMode()
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: '800px',
          maxWidth: '90vw',
          padding: 0,
        },
      }}
    >
      <div className="h-full flex flex-col bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200/60 bg-white/60 backdrop-blur-sm">
          <div className="flex items-center space-x-4">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl shadow-sm">
              <Edit className="w-5 h-5 text-white" />
            </div>
            <div>
              <Typography variant="h6" className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                {isViewMode ? t('prompts.optimizeEditPage.testCaseDialog.view') : t('prompts.optimizeEditPage.testCaseDialog.edit')}
              </Typography>
              <div className="flex items-center space-x-2 mt-1">
                <Typography variant="body2" className="text-gray-600">
                  {t('prompts.optimizeEditPage.testCaseDialog.caseId', { id: currentTestCase?.id })}
                </Typography>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <IconButton
              size="small"
              onClick={onClose}
              sx={{
                color: '#6b7280',
                '&:hover': {
                  color: '#ef4444',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                },
              }}
            >
              <X className="w-4 h-4" />
            </IconButton>
          </div>
        </div>
        {/* 编辑表单 */}
        <div className="flex-1 p-6 space-y-6 overflow-y-auto">
          {testCaseDetails.map((detail, index) => (
            <div key={detail.id} className="bg-white/60 backdrop-blur-sm border border-gray-200/60 rounded-xl shadow-sm">
              <div className="flex items-center justify-between p-4 border-b border-gray-200/60 bg-gradient-to-r from-blue-50/50 to-indigo-50/50">
                <div className="flex items-center space-x-3">
                  <Typography variant="subtitle1" className="font-semibold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                    {t('prompts.optimizeEditPage.testCaseDialog.messageNumber', { number: index + 1 })}
                  </Typography>
                </div>
                <div className="flex items-center space-x-2">
                  <Chip
                    label={detail.role}
                    size="small"
                    sx={{
                      backgroundColor: detail.role === 'inputs' ? '#dbeafe' : '#f0fdf4',
                      color: detail.role === 'inputs' ? '#1d4ed8' : '#15803d',
                      fontWeight: 500,
                      fontSize: '12px',
                      borderRadius: '6px',
                    }}
                  />
                  {!isViewMode && (
                    <IconButton
                      size="small"
                      onClick={() => handleDeleteDetailRow(detail.id)}
                      sx={{
                        color: '#6b7280',
                        '&:hover': {
                          color: '#ef4444',
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        },
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </IconButton>
                  )}
                </div>
              </div>
              <div className="p-4 space-y-4">
                {/* 字段类型显示 */}
                <div>
                  <Typography variant="body2" className="text-gray-700 mb-2 font-medium">
                    {t('prompts.optimizeEditPage.testCaseDialog.fieldType')}
                  </Typography>
                  <TextField
                    value={detail.role}
                    size="small"
                    fullWidth
                    disabled={true}
                    sx={{
                      backgroundColor: '#f9fafb',
                      borderRadius: '8px',
                      '& .MuiOutlinedInput-root': {
                        borderRadius: '8px',
                        '& fieldset': {
                          borderColor: '#e5e7eb',
                        },
                        '&.Mui-disabled': {
                          backgroundColor: '#f9fafb',
                          '& fieldset': {
                            borderColor: '#e5e7eb',
                          },
                        },
                      },
                      '& .MuiInputBase-input.Mui-disabled': {
                        WebkitTextFillColor: '#6b7280',
                      },
                    }}
                  />
                </div>

                {/* 字段名称输入 */}
                <div>
                  <Typography variant="body2" className="text-gray-700 mb-2 font-medium">
                    {t('prompts.optimizeEditPage.testCaseDialog.fieldName')}
                  </Typography>
                  {detail.role === 'label' ? (
                    <Select
                      value={detail.variableName || ''}
                      onChange={e => handleUpdateDetail(detail.id, 'variableName', e.target.value)}
                      size="small"
                      fullWidth
                      disabled={isViewMode}
                      displayEmpty
                      sx={{
                        backgroundColor: 'white',
                        borderRadius: '8px',
                        '& .MuiOutlinedInput-notchedOutline': {
                          borderColor: '#e5e7eb',
                        },
                        '&:hover .MuiOutlinedInput-notchedOutline': {
                          borderColor: isViewMode ? '#e5e7eb' : '#3b82f6',
                        },
                        '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                          borderColor: isViewMode ? '#e5e7eb' : '#3b82f6',
                        },
                      }}
                    >
                      <MenuItem value="output">output</MenuItem>
                      <MenuItem value="tool_calls">tool_calls</MenuItem>
                    </Select>
                  ) : (
                    <TextField
                      value={detail.variableName || ''}
                      onChange={e => handleUpdateDetail(detail.id, 'variableName', e.target.value)}
                      size="small"
                      fullWidth
                      disabled={true}
                      placeholder={t('prompts.optimizeEditPage.testCaseDialog.fieldNamePlaceholder')}
                      sx={{
                        backgroundColor: '#f9fafb',
                        borderRadius: '8px',
                        '& .MuiOutlinedInput-root': {
                          borderRadius: '8px',
                          '& fieldset': {
                            borderColor: '#e5e7eb',
                          },
                          '&.Mui-disabled': {
                            backgroundColor: '#f9fafb',
                            '& fieldset': {
                              borderColor: '#e5e7eb',
                            },
                          },
                        },
                        '& .MuiInputBase-input.Mui-disabled': {
                          WebkitTextFillColor: '#6b7280',
                        },
                      }}
                    />
                  )}
                </div>

                {/* 字段值输入 */}
                <div>
                  <FieldEditor
                    label={t('prompts.optimizeEditPage.testCaseDialog.fieldValue')}
                    value={detail.content}
                    fieldType={detail.contentType || 'PlainText'}
                    placeholder={t('prompts.optimizeEditPage.testCaseDialog.fieldValuePlaceholder')}
                    maxLength={2000}
                    showCharCount={true}
                    disabled={isViewMode}
                    allowedTypes={['PlainText', 'Code', 'JSON', 'Markdown']}
                    onValueChange={value => handleUpdateDetail(detail.id, 'content', value)}
                    onTypeChange={type => handleUpdateDetail(detail.id, 'contentType', type)}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200/60 bg-white/60 backdrop-blur-sm">
          <Button
            variant="outlined"
            onClick={onClose}
            sx={{
              borderColor: '#e5e7eb',
              color: '#6b7280',
              '&:hover': {
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.05)',
                color: '#ef4444',
              },
              borderRadius: '8px',
              textTransform: 'none',
              fontWeight: 500,
              minWidth: '100px',
            }}
          >
            {isViewMode ? t('prompts.optimizeEditPage.testCaseDialog.close') : t('prompts.optimizeEditPage.testCaseDialog.cancel')}
          </Button>
          {isViewMode ? (
            <Button
              variant="contained"
              onClick={handleSwitchToEditMode}
              startIcon={<Edit className="w-4 h-4" />}
              sx={{
                background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
                },
                transition: 'all 0.2s ease',
                borderRadius: '8px',
                textTransform: 'none',
                fontWeight: 600,
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                minWidth: '100px',
              }}
            >
              {t('prompts.optimizeEditPage.testCaseDialog.editButton')}
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={handleSaveEdit}
              startIcon={<CheckCircle className="w-4 h-4" />}
              sx={{
                background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)',
                  transform: 'translateY(-1px)',
                  boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
                },
                transition: 'all 0.2s ease',
                borderRadius: '8px',
                textTransform: 'none',
                fontWeight: 600,
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                minWidth: '100px',
              }}
            >
              {t('prompts.optimizeEditPage.testCaseDialog.save')}
            </Button>
          )}
        </div>
      </div>
    </Drawer>
  )
}

export default TestCaseEditDrawer
