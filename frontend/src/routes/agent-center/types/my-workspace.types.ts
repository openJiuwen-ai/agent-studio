import i18next from 'i18next';
import { IMemoParam } from '../app-agent/components/create-memo/types';
import { IContentReview, IWorkflowField } from '../app-flow/node.type';

const getHoursOption = () => {
  return [
    { label: '00:00' },
    { label: '01:00' },
    { label: '02:00' },
    { label: '03:00' },
    { label: '04:00' },
    { label: '05:00' },
    { label: '06:00' },
    { label: '07:00' },
    { label: '08:00' },
    { label: '09:00' },
    { label: '10:00' },
    { label: '11:00' },
    { label: '12:00' },
    { label: '13:00' },
    { label: '14:00' },
    { label: '15:00' },
    { label: '16:00' },
    { label: '17:00' },
    { label: '18:00' },
    { label: '19:00' },
    { label: '20:00' },
    { label: '21:00' },
    { label: '22:00' },
    { label: '23:00' },
  ];
};

const hoursOption = getHoursOption();

/** Agent创编页，分页组件的每页条数limit值 */
export const PAGINATION_LIMIT_NUM = 10;

/** 工作流卡片可选状态，使用处：Agent创编页添加工作流 */
 export const  WORKFLOW_NORMAL_STATUS = 1;

/** 添加插件弹窗中的2个Tab Id */
export enum EPluginCategoryTabId {
  MARKET = 'MARKET',
  PERSONAL = 'PERSONAL',
  SHARE = 'SHARE',
}

export interface IModelConfigType {
  modelName: string;
  top_p?: number;
  temperature?: number;
  url?: string;
  healthy?: string;
  showUrl?: string;
  default?: string;
  label?: string;
  mode?: string;
}

export interface IPromptTagItem {
  name: string;
  type: string;
}

export interface ISingleAgentQueryResp {
  icon: string;
  name?: string;
  title?:string;
  description: string;
  status?: string;
  promptTags?: IPromptTagItem[];
  agentType?: string;
  agentSubType?: string;
  id?: string,
}

export interface INameDescription {
  name?: string;
  description?: string;
}

export interface IPrologueAndQuestionsParams {
  prologue?: string;
  suggest_queries?: string[];
}

export type TimeConsumption = {
  total_latency?: number;
  overall_latency?: number;
  overall?: number;
  model_latency?: number;
  wait_latency?: number;
  plugin_latency?: number;
  first_token_latency?: number;
};

export type TimeConsumptionStr = {
  total_latency_str: string;
  overall_latency_str: string;
  overall_str?: string;
  model_latency_str: string;
  wait_latency_str: string;
  plugin_latency_str?: string;
  first_token_latency_str?: string;
};

export type ConversationContent = {
  role: string;
  content: any;
  reasoning_content?: any;
  title?: any;
  thinking?:boolean;
  collapsed?:boolean;
  image: string;
  function_call?: {
    name: string;
    arguments: string;
  };
  name?: string;
  time_consumption?: TimeConsumption;
  data?: {
    answer: any;
    error_code?: string;
    error_message?: string;
  };
  event?: string;
  conversation_id?: string;
  created_time?: string;
  answer?: {};
  memory_variables?: { key: string; value: any }[];
  is_workflow?: boolean;
  quoteList?: any;
  isLikeClicked?: boolean;
  isDislikeClicked?: boolean;
  file?: string;
  img?: string;
  uploadData?: Array<any>;
  executionId?: string;
  tagNum?: string;
  vote?: Number;
  isShowInputParams?:boolean
  inputList?: Array<any>
  cards?:Array<any>
  isConfirm?:boolean,
  isError?:boolean,
  errorContent?: string;
  errorIsOpen?:boolean,
  icon?:string;
  thought?: any;
  timeConsumptionStr?: any;
  isConfirmed?: string,
  dialogId?:string,
  hasSummary?:boolean
};

export type FuncCallItem = {
  pluginName: string;
  request: Record<string, any>;
  response: Record<string, any>;
  role: string;
  title: string;
  isRunning: boolean;
  time_consumption: TimeConsumption & { totalEx?: number };
  toolType?: string;
  status: string;
  memory_variables?: { key: string; value: any }[];
  collapsed?: boolean;
  allCollapsed?: boolean;
  icon?:string;
  thought?:any,
  tipTitle?:string
};

export interface IAssistantRoleItem {
  role: string;
  time_consumption: TimeConsumption;
  content?: string;
}

export interface IVoiceInteraction {
  language: string;
  timbre: string;
  domain: string;
}

export interface ReferenceResponse {
  switch: boolean;
  json_format: boolean;
}

