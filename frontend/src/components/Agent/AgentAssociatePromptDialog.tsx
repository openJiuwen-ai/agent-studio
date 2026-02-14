import React, { useEffect, useMemo, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  CircularProgress,
  IconButton,
  Paper,
  Alert,
  MenuItem,
  InputAdornment,
} from '@mui/material'
import { X, Plus, Search } from 'lucide-react'
import { PromptService, type Prompt, RelatedMemberService, MemberType, type RelatedMemberInfo } from '@test-agentstudio/api-client'
import { getVersionOptions, getPromptDetailByVersion, extractPromptTextFromDetail, type VersionOption } from './helper/promptHelpers'
import { useAuthStore } from '@/stores/useAuthStore'
import { ENV_CONFIG } from '@/config/environment'
import { getDefaultSpaceId } from '../../utils/spaceUtils'
import { useScopedTranslation } from '@/i18n'

interface AgentInfo {
  agentId?: string
  agentName?: string
  agentVersion?: string
}

interface AgentAssociatePromptDialogProps {
  open: boolean
  onClose: () => void
  onReplace: (_text: string) => void
  onInsert: (_text: string) => void
  workspaceId?: string
  agentInfo?: AgentInfo // 可选：用于历史关联查询与注册（智能体场景）
  relatedMemberInfo?: RelatedMemberInfo // 可选：直接传入关联成员信息（工作流场景，优先级高于 agentInfo）
  onRelationUpdated?: (_info: { promptId: string; promptName: string; promptVersion: string; promptContent: string }) => void
}

