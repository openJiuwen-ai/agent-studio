import { Injectable } from '@angular/core';

import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import {
  IChangeMemoryParams,
  IMemoryBasicQuery,
  IMemoryQueryParams,
  IMemoryRes,
} from '@shared/components/memory-management/memory-management.interface';

/** manager v2 记忆条目单条结构（id/content/type/last_update_time） */
interface IMemoryItemV2 {
  id: string;
  content: string;
  type?: string;
  last_update_time?: string;
}

/** manager v2 记忆条目列表响应 */
interface IListMemoryItemsV2Response {
  items?: IMemoryItemV2[];
  total?: number;
}

@Injectable({
  providedIn: 'root',
})
export class MemoryManagementService {
  isSupportUerPersona = false;

  /**
   * v2 manager 记忆条目资源根路径（baseUrl /v1/ → /v2/，memory_repo_id 为 path 参数）
   */
  private get repoPrefix(): string {
    return `${this.ctxServ.baseUrl}/agent-manager`.replaceAll('/v1/', '/v2/');
  }

  constructor(
    private configServ: AgentConfigService,
    private ctxServ: ContextService,
    private http: HttpService
  ) {
    this.isSupportUerPersona = Boolean(this.configServ.getConfigs().memory_user_profile_enable);
  }

  /**
   * persona  start
   */
  /**
   * 查看记忆
   * manager v2 使用 page_num/page_size 入参、items[].id 返回；
   * 此处完成 offset/limit → page_num/page_size 与 items → memories 的转换，
   * 对弹窗组件保持 {memories, total} 结构不变。
   */
  queryMemory(query: IMemoryQueryParams): Promise<IMemoryRes> {
    const pageNum = Math.floor(query.offset / query.limit) + 1;
    return this.http
      .getAsync<IListMemoryItemsV2Response>({
        url: `${this.repoPrefix}/memory-repositories/${query.memory_repo_id}/memories`,
        query: {
          page_num: pageNum,
          page_size: query.limit,
          memory_type: query.memory_type,
        },
      })
      .then(res => ({
        memories: (res.items ?? []).map(item => ({
          memory_id: item.id,
          content: item.content,
          type: item.type,
          last_update_time: item.last_update_time,
        })),
        total: res.total ?? 0,
      }));
  }

  /**
   * 修改记忆内容（保持一次提交多条已编辑条目的语义）
   */
  changeMemoryContent(memoryData: IChangeMemoryParams, query: IMemoryBasicQuery) {
    return this.http.putAsync({
      url: `${this.repoPrefix}/memory-repositories/${query.memory_repo_id}/memories`,
      params: memoryData,
    });
  }

  /**
   * 删除记忆
   */
  deleteMemory(memoryIds: string[], query: IMemoryBasicQuery) {
    return this.http.postAsync({
      url: `${this.repoPrefix}/memory-repositories/${query.memory_repo_id}/memories/batch-delete`,
      params: {
        memory_ids: memoryIds,
      },
    });
  }

  /**
   * 清空记忆
   */
  clearMemory(query: IMemoryBasicQuery) {
    return this.http.deleteAsync({
      url: `${this.repoPrefix}/memory-repositories/${query.memory_repo_id}/memories`,
    });
  }
}
