import { Injectable } from '@angular/core';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import { ModelType } from '@enums/jiuwen-model.enum';
import { ModelSquareListRes } from './model-management.interface';
import { catchError, map, Observable, of } from 'rxjs';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonUtils } from 'src/utils/common.util';
import { CommonService } from '@services/common.service';

/** 模型导入预检单行结果（与后端 ModelImportPreviewItem 字段对齐，snake_case）。 */
export interface ModelImportPreviewItem {
  id: string | null;
  service_name: string | null;
  provider_id: string | null;
  conflict: boolean;
  signature_valid: boolean;
  api_url_valid: boolean;
  env_var_valid: boolean;
  cipher_adapted: boolean | null;
  detail: string | null;
  /** 行类型：MODEL=模型行，PROVIDER=空供应商壳行（用于第一列标题动态切换）。 */
  type: string;
}

/** 模型导入预检响应。 */
export interface ModelImportPreviewRsp {
  total_count: number;
  conflict_count: number;
  items: ModelImportPreviewItem[];
}

/** 模型导入结果单行（与后端 ImportRes 字段对齐）。 */
export interface ModelImportResultItem {
  id: string | null;
  name: string;
  type: string;
  status: string;
  detail: string;
}

/** 模型导入响应（仅取需要的字段）。 */
export interface ModelImportRsp {
  succeed_len: number;
  failed_len: number;
  skipped_len: number;
  count: number;
  succeed_ids: string[];
  failed_ids: string[];
  skipped_ids: string[];
  import_list: ModelImportResultItem[];
}

