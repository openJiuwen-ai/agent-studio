import { afterEach, describe, expect, it } from 'vitest'

import { __testUtils } from '../api'

describe('DeepSearchExplorer telemetry parsing', () => {
  afterEach(() => {
    __testUtils.clearRunCache()
  })

  it('assigns tool calls to the correct action_id for parallel messages_updated payloads', () => {
    __testUtils.processTelemetryEvent(
      {
        run_id: 'run-parallel-tools',
        seq: 1,
        event: 'messages_updated',
        payload: {
          messages: [
            {
              action_id: 'action-1',
              tool_calls: [
                {
                  function: {
                    name: 'web_search',
                    arguments: JSON.stringify({ query: 'alpha query' }),
                  },
                },
              ],
            },
            {
              action_execution: {
                action_id: 'action-2',
              },
              tool_calls: [
                {
                  function: {
                    name: 'web_search',
                    arguments: JSON.stringify({ query: 'beta query' }),
                  },
                },
              ],
            },
          ],
        },
      },
      'parallel tool attribution',
    )

    const snapshot = __testUtils.getRunSnapshot('run-parallel-tools')
    const action1Result = snapshot.actionInfoById.get('action-1')?.result as { tool_calls_history?: Array<{ tool: string; query: string }> }
    const action2Result = snapshot.actionInfoById.get('action-2')?.result as { tool_calls_history?: Array<{ tool: string; query: string }> }

    expect(action1Result.tool_calls_history).toEqual([{ tool: 'web_search', query: 'alpha query' }])
    expect(action2Result.tool_calls_history).toEqual([{ tool: 'web_search', query: 'beta query' }])
  })

  it('falls back to the payload action_id when child messages do not carry their own action ids', () => {
    __testUtils.processTelemetryEvent(
      {
        run_id: 'run-payload-action-fallback',
        seq: 1,
        event: 'messages_updated',
        payload: {
          action_id: 'action-root',
          messages: [
            {
              tool_calls: [
                {
                  function: {
                    name: 'web_search',
                    arguments: JSON.stringify({ query: 'gamma query' }),
                  },
                },
              ],
            },
          ],
        },
      },
      'payload action fallback',
    )

    const snapshot = __testUtils.getRunSnapshot('run-payload-action-fallback')
    const actionResult = snapshot.actionInfoById.get('action-root')?.result as { tool_calls_history?: Array<{ tool: string; query: string }> }

    expect(actionResult.tool_calls_history).toEqual([{ tool: 'web_search', query: 'gamma query' }])
  })

  it('keeps action_pool_snapshot counts accurate for simultaneous pending/running/completed actions', () => {
    __testUtils.processTelemetryEvent(
      {
        run_id: 'run-action-pool',
        seq: 1,
        event: 'action_pool_snapshot',
        payload: {
          snapshot: {
            pending: [
              { id: 'pending-1', direction: 'Pending 1', score: 0.1 },
              { id: 'pending-2', direction: 'Pending 2', score: 0.2 },
            ],
            running: [
              { id: 'running-1', direction: 'Running 1', score: 0.9 },
            ],
            completed: [
              { id: 'completed-1', direction: 'Completed 1', score: 0.7 },
              { id: 'completed-2', direction: 'Completed 2', score: 0.6 },
            ],
          },
        },
      },
      'snapshot counts',
    )

    const snapshot = __testUtils.getRunSnapshot('run-action-pool')

    expect(snapshot.actions.filter(action => action.type === 'pending')).toHaveLength(2)
    expect(snapshot.actions.filter(action => action.type === 'running')).toHaveLength(1)
    expect(snapshot.actions.filter(action => action.type === 'completed')).toHaveLength(2)
  })
})
