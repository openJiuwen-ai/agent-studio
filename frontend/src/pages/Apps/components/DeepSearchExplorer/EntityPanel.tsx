import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from './ui/badge';
import { Check, HelpCircle, Search, Lightbulb, ChevronDown, ListTodo, Wrench } from 'lucide-react';
import { Card } from './ui/card';

import { HoverCard, HoverCardContent, HoverCardTrigger } from './ui/hover-card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';

export interface HypothesisEvidence {
  url: string;
  snippet: string;
}

export interface Entity {
  name: string;
  value?: string;
  type?: string;
  /** When set on an unknown entity, display as "Hypothesis" with this value and distinct styling. */
  hypothesisValue?: string;
  /** Example value assumptions for unknown entities (shown with distinct styling). */
  assumedValues?: string[];
  /** Evidences supporting this hypothesis (URL + text snippet). Shown on hover. */
  evidences?: HypothesisEvidence[];
  /** True if this unknown entity is the one needed for the final answer (target answer). */
  targetAnswer?: boolean;
  /** True when this known row comes from result.new_states (action hypothesis). */
  fromNewState?: boolean;
  /** question_clues from state; shown on hover (known + unknown). */
  discoveredClues?: string[];
}

export interface CandidateEntity {
  name: string;
  candidates: Array<{ value: string; confidence: number }>;
}

export interface ActionToolCall {
  tool: string;
  query: string;
}

interface EntityPanelProps {
  question: string;
  selectedActionDescription?: string | null;
  actionToolCalls?: ActionToolCall[] | null;
  knownEntities: Entity[];
  unknownEntities: Entity[];
  candidateEntities: CandidateEntity[];
}

