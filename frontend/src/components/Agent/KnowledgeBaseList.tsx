import Typography from '@mui/material/Typography'
import { Settings, Trash2, BookOpen } from 'lucide-react'
import { useState } from 'react'
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog'
import { useScopedTranslation } from '@/i18n'

interface KnowledgeBaseItem {
  id: string
  name: string
  description?: string
}

const KnowledgeBaseList = ({
  knowledgeBaseObjects,
  onClick,
  disabled = false,
}: {
  knowledgeBaseObjects: KnowledgeBaseItem[]
  onClick: (operate: 'delete' | 'setting', knowledgeBaseId: string) => void
  disabled?: boolean
}) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null)

  return (
    <div className="space-y-3">
      {knowledgeBaseObjects.map(kb => (
        <div
          key={kb.id}
          className="flex items-start justify-between py-2 px-3 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all duration-200"
        >
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-green-100 to-emerald-100 rounded-lg flex items-center justify-center border border-green-200 mt-1">
              <BookOpen className="w-4 h-4 text-green-600" />
            </div>
            <div className="flex-1 min-w-0">
              <Typography sx={{ fontWeight: 'bold', fontSize: '1rem' }}>{kb.name}</Typography>
              {kb.description && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontSize: '0.875rem',
                    lineHeight: 1.4,
                    mt: 0.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {kb.description}
                </Typography>
              )}
            </div>
          </div>
          <div className="flex space-x-4 pt-1">
            <button
              title={t('orchestrationPage.knowledgeBaseList.settingsTitle')}
              onClick={e => {
                e.stopPropagation()
                onClick('setting', kb.id)
              }}
            >
              <Settings className="w-4 h-4 text-gray-600" />
            </button>
            <button
              title={t('orchestrationPage.knowledgeBaseList.deleteTitle')}
              onClick={e => {
                e.stopPropagation()
                if (!disabled) {
                  setPendingDelete({ id: kb.id, name: kb.name })
                  setConfirmOpen(true)
                }
              }}
              disabled={disabled}
              className={`${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Trash2 className="w-4 h-4 text-gray-600" />
            </button>
          </div>
        </div>
      ))}
      {knowledgeBaseObjects.length === 0 && (
        <div className="text-center py-6 text-gray-500">{t('orchestrationPage.knowledgeBaseList.list.empty')}</div>
      )}
      <DeleteConfirmationDialog
        isOpen={confirmOpen}
        onClose={() => {
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        onConfirm={() => {
          if (pendingDelete) onClick('delete', pendingDelete.id)
          setConfirmOpen(false)
          setPendingDelete(null)
        }}
        itemType="knowledgeBase"
        itemName={pendingDelete?.name || ''}
        title={t('orchestrationPage.knowledgeBaseList.removeDialog.title')}
        confirmButtonText={t('orchestrationPage.knowledgeBaseList.removeDialog.confirmButtonText')}
        message={t('orchestrationPage.knowledgeBaseList.removeDialog.message')}
      />
    </div>
  )
}

export default KnowledgeBaseList

