import type {
  RunStatusResponse,
  RunRoute,
  CreateRunResponse,
  ActionResponse,
  ActionType,
  ActionInfoResponse,
  AnswerResponse,
  EntitiesResponse,
  EntityVariable,
} from './types';
import { DEEP_SEARCH_API_BASE } from './apiConfig';
import { getToken } from '@test-agentstudio/api-client';

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'killed', 'cancelled', 'aborted']);
const SIMPLE_ROUTE_EVENTS = new Set(['react_run_started', 'react_llm_turn']);
const DEEPSEARCH_ROUTE_EVENTS = new Set([
  'state_created',
  'action_proposals_created',
  'action_pool_snapshot',
  'messages_updated',
  'search_final_result',
  'action_result_saved',
]);

const MAX_TRACKED_RUNS = 200;
const MAX_TRACKED_ACTIONS = 2000;
const MAX_TRACKED_ACTION_INFOS = 2000;
const MAX_TRACKED_ANSWERS = 100;

interface DeepSearchTelemetryEnvelope {
  run_id?: unknown;
  seq?: unknown;
  event?: unknown;
  payload?: unknown;
}

interface RunContext {
  conversationId?: string;
  spaceId?: string;
}

interface RunCacheState {
  runStatus: RunStatusResponse;
  actionsById: Map<string, ActionResponse>;
  actionInfoById: Map<string, ActionInfoResponse>;
  answers: AnswerResponse[];
  entities: EntitiesResponse;
  lastSeq: number;
  context: RunContext;
}

const runCache = new Map<string, RunCacheState>();
const telemetrySyncs = new Map<string, Promise<void>>();

function trimRunCache(): void {
  if (runCache.size <= MAX_TRACKED_RUNS) {
    return;
  }

  for (const [runId, cached] of runCache) {
    if (runCache.size <= MAX_TRACKED_RUNS) {
      return;
    }
    if (TERMINAL_STATUSES.has(cached.runStatus.status)) {
      runCache.delete(runId);
    }
  }

  for (const runId of runCache.keys()) {
    if (runCache.size <= MAX_TRACKED_RUNS) {
      break;
    }
    runCache.delete(runId);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function extractUrls(text: string): string[] {
  const matches = text.match(/https?:\/\/[^\s"'<>]+/g) ?? [];
  return Array.from(new Set(matches.map(item => item.trim())));
}

function normalizeToolCallQuery(raw: unknown): string {
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (!trimmed) {
      return '';
    }

    // Some tool-call payloads are JSON-encoded argument strings.
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        return normalizeToolCallQuery(JSON.parse(trimmed));
      } catch {
        // Fall through to URL/plain-text extraction.
      }
    }

    const urls = extractUrls(raw);
    if (urls.length > 0) {
      return urls.join('\n');
    }

    return trimmed.length > 300 ? `${trimmed.slice(0, 300)}…` : trimmed;
  }
  if (isRecord(raw) || Array.isArray(raw)) {
    if (isRecord(raw)) {
      const queryLike =
        asString(raw.query)
        ?? asString(raw.search_query)
        ?? asString(raw.q)
        ?? asString(raw.keyword)
        ?? asString(raw.prompt)
        ?? asString(raw.input)
        ?? asString(raw.url);
      if (queryLike && queryLike.trim()) {
        return queryLike.trim();
      }
    }

    try {
      const serialized = JSON.stringify(raw);
      const urls = extractUrls(serialized);
      return urls.length > 0 ? urls.join('\n') : '';
    } catch {
      return '';
    }
  }
  return '';
}

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .filter((item): item is string => typeof item === 'string')
      .map(item => item.trim())
      .filter(Boolean);
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()];
  }
  return [];
}

function extractToolResultQuery(content: string): string {
  const quotedMatch = content.match(/results\s+for\s+query\s+["']([^"']+)["']/i);
  if (quotedMatch?.[1]) {
    const queryText = quotedMatch[1].trim();
    if (queryText) {
      return queryText;
    }
  }
  return normalizeToolCallQuery(content);
}

function inferToolNameFromContent(content: string): string {
  if (/results\s+for\s+query/i.test(content)) {
    return 'web_search';
  }
  return 'tool_call';
}

