import React, { useEffect, useState } from 'react'
import { Dialog, Button, Select, MenuItem, FormControl, InputLabel } from '@mui/material'
import { Send } from 'lucide-react'
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

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="sm"
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
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white p-4 sm:p-6">
          <div className="flex items-center">
            <div className="bg-white/20 backdrop-blur-sm p-2 sm:p-3 rounded-xl">
              <Send className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <div className="ml-3 sm:ml-4">
              <h2 className="text-lg sm:text-xl font-bold">{t('title')}</h2>
              <p className="text-indigo-100 text-xs sm:text-sm mt-1">{t('subtitle')}</p>
            </div>
          </div>
        </div>

        <div className="p-4 sm:p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-gray-500">{t('status.loading')}</div>
          ) : versions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">{t('status.noVersions')}</div>
          ) : (
            <>
              <FormControl fullWidth size="small" className="mb-4">
                <InputLabel id="publish-dialog-version-label">{t('fields.version')}</InputLabel>
                <Select
                  labelId="publish-dialog-version-label"
                  value={selectedVersion}
                  label={t('fields.version')}
                  onChange={e => setSelectedVersion(e.target.value)}
                  disabled={publishing}
                >
                  {versions.map((v, i) => {
                    const rawVer = String(v.agent_version || '')
                    const ver = rawVer.toLowerCase() === 'draft' ? 'draft' : rawVer.startsWith('v') ? rawVer : `v${rawVer}`
                    return (
                      <MenuItem key={i} value={ver}>
                        {ver}
                        {v.version_description ? ` - ${v.version_description}` : ''}
                      </MenuItem>
                    )
                  })}
                </Select>
              </FormControl>
              {error && (
                <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}
            </>
          )}
        </div>

        <div className="bg-gray-50 px-4 sm:px-6 py-3 sm:py-4 rounded-b-2xl border-t border-gray-200">
          <div className="flex justify-end gap-3">
            <Button onClick={onClose} disabled={publishing} variant="outlined" className="border-gray-300 text-gray-700">
              {t('buttons.cancel')}
            </Button>
            <Button
              onClick={handlePublish}
              disabled={loading || publishing || versions.length === 0 || !selectedVersion}
              variant="contained"
              className="btn-primary"
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
