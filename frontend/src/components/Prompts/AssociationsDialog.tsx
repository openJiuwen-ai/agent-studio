import React from 'react'
import { Dialog, DialogTitle, DialogContent, Box, Typography, IconButton } from '@mui/material'
import { X, ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { type RelationObj } from '@test-agentstudio/api-client'
import { useNavigate } from 'react-router-dom'
import { handleRelationObjNavigate } from '@/utils/prompts/utils'

interface AssociationsDialogProps {
  open: boolean
  onClose: () => void
  associations: RelationObj[]
  versionName: string
  workspaceId: string
}

export const AssociationsDialog: React.FC<AssociationsDialogProps> = ({
  open,
  onClose,
  associations,
  versionName,
  workspaceId,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const handleNavigateToObject = (relationObj: RelationObj) => {
    handleRelationObjNavigate(relationObj, workspaceId, navigate)
    onClose()
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
        },
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={1}>
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: 1,
                background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ExternalLink size={16} color="white" />
            </Box>
            <Box>
              <Typography variant="h6" component="div" fontWeight="600">
                {t('components.prompts.associationsDialog.title')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('components.prompts.associationsDialog.subtitle', { versionName, count: associations.length })}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <X size={20} />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
          {associations.length === 0 ? (
            <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={4} color="text.secondary">
              <ExternalLink size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
              <Typography variant="body1">{t('components.prompts.associationsDialog.noAssociations')}</Typography>
            </Box>
          ) : (
            <Box display="flex" flexDirection="column" gap={2}>
              {associations.map((relationObj, index) => (
                <Box
                  key={relationObj.obj_id}
                  sx={{
                    p: 3,
                    border: '1px solid',
                    borderColor: 'grey.200',
                    borderRadius: 2,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      borderColor: 'primary.main',
                      backgroundColor: 'primary.50',
                      transform: 'translateY(-1px)',
                      boxShadow: '0 4px 12px rgba(59, 130, 246, 0.15)',
                    },
                  }}
                  onClick={() => handleNavigateToObject(relationObj)}
                >
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Box display="flex" alignItems="center" gap={2}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: 1,
                          background: 'linear-gradient(135deg, #f3f4f6, #e5e7eb)',
                          border: '2px solid #d1d5db',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '14px',
                          fontWeight: 'bold',
                          color: '#374151',
                        }}
                      >
                        {relationObj.obj_type_name.charAt(0)}
                      </Box>
                      <Box>
                        <Typography variant="subtitle1" fontWeight="600" color="text.primary">
                          {relationObj.obj_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {relationObj.obj_type_name} · ID: {relationObj.obj_id}
                        </Typography>
                        {relationObj.obj_version && (
                          <Typography variant="caption" color="text.secondary">
                            {t('components.prompts.associationsDialog.version', { version: relationObj.obj_version })}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                    <ExternalLink size={16} style={{ opacity: 0.5 }} />
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}