function normalizeMessageRecords(raw: unknown): Record<string, unknown>[] {
  if (Array.isArray(raw)) {
    return raw.filter((item): item is Record<string, unknown> => isRecord(item));
  }
  if (isRecord(raw)) {
    if (Array.isArray(raw.messages)) {
      return raw.messages.filter((item): item is Record<string, unknown> => isRecord(item));
    }
    return [raw];
  }
  return [];
}

function extractToolCallsFromMessagesPayload(payload: Record<string, unknown>): Array<{ tool: string; query: string }> {
  const messagesRoot = isRecord(payload.messages) ? payload.messages : payload;
  const messages = normalizeMessageRecords(payload.messages);
  const extracted: Array<{ tool: string; query: string }> = [];

  for (const message of messages) {
    const toolNames = asStringArray(message.last_assistant_tool_call_names);
    const messageToolName = asString(message.last_assistant_tool_call_name);
    const toolCalls = Array.isArray(message.tool_calls) ? message.tool_calls : [];
    const toolsExecuted = message.tools_executed === true || payload.tools_executed === true;

    for (const toolCall of toolCalls) {
      if (!isRecord(toolCall)) continue;
      const fnBlock = isRecord(toolCall.function) ? toolCall.function : null;
      const tool =
        asString(toolCall.name)
        ?? (fnBlock ? asString(fnBlock.name) : null)
        ?? messageToolName
        ?? 'tool_call';
      const rawArgs =
        (fnBlock ? fnBlock.arguments : undefined)
        ?? toolCall.args
        ?? toolCall.arguments
        ?? toolCall.query
        ?? toolCall.input
        ?? toolCall.content;
      const query = normalizeToolCallQuery(rawArgs);
      if (!query) continue;
      extracted.push({ tool, query });
    }

    const messageContents = Array.isArray(message.message_contents)
      ? message.message_contents.filter((item): item is Record<string, unknown> => isRecord(item))
      : [];
    const toolMessages = messageContents.filter(item => asString(item.role) === 'tool');
    if (toolMessages.length > 0) {
      toolMessages.forEach((toolMessage, index) => {
        const content = asString(toolMessage.content);
        if (!content) {
          return;
        }
        const query = extractToolResultQuery(content);
        if (!query) {
          return;
        }
        const inferredTool = toolNames[index] ?? toolNames[0] ?? inferToolNameFromContent(content);
        extracted.push({ tool: inferredTool, query });
      });
      continue;
    }

    if (toolCalls.length === 0 && toolsExecuted && messageToolName) {
      const query = normalizeToolCallQuery(message.content);
      if (query) {
        extracted.push({ tool: messageToolName, query });
      }
    }
  }

  // Current telemetry shape uses payload.messages.message_contents + payload.tools_executed.
  const rootToolNames = asStringArray(messagesRoot.last_assistant_tool_call_names);
  const rootMessageContents = Array.isArray(messagesRoot.message_contents)
    ? messagesRoot.message_contents.filter((item): item is Record<string, unknown> => isRecord(item))
    : [];
  const rootToolMessages = rootMessageContents.filter(item => asString(item.role) === 'tool');
  rootToolMessages.forEach((toolMessage, index) => {
    const content = asString(toolMessage.content);
    if (!content) {
      return;
    }
    const query = extractToolResultQuery(content);
    if (!query) {
      return;
    }
    const tool = rootToolNames[index] ?? rootToolNames[0] ?? inferToolNameFromContent(content);
    extracted.push({ tool, query });
  });

  const dedup = new Map<string, { tool: string; query: string }>();
  for (const entry of extracted) {
    dedup.set(`${entry.tool}|${entry.query}`, entry);
  }
  return Array.from(dedup.values());
}

function extractAssistantFinalAnswerFromMessagesPayload(
  payload: Record<string, unknown>,
  runRoute: RunRoute | undefined,
): string | null {
  const agent = asString(payload.agent)?.toLowerCase();
  const shouldExtract = runRoute === 'simple' || agent === 'simple_react_search';
  if (!shouldExtract) {
    return null;
  }

  const messagesRoot = isRecord(payload.messages) ? payload.messages : payload;
  const lastContent = asString(messagesRoot.last_content);
  if (lastContent && lastContent.trim()) {
    return lastContent.trim();
  }

  const messageContents = Array.isArray(messagesRoot.message_contents)
    ? messagesRoot.message_contents.filter((item): item is Record<string, unknown> => isRecord(item))
    : [];
  const assistantMessages = messageContents
    .filter(item => asString(item.role) === 'assistant')
    .map(item => asString(item.content)?.trim())
    .filter((content): content is string => !!content);

  return assistantMessages.length > 0 ? assistantMessages[assistantMessages.length - 1] : null;
}

