import { IModel } from '@routes/agent-center/app-flow/app-flow.types';
import { KbItem } from '@routes/knowledge-center/knowledge-base.interface';
import { AdvancedRuleNode } from '@routes/knowledge-center/knowledge.types';

export const NoOutputsNodeTypes: INodeType[] = [
  'End',
  'Branch',
  'Message',
  'SetVariable',
  'LoopInput',
  'LoopOutput',
  'Controller',
  'StreamTransform',
];
export const NoInputsNodeTypes: INodeType[] = [
  'Start',
  'LoopInput',
  'LoopOutput',
];
export const LLM_LIKE_NODES: INodeType[] = [
  'LLM',
  'IntentDetection',
  'Questioner',
  'LTM',
  'Agent',
  'ComplexIntentDetection',
  'ParamExtraction',
];
export const INTERACTION_NODES: INodeType[] = ['Input', 'Questioner', 'QA', 'Loop', 'Agent'];

export type ValueLabelType = 'String' | 'Integer' | 'Number';
export const CANT_EMBEDDING_NODES = ['Start', 'End', 'Loop'];
export const UnDeletableNodeTypes = [
  'Start',
  'End',
  'IntentDetectionContainer',
  'LoopInput',
  'LoopOutput',
];

export const ExchangeNoOutputType = [
  ...NoOutputsNodeTypes,
  'Input',
];
/** 转换成目标节点时，不携带输入输出的类型 */
export const ExchangeUnSaveTypes: INodeType[] = [
  'SetVariable',
  'Aggregation',
  'KnowledgeRepo',
];

export const UnCopyNodeTypes = ['Start', 'End', 'LoopInput', 'LoopOutput'];
export const BRANCH_ARRAY = [
  `elseIf-1`,
  `elseIf-2`,
  `elseIf-3`,
  `elseIf-4`,
  `elseIf-5`,
  `elseIf-6`,
  `elseIf-7`,
  `elseIf-8`,
  `elseIf-9`,
  `elseIf-10`,
  `elseIf-11`,
  `elseIf-12`,
  `elseIf-13`,
  `elseIf-14`,
  `elseIf-15`,
  `elseIf-16`,
  `elseIf-17`,
  `elseIf-18`,
];
export const userDrivenNodeTypes = ['Questioner', 'Input', 'Agent', 'QA'];
// 具有版本管理功能的原子资源节点。意图动作配置和agent节点也支持版本升级功能，但它们属于绑定了多个原子资源节点。
export const versionedResNodes = [
  'Workflow',
  'Plugin',
  'Card',
  'SubController',
];
// 没有版本管理功能的原子资源节点。
export const nonVersionedResNodes = ['Mcp'];
export type ValueType = string | number;

export interface IRefContent {
  name: string;
  source: string;
}

export interface IParameter {
  name: string;
  type: ValueLabelType | 'ref';
  content: ValueType | IRefContent;
}

export interface IInputParameter {
  name: string;
  type: ValueLabelType | 'ref';
  description?: string;
  value: ValueType;
}

export interface IOutputParameter {
  name: string;
  type: string;
  description: string;
  required?: boolean;
  value?: string;
}

export interface IOutputBase {
  description: string;
  name: string;
  type: string;
}

export interface IQuestionKeywordParameter {
  name: string;
  questionKeyWord: string;
  case: string;
  description: string;
}

