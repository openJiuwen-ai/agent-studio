/* eslint-disable eslint-comments/disable-enable-pair */
import { IMemoryLibBaseInfo } from '@routes/memory-lib/memory-lib-interfaces';
import {
  ICommentNode,
  IContentReview,
  INodeType,
  IWorkflowField,
  NodeInfo,
} from './node.type';

export interface INodePort {
  id: string;
  group: string;
}

export interface IEdgeType {
  id: string;
  shape: string;
  source: IConnection;
  target: IConnection;
  zIndex: number;
}

export interface IConnection {
  cell: string;
  port: string;
}

export interface Position {
  x: number;
  y: number;
}

export interface Parameter {
  name: string;
  type: string;
  content: string | { source: string; name: string };
}

export interface CellNodeData {
  inputs?: {
    parameters: Array<Parameter>;
    code?: string;
  };
  outputs?: Array<{ name: string }>;
  meta: { name: string };
  workflowId?: string;
}

export interface Port {
  id: string;
  group: string;
}

export interface NewNode {
  id: string;
  shape: string;
  position: Position;
  data?: any;
  ports: {
    items: Port[];
  };
}

export interface IWorkflowNode {
  id: string;
  type: string;
  name: string;
}

export interface NodeData {
  id: string;
  shape: string;
  position: Position;
  data: CellNodeData;
  ports: {
    items: Array<{ id: string; group: string }>;
  };
}

export interface FetchEdge {
  source: string;
  target: string;
  conditionId?: string;
}

export interface ILayout {
  [key: string]: Position;
}

export type ILayouts = Record<string, Position>;

export interface IWorkflowEdge {
  exception_branch?: boolean;
  id?: string;
  source: string;
  target: string;
  branch?: string;
}

export interface IFlowTrigger {
  type: string;

  // Dify
  cron_expression?: string;
  frequency?: string;
  mode?: string;
  time?: string;
  name?: string;
  cron?: string;
  hook_url?: string;
  prompt?: string;
  invocation?: string;
}

export interface IFlowConfigs {
  default_model: {
    model_name: string;
    model_deployment_id: string;
    model_type: string;
    model?: string;
  };
  environment?: string;
  default_model_switch: boolean;
  prologue: string;
  suggest_queries: string[];
  long_memory_enabled: boolean;
  memory: IWorkflowField[];
  safety_barrier: boolean;
  content_review: IContentReview;
  trigger_list?: any[];
  voice_interaction: {
    language: string;
    timbre: string;
    domain: string;
  };
  additional_questions_config:{
    enable: boolean;
    prompt: string;
  }
  type?: string;
  voice_interaction_switch: boolean;
  nl2workflow_first?: boolean; //是否是nl2workflow 首次打开
  // dify导入的触发器
  trigger?: IFlowTrigger;
  memory_config?: IMemoryLibBaseInfo;
}

export interface IWorkflowDetail {
  id?: string;
  name?: string;
  description?: string;
  metadata?: {
    layout: ILayout;
  };
  nodes: NodeInfo[];
  comments: ICommentNode[];
  edges: IWorkflowEdge[];
  configs?: IFlowConfigs;
  layouts: ILayouts;
  connections?: FetchEdge[];
  inputs?: IWorkflowField[];
  global_variables?: IWorkflowField[];
  memory_config?: IMemoryLibBaseInfo;
  environment?: string;
}

export interface SourceTargetCell {
  cell: string;
  port: string;
}

export interface EdgeData {
  id?: string;
  shape: string;
  source: SourceTargetCell;
  target: SourceTargetCell;

  attrs: any;
  connector?: {
    name: string;
  };
  router?: {
    name: string;
  };
}

export interface CellData {
  nodes: NodeData[];
  edges: EdgeData[];
  comments: NodeData[];
}

export interface IStartEndParam {
  name: string;
  type?: string;
  description?: string;
  value: string;
}

export interface WorkFlowBriefInfo {
  avatar: string;
  name: string;
}

export interface IWorkflowBasic {
  name: string;
  code: string;
  description?: string;
  inputs: IStartEndParam[];
  outputs: IStartEndParam[];
  status?: number;
  creator: string;
}

export interface RelatedInfo {
  logo: string;
}

