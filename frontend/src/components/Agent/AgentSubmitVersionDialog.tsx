import React, { useEffect, useMemo, useState } from 'react'
import { Dialog, Button } from '@mui/material'
import { Tag } from 'lucide-react'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import { AgentService, AgentPublishRequest, AgentPublishResponse, AgentVersionListRequest, AgentVersionListResponse } from '@test-agentstudio/api-client'
import { useAgentStore } from '@/stores/useAgentStore'
import { useScopedTranslation } from '@/i18n'

export interface AgentSubmitVersionDialogProps {
  open: boolean
  agentId?: string
  onClose: () => void
  onVersionSubmitted?: (version?: string) => void
}

const AgentSubmitVersionDialog: React.FC<AgentSubmitVersionDialogProps> = ({ open, agentId, onClose, onVersionSubmitted }) => {
  const { saveAgent, saveError } = useAgentStore()
  const [versionNumber, setVersionNumber] = useState('')
  const [versionDescription, setVersionDescription] = useState('')
  const [isPublishing, setIsPublishing] = useState(false)
  const [publishError, setPublishError] = useState<string | null>(null)
  const [latestVersionDisplay, setLatestVersionDisplay] = useState<string | null>(null)
  const { t } = useScopedTranslation('agents.agentPublishDialog')

  const suggestedVersion = useMemo(() => {
    const base = latestVersionDisplay || ''
    const version = base && base !== 'draft' ? base : ''
    if (version) {
      const parts = version.replace(/^v/, '').split('.')
      if (parts.length === 3) {
        const patch = parseInt(parts[2] || '0', 10) + 1
        return `v${parts[0]}.${parts[1]}.${patch}`
      }
    }
    return 'v0.0.1'
  }, [latestVersionDisplay])

  useEffect(() => {
    const loadLatestVersion = async () => {
      if (!open || !agentId) return
      try {
        const req: AgentVersionListRequest = {
          agent_id: agentId,
          space_id: getDefaultSpaceId(),
        }
        const resp: AgentVersionListResponse = await AgentService.getAgentVersionList(req)
        if ((resp.code === 200 || resp.code === 0) && resp.data?.versions?.length) {
          const toMs = (ts: any): number => {
            if (typeof ts === 'number') {
              return ts > 1e12 ? ts : ts > 1e10 ? ts : ts * 1000
            }
            const n = Date.parse(String(ts || ''))
            return isNaN(n) ? 0 : n
          }
          const published = resp.data.versions.filter((v: any) => {
            const ver = String(v.agent_version || '').toLowerCase()
            return ver !== '' && ver !== 'draft'
          })
          if (published.length > 0) {
            const latest = published.sort((a: any, b: any) => toMs(b.create_time) - toMs(a.create_time))[0]
            const ver = latest.agent_version?.startsWith('v') ? latest.agent_version : `v${latest.agent_version}`
            setLatestVersionDisplay(ver)
          } else {
            setLatestVersionDisplay(null)
          }
        } else {
          setLatestVersionDisplay(null)
        }
      } catch (e) {
        setLatestVersionDisplay(null)
      }
    }

    if (open) {
      loadLatestVersion()
      setVersionDescription('')
      setPublishError(null)
      setIsPublishing(false)
    } else {
      setVersionNumber('')
      setVersionDescription('')
      setPublishError(null)
      setIsPublishing(false)
      setLatestVersionDisplay(null)
    }
  }, [open, agentId])

  useEffect(() => {
    if (open) {
      setVersionNumber(suggestedVersion)
    }
  }, [open, suggestedVersion])

  const handlePublish = async () => {
    if (!agentId) {
      setPublishError(t('errors.missingAgent'))
      return
    }

    if (!versionNumber.trim()) {
      setPublishError(t('errors.missingVersion'))
      return
    }
    if (!versionDescription.trim()) {
      setPublishError(t('errors.missingDescription'))
      return
    }

    try {
      setIsPublishing(true)
      setPublishError(null)
      const saveSuccess = await saveAgent()
      if (!saveSuccess) {
        throw new Error(saveError || t('errors.saveFailed'))
      }
      const publishRequest: AgentPublishRequest = {
        agent_id: agentId,
        space_id: getDefaultSpaceId(),
        version: versionNumber.trim(),
        version_description: versionDescription.trim(),
      }

      const response: AgentPublishResponse = await AgentService.publishAgent(publishRequest)

      if (response.code === 200 && response.data?.success) {
        onVersionSubmitted?.(versionNumber.trim())
        onClose()
      } else {
        throw new Error(response.message || t('errors.publishFailed'))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('errors.publishFailedRetry')
      setPublishError(errorMessage)
    } finally {
      setIsPublishing(false)
    }
  }
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        className: 'overflow-hidden shadow-2xl',
        style: {
          backgroundColor: '#fafafa',
          borderRadius: '16px',
          maxHeight: '90vh',
          margin: '5vh auto',
        },
      }}
    >
      {/* 头部 */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-4 sm:p-6">
        <div className="flex items-center">
          <div className="bg-white/20 backdrop-blur-sm p-2 sm:p-3 rounded-xl">
            <Tag className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
          </div>
          <div className="ml-3 sm:ml-4">
            <h2 className="text-lg sm:text-xl font-bold">{t('title')}</h2>
            <p className="text-blue-100 text-xs sm:text-sm mt-1">{t('subtitle')}</p>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="p-4 sm:p-6 max-h-[calc(90vh-200px)] overflow-y-auto">
        <div className="space-y-4 sm:space-y-5">
          {/* 版本信息卡片 */}
          <div className="bg-white rounded-xl border border-gray-200 p-3 sm:p-5 shadow-sm">
            {/* 版本号 */}
            <div className="mb-3 sm:mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('fields.version.label')} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={versionNumber}
                onChange={e => {
                  const v = e.target.value
                  if (v.length <= 80) setVersionNumber(v)
                }}
                disabled={isPublishing}
                placeholder={t('fields.version.placeholder')}
                className="w-full px-3 sm:px-4 py-2 sm:py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors text-sm"
                maxLength={80}
              />
              <div className="flex justify-between items-center mt-1 sm:mt-2">
                <p className="text-xs text-gray-500">{t('fields.version.hint')}</p>
                <span className="text-xs text-gray-500">{versionNumber.length}/80</span>
              </div>
            </div>

            {/* 版本描述 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('fields.description.label')} <span className="text-red-500">*</span>
              </label>
              <textarea
                value={versionDescription}
                onChange={e => {
                  const text = e.target.value
                  if (text.length <= 200) {
                    setVersionDescription(text)
                  }
                }}
                disabled={isPublishing}
                placeholder={t('fields.description.placeholder')}
                rows={3}
                maxLength={200}
                className="w-full px-3 sm:px-4 py-2 sm:py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed resize-none transition-colors text-sm"
              />
              <div className="flex justify-between items-center mt-1 sm:mt-2">
                <p className="text-xs text-gray-500">{t('fields.description.hint')}</p>
                <span className="text-xs text-gray-500">{versionDescription.length}/200</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 底部按钮 */}
      <div className="bg-gray-50 px-4 sm:px-6 py-3 sm:py-4 rounded-b-2xl border-t border-gray-200">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-0">
          <Button
            onClick={onClose}
            disabled={isPublishing}
            variant="outlined"
            className="w-full sm:w-auto px-4 sm:px-6 py-2 border-gray-300 text-gray-700 hover:bg-gray-50"
          >
            {t('buttons.cancel')}
          </Button>
          <Button
            onClick={handlePublish}
            disabled={isPublishing || !versionNumber.trim() || !versionDescription.trim()}
            variant="contained"
            className="btn-primary w-full sm:w-auto px-6 sm:px-8 py-2 font-medium"
          >
            {isPublishing ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                {t('status.publishing')}
              </div>
            ) : (
              <div className="flex items-center justify-center">{t('buttons.confirm')}</div>
            )}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}

export default AgentSubmitVersionDialog
