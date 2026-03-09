import { useEffect, useMemo, useState } from 'react'
import { WorkflowService } from '@test-agentstudio/api-client'
import { WorkflowDetail, WorkflowSelectDetail } from '@/types/agentTypes'

export type VersionsMap = Record<string, { published: { version: string; create_time: number }[]; latestPublished: string | null }>
export type LoadingMap = Record<string, boolean>

export const useWorkflowVersions = (workflows: WorkflowDetail[], spaceId: string, enabled: boolean = true) => {
  const [versionsMap, setVersionsMap] = useState<VersionsMap>({})
  const [loadingMap, setLoadingMap] = useState<LoadingMap>({})
  const idsKey = useMemo(
    () =>
      workflows
        .map(w => w.workflow_id)
        .sort()
        .join(','),
    [workflows],
  )

  const loadVersions = async (force: boolean) => {
    if (!spaceId) return
    const toFetch = force ? workflows : workflows.filter(w => !versionsMap[w.workflow_id])
    if (toFetch.length === 0) return

    // 只设置要获取的工作流的 loading 状态
    setLoadingMap(prev => {
      const next = { ...prev }
      toFetch.forEach(w => {
        next[w.workflow_id] = true
      })
      return next
    })

    const entries = await Promise.all(
      toFetch.map(async w => {
        try {
          const res = await WorkflowService.getWorkflowVersionList({ workflow_id: w.workflow_id, space_id: spaceId })
          const list = Array.isArray(res.data?.versions) ? res.data.versions.map(v => ({ version: v.workflow_version, create_time: v.create_time })) : []
          const latest = list.length > 0 ? [...list].sort((a, b) => b.create_time - a.create_time)[0].version : null
          return [w.workflow_id, { published: list, latestPublished: latest }] as const
        } catch {
          return [w.workflow_id, { published: [], latestPublished: null }] as const
        }
      }),
    )
    const map = Object.fromEntries(entries)
    setVersionsMap(prev => ({ ...prev, ...map }))

    // 清除已完成的 loading 状态
    setLoadingMap(prev => {
      const next = { ...prev }
      toFetch.forEach(w => {
        delete next[w.workflow_id]
      })
      return next
    })
  }

  useEffect(() => {
    if (enabled && spaceId) {
      loadVersions(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, spaceId, enabled])

  const refresh = async () => {
    await loadVersions(true)
  }

  return { versionsMap, loadingMap, refresh }
}

export const resolveVersion = (w: WorkflowDetail, versionsMap: VersionsMap, prevSelected: Record<string, string>) => {
  if (w.workflow_version !== undefined && w.workflow_version !== null) {
    return w.workflow_version === '' ? 'draft' : w.workflow_version
  }
  const latest = versionsMap[w.workflow_id]?.latestPublished
  if (latest) return latest
  return prevSelected[w.workflow_id] ?? 'draft'
}

export const useSelectedVersions = (workflows: WorkflowDetail[], versionsMap: VersionsMap) => {
  const [selected, setSelected] = useState<Record<string, string>>({})
  useEffect(() => {
    setSelected(prev => {
      const next = { ...prev }
      workflows.forEach(w => {
        next[w.workflow_id] = resolveVersion(w, versionsMap, prev)
      })
      return next
    })
  }, [workflows, versionsMap])
  return selected
}

export const mapWorkflow = (workflow: any): WorkflowSelectDetail => ({
  id: workflow.workflow_id,
  workflow_id: workflow.workflow_id,
  name: workflow.name,
  description: workflow.desc,
  desc: workflow.desc,
  icon: workflow.icon_uri || '📋',
  icon_uri: workflow.icon_uri,
  version: workflow.workflow_version || '',
  create_time: workflow.create_time,
  space_id: workflow.space_id,
  tags: workflow.tags || [],
})

export const fetchLatestVersionForWorkflow = async (workflow_id: string, spaceId: string) => {
  try {
    const res = await WorkflowService.getWorkflowVersionList({ workflow_id, space_id: spaceId })
    const list = Array.isArray(res.data?.versions) ? res.data.versions : []
    const latest = list.length > 0 ? [...list].sort((a, b) => b.create_time - a.create_time)[0].workflow_version : 'draft'
    return latest
  } catch {
    return 'draft'
  }
}

export const buildDetails = async (existing: WorkflowDetail[], selectedObjs: WorkflowSelectDetail[], spaceId: string): Promise<WorkflowDetail[]> => {
  const map = new Map<string, WorkflowDetail>(existing.map(e => [e.workflow_id, e]))
  const toAdd = selectedObjs.filter(w => !map.has(w.workflow_id))
  const added = await Promise.all(
    toAdd.map(async w => ({
      description: w.description,
      workflow_id: w.workflow_id,
      workflow_name: w.name,
      workflow_version: await fetchLatestVersionForWorkflow(w.workflow_id, spaceId),
    })),
  )
  return [...existing, ...added]
}
