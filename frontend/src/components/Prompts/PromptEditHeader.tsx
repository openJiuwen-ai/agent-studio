import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Save, Copy, GitBranch, Code, Sparkles, Edit } from 'lucide-react'
import { Button, Typography, IconButton } from '@mui/material'
import { ConditionalTooltip } from './index'
import { formatDraftDateTime } from '@/utils/prompts/utils'
import type { ComparisonGroupData } from '@/types/promptType'

export interface PromptEditHeaderProps {
  isNew: boolean
  prompt: {
    name: string
    description: string
  }
  loading: boolean
  isReadOnlyMode: boolean
  onOpenEditInfoDialog: () => void
  isNewPromptScenario: boolean
  isDraftEdited: boolean
  draftSavedTime: Date | null
  latestVersion: string
  isComparisonMode: boolean
  onEnterComparisonMode: () => void
  onNavigateToOptimization: () => void
  onOpenVersionHistory: () => void
  onSubmitVersion: () => void
  onExitComparison: () => void
  comparisonGroupsData: ComparisonGroupData[]
  onAddControlGroup: () => void
}

const PromptEditHeader: React.FC<PromptEditHeaderProps> = ({
  isNew,
  prompt,
  loading,
  isReadOnlyMode,
  onOpenEditInfoDialog,
  isNewPromptScenario,
  isDraftEdited,
  draftSavedTime,
  latestVersion,
  isComparisonMode,
  onEnterComparisonMode,
  onNavigateToOptimization,
  onOpenVersionHistory,
  onSubmitVersion,
  onExitComparison,
  comparisonGroupsData,
  onAddControlGroup,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div 
      className="flex items-center bg-white/60 backdrop-blur-sm border border-gray-200/60 shadow-sm"
      style={{
        padding: 'clamp(0.375rem, 0.5vw, 0.625rem)', // 减小内边距
        minHeight: 'clamp(3.5rem, 4.5vh, 4rem)',
        width: '100%',
        maxWidth: '100%',
        overflow: 'hidden',
      }}
    >
      <IconButton
        onClick={() => navigate('/dashboard/prompts')}
        className="hover:bg-gray-100/80 transition-colors duration-200"
        sx={{
          width: 'clamp(1.75rem, 2vw, 2.25rem)',
          height: 'clamp(1.75rem, 2vw, 2.25rem)',
          '&:hover': {
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            transform: 'translateX(-2px)',
          },
          transition: 'all 0.2s ease',
        }}
      >
        <ArrowLeft 
          className="text-gray-600"
          style={{
            width: 'clamp(0.875rem, 1vw, 1.125rem)',
            height: 'clamp(0.875rem, 1vw, 1.125rem)',
          }}
        />
      </IconButton>
      <div 
        className="flex items-center min-w-0"
        style={{
          gap: 'clamp(0.25rem, 0.4vw, 0.375rem)', // 减小间距
          marginLeft: 'clamp(0.375rem, 0.6vw, 0.625rem)', // 减小左边距
          overflow: 'hidden',
          flex: '0 0 auto', // 完全不扩展，严格按内容大小
        }}
      >
        <div 
          className="min-w-0" 
          style={{ 
            maxWidth: 'clamp(200px, 30vw, 400px)', // 使用固定的最大宽度范围
            overflow: 'hidden',
            flex: '0 0 auto', // 完全不扩展，严格按内容大小
            minWidth: 0, // 确保可以收缩到 0
          }}
        >
          <ConditionalTooltip title={isNew ? t('prompts.promptEdit.header.createPrompt') : prompt.name || t('prompts.promptEdit.header.promptName')}>
            <h1 
              className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent cursor-pointer"
              style={{
                fontSize: 'clamp(0.875rem, 0.85vw, 1.125rem)',
                lineHeight: 1.5,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                width: '100%',
              }}
            >
              {isNew ? t('prompts.promptEdit.header.createPrompt') : prompt.name || t('prompts.promptEdit.header.promptName')}
            </h1>
          </ConditionalTooltip>
          <ConditionalTooltip
            title={isNew ? t('prompts.promptEdit.header.createDescription') : prompt.description || t('prompts.promptEdit.header.promptDescription')}
          >
            <p 
              className="text-gray-600 cursor-pointer"
              style={{
                fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                marginTop: 'clamp(0.125rem, 0.1vh, 0.1875rem)',
                lineHeight: 1.6,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                width: '100%',
              }}
            >
              {isNew ? t('prompts.promptEdit.header.createDescription') : prompt.description || t('prompts.promptEdit.header.promptDescription')}
            </p>
          </ConditionalTooltip>
        </div>
        <IconButton
          onClick={onOpenEditInfoDialog}
          className="text-blue-600 hover:bg-blue-50 flex-shrink-0"
          title={t('prompts.promptEdit.header.editBasicInfo')}
          disabled={loading || isReadOnlyMode}
          sx={{
            width: 'clamp(1.75rem, 2vw, 2.25rem)',
            height: 'clamp(1.75rem, 2vw, 2.25rem)',
          }}
        >
          <Edit 
            style={{
              width: 'clamp(0.875rem, 1vw, 1.125rem)',
              height: 'clamp(0.875rem, 1vw, 1.125rem)',
            }}
          />
        </IconButton>
      </div>

      <div 
        className="flex items-center flex-shrink-0"
        style={{
          gap: 'clamp(0.375rem, 0.7vw, 0.75rem)', // 减小右侧按钮区域的间距
          marginLeft: 'auto', // 自动推到右边，消除中间空白
        }}
      >
        <div
          className={`flex items-center transition-opacity ${isReadOnlyMode ? 'opacity-60' : 'opacity-100'}`}
          style={{ 
            pointerEvents: isReadOnlyMode ? 'none' : 'auto',
            gap: 'clamp(0.375rem, 0.7vw, 0.625rem)',
          }}
        >
          {/* 状态信息 - 只有在非新建场景或用户已编辑时才显示 */}
          {(!isNewPromptScenario || isDraftEdited) && (
            <div 
              className="flex items-center"
              style={{
                gap: 'clamp(0.375rem, 0.7vw, 0.75rem)',
                marginRight: 'clamp(0.375rem, 0.7vw, 0.75rem)',
              }}
            >
              <div 
                className="flex items-center"
                style={{
                  gap: 'clamp(0.25rem, 0.4vw, 0.375rem)',
                }}
              >
                <div 
                  className={`rounded-full ${isDraftEdited ? 'bg-orange-500' : 'bg-green-500'}`}
                  style={{
                    width: 'clamp(0.375rem, 0.5vw, 0.4375rem)',
                    height: 'clamp(0.375rem, 0.5vw, 0.4375rem)',
                  }}
                ></div>
                <Typography 
                  variant="body2" 
                  className={`font-medium ${isDraftEdited ? 'text-orange-600' : 'text-green-600'}`}
                  sx={{
                    fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                  }}
                >
                  {isDraftEdited ? t('prompts.promptEdit.header.modifiedNotSubmitted') : t('prompts.promptEdit.header.submitted')}
                </Typography>
              </div>

              {/* 根据状态显示不同信息 */}
              {isDraftEdited
                ? draftSavedTime && (
                    <div 
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.35vw, 0.375rem)',
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        className="text-gray-500"
                        sx={{
                          fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                        }}
                      >
                        {t('prompts.promptEdit.header.draftSavedTime')}: {formatDraftDateTime(draftSavedTime)}
                      </Typography>
                    </div>
                  )
                : latestVersion && (
                    <div 
                      className="flex items-center"
                      style={{
                        gap: 'clamp(0.25rem, 0.35vw, 0.375rem)',
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        className="text-gray-500"
                        sx={{
                          fontSize: 'clamp(0.6875rem, 0.65vw, 0.8125rem)',
                        }}
                      >
                        {t('prompts.promptEdit.header.latestVersion')}: {latestVersion}
                      </Typography>
                    </div>
                  )}
            </div>
          )}

          {!isComparisonMode ? (
            <>
              <Button
                variant="outlined"
                startIcon={<Code style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onEnterComparisonMode}
                sx={{
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    borderColor: '#f97316',
                    backgroundColor: 'rgba(249, 115, 22, 0.05)',
                    color: '#f97316',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(249, 115, 22, 0.15)',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 500,
                }}
              >
                {t('prompts.promptEdit.header.enterComparisonMode')}
              </Button>
              <Button
                variant="outlined"
                startIcon={<Sparkles style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onNavigateToOptimization}
                sx={{
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    color: '#a855f7',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(168, 85, 247, 0.15)',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 500,
                }}
              >
                {t('prompts.promptEdit.header.promptOptimization')}
              </Button>
              <Button
                variant="outlined"
                startIcon={<GitBranch style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onOpenVersionHistory}
                sx={{
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    color: '#10b981',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.15)',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 500,
                }}
              >
                {t('prompts.promptEdit.header.versionHistory')}
              </Button>

              <Button
                variant="contained"
                startIcon={<Save style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onSubmitVersion}
                sx={{
                  background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 600,
                  boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                }}
              >
                {t('prompts.promptEdit.header.submitNewVersion')}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outlined"
                startIcon={<ArrowLeft style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onExitComparison}
                sx={{
                  borderColor: '#e5e7eb',
                  color: '#6b7280',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                    color: '#3b82f6',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(59, 130, 246, 0.15)',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 500,
                }}
              >
                {t('prompts.promptEdit.header.exitComparison')}
              </Button>
              <Button
                variant="contained"
                startIcon={<Copy style={{ width: 'clamp(0.75rem, 0.75vw, 0.9375rem)', height: 'clamp(0.75rem, 0.75vw, 0.9375rem)' }} />}
                onClick={onAddControlGroup}
                disabled={comparisonGroupsData.length >= 3}
                sx={{
                  background:
                    comparisonGroupsData.length >= 3
                      ? 'linear-gradient(135deg, #9ca3af 0%, #6b7280 100%)'
                      : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  fontSize: 'clamp(0.6875rem, 0.7vw, 0.8125rem)',
                  padding: 'clamp(0.3125rem, 0.45vh, 0.4375rem) clamp(0.625rem, 0.75vw, 0.875rem)',
                  minHeight: 'clamp(1.875rem, 2.75vh, 2.25rem)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                    transform: 'translateY(-1px)',
                    boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)',
                  },
                  '&:disabled': {
                    background: 'linear-gradient(135deg, #d1d5db 0%, #9ca3af 100%)',
                    color: '#6b7280',
                  },
                  transition: 'all 0.2s ease',
                  borderRadius: 'clamp(0.3125rem, 0.45vw, 0.4375rem)',
                  textTransform: 'none',
                  fontWeight: 600,
                  boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)',
                }}
              >
                增加对照组 ({comparisonGroupsData.length - 1}/2)
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default PromptEditHeader
