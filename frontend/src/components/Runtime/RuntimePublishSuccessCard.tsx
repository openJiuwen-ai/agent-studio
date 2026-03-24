import React from 'react'
import { Dialog, Button } from '@mui/material'
import publishSuccessIcon from '@/assets/icons/runtime-publish-success.svg'
import { useScopedTranslation } from '@/i18n'

export interface RuntimePublishSuccessCardProps {
  open: boolean
  onClose: () => void
  onGoTest: () => void
  goTestDisabled?: boolean
}

const RuntimePublishSuccessCard: React.FC<RuntimePublishSuccessCardProps> = ({ open, onClose, onGoTest, goTestDisabled = false }) => {
  const { t } = useScopedTranslation('runtime.publish.successCard')

  return (
    <Dialog
      open={open}
      onClose={onClose}
      PaperProps={{
        className: 'overflow-hidden',
        style: {
          width: 380,
          maxWidth: 'calc(100vw - 32px)',
          borderRadius: 10,
        },
      }}
    >
      <div className="px-8 py-7 text-center">
        <img src={publishSuccessIcon} alt="" className="mx-auto w-[120px] h-[64px]" aria-hidden="true" />
        <h3 className="text-3xl font-semibold text-[#1F2937] mt-3">{t('title')}</h3>
        <p className="text-[15px] text-[#9CA3AF] mt-3">{t('subtitle')}</p>
        <div className="mt-7 flex items-center justify-center gap-3">
          <Button
            variant="outlined"
            onClick={onClose}
            sx={{
              minWidth: 88,
              height: 36,
              color: '#111827',
              borderColor: '#D1D5DB',
              backgroundColor: '#FFFFFF',
              '&:hover': {
                borderColor: '#9CA3AF',
                backgroundColor: '#F9FAFB',
              },
            }}
          >
            {t('buttons.close')}
          </Button>
          <Button
            variant="contained"
            onClick={onGoTest}
            disabled={goTestDisabled}
            sx={{
              minWidth: 88,
              height: 36,
            }}
            className="btn-primary"
          >
            {t('buttons.goTest')}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}

export default RuntimePublishSuccessCard