function asTelemetryItems(value: unknown): DeepSearchTelemetryEnvelope[] {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    return [];
  }

  return value.items.filter((item): item is DeepSearchTelemetryEnvelope => isRecord(item));
}

function getActionId(payload: Record<string, unknown>): string | null {
  const directActionId =
    asString(payload.action_id)
    ?? asString(payload.current_action_id);
  if (directActionId) {
    return directActionId;
  }

  const actionExecution = payload.action_execution;
  if (isRecord(actionExecution)) {
    const nestedActionId = asString(actionExecution.action_id);
    if (nestedActionId) {
      return nestedActionId;
    }
  }

  if (Array.isArray(payload.messages)) {
    for (let i = payload.messages.length - 1; i >= 0; i -= 1) {
      const message = payload.messages[i];
      if (!isRecord(message)) continue;

      const messageActionId = asString(message.action_id);
      if (messageActionId) {
        return messageActionId;
      }

      if (isRecord(message.action_execution)) {
        const nestedMessageActionId = asString(message.action_execution.action_id);
        if (nestedMessageActionId) {
          return nestedMessageActionId;
        }
      }
    }
  }

  return null;
}

function mapTerminationToStatus(termination: string | null, hasPrediction: unknown): string {
  if (!termination) {
    return hasPrediction === false ? 'failed' : 'completed';
  }

  const normalized = termination.toLowerCase();
  if (['cancel', 'cancelled', 'canceled', 'aborted', 'killed'].includes(normalized)) {
    return 'cancelled';
  }
  if (['failed', 'error', 'timeout'].includes(normalized)) {
    return 'failed';
  }
  return 'completed';
}

function nextRouteFromEvent(currentRoute: RunRoute | undefined, eventName: string): RunRoute | undefined {
  if (eventName === 'question_router_routed_to_react') {
    return 'simple';
  }
  if (currentRoute === 'unknown' || currentRoute == null) {
    if (SIMPLE_ROUTE_EVENTS.has(eventName)) {
      return 'simple';
    }
    if (DEEPSEARCH_ROUTE_EVENTS.has(eventName)) {
      return 'deepsearch';
    }
  }
  return currentRoute;
}

function normalizeEntity(raw: unknown): EntityVariable | null {
  if (!isRecord(raw)) {
    return null;
  }

  const id =
    typeof raw.id === 'number'
      ? raw.id
      : typeof raw.id === 'string' && raw.id.trim() !== ''
        ? Number(raw.id)
        : Number.NaN;
  if (!Number.isFinite(id)) {
    return null;
  }

  const questionClues = Array.isArray(raw.question_clues)
    ? raw.question_clues.filter((item): item is string => typeof item === 'string')
    : [];
  const discoveredClues = Array.isArray(raw.discovered_clues)
    ? raw.discovered_clues.filter((item): item is string => typeof item === 'string')
    : [];

  return {
    id,
    type: asString(raw.type) ?? 'Unknown',
    question_clues: questionClues,
    discovered_clues: discoveredClues,
    candidate: asString(raw.candidate),
    candidate_strength: asNumber(raw.candidate_strength),
  };
}

function boundedMapSet<K, V>(map: Map<K, V>, key: K, value: V, maxSize: number): void {
  if (map.has(key)) {
    map.delete(key);
  }
  map.set(key, value);
  while (map.size > maxSize) {
    const firstKey = map.keys().next().value;
    if (firstKey === undefined) break;
    map.delete(firstKey);
  }
}

function buildActionFromSnapshot(raw: unknown, type: ActionType): ActionResponse | null {
  if (!isRecord(raw)) {
    return null;
  }
  const actionId = asString(raw.id);
  if (!actionId) {
    return null;
  }
  return {
    action_id: actionId,
    action_proposal: asString(raw.direction) ?? '',
    score: asNumber(raw.score) ?? 0,
    depth: asNumber(raw.depth),
    type,
    had_result: null,
  };
}

