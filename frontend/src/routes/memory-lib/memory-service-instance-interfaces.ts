/** 外部记忆服务实例列表项  */
export interface IMemoryServiceInstanceItem {
  instance_id: string;
  name: string;
  base_url: string;
  health_status: string;
  last_check_at?: number;
  deploy_meta?: string;
  created_user_id: string;
  created_user_name: string;
  create_time: number;
  update_time: number;
}

/** 实例列表响应  */
export interface IListInstancesResponse {
  total: number;
  items: IMemoryServiceInstanceItem[];
}

/** 实例详情  */
export interface IInstanceDetail extends IMemoryServiceInstanceItem {}

/** 创建实例参数  */
export interface ICreateInstanceParams {
  name: string;
  base_url: string;
  api_key?: string;
}

/** 修改实例参数  */
export interface IModifyInstanceParams {
  name?: string;
  base_url?: string;
  api_key?: string;
}

/** 创建实例响应  */
export interface ICreateInstanceResponse {
  instance_id: string;
}

/** 记忆后端类型枚举  */
export enum MemoryBackendType {
  BUILTIN = 'BUILTIN',
  EXTERNAL = 'EXTERNAL',
}