@Injectable({
  providedIn: 'root',
})
export class ModelManagementService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/model-manager`;
  }

  get observatoryPrefix() {
    return this.ctxServ.baseUrl;
  }

  private controller = new AbortController();
  private subscribeMap: Map<string, boolean> = new Map();

  constructor(private http: HttpService, private ctxServ: ContextService, private configServ: AgentConfigService, private commonService: CommonService) {}

  public getPublisherList(query, source): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${source}/providers`,
      query,
    });
  }

  public getModelPublisherInfo(id, source): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/${source}/providers/${id}`,
    });
  }

  public createModelProviders(params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/integration/providers`,
      params,
    });
  }

  public updateModelProviders(id, params): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/integration/providers/${id}`,
      params,
    });
  }

  public deleteProvider(id): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.prefix}/integration/providers/${id}`,
    });
  }

  public getModelList(query): Promise<ModelSquareListRes> {
    return this.http.getAsync({
      url: `${this.prefix}/model-services`,
      query,
    });
  }

  public getModelSubscribeSetting(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/user-subscribe-settings`,
    });
  }

  public subscribeModels(params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/model-services/subscribe`,
      params,
    }).then(() => this.getMaaSModalSubscribe(true));
  }

  public getModelService(model_type: string = ModelType.LLM): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/available/model-services?model_type=${model_type}`,
    });
  }
  public getAvailableModelList(
    query?: any,
    signal?: AbortSignal,
  ): Promise<any> {
    return Promise.all([
      this.getMaaSModalSubscribe(),
      this.http.getAsync<any>({
        url: `${this.prefix}/available/model-services`,
        query,
        signal,
      })
    ]).then(([map, res]) => {
      return res;
    });
  }

  public publishModelInfo(model_id, status, query): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/model-services/${model_id}/${status}`,
      query: query,
    });
  }

  public createModel(params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/model-services`,
      params,
    });
  }

  public updateModel(model_id, params): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/model-services/${model_id}`,
      params,
    });
  }


  public checkModelName(query): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/model-services/model-name/check`,
      query,
    });
  }
  public deleteModel(model_id) {
    return this.http.deleteAsync({
      url: `${this.prefix}/model-services/${model_id}`,
    });
  }

  public getProviderAuths(query) {
    return this.http.getAsync({
      url: `${this.prefix}/provider/auths`,
      query,
    });
  }

  public postProviderAuths(params, query) {
    return this.http.postAsync({
      url: `${this.prefix}/provider/auths`,
      params,
      query,
    });
  }

  public deleteProviderAuths(id) {
    return this.http.deleteAsync({
      url: `${this.prefix}/provider/auths/${id}`,
    });
  }

  public modifyModel(model_id, params) {
    return this.http.putAsync({
      url: `${this.prefix}/custom-models/${model_id}`,
      params,
    });
  }

  public getModelInfo(model_id): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/model-services/${model_id}`,
    });
  }

  public getModels(query, params): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/custom-models/search`,
      query,
      params,
    });
  }

  public getProviders(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/custom-models/provider`,
    });
  }

  public getAPIType(provider_id): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/custom-models/${provider_id}/api-type`,
    });
  }

  //删除路由策略
  public deleteModelRouterStrategies(strategy_id) {
    return this.http.deleteAsync({
      url: `${this.ctxServ.baseUrl}/model-router-strategies/${strategy_id}`,
    });
  }

  public getAvailableProvidersModelList(): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/available/providers/models`,
    });
  }

  //删除部署应用
  public deleteAgentDeployment(agent_id) {
    return this.http.deleteAsync({
      url: `${this.observatoryPrefix}/ops/deploy/${agent_id}`,
    });
  }

  // 删除评测集
  public deleteDatasets(id) {
    return this.http.deleteAsync({
      url: `${this.observatoryPrefix}/ops/evaluation-sets/${id}`,
    });
  }

  // 删除评测任务
  public deleteExperiment(params): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.observatoryPrefix}/ops/evaluation/experiment/delete`,
      params: {
        experiment_id_list: params,
      },
    });
  }

  // 删除评测算子
  public deleteEvaluators(id): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.observatoryPrefix}/ops/evaluators/${id}`,
    });
  }


  public getInterfaceProtocoList( query?:any): Promise<any> {
    return this.http.getAsync({
      url: `${this.prefix}/interface-protocol`,
      query,
    });
  }

  public postApiAuth(params) {
    return this.http.postAsync({
      url: `${this.observatoryPrefix}/api-auth/api-keys`,params
    });
  }

  public getApiAuthLists(query) {
    return this.http.getAsync({
      url: `${this.observatoryPrefix}/api-auth/api-keys/list`,
      query
    });
  }

  public deleteApiAuth(id) {
    return this.http.deleteAsync({
      url: `${this.observatoryPrefix}/api-auth/api-keys/${id}`,
    })
  }
  public getSynchronizeModelService(provider_id): Promise<any> {
    return this.http.postAsync({
      url: `${this.prefix}/model-services/sync?provider_id=${provider_id}`,
    });
  }

  /**
   * 批量导出模型服务为签名 JSONL 文件（Blob）。
   * workspace_id 由 HttpService.mergeConfig 自动注入为 query 参数。
   * @param includeProvider true=供应商+模型（缺省），false=只导模型（详情页用，模型挂到目标供应商）
   */
  public exportModels(modelIds: string[], opts?: { includeProvider?: boolean }): Promise<Blob> {
    return this.http.postBlobAsync({
      url: `${this.prefix}/model-services/export`,
      params: { model_ids: modelIds, include_provider: opts?.includeProvider ?? true },
    });
  }

  /**
   * 按供应商导出（供应商列表页卡片入口）：导出该供应商+其下全部模型。
   */
  public exportModelsByProvider(providerId: string): Promise<Blob> {
    return this.http.postBlobAsync({
      url: `${this.prefix}/model-services/export`,
      params: { provider_id: providerId },
    });
  }

  /**
   * 模型导入预检：上传 .jsonl → 解析+验签+冲突检测+URL/占位符校验，不落库。
   * @param targetProviderId 目标供应商 id（详情页只导模型导入用，模型重定向挂到该供应商）
   */
  public previewImportModels(file: File, targetProviderId?: string): Promise<ModelImportPreviewRsp> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    const query: Record<string, string> = {};
    if (targetProviderId) {
      query['target_provider_id'] = targetProviderId;
    }
    return this.http.postAsync({
      url: `${this.prefix}/model-services/import/preview`,
      query,
      params: formData,
      cancelGlobalError: true,
    });
  }

  /**
   * 批量导入模型服务（落库，保留跨环境 id）。conflict_strategy: SKIP | COVER。
   * @param targetProviderId 目标供应商 id（详情页只导模型导入用，模型重定向挂到该供应商）
   */
  public importModels(file: File, conflictStrategy: string, targetProviderId?: string): Promise<ModelImportRsp> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    const query: Record<string, string> = { conflict_strategy: conflictStrategy };
    if (targetProviderId) {
      query['target_provider_id'] = targetProviderId;
    }
    return this.http.postAsync({
      url: `${this.prefix}/model-services/import`,
      query,
      params: formData,
      cancelGlobalError: true,
    });
  }

  /**
   * 查询MaaS模型的开通状态
   * @returns
   */
  public getMaaSModalSubscribe(isRefresh = false): Promise<any> {
    return Promise.resolve(new Map());
  }
}