function ensureRunCache(runId: string, question = '', context?: RunContext): RunCacheState {
  const existing = runCache.get(runId);
  if (existing) {
    if (question && !existing.runStatus.question) {
      existing.runStatus.question = question;
    }
    if (context?.conversationId) {
      existing.context.conversationId = context.conversationId;
    }
    if (context?.spaceId) {
      existing.context.spaceId = context.spaceId;
    }
    return existing;
  }

  const created: RunCacheState = {
    runStatus: {
      run_id: runId,
      status: 'running',
      question,
      route: 'unknown',
    },
    actionsById: new Map(),
    actionInfoById: new Map(),
    answers: [],
    entities: {
      answer_variable: -1,
      entities: [],
    },
    lastSeq: -1,
    context: {
      conversationId: context?.conversationId,
      spaceId: context?.spaceId,
    },
  };
  runCache.set(runId, created);
  trimRunCache();
  return created;
}

function upsertAnswer(run: RunCacheState, answer: AnswerResponse): void {
  const key = answer.previous_action_id ?? `${answer.source}|${answer.file}|${answer.answer ?? ''}`;
  const index = run.answers.findIndex(
    item => (item.previous_action_id ?? `${item.source}|${item.file}|${item.answer ?? ''}`) === key,
  );
  if (index >= 0) {
    run.answers[index] = answer;
  } else {
    run.answers.unshift(answer);
    if (run.answers.length > MAX_TRACKED_ANSWERS) {
      run.answers.length = MAX_TRACKED_ANSWERS;
    }
  }
}

