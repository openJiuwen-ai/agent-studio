import { MemoryLibCardOperationType, MemoryStrategyType } from '@routes/memory-lib/memory-lib-enums';

/** 记忆库一致性数组  */
export interface IMemoryStrategyItem {
  type: MemoryStrategyType;
  name: string;
  description: string;
  defaultPrompt: string;
}

/** 前端主动添加的记忆库item的属性  */
export interface IMemoryLibItemVirtualData {
  operations?: any; // 当前记忆库的操作（卡片态列表）
  selected?: boolean; // 当前记忆库是否选中 (被选择引用时)
  invalid?: boolean; // 当前记忆库是否失效（曾经被引用，之后被删除）
}

/** 记忆库的基本信息（用于存储在智能体等资源的信息）  */
export interface IMemoryLibBaseInfo {
  memory_repo_id: string;
  name?: string;
  description?: string;
}

/** 记忆库详情  */
export interface IMemoryLibItem extends IMemoryLibItemVirtualData, IMemoryLibBaseInfo {
  icon: string;
  workspace_id: string;
  long_term_memory_strategies: IMemoryStrategy[];
  created_user_id: string;
  created_user_name: string;
  create_time: number;
  last_update_user_id: string;
  last_update_user_name: string;
  update_time: number;
  conversation_round?: number;
  time_span?: number;
  memory_backend_type?: string;
  memory_service_instance_id?: string;
}

/** 记忆库的提取策略  */
export interface IMemoryStrategy {
  type: MemoryStrategyType;
  prompt: string;
}

/** 调用记忆库创建的返回值  */
export interface IMemoryLibCreationData {
  reason: boolean;
  halfModalRef: any;
  data: IMemoryLibChangeParams | null;
  setLoading: (isLoading: boolean) => void;
}

/** 记忆库详情  */
export interface IMemoryLibDetail extends IMemoryLibBaseInfo {
  workspace_id: string;
  icon: string;
  long_term_memory_strategies: IMemoryStrategy[];
  created_user_id: string;
  created_user_name: string;
  create_time: number;
  last_update_user_id: string;
  last_update_user_name: string;
  update_time: number;
  conversation_round?: number;
  time_span?: number;
  memory_backend_type?: string;
  memory_service_instance_id?: string;
}

/** 记忆库的卡片展示模式配置  */
export interface MemoryLibCardDisplayConfig {
  layoutConfig?: {
    layout?: 'grid' | 'flex';
    flexQuantities?: number;
  };
  cardSize?: 'small' | 'middle' | 'large';
  cardBgColor?: string;
  cardNameBold?: boolean;
  descriptionConfig?: {
    enable?: boolean;
    maxLine?: number;
  };
  operationConfig?: {
    enable?: boolean;
    singleOperationEnable?: (kb: IMemoryLibItem, operationType: MemoryLibCardOperationType) => boolean;
  };
  tagsConfig?: {
    enable?: boolean;
    tagSize?: 'xs' | 'small' | 'middle' | 'large';
  };
  noDataConfig?: {
    showImg?: boolean;
    showTitle?: boolean;
    showDescription?: boolean;
    showCreate?: boolean;
  };
  footerConfig?: {
    userShow?: boolean;
    timeShow?: boolean;
    operation?: boolean;
  };
  detailLink?: {
    enable?: boolean;
  };
}

/** 在智能体等选择记忆库的回调参数  */
export interface IMemoryLibSelectData {
  reason: boolean;
  halfModalRef: any | null;
  data: IMemoryLibItem[];
}

/** 记忆库查询参数  */
export interface IMemoryLibsQueryParams {
  offset?: number;
  limit?: number;
  name?: string;
  ids?: string[];
}

/** 记忆库查询返回值  */
export interface IMemoryLibsQueryResponse {
  total: number;
  items: IMemoryLibItem[];
}

/** 记忆库创建、修改参数  */
export interface IMemoryLibChangeParams {
  name: string;
  description: string;
  icon?: string;
  long_term_memory_strategies?: IMemoryStrategy[];
  conversation_round?: number;
  time_span?: number;
  memory_backend_type?: string;
  memory_service_instance_id?: string;
}

/** 记忆库创建Res  */
export interface ICreateMemoryLibResponse {
  memory_repo_id: string;
}

/** 记忆库修改Res  */
export interface IPatchMemoryLibResponse {
  memory_repo_id: string;
}

/** 记忆库删除Res  */
export interface IDeleteMemoryLibResponse {
  memory_repo_id: string;
}
