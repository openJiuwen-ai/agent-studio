import { I18nNamespace } from '@i18n';
import i18next from 'i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { IMcpNode, IParamSource, IWorkflowField } from './node.type';

export const ADD_NODES_MODAL_WIDTH = 264;
export const ADD_NODES_MODAL_HEIGHT = 741;
export const ADD_NODES_MODAL_HEIGHT_TASK = 639;
export const ADD_BETWEEN_NODE_DISTANCE = 125; // 点击中间添加节点，距离左侧距离

export const DEFAULT_FLOW_SEND_MSG_MAX_LEN = 100000;

export const FLOW_COLORS = {
  defaultPort: '#90b5e8',
  portStroke: '#fff',
  hoverPort: '#1476ff',
  defaultLine: '#B8C3D2',
  connected: '#B8C3D2',
  edgeActive: '#1476ff',
};

export const PORT_STROKE_WIDTH = 2;
export const PORT_RADIUS = 5;
export const PORT_HOVER_NODE_RADIUS = 7;
export const PORT_HOVER_PORT_RADIUS = 10;
export const PORT_CONNECTED_ATTR = 'data-connected';
export const PORT_CONNECTED = {
  connected: '1',
  defaultPort: '0',
};

export const NODE_HEIGHT_OFFSET = 2;

export const NODE_SIZE = {
  width: 380,
  height: 45,
  loopIO: 53,
  onePortHeight: 22,
};

export const FLOW_OBJ_MAX_PROPS = 10;

export const MULTI_PORT_NODE = ['IntentDetection', 'Branch'];

export const getLLMLikeOutputParamTypes = () => [
  { label: 'String', value: 'string' },
  { label: 'Integer', value: 'integer' },
  { label: 'Number', value: 'number' },
  { label: 'Boolean', value: 'boolean' },
];

export const getInputParamTypes = () => [
  { label: 'String', value: 'string', isLeaf: true },
  {
    label: 'File',
    value: 'file',
    children: [
      { label: 'Default', value: 'default', isLeaf: true },
      { label: 'Doc', value: 'doc', isLeaf: true },
      { label: 'Txt', value: 'txt', isLeaf: true },
      { label: 'Excel', value: 'excel', isLeaf: true },
      { label: 'PPT', value: 'ppt', isLeaf: true },
      { label: 'Image', value: 'image', isLeaf: true },
      { label: 'Audio', value: 'audio', isLeaf: true },
      { label: 'Video', value: 'video', isLeaf: true },
    ],
  },
  { label: 'Integer', value: 'integer', isLeaf: true },
  { label: 'Number', value: 'number', isLeaf: true },
  { label: 'Boolean', value: 'boolean', isLeaf: true },
  { label: 'Object', value: 'object', isLeaf: true },
  { label: 'Array<String>', value: 'array<string>', isLeaf: true },
  { label: 'Array<Number>', value: 'array<number>', isLeaf: true },
  { label: 'Array<Integer>', value: 'array<integer>', isLeaf: true },
  { label: 'Array<Boolean>', value: 'array<boolean>', isLeaf: true },
  { label: 'Array<Object>', value: 'array<object>', isLeaf: true },
  {
    label: 'Array<File>',
    value: 'array<file>',
    children: [
      { label: 'Default', value: 'default', isLeaf: true },
      { label: 'Doc', value: 'doc', isLeaf: true },
      { label: 'Txt', value: 'txt', isLeaf: true },
      { label: 'Excel', value: 'excel', isLeaf: true },
      { label: 'PPT', value: 'ppt', isLeaf: true },
      { label: 'Image', value: 'image', isLeaf: true },
      { label: 'Audio', value: 'audio', isLeaf: true },
      { label: 'Video', value: 'video', isLeaf: true },
    ],
  },
];

export const getOutputParamTypes = () => [
  { label: 'String', value: 'string', isLeaf: true },
  { label: 'Integer', value: 'integer', isLeaf: true },
  { label: 'Number', value: 'number', isLeaf: true },
  { label: 'Boolean', value: 'boolean', isLeaf: true },
  { label: 'Object', value: 'object', isLeaf: true },
  { label: 'Array<String>', value: 'array<string>', isLeaf: true },
  { label: 'Array<Number>', value: 'array<number>', isLeaf: true },
  { label: 'Array<Integer>', value: 'array<integer>', isLeaf: true },
  { label: 'Array<Boolean>', value: 'array<boolean>', isLeaf: true },
  { label: 'Array<Object>', value: 'array<object>', isLeaf: true },
];