function processTelemetryEvent(
  envelope: DeepSearchTelemetryEnvelope,
  fallbackQuestion: string,
  context?: RunContext,
): string | null {
  const runId = asString(envelope.run_id);
  const eventName = asString(envelope.event);
  if (!runId || !eventName) {
    return null;
  }

  const run = ensureRunCache(runId, fallbackQuestion, context);
  const seq = asNumber(envelope.seq);
  if (seq !== null && seq <= run.lastSeq) {
    return runId;
  }
  if (seq !== null) {
    run.lastSeq = seq;
  }

  const payload = isRecord(envelope.payload) ? envelope.payload : {};
  run.runStatus.route = nextRouteFromEvent(run.runStatus.route, eventName);

  switch (eventName) {
    case 'run_started': {
      const queryPreview = asString(payload.query_preview);
      run.runStatus = {
        ...run.runStatus,
        status: 'running',
        question: queryPreview ?? run.runStatus.question,
      };
      const conversationId = asString(payload.conversation_id);
      if (conversationId) {
        run.context.conversationId = conversationId;
      }
      break;
    }
    case 'state_created': {
      const states = Array.isArray(payload.states) ? payload.states : [];
      const latest = states[states.length - 1];
      if (isRecord(latest) && isRecord(latest.state)) {
        const stateBlock = latest.state;
        const entities = Array.isArray(stateBlock.state)
          ? stateBlock.state.map(normalizeEntity).filter((item): item is EntityVariable => item !== null)
          : [];
        run.entities = {
          answer_variable: asNumber(stateBlock.answer_variable) ?? -1,
          entities,
        };
      }

      const actionId = getActionId(payload);
      if (actionId) {
        const existingInfo = run.actionInfoById.get(actionId);
        const statePayloads = states
          .map(stateItem => {
            if (!isRecord(stateItem)) return null;
            return isRecord(stateItem.state) ? stateItem.state : null;
          })
          .filter((item): item is Record<string, unknown> => item !== null);
        if (statePayloads.length > 0 || existingInfo) {
          const existingResult = isRecord(existingInfo?.result)
            ? { ...(existingInfo?.result as Record<string, unknown>) }
            : {};
          const existingNewStates = Array.isArray(existingResult.new_states)
            ? existingResult.new_states
            : [];
          existingResult.new_states = [...existingNewStates, ...statePayloads];

          const info: ActionInfoResponse = {
            action_id: actionId,
            previous_action: existingInfo?.previous_action ?? null,
            previous_state: existingInfo?.previous_state ?? null,
            result: existingResult,
            time_taken: existingInfo?.time_taken ?? null,
          };
          boundedMapSet(run.actionInfoById, actionId, info, MAX_TRACKED_ACTION_INFOS);
        }
      }
      break;
    }
    case 'action_proposals_created': {
      const actions = Array.isArray(payload.actions) ? payload.actions : [];
      for (const rawAction of actions) {
        if (!isRecord(rawAction)) continue;
        const actionId = asString(rawAction.action_id);
        if (!actionId) continue;
        const action: ActionResponse = {
          action_id: actionId,
          action_proposal: asString(rawAction.proposal_direction) ?? '',
          score: asNumber(rawAction.score) ?? 0,
          depth: asNumber(rawAction.depth),
          type: 'pending',
          had_result: null,
        };
        boundedMapSet(run.actionsById, actionId, action, MAX_TRACKED_ACTIONS);
      }
      break;
    }
    case 'action_pool_snapshot': {
      const snapshot = isRecord(payload.snapshot) ? payload.snapshot : {};
      const collected: ActionResponse[] = [];
      const nextActions = new Map<string, ActionResponse>();
      (['pending', 'running', 'completed'] as const).forEach(statusType => {
        const bucket = Array.isArray(snapshot[statusType]) ? snapshot[statusType] : [];
        for (const rawAction of bucket) {
          const action = buildActionFromSnapshot(rawAction, statusType);
          if (!action) continue;
          collected.push(action);
        }
      });
      collected
        .sort((a, b) => b.score - a.score)
        .slice(0, MAX_TRACKED_ACTIONS)
        .forEach(action => {
          nextActions.set(action.action_id, action);
        });
      run.actionsById = nextActions;
      break;
    }
    case 'messages_updated': {
      const finalAnswer = extractAssistantFinalAnswerFromMessagesPayload(payload, run.runStatus.route);
      if (finalAnswer) {
        upsertAnswer(run, {
          source: asString(payload.source) ?? 'telemetry',
          file: '',
          answer: finalAnswer,
          summary: finalAnswer,
          termination: null,
          completion_time: null,
          previous_action: null,
          previous_action_id: null,
        });
      }

      const actionId = getActionId(payload);
      if (actionId) {
        const calls = extractToolCallsFromMessagesPayload(payload);
        if (calls.length > 0) {
          const existingInfo = run.actionInfoById.get(actionId);
          const existingResult = isRecord(existingInfo?.result)
            ? { ...(existingInfo?.result as Record<string, unknown>) }
            : {};
          const existingHistory = Array.isArray(existingResult.tool_calls_history)
            ? existingResult.tool_calls_history.filter((item): item is Record<string, unknown> => isRecord(item))
            : [];
          const dedup = new Map<string, { tool: string; query: string }>();
          existingHistory.forEach(item => {
            const tool = asString(item.tool);
            const query = asString(item.query);
            if (tool && query) dedup.set(`${tool}|${query}`, { tool, query });
          });
          calls.forEach(item => {
            dedup.set(`${item.tool}|${item.query}`, item);
          });
          existingResult.tool_calls_history = Array.from(dedup.values());

          const info: ActionInfoResponse = {
            action_id: actionId,
            previous_action: existingInfo?.previous_action ?? null,
            previous_state: existingInfo?.previous_state ?? null,
            result: existingResult,
            time_taken: existingInfo?.time_taken ?? null,
          };
          boundedMapSet(run.actionInfoById, actionId, info, MAX_TRACKED_ACTION_INFOS);
        }
      }
      break;
    }
    case 'action_result_saved': {
      const actionId = getActionId(payload);
      const hasAnswer = payload.has_answer === true;
      if (actionId) {
        const existingAction = run.actionsById.get(actionId);
        if (existingAction) {
          boundedMapSet(
            run.actionsById,
            actionId,
            {
              ...existingAction,
              had_result: true,
            },
            MAX_TRACKED_ACTIONS,
          );
        }

        const existingInfo = run.actionInfoById.get(actionId);
        const existingResult = isRecord(existingInfo?.result)
          ? { ...(existingInfo?.result as Record<string, unknown>) }
          : {};
        const mergedResult = {
          ...existingResult,
          ...payload,
        };

        const info: ActionInfoResponse = {
          action_id: actionId,
          previous_action: existingInfo?.previous_action ?? null,
          previous_state: existingInfo?.previous_state ?? null,
          result: mergedResult,
          time_taken: existingInfo?.time_taken ?? null,
        };
        boundedMapSet(run.actionInfoById, actionId, info, MAX_TRACKED_ACTION_INFOS);
      }

      if (hasAnswer) {
        const answerPreview = asString(payload.answer_preview);
        const answer: AnswerResponse = {
          source: asString(payload.source) ?? 'telemetry',
          file: asString(payload.result_file) ?? '',
          answer: answerPreview,
          summary: answerPreview,
          termination: null,
          completion_time: null,
          previous_action: null,
          previous_action_id: actionId,
        };
        upsertAnswer(run, answer);
      }
      break;
    }
    case 'search_final_result': {
      const termination = asString(payload.termination);
      const completionTime = asNumber(payload.completion_time_sec);
      const status = mapTerminationToStatus(termination, payload.has_prediction);

      run.runStatus = {
        ...run.runStatus,
        status,
      };

      if (run.answers.length === 0) {
        upsertAnswer(run, {
          source: asString(payload.source) ?? 'telemetry',
          file: '',
          answer: null,
          summary: termination ? `Run completed with termination: ${termination}` : null,
          termination,
          completion_time: completionTime,
          previous_action: null,
          previous_action_id: null,
        });
      } else {
        run.answers = run.answers.map(answer => ({
          ...answer,
          termination: answer.termination ?? termination,
          completion_time: answer.completion_time ?? completionTime,
        }));
      }
      break;
    }
    case 'run_completed': {
      run.runStatus = {
        ...run.runStatus,
        status: 'completed',
      };
      break;
    }
    case 'run_failed': {
      run.runStatus = {
        ...run.runStatus,
        status: 'failed',
      };
      break;
    }
    case 'run_cancelled': {
      run.runStatus = {
        ...run.runStatus,
        status: 'cancelled',
      };
      break;
    }
    default:
      break;
  }

  return runId;
}