export interface IWorkflowInfo extends IWorkflowBasic {
  workflow_id?: string;
  agent_id?: string;
  update_time?: string;
  project_id?: string;
  details?: IWorkflowDetail;
  avatar?: string;
  icon?: string;
  referenced_by?: string;
  related_info?: RelatedInfo;
  workflow_details?: IWorkflowDetail;
  published_data?: IWorkflowDetail;
  published?: boolean;
  url?: string;
  type?: string;
  updated_on?: number;
  version_id?: string;
}

export interface IWorkflowUpdateData {
  workflow_id: string;
  avatar?: string;
  name?: string;
  workflow_details?: IWorkflowDetail;
  description?: string;
  update_time?: number;
  customize_node?: boolean;
  updated_on?: number;
  code?:string;
}

export interface taskItem {
  id?: string;
  type: string;
  name: string;
  mode: string;
  inputs: { query: string };
  timeout: number;
  version: number;
  isEdit?: boolean;
  status: string;
  message?:string;
  is_published?: boolean;
}

export interface IWorkflow {
  workflow_id: string;
  avatar: string;
  status: number | string;
  name: string;
  workflow_details: IWorkflowDetail;
  details?: IWorkflowDetail;
  type: WorkFlowType;
  description: string;
  create_time: string;
  update_time: number;
  creator: string;
  creator_id: string;
  is_drag?: boolean;
  code?: string;
  test_status: number;
  ref_workflows?: IRefWorkflows[];
  publish_time?: number;
  taskInfo?: taskItem;
  memory_config?: IMemoryLibBaseInfo;
  fromShare?: boolean;
}

export interface IMCPService {
  server_id?: string;
  id?: string;
  icon?: string;
  name: string;
  name_en?: string;
  desc?: string;
  expand?: boolean;
  visibility?: string;
  config_status?: string;
  configs?: string;
  auth?: any;
  url?: string;
  type?: string;
  creator?: string;
  updated_on?: string;
  created_on?: string;
  creator_id?: string;
  tools?: {
    count: number;
    tools?: Tools[];
  };
  mcpInfo?: any;
}

export interface Tools {
  name?: string;
  desc?: string;
  title?: string;
  params_count?: number;
  input?: string;
  output?: string;
}

export interface dataProcessTools {
  name?: string;
  description?: string;
  title?: string;
  params_count?: number;
  input?: string;
  output?: string;
}

export interface UpWorkflowDetailType {
  name?: string;
  description?: string;
  status?: number;
  workflow_details?: IWorkflowDetail;
  inputParams?: IStartEndParam[];
  outputParams?: IStartEndParam[];
  childWorkflowIdList?: string[];
}

export interface IBaseQuery {
  offset: number;
  limit: number;
}

export interface IBaseQueryResp {
  count: number;
}

export interface IWorkflowListQueryResp extends IBaseQueryResp {
  workflow_list: IWorkflowInfo[];
}

export interface PublishedAgent {
  agent_id: string;
  name: string;
  icon: string;
  code: string;
  description: string;
  version_id: string;
  version_name: string;
}

export interface PublishedWorkflow {
  workflow_id: string;
  name: string;
  avatar: string;
  code: string;
  description: string;
  creator: string;
  type?: string;
  version_id?: string;
  version_name?: string;
  reference_workflows: string;
  disabled?: boolean;
  tip?: string;
  version_info_list?:[];
  version_options?:[];
  fromShare?: boolean;
}

export interface IPublishedWorkflowListQueryResp extends IBaseQueryResp {
  workflow_version_list: PublishedWorkflow[];
}

export interface PublishedMultiAgent {
  id: string;
  name: string;
  icon: string;
  description: string;
  creator: string;
  version_id: string;
  version_name: string;
}

export interface IPublishedAgentsListQueryResp extends IBaseQueryResp {
  agent_version_list: PublishedMultiAgent[];
}

export interface IWorkflowListQuery extends IBaseQuery {
  id?: string;
  name?: string;
  description?: string;
  author?: string;
  workflow_type?: string;
  code?: string;
  customize_node?: boolean;
}

export interface IModelParamInfo {
  min: number;
  max: number;
  step: number;
  mid: number;
  name: string;
  default: number;
}

export interface IApiSetting {
  params: {
    key: string;
    value: string;
    name?: string;
    isHidden?: boolean;
  }[];
  id: string;
  name: string;
  collapsed?: boolean;
  scope?: string;
}

