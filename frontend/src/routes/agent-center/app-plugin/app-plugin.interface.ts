/** 插件整体结构 */
export interface PluginDetail {
  name: string;
  tool_chinese_name?: string;
  description: string;
  url: string;
  method: string;
  visibility: 'project' | 'user';
  headers?: any;
  logo?: string;
  auth?: any;
  arguments?: any;
  response?: any;
  is_input_list: boolean;
  is_output_list: boolean;
  intf_type: 'blocking' | 'streaming';
  auth_required?: boolean;
  metadata?: string;
  function_id?: string;
  call_mode?: string;
}

/** 插件请求参数 */
export interface IRequestArgsBase {
  name: string;
  description: string;
  type: string;
  location: string;
  required: boolean;
  default: string;
  name_cn: string;
  visible?: boolean;

  /** 是否需要参数校验 */
  validated: boolean;
  validate_type: string;
  validate_rule: string;

  oneOf?: IRequestArgsOF[];
  anyOf?: IRequestArgsOF[];

  /** 引用的环境变量名，设置后该参数在工作流中自动绑定到同名环境变量 */
  env_var_ref?: string;
}

export interface IRequestArgsOF {
  name?: string;
  description?: string;
  type?: string;
  properties?: {
    [key: string]: IReqSchemaBaseProps | IReqArrayProps | IReqObjProps;
  };
  required?: string[];
}

export interface IRequestArgsView extends IRequestArgsBase {
  children?: IRequestArgsView[];
  parentType?: string;

  /** 标识当前参数处于第几层, 从根节点开始, 最小层级为 0, 最大为 3 */
  depth: number;

  expanded?: boolean;

  keyindex?: string;
}

/** 插件响应参数 */
export interface IResponseArgumentsBase {
  name: string;
  description: string;
  type: string;
  required: boolean;
  default?: string;
}

export interface IResponseArgsView extends IResponseArgumentsBase {
  children?: IResponseArgsView[];
  parentType?: string;
  depth: number;
  expanded?: boolean;
}

/** 基本类型 */
export type IReqSchemaBaseProps = Omit<IRequestArgsBase, 'required' | 'name'>;

/** 对象类型 */
export interface IReqObjProps extends IReqSchemaBaseProps {
  properties: {
    [key: string]: IReqSchemaBaseProps | IReqArrayProps | IReqObjProps;
  };
  required?: string[];
}

/** 数组类型 */
export interface IReqArrayProps extends IReqSchemaBaseProps {
  items:
    | IReqObjProps
    | {
        type: string;
      };
  required?: string[];
}

export type IReqArgProps = IReqSchemaBaseProps | IReqArrayProps | IReqObjProps;

export interface IReqSchema {
  type: string;
  properties?: {
    [key: string]: IReqArgProps;
  };
  required?: string[];
}

/** 响应基本类型 */
export type IResSchemaBaseProps = Omit<
  IResponseArgumentsBase,
  'required' | 'name'
>;

/** 响应对象类型 */
export interface IResObjProps extends IResSchemaBaseProps {
  properties: {
    [key: string]: IResSchemaBaseProps | IReqArrayProps | IReqObjProps;
  };
  required?: string[];
}

/** 响应数组类型 */
export interface IResArrayProps extends IResSchemaBaseProps {
  items:
    | IResObjProps
    | {
        type: string;
      };
  required?: string[];
}

export type IResArgProps = IResSchemaBaseProps | IResArrayProps | IResObjProps;

export interface IResSchema {
  type: string;
  properties?: {
    [key: string]: IResArgProps;
  };
  required?: string[];
}

export interface IDataAcquisitionConfigSchema {
  label: string;
  value: string;
  description?: string;
  children: IDataAcquisitionConfigSchema[];
}

export interface IUserAuthKV {
  target_name: string;
  source_name: string;
}

export interface IServAuthKV {
  target_name: string;
  auth_key: string;
}

export type IAuthInfo =
  | {
      scope: string;
      domain?: string;
      auth_keys?: IUserAuthKV[] | IServAuthKV[];
      iam_credentials?: {
        projectId?: string;
      };
    }
  | Record<string, never>;

