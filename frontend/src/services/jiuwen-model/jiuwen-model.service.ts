import { Injectable } from '@angular/core';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { JiuwenSse } from '@services/jiuwen-model/jiuwen-sse';
import { ModelType } from '@enums/jiuwen-model.enum';

@Injectable({
  providedIn: 'root',
})
export class JiuwenModelService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/model-manager`;
  }

  get prefixChatSseManager() {
    return `${this.http.prefixPath}/v1/${this.ctxServ.projectId}/agent-manager/agent-builder`;
  }

  get prefixChatManager() {
    return `${this.ctxServ.baseUrl}/agent-manager/agent-builder`;
  }


  constructor(
    private http: HttpService,
    private ctxServ: ContextService,
    private configServ: AgentConfigService,
  ) {}

  public getModelProvidersInfo(source: string, id: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${source}/providers/${id}`,
    });
  }

  public getModelService(
    model_type: string = ModelType.LLM,
    publish_status: string = 'all',
    provider_id: string = null,
  ): Promise<any> {
    const query: any = {
      model_type,
      publish_status,
    };

    if (provider_id !== null) {
      query.provider_id = provider_id;
    }

    return this.http.getAsync({
      url: `${this.prefix}/available/model-services`,
      query: query,
    });
  }

  private configureJiuwenSse(
    seeUrl: string,
    params: any,
    lang: string,
    handlers: {
      onStatus?: () => void;
      onOpen?: () => void;
      onMessage?: (event: any) => void;
      onError?: (event: any) => void;
      onAbort?: () => void;
      onReadyStateChange?: (event: any) => void;
      onModeration?: (event: any) => void;
      onTimeout?: () => void;
      onDone?: () => void;
    } = {},
    extraHeaders?: Record<string, string>,
  ): JiuwenSse {
    const nilFunc = () => void 0;
    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      stream: 'true',
      'X-Language': lang ?? 'zh-cn',
    };
    if (extraHeaders) {
      Object.keys(extraHeaders).forEach(key => {
        headers[key] = extraHeaders[key];
      });
    }

    const source = new JiuwenSse(seeUrl, {
      headers,
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });

    // 添加事件监听器

    source.addEventListener(
      'readystatechange',
      handlers.onReadyStateChange ?? nilFunc,
    );
    source.addEventListener('moderation', handlers.onModeration ?? nilFunc);
    source.addEventListener('timeout', handlers.onTimeout ?? nilFunc);
    source.addEventListener('error', handlers.onError ?? nilFunc);
    source.addEventListener('open', handlers.onOpen ?? nilFunc);
    source.addEventListener('message', handlers.onMessage ?? nilFunc);
    source.addEventListener('status', handlers.onStatus ?? nilFunc);
    source.addEventListener('abort', handlers.onAbort ?? nilFunc);
    source.addEventListener('done', handlers.onDone ?? nilFunc);

    source.stream();

    return source;
  }

  /** 流式接口：调测模型  */
  public modelTestChatSSE(
    params: any,
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
    apiUrlEnvOverrides?: Record<string, string>,
    environmentId?: string,
  ): any {
    let seeUrl = `${
      this.prefixChatSseManager
    }/chat/completions?workspace_id=${this.http.getWorkspaceId()}&refresh=true`;
    if (apiUrlEnvOverrides && Object.keys(apiUrlEnvOverrides).length) {
      seeUrl += `&api_url_env_vars=${encodeURIComponent(JSON.stringify(apiUrlEnvOverrides))}`;
    }
    const extraHeaders: Record<string, string> | undefined = environmentId
      ? { 'X-Environment-Id': environmentId }
      : undefined;
    return this.configureJiuwenSse(seeUrl, params, lang, {
      onStatus,
      onOpen,
      onMessage,
      onError,
      onAbort,
      onReadyStateChange,
      onModeration,
      onTimeout,
      onDone,
    }, extraHeaders);
  }

  /** 非流式接口：调测模型  */
  public modelTestChat(params: any, signal?: AbortSignal, apiUrlEnvOverrides?: Record<string, string>, environmentId?: string) {
    const query: any = { refresh: "true" }; //接口参数有更新
    if (apiUrlEnvOverrides && Object.keys(apiUrlEnvOverrides).length) {
      query.api_url_env_vars = JSON.stringify(apiUrlEnvOverrides);
    }
    return this.http
      .postAsync({
        url: `${this.prefixChatManager}/chat/completions`,
        query,
        params: params,
        signal,
        timeout: 120_000,
        headers: environmentId ? { 'X-Environment-Id': environmentId } : undefined,
      })
      .then(async (res: any) => {
        if (!res?.choices) {
          throw {
            data: {
              error_msg: JSON.parse(res.model_response).error.message,
            },
          };
        }
        return {
          content: res?.choices[0]?.message?.content ?? '',
          reasoning_content: res?.choices[0]?.message?.reasoning_content ?? '',
        };
      });
  }

  /** 非流式接口：文本向量化 */
  public modelTestEmbedding(params: any, signal?: AbortSignal, apiUrlEnvOverrides?: Record<string, string>, environmentId?: string) {
    const query: any = { refresh: "true" };
    if (apiUrlEnvOverrides && Object.keys(apiUrlEnvOverrides).length) {
      query.api_url_env_vars = JSON.stringify(apiUrlEnvOverrides);
    }
    return this.http
      .postAsync({
        url: `${this.prefixChatManager}/embeddings`,
        query,
        params: params,
        signal,
        timeout: 120_000,
        headers: environmentId ? { 'X-Environment-Id': environmentId } : undefined,
      })
      .then(async (res: any) => {
        return res?.data ?? null;
      });
  }

  /** 非流式接口：文本排序 */
  public modelTestReRank(params: any, signal?: AbortSignal, apiUrlEnvOverrides?: Record<string, string>, environmentId?: string) {
    const query: any = { refresh: "true" };
    if (apiUrlEnvOverrides && Object.keys(apiUrlEnvOverrides).length) {
      query.api_url_env_vars = JSON.stringify(apiUrlEnvOverrides);
    }
    return this.http
      .postAsync({
        url: `${this.prefixChatManager}/rerank`,
        query,
        params: params,
        signal,
        timeout: 120_000,
        headers: environmentId ? { 'X-Environment-Id': environmentId } : undefined,
      })
      .then(async (res: any) => {
        return res?.results ?? null;
      });
  }
}