export interface INodeInputs {
  model?: {
    config: {
      model: string;
      temperature: number;
      top_p: number;
      max_tokens: number;
      presence_penalty: number;
    };
    name: string;
  };
  parameters: {
    name: string;
    type: string;
    content: {
      source: string;
      name: string;
    };
  }[];
  prompt?: string;
}

export interface INodeMeta {
  id: string;
  name: string;
  type: string;
  group: string;
}

export interface INodeOutput {
  name: string;
  type: string;
}

export interface INodeData {
  id: string;
  inputs: INodeInputs;
  meta: INodeMeta;
  outputs: INodeOutput[];
}

export interface INameId {
  name: string;
  id: string;
}

export interface IRefInfo {
  refNodeId: string;
  refNodeName: string;
  outputs: IWorkflowField[];
  type: INodeType;
}

export interface IModel {
  model_name: string;
  model_version?: string;
  model_type: string;
  model_deployment_id: string;
  model?: string;
  model_id?:string;
  is_support_close_reasoning?: boolean;
  [key: string]: any;
}

export type WorkFlowType = 'chat' | 'task' | 'controller';

export interface ICreateWorkflow {
  name: string;
  code: string;
  description: string;
  avatar?: string;
  workflow_type?: WorkFlowType;
  type?: string;
}

export interface IPluginConfig {
  plugin_id: string;
  config: Record<string, string>;
}

export enum EViewType {
  CONFIG = 'CONFIG',
  CHAT_EMPTY = 'CHAT_EMPTY',
  CHAT_NOT_EMPTY = 'CHAT_NOT_EMPTY',
  CHAT = 'CHAT',
  LOG = 'LOG',
}

export interface IRefWorkflows {
  workflow_id: string;
  last_version_id: string;
  last_version_name: string;
  workflow_name?: string;
  valid?: boolean;
  resource_version?: string;
  app_type?: string;
  latest_version_app_sub_type?: string;
}

export interface IModeOfIntentNode {
  node_id: string;
  mode: 'normal' | 'advanced';
}

export interface IIntentGroupItem {
  intent_id: string;
  project_id: string;
  name: string;
  description?: string;
  branches_cnt: number;
  creator_id: string;
  merge_name?: string;
}

export interface IWorkflowApp {
  id: string;
  name: string;
  description: string;
  type: string;
  icon: string;
  inputs: IWorkflowAppField[];
  outputs: IWorkflowAppField[];
  prologue: string;
  suggest_queries: string[];
}

export interface IWorkflowAppField {
  name: string;
  front_name: string;
  front_content: string;
  type: string;
  description: string;
  required: boolean;
  source: string;
}

export enum EHalfmodalType {
  NODE_CONFIG = 'NODE_CONFIG', // 节点配置
  TEST_RUN = 'TEST_RUN', // 试运行
  INSIGHT = 'INSIGHT', // 调试
  SINGLE_TEST = 'SINGLE_TEST', // 单节点测试
  GLOBAL = 'GLOBAL', // 全局配置
  HISTORY = 'HISTORY', // 发布历史
  TRIGGER = 'TRIGGER', // 触发器配置
  DEFAULT = '', // 没打开任何半屏抽屉
}

interface ICardItem {
  isOverflow: boolean;
  question: string;
}

interface IBoundFlowItem extends IRefWorkflows {
  workflow_icon: string;
  desc: string;
}

interface IBoundToolItem {
  tool_id: string;
  tool_name: string;
  tool_icon: string;
  desc: string;
}

interface IBoundKBItem {
  knowledge_repo_id: string;
  knowledge_repo_name: string;
  knowledge_repo_icon: string;
  status: string;
  desc: string;
  name?: string;
}

export interface IFreeTrialQuota {
  limit: number;
  usage: number;
}

export interface IChatFlowAppDetail {
  title: string;
  icon: string;
  tags: string[];
  model_name: string;
  workflows: IBoundFlowItem[];
  tools: IBoundToolItem[];
  creator: string;
  description: string;
  knowledge_repos: IBoundKBItem[];
  prologue?: string;
  cardList?: ICardItem[];
  published_on?: string;
  publish_time?: string;
  free_trial_quota?: IFreeTrialQuota;
  memoryLibId?: string;
}

export enum DragMode {
  HAND = 'hand', // 节点配置
  POINTER = 'pointer', // 试运行
}

export interface WorkflowImportQuery {
  type: 'Dify'
}

export interface WorkflowImportReq {

}
