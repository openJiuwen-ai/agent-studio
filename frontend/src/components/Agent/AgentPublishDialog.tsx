import React, { useEffect, useState } from 'react'
import { Dialog, Button, IconButton } from '@mui/material'
import { X } from 'lucide-react'
import dayjs from 'dayjs'
import { getDefaultSpaceId } from '@/utils/spaceUtils'
import {
  AgentService,
  AgentVersionListRequest,
  AgentVersionListResponse,
  useDeployRuntime,
  useRemoveRuntime,
  type AgentVersionInfo,
  type RuntimeDeployRequest,
} from '@test-agentstudio/api-client'
import { useScopedTranslation } from '@/i18n'
import AgentSubmitVersionDialog from './AgentSubmitVersionDialog'
import publishDialogDraftIcon from '@/assets/icons/runtime-publish-dialog-draft.svg.svg'
import publishDialogVersionIcon from '@/assets/icons/runtime-publish-dialog-version.svg'

export interface AgentPublishDialogProps {
  open: boolean
  agentId?: string
  agentName?: string
  port?: string
  hasRuntimeDeployment?: boolean
  onClose: () => void
  onPublished?: () => void
}

const toMs = (ts: number | string): number => {
  if (typeof ts === 'number') {
    return ts > 1e12 ? ts : ts > 1e10 ? ts : ts * 1000
  }
  const n = Date.parse(String(ts || ''))
  return isNaN(n) ? 0 : n
}

const formatVersionTime = (ts?: number | string): string => {
  if (ts === undefined || ts === null || ts === '') return '-'
  const d = dayjs(toMs(ts))
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : String(ts)
}

