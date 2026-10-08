import { ControllerSubFlowType, FlowAction } from "@routes/agent-center/app-flow/node.type";

export const CONTROLLER_SUB_FLOW_LIMIT = 50;

export const CONTROLLER_SUB_CONTROLLER_LIMIT = 50;

/** 顶层控制器可挂载的单智能体数量上限，与后端 controller.single-agent-limit 默认值对齐 */
export const CONTROLLER_SUB_SINGLE_AGENT_LIMIT = 10;

export interface SubApplication {
  id: string;
  node_id?: string;
  name: string;
  // 默认为空，暂不展示自定义图标
  avatar?: string;
  type: string;
  subAgentType: string;
  description: string;
  version_id?: string;
  version_name?: string;
  checked?: boolean;
  disable?: boolean;
  tip?: string;
  action?: FlowAction;
  tags?: string[];

  // 版本更新
  update?: any;
  validVersion?: boolean;
  valid?: boolean;

  // 团队共享
  fromShare?: boolean;
  creator?: string;
  workspace_name?: string;
  workspace_id?: string;
  version_info_list?: any[];
}

export interface SubAgentModel extends SubApplication {
  mode: string;
  workflows?: any[];
  tip?: string;
  code?: string;
}

export interface SubWorkFlow extends SubApplication {
  type: ControllerSubFlowType;
  /** 工作流类型-对话型、任务型 */
  flowType: string;
  code?: string;
}
