import { MemoryStrategyType } from '@routes/memory-lib/memory-lib-enums';

export type ModuleResolveFn = Promise<boolean>;

export interface IMemoryBasicQuery {
  memory_repo_id: string;
}

export interface IMemoryQueryParams extends IMemoryBasicQuery {
  memory_type: string;
  offset: number;
  limit: number;
}

export interface IMemoryRes {
  memories: IMemoryItem[];
  total?: number;
}

export interface IMemoryManagementData extends IMemoryRes {
  enable_retrieve: boolean;
  enable_extract: boolean;
}
export interface ConversationState {
  isExtract: boolean;
  isRetrieve: boolean;
}

export interface MemoryUpdatedSSE {
  event: 'MEMORY_UPDATED';
  data: {
    time: number;
    agent_id: string;
    conversation_id: string;
    memories: IUpdatedMemoryItem[];
  };
}

export interface IUpdatedMemoryItem {
  content: string;
  id: string;
  operation: MemUpdatedOperationType;
}

export enum MemUpdatedOperationType {
  UPDATE = 'UPDATE',
  DELETE = 'DELETE',
}

export interface IMemoryInfo {
  // all
  content: string;
  updatedType: MemUpdatedOperationType;
  fakeId: string; // uuid from frontend
  id?: string;
}

export interface IChangeMemoryParams {
  memories?: IMemoryItem[];
}

export interface IMemoryItem {
  memory_id: string;
  content: string;
  type?: string;
  last_update_time?: string;
}
