// Types matching the DeepSearch API (OpenAPI spec)

export type ActionType = "pending" | "running" | "completed";
export type RunRoute = "unknown" | "deepsearch" | "simple";

export interface RunStatusResponse {
  run_id: string;
  status: string;
  question: string;
  route?: RunRoute;
}

export interface CreateRunResponse {
  run_id: string;
  status: string;
  mode: string;
}

export interface ActionResponse {
  action_id: string;
  action_proposal: string;
  score: number;
  depth?: number | null;
  type: ActionType;
  had_result?: boolean | null;
}

export interface ActionInfoResponse {
  action_id: string;
  previous_action?: string | null;
  previous_state?: unknown | null;
  result?: unknown | null;
  time_taken?: number | null;
}

export interface AnswerResponse {
  source: string;
  file: string;
  answer?: string | null;
  termination?: string | null;
  completion_time?: number | null;
  previous_action?: string | null;
  previous_action_id?: string | null;
  summary?: string | null;
}

export interface EntityVariable {
  id: number;
  type: string;
  question_clues: string[];
  discovered_clues: string[];
  candidate?: string | null;
  candidate_strength?: number | null;
}

export interface EntitiesResponse {
  answer_variable: number;
  entities: EntityVariable[];
}