export type INodeType =
  | 'Start'
  | 'End'
  | 'LLM'
  | 'Code'
  | 'Plugin'
  | 'Branch'
  | 'Workflow'
  | 'TaskFlow'
  | 'IntentDetection'
  | 'KnowledgeRepo'
  | 'Message'
  | 'Questioner'
  | 'Aggregation'
  | 'Controller'
  | 'Input'
  | 'Loop'
  | 'SetVariable'
  | 'LoopInput'
  | 'LoopOutput'
  | 'System'
  | 'Http'
  | 'Mcp'
  | 'Agent'
  | 'MemoVal'
  | 'IntentDetectionContainer'
  | 'LTM'
  | 'QA'
  | 'Sql'
  | 'ComplexIntentDetection'
  | 'DataAcquisition'
  | 'DataProcess'
  | 'Card'
  | 'Exception'
  | 'environment'
  | 'StructuredMessagesException'
  | 'env'
  | 'SubController'
  | 'SubWorkflow'
  | 'ParamExtraction'
  | 'DataQuery'
  | 'DataSynthesis'
  | 'Empty'
  | 'Comment'
  | 'StreamTransform';

export interface INodeBase {
  id: string;
  name: string;
  type: INodeType;
  configs?: {
    [propName: string]: any;
  };
  inputs?:any;
}

export type IWorkflowFieldType =
  | 'string'
  | 'ref'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'array'
  | 'object'
  | 'array<string>'
  | 'array<number>'
  | 'array<integer>'
  | 'array<boolean>'
  | 'array<object>'
  | 'file/default'
  | 'file/doc'
  | 'file/image'
  | 'file/video'
  | 'file/txt'
  | 'file/ppt'
  | 'file/excel'
  | 'array<file/default>'
  | 'array<file/doc>'
  | 'array<file/image>'
  | 'array<file/video>'
  | 'array<file/txt>'
  | 'array<file/ppt>'
  | 'array<file/excel>'
  | 'any';

export interface IParamRef extends IRefContentType {
  name: string;
  type: IWorkflowFieldType | INodeType;
  schema?: IWorkflowFieldSchema;
  isTop?: boolean;
  children?: IParamRef[];
  expanded?: boolean;
  checked?: boolean;

  [key: string]: any;
}

export interface IRefContentType {
  ref_node_id: string;
  ref_var_name: string;
  source: IParamSource;
}

export interface VarRefContentType {
  name?: string;
  variable_key: string;
  description: string;
  default_value?: string;
}

export type FieldValueType =
  | 'generated'
  | 'ref'
  | 'literal'
  | 'nested'
  | 'operator'
  | 'input_ref';
export type FieldValueContent =
  | null
  | IRefContentType
  | VarRefContentType
  | string
  | IParamRef[]
  | number
  | boolean;

export interface IWorkflowFieldValue {
  type: FieldValueType;

  /**
   * 取值结构如下：
   * type：generated， content=null
   * type：ref ，content为对象
   *    ref_node_id：引用节点
   *    ref_var_name：引用变量名
   * type：literal，content为字符
   */
  content: FieldValueContent;

  // 字段值提示或默认值
  hint: string;

  default?: string;
  display?: string;
  operator?: string;
}

export type IParamSource =
  | 'system'
  | 'user'
  | 'pre_defined'
  | 'environment'
  | '';

export type IWorkflowFieldSchema = IWorkflowField[] | IWorkflowField;

export interface IWorkflowField {
  name?: string;
  type?: IWorkflowFieldType;
  description?: string;
  options?: any[];
  // 是否必填，一般inputs必填，outputs不必填
  required?: boolean;
  showRequired?: boolean;
  field_type?: string;
  schema?: IWorkflowFieldSchema;
  value?: IWorkflowFieldValue;
  source?: IParamSource;
  refs?: IParamRef[];
  reflection?: boolean;
  isDisabled?: boolean;
  aging_level?: 'session' | 'permanent';
  storage_method?: 'auto' | 'assignment';
  location?: string;
  subType?: string[];
  visibility?: boolean;
  refWithout?: boolean;
  isTemp?: string;
  _refSelectedKey?: string | null;
}

export type IWFViewParentType = IWorkflowFieldType | 'none';

export type IWFView = {
  key?: string;
  parentType?: IWFViewParentType;
  children?: IWFView[];
  depth?: number;
  expanded?: boolean;
  visibility?: boolean;
  schema?: IWorkflowFieldSchema;
} & Omit<IWorkflowField, 'schema'>;