export interface ISingleAgentPutBodyNew {
  name: string;
  description: string;
  icon: string;
  instructions: string;
  model_deployment_id: string;
  model_name: string;
  model_endpoint: string;
  model_version: string;
  model_config: IModelConfig;
  model_type: string;
  model: string;
  tools: object[];
  tool_details: object[];
  mcp_details: object[];
  workflows: object[];
  workflow_details: object[];
  mcp_servers: string[];
  knowledge_repos: string[];
  trigger_list: ITriggerList[];
  memory_variables: IMemoParam[];
  variables: IWorkflowField[];
  prologue: string;
  suggest_queries: string[];
  additional_questions_config: IAdditionalQuestionsConfig;
  knowledge_retrieve_policy: IKnowledgeRetrievePolicy;
  status: number;
  creator: string;
  scheduling_mode: string;
  workflow_switch_enabled: boolean;
  create_time: string;
  update_time: string;
  publish_time: string;
  voice_interaction: IVoiceInteraction;
  content_review: IContentReview;
  safety_barrier: boolean;
  agent_variables: Array<AgentVarInfo>;
  memory_config: {
    memory_repo_id?: string;
    name?: string;
    description?: string;
  } | null;
  type?: string;
  writing_template?: string;
  is_template?: boolean;
  search_engine?: any;
  reference?: any;
  mcp_choose_tools?: any;
  input_variables: Array<InputVarInfo>;
}

export interface ISingleAgentPutBody {
  name: string;
  description: string;
  icon: string;
  instructions: string;
  model_deployment_id: string;
  model_name: string;
  model_endpoint: string;
  model_version: string;
  model_config: IModelConfig;
  model_type: string;
  model: string;
  tools: string[];
  workflows: string[];
  mcp_servers: string[];
  knowledge_repos: string[];
  trigger_list: ITriggerList[];
  memory_variables: IMemoParam[];
  variables: IWorkflowField[];
  prologue: string;
  suggest_queries: string[];
  additional_questions_config: IAdditionalQuestionsConfig;
  knowledge_retrieve_policy: IKnowledgeRetrievePolicy;
  agent_variables: Array<AgentVarInfo>;
  memory_config: { long_term_memory: boolean };
  status: number;
  creator: string;
  scheduling_mode: string;
  workflow_switch_enabled: boolean;
  create_time: string;
  update_time: string;
  publish_time: string;
  voice_interaction: IVoiceInteraction;
  content_review: IContentReview;
  safety_barrier: boolean;
}

export interface IModelConfig {
  top_p: number;
  temperature: number;
  history_size: number;
  max_tokens: number;
  output_format: string;
}

export interface AgentVarInfo {
  variable_key: string,
  description: string,
  default_value: string,
}

export interface InputVarInfo {
  variable_key: string,
  description: string,
  default_value: string,
  input_type: string,
}

export interface ITriggerList {
  trigger_id: string;
  name: string;
  type: string;
  cron: string;
  prompt: string;
  params: ITriggerParam[];
  hook_url: string;
  created_on: string;
}

export interface ITriggerParam {
  name: string;
  description: string;
}

export interface IAdditionalQuestionsConfig {
  enable: boolean;
  prompt: string;
  rounds?: number;
}

export interface IKnowledgeRetrievePolicy {
  search_mode: string;
  top_k: number;
  recall_threshold: number;
  faq_threshold: number;
  need_extras_faq_search: boolean;
  extra_params?: Array<{key: string, value: string}>;
}

export interface IUpdateSingleAgentConfig {
  data: Partial<ISingleAgentPutBodyNew>;
  successCb?: () => void;
  failCb?: (error?: any) => void;
  finallyCb?: () => void;
}

export const triggerTimeOptions = [
  {
    label: i18next.t('triggerhalfmodalcomponent_111'),
    children: hoursOption,
  },
  {
    label: i18next.t('triggerhalfmodalcomponent_112'),
    children: [
      { label: i18next.t('commonlogicagent_5'), children: hoursOption },
      { label: i18next.t('commonlogicagent_6'), children: hoursOption },
      { label: i18next.t('commonlogicagent_7'), children: hoursOption },
      { label: i18next.t('commonlogicagent_8'), children: hoursOption },
      { label: i18next.t('commonlogicagent_9'), children: hoursOption },
      { label: i18next.t('commonlogicagent_10'), children: hoursOption },
      { label: i18next.t('commonlogicagent_11'), children: hoursOption },
    ],
  },
  {
    label: i18next.t('triggerhalfmodalcomponent_113'),
    children: [
      { label: i18next.t('myworkspacetypes_1244'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1245'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1246'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1247'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1248'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1249'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1250'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1251'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1252'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1253'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1254'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1255'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1256'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1257'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1258'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1259'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1260'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1261'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1262'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1263'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1264'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1265'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1266'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1267'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1268'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1269'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1270'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1271'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1272'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1273'), children: hoursOption },
      { label: i18next.t('myworkspacetypes_1274'), children: hoursOption },
    ],
  },
  {
    label: i18next.t('triggerhalfmodalcomponent_115'),
    children: [
      {
        label: i18next.t('myworkspacetypes_1276'),
        children: getHoursOption(),
      },
      {
        label: i18next.t('myworkspacetypes_1277'),
        children: getHoursOption(),
      },
      {
        label: i18next.t('myworkspacetypes_1278'),
        children: getHoursOption(),
      },
      {
        label: i18next.t('myworkspacetypes_1279'),
        children: getHoursOption(),
      },
      {
        label: i18next.t('myworkspacetypes_1280'),
        children: getHoursOption(),
      },
    ],
  },
];
