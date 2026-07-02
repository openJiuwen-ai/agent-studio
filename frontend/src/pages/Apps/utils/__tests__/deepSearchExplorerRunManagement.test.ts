import { describe, expect, it, vi } from 'vitest'

import {
  cancelDeepSearchConversationRuns,
  handleDeepSearchExplorerLeave,
  killDeepSearchExplorerRun,
} from '../deepSearchExplorerRunManagement'

describe('deepSearchExplorerRunManagement', () => {
  it('does not cancel runs when switching conversations', async () => {
    const killRun = vi.fn().mockResolvedValue(undefined)

    const cancelledRunIds = await handleDeepSearchExplorerLeave(
      'conversation-switch',
      {
        deepSearchRunIds: new Map([['message-1', 'run-1']]),
        activeDeepSearchRunId: 'run-1',
        killedDeepSearchRunIds: new Set(),
      },
      killRun,
    )

    expect(cancelledRunIds).toEqual([])
    expect(killRun).not.toHaveBeenCalled()
  })

  it('does not cancel runs when starting a new conversation', async () => {
    const killRun = vi.fn().mockResolvedValue(undefined)

    const cancelledRunIds = await handleDeepSearchExplorerLeave(
      'new-conversation',
      {
        deepSearchRunIds: new Map([['message-1', 'run-1']]),
        activeDeepSearchRunId: 'run-1',
        killedDeepSearchRunIds: new Set(),
      },
      killRun,
    )

    expect(cancelledRunIds).toEqual([])
    expect(killRun).not.toHaveBeenCalled()
  })

  it('kills stored deep search runs before conversation deletion', async () => {
    const killRun = vi.fn().mockResolvedValue(undefined)

    const cancelledRunIds = await cancelDeepSearchConversationRuns(
      {
        agentType: 'deepsearch-explorer',
        deepSearchRunIds: {
          'message-1': 'run-1',
          'message-2': 'run-2',
          'message-3': 'run-1',
        },
      },
      killRun,
    )

    expect(cancelledRunIds).toEqual(['run-1', 'run-2'])
    expect(killRun).toHaveBeenCalledTimes(2)
    expect(killRun).toHaveBeenNthCalledWith(1, 'run-1')
    expect(killRun).toHaveBeenNthCalledWith(2, 'run-2')
  })

  it('delegates explicit kill to killRun', async () => {
    const killRun = vi.fn().mockResolvedValue(undefined)

    await killDeepSearchExplorerRun('run-7', killRun)

    expect(killRun).toHaveBeenCalledTimes(1)
    expect(killRun).toHaveBeenCalledWith('run-7')
  })
})
