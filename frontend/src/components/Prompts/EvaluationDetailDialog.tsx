import React from 'react'
import { useTranslation } from 'react-i18next'
import { X } from 'lucide-react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
  Typography,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Tooltip,
} from '@mui/material'
import { Pagination } from '@/components/Common/common-table'

// 截断文本函数
const truncateText = (text: string, maxLength: number = 400): string => {
  if (!text || text.length <= maxLength) {
    return text
  }
  return text.substring(0, maxLength) + '...'
}

export interface EvaluationDataItem {
  userInput: string
  modelAnswer: string
  referenceAnswer: string
  score: number
  reason: string
}

interface EvaluationDetailDialogProps {
  open: boolean
  onClose: () => void
  type: 'original' | 'optimized'
  loading: boolean
  evaluationData: EvaluationDataItem[]
  evaluateCases: any[]
  pageNum: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

const EvaluationDetailDialog: React.FC<EvaluationDetailDialogProps> = ({
  open,
  onClose,
  type,
  loading,
  evaluationData,
  evaluateCases,
  pageNum,
  pageSize,
  onPageChange,
  onPageSizeChange,
}) => {
  const { t } = useTranslation()

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: '16px',
          background: 'linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.95))',
          backdropFilter: 'blur(10px)',
          maxWidth: '70vw',
          width: '70vw',
        },
      }}
    >
      <DialogTitle
        sx={{
          borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
          background: 'linear-gradient(to right, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.8))',
          py: 2.5,
        }}
      >
        <Box className="flex items-center justify-between">
          <Typography
            variant="h6"
            className="font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent"
          >
            {type === 'original'
              ? t('prompts.optimizeEditPage.optimizationResult.originalPrompt')
              : t('prompts.optimizeEditPage.optimizationResult.optimizedPrompt')}
            {t('prompts.optimizeEditPage.optimizationResult.evaluationDetail')}
          </Typography>
          <IconButton
            onClick={onClose}
            size="small"
            sx={{
              color: '#6b7280',
              '&:hover': {
                color: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
              },
              transition: 'all 0.2s ease',
            }}
          >
            <X className="w-5 h-5" />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent sx={{ p: 3, bgcolor: 'transparent' }}>
        {loading ? (
          <Box className="flex items-center justify-center py-8">
            <CircularProgress size={40} />
            <Typography variant="body1" className="ml-4" sx={{ color: '#6b7280' }}>
              {t('prompts.optimizeEditPage.optimizationResult.loading')}
            </Typography>
          </Box>
        ) : evaluationData.length === 0 ? (
          <Box className="flex items-center justify-center py-8">
            <Typography variant="body1" sx={{ color: '#6b7280' }}>
              {t('prompts.optimizeEditPage.optimizationResult.noEvaluationData')}
            </Typography>
          </Box>
        ) : (
          <>
            <TableContainer
              component={Paper}
              className="mt-2"
              sx={{
                borderRadius: '12px',
                border: '1px solid rgba(0, 0, 0, 0.06)',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
                overflow: 'hidden',
              }}
            >
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f9fafb', '& th': { py: 2 } }}>
                    <TableCell
                      width="4%"
                      className="font-semibold"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.testCaseDialog.sequenceNumberColumn')}
                    </TableCell>
                    <TableCell
                      width="20%"
                      className="font-semibold"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.optimizationResult.userInput')}
                    </TableCell>
                    <TableCell
                      width="25%"
                      className="font-semibold"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.optimizationResult.modelAnswer')}
                    </TableCell>
                    <TableCell
                      width="25%"
                      className="font-semibold"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.optimizationResult.referenceAnswer')}
                    </TableCell>
                    <TableCell
                      width="7%"
                      className="font-semibold text-center"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.optimizationResult.modelScore')}
                    </TableCell>
                    <TableCell
                      width="24%"
                      className="font-semibold"
                      sx={{
                        fontWeight: 600,
                        color: '#374151',
                        fontSize: '0.875rem',
                        borderBottom: '2px solid #e5e7eb',
                      }}
                    >
                      {t('prompts.optimizeEditPage.optimizationResult.scoreReason')}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {evaluationData.map((item, index) => (
                    <TableRow
                      key={index}
                      hover
                      sx={{
                        '&:hover': {
                          backgroundColor: 'rgba(59, 130, 246, 0.04)',
                        },
                        '&:last-child td': {
                          borderBottom: 'none',
                        },
                      }}
                    >
                      <TableCell
                        sx={{
                          color: '#6b7280',
                          fontSize: '0.875rem',
                          fontWeight: 500,
                        }}
                      >
                        {index + 1}
                      </TableCell>
                      <Tooltip title={item.userInput || ''} arrow placement="top">
                        <TableCell
                          className="text-sm"
                          sx={{
                            color: '#374151',
                            fontSize: '0.875rem',
                            maxWidth: '200px',
                          }}
                        >
                          {truncateText(item.userInput)}
                        </TableCell>
                      </Tooltip>
                      <Tooltip title={item.modelAnswer || ''} arrow placement="top">
                        <TableCell
                          className="text-sm whitespace-pre-wrap"
                          sx={{
                            color: '#374151',
                            fontSize: '0.875rem',
                            maxWidth: '250px',
                          }}
                        >
                          {truncateText(item.modelAnswer)}
                        </TableCell>
                      </Tooltip>
                      <Tooltip title={item.referenceAnswer || ''} arrow placement="top">
                        <TableCell
                          className="text-sm whitespace-pre-wrap"
                          sx={{
                            color: '#374151',
                            fontSize: '0.875rem',
                            maxWidth: '250px',
                          }}
                        >
                          {truncateText(item.referenceAnswer)}
                        </TableCell>
                      </Tooltip>
                      <TableCell align="center">
                        <Chip
                          label={item.score}
                          size="small"
                          color={item.score >= 80 ? 'success' : item.score >= 60 ? 'warning' : 'error'}
                          sx={{
                            fontWeight: 600,
                            fontSize: '0.75rem',
                          }}
                        />
                      </TableCell>
                      <Tooltip title={item.reason || ''} arrow placement="top">
                        <TableCell
                          className="text-sm"
                          sx={{
                            color: '#6b7280',
                            fontSize: '0.875rem',
                            maxWidth: '200px',
                          }}
                        >
                          {truncateText(item.reason)}
                        </TableCell>
                      </Tooltip>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Box
              className="mt-4 rounded-xl border"
              sx={{
                p: 3,
                background: 'linear-gradient(to right, rgba(249, 250, 251, 0.8), rgba(243, 244, 246, 0.8))',
                border: '1px solid rgba(0, 0, 0, 0.06)',
                borderRadius: '12px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  color: '#374151',
                  fontSize: '0.9375rem',
                  fontWeight: 500,
                }}
              >
                <strong style={{ color: '#1f2937', fontWeight: 600 }}>{t('prompts.optimizeEditPage.optimizationResult.averageScore')}</strong>{' '}
                <span
                  style={{
                    color: '#3b82f6',
                    fontWeight: 700,
                    fontSize: '1.125rem',
                  }}
                >
                  {Math.round(evaluationData.reduce((sum, item) => sum + item.score, 0) / evaluationData.length)}
                </span>
                <span style={{ color: '#6b7280', marginLeft: '4px' }}>{t('prompts.optimizeEditPage.optimizationResult.scoreUnit')}</span>
              </Typography>
            </Box>

            {/* 分页组件 */}
            {!loading && evaluateCases.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
                <Pagination
                  pager={{
                    total: evaluateCases.length,
                    currentPage: pageNum,
                    pageSize: pageSize,
                    pageSizeOptions: [10, 20, 30, 50],
                  }}
                  loading={loading}
                  onPagerChange={(page, pageSize) => {
                    onPageSizeChange(pageSize)
                    onPageChange(page)
                  }}
                />
              </Box>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default EvaluationDetailDialog

