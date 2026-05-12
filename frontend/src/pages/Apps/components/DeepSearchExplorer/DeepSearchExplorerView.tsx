import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { EntityPanel, Entity, CandidateEntity, ActionToolCall } from './EntityPanel'
import { ActionQueue, Action } from './ActionQueue'
import { Button } from './ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { RunRoute } from './types'

export interface DeepSearchExplorerViewProps {
  actions: Action[]
  selectedAction?: Action | null
  onActionClick?: (action: Action) => void
  onPause?: (actionId: string) => void
  onResume?: (actionId: string) => void
  onUpvote?: (actionId: string) => void
  onDownvote?: (actionId: string) => void
  onDelete?: (actionId: string) => void
  onReorder?: (dragIndex: number, hoverIndex: number, status: Action['status']) => void
  onEditAction?: (actionId: string, newDescription: string) => void
  actionEntities?: {
    knownEntities: Entity[]
    unknownEntities: Entity[]
    candidateEntities: CandidateEntity[]
  } | null
  actionToolCalls?: ActionToolCall[] | null
  runEntities?: {
    knownEntities: Entity[]
    unknownEntities: Entity[]
  } | null
  currentQuestion?: string
  isRunning?: boolean
  runStatus?: string
  runRoute?: RunRoute
  elapsedSeconds?: number
}

/**
 * DeepSearchExplorerView — Explorer tab content.
 * Renders EntityPanel (center) + ActionQueue (right pane) without the left SearchTree pane.
 */
export function DeepSearchExplorerView({
  actions,
  selectedAction,
  onActionClick,
  onPause,
  onResume,
  onUpvote,
  onDownvote,
  onDelete,
  onReorder,
  onEditAction,
  actionEntities,
  actionToolCalls,
  runEntities,
  currentQuestion,
  isRunning = false,
  runStatus,
  runRoute,
  elapsedSeconds = 0,
}: DeepSearchExplorerViewProps) {
  const { t } = useTranslation()
  const [showActionQueue, setShowActionQueue] = useState(true)

  const emptyEntities = {
    knownEntities: [] as Entity[],
    unknownEntities: [] as Entity[],
    candidateEntities: [] as CandidateEntity[],
  }

  const displayEntities =
    selectedAction != null
      ? (actionEntities ?? emptyEntities)
      : {
          knownEntities: runEntities?.knownEntities ?? [],
          unknownEntities: runEntities?.unknownEntities ?? [],
          candidateEntities: [] as CandidateEntity[],
        }

  const showEntityPanel = !!(currentQuestion || runEntities)
  const elapsedDisplay = `${Math.floor(elapsedSeconds / 60)}m ${elapsedSeconds % 60}s`
  const routeName =
    runRoute === 'simple'
      ? t('apps.deepSearchExplorer.routeSimpleAgent', 'Simple agent')
      : runRoute === 'deepsearch'
        ? t('apps.deepSearchExplorer.routeDeepSearchAgent', 'DeepSearch agent')
        : t('apps.deepSearchExplorer.routeDetecting', 'Detecting...')
  const routeLabel = t('apps.deepSearchExplorer.runSummary.routeLabel', 'Route: {{route}}', { route: routeName })
  const statusLabel = t('apps.deepSearchExplorer.view.statusLabel', 'Status:')
  const runStatusLabel = runStatus
    ? t(`apps.deepSearchExplorer.view.statusValues.${runStatus}`, runStatus)
    : ''

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Center Panel — Entity Panel */}
        <div className="flex-1 overflow-hidden min-w-0">
          {showEntityPanel ? (
            <EntityPanel
              question={currentQuestion ?? ''}
              selectedActionDescription={selectedAction?.description}
              actionToolCalls={actionToolCalls ?? null}
              knownEntities={displayEntities.knownEntities}
              unknownEntities={displayEntities.unknownEntities}
              candidateEntities={displayEntities.candidateEntities}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              {t('apps.deepSearchExplorer.view.emptyState', 'Select an action to view details')}
            </div>
          )}
        </div>

        {/* Right Panel — Action Queue (hideable) */}
        <div className={`flex flex-shrink-0 border-l border-gray-200 bg-gray-50 transition-[width] duration-200 ${showActionQueue ? 'w-96' : 'w-10'}`}>
          {showActionQueue ? (
            <>
              <div className="w-8 flex-shrink-0 flex items-start justify-center pt-4 border-r border-gray-200 bg-white/80">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setShowActionQueue(false)}
                  title={t('apps.deepSearchExplorer.view.hideActionQueue', 'Hide Action Queue')}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
              <div className="flex-1 min-w-0 overflow-hidden">
                <ActionQueue
                  actions={actions}
                  isLoading={isRunning && actions.length === 0}
                  onActionClick={onActionClick}
                  onPause={onPause}
                  onResume={onResume}
                  onUpvote={onUpvote}
                  onDownvote={onDownvote}
                  onDelete={onDelete}
                  onReorder={onReorder}
                  onEditAction={onEditAction}
                />
              </div>
            </>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              className="h-full w-full rounded-none hover:bg-gray-200"
              onClick={() => setShowActionQueue(true)}
              title={t('apps.deepSearchExplorer.view.showActionQueue', 'Show Action Queue')}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Footer status bar */}
      <div className="flex items-center px-6 py-3 border-t bg-gray-50 text-sm text-gray-600">
        <div className="flex gap-6 flex-wrap">
          {runStatus && (
            <span className="flex items-center gap-1.5">
              {statusLabel}{' '}
              <strong className={
                runStatus === 'completed' ? 'text-green-700' :
                runStatus === 'running' ? 'text-blue-700' :
                runStatus === 'failed' ? 'text-red-700' :
                'text-gray-900'
              }>
                {runStatusLabel}
              </strong>
              {runStatus === 'running' && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                </span>
              )}
            </span>
          )}
          <span>{routeLabel}</span>
          <span>
            {t('apps.deepSearchExplorer.view.activeActions', 'Active Actions:')}{' '}
            <strong className="text-gray-900">
              {actions.filter((a) => a.status === 'running').length}
            </strong>
          </span>
          <span>
            {t('apps.deepSearchExplorer.view.pendingActions', 'Pending Actions:')}{' '}
            <strong className="text-gray-900">
              {actions.filter((a) => a.status === 'pending').length}
            </strong>
          </span>
          <span>
            {t('apps.deepSearchExplorer.view.completedActions', 'Completed Actions:')}{' '}
            <strong className="text-gray-900">
              {actions.filter((a) => a.status === 'completed').length}
            </strong>
          </span>
          <span>
            {t('apps.deepSearchExplorer.view.elapsedTimeLabel', 'Elapsed Time:')}{' '}
            <strong className="text-gray-900">{elapsedDisplay}</strong>
          </span>
        </div>
      </div>
    </div>
  )
}

export default DeepSearchExplorerView