export interface IPluginBase {
  tool_display_name: string;
  tool_chinese_name?: string;
  tool_desc: string;
  tool_id?: string;
}

export interface IPlugin extends IPluginBase {
  request_info: {
    url: string;
    method: string;
    headers?: Record<string, any>;
    input_schema?: string; // 插件路径参数
  };
  name?: string;
  visibility: 'project' | 'user';
  auth_info: IAuthInfo;
  input_schema?: string;
  output_schema?: string;
  is_input_list: boolean;
  is_output_list: boolean;
  creator?: string;
  creator_id?: string;
  icon: string;
  intf_type: 'blocking' | 'streaming';
  type?: 'custom' | 'inner';
  test_status?: 'SUCCESS' | 'FAILED' | 'UNKNOWN';
  last_version_id?: string;
  customize_node?: boolean;
  auth_required?: boolean;
  metadata?: string;
  update_time?: string;
  function_id?: string;
  credential_status?: string;
}

export interface PluginListReq {
  offset?: number;
  limit?: number;
  id?: string;
  name?: string;
  tool_desc?: string;
  tool_chinese_name?: string;
  customize_node?: boolean;
  type?: string;
  ids?: string[];
  intf_type?: string;
  published?: number;
  call_mode?: string;
  entry_point?: string;
  label?: string;
  category?: string;
}

export interface PluginListResponse {
  tool_list: IPlugin[];
  count: number;
}

export interface ApiKeyAuthArguments {
  name: string;
  value: string;
}

export interface UserAuthArguments {
  name: string;
  sourceName: string;
}

export interface IDebugPluginResponse {
  raw_request_url: string;
  raw_request_headers: Record<string, string>;
  raw_request_body: string;
  raw_response_code: number;
  raw_response: string;
  success: boolean;
  errorMessage: string;
}

export interface IToolCreate{
  tool_id?: string; //创建时不要，修改时需要
  tool_display_name: string;
  tool_chinese_name: string;
  tool_desc: string;
  visibility:string;
  input_schema: string;
  output_schema: string;
  request_info:{
    url: string;
    method: string;
    headers: any;
  }
  is_input_list: boolean;
  is_output_list: boolean;
  intf_type: 'blocking' | 'streaming';
}

export interface ITool {
  [key: string]: any;

  tool_id: string;
  tool_display_name: string;
  tool_chinese_name: string;
  tool_desc: string;
  url: string;
  method: string;
  headers: any;
  path: string;
}
export interface IToolInfo{
  tool_id: string;
  tool_display_name: string;
  tool_chinese_name: string;
  tool_desc: string;
  input_schema: string;
  output_schema: string;
}

/**
 * 插件的类型以后都改成使用这个，其他的都逐步替换掉
 */
export interface IPluginWithTools {
  [key: string]: any;

  plugin_id: string;
  project_id: string;
  plugin_display_name: string;
  plugin_chinese_name: string;
  plugin_desc: string;
  icon: string;
  request_info: {
    basic_info: {
      host: string;
      path: string;
      protocol: string;
    };
    tool_info: Array<ITool>;
  };
  auth_info: any;
  visibility: string;
  input_schema: [
    {
      tool_id: string;
      input_schema: string;
    },
  ];
  output_schema: [
    {
      tool_id: string;
      output_schema: string;
    },
  ];
  is_input_list: [
    {
      tool_id: string;
      is_input_list: false;
    },
  ];
  is_output_list: [
    {
      tool_id: string;
      is_output_list: false;
    },
  ];
  type: string;
  call_mode: string;
  intf_type: [
    {
      tool_id: string;
      intf_type: string;
    },
  ];
  metadata: string;
  creator: string;
  creator_id: string;
  created_on: number;
  updated_on: number;
  test_status: [
    {
      tool_id: string;
      test_status: number;
    },
  ];
  credential: any;
  credential_status: string;
  auth_required: boolean;
  published: number;
  is_free: number;
  is_share: number;
}

export interface ListIPluginWithToolsResponse {
  count: number;
  plugin_list: IPluginWithTools[];
}

export enum PLUGIN_QUOTA {
  NEED_AUTH_NO_QUOTA = -1,
  NOT_NEED_AUTH = -2,
}
