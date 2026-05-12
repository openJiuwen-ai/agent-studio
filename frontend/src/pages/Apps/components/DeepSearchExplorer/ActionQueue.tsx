import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDrag, useDrop, DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import {
  Play,
  Pause,
  Clock,
  CheckCircle2,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Trash2,
  GripVertical,
  Pencil,
  Check,
  X,
  ChevronDown,
} from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";
import { AiLoader } from "./ui/ai-loader";

export interface Action {
  id: string;
  type: "query" | "expand" | "validate" | "filter";
  description: string;
  status: "pending" | "running" | "paused" | "completed" | "failed";
  priority: number;
  target?: string;
  estimatedTime?: number;
  /** Final cost in USD (for completed/failed actions). */
  costUsd?: number;
  /** Current cost in USD so far (for running actions). */
  currentCostUsd?: number;
  /** Proposal score from backend (0-1). */
  score?: number;
  /** Depth of the state this action operates on. */
  stateDepth?: number;
  /** ID of the source state. */
  stateId?: number;
  /** Completion timestamp (ISO string) for chronological ordering. */
  completedAt?: string;
  /** True when this action yielded the final answer from the backend. */
  foundAnswer?: boolean;
}

interface ActionQueueProps {
  actions: Action[];
  /** When true and actions is empty, show the "Generating" loader */
  isLoading?: boolean;
  onActionClick?: (action: Action) => void;
  onPause?: (actionId: string) => void;
  onResume?: (actionId: string) => void;
  onUpvote?: (actionId: string) => void;
  onDownvote?: (actionId: string) => void;
  onDelete?: (actionId: string) => void;
  onReorder?: (
    dragIndex: number,
    hoverIndex: number,
    status: Action["status"],
  ) => void;
  onEditAction?: (actionId: string, newDescription: string) => void;
}

