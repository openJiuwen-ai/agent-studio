import { MemoryUpdatedSSE } from "@shared/components/memory-management/memory-management.interface";

export interface IMappings {
  count: number;
  relations: IMappingItem[];
}

export interface IMappingItem {
  mapping_id: string;
  app_id: string;
  app_name: string;
  app_type: string;
  resource_id: string;
  resource_type: string;
  resource_name: string;
}

export interface IBatchMappings {
  count: number;
  resource_list: IResourceList[];
}

export interface IResourceList {
  resource_id: string;
  resource_name: string;
  reference_number: number;
}

export interface IPage {
  limit: number;
  offset: number;
}

export interface ICallbackFn {
  successCb?: () => void;
  failCb?: () => void;
  finallyCb?: () => void;
}

export enum ENodeStatus {
  NOTFINISHED = 'not-finished',
  FINISHED = 'finished',
  ADDED = 'added',
}

// 任务型工作流，需要被过滤的输入参数名称列表
export const TASK_FILTER_KEYS = ['sys', 'conversation_history', 'env'];

// 对话型工作流，需要被过滤的输入参数名称列表
export const CHAT_FILTER_KEYS = ['sys', 'conversation_history', 'query', 'env'];

export const CHAT_ASYNC_FILTER_KEYS = ['sys', 'conversation_history', 'env'];

export interface IFlowChatItemArgs {
  query: string;
  dialogId: string;
  options?: Record<string, any>;
}

export interface IFlowChatItem {
  /** 输入的询问，同 query */
  showQuestion: string;

  /** 回答正文 */
  showAnswer: IAnswerItem[];

  thinking: boolean;

  /** 思考内容 */
  thinkValue: string;

  thinkLoading: boolean;

  /** 思考内容是否折叠 */
  collapsed: boolean;

  /** 试运行ID */
  dialogId: string;

  /** 会话执行ID */
  execution_id?: string;

  showCopiedTip?: boolean;

  /** 询问请求报错时的错误码 */
  reqErrorStatus?: string;

  /** 任务型工作流，作用未知 */
  answer?: string;

  /** 卡片式问答数据 */
  cards?: IFlowChatCard[];

  /** 规划模式思考过程 */
  plans?: IFlowChatPlan[];

  /** 试运行执行耗时 */
  latency?: string;

  tagNum?: number;

  /** 点赞/点踩数量 */
  vote?: number;

  /** 用户画像 */
  userPersona?: MemoryUpdatedSSE;

  /** 是否终止 */
  terminate?: boolean

  /** 最终输出结果复制按钮是否已点击（图标切换） */
  answerCopyIcon?: boolean;
}

export interface IAnswerItem {
  /** 回答内容 */
  text: string;

  /** 输入参数 */
  inputList?: IInputItem[];

  uuid?: string;
  messageId?: string;
  loading?: boolean;
  isLike?: boolean;
  isDislike?: boolean;
  isShowInputParams?: boolean;

  /** input输入节点提交状态 */
  inputStatus?: string;

  /** @deprecated 已废弃，优先使用 inputStatus */
  isConfirmed?: string;
  isFinished?: boolean;
  isException?: boolean;
  isError?: boolean;
}

export interface IInputItem {
  actualType: string;
  sourceType: string;
  description: string;
  name: string;
  type: string;
  required: boolean;
  uniqueId: string;
}

export interface IFlowChatCard {
  instance_id: string;
  resource_url: string;
  node_id: string;
  node_type: string;
  node_name: string;
  workflow_id: string;
  workflow_name: string;
  createdTime: number;

  /** 卡片内容，源数据为流式数据时需持续写入 */
  desc: string;

  /** 卡片标题，源数据为流式数据时需持续写入 */
  title: string;
}

export interface IFlowChatPlan {
  id?: string;
  title: string;
  // 待废弃，使用id
  type?: 'execStep';
  status: 'loading' | 'finished';
  steps?: Array<{
    description: string;
    step_idx: number;
    step_name: string;
  }>;
  actionSteps?: Array<{
    title: string;
    actions: Array<{
      content?: string;
      title: string;
    }>;
  }>;
}

export interface IAppRefList {
  count: number;
  relations: IRelationItem[];
}

export interface IRelationItem {
  latest_version_app_sub_type?: string;
  relation_id: string;
  app_id: string;
  app_type: string;
  app_name: string;
  resource_id: string;
  resource_version: string;
  resource_type: string;
  resource_name: string;
  valid: boolean;
  resource_latest_version?: string;
  resource_latest_version_name?: string;
}

export enum EValidationMode {
  DEFAULT = 'default', // 默认执行校验
  SKIP = 'skip', // 跳过校验
}

export enum NodeTypeTopic {
  Start = 'Start',
  End = 'end',
  LLM = 'llm',
  Workflow = 'workflow',
  Branch = 'branch',
  IntentDetection = 'intent_detection',
  Code = 'code',
  ComplexIntentDetection = 'complex_intent_detection',
  Loop = 'loop',
  Plugin = 'plugin',
  Mcp = 'mcp',
  Http = 'http',
  Card = 'card',
  StructuredMessagesException = 'structured_messages_exception',
  SetVariable = 'set_variable',
  Aggregation = 'aggregation',
  KnowledgeRepo = 'knowledge_repo',
  Agent = 'agent',
  Message = 'message',
  Questioner = 'questioner',
  Input = 'input',
  QA = 'qa',
  ParamExtraction = 'param_extraction',
}

export interface McpDeployFailType {
  code: string;
  debug_info: string;
  message_cn: string;
  message_en: string;
  reason_cn: string;
  reason_en: string;
  suggestion_cn: string;
  suggestion_en: string;
}

export enum ERROR_CODE {
  QUOTA_USED_UP = 'Openjiuwen.02801001',
}

export enum BELONGS_TYPE {
  CUSTOM = 'custom',
  INNER = 'inner',
  SHARE = 'share',
}

export enum MCP_SERVER {
  NPX = 'example-npx',
  SSE = 'example-sse',
  UVX = 'example-uvx',
  STREAMABLE_HTTP = 'example-streamable-http',
}