export const getNoneObjOutputParamTypes = () => [
  { label: 'String', value: 'string', isLeaf: true },
  { label: 'Integer', value: 'integer', isLeaf: true },
  { label: 'Number', value: 'number', isLeaf: true },
  { label: 'Boolean', value: 'boolean', isLeaf: true },
  { label: 'Object', value: 'object', disabled: true, isLeaf: true },
  { label: 'Array<String>', value: 'array<string>', disabled: true, isLeaf: true },
  { label: 'Array<Number>', value: 'array<number>', disabled: true, isLeaf: true },
  { label: 'Array<Integer>', value: 'array<integer>', disabled: true, isLeaf: true },
  { label: 'Array<Boolean>', value: 'array<boolean>', disabled: true, isLeaf: true },
  { label: 'Array<Object>', value: 'array<object>', disabled: true, isLeaf: true },
];

export const getInitInputParamConfig = (source: IParamSource = 'user'): IWorkflowField => {
  return {
    name: '',
    description: '',
    required: true,
    value: {
      type: 'literal',
      content: '',
      hint: '',
    },
    source,
  };
};

export const getInitInputParamRefConfig = (source: IParamSource = 'user'): IWorkflowField => {
  return {
    name: '',
    description: '',
    required: true,
    value: {
      type: 'ref',
      content: '',
      hint: '',
    },
    source,
  };
};

export const getInitGeneratedInputParamConfig = (source: IParamSource = 'user'): IWorkflowField => {
  return {
    name: '',
    description: '',
    required: true,
    value: {
      type: 'generated',
      content: '',
      hint: '',
    },
    source,
  };
};

export const getInitOutputParamConfig = (): IWorkflowField => {
  return {
    name: '',
    type: 'string',
    description: '',
    required: true,
    reflection: false,
    value: {
      type: 'generated',
      content: null,
      hint: '',
      default: '',
    },
    source: 'user',
  };
};

export const getInitRefParamConfig = (): IWorkflowField => {
  return {
    name: '',
    description: '',
    required: true,
    reflection: false,
    value: {
      type: 'ref',
      content: '',
      hint: '',
    },
    source: 'user',
  };
};

export const NODE_NAMES = [
  'llm',
  'questioner',
  'taskflow',
  'plugin',
  'code',
  'childflow',
  'start',
  'end',
  'branch',
  'intentdetection',
  'message',
  'aggregation',
  'controller',
  'input',
  'loop',
  'setvariable',
  'ltm',
  'loopstart',
  'loopend',
  'intentdetectioncontainer',
];