export function ActionQueue({
  actions,
  isLoading = false,
  onActionClick,
  onPause,
  onResume,
  onUpvote,
  onDownvote,
  onDelete,
  onReorder,
  onEditAction,
}: ActionQueueProps) {
  const { t } = useTranslation();
  const sortedActions = [...actions].sort(
    (a, b) => b.priority - a.priority,
  );

  const statusGroups = {
    running: sortedActions.filter(
      (a) => a.status === "running",
    ),
    paused: sortedActions.filter((a) => a.status === "paused"),
    pending: sortedActions.filter(
      (a) => a.status === "pending",
    ),
    completed: sortedActions.filter(
      (a) => a.status === "completed",
    ),
    failed: sortedActions.filter((a) => a.status === "failed"),
  };

  const [sectionOpen, setSectionOpen] = useState({
    running: true,
    paused: true,
    pending: true,
    completed: true,
    failed: true,
  });

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="h-full overflow-auto p-4 bg-gray-50 border-l flex flex-col">
        <h2 className="mb-4 text-gray-900 shrink-0">{t("apps.deepSearchExplorer.actionQueue.title", "Action Queue")}</h2>

        {isLoading && actions.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <AiLoader text={t("apps.deepSearchExplorer.actionQueue.generating", "Generating")} size={160} />
          </div>
        ) : (
        <div className="space-y-4">
          {/* Running Actions */}
          {statusGroups.running.length > 0 && (
            <Collapsible
              open={sectionOpen.running}
              onOpenChange={(open) => setSectionOpen((s) => ({ ...s, running: open }))}
            >
              <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-200/80 text-sm text-gray-700">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${sectionOpen.running ? "" : "-rotate-90"}`}
                />
                <Play className="w-4 h-4" />
                {t("apps.deepSearchExplorer.actionQueue.sections.running", "Running")}
                <Badge variant="default" className="bg-blue-600 text-white border-blue-600">
                  {statusGroups.running.length}
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-2 mt-2">
                  {statusGroups.running.map((action, index) => (
                    <DraggableActionCard
                      key={action.id}
                      action={action}
                      index={index}
                      onClick={onActionClick}
                      onPause={onPause}
                      onResume={onResume}
                      onUpvote={onUpvote}
                      onDownvote={onDownvote}
                      onDelete={onDelete}
                      onReorder={onReorder}
                      onEditAction={onEditAction}
                      isDraggable={false}
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Paused Actions */}
          {statusGroups.paused.length > 0 && (
            <Collapsible
              open={sectionOpen.paused}
              onOpenChange={(open) => setSectionOpen((s) => ({ ...s, paused: open }))}
            >
              <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-200/80 text-sm text-gray-700">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${sectionOpen.paused ? "" : "-rotate-90"}`}
                />
                <Pause className="w-4 h-4" />
                {t("apps.deepSearchExplorer.actionQueue.sections.paused", "Paused")}
                <Badge variant="secondary" className="bg-amber-100 text-amber-800 border-amber-300">
                  {statusGroups.paused.length}
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-2 mt-2">
                  {statusGroups.paused.map((action, index) => (
                    <DraggableActionCard
                      key={action.id}
                      action={action}
                      index={index}
                      onClick={onActionClick}
                      onPause={onPause}
                      onResume={onResume}
                      onUpvote={onUpvote}
                      onDownvote={onDownvote}
                      onDelete={onDelete}
                      onReorder={onReorder}
                      onEditAction={onEditAction}
                      isDraggable={false}
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Pending Actions */}
          {statusGroups.pending.length > 0 && (
            <Collapsible
              open={sectionOpen.pending}
              onOpenChange={(open) => setSectionOpen((s) => ({ ...s, pending: open }))}
            >
              <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-200/80 text-sm text-gray-700">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${sectionOpen.pending ? "" : "-rotate-90"}`}
                />
                <Clock className="w-4 h-4" />
                {t("apps.deepSearchExplorer.actionQueue.sections.pending", "Pending")}
                <Badge variant="secondary">
                  {statusGroups.pending.length}
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-2 mt-2">
                  {statusGroups.pending.map((action, index) => (
                    <DraggableActionCard
                      key={action.id}
                      action={action}
                      index={index}
                      onClick={onActionClick}
                      onPause={onPause}
                      onResume={onResume}
                      onUpvote={onUpvote}
                      onDownvote={onDownvote}
                      onDelete={onDelete}
                      onReorder={onReorder}
                      onEditAction={onEditAction}
                      isDraggable={true}
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Completed Actions */}
          {statusGroups.completed.length > 0 && (
            <Collapsible
              open={sectionOpen.completed}
              onOpenChange={(open) => setSectionOpen((s) => ({ ...s, completed: open }))}
            >
              <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-200/80 text-sm text-gray-700">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${sectionOpen.completed ? "" : "-rotate-90"}`}
                />
                <CheckCircle2 className="w-4 h-4" />
                {t("apps.deepSearchExplorer.actionQueue.sections.completed", "Completed")}
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  {statusGroups.completed.length}
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-2 mt-2">
                  {[...statusGroups.completed]
                    .sort((a, b) => (b.completedAt ?? "").localeCompare(a.completedAt ?? ""))
                    .map((action, index) => (
                      <DraggableActionCard
                        key={action.id}
                        action={action}
                        index={index}
                        onClick={onActionClick}
                        onPause={onPause}
                        onResume={onResume}
                        onUpvote={onUpvote}
                        onDownvote={onDownvote}
                        onDelete={onDelete}
                        onReorder={onReorder}
                        onEditAction={onEditAction}
                        isDraggable={false}
                      />
                    ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Failed Actions */}
          {statusGroups.failed.length > 0 && (
            <Collapsible
              open={sectionOpen.failed}
              onOpenChange={(open) => setSectionOpen((s) => ({ ...s, failed: open }))}
            >
              <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-200/80 text-sm text-gray-700">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 transition-transform ${sectionOpen.failed ? "" : "-rotate-90"}`}
                />
                <AlertCircle className="w-4 h-4" />
                {t("apps.deepSearchExplorer.actionQueue.sections.failed", "Failed")}
                <Badge variant="destructive" className="bg-red-600 text-white border-red-600">
                  {statusGroups.failed.length}
                </Badge>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="space-y-2 mt-2">
                  {statusGroups.failed.map((action, index) => (
                    <DraggableActionCard
                      key={action.id}
                      action={action}
                      index={index}
                      onClick={onActionClick}
                      onPause={onPause}
                      onResume={onResume}
                      onUpvote={onUpvote}
                      onDownvote={onDownvote}
                      onDelete={onDelete}
                      onReorder={onReorder}
                      onEditAction={onEditAction}
                      isDraggable={false}
                    />
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
        )}
      </div>
    </DndProvider>
  );
}

interface DraggableActionCardProps {
  action: Action;
  index: number;
  onClick?: (action: Action) => void;
  onPause?: (actionId: string) => void;
  onResume?: (actionId: string) => void;
  onUpvote?: (actionId: string) => void;
  onDownvote?: (actionId: string) => void;
  onDelete?: (actionId: string) => void;
  onReorder?: (
    dragIndex: number,
    hoverIndex: number,
    status: Action["status"],
  ) => void;
  onEditAction?: (actionId: string, newDescription: string) => void;
  isDraggable: boolean;
}

const ItemType = "ACTION_CARD";

function DraggableActionCard({
  action,
  index,
  onClick,
  onPause,
  onResume,
  onUpvote,
  onDownvote,
  onDelete,
  onReorder,
  onEditAction,
  isDraggable,
}: DraggableActionCardProps) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const [draftDescription, setDraftDescription] = useState(action.description);

  const [{ isDragging }, drag] = useDrag({
    type: ItemType,
    item: { id: action.id, index, status: action.status },
    canDrag: isDraggable,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [{ isOver }, drop] = useDrop({
    accept: ItemType,
    canDrop: (item: {
      id: string;
      index: number;
      status: Action["status"];
    }) => {
      return item.status === action.status && isDraggable;
    },
    hover: (item: {
      id: string;
      index: number;
      status: Action["status"];
    }) => {
      if (!ref.current) {
        return;
      }
      const dragIndex = item.index;
      const hoverIndex = index;

      if (dragIndex === hoverIndex) {
        return;
      }

      if (item.status === action.status) {
        onReorder?.(dragIndex, hoverIndex, action.status);
        item.index = hoverIndex;
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver() && monitor.canDrop(),
    }),
  });

  if (isDraggable) {
    drag(drop(ref));
  }

  const statusColors: Record<Action["status"], string> = {
    pending: "bg-gray-100 border-gray-300",
    running: "bg-blue-50 border-blue-300",
    paused: "bg-amber-50 border-amber-400",
    completed: "bg-green-50 border-green-300",
    failed: "bg-red-50 border-red-300",
  };

  const typeColors = {
    query: "bg-blue-100 text-blue-800",
    expand: "bg-purple-100 text-purple-800",
    validate: "bg-green-100 text-green-800",
    filter: "bg-orange-100 text-orange-800",
  };

  const showVoteAndDelete =
    action.status !== "completed" && action.status !== "failed";

  return (
    <div ref={ref} style={{ opacity: isDragging ? 0.5 : 1 }}>
      <Card
        className={`
          p-3 transition-all
          ${statusColors[action.status]}
          ${isOver ? "ring-2 ring-blue-500 shadow-lg" : ""}
          ${isDraggable ? "cursor-move" : ""}
        `}
      >
        <div className="flex items-start gap-2">
          {/* Drag Handle */}
          {isDraggable && (
            <div className="flex-shrink-0 text-gray-400 mt-1">
              <GripVertical className="w-4 h-4" />
            </div>
          )}

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-2 flex-wrap">
              <Badge variant="outline" className="text-xs">
                P{action.priority}
              </Badge>

              <Badge className={typeColors[action.type]}>
                {action.type === "query"
                  ? t("apps.deepSearchExplorer.actionQueue.type.query", "Query")
                  : action.type === "expand"
                    ? t("apps.deepSearchExplorer.actionQueue.type.expand", "Expand")
                    : action.type === "validate"
                      ? t("apps.deepSearchExplorer.actionQueue.type.validate", "Validate")
                      : t("apps.deepSearchExplorer.actionQueue.type.filter", "Filter")}
              </Badge>

              {action.foundAnswer && (
                <Badge className="bg-emerald-600 text-white hover:bg-emerald-600 border-0 text-xs shrink-0">
                  {t("apps.deepSearchExplorer.actionQueue.answerBadge", "Answer")}
                </Badge>
              )}

              {showVoteAndDelete && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 hover:bg-green-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpvote?.(action.id);
                    }}
                  >
                    <ThumbsUp className="w-3 h-3 mr-1" />
                    <span className="text-xs">{/* Upvote */}</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 hover:bg-orange-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDownvote?.(action.id);
                    }}
                  >
                    <ThumbsDown className="w-3 h-3 mr-1" />
                    <span className="text-xs">
                      {/* Downvote */}
                    </span>
                  </Button>
                </>
              )}
              {action.status === "running" && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 hover:bg-red-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    onPause?.(action.id);
                  }}
                >
                  <Pause className="w-3 h-3" />
                </Button>
              )}
              {action.status === "paused" && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 hover:bg-green-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    onResume?.(action.id);
                  }}
                >
                  <Play className="w-3 h-3" />
                </Button>
              )}
              {showVoteAndDelete && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2 hover:bg-red-100 ml-auto"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete?.(action.id);
                  }}
                >
                  <Trash2 className="w-3 h-3 mr-1" />
                  <span className="text-xs">{/* Delete */}</span>
                </Button>
              )}
            </div>

            {action.status === "pending" && isEditingDescription ? (
              <div className="space-y-2 mb-1" onClick={(e) => e.stopPropagation()}>
                <Textarea
                  value={draftDescription}
                  onChange={(e) => setDraftDescription(e.target.value)}
                  placeholder={t("apps.deepSearchExplorer.actionQueue.descriptionPlaceholder", "Action description...")}
                  className="min-h-[80px] text-sm resize-y"
                  autoFocus
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 gap-1"
                    onClick={() => {
                      onEditAction?.(action.id, draftDescription.trim());
                      setIsEditingDescription(false);
                    }}
                    disabled={!draftDescription.trim()}
                  >
                    <Check className="w-3 h-3" />
                    {t("apps.deepSearchExplorer.actionQueue.save", "Save")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 gap-1"
                    onClick={() => {
                      setDraftDescription(action.description);
                      setIsEditingDescription(false);
                    }}
                  >
                    <X className="w-3 h-3" />
                    {t("apps.deepSearchExplorer.actionQueue.cancel", "Cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <p
                className="text-sm text-gray-900 mb-1 cursor-pointer hover:text-blue-600"
                onClick={() => onClick?.(action)}
              >
                {action.description}
              </p>
            )}

            {(action.target || action.stateDepth != null) && (
              <p className="text-xs text-gray-600 mb-1">
                {t("apps.deepSearchExplorer.actionQueue.targetLabel", "Target:")}{" "}
                <span className="font-mono">
                  {action.stateDepth != null
                    ? t("apps.deepSearchExplorer.actionQueue.depthLabel", "Depth {{depth}}", { depth: action.stateDepth })
                    : action.target}
                </span>
              </p>
            )}

            {action.status === "pending" && (
              <div className="flex items-center justify-end gap-2 mt-2">
                {action.estimatedTime && (
                  <p className="text-xs text-gray-500 mr-auto">
                    {t("apps.deepSearchExplorer.actionQueue.estimate", "Est. {{seconds}}s", { seconds: action.estimatedTime })}
                  </p>
                )}
                {onEditAction && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 px-2 hover:bg-blue-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDraftDescription(action.description);
                      setIsEditingDescription(true);
                    }}
                    title={t("apps.deepSearchExplorer.actionQueue.editActionProposal", "Edit action proposal")}
                  >
                    <Pencil className="w-3 h-3 mr-1" />
                    <span className="text-xs">{t("apps.deepSearchExplorer.actionQueue.edit", "Edit")}</span>
                  </Button>
                )}
              </div>
            )}

            {action.status === "running" && (
              <>
                {action.currentCostUsd != null && (
                  <p className="text-xs text-blue-700 font-medium mb-1">
                    {t("apps.deepSearchExplorer.actionQueue.currentCost", "Current cost: ${{cost}} USD", { cost: action.currentCostUsd.toFixed(2) })}
                  </p>
                )}
                <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 animate-pulse"
                    style={{ width: "60%" }}
                  />
                </div>
              </>
            )}

            {action.status === "paused" && (
              <>
                {action.currentCostUsd != null && (
                  <p className="text-xs text-amber-700 font-medium mb-1">
                    {t("apps.deepSearchExplorer.actionQueue.costSoFar", "Cost so far: ${{cost}} USD", { cost: action.currentCostUsd.toFixed(2) })}
                  </p>
                )}
                <p className="text-xs text-amber-600 font-medium">{t("apps.deepSearchExplorer.actionQueue.paused", "Paused")}</p>
              </>
            )}

            {(action.status === "completed" || action.status === "failed") &&
              action.costUsd != null && (
                <p className="text-xs text-gray-700 font-medium mt-1">
                  {t("apps.deepSearchExplorer.actionQueue.cost", "Cost: ${{cost}} USD", { cost: action.costUsd.toFixed(2) })}
                </p>
              )}

          </div>
        </div>
      </Card>
    </div>
  );
}