function getRunOrDefault(runId: string): RunCacheState {
  return ensureRunCache(runId);
}

function buildAuthHeaders(): HeadersInit {
  const token = getToken();
  if (!token) {
    throw new Error('Unable to get auth token');
  }
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

function normalizeCreatedStatus(status: string | null): string {
  if (!status) {
    return 'running';
  }
  const normalized = status.toLowerCase();
  if (normalized === 'started') {
    return 'running';
  }
  return normalized;
}

function buildTelemetryQuery(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined) {
      return;
    }
    query.set(key, String(value));
  });
  const queryString = query.toString();
  return queryString ? `?${queryString}` : '';
}

async function readRecentTelemetry(run: RunCacheState): Promise<DeepSearchTelemetryEnvelope[]> {
  const query = buildTelemetryQuery({
    n: 1,
    run_id: run.runStatus.run_id,
    space_id: run.context.spaceId,
  });
  const response = await fetch(`${DEEP_SEARCH_API_BASE}/telemetry/recent${query}`, {
    method: 'GET',
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`getRecentTelemetry failed: ${response.status}`);
  }
  return asTelemetryItems(await response.json());
}

async function readTelemetryRange(
  run: RunCacheState,
  startSeq: number,
  endSeq: number,
): Promise<DeepSearchTelemetryEnvelope[]> {
  const query = buildTelemetryQuery({
    run_id: run.runStatus.run_id,
    start_seq: startSeq,
    end_seq: endSeq,
    space_id: run.context.spaceId,
  });
  const response = await fetch(`${DEEP_SEARCH_API_BASE}/telemetry/range${query}`, {
    method: 'GET',
    headers: buildAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`getTelemetryRange failed: ${response.status}`);
  }
  return asTelemetryItems(await response.json());
}

async function syncRunTelemetry(runId: string, fallbackQuestion = ''): Promise<void> {
  const inFlight = telemetrySyncs.get(runId);
  if (inFlight) {
    return inFlight;
  }

  const run = ensureRunCache(runId, fallbackQuestion);
  const syncPromise = (async () => {
    const latestItems = await readRecentTelemetry(run);
    if (latestItems.length === 0) {
      return;
    }

    const latestEnvelope = latestItems[latestItems.length - 1];
    const latestSeq = asNumber(latestEnvelope.seq);
    if (latestSeq === null || latestSeq <= run.lastSeq) {
      return;
    }

    const startSeq = Math.max(run.lastSeq + 1, 0);
    const rangeItems = await readTelemetryRange(run, startSeq, latestSeq);
    rangeItems
      .slice()
      .sort((a, b) => (asNumber(a.seq) ?? 0) - (asNumber(b.seq) ?? 0))
      .forEach(item => {
        processTelemetryEvent(item, fallbackQuestion, run.context);
      });
  })().finally(() => {
    telemetrySyncs.delete(runId);
  });

  telemetrySyncs.set(runId, syncPromise);
  return syncPromise;
}