const AgentPublishDialog: React.FC<AgentPublishDialogProps> = ({
  open,
  agentId,
  agentName,
  port ,
  hasRuntimeDeployment,
  onClose,
  onPublished,
}) => {
  const { t } = useScopedTranslation('agents.publishDialog')
  const [versions, setVersions] = useState<AgentVersionInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<string>('')
  const [submitVersionDialogOpen, setSubmitVersionDialogOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const deployRuntimeMutation = useDeployRuntime()
  const removeRuntimeMutation = useRemoveRuntime()

  useEffect(() => {
    if (!open || !agentId) return
    setError(null)
    setSelectedVersion('')
    const load = async () => {
      setLoading(true)
      try {
        const req: AgentVersionListRequest = {
          agent_id: agentId,
          space_id: getDefaultSpaceId(),
        }
        const resp: AgentVersionListResponse = await AgentService.getAgentVersionList(req)
        if (resp.code === 200 || resp.code === 0) {
          const sourceVersions = resp.data?.versions || []
          const draftInResponse = sourceVersions.filter((v: AgentVersionInfo) => String(v.agent_version || '').toLowerCase() === 'draft')
          const draft: AgentVersionInfo[] =
            draftInResponse.length > 0
              ? draftInResponse
              : [
                  {
                    agent_version: 'draft',
                  } as AgentVersionInfo,
                ]
          const published = sourceVersions.filter((v: AgentVersionInfo) => {
            const ver = String(v.agent_version || '').toLowerCase()
            return ver !== '' && ver !== 'draft'
          })
          const sortedPublished = [...published].sort((a, b) => toMs(b.create_time) - toMs(a.create_time))
          const merged = [...draft, ...sortedPublished]
          setVersions(merged)
          if (merged.length > 0) {
            const defaultVersion = String(merged[0].agent_version || '')
            const ver =
              defaultVersion.toLowerCase() === 'draft'
                ? 'draft'
                : defaultVersion.startsWith('v')
                  ? defaultVersion
                  : `v${defaultVersion}`
            setSelectedVersion(ver)
          }
        } else {
          setVersions([{ agent_version: 'draft' } as AgentVersionInfo])
          setSelectedVersion('draft')
        }
      } catch (e) {
        setError(t('errors.loadFailed'))
        setVersions([{ agent_version: 'draft' } as AgentVersionInfo])
        setSelectedVersion('draft')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [open, agentId])

  useEffect(() => {
    if (!open) {
      setSubmitVersionDialogOpen(false)
    }
  }, [open])

  const deployWithVersion = async (version: string) => {
    if (!agentId) {
      setError(t('errors.selectVersion'))
      return
    }
    setPublishing(true)
    setError(null)
    try {
      const shouldRemoveBeforeDeploy = hasRuntimeDeployment !== false
      if (shouldRemoveBeforeDeploy) {
        await removeRuntimeMutation.mutateAsync({
          agent_id: agentId,
          space_id: getDefaultSpaceId(),
        })
      }

      const request: RuntimeDeployRequest = {
        agent_id: agentId,
        agent_name: agentName || '',
        agent_version: version,
        space_id: getDefaultSpaceId(),
        ...(port?.trim() ? { port: port.trim() } : {}),
      }
      await deployRuntimeMutation.mutateAsync(request)
      onPublished?.()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.publishFailed'))
    } finally {
      setPublishing(false)
    }
  }

  const handlePublish = async () => {
    if (!agentId || !selectedVersion) {
      setError(t('errors.selectVersion'))
      return
    }
    if (selectedVersion.toLowerCase() === 'draft') {
      setSubmitVersionDialogOpen(true)
      return
    }
    await deployWithVersion(selectedVersion)
  }

  const handleSubmitVersionClose = () => {
    if (publishing) return
    setSubmitVersionDialogOpen(false)
  }

  const handleVersionSubmitted = async (newVersion?: string) => {
    const version = (newVersion || '').trim()
    setSubmitVersionDialogOpen(false)
    if (!version) {
      setError(t('errors.publishFailed'))
      return
    }
    setSelectedVersion(version)
    await deployWithVersion(version)
  }

  const disablePublish = loading || publishing || versions.length === 0 || !selectedVersion

  return (
    <>
      <Dialog
        open={open}
        onClose={publishing ? undefined : onClose}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          className: 'overflow-hidden shadow-xl',
          style: {
            backgroundColor: '#FFFFFF',
            borderRadius: '8px',
            maxHeight: '90vh',
            margin: '5vh auto',
          },
        }}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E7EB]">
          <h2 className="text-[18px] leading-6 font-semibold text-[#111827]">{t('title')}</h2>
          <IconButton size="small" onClick={onClose} disabled={publishing}>
            <X className="w-4 h-4 text-[#6B7280]" />
          </IconButton>
        </div>

        <div className="px-5 py-4">
          <div className="text-[14px] text-[#374151] mb-3">{t('fields.version')}</div>
          {loading ? (
            <div className="flex items-center justify-center h-[240px] text-[#6B7280]">{t('status.loading')}</div>
          ) : versions.length === 0 ? (
            <div className="flex items-center justify-center h-[240px] text-[#6B7280]">{t('status.noVersions')}</div>
          ) : (
            <>
              <div className="h-[240px] overflow-y-auto pr-1">
                <div className="space-y-3">
                  {versions.map((v, i) => {
                    const rawVer = String(v.agent_version || '')
                    const ver = rawVer.toLowerCase() === 'draft' ? 'draft' : rawVer.startsWith('v') ? rawVer : `v${rawVer}`
                    const selected = selectedVersion === ver
                    const isDraft = rawVer.toLowerCase() === 'draft'
                    const desc = String(v.version_description ?? '').trim()
                    const versionLabel = isDraft ? t('labels.draft') : desc ? `${ver}-${desc}` : ver
                    const timeText = isDraft ? '' : formatVersionTime(v.create_time)
                    return (
                      <button
                        key={`${ver}-${i}`}
                        type="button"
                        onClick={() => setSelectedVersion(ver)}
                        disabled={publishing}
                        className={`w-full text-left rounded-[8px] border px-3 py-3 transition-colors ${
                          selected ? 'border-[#4F6EF7] bg-[#F8FAFF]' : 'border-[#EEF2F7] bg-[#FAFBFD] hover:border-[#D4DCE8]'
                        }`}
                      >
                        <div className="flex items-start">
                          <div className="w-6 h-6 rounded bg-white border border-[#E5E7EB] flex items-center justify-center mt-0.5">
                            <img
                              src={isDraft ? publishDialogDraftIcon : publishDialogVersionIcon}
                              alt=""
                              className="w-3.5 h-3.5"
                              aria-hidden="true"
                            />
                          </div>
                          <div className="ml-2.5 min-w-0">
                            <div className="text-[14px] leading-5 font-medium text-[#111827]">{versionLabel}</div>
                            {!isDraft && (
                              <div className="mt-1 text-[12px] leading-4 text-[#9CA3AF]">
                                {t('labels.versionSubmitTime')}&nbsp;&nbsp;{timeText}
                              </div>
                            )}
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
              {error && (
                <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}
            </>
          )}
        </div>

        <div className="px-5 py-3 border-t border-[#E5E7EB] bg-white">
          <div className="flex justify-end gap-3">
            <Button
              onClick={onClose}
              disabled={publishing}
              variant="outlined"
              sx={{
                minWidth: 84,
                height: 32,
                borderColor: '#D1D5DB',
                color: '#4B5563',
                backgroundColor: '#FFFFFF',
                '&:hover': {
                  borderColor: '#9CA3AF',
                  backgroundColor: '#F9FAFB',
                },
              }}
            >
              {t('buttons.cancel')}
            </Button>
            <Button
              onClick={handlePublish}
              disabled={disablePublish}
              variant="contained"
              className="btn-primary"
              sx={{ minWidth: 96, height: 32 }}
            >
              {publishing ? t('status.publishing') : t('buttons.confirm')}
            </Button>
          </div>
        </div>
      </Dialog>

      <AgentSubmitVersionDialog
        open={submitVersionDialogOpen}
        agentId={agentId}
        onClose={handleSubmitVersionClose}
        onVersionSubmitted={handleVersionSubmitted}
      />
    </>
  )
}

export default AgentPublishDialog
