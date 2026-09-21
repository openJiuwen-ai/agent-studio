/** 对话工作台中浏览器可见的最小 Skill 目录项。 */
export interface ConversationSkillItem {
  skillId: string;
  name: string;
  description: string;
}

/** 浏览器发往对话工作台的本轮请求。 */
export interface ConversationFileReference {
  url: string;
  fileName: string;
  progress?: 'loading' | 'succeeded' | 'failed';
  fileId?: string;
}

export interface ConversationSendRequest {
  query: string;
  model_deployment_id?: string;
  recommended_skill_ids: string[];
  select_type?: 'SUPERVISOR' | 'APP';
  app_id?: string;
  file_ids?: Array<Pick<ConversationFileReference, 'url' | 'fileName'>>;
}

/** 工作台可执行目标。资源列表复用 AgentCenter 现有接口。 */
export interface ConversationExecutionTarget {
  id: string;
  name: string;
  type: 'SUPERVISOR' | 'SINGLE_AGENT' | 'MULTI_AGENT';
}

/** 对话工作台 SSE 回调。 */
export interface ConversationSseCallbacks {
  onStatus?: (event: unknown) => void;
  onOpen?: () => void;
  onMessage?: (event: MessageEvent) => void;
  onModeration?: (event: unknown) => void;
  onTimeout?: () => void;
  onDone?: () => void;
  onError?: () => void;
  onAbort?: () => void;
  onReadyStateChange?: (event: unknown) => void;
}