export function EntityPanel({
  question,
  selectedActionDescription,
  actionToolCalls,
  knownEntities,
  unknownEntities,
  candidateEntities,
}: EntityPanelProps) {
  const { t } = useTranslation();
  const [sectionOpen, setSectionOpen] = useState({
    currentQuestion: true,
    actionProposal: true,
    actionExecution: true,
    actionExecutionToolCalls: true,
    actionExecutionCandidateValues: true,
    unknownEntities: true,
    knownEntities: true,
    // stateGraph removed (no EntityGraph in task space)
  });

  return (
    <>
    <div className="h-full overflow-auto p-6 bg-white">
      {/* Current Question - collapsible */}
      <Collapsible
        open={sectionOpen.currentQuestion}
        onOpenChange={(open) => setSectionOpen((s) => ({ ...s, currentQuestion: open }))}
        className="mb-6"
      >
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-2 text-left hover:bg-gray-100 min-w-0">
          <ChevronDown
            className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${sectionOpen.currentQuestion ? "" : "-rotate-90"}`}
          />
          <h2 className="shrink-0 text-gray-900">{t('apps.deepSearchExplorer.entityPanel.currentQuestion', 'Current Question')}</h2>
          {!sectionOpen.currentQuestion && question && (
            <span className="min-w-0 truncate text-sm text-gray-500">
              {question.replace(/\s+/g, " ").slice(0, 80)}
              {question.replace(/\s+/g, " ").length > 80 ? "…" : ""}
            </span>
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2">
            <Card className="p-4 bg-blue-50 border-blue-200">
              <p className="text-gray-900 whitespace-pre-line">{question}</p>
            </Card>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Action Proposal - collapsible */}
      <Collapsible
        open={sectionOpen.actionProposal}
        onOpenChange={(open) => setSectionOpen((s) => ({ ...s, actionProposal: open }))}
        className="mb-6"
      >
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-1.5 text-left hover:bg-gray-100 min-w-0">
          <ChevronDown
            className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${sectionOpen.actionProposal ? "" : "-rotate-90"}`}
          />
          <Lightbulb className="w-5 h-5 shrink-0 text-amber-600" />
          <h3 className="shrink-0 text-gray-900">{t('apps.deepSearchExplorer.entityPanel.actionProposal', 'Action Proposal')}</h3>
          {!sectionOpen.actionProposal && (
            <span className="min-w-0 truncate text-sm text-gray-500">
              {selectedActionDescription
                ? (selectedActionDescription.length > 80 ? `${selectedActionDescription.slice(0, 80)}…` : selectedActionDescription)
                : t('apps.deepSearchExplorer.entityPanel.selectActionForProposal', 'Select an action from the Action Queue to view its proposal')}
            </span>
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2">
            <Card className="p-4 bg-amber-50 border-amber-200 min-h-[4rem]">
              {selectedActionDescription ? (
                <p className="text-gray-900">{selectedActionDescription}</p>
              ) : (
                <p className="text-gray-500 italic text-sm">
                  {t('apps.deepSearchExplorer.entityPanel.selectActionForProposal', 'Select an action from the Action Queue to view its proposal')}
                </p>
              )}
            </Card>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Action Execution - collapsible */}
      <Collapsible
        open={sectionOpen.actionExecution}
        onOpenChange={(open) => setSectionOpen((s) => ({ ...s, actionExecution: open }))}
        className="mb-6"
      >
        <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-1.5 text-left hover:bg-gray-100 min-w-0">
          <ChevronDown
            className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${sectionOpen.actionExecution ? "" : "-rotate-90"}`}
          />
          <ListTodo className="w-5 h-5 text-slate-600 shrink-0" />
          <h3 className="shrink-0 text-gray-900">{t('apps.deepSearchExplorer.entityPanel.actionExecution', 'Action Execution')}</h3>
          {!sectionOpen.actionExecution && actionToolCalls && actionToolCalls.length > 0 && (
            <span className="min-w-0 truncate text-sm text-gray-500">
              {t('apps.deepSearchExplorer.entityPanel.toolCallsCount', '{{count}} tool call(s)', { count: actionToolCalls.length })}
            </span>
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
        <div className="space-y-5 mt-3">

          {/* Tool Calls - collapsible */}
          <Collapsible
            open={sectionOpen.actionExecutionToolCalls}
            onOpenChange={(open) => setSectionOpen((s) => ({ ...s, actionExecutionToolCalls: open }))}
          >
            <Card className="p-0 bg-slate-50 border-slate-200 min-h-0 overflow-hidden">
              <CollapsibleTrigger className="flex w-full items-center gap-2 px-5 py-4 text-left hover:bg-slate-100/80">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 text-slate-600 transition-transform ${sectionOpen.actionExecutionToolCalls ? "" : "-rotate-90"}`}
                />
                <Wrench className="w-4 h-4 text-slate-600" />
                <span className="text-slate-700 font-medium">{t('apps.deepSearchExplorer.entityPanel.toolCalls', 'Tool Calls')}</span>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="px-5 pb-5 pt-1">
                  {!selectedActionDescription ? (
                    <p className="text-sm text-gray-500 italic">{t('apps.deepSearchExplorer.entityPanel.selectActionForToolCalls', 'Select an action to view tool calls.')}</p>
                  ) : actionToolCalls && actionToolCalls.length > 0 ? (
                    <div className="space-y-3">
                      {actionToolCalls.map((tc, i) => (
                        <div key={i} className="text-sm">
                          <div className="font-medium text-gray-700 mb-1">{tc.tool}</div>
                          <pre className="text-xs text-gray-600 bg-white border border-slate-200 rounded p-2.5 overflow-x-auto whitespace-pre-wrap font-mono max-h-40">
                            {tc.query}
                          </pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic">{t('apps.deepSearchExplorer.entityPanel.noToolCalls', 'No tool calls for this action.')}</p>
                  )}
                </div>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          {/* Candidate Values - collapsible */}
          <Collapsible
            open={sectionOpen.actionExecutionCandidateValues}
            onOpenChange={(open) => setSectionOpen((s) => ({ ...s, actionExecutionCandidateValues: open }))}
          >
            <Card className="p-0 bg-slate-50 border-slate-200 min-h-0 overflow-hidden">
              <CollapsibleTrigger className="flex w-full items-center gap-2 px-5 py-4 text-left hover:bg-slate-100/80">
                <ChevronDown
                  className={`h-4 w-4 shrink-0 text-slate-600 transition-transform ${sectionOpen.actionExecutionCandidateValues ? "" : "-rotate-90"}`}
                />
                <Search className="w-4 h-4 text-slate-600" />
                <span className="text-slate-700 font-medium">{t('apps.deepSearchExplorer.entityPanel.candidateEntities', 'Candidate Entities')}</span>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="px-5 pb-5 pt-1">
                  {candidateEntities.length === 0 ? (
                    <p className="text-sm text-gray-500 italic">{t('apps.deepSearchExplorer.entityPanel.noCandidateValues', 'No candidate values for this state.')}</p>
                  ) : (
                    <div className="space-y-3 max-h-48 overflow-auto">
                      {candidateEntities.map((entity, idx) => (
                        <div key={idx} className="text-sm">
                          <div className="font-medium text-gray-700 mb-1">{entity.name}</div>
                          <div className="space-y-1">
                            {entity.candidates.map((candidate, cidx) => (
                              <div
                                key={cidx}
                                className="flex items-center justify-between gap-2 py-1.5 px-2.5 bg-white rounded border text-xs"
                              >
                                <span className="font-mono text-gray-900 truncate">{candidate.value}</span>
                                <span className="text-gray-600 shrink-0">{(candidate.confidence * 100).toFixed(0)}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Entities & Candidates */}
      <div className="mb-6 min-h-0">
        <div className="min-w-0 overflow-auto space-y-6">
          {/* Unknown Entities - collapsible */}
          <Collapsible
            open={sectionOpen.unknownEntities}
            onOpenChange={(open) => setSectionOpen((s) => ({ ...s, unknownEntities: open }))}
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-1.5 text-left hover:bg-gray-100">
              <ChevronDown
                className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${sectionOpen.unknownEntities ? "" : "-rotate-90"}`}
              />
              <HelpCircle className="w-5 h-5 text-orange-600" />
              <h3 className="text-gray-900">{t('apps.deepSearchExplorer.entityPanel.unknownEntities', 'Unknown Entities')}</h3>
              <Badge variant="secondary">{unknownEntities.length}</Badge>
            </CollapsibleTrigger>
            <CollapsibleContent>
            <div className="space-y-2 mt-2">
              {unknownEntities.length === 0 ? (
                <p className="text-sm text-gray-500 italic">{t('apps.deepSearchExplorer.entityPanel.noUnknownEntities', 'No unknown entities')}</p>
              ) : (
                unknownEntities.map((entity, idx) => {
                  const hypothesisValueDisplay = entity.hypothesisValue ?? entity.assumedValues?.[0];
                  const isHypothesis = hypothesisValueDisplay != null && hypothesisValueDisplay !== "";
                  const hasEvidences = entity.evidences && entity.evidences.length > 0;
                  const isTargetAnswer = entity.targetAnswer === true;
                  const clueList = entity.discoveredClues?.filter(Boolean) ?? [];
                  const hasClueTooltip = clueList.length > 0;
                  const cardBg = isTargetAnswer
                    ? "bg-violet-50 border-violet-400"
                    : isHypothesis
                      ? "bg-sky-50 border-sky-300"
                      : "bg-orange-50 border-orange-200";
                  const cardContent = (
                    <Card
                      key={`${entity.name}-${idx}`}
                      className={`p-3 ${cardBg} ${hasEvidences || hasClueTooltip ? "cursor-help" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm text-gray-900">{entity.name}</span>
                            {isTargetAnswer && (
                              <Badge variant="outline" className="bg-violet-100 text-violet-800 border-violet-400 text-xs shrink-0">
                                {t('apps.deepSearchExplorer.entityPanel.targetAnswer', 'Target Answer')}
                              </Badge>
                            )}
                          </div>
                          {entity.type && (
                            <div className="text-xs text-gray-500 mt-1">{entity.type}</div>
                          )}
                          {isHypothesis && (
                            <div
                              className={`mt-2 w-full min-w-0 text-sm font-mono rounded px-2 py-2 whitespace-pre-wrap break-words overflow-x-auto max-h-80 overflow-y-auto ${isTargetAnswer ? "text-violet-900 bg-violet-100/80 border border-violet-200" : "text-sky-900 bg-sky-100/80 border border-sky-200"}`}
                            >
                              {hypothesisValueDisplay}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <Badge
                            variant="outline"
                            className={isTargetAnswer && isHypothesis ? "bg-violet-100 text-violet-800 border-violet-400" : isHypothesis ? "bg-sky-100 text-sky-800 border-sky-300" : "bg-white"}
                          >
                            {isHypothesis
                              ? t('apps.deepSearchExplorer.entityPanel.hypothesis', 'Hypothesis')
                              : t('apps.deepSearchExplorer.entityPanel.unknown', 'Unknown')}
                          </Badge>
                        </div>
                      </div>
                    </Card>
                  );
                  if (isHypothesis && hasEvidences) {
                    return (
                      <HoverCard key={`${entity.name}-${idx}`} openDelay={300} closeDelay={100}>
                        <HoverCardTrigger asChild>
                          <div className="w-full text-left">{cardContent}</div>
                        </HoverCardTrigger>
                        <HoverCardContent className="z-[100] w-96 max-h-80 overflow-auto" side="right" align="start">
                          <div className="space-y-3">
                            <div className="text-sm font-semibold text-teal-800 border-b border-teal-200 pb-1">
                              {t('apps.deepSearchExplorer.entityPanel.evidenceForHypothesis', 'Evidence for hypothesis')}
                            </div>
                            {entity.evidences!.map((ev, i) => (
                              <div key={i} className="text-xs space-y-1 border-b border-gray-100 last:border-0 pb-2 last:pb-0">
                                <a
                                  href={ev.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline block truncate font-medium"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {ev.url}
                                </a>
                                <p className="text-gray-700 leading-snug">{ev.snippet}</p>
                              </div>
                            ))}
                          </div>
                        </HoverCardContent>
                      </HoverCard>
                    );
                  }
                  if (hasClueTooltip) {
                    return (
                      <Tooltip key={`${entity.name}-${idx}`} delayDuration={250}>
                        <TooltipTrigger asChild>
                          <div className="w-full text-left">{cardContent}</div>
                        </TooltipTrigger>
                        <TooltipContent side="right" align="start" className="max-w-sm bg-white border border-gray-200 shadow-lg text-gray-900">
                          <p className="text-xs font-semibold text-gray-900 mb-1.5">{t('apps.deepSearchExplorer.entityPanel.discoveredClues', 'Discovered clues')}</p>
                          <ul className="text-xs text-gray-700 space-y-1 list-disc pl-4">
                            {clueList.map((c, i) => (
                              <li key={i}>{c}</li>
                            ))}
                          </ul>
                        </TooltipContent>
                      </Tooltip>
                    );
                  }
                  return <React.Fragment key={`${entity.name}-${idx}`}>{cardContent}</React.Fragment>;
                })
              )}
            </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Known Entities - collapsible */}
          <Collapsible
            open={sectionOpen.knownEntities}
            onOpenChange={(open) => setSectionOpen((s) => ({ ...s, knownEntities: open }))}
          >
            <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md py-1.5 text-left hover:bg-gray-100">
              <ChevronDown
                className={`h-5 w-5 shrink-0 text-gray-500 transition-transform ${sectionOpen.knownEntities ? "" : "-rotate-90"}`}
              />
              <Check className="w-5 h-5 text-green-600" />
              <h3 className="text-gray-900">{t('apps.deepSearchExplorer.entityPanel.knownEntities', 'Known Entities')}</h3>
              <Badge variant="secondary">{knownEntities.length}</Badge>
            </CollapsibleTrigger>
            <CollapsibleContent>
            <p className="text-xs text-gray-500 mb-2 mt-2">{t('apps.deepSearchExplorer.entityPanel.knownEntitiesHint', 'Assumed true in current search state')}</p>
            <div className="space-y-2">
              {knownEntities.length === 0 ? (
                <p className="text-sm text-gray-500 italic">{t('apps.deepSearchExplorer.entityPanel.noKnownEntities', 'No known entities yet')}</p>
              ) : (
                knownEntities.map((entity, idx) => {
                  const isAux = entity.type === "metric" || entity.type === "result";
                  const clueList = entity.discoveredClues?.filter(Boolean) ?? [];
                  const hasClueTooltip = clueList.length > 0;

                  const candidateCard = (
                    <Card
                      className={`p-3 bg-green-50 border-green-200 ${hasClueTooltip ? "cursor-help" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-gray-900">{entity.name}</div>
                          {entity.type ? (
                            <div className="text-xs text-gray-500 mt-1">{entity.type}</div>
                          ) : null}
                          {entity.value != null && entity.value !== "" ? (
                            <div className="mt-2 w-full min-w-0 rounded border border-green-200/80 bg-white px-2 py-2 text-sm font-medium text-gray-900">
                              {entity.value}
                            </div>
                          ) : null}
                        </div>
                        {entity.fromNewState ? (
                          <div className="shrink-0">
                              <Badge variant="outline" className="bg-sky-50 text-sky-900 border-sky-300 text-xs">
                               {t('apps.deepSearchExplorer.entityPanel.hypothesis', 'Hypothesis')}
                              </Badge>
                            </div>
                        ) : null}
                      </div>
                    </Card>
                  );

                  if (isAux) {
                    return (
                      <Card key={`${entity.name}-${idx}`} className="p-3 bg-green-50 border-green-200">
                        <div className="min-w-0 space-y-2">
                          <div className="text-sm text-gray-900">{entity.name}</div>
                          {entity.value != null && entity.value !== "" && (
                            <div className="w-full min-w-0 rounded border border-green-200/80 bg-white px-2 py-2 text-sm text-gray-900">
                              {entity.value}
                            </div>
                          )}
                        </div>
                      </Card>
                    );
                  }

                  if (hasClueTooltip) {
                    return (
                      <Tooltip key={`${entity.name}-${idx}`} delayDuration={250}>
                        <TooltipTrigger asChild>{candidateCard}</TooltipTrigger>
                        <TooltipContent side="right" align="start" className="max-w-sm bg-white border border-gray-200 shadow-lg text-gray-900">
                          <p className="text-xs font-semibold text-gray-900 mb-1.5">{t('apps.deepSearchExplorer.entityPanel.discoveredClues', 'Discovered clues')}</p>
                          <ul className="text-xs text-gray-700 space-y-1 list-disc pl-4">
                            {clueList.map((c, i) => (
                              <li key={i}>{c}</li>
                            ))}
                          </ul>
                        </TooltipContent>
                      </Tooltip>
                    );
                  }

                  return (
                    <React.Fragment key={`${entity.name}-${idx}`}>{candidateCard}</React.Fragment>
                  );
                })
              )}
            </div>
            </CollapsibleContent>
          </Collapsible>
        </div>


      </div>
    </div>
    </>
  );
}