export async function createRun(question: string, config?: Record<string, unknown> | null): Promise<CreateRunResponse> {
  if (!config || !isRecord(config)) {
    throw new Error('createRun requires a DeepSearch run payload');
  }

  const spaceId = asString(config.space_id);
  if (!spaceId) {
    throw new Error('createRun requires space_id');
  }

  const body: Record<string, unknown> = {
    ...config,
    query: question,
    search_mode: 'search',
  };

  const response = await fetch(`${DEEP_SEARCH_API_BASE}/runs`, {
    method: 'POST',
    headers: buildAuthHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = '';
    try {
      const errBody = await response.json();
      if (errBody && typeof errBody === 'object' && 'detail' in errBody) {
        const raw = (errBody as { detail?: unknown }).detail;
        detail = typeof raw === 'string' ? raw : JSON.stringify(raw);
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(
      detail
        ? `createRun failed: ${response.status} — ${detail}`
        : `createRun failed: ${response.status}`,
    );
  }

  const payload = await response.json();
  const runId = isRecord(payload) ? asString(payload.run_id) : null;
  if (!runId) {
    throw new Error('createRun failed: missing run_id');
  }

  const run = ensureRunCache(runId, question, {
    spaceId,
    conversationId: isRecord(payload) ? asString(payload.conversation_id) ?? undefined : undefined,
  });
  run.runStatus = {
    ...run.runStatus,
    status: normalizeCreatedStatus(isRecord(payload) ? asString(payload.status) : null),
  };

  await syncRunTelemetry(runId, question);
  return {
    run_id: runId,
    status: run.runStatus.status,
    mode: 'search',
  };
}

export async function listRuns(): Promise<RunStatusResponse[]> {
  return Array.from(runCache.values()).map(run => ({ ...run.runStatus }));
}

export async function getRunStatus(runId: string): Promise<RunStatusResponse> {
  const run = getRunOrDefault(runId);
  await syncRunTelemetry(runId, run.runStatus.question);
  return { ...run.runStatus };
}

export async function getActions(runId: string, type?: ActionType): Promise<ActionResponse[]> {
  const run = getRunOrDefault(runId);
  await syncRunTelemetry(runId, run.runStatus.question);
  const allActions = Array.from(run.actionsById.values())
    .sort((a, b) => b.score - a.score)
    .map(action => ({ ...action }));
  return type ? allActions.filter(action => action.type === type) : allActions;
}

export async function getActionInfo(runId: string, actionId: string): Promise<ActionInfoResponse> {
  const run = getRunOrDefault(runId);
  await syncRunTelemetry(runId, run.runStatus.question);
  const cached = run.actionInfoById.get(actionId);
  if (cached) {
    return {
      action_id: cached.action_id,
      previous_action: cached.previous_action ?? null,
      previous_state: cached.previous_state ?? null,
      result: cached.result ?? null,
      time_taken: cached.time_taken ?? null,
    };
  }

  const action = run.actionsById.get(actionId);
  return {
    action_id: actionId,
    previous_action: null,
    previous_state: null,
    result: action ?? null,
    time_taken: null,
  };
}

export async function getAnswers(runId: string): Promise<AnswerResponse[]> {
  const run = getRunOrDefault(runId);
  await syncRunTelemetry(runId, run.runStatus.question);
  return run.answers.map(answer => ({ ...answer }));
}

export async function getEntities(runId: string): Promise<EntitiesResponse> {
  const run = getRunOrDefault(runId);
  await syncRunTelemetry(runId, run.runStatus.question);
  return {
    answer_variable: run.entities.answer_variable,
    entities: run.entities.entities.map(entity => ({ ...entity })),
  };
}

export async function killRun(runId: string): Promise<void> {
  const run = getRunOrDefault(runId);
  run.runStatus = {
    ...run.runStatus,
    status: 'cancelled',
  };

  const query = buildTelemetryQuery({
    space_id: run.context.spaceId,
  });
  const response = await fetch(`${DEEP_SEARCH_API_BASE}/runs/${encodeURIComponent(runId)}/cancel${query}`, {
    method: 'POST',
    headers: buildAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`killRun failed: ${response.status}`);
  }

  await syncRunTelemetry(runId, run.runStatus.question);
}

export async function healthCheck(): Promise<unknown> {
  const res = await fetch(`${DEEP_SEARCH_API_BASE}/heartbeat`, {
    headers: buildAuthHeaders(),
  });
  if (!res.ok) throw new Error(`healthCheck failed: ${res.status}`);
  return res.json();
}
