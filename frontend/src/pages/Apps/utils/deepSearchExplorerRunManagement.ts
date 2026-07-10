export type DeepSearchExplorerLeaveIntent =
  | 'agent-deselect'
  | 'agent-switch'
  | 'close-panel'
  | 'conversation-delete'
  | 'conversation-switch'
  | 'new-conversation'

export interface DeepSearchExplorerLocalRunState {
  deepSearchRunIds: Map<string, string>
  activeDeepSearchRunId: string | null
  killedDeepSearchRunIds: Set<string>
}

type KillRunFn = (runId: string) => Promise<void>

export function shouldCancelDeepSearchExplorerRuns(intent: DeepSearchExplorerLeaveIntent): boolean {
  return intent === 'conversation-delete'
}

export function collectLiveDeepSearchExplorerRunIds({
  deepSearchRunIds,
  activeDeepSearchRunId,
  killedDeepSearchRunIds,
}: DeepSearchExplorerLocalRunState): string[] {
  return Array.from(new Set([
    ...deepSearchRunIds.values(),
    ...(activeDeepSearchRunId ? [activeDeepSearchRunId] : []),
  ])).filter(runId => !killedDeepSearchRunIds.has(runId))
}

export function getDeepSearchRunIdsFromConversationConfig(config: unknown): string[] {
  if (!config || typeof config !== 'object') {
    return []
  }

  const record = config as Record<string, unknown>
  if (record.agentType !== 'deepsearch-explorer') {
    return []
  }

  const rawRunIds = record.deepSearchRunIds
  if (!rawRunIds || typeof rawRunIds !== 'object' || Array.isArray(rawRunIds)) {
    return []
  }

  return Array.from(
    new Set(
      Object.values(rawRunIds).filter((value): value is string => typeof value === 'string' && value.trim().length > 0),
    ),
  )
}

export async function handleDeepSearchExplorerLeave(
  intent: DeepSearchExplorerLeaveIntent,
  state: DeepSearchExplorerLocalRunState,
  killRun: KillRunFn,
): Promise<string[]> {
  if (!shouldCancelDeepSearchExplorerRuns(intent)) {
    return []
  }

  const runIds = collectLiveDeepSearchExplorerRunIds(state)
  if (runIds.length === 0) {
    return []
  }

  await Promise.allSettled(runIds.map(runId => killRun(runId)))
  return runIds
}

export async function cancelDeepSearchConversationRuns(
  config: unknown,
  killRun: KillRunFn,
): Promise<string[]> {
  const runIds = getDeepSearchRunIdsFromConversationConfig(config)
  if (runIds.length === 0) {
    return []
  }

  await Promise.allSettled(runIds.map(runId => killRun(runId)))
  return runIds
}

export async function killDeepSearchExplorerRun(runId: string, killRun: KillRunFn): Promise<void> {
  await killRun(runId)
}