const AgentAssociatePromptDialog: React.FC<AgentAssociatePromptDialogProps> = ({
  open,
  onClose,
  onInsert,
  workspaceId: workspaceIdProp,
  agentInfo,
  relatedMemberInfo,
  onRelationUpdated,
}) => {
  const { user } = useAuthStore()
  const workspaceId = useMemo(() => workspaceIdProp || user?.spaceId || getDefaultSpaceId() || ENV_CONFIG.DEFAULT_SPACE_ID, [workspaceIdProp, user])
  const { t } = useScopedTranslation('agents.agentEditor.systemPrompt.agentAssociatePromptDialog')

  // 推荐模板列表
  const [promptTemplateSearch, setPromptTemplateSearch] = useState('')
  const [promptTemplates, setPromptTemplates] = useState<Prompt[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [templatesError, setTemplatesError] = useState<string | null>(null)

  // 选择与版本
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [versionLoading, setVersionLoading] = useState(false)
  const [commitsList, setCommitsList] = useState<VersionOption[]>([])
  const [dialogSelectedVersionId, setDialogSelectedVersionId] = useState('')

  // 详情预览
  const [promptDetail, setPromptDetail] = useState<unknown>(null)
  const [promptDetailLoading, setPromptDetailLoading] = useState(false)
  // 替换过程轻量加载态
  const [replacing, setReplacing] = useState(false)

  // ————— 数据加载 —————
  const loadRecommendedPrompts = async () => {
    try {
      setTemplatesLoading(true)
      setTemplatesError(null)
      const res = await PromptService.getPrompts({ page: 1, pageSize: 100, workspaceId, key_word: promptTemplateSearch || undefined })
      const list = res.prompts || []
      setPromptTemplates(list)
      // 每次打开默认选中查询列表中的第一项并预览其最新版本（不依赖旧状态，以避免关闭后再次打开不触发）
      if (list.length > 0) {
        const firstId = String(list[0].id)
        setSelectedTemplateId(firstId)
        await loadVersionList(firstId)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('loadFailed')
      setTemplatesError(errorMessage)
      setPromptTemplates([])
    } finally {
      setTemplatesLoading(false)
    }
  }

  // ————— 行为 —————
  const handleTemplateSelectFromRecommended = (id: string) => {
    const nextId = String(id)
    // 固定选中：不支持取消选中同一项
    if (String(selectedTemplateId) !== nextId) {
      setSelectedTemplateId(nextId)
      loadVersionList(nextId)
    } else {
      // 再次点击同一项保持选中（可按需避免重复请求）
      setSelectedTemplateId(nextId)
    }
  }

  const loadVersionList = async (tplId?: string, preferVersion?: string) => {
    const targetId = tplId || selectedTemplateId
    if (!targetId) return
    setVersionLoading(true)
    try {
      const formatted = await getVersionOptions(targetId, workspaceId)
      setCommitsList(formatted)

      // 根据 preferVersion 优先选中对应版本，否则选择最新
      let selectedVersion = formatted[0]
      if (preferVersion) {
        const matched = formatted.find(v => v.version === preferVersion)
        if (matched) selectedVersion = matched
      }

      setDialogSelectedVersionId(selectedVersion ? selectedVersion.id : '')
      if (selectedVersion?.version) {
        await previewByVersion(targetId, selectedVersion.version)
      } else {
        setPromptDetail(null)
      }
    } catch (e) {
      setCommitsList([])
      setDialogSelectedVersionId('')
      setPromptDetail(null)
    } finally {
      setVersionLoading(false)
    }
  }

  const previewByVersion = async (promptId?: string, commitVersion?: string) => {
    const pid = promptId || selectedTemplateId
    if (!pid || !commitVersion) return
    setPromptDetailLoading(true)
    try {
      const result = await getPromptDetailByVersion(pid, commitVersion, workspaceId, { includeDraft: false, withDefaultConfig: false })
      setPromptDetail(result)
    } catch (err) {
      // 获取提示词详情失败，静默处理
      console.warn('Failed to get prompt detail by version:', err)
    } finally {
      setPromptDetailLoading(false)
    }
  }

  const extractPreviewContent = (): string => {
    return extractPromptTextFromDetail(promptDetail, commitsList.find(v => v.id === dialogSelectedVersionId)?.version)
  }

  const handleVersionChange = async (versionId: string) => {
    setDialogSelectedVersionId(versionId)
    const selected = commitsList.find(v => v.id === versionId)
    await previewByVersion(selectedTemplateId, selected?.version)
  }

  const handleReplace = async () => {
    const content = extractPreviewContent()
    setReplacing(true)

    // 仅在替换时进行关联注册与活跃列表查询
    try {
      // 优先使用传入的 relatedMemberInfo，否则从 agentInfo 构造（向后兼容）
      const finalRelatedMemberInfo: RelatedMemberInfo | null =
        relatedMemberInfo ||
        (agentInfo?.agentId
          ? {
              id: agentInfo.agentId,
              version: agentInfo.agentVersion || 'draft',
              name: agentInfo.agentName || '',
              type: MemberType.AGENT,
            }
          : null)

      if (finalRelatedMemberInfo && selectedTemplateId && dialogSelectedVersionId) {
        const selected = commitsList.find(v => v.id === dialogSelectedVersionId)
        const promptVersion = selected?.version || ENV_CONFIG.DEFAULT_PROMPT_VERSION
        const promptInfo: RelatedMemberInfo = {
          id: String(selectedTemplateId),
          version: promptVersion,
          name: promptTemplates.find(t => t.id === selectedTemplateId)?.name || '',
          type: MemberType.PROMPT,
        }
        await RelatedMemberService.registerPromptRelation(workspaceId, promptInfo, finalRelatedMemberInfo)
        try {
          await RelatedMemberService.getPromptRelations(workspaceId, finalRelatedMemberInfo, true)
        } catch (err) {
          // 获取活跃列表失败不阻断主流程
        }
        // 通知父组件立刻更新关联显示与内容
        onRelationUpdated?.({
          promptId: String(selectedTemplateId),
          promptName: promptTemplates.find(t => t.id === selectedTemplateId)?.name || '',
          promptVersion,
          promptContent: content,
        })
      }
    } catch (e) {
      // 不阻断流程
    } finally {
      setReplacing(false)
    }

    // 关闭并重置（成功或失败均关闭，最小化改动）
    onClose()
    setSelectedTemplateId('')
    setDialogSelectedVersionId('')
    setPromptDetail(null)
  }

  const handleInsertAction = async () => {
    const content = extractPreviewContent()
    if (content) {
      onInsert(content)
    }
    // 插入不进行关联注册
    onClose()
    setSelectedTemplateId('')
    setDialogSelectedVersionId('')
    setPromptDetail(null)
  }

  // ————— 生命周期 —————
  useEffect(() => {
    if (open) {
      setSelectedTemplateId('')
      setDialogSelectedVersionId('')
      setPromptDetail(null)
      // 仅加载推荐列表并默认选中第一项
      loadRecommendedPrompts()
    }
  }, [open])

  // ————— 渲染 —————
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth PaperProps={{ sx: { height: '70vh' } }}>
      <>
        <DialogTitle className="font-bold text-lg bg-gradient-to-r from-blue-50 to-indigo-50 py-4 flex items-center justify-between">
          {t('title')}
          <IconButton onClick={onClose} size="small" className="text-gray-500 hover:text-gray-700 hover:bg-gray-100">
            <X size={20} />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ overflowY: 'auto', maxHeight: 'calc(70vh - 112px)' }}>
          <div className="flex items-center gap-2 mb-3 small">
            <TextField
              placeholder={t('searchPlaceholder')}
              size="small"
              value={promptTemplateSearch}
              onChange={e => setPromptTemplateSearch(e.target.value)}
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter') loadRecommendedPrompts()
              }}
              className="w-64"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton aria-label={t('searchPlaceholder')} size="small" onClick={() => loadRecommendedPrompts()}>
                      <Search size={16} />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="outlined"
              startIcon={<Plus className="w-4 h-4" />}
              sx={{ height: 40, py: 0, display: 'inline-flex', alignItems: 'center', lineHeight: 1, '& .MuiButton-startIcon': { alignItems: 'center' } }}
              onClick={() => window.open('/dashboard/prompts', '_blank')}
            >
              {t('createPrompt')}
            </Button>
            <TextField
              select
              label={t('versionLabel')}
              size="small"
              value={dialogSelectedVersionId}
              onChange={e => handleVersionChange(String(e.target.value))}
              disabled={!selectedTemplateId || versionLoading || commitsList.length === 0}
              className="w-48"
              style={{ marginLeft: 'auto' }}
            >
              {commitsList.map(v => (
                <MenuItem key={v.id} value={v.id}>
                  {v.version || '1.0.0'}
                </MenuItem>
              ))}
            </TextField>
          </div>
          <div className="grid grid-cols-12 gap-4 h-[calc(100%-52px)]">
            <div className="col-span-4">
              <Paper elevation={0} className="overflow-hidden">
                <div className="max-h-[360px] overflow-y-auto">
                  {templatesLoading ? (
                    <div className="flex justify-center items-center h-40">
                      <CircularProgress />
                    </div>
                  ) : templatesError ? (
                    <Alert severity="error" className="m-3">
                      {templatesError}
                    </Alert>
                  ) : promptTemplates.length === 0 ? (
                    <Alert severity="info" className="m-3">
                      {t('noTemplates')}
                    </Alert>
                  ) : (
                    promptTemplates.map(template => (
                      <React.Fragment key={template.id}>
                        <div
                          className={`w-full text-left px-3 py-2 block rounded-md hover:cursor-pointer ${String(selectedTemplateId) === String(template.id) ? 'bg-blue-50' : 'hover:bg-gray-50 hover:ring-gray-200'}`}
                          onClick={() => handleTemplateSelectFromRecommended(String(template.id))}
                        >
                          <div className="font-medium text-gray-900 truncate h-8">{template.name}</div>
                          <div className={`text-xs truncate h-4 ${template.description ? 'text-gray-600' : 'text-gray-400'}`}>
                            {template.description || t('noDescription')}
                          </div>
                        </div>
                        <div className="border-b border-gray-200"></div>
                      </React.Fragment>
                    ))
                  )}
                </div>
              </Paper>
            </div>

            <div className="col-span-8">
              <Paper elevation={0} className="h-full border border-gray-200 rounded-lg overflow-hidden">
                {promptDetailLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <CircularProgress size={24} />
                  </div>
                ) : (
                  <div className="p-4 h-full">
                    <Paper elevation={0} className="bg-gray-50">
                      <div className="text-sm max-h-[440px] overflow-y-auto">{renderPreviewContent(extractPreviewContent(), !!selectedTemplateId, t)}</div>
                    </Paper>
                  </div>
                )}
              </Paper>
            </div>
          </div>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={handleInsertAction} disabled={!extractPreviewContent() || replacing}>
            {t('insert')}
          </Button>
          <Button
            variant="contained"
            onClick={handleReplace}
            disabled={!extractPreviewContent() || replacing}
            className="btn-primary"
            startIcon={replacing ? <CircularProgress size={16} /> : undefined}
          >
            {replacing ? t('replacing') : t('replaceSystemPrompt')}
          </Button>
        </DialogActions>
      </>
    </Dialog>
  )
}

