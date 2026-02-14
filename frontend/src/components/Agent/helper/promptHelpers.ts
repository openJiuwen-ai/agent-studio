import { PromptService } from '@test-agentstudio/api-client'

export type VersionOption = {
  id: string
  version: string
  committed_at?: number
  is_default?: boolean
}

// 将接口返回的 commit 列表格式化为前端使用的选项，并按时间倒序
export function formatVersionListOptions(promptId: string, commitInfos: any[]): VersionOption[] {
  const formatted = (commitInfos || [])
    .map((c: any) => ({
      id: c.id || `${promptId}_${c.version}`,
      version: c.version,
      committed_at: c.committed_at ? c.committed_at * 1000 : Date.now(),
      is_default: c.is_default || false,
    }))
    .sort((a: any, b: any) => (b.committed_at || 0) - (a.committed_at || 0))
  return formatted
}

// 若当前版本不在列表（如 draft），则加入以保证选择值可见
export function mergeCurrentVersionOption(options: VersionOption[], promptId: string, currentVersion?: string): VersionOption[] {
  if (!currentVersion) return options
  const exists = options.some(v => v.version === currentVersion)
  return exists ? options : [{ id: `${promptId}_current`, version: currentVersion }, ...options]
}

// 拉取指定提示词的版本选项（已格式化）
export async function getVersionOptions(promptId: string, workspaceId: string): Promise<VersionOption[]> {
  const commitResult = await PromptService.getVersionList(promptId, workspaceId, { page_size: 100 })
  return formatVersionListOptions(promptId, commitResult.prompt_commit_infos || [])
}

// 从详情结果中提取文本内容（根据版本选择 commit 或 draft）
export function extractPromptTextFromDetail(result: any, version?: string): string {
  const useDraft = version === 'draft'
  const commitMsg = result?.prompt?.[0]?.prompt_commit?.detail?.prompt_template?.messages?.[0]?.content
  const draftMsg = result?.prompt?.[0]?.prompt_draft?.detail?.prompt_template?.messages?.[0]?.content
  const content = useDraft ? draftMsg : commitMsg
  const text = Array.isArray(content) ? content.join('\n') : typeof content === 'string' ? content : ''
  return text || ''
}

// 拉取详情，可配置是否包含 draft（当 version==='draft' 时才会拉取）
export async function getPromptDetailByVersion(
  promptId: string,
  version: string,
  workspaceId: string,
  options?: { includeDraft?: boolean; withDefaultConfig?: boolean },
): Promise<any> {
  const includeDraft = options?.includeDraft ?? true
  const withDefaultConfig = options?.withDefaultConfig ?? false
  const withCommit = version !== 'draft'
  const withDraft = includeDraft && version === 'draft'
  const req: any = {
    withCommit,
    withDraft,
    withDefaultConfig,
    workspaceId,
  }
  if (withCommit) req.commitVersion = version
  const result = await PromptService.getPromptDetail(promptId, req)
  return result
}

// 便捷函数：直接获取文本内容
export async function fetchPromptText(
  promptId: string,
  version: string,
  workspaceId: string,
  options?: { includeDraft?: boolean; withDefaultConfig?: boolean },
): Promise<string> {
  const result = await getPromptDetailByVersion(promptId, version, workspaceId, options)
  return extractPromptTextFromDetail(result, version)
}

// 比较两个语义化版本号，返回 1 / -1 / 0
export function compareVersions(a?: string, b?: string): number {
  const pa = (a || '').split('.').map(n => parseInt(n, 10) || 0)
  const pb = (b || '').split('.').map(n => parseInt(n, 10) || 0)
  const len = Math.max(pa.length, pb.length)
  for (let i = 0; i < len; i++) {
    const va = pa[i] || 0
    const vb = pb[i] || 0
    if (va > vb) return 1
    if (va < vb) return -1
  }
  return 0
}

// 将版本号 +1（仅 patch 位），无效输入时使用 defaultVersion 作为基线
export function incrementVersion(v?: string, defaultVersion = '1.0.0'): string {
  const base = v && /^\d+\.\d+\.\d+$/.test(v) ? v : defaultVersion
  const [maj, min, patch] = base.split('.').map(n => parseInt(n, 10))
  return `${maj}.${min}.${(patch || 0) + 1}`
}

// —— 输入校验：Key、名称 ——
export function isPromptKeyValid(key: string): boolean {
  const trimmed = key.trim()
  return !!trimmed && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(trimmed)
}

export function isPromptNameValid(name: string): boolean {
  return !!name.trim()
}

// —— 输入校验：版本 ——
export function isVersionFormatValid(v: string): boolean {
  return /^\d+\.\d+\.\d+$/.test(v.trim())
}

export function isVersionGreaterThan(version: string, latest?: string): boolean {
  if (!isVersionFormatValid(version)) return false
  if (!latest) return true
  return compareVersions(version, latest) > 0
}

// 保存按钮禁用条件：Key/名称合法，版本需为 x.x.x 且大于 latest（若存在）
export function shouldDisableSaveConfirm(key: string, name: string, version: string, latestVersion?: string): boolean {
  return !isPromptKeyValid(key) || !isPromptNameValid(name) || !isVersionFormatValid(version) || !isVersionGreaterThan(version, latestVersion)
}

export function hasPromptKeyError(key: string, name?: string): boolean {
  const kt = (key || '').trim()
  const nt = (name || '').trim()
  return (kt !== '' && !isPromptKeyValid(kt)) || (kt === '' && nt !== '')
}

export function hasPromptNameError(name: string, key?: string): boolean {
  const kt = (key || '').trim()
  const nt = (name || '').trim()
  return !isPromptNameValid(nt) && kt !== ''
}
