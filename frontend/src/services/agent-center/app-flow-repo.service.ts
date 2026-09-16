import { Injectable } from '@angular/core';
import {
  ICreateWorkflow,
  IModel, IPublishedAgentsListQueryResp,
  IPublishedWorkflowListQueryResp,
  IWorkflow,
  IWorkflowInfo,
  IWorkflowListQuery,
  IWorkflowListQueryResp,
  IWorkflowUpdateData,
  WorkflowImportQuery,
} from '@routes/agent-center/app-flow/app-flow.types';
import { IAppRefList } from '@routes/agent-center/types/common.types';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import { MessageComponent } from '@shared/services/cfdata.service';

@Injectable({
  providedIn: 'root',
})
export class AppFlowRepoService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager`;
  }

  get functionHeard() {
    return `${this.ctxServ.baseUrl}`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  public getFlows(params: IWorkflowListQuery): Promise<IWorkflowListQueryResp> {
    const { offset, limit, ...rest } = params;

    const searchOptions: any = {};
    for (const key in rest) {
      if (rest[key] != null && rest[key] !== '') {
        //映射列表查询字段，待有空整改
        if (key === 'workflow_type') {
          searchOptions.type = rest[key];
        } else if (key === 'author') {
          searchOptions.creator = rest[key];
        } else {
          searchOptions[key] = rest[key];
        }
      }
    }

    return this.http.getAsync({
      url: `${this.prefix}/workflows`,
      query: {
        offset,
        limit,
        ...searchOptions,
      },
    });
  }
  public getShareFlows(params: IWorkflowListQuery,): Promise<IPublishedWorkflowListQueryResp> {
    const { offset, limit, ...rest } = params;
    const searchOptions = {};
    for (const key in rest) {
      if (rest[key] != null && rest[key] !== '') {
        searchOptions[key] = rest[key];
      }
    }

    const url = `${this.prefix}/resource/share`;
    return this.http.getAsync({
      url,
      query: {
        offset,
        limit,
        ...searchOptions,
      },
    });
  }

  public getPublishedFlows(
    params: IWorkflowListQuery,
  ): Promise<IPublishedWorkflowListQueryResp> {
    const { offset, limit, ...rest } = params;

    const searchOptions = {};
    for (const key in rest) {
      if (rest[key] != null && rest[key] !== '') {
        searchOptions[key] = rest[key];
      }
    }

    const url = `${this.prefix}/workflows/lastversions`;
    return this.http.getAsync({
      url,
      query: {
        offset,
        limit,
        ...searchOptions,
      },
    });
  }
  /*得到多智能体列表*/
  public getPublishedMutilAgentList(
    params:any
  ):Promise<IPublishedAgentsListQueryResp>{
    const { offset, limit, type, id, name, sub_type } = params;
    const query: any = {
      offset,
      limit,
      type,
    };
    if (id) {
      query.id = id;
    }
    if (name) {
      query.name = name;
    }
    if(sub_type) {
      query.sub_type = sub_type;
    }
    const url = `${this.prefix}/agents/lastversions`;
    return this.http.getAsync({
      url,
      query,
    });
  }

  /*得到多智能的详情*/
  public getPublishedMutilAgentDetails(
    agents_id:string,version_id:string
  ):Promise<IPublishedAgentsListQueryResp>{
    const url = `${this.ctxServ.baseUrl}/agent-manager/agents/${agents_id}/versions/${version_id}`;
    return this.http.getAsync({
      url,
    });
  }

  public getFlow(workflowId: string, param = {}): Promise<IWorkflow> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}`,
      query: {
        ...param,
      },
    });
  }

  public getFlowVersionInfo(
    workflowId: string,
    versionId: string,
  ): Promise<IWorkflow> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${workflowId}/versions/${versionId}`,
      headers: {
        'nested-check': 'true',
      },
    });
  }

  public modifyFlow(workflow: IWorkflowUpdateData): Promise<IWorkflow> {
    return this.http.putAsync({
      url: `${this.prefix}/workflows/${workflow.workflow_id}`,
      params: workflow,
    });
  }

  public createFlow(basicInfo: ICreateWorkflow): Promise<IWorkflowInfo> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows`,
      params: basicInfo,
    });
  }

  public deleteFlow(workflowId: string): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/workflows/${workflowId}`,
    });
  }

  public copyFlow(
    workflowId: string,
    target_workspace_id: string,
  ): Promise<void> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/copy`,
      query: {
        target_workspace_id,
      },
    });
  }

  public copyAgentToASpace(
    agent_id: string,
    target_workspace_id: string,
  ): Promise<void> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/copy`,
      query: {
        target_workspace_id,
        workspace_id: this.ctxServ.workspaceId,
      },
    });
  }

  /** 导入知识型Agent/工作流/插件之前，解析jsonl文件 */
  public parseFile(formatData: FormData): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/list`,
      body: formatData,
    });
  }

  /** 导入工作流 */
  public importWorkflow(formatData: FormData): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/import`,
      body: formatData,
    });
  }

  /** 删除触发器 */
  public deleteOneTrigger(
    workflowId: string,
    trigger_id: string,
  ): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/workflows/${workflowId}/triggers/${trigger_id}`,
    });
  }

  /** 添加触发器 */
  public addOneTrigger(workflowId: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/${workflowId}/triggers/add`,
      params,
    });
  }

  /**編輯触发器*/
  public editOneTrigger(workflowId: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/${workflowId}/triggers/edit`,
      params,
    });
  }

  /** 导出工作流 */
  public exportWorkflows(params: any): Promise<any> {
    return this.http.postBlobAsync({
      url: `${this.prefix}/workflows/export`,
      params,
      dataType: 'blob',
    }).catch(error=>{
      if (error.data instanceof Blob) {
        this.http.parseBlobError(error.data).subscribe({
          error: (err) => {
            MessageComponent.showError(err.error_msg);
          },
        });
      }
    });
  }

  /** 校验工作流 */
  public validateFlow(workflowId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/validate`,
    });
  }

  /** 校验多智能体（试运行前预校验：子工作流版本存在性） */
  public validateControllerAgent(agentId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agentId}/validate`,
      query: {
        workspace_id: this.ctxServ.workspaceId,
      },
    });
  }

  public getModelList(): Promise<IModel[]> {
    return this.http.getAsync({
      url: `${this.prefix}/models`,
    });
  }

  /** 查询日志的conversations列表 */
  public getConversationList(
    workflowId: string,
    params: {
      start_time?: number;
      end_time?: number;
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<any> {
    const { start_time, end_time, limit, offset } = params;

    const query: any = {};
    if (start_time !== undefined) {
      query.start_time = start_time;
    }
    if (end_time !== undefined) {
      query.end_time = end_time;
    }
    if (offset !== undefined) {
      query.offset = offset;
    }
    if (limit !== undefined) {
      query.limit = limit;
    }
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/conversations`,
      query,
    });
  }

  /** 查询日志的execution列表 */
  public getExecList(workflowId: string, conversationId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/conversations/${conversationId}/executions`,
    });
  }

  /** 查询单次execution的信息 */
  public getSingleExecInfo(
    workflowId: string,
    executionId: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/executions/${executionId}`,
    });
  }

  /** 查询日志的execution列表 */
  public getAsyncExecList(workflowId: string, conversationId: string,query?:object): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/conversations/${conversationId}/executions`,
      // query
    });
  }

  public getAsyncSingleExecInfo(
    workflowId: string,
    executionId: string,query:object
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/executions/${executionId}`,
      query
    });
  }

  public generatePrologue(flowId: string): Promise<{
    prologue: string;
  }> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flowId}/prologue`,
    });
  }

  public generateQuestions(flowId: string): Promise<{
    questions: string[];
  }> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flowId}/recommended-questions`,
      timeout: 120000,
    });
  }

  public getFrontParams(workflowId: string, versionId: string) {
    return this.http.getAsync({
      url: `${this.prefix}/workflows/${workflowId}/front-params`,
      query: { version: versionId },
    });
  }

  /** 获取指定应用的引用资源列表 */
  public getAppRefs(id: string, query: any): Promise<IAppRefList> {
    return this.http.getAsync({
      url: `${this.prefix}/relation/apps/${id}`,
      query,
    });
  }

  public getPluginVersionInfo(
    pluginId: string,
    versionId: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${pluginId}/versions/${versionId}`,
    });
  }

  public getFunctionsList(
    limit: number,
    offset: number,
    keyword: string,
  ): Promise<any> {
    const params: any = {
      workspace_id: this.ctxServ.workspaceId,
      offset: offset,
      limit: limit,
      usage_type: 'flow',
    };
    if (keyword?.length > 0) {
      params.keyword = keyword;
    }
    return this.http.getAsync({
      url: `${this.prefix}/functions`,
      query: params,
    });
  }

  public getFunctionsdetail(id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/functions/${id}`,
      params: {
        workspace_id: this.ctxServ.workspaceId,
      },
    });
  }

  public addFunctionsdetail(body: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/functions`,
      params: {
        workspace_id: this.ctxServ.workspaceId,
      },
      body: JSON.stringify(body),
    });
  }

  public putFunctionsdetail(id: string, body: any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/functions/${id}`,
      params: {
        workspace_id: this.ctxServ.workspaceId,
      },
      body: JSON.stringify(body),
    });
  }

  public deleteFunction(id: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/functions/${id}`,
    });
  }

  public getAuth(): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/queryAuthorization`,
      query:{
        workspace_id: this.ctxServ.workspaceId,
      }
    });
  }
  public doAuth(): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/doAuthorization`,
      query: {
        workspace_id: this.ctxServ.workspaceId,
      }
    });
  }


  public getConversationsDetail(id: string,conversationId:string): Promise<any> {
    return this.http.getAsync({
      url: `${this.functionHeard}/agent-manager/agents/${id}/conversations/${conversationId}/history`,

    });
  }

  public getCitationList(params, functionId): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/relation/resources/${functionId}`,
      query: params,
    });
  }

  public deleteFg(functionId) {
    return this.http.deleteAsync({
      url: `${this.prefix}/functions/${functionId}`,
    });
  }

  // 查询依赖包列表
  public getDependencyList(params: any): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/dependencies`,
      query: {
        ...params,
      },
    });
  }

  // 查询版本
  public getDependencyVersionList(params: any, dependId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/dependencies/${dependId}/versions`,
      query: {
        ...params,
      },
    });
  }

  /**
   * 解析并转换外部工作流
   */
  public importParseWorkFlow(query: WorkflowImportQuery, formatData: FormData): Promise<IWorkflowInfo> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/import/parse`,
      query,
      body: formatData,
    });
  }

  /** 供应商鉴权*/
  public saveAutheConfig(params, id): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/integration/providers/auth-info/${id}`,
      params,
    });
  }

  /** mcp鉴权*/
  public saveMcpAutheConfig(params, id): Promise<any> {
    return this.http.putAsync({
      url: `${this.functionHeard}/mcp/service/auth-info/${id}`,
      params,
    });
  }

  /** 插件鉴权*/
  public savePluginAutheConfig(params, id): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/plugins/${id}/auth-info`,
      params,
    });
  }
}