export default AgentAssociatePromptDialog

// 预览内容渲染：基础高亮（标题与标签）
const renderPreviewContent = (text: string, hasSelection: boolean, t: (key: string) => string) => {
  if (!text) return <span>{hasSelection ? t('noContentForVersion') : t('selectPrompt')}</span>
  const lines = text.split(/\r?\n/)
  const headingRegs = [/^##+\s*/, /^角色[：:]/, /^目标[：:]/, /^工作流[：:]/, /^输出格式[：:]/, /^限制[：:]/]
  return (
    <div className="space-y-1">
      {lines.map((line: string, i: number) => {
        const isHeading = headingRegs.some(r => r.test(line))
        const parts: React.ReactNode[] = []
        const lastIndex = 0
        // for (const match of line.matchAll(tagReg)) {
        //   const idx = match.index || 0
        //   const word = match[0]
        //   if (idx > lastIndex) parts.push(<span key={`t-${i}-${lastIndex}`}>{line.slice(lastIndex, idx)}</span>)
        //   parts.push(
        //     <span key={`tag-${i}-${idx}`} className="inline-block px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 text-xs">
        //       {word}
        //     </span>,
        //   )
        //   lastIndex = idx + word.length
        // }
        if (lastIndex < line.length) parts.push(<span key={`t-end-${i}`}>{line.slice(lastIndex)}</span>)
        return (
          <div key={i} className={isHeading ? 'font-semibold text-gray-900' : 'text-gray-800'}>
            {parts.length ? parts : line || '\u00A0'}
          </div>
        )
      })}
    </div>
  )
}