export const WORKFLOW_SVGS = {
  Start: cdnAssetUrl('assets/agent-center/flow/Start.svg'),
  LoopInput: cdnAssetUrl('assets/agent-center/flow/Start.svg'),
  LoopOutput: cdnAssetUrl('assets/agent-center/flow/End.svg'),
  System: cdnAssetUrl('assets/agent-center/flow/System.svg'),
  MemoVal: cdnAssetUrl('assets/agent-center/flow/MemoVal.svg'),
  LLM: cdnAssetUrl('assets/agent-center/flow/LLM.svg'),
  Controller: cdnAssetUrl('assets/agent-center/flow/Controller.svg'),
  KnowledgeRepo: cdnAssetUrl('assets/agent-center/flow/KnowledgeRepo.svg'),
  Code: cdnAssetUrl('assets/agent-center/flow/Code.svg'),
  Branch: cdnAssetUrl('assets/agent-center/flow/Branch.svg'),
  IntentDetection: cdnAssetUrl('assets/agent-center/flow/Intent.svg'),
  IntentDetectionContainer: cdnAssetUrl('assets/agent-center/flow/Intent.svg'),
  Questioner: cdnAssetUrl('assets/agent-center/flow/Questioner.svg'),
  Plugin: cdnAssetUrl('assets/agent-center/flow/Plugin.svg'),
  Workflow: cdnAssetUrl('assets/agent-center/flow/ChildFlow.svg'),
  WorkflowMulti: cdnAssetUrl('assets/agent-center/flow/Workflow.svg'),
  SingleAgent: cdnAssetUrl('assets/agent-center/flow/SingleAgent.svg'),
  Mcp: cdnAssetUrl('assets/agent-center/flow/Mcp.svg'),
  End: cdnAssetUrl('assets/agent-center/flow/End.svg'),
  Message: cdnAssetUrl('assets/agent-center/flow/message.svg'),
  StreamTransform: cdnAssetUrl('assets/agent-center/flow/stream-transform.svg'),
  TaskFlow: cdnAssetUrl('assets/agent-center/flow/Task.svg'),
  Aggregation: cdnAssetUrl('assets/agent-center/flow/Aggregation.svg'),
  Input: cdnAssetUrl('assets/agent-center/flow/Input.svg'),
  Http: cdnAssetUrl('assets/agent-center/flow/Http.svg'),
  Agent: cdnAssetUrl('assets/agent-center/flow/Agent.svg'),
  Loop: cdnAssetUrl('assets/agent-center/flow/Loop.svg'),
  SetVariable: cdnAssetUrl('assets/agent-center/flow/SetVariable.svg'),
  LTM: cdnAssetUrl('assets/agent-center/flow/LTM.svg'),
  MultiAgent: cdnAssetUrl('assets/agent-center/flow/MultiAgent.svg'),
  QA: cdnAssetUrl('assets/agent-center/flow/QA.svg'),
  Sql: cdnAssetUrl('assets/agent-center/flow/Sql.svg'),
  Empty: cdnAssetUrl('assets/agent-center/flow/Empty.svg'),
  ValidateAlert: cdnAssetUrl('assets/agent-center/icons/validate-alert.svg'),
  Loading: cdnAssetUrl('assets/agent-center/flow/call-node-loading.svg'),
  Succeeded: cdnAssetUrl('assets/agent-center/flow/call-node-success.svg'),
  Failed: cdnAssetUrl('assets/agent-center/flow/call-node-error.svg'),
  ComplexIntentDetection: cdnAssetUrl('assets/agent-center/flow/Controller.svg'),
  DataAcquisition: cdnAssetUrl('assets/agent-center/flow/DataObtain.svg'),
  DataProcess: cdnAssetUrl('assets/agent-center/flow/DataProcess.svg'),
  Card: cdnAssetUrl('assets/agent-center/flow/Card.svg'),
  StructuredMessagesException: cdnAssetUrl('assets/agent-center/flow/Exception.svg'),
  environment: cdnAssetUrl('assets/agent-center/flow/env.svg'),
  exception: cdnAssetUrl('assets/agent-center/flow/exception_triangle.svg'),
  ParamExtraction: cdnAssetUrl('assets/agent-center/flow/param-extraction.svg'),
  DataQuery: cdnAssetUrl('assets/agent-center/flow/data-query.svg'),
  DataSynthesis: cdnAssetUrl('assets/agent-center/flow/DataSynthesis.svg'),
  Comment: cdnAssetUrl('assets/agent-center/flow/annotate.svg'),
  Request: cdnAssetUrl('assets/agent-center/flow/Http.svg'),
};

export const WF_MAX_PARAMS_NUM = 100;

export const LAZY_LOAD_LIMIT = 100;

export const EXCEPTION_PORT_NODE = ['Workflow', 'LLM', 'Plugin', 'Code', 'IntentDetection', 'Mcp'];

export const NODE_TYPE = {
  AGENT: 'agent',
  SUB_CONTROLLER: 'sub_controller',
  CONTROLLER: 'controller',
};

export const flowConfig = {
  default_model: {
    model_name: '',
    model_deployment_id: '',
    model_type: '',
  },
  environment: '',
  default_model_switch: false,
  prologue: '',
  suggest_queries: [],
  long_memory_enabled: false,
  memory: [],
  safety_barrier: false,
  content_review: {
    enabled: false,
    filter: {
      keywords: '',
    },
    replace: [],
    reply: [],
  },
  voice_interaction: {
    language: '',
    timbre: '',
    domain: '',
  },
  voice_interaction_switch: false,
  additional_questions_config: {
    enable: true,
    prompt: '',
  },
};

export const flowMcpListParams = {
  type: 'inner',
  offset: 0,
  limit: 1,
  node_type: 'DataAcquisition',
  visibility: 'global',
};

export const getFlowMcpNodeData = (apiNodeData: IMcpNode) => {
  return {
    ...apiNodeData,
    id: `node_${Date.now()}`,
    name: apiNodeData.name,
    type: apiNodeData.type,
    shape: `op-${apiNodeData.type.toLowerCase()}-node`,
  };
};

export const appFlowOutput = {
  name: 'summary',
  type: 'string',
  description: i18next.t('summary_description_content', { ns: [I18nNamespace.AGENT_CENTER] }),
  required: false,
  source: 'user',
  reflection: false,
  value: {
    default: '',
    type: 'generated',
    hint: '',
    content: '',
  },
};

export const HOVER_TOOLS_NAME = 'edge-hover-tools';

export const NODE_SAVE_DEBOUNCE_TIME = 300;