export type IWFViewWithMultiType = {
  key?: string;
  parentType?: IWFViewParentType;
  children?: IWFViewWithMultiType[];
  depth?: number;
  expanded?: boolean;
  type: string[];
} & Omit<IWorkflowField, 'schema' | 'type'>;

export interface IStartNode extends INodeBase {
  outputs: IWorkflowField[];

  configs?: {
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IChatStartNode extends IStartNode {
  modelUri: string;
  isError: boolean;
  isEmpty: boolean;
}

export interface IEndNode extends INodeBase {
  inputs: IWorkflowField[];

  /** system responseContent */
  outputs: IWorkflowField[];

  configs: {
    response_template: string;

    /** true */
    is_stream_out: string;

    /** directResponse */
    response_mode: string;

    struct_output_template?: string;

    descriptionText?: string;

    isDefaultName?: boolean;
  };
}

export interface ILLMConfig {
  model_name?: string;
  model_type?: string;
  model_id?: string;
  id?: string;
  model_deployment_id?: string;
  model?: string;
  api_type?: string;
}

export interface IExceptionProcess {
  timeout: number;
  retry_times: number;
  handle_type: string;
  default_outputs: object;
}

export interface ILLMNode extends INodeBase {
  inputs: IWorkflowField[];

  /** rawOutput system */
  outputs: IWorkflowField[];

  configs: {
    enable_history: boolean;
    template_content: string;
    model: ILLMConfig;
    temperature: number;
    top_p: number;
    response_format: 'text' | 'json' | 'markdown';
    format_instruction: string;
    system_prompt: string;
    history_size: number;
    max_tokens: number;
    frequency_penalty?: number;
    stream?: boolean;
    vision?: string[];
    safety_barrier?: boolean;
    exception_process?: IExceptionProcess;
    enable_thinking?: boolean; //模型是否输出深度思考
    enable_memory?: boolean; // 是否启用记忆
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IProcessingWorkflow {
  name: string;
  description: string;
  inputs: IWorkflowField[]; // 领域对象处理工作流输入支持引用节点输入变量（包括领域对象输入，上下文变量，用户输入，其中pre_defined变量支持更改）
  outputs: IWorkflowField[];
  version_name: string;
  id: string;
  version_id: string;
  entry_condition: IBranchConfigs; // 领域对象处理工作流进入条件判断
  memory?: IWorkflowField[];
  isNewSelected?: boolean; //前端使用判断是否为重新选择的，组装接口数据删除
  showUpdate?: boolean; //是否显示更新按钮
  updateFlowTip?: boolean; //更新按钮tip
  canConfigure?: boolean; //是否加载完详情可以点击配置按钮
}

export interface IExtensionWorkflow {
  name: string;
  description: string;
  execution_timing: 'BEFORE_ENTRY' | 'AFTER_QUIT' | 'AFTER_EXTRACTION'; // 执行时机，预处理、退出前、参数提取后
  inputs: IWorkflowField[]; // 领域对象处理工作流输入支持引用节点输入变量（包括领域对象输入，上下文变量，用户输入，其中pre_defined变量支持更改）
  outputs: IWorkflowField[];
  version_name: string;
  id: string;
  version_id: string;
  entry_condition: IBranchConfigs; // 拓展工作流进入条件判断
  memory?: IWorkflowField[];
  isNewSelected?: boolean; //前端使用判断是否为重新选择的，组装接口数据删除
  showUpdate?: boolean; //是否显示更新按钮
  updateFlowTip?: boolean; //更新按钮tip
  canConfigure?: boolean; //是否加载完详情可以点击配置按钮
}

export interface IDomainObject {
  name: string; // 领域对象ID对应
  description: string;
  processing_workflows: IProcessingWorkflow[]; // 领域对象处理工作流定义
}

export interface IExceptionConfig {
  max_iterations: number;
  exception_condition: IBranchConfigs;
}

export interface IParamExtractionNode extends INodeBase {
  inputs: IWorkflowField[];

  /** rawOutput system */
  outputs: IWorkflowField[];

  configs: {
    domain_objects?: IDomainObject[];
    model?: IModel;
    prompt?: string;
    enable_intent_break?: boolean; // 允许意图跳出
    intent_break_prompt?: string;
    entry_condition?: IBranchConfigs; // 模型提取参数进入条件判断
    extension_workflows?: IExtensionWorkflow[]; // 拓展工作流
    break_condition?: IBranchConfigs; // 节点跳出条件
    description?: string; //备注信息
    exception_config?: IExceptionConfig; //异常配置
    temperature?: number;
    top_p?: number;
    history_size?: number;
    max_tokens?: number;
    frequency_penalty?: number;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export type IIntentHandler = string | IWorkflowNode;

export type FlowAction = 'Continue' | 'Terminal' | 'WaitUserInput';

export interface IGlobalIntent {
  id: string;
  name: string;
  description: string;
  handler_type: 'Workflow' | 'Text';
  handler: IIntentHandler;
  termination?: boolean;
  action?: FlowAction;
}

export type ControllerSubFlowType =
  | 'Start'
  | 'End'
  | 'Normal'
  | 'Default'
  | 'Intent'
  | 'IntentIdentification';

export interface IControllerFlow {
  node_id?: string;
  name: string;
  id: string;
  type: ControllerSubFlowType;
  flowType?: string;
  action?: FlowAction;

  // 视图层需要，接口不需要这些参数
  disabled?: boolean;
  description?: string;
  version?: string;
  inputs?: IWorkflowField[];
  outputs?: IWorkflowField[];
  configs?: IWorkflowConfigs;
  version_id?: string;
  version_name?: string;
  code?: string;
  update?: any;
  fromShare?: boolean;
}

export interface IControllerAgents {
  node_id?: string;
  name: string;
  id: string;
  mode?: string;

  // 视图层需要，接口不需要这些参数
  disabled?: boolean;
  description?: string;
  version?: string;
  inputs?: IWorkflowField[];
  outputs?: IWorkflowField[];
  configs?: IWorkflowConfigs;
  version_id?: string;
  version_name?: string;
  code?: string;
}

export interface IControllerNode extends INodeBase {
  configs: {
    name?: string;
    model: ILLMConfig;
    temperature: number;
    top_p: number;
    prompt: string;
    max_iteration: number;
    chat_history_max_turn: number;
    workflows: IControllerFlow[];
    agents?: IControllerAgents[];
    global_intents: IGlobalIntent[];
    description?: string;
    id?: string;
    version_id?: string;
    version_name?: string;
    intent?: any;
    fromShare?: boolean;
    valid?: boolean;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  showUpdatedIcon?: boolean;
}

export interface IWorkflowConfigs {
  id: string;
  name: string;
  description: string;
  version_id: string;
  version_name: string;
  code: string;
  type?: string;
  exception_process?: IExceptionProcess;
  intent?: any;
  fromShare?: boolean;
  valid?: boolean;
  isDefaultName?: boolean;
}

export interface ISingleAgentConfigs extends IWorkflowConfigs {
  mode?: string;
  model?: {
    id?: string;
    model_deployment_id?: string;
    model_name?: string;
    model_type?: string;
  };
  intent?: {
    name: string;
    description: string;
  };
}

export interface IWorkflowNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: IWorkflowConfigs;
  parent_node_type?: string;
}

export interface ISingleAgentNode extends INodeBase {
  configs: ISingleAgentConfigs;
  parent_node_type?: string;
}


export interface IQANode extends INodeBase {
  inputs?: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    qaStrategy: string;
    options: string[];
    needReply?: boolean;
    struct_output_template?: string;
    enable_history?: boolean;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface ICardNode extends INodeBase {
  inputs?: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    [propKey: string]: any;
    isDefaultName?: boolean;
  };
}

export interface ISqlNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    id: string;
    name: string;
    sql: string;
    type?: string;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IDataQueryNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    id: string;
    name: string;
    sql: string;
    type?: string;
    table_name?: string;
    output_column?: Array<any>;
    select_query?: any;
    limit?: Number;
    orders?: Array<any>;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export type QuesRailsAction =
  | 'date_time_format'
  | 'number_range_validate'
  | 'length_limit_validate'
  | 'enum_legality_validate'
  | 'common_data_format_check';

export interface IQuesValidator {
  type: QuesRailsAction;
  params: string[];
}

export interface IQuesRailsActionConfig {
  action: QuesRailsAction;
  action_extra_args: {
    [key: string]: string;
  };
}

export interface IQuesExecution {
  action: QuesRailsAction;
}

export interface IQuesRewriteChain {
  type: 'rewrite_api' | 'rewrite_time_info_in_query';
  index: number;
  enabled: boolean;
  args: {
    url?: string;
    [key: string]: any;
  };
}

export interface IQuesCommonConfigs {
  model: ILLMConfig;
  mode: string;
  temperature: number;
  top_p: number;
  extra_prompt_for_fields_extraction: string;
  question_content: string;
  with_chat_history: boolean;
  extract_fields_from_response: boolean;
  max_response: number;
  rewrite_chain: IQuesRewriteChain[];
  example_content: string;
  allow_node_break: boolean;
  allow_node_confirm: boolean;
  template_anthropomorphic: boolean;
  auto_ask_template: string;
  enum_visible: boolean;
  max_tokens: number;
  enable_memory?: boolean;
  descriptionText?: string;
  isDefaultName?: boolean;
}

export interface IQuesWorkflowField extends IWorkflowField {
  cn_name: string;
  validator: IQuesValidator[];
  reflection: boolean;
}

export interface IQuestionerNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IQuesWorkflowField[];
  configs: IQuesCommonConfigs;
}

export interface ICodeNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    code: string;
    exec_env: string;
    enable_sandbox?: boolean;
    fg_id?: string;
    exception_process?: IExceptionProcess;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IFlowNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs?: {
    id: string;
    name: string;
    version_id: string;
    version_name: string;
    plugins: {
      id: string;
      version: string;
    }[];
    valid?: boolean;
    original_info?: IToolOriginalInfo;
    exception_process?: null;
    fromShare?: boolean;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  isAction?: boolean;
}

export interface IMcpNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs?: {
    id?: string;
    name?: string;
    name_en?: string;
    tool_name?: string;
    valid?: boolean;
    original_info?: IToolOriginalInfo;
    dataConfig?: any;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  isAction?: boolean;
}

export interface IToolOriginalInfo {
  name?: string;
  name_en?: string;
  description?: string;
  type?: 'custom' | 'inner';
  valid?: boolean;
  version_id?: string;
}

export interface IPluginNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    id: string;
    tool_id: string;
    type: string;
    exception_enable?: boolean;
    exception_suppression?: string;
    streaming?: boolean;
    original_info?: IToolOriginalInfo;
    version_id?: string;
    name?: string;
    valid?: boolean;
    output_schema?: string;
    exception_process?: IExceptionProcess;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  isAction?: boolean;
}

export type LoopType = 'arrayLoop' | 'numLoop';

export interface ILoopNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    loop_type: LoopType;
    loop_body: string[];
    break_condition?: IBranchConfigs;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface ISetVariableNode extends INodeBase {
  inputs: IWorkflowField[];
  configs: {
    settings: {
      left: IWorkflowField;
      right: IWorkflowField;
    }[];
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IAggregationGroups {
  [key: string]: {
    name: string;
    index: number;
  }[];
}

export interface IAggregationNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    groups: IAggregationGroups;
    mode: 'first-non-null';
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IInputNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: Record<string, any>;
}

export interface ILTMNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    model: ILLMConfig;
    temperature: number;
    top_p: number;
    top_k: number;
    recall_threshold: number;
    output_mode: 'summary' | 'variable';
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export type IBranchOp =
  | 'eq'
  | 'not_eq'
  | 'contain'
  | 'not_contain'
  | 'longer_than'
  | 'longer_than_or_eq'
  | 'shorter_than'
  | 'shorter_than_or_eq'
  | 'is_empty'
  | 'is_not_empty'
  | 'eq_true'
  | 'eq_false';

export interface IBranchCondition {
  operator: IBranchOp;
  left: IWorkflowField;
  right: IWorkflowField;
}

export interface IBranchConfigs {
  logic: 'and' | 'or';
  conditions: IBranchCondition[];
  descriptionText?: string;
  isDefaultName?: boolean;
}

export interface IBranch {
  id: string;
  configs?: IBranchConfigs;
  branch?: string;
  expression?: string;
}

export interface IBranchNode extends INodeBase {
  branches: IBranch[];
  configs?: {
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  isTemp?: boolean;
}

export interface IIntentBranch {
  id: string;
  configs: {
    category: string;
  };
}

export interface IIntentGroupConfig {
  id: string;
  name: string;
  branches_cnt?: number;
  intent_id?: string; // 视图层需要，接口不需要。作为选择框的idKey
}

export interface IIntentContainerBranch {
  id: string;
  configs: {
    category: string;
    description: string;
    index: string;
    intent_id: string;
    branch_id: string;
    workflow_id: string;
    workflow_name: string;
    workflow_version_id: string;
    workflow_version_name: string;
  };
}

export interface IIntentNode extends INodeBase {
  inputs: IWorkflowField[];

  /** result system */
  outputs: IWorkflowField[];

  branches: IIntentBranch[];
  configs: {
    prompt: string;
    llm: {
      model: ILLMConfig;
      temperature: number;
      top_p: number;
      max_tokens: number;
    };
    chat_history_max_turn: number;
    enable_knowledge?: boolean;
    recall_threshold?: number;
    repos?: IKbConf[];
    intent?: IIntentGroupConfig;
    exception_process?: IExceptionProcess;
    enable_memory?: boolean; // 意图节点启用记忆
    descriptionText?: string;
    isDefaultName?: boolean;
    common_tags?: AdvancedRuleNode; // 知识库tag过滤
    advanced_tags?: AdvancedRuleNode; // 知识库tag过滤
  };
}

export interface IIntentContainerNode extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  branches: IIntentContainerBranch[];
  configs: {
    groups: {
      response_content: IWorkflowField[];
    };
    mode: 'first-non-null';
    exception_process?: IExceptionProcess;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
  intentId?: string;
}

export interface IMessageNode extends INodeBase {
  inputs: IWorkflowField[];

  /**
   *  内容为定值，且不在页面上展示, system
   *  {
   *    "name": "results",
   *    "type": "string",
   *    "description": "",
   *    "required": false
   *  }
   */
  outputs: IWorkflowField[];

  configs: {
    template: string;
    struct_output_template?: string;
    descriptionText?: string;
    isDefaultName?: boolean;
    enable_history?: boolean;
  };
}

export interface IStreamTransformNode extends INodeBase {
  inputs: IWorkflowField[];

  /**
   *  内容为定值，且不在页面上展示, system
   *  {
   *    "name": "results",
   *    "type": "string",
   *    "description": "",
   *    "required": false
   *  }
   */
  outputs: IWorkflowField[];

  configs: {
    concat?: Array<any>;
    transformer?: {
      frame_template?: string;
    };
  };
}

export interface IExceptionNode extends INodeBase {
  inputs: IWorkflowField[];

  /**
   *  内容为定值，且不在页面上展示, system
   *  {
   *    "name": "results",
   *    "type": "string",
   *    "description": "",
   *    "required": false
   *  }
   */
  outputs: IWorkflowField[];

  configs: {
    template: string;
    descriptionText?: string;
    isDefaultName?: boolean;
  };
}

export interface IKbConf extends KbItem{
  metadata?: Record<string, any>;
}

export interface IKnowledgeRepo extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: {
    repos: IKbConf[];
    top_k: number;
    recall_threshold: number;
    search_mode: string;
    faq_threshold: number;
    need_extras_faq_search: boolean;
    show_source?: boolean;
    retrieve_image?: boolean;
    extra_params?: Array<{ key: string; value: string }>;
    descriptionText?: string;
    common_tags?: AdvancedRuleNode;
    advanced_tags?: AdvancedRuleNode;
    isDefaultName?: boolean;
  };
}

export interface IServAuthKV {
  target_name: string;
  auth_key: string;
}

export interface IHttpConfig {
  method: 'POST' | 'GET';
  endpoint: string; // endpoint不支持引用
  path: string; // 支持引用
  request_type: 'JSON' | 'NONE';
  request_body: string;
  auth_info: {
    scope?: string;
    domain?: string;
    auth_keys?: IServAuthKV[];
  };
  exception_enable: boolean;
  exception_suppression: string;
  descriptionText?: string;
  isDefaultName?: boolean;
}

export interface IHttpRepo extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: IHttpConfig;
}

export interface IAgentConfig {
  model: ILLMConfig;
  system_prompt: string;
  max_iteration: number; // 最大工具调用轮次
  temperature: number;
  top_p: number;
  max_tokens: number;
  plugins: {
    id: string;
    name: string;
    description: string;
    version_id?: string;
  }[];
  descriptionText?: string;
  isDefaultName?: boolean;
}

export interface IAgentRepo extends INodeBase {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
  configs: IAgentConfig;
}

export interface ICommentNode extends INodeBase{
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export type MultiPortNode = IIntentNode | IBranchNode;

export type NodeInfo =
  | IStartNode
  | IEndNode
  | ILLMNode
  | IPluginNode
  | ICardNode
  | IBranchNode
  | IQuestionerNode
  | ICodeNode
  | IIntentNode
  | IMessageNode
  | IAggregationNode
  | IInputNode
  | ILoopNode
  | IFlowNode
  | IMcpNode
  | ISetVariableNode
  | IControllerNode
  | IWorkflowNode
  | IIntentContainerNode
  | IQANode
  | ISqlNode
  | IDataQueryNode
  | ISingleAgentNode
  | ICommentNode;

export type HasOutputsNode =
  | IStartNode
  | ILLMNode
  | IPluginNode
  | IQuestionerNode
  | ICodeNode;

export type HasInputsNode =
  | IEndNode
  | ILLMNode
  | IPluginNode
  | IQuestionerNode
  | ICodeNode
  | IIntentNode
  | IKnowledgeRepo
  | IMessageNode;

export type IsolatedTestableNode =
  | ILLMNode
  | IPluginNode
  | IQuestionerNode
  | ICodeNode
  | IIntentNode;

export type MidNode = ILLMNode | IPluginNode;

export interface IGraphNode {
  id: string;
  x: string;
  y: string;
  shape:
    | 'flow-start'
    | 'flow-end'
    | 'flow-llm'
    | 'flow-code'
    | 'flow-workflow'
    | 'flow-branch'
    | 'flow-api'
    | 'flow-intent';
  data: NodeInfo;
}

export interface IViewNodeData {
  ngArguments: {
    nodeInfo: NodeInfo;
  };
}

export type CopyType = 'input' | 'output' | 'modelInput' | 'modelOutput' | '';

export interface IContentReview {
  enabled: boolean;
  filter: {
    keywords: string;
  };
  replace: IContentReviewReplaceItem[];
  reply: IContentReviewReplyItem[];
}

export interface IContentReviewReplaceItem {
  keywords: string;
  replace: string;
}

export interface IContentReviewReplyItem {
  keywords: string;
  input_enable: boolean;
  input_text: string;
  output_enable: boolean;
  output_text: string;
}
