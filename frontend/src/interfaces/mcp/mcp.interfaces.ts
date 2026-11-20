import { McpDeployFailType } from '@routes/agent-center/types/common.types';

type McpServiceType = 'inner' | 'user';

export interface McpToolProperties {
  [key: string]: {
    type: string;
    description: string;
    description_en: string;
    default: any;
    properties: McpToolProperties;
    items?: {
      type: string;
    };
    required?: string[];
    additionalProperties?: boolean;
    value: any;
    copyValue: any;
    isRequired: boolean;
    isRight: boolean;
  }
}

interface McpMonitorDataSum {
  sum: number;
  date: string;
}

interface McpMonitorDataAverage {
  average: number;
  date: string;
}


export interface McpMonitorData {
  oneDay: number;
  sevenDay: number;
  thirtyDay: number;
  sum: McpMonitorDataSum[];
  average: McpMonitorDataAverage[];
}

export interface McpTool {
  name: string;
  description: string;
  description_en: string;
  inputSchema: {
    type: string;
    properties: McpToolProperties;
    required: string[];
    additionalProperties: boolean;
  }
  isCollapsed: boolean;
}

interface AuthKey {
  auth_key: string;
  target_name: string;
}
interface CustomOauth {
  endpoint_url: string;
  client_id: string;
  client_secret: string;
  scope: string;
}

interface AuthInfo {
  scope: string;
  domain?: string;
  auth_keys?: AuthKey[];
  custom_oauth?: CustomOauth;
}

export interface McpInterfaces {
  id: string;
  name: string;
  name_en: string;
  deploy_type: string;
  description: string;
  description_en: string;
  fc_instance_status: string;
  status_cn: string;
  status_en: string;
  install_times: number;
  view_times: number;
  created_on: string;
  icon: string;
  config_status: string;
  desc: string;
  creator: string;
  type: McpServiceType;
  type_cn: string;
  type_en: string;
  isHover: boolean;
  isSelected: boolean;
  created_date: string;
  readme: string;
  last_updated_date: string;
  tools: McpTool[];
  url: string;
  org_type: string;
  server_config: string;
  monitorData: McpMonitorData;
  score: number;
  third_resource?: string;
  resource?: string;
  category?: string;
  auth_info?: AuthInfo;
  fail_reason_detail?: McpDeployFailType;
  /** FEAT-134: 导入后待补配标记（true=有配置项需在目标环境补配） */
  import_config_pending?: boolean;
  /** FEAT-134: 待补配的路径清单（逗号分隔） */
  import_config_paths?: string;
}

interface McpAuthKey {
  target_name: string;
  source_name: string;
  desc: string;
  auth_key: string;
}

export interface McpServer {
  auth: { auth_keys: McpAuthKey[] };
  config_status: 'none' | 'need' | 'done';
  icon: string;
  name: string;
  desc: string;
  description: string;
  [key: string]: any;
}
