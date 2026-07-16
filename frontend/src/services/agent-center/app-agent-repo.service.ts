import { Injectable } from '@angular/core';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import { IModel } from '@routes/agent-center/app-flow/app-flow.types';
import { SSE } from '@shared/services/sse';
import { environment } from 'src/environment/environment';
import { IMemoParamExt } from '@routes/agent-center/app-agent/components/preview-memos/preview-memos.component';
import {
  AgentConfigService,
  IAgentConfigs,
} from '@routes/agent-center/agent-config.service';
import { CommonUtils } from '../../utils/common.util';
import { IPlugin } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { PE_SESSION_KEY } from '@constants/exp-tmpl-config.const';
import i18next from 'i18next';
import { CONVERSATION_TYPE } from './app-controller.service';
import { v4 as uuidV4 } from 'uuid';

type AppType = 'agent' | 'workflow';

enum mapKeys {
  offset = 'offset',
  limit = 'limit',
}

@Injectable({
  providedIn: 'root',
})
export class AppAgentRepoService {
  public lang: string;

  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager`;
  }

  get prefixRuntime() {
    return `${this.ctxServ.baseUrl}/agent-manager/agents`;
  }

  get prefixAgentRuntime() {
    return `${this.ctxServ.baseUrl}/agent-runtime`;
  }

  get MCPPath() {
    return `${this.ctxServ.baseUrl}/mcp`;
  }

  get runPrefix() {
    return `${this.ctxServ.baseUrl}`;
  }

  get cur_workspace_id() {
    return this.ctxServ.currentWorkspaceId;
  }
  get resource_prefix() {
    return '/v1';
  }

  constructor(
    private http: HttpService,
    private ctxServ: ContextService,
    private configServ: AgentConfigService,
  ) {
    this.lang = CommonUtils.getLanguage();
  }

  /** 创建知识型Agent */
  public createAgent(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents`,
      params,
    });
  }

  /** 获取用户权限 */
  public acquirePermission(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/permissions`,
    });
  }

  public requireMasOperator(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workspace/${this.cur_workspace_id}`,
    });
  }

  /** 获取知识型Agent列表 */
  public getAgentList(
    params: any,
    offset: number,
    limit: number,
  ): Promise<any> {
    const { id, name, type, status, description, creator } = params;

    return this.http.getAsync({
      url: `${this.prefix}/agents`,
      query: {
        ...(offset !== undefined && { offset }),
        ...(limit !== undefined && { limit }),
        ...(id !== undefined && { id }),
        ...(name !== undefined && { name }),
        ...(type !== undefined && { type }),
        ...(status !== undefined && { status }),
        ...(creator !== undefined && { creator }),
        ...(description !== undefined && { description }),
      },
    });
  }

  /** 获取知识型workflow列表 */
  public getWorkflowList(
    params: any,
    offset: number,
    limit: number,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/workflows`,
      query: {
        ...(offset !== undefined && { offset }),
        ...(limit !== undefined && { limit }),
        ...params,
      },
    });
  }

  /** 删除一个知识型Agent */
  public deleteAgent(agent_id: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/agents/${agent_id}`,
    });
  }

  /** 查询一个知识型Agent信息 */
  public fetchAgentDetail(agentId: string, param = {}): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agentId}`,
      query: {
        ...param,
      },
    });
  }

  /** 查询一个Multi Agent信息 */
  public getMultiAgent(agentId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agentId}`,
    });
  }

  /** 获取模型列表 */
  public getModelList(): Promise<IModel[]> {
    return this.http.getAsync({
      url: `${this.prefix}/models`,
    });
  }

  /* new 获取新的模型列表 */
  public getNewModelList(): Promise<IModel[]> {
    return this.http.getAsync({
      url: `${this.runPrefix}/model-manager/available/model-services`,
      query: {
        model_type: 'LLM',
      },
    });
  }

  /** 修改一个Agent信息，触发实时保存 */
  public triggerSave(agentId: string, params: any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/agents/${agentId}`,
      params,
    });
  }

  /** 修改一个Multi Agent信息 */
  public modifyMultiAgent(params: any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/agents/${params.agent_id}`,
      params,
    });
  }

  /** 获取知识型Agent发布所属的标签列表 */
  public getTagList(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/tags`,
    });
  }

  /** 发布知识型Agent */
  public publishAgent(agent_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/publish`,
      params,
    });
  }

  /** 导入知识型Agent */
  public importAgents(formatData: FormData): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/import`,
      body: formatData,
    });
  }

  /** 导出知识型Agent */
  public exportAgents(params: any): Promise<any> {
    return this.http
      .postBlobAsync({
        url: `${this.prefix}/agents/export`,
        params,
        dataType: 'blob',
      })
      .catch((error) => {
        if (error.data instanceof Blob) {
          this.http.parseBlobError(error.data).subscribe({
            error: (err) => {
              MessageComponent.showError(err.error_msg);
            },
          });
        }
      });
  }

  /** 新版导出 */
  public newExportAgents(params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/resource/export`,
      params,
    });
  }

  /** 语言转文字 */
  public queryShortAudio(data): Promise<any> {
    return this.http.postAsync({
      url: `/sis/rest${this.ctxServ.prefix}/asr/short-audio`,
      params: data,
      overrideUrl: true,
    });
  }

  /** 智能生成开场白 */
  public generatePrologue(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/prologue`,
    });
  }

  /** 智能生成应用名称 */
  public generateName(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/name`,
    });
  }

  /** 智能生成应用描述 */
  public generateDescription(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/description`,
    });
  }

  /** 智能生成推荐问题 */
  public generateQuestions(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/recommended-questions`,
      timeout: 120000,
    });
  }

  /** 获取自动追问列表 */
  public getNextQuestions(
    agent_id: string,
    session_id: string,
    params: any,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/conversations/${session_id}/additional-questions`,
      params,
    });
  }

  /** 获取自动追问列表 */
  public getFlowNextQuestions(
    workflow_id: string,
    conversation_id: string,
    params: any,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/${workflow_id}/conversations/${conversation_id}/additional-questions`,
      params,
    });
  }

  /** 添加触发器 */
  public addOneTrigger(agent_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/triggers/add`,
      params,
    });
  }

  /**編輯触发器*/
  public editOneTrigger(agent_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/triggers/edit`,
      params,
    });
  }

  /** 删除触发器 */
  public deleteOneTrigger(agent_id: string, trigger_id: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/agents/${agent_id}/triggers/${trigger_id}`,
    });
  }

  /** 获取事件触发器的调用URL和trigger_id */
  public getEventTriggerURL(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/triggers/hook`,
    });
  }

  /** 知识型Agent中，查询日志的conversations列表 */
  public getConversationList(
    agent_id: string,
    params: {
      start_time?: number;
      end_time?: number;
      limit?: number;
      offset?: number;
      type?: CONVERSATION_TYPE;
    } = {},
  ): Promise<any> {
    const { start_time, end_time, offset, limit, type } = params;

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
    if (type !== undefined) {
      query.type = type;
    }
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/conversations`,
      query,
    });
  }

  /** 知识型Agent中，查询日志的execution列表 */
  public getExecList(agent_id: string, conversation_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/conversations/${conversation_id}/execution-queries`,
    });
  }

  /** 知识型Agent中，查询单次execution的信息 */
  public getSingleExecInfo(
    agent_id: string,
    execution_id: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/executions/${execution_id}`,
    });
  }

  /** 获取知识型Agent版本列表 */
  public getAgentVersionList(agent_id: string, params = {}): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/agents/${agent_id}/versions`,
      query: {
        ...params,
      },
    });
  }

  public getWorkflowVersionList(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${agent_id}/versions`,
    });
  }

  /** 知识型Agent中，发布一个版本 */
  public publishAgentVersion(agent_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/agents/${agent_id}/versions`,
      params,
    });
  }

  /** 知识型Agent中，删除一个版本 */
  public deleteAgentVersion(
    agent_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/agents/${agent_id}/versions/${version_id}`,
    });
  }

  /** 知识型Agent中，还原一个版本 */
  public rollbackAgentVersion(
    agent_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/agents/${agent_id}/versions/${version_id}`,
    });
  }

  /** 工作流中，获取版本列表 */
  public getFlowVersion(flow_id: string, params = {}): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flow_id}/versions`,
      query: {
        ...params,
      },
    });
  }

  /** 工作流中，发布一个版本 */
  public publishFlowVersion(flow_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flow_id}/versions`,
      params,
    });
  }

  /** 工作流中，删除一个版本 */
  public deleteFlowVersion(flow_id: string, version_id: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flow_id}/versions/${version_id}`,
    });
  }

  /** 工作流中，还原一个版本 */
  public rollbackFlowVersion(
    flow_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/workflows/${flow_id}/versions/${version_id}`,
    });
  }

  /** 插件中，版本详情列表 */
  public getPluginVersion(agent_id: string, version_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${agent_id}/versions/${version_id}`,
    });
  }

  /** 插件中，版本列表 */
  public getPluginVersionList(agent_id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${agent_id}/versions`,
    });
  }

  /** 插件中，发布一个版本 */
  public publishPluginVersion(plugin_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${plugin_id}/versions`,
      params,
    });
  }

  /** 插件中，删除一个版本 */
  public deletePluginVersion(
    tool_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${tool_id}/versions/${version_id}`,
    });
  }

  /** 插件详情，还原一个版本 */
  public restorePluginVersion(
    tool_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/plugins/${tool_id}/versions/${version_id}`,
    });
  }

  /** 获取长期记忆列表 */
  public getLongMemoryList(
    agent_id: string,
    conversation_id: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agents/${agent_id}/conversations/${conversation_id}/memory-chunks`,
    });
  }

  /** 生成一条长期记忆 */
  public generateLongMemory(
    agent_id: string,
    conversation_id: string,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agents/${agent_id}/conversations/${conversation_id}/memory-chunks`,
    });
  }

  /** 删除一条长期记忆 */
  public deleteLongMemory(
    agent_id: string,
    conversation_id: string,
    chunk_id?: string,
  ): Promise<any> {
    const url = `${this.ctxServ.baseUrl}/agents/${agent_id}/conversations/${conversation_id}/memory-chunks`;
    const queryParams = chunk_id ? `?chunk_id=${chunk_id}` : '';
    return this.http.deleteAsync({
      url: url + queryParams,
    });
  }

  /** 智能添加插件 */
  public generatePlugins(agent_id: string): any {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/auto-add/tools`,
    });
  }

  /** 智能添加工作流 */
  public generateFlows(agent_id: string): any {
    return this.http.getAsync({
      url: `${this.prefix}/agents/${agent_id}/auto-add/workflows`,
    });
  }

  /** 知识型Agent中，上传文件或图片 */
  public uploadFile(formatData: FormData, signal?): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefixRuntime}/upload-file`,
      body: formatData,
      signal,
    });
  }

  /** deepResearch上传文件 **/
  public uploadFileDeepResearch(
    agentId: string,
    formData: FormData,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefixRuntime}/${agentId}/uploadDeepResearchTemplate`,
      body: formData,
    });
  }

  /** 知识型Agent Runtime中，上传文件或图片 */
  public uploadFileRuntime(formatData: FormData, signal?): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefixRuntime}/upload-file`,
      body: formatData,
      signal,
    });
  }

  /** 知识型Agent中，查询已发布版本的通道列表 */
  public getPublishChannels(
    type: 'agents' | 'workflows',
    id: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/${type}/${id}/channels`,
    });
  }

  /** 知识型Agent中，选择某个通道发布应用版本 */
  public publishVersionForChannel(
    type: 'agents' | 'workflows',
    id: string,
    params: any,
  ): Promise<any> {
    return this.http.postAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/${type}/${id}/channels`,
      params,
    });
  }

  // 更新单智能体和工作流中发布管理的资源配置
  public updateSourceConfigForChannel(
    id: string,
    type: 'agents' | 'workflows',
    channel_id: string,
    params: any,
  ): Promise<any> {
    return this.http.putAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/${type}/${id}/channels/${channel_id}`,
      params,
    });
  }

  /** 知识型Agent中，删除某个通道信息 */
  public deleteVersionChannel(
    type: 'agents' | 'workflows',
    id: string,
    channel_id: string,
  ): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/${type}/${id}/channels/${channel_id}`,
    });
  }

  /** 知识型Agent中，更新某个通道发布的应用版本 */
  public updateVersionChannel(
    type: 'agents' | 'workflows',
    id: string,
    channel_id: string,
    version_id: string,
  ): Promise<any> {
    return this.http.putAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/${type}/${id}/channels/${channel_id}`,
      params: { version_id },
    });
  }

  /** 知识型Agent和工作流中，点赞点踩的问题反馈接口 */
  public feedback(agent_id: string, params: any): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/analytics/event`,
      params,
    });
  }

  /** 查询已发布的网页版详情  */
  public getWebPageInfo(
    short_code: string,
    find_by: string,
    channel_type: string,
    workspace_id?: string,
  ): Promise<any> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/releases/${short_code}?find_by=${find_by}&channel_type=${channel_type}`,
      query: {
        workspace_id: workspace_id ? workspace_id : this.cur_workspace_id,
      },
    });
  }

  /** 工作流是否校验通过 */
  public updateFlowStatus(workflowId: string, query): Promise<any> {
    return this.http.putAsync({
      url: `${this.runPrefix}/agent-manager/workflows/${workflowId}/test-status`,
      query,
    });
  }

  public abort(workflowId, conversationId) {
    return this.http.postAsync({
      url: `${this.prefix}/workflows/${workflowId}/conversations/${conversationId}/abort`,
    });
  }

  // /** 获取mcp服务列表 （用户创建的MCP） **/
  public getMCPServiceList(params: any): Promise<any> {
    const {
      offset,
      limit,
      name,
      type,
      fc_instance_status,
      node_type,
      visibility,
    } = params;
    const param = {
      offset: offset,
      limit: limit,
    };
    const query: any = {};
    if (name !== undefined && name !== null && name !== '') {
      query.name = name;
      query.language = this.isZH() ? 'ZH' : 'EN';
    }
    if (fc_instance_status) {
      query.fc_instance_status = fc_instance_status;
    }
    if (node_type) {
      query.node_type = node_type;
    }
    if (visibility) {
      query.visibility = visibility;
    }
    return this.http.postAsync({
      url: `${this.MCPPath}/service/list`,
      query: query,
      params: param,
    });
  }

  // /** 获取mcp服务列表 （平台提供的MCP） */
  public getMCPServerList(params: any): Promise<any> {
    const { offset, limit, name, type } = params;
    const param = {
      offset: offset,
      limit: limit,
    };

    const query: any = {};

    if (name !== undefined && name !== null && name !== '') {
      query.name = name;
      query.language = this.isZH() ? 'ZH' : 'EN';
    }

    query[mapKeys.offset] = param.offset;
    query[mapKeys.limit] = param.limit;

    return this.http.getAsync({
      url: `${this.MCPPath}/server/list`,
      query: query,
    });
  }

  /** 复制一个应用 */
  public copyAgent(agent_id: string): Promise<void> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/copy`,
    });
  }

  public copyAgentToASpace(
    agent_id: string,
    target_workspace_id: string,
  ): Promise<void> {
    return this.http.postAsync({
      url: `${this.prefix}/agents/${agent_id}/copy`,
      query: {
        target_workspace_id,
      },
    });
  }

  /** 流式接口：调测已发布的网页版应用  */
  public webPageChatSSE(
    params: any,
    app_type: 'workflows' | 'agents',
    short_code: string,
    conversation_id,
    invokeMode: 'DEBUG' | 'PUBLISHED',
    lang: string,
    {
      onStatus,
      onOpen,
      onMessage,
      onModeration,
      onTimeout,
      onDone,
      onError,
      onAbort,
      onReadyStateChange,
    }: any = {},
    agent_type:string='',
  ): any {
    const nilFunc = () => void 0;

    let seeUrl = `${this.http.prefixPath}/v1/${
      this.ctxServ.projectId
    }/agent-manager/${app_type}/chat/${short_code}/conversations/${conversation_id}?workspace_id=${this.http.getWorkspaceId()}`;

    if (app_type === 'agents') {
      seeUrl = `${this.http.prefixPath}/v1/${
        this.ctxServ.projectId
      }/agent-manager/${app_type}/chat/${short_code}?workspace_id=${this.http.getWorkspaceId()}`;
    }
    if (agent_type) {
      seeUrl = `${seeUrl}&agent_type=${agent_type}`
    }
    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        stream: 'true',
        'X-Language': lang ?? 'zh-cn',
        'X-Invoke-Mode': invokeMode,
        projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage?.getItem('cfCurrentRegion')),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });
    source.addEventListener('status', onStatus ?? nilFunc);
    source.addEventListener('open', onOpen ?? nilFunc);
    source.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source.addEventListener('abort', onAbort ?? nilFunc);
    source.addEventListener('readystatechange', onReadyStateChange ?? nilFunc);
    source.addEventListener('moderation', onModeration ?? nilFunc);
    source.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);

    source.stream();

    return source;
  }

  /** 调试预览 和 知识型应用 的流式接口 */
  knowledgeChatSSE(
    params: any,
    agent_id: string,
    conversation_id: string,
    invokeMode: 'DEBUG' | 'PUBLISHED',
    lang: string,
    {
      onTimeout,
      onDone,
      onStatus,
      onOpen,
      onMessage,
      onError,
      onAbort,
      onReadyStateChange,
      onModeration,
    }: any = {},
    version_id = '',
    app_type: 'agents' | 'workflows' = 'agents',
    assets = false,
    agent_type: string='',
  ): any {
    const nilFunc = () => void 0;
    const assetsSuffix = assets ? '-assets' : ''; //百宝箱页面接口需要添加-assets
    let seeUrl = `${this.http.prefixPath}${
      this.ctxServ.baseUrl
    }/agent-manager/${app_type}${assetsSuffix}/${agent_id}/conversations/${conversation_id}?workspace_id=${this.http.getWorkspaceId()}`;
    if (version_id) {
      seeUrl = `${this.http.prefixPath}${
        this.ctxServ.baseUrl
      }/agent-manager/${app_type}${assetsSuffix}/${agent_id}/conversations/${conversation_id}?version=${version_id}&workspace_id=${this.http.getWorkspaceId()}`;
    }
    if (agent_type) {
      seeUrl = `${seeUrl}&agent_type=${agent_type}`
    }
    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ?.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        'X-Invoke-Mode': invokeMode,
        stream: 'true',
        'X-Language': lang ?? 'zh-cn',
        projectname: JSON.parse(sessionStorage?.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });
    source?.addEventListener('open', onOpen ?? nilFunc);
    source.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('status', onStatus ?? nilFunc);
    source.addEventListener('abort', onAbort ?? nilFunc);
    source?.addEventListener('readystatechange', onReadyStateChange ?? nilFunc);
    source.addEventListener('moderation', onModeration ?? nilFunc);
    source.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source?.addEventListener('done', onDone ?? nilFunc);

    source.stream();

    return source;
  }

  /** 调试预览 和 知识型应用 的流式接口 */
  deepResearchChatSSE(
    params: any,
    agent_id: string,
    conversation_id: string,
    invokeMode: 'DEBUG' | 'PUBLISHED',
    lang: string,
    {
      onStatus,
      onOpen,
      onMessage,
      onError,
      onAbort,
      onReadyStateChange,
      onModeration,
      onTimeout,
      onDone,
    }: any = {},
    app_type: 'agents' | 'workflows' = 'agents',
  ): any {
    const nilFunc = () => void 0;

    let seeUrl = `${this.http.prefixPath}${
      this.ctxServ.baseUrl
    }/agent-manager/agents/${agent_id}/conversations/${conversation_id}?workspace_id=${this.http.getWorkspaceId()}&agent_type=deepresearch`;

    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        'X-Invoke-Mode': invokeMode,
        stream: 'true',
        'X-Language': lang ?? 'zh-cn',
        projectname: JSON.parse(sessionStorage?.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage?.getItem('cfCurrentRegion')),
      },
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
    });
    source.addEventListener('open', onOpen ?? nilFunc);
    source?.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('status', onStatus ?? nilFunc);
    source.addEventListener('abort', onAbort ?? nilFunc);
    source.addEventListener('readystatechange', onReadyStateChange ?? nilFunc);
    source.addEventListener('moderation', onModeration ?? nilFunc);
    source?.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);

    source.stream();

    return source;
  }

  /** f1项目，对话生成应用+工作流+插件的流式接口 */
  generateAppChatSSE(
    params: any,
    agent_id: string,
    conversation_id: string,
    lang: string,
    {
      onStatus,
      onOpen,
      onMessage,
      onError,
      onAbort,
      onReadyStateChange,
      onModeration,
      onTimeout,
      onDone,
    }: any = {},
  ): any {
    const nilFunc = () => void 0;
    let seeUrl = `${this.http.prefixPath}${
      this.ctxServ.baseUrl
    }/f1/agents/${agent_id}/conversations/${conversation_id}?workspace_id=${this.http.getWorkspaceId()}`;

    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        stream: 'true',
        'X-Language': lang ?? 'zh-cn',
        projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });
    source.addEventListener('status', onStatus ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);
    source.addEventListener('abort', onAbort ?? nilFunc);
    source.addEventListener('readystatechange', onReadyStateChange ?? nilFunc);
    source.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('moderation', onModeration ?? nilFunc);
    source.addEventListener('open', onOpen ?? nilFunc);
    source.addEventListener('timeout', onTimeout ?? nilFunc);

    source.stream();

    return source;
  }

  /** 智能优化Prompt的流式接口 */
  optimizePromptSSE(
    params: any,
    agent_id: string,
    lang: string,
    { onMessage, onError, onTimeout, onDone }: any = {},
  ): any {
    const nilFunc = () => void 0;
    let seeUrl = `${this.http.prefixPath}${this.ctxServ.baseUrl.replace(
      'v1',
      'v2',
    )}/agent-builder/prompt/generate?workspace_id=${this.http.getWorkspaceId()}`;

    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        'X-Language': lang ?? 'zh-cn',
        projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
      withCsrf: true,
      timeout: 3600000,
    });
    source.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source?.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);

    source.stream();
    return source;
  }


  /** 试运行multi agent的流式接口 */
  debugMultiAgentSSE(
    params: any,
    agent_id: string,
    conversation_id: string,
    lang: string,
    { onMessage, onError, onTimeout, onDone }: any = {},
    version_id = '',
    assets = false,
  ) {
    const nilFunc = () => void 0;
    const assetsSuffix = assets ? '-assets' : ''; //百宝箱页面接口需要添加-assets
    let seeUrl = `${this.http.prefixPath}${
      this.ctxServ.baseUrl
    }/agent-manager/agents${assetsSuffix}/${agent_id}/conversations/${conversation_id}?type=controller&workspace_id=${this.http.getWorkspaceId()}`;
    if (version_id) {
      seeUrl = `${seeUrl}&version=${version_id}`;
    }
    if (params.environment_id) {
      seeUrl += `&environment_id=${params.environment_id}`;
    }
    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(seeUrl, {
      headers: {
        'Content-Type': 'application/json',
        stream: 'true',
        'X-Language': lang ?? 'zh-cn',
        'X-Invoke-Mode': 'debug',
        projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        'X-Execution-Id': uuidV4(),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });
    source.addEventListener('message', onMessage ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);

    source.stream();
    return source;
  }

  getConfigs(): Promise<IAgentConfigs> {
    return this.http.getAsync({
      url: `${this.ctxServ.baseUrl}/agent-manager/system/settings`,
      query: {
        service: 'front',
        workspace_id: 'default',
      },
    });
  }

  getHealth(paramsUserId?: string, paramsProjectId?: string): Promise<any> {
    const config: any = {
      method: 'GET',
      url: `${this.resource_prefix}/agent-manager/health`,
    };
    if (paramsUserId && paramsProjectId) {
      config.query = {
        'x-user-id': paramsUserId,
        'x-project-id': paramsProjectId,
      };
    }
    return this.http.getAsync(config);
  }


  getLicenseRuery(): Promise<any> {
    return this.http.getAsync({
      url: `${this.resource_prefix}/common/license/query`,
    });
  }



  public exeNode(options: {
    workflowId: string;
    conversationId: string;
    nodeId: string;
    data: {
      inputs: Record<string, any>;
      globals: Record<string, any>;
      plugin_configs: Record<string, any>[];
    };
    invokeMode: 'DEBUG' | 'PUBLISHED';
    lang: string;
    onmessage: (event) => void;
    ondone: () => void;
    onerror: (error) => void;
    ontimeout: () => void;
  }) {
    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const sse = new SSE(
      `${this.http.prefixPath}${this.prefix}/workflows/${
        options.workflowId
      }/conversations/${options.conversationId}/node_execute/${
        options.nodeId
      }?workspace_id=${this.http.getWorkspaceId()}`,
      {
        payload: JSON.stringify(options.data),
        method: 'POST',
        withCsrf: true,
        headers: {
          'Content-Type': 'application/json',
          'X-Invoke-Mode': options.invokeMode,
          'X-Language': options.lang ?? 'zh-cn',
          projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
          region: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        },
        timeout: 3600000,
        streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
        streamTimeout: stream_interval_timeout ?? 60000,
      },
    );

    sse.addEventListener('message', options.onmessage);
    sse.addEventListener('done', options.ondone);
    sse.addEventListener('error', options.onerror);
    sse.addEventListener('timeout', options.ontimeout);

    sse.stream();

    return sse;
  }

  /** 工作流、应用赞踩反馈新接口 */
  conversationFeedback(
    appId: string,
    conversationId: string,
    messageId: number,
    appType: AppType,
    params: {
      rating: number;
      reason?: {
        tags: Array<string>;
        content: string;
      };
      app_name: string;
    },
  ) {
    return this.http.postAsync({
      url: `${this.ctxServ.prefix}/apps/${appId}/conversions/${conversationId}/messages/${messageId}/feedback?app_type=${appType}`,
      params,
    });
  }

  /** 工作流、应用取消赞踩 */
  cancelFeedback(appId: string, conversationId: string, messageId: number) {
    return this.http.deleteAsync({
      url: `${this.prefix}/apps/${appId}/conversions/${conversationId}/messages/${messageId}/feedback`,
    });
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }



  batchDeleteVarByKey(agentId: string, varKeys: Array<string>): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/agents/${agentId}/memories/variables/batch-delete`,
      params: { variable_keys: varKeys },
    });
  }

  getNewLongMemoryVarList(agentId: string): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/agents/${agentId}/memories/variables`,
    });
  }

  getResourceQuantity(type: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/resource-management`,
      query: { resourceType: type },
    });
  }

  ResetAllNewLongMemoryVar(agentId: string): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/agents/${agentId}/memories/variables/reset`,
    });
  }
}
