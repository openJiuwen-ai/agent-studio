import { Injectable } from '@angular/core';
import { KBAbilityRes, KbConstantConfig } from '@routes/knowledge-center/knowledge-base.interface';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import {
  IFile,
  IFileChunkReq,
  IKbListQuery,
  IKbQueryBase,
  IKbSearchRecordRsp,
  IKnowledge,
  IKnowledgeCreateReq,
  IKnowledgeSearchRsp,
  IListFilesResp,
  IListKnowledgeResp,
  ISearchKbHTReq,
  IFileChunkListRsp,
  IKnowledgeDefaultConfigConnection,
} from "@routes/agent-center/app-knowledge/knowledge.types";
import { removeHTMLTag } from 'src/utils/utils';
import { MessageComponent } from '@shared/services/cfdata.service';
import { Clipboard } from '@angular/cdk/clipboard';
import { NzModalService } from 'ng-zorro-antd/modal';
import {
  BatchDeleteRes,
  DeleteTaskParams,
  FaqListQuery,
  FaqListRes,
  KnowledgeChunk,
  KnowledgeFaq,
  SegmentRule,
  SegmentRuleRes, KbTagListRes,
  TaskListRes,
  TaskQuery,
  TaskReq, KbTagCreation, KbTagCreationRes, KbTagQueryParams,
} from '@routes/knowledge-center/knowledge.types';
import { I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';

@Injectable({
  providedIn: 'root',
})
export class KnowledgeRepoService {
  get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager`;
  }

  get prefixV2() {
    return `${this.ctxServ.baseUrl}/agent-manager`.replaceAll('/v1/', '/v2/');
  }

  constructor(
    private http: HttpService,
    private ctxServ: ContextService,
    private clipboard: Clipboard,
    private i18n: I18NextEagerPipe,
    private nzModalService: NzModalService,
  ) {}

  /** 获取知识库列表 */
  getKnowledges(params: IKbListQuery): Promise<IListKnowledgeResp> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges`,
      query: {
        offset: params?.offset,
        limit: params?.limit,
        ...(params?.type && { type: params.type }),
        ...(params?.id && { id: params.id }),
        ...(params?.name && { name: params.name }),
      },
    });
  }

  // 删除知识库
  deleteKb(id: string): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${id}`,
    });
  }

  // 创建知识库
  createKb(params: IKnowledgeCreateReq): Promise<IKnowledge> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges`,
      params,
    });
  }

  // 知识库详情
  retrieveKb(id: string): Promise<IKnowledge> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${id}`,
      timeout: 3000,
    });
  }

  searchKbHitTesting(params: ISearchKbHTReq): Promise<IKnowledgeSearchRsp> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/search-text`,
      params: {
        knowledge_repo_id: params.knowledge_repo_id,
        query: params.query,
        search_mode: params.search_mode,
      },
      query: {
        offset: params.offset,
        limit: params.limit,
      },
    });
  }

  listKbSearchRecords(params: IKbQueryBase): Promise<IKbSearchRecordRsp> {
    const { knowledge_repo_id, ...query } = params;

    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${params.knowledge_repo_id}/search-records`,
      query,
    });
  }

  deleteKbSearchRecord(kbId: string, recordId: string): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${kbId}/search-records/${recordId}`,
    });
  }

  // 编辑知识库
  modifyKb(id: string, params: IKnowledgeCreateReq): Promise<IKnowledge> {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${id}`,
      params,
    });
  }

  // 知识文档
  listFiles(params: IKbQueryBase): Promise<IListFilesResp> {
    const { knowledge_repo_id, ...query } = params;

    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/files`,
      query,
    });
  }

  retrieveFile(kbId: string, fileId: string): Promise<IFile> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${kbId}/files/${fileId}`,
    });
  }

  deleteFile(kbId: string, fileId: string): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${kbId}/files/${fileId}`,
    });
  }

  batchDeleteFile(kbId: string, params) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${kbId}/files/batch-delete`,
      params,
    });
  }

  listFileChunks(params: IFileChunkReq): Promise<IFileChunkListRsp> {
    const { knowledge_repo_id, file_id, ...query } = params;

    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${params.knowledge_repo_id}/files/${params.file_id}/chunks`,
      query,
    });
  }

  createFileChunk(
    knowledge_repo_id: string,
    file_id: string,
    params: KnowledgeChunk,
  ): Promise<void> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/files/${file_id}/chunks`,
      params,
    });
  }

  deleteFileChunk(
    knowledge_repo_id: string,
    file_id: string,
    chunk_id: string,
  ): Promise<void> {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/files/${file_id}/chunks/${chunk_id}`,
    });
  }

  modifyFileChunk(
    knowledge_repo_id: string,
    file_id: string,
    chunk_id: string,
    params: KnowledgeChunk,
  ): Promise<void> {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/files/${file_id}/chunks/${chunk_id}`,
      params,
    });
  }

  uploadFile(kbId: string, file: FormData, query = null): Promise<void> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${kbId}/files`,
      body: file,
      query,
    });
  }

  // 启用知识库
  startKb(id: string) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${id}/start`,
    });
  }

  // 停用知识库
  stopKb(id: string) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${id}/stop`,
    });
  }

  handleKbStop(knowledge_repo_id: string) {
    return new Promise((resolve) => {
      this.nzModalService.create({
        nzTitle: this.i18n.transform('knowledge_close_title', {
          ns: I18nNamespace.KNOWLEDGE,
        }),
        nzContent: this.i18n.transform('knowledgeservice_3', {
          ns: I18nNamespace.COMMON,
        }),
        nzOkText: this.i18n.transform('button_close', {
          ns: I18nNamespace.KNOWLEDGE,
        }),
        nzOnOk: async () => {
          try {
            await this.stopKb(knowledge_repo_id);
            MessageComponent.showSuccess(
              this.i18n.transform('knowledge_close_success', {
                ns: I18nNamespace.KNOWLEDGE,
              }),
            );
            resolve(knowledge_repo_id);
          } catch (e) {
            throw e;
          }
        },
      });
    });
  }

  handleKbStart(knowledge_repo_id: string) {
    return new Promise(async (resolve) => {
      try {
        await this.startKb(knowledge_repo_id);
        MessageComponent.showSuccess(
          this.i18n.transform('knowledge_open_success', {
            ns: I18nNamespace.KNOWLEDGE,
          }),
        );
        resolve(knowledge_repo_id);
      } finally {
      }
    });
  }

  handleIdCopy(knowledge_repo_id: string) {
    this.clipboard.copy(knowledge_repo_id);
    MessageComponent.showSuccess(
      this.i18n.transform('copy_success', {
        ns: I18nNamespace.KNOWLEDGE,
      }),
    );
  }

  handleKbDelete(kb, tiMessage: any) {
    return new Promise((resolve) => {
      const { knowledge_base_id, name } = kb;
      const modalInstance = tiMessage.open({
        type: 'warn',
        content: this.i18n.transform('knowledge_delete_content', {
          ns: I18nNamespace.KNOWLEDGE,
          name: removeHTMLTag(name),
        }),
        title: this.i18n.transform('delete'),
        okButton: {
          click: async () => {
            modalInstance.setLoading(true);
            try {
              await this.deleteKb(knowledge_base_id);
              MessageComponent.showSuccess(
                this.i18n.transform('delete_success'),
              );
              resolve(knowledge_base_id);
            } finally {
              modalInstance.close();
            }
          },
        },
      });
    });
  }

  createSegmentRule(params: SegmentRule) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/rule-regex`,
      params,
    });
  }

  listSegmentRule(query): Promise<SegmentRuleRes> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/rule-regex`,
      query,
    });
  }

  deleteSegmentRule(id: string) {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/rule-regex/${id}`,
    });
  }

  modifySegmentRule(id: string, params: SegmentRule) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/rule-regex/${id}`,
      params,
    });
  }

  listFaq(knowledge_repo_id: string, query: FaqListQuery): Promise<FaqListRes> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq`,
      query,
    });
  }

  createFaq(knowledge_repo_id: string, params: KnowledgeFaq) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq`,
      params,
    });
  }

  modifyFaq(knowledge_repo_id: string, faq_id: string, params: KnowledgeFaq) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq/${faq_id}`,
      params,
    });
  }

  deleteFaq(knowledge_repo_id: string, faq_id: string) {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq/${faq_id}`,
    });
  }

  batchDeleteFaq(knowledge_repo_id: string, params): Promise<BatchDeleteRes> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq/batch-delete`,
      params,
    });
  }

  generateTasks(knowledge_repo_id: string, params: TaskReq) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/tasks`,
      params,
    });
  }

  // 下载知识文档
  retrieveFileContent(knowledge_repo_id: string, file_id: string) {
    return this.http.getBlobAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/files/${file_id}/content`,
      dataType: 'blob',
    });
  }

  // 下载知识文档
  downloadFileFetch(knowledge_repo_id: string, file_id: string): Promise<any> {
    return this.http.getBlobAsync({
      method: 'GET',
      url: `${this.prefixV2}/knowledge-bases/${knowledge_repo_id}/files/${file_id}/content`,
      dataType: 'blob',
    });
  }

  uploadFaqFile(knowledge_repo_id: string, file: FormData) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files`,
      body: file,
    });
  }

  // 下载FAQ文档
  downloadFaqFile(knowledge_base_id: string, file_id: string) {
    return this.http.getBlobAsync({
      url: `${this.prefix}/knowledges/${knowledge_base_id}/faq-files/${file_id}`,
      dataType: 'blob',
    });
  }

  // 下载FAQ文档
  downloadFaqFileFetch(knowledge_base_id: string, file_id: string): Promise<any> {
    return this.http.getBlobAsync({
      method: 'GET',
      url: `${this.prefixV2}/knowledge-bases/${knowledge_base_id}/faq-files/${file_id}/content`,
      dataType: 'blob',
    });
  }


  listFaqFiles(
    knowledge_repo_id: string,
    query,
    params?: any,
  ): Promise<IListFilesResp> {
    const { limit, offset } = query ?? {};
    const { file_name, ids, file_status } = params ?? {};

    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files`,
      query: {
        ...(offset !== undefined && { offset }),
        ...(limit !== undefined && { limit }),
        ...(file_name !== undefined && { name: file_name }),
        ...(ids !== undefined && { ids }),
        ...(file_status !== undefined && { status: file_status }),
      },
    });
  }

  deleteFaqFile(knowledge_repo_id: string, file_id: string) {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files/${file_id}`,
    });
  }

  createFaqChunk(knowledge_repo_id: string, file_id: string, params) {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files/${file_id}/chunks`,
      params,
    });
  }

  deleteFaqChunk(knowledge_repo_id: string, file_id: string, chunk_id: string) {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files/${file_id}/chunks/${chunk_id}`,
    });
  }

  modifyFaqChunk(
    knowledge_repo_id: string,
    file_id: string,
    chunk_id: string,
    params,
  ) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files/${file_id}/chunks/${chunk_id}`,
      params,
    });
  }

  listFaqChunks(
    knowledge_repo_id: string,
    file_id: string,
    query,
  ): Promise<IFileChunkListRsp> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/faq-files/${file_id}/chunks`,
      query,
    });
  }

  listTasks(knowledge_repo_id: string, query: TaskQuery): Promise<TaskListRes> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/tasks`,
      query,
    });
  }

  deleteTask(knowledge_repo_id: string, params: DeleteTaskParams): Promise<BatchDeleteRes> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${knowledge_repo_id}/tasks/batch-delete`,
      params,
    });
  }

  uploadAvator(file: FormData): Promise<{ file_name: string }> {
    return this.http.postAsync({
      url: `${this.prefix}/upload-avatar`,
      body: file,
    });
  }

  // 知识库列表（创建）
  getKnowledgeBaseList(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases`,
      cancelGlobalError: params?.cancelGlobalError,
      query: {
        ids: params?.ids ?? [],
        offset: params?.offset,
        limit: params?.limit,
        ...(params?.status && { status: params.status }),
        ...(params?.name && { name: params.name }),
        ...(params?.type && { type: params.type }),
        ...(params?.knowledge_base_connection_id && { knowledge_base_connection_id: params.knowledge_base_connection_id }),
        ...(params?.knowledge_base_ids && { knowledge_base_ids: params.knowledge_base_ids }),
        ...(params?.share_scope && { share_scope: params.share_scope }),
        ...(params?.share_type && { share_type: params.share_type }),
        ...(params?.knowledge_base_type != null && { knowledge_base_type: params.knowledge_base_type }),
      },
    });
  }

  // 编辑知识库
  editKnowledgeBase(id: string, params: any): Promise<any> {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${id}`,
      params,
    });
  }

  // 接入知识库列表
  getAccessKnowledgeBaseList(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/external`,
      query: {
        offset: params?.offset,
        limit: params?.limit,
        knowledge_base_connection_id: params.knowledge_base_connection_id,
        ...(params?.name && { name: params.name }),
      },
    });
  }

  // 新增第三方知识库
  createThirdPartyKnowledgeBase(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/external`,
      params,
    });
  }

  // 页面接入知识库tab里面的内容
  // 创建第三方知识库连接
  accessThirdPartyKnowledgeBase(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections`,
      params,
    });
  }

  // 查询第三方知识库连接列表
  getThirdPartyKnowledgeBaseList(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections`,
      query: {
        offset: params?.offset,
        limit: params?.limit,
        ...(params?.name && { name: params.name }),
        ...(params?.connector_id && { connector_id: params.connector_id }),
      },
    });
  }

  // 查询第三方知识库连接详情
  getThirdPartyKnowledgeBaseDetail(knowledge_base_connection_id: string): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections/${knowledge_base_connection_id}`,
    });
  }

  // 删除第三方知识库连接
  deleteThirdPartyKnowledgeBase(knowledge_base_connection_id: string): Promise<void> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.deleteAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections/${knowledge_base_connection_id}`,
    });
  }

  // 编辑第三方知识库连接
  editThirdPartyKnowledgeBase(knowledge_base_connection_id: string, params: any): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.putAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections/${knowledge_base_connection_id}`,
      params,
    });
  }

  // 查询第三方知识库连接器
  getThirdPartyKnowledgeBaseConnectors(): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connectors`,
    });
  }

  // 用于测试第三方知识库连接是否正常
  testThirdPartyKnowledgeBase(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections/test-connection`,
      params,
    });
  }

  // 测试指定第三方知识库连接是否正常
  pointTestThirdPartyKnowledgeBase(knowledge_base_connection_id): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/third-party/knowledge-bases/connections/${knowledge_base_connection_id}/test-connection`,
    });
  }

  getKBAbilities(connectionId: string): Promise<KBAbilityRes> {
    const query = {
      connection_id: connectionId,
      workspace_id: this.ctxServ.currentWorkspaceId,
    }
    return this.http.getAsync({
      url: `${this.prefixV2}/knowledge-bases/connectors/abilities`,
      query,
    });
  }

  getWebPath(str,url) {
    const index = str.indexOf('/v1');
    return str.substring(0, index) + url;
  }

  //查看图片
  previewImg(url) {
    return this.http.getBlobAsync({
      url:this.getWebPath(this.prefix,url),
      dataType: 'blob',
    });
  }

  queryImage(imageId: string): Promise<Blob> {
    return this.http.getBlobAsync({
      url: `${this.prefixV2}/knowledge-bases/images/${imageId}`,
      dataType: 'blob',
    });
  }

  // 查询知识库使用的模型列表
  getKnowledgeBaseUseModel(params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/models`,
      query: {
        offset: 0,
        limit: 1000,
        ...(params?.model_name && { model_name: params.model_name }),
        ...(params?.model_type && { model_type: params.model_type }),
        ...(params?.repo_id && { repo_id: params.repo_id }),
      },
    });
  }

  // 查询知识库默认配置详情
  getKnowledgeDefaultConfigDetail(kbConnectionId): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/configurations/default-connections/${kbConnectionId}`,
    });
  }

  // 创建知识库默认配置
  createKnowLedgeDefaultConfig(params: IKnowledgeDefaultConfigConnection): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/configurations/default-connections`,
      params,
    });
  }

  // 编辑知识库默认配置
  updateKnowLedgeDefaultConfig(params: IKnowledgeDefaultConfigConnection, kbConnectionId): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.putAsync({
      url: `${v2Prefix}/knowledge-bases/configurations/default-connections/${kbConnectionId}`,
      params,
    });
  }

  // 知识库默认配置测试连接
  testKnowLedgeDefaultConfig(params: IKnowledgeDefaultConfigConnection): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/configurations/default-connections/test-connection`,
      params,
    });
  }

  // 知识库默认配置测试连接
  testKnowLedgeDefaultConfigById( kbConnectionId): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/configurations/default-connections/${kbConnectionId}/test-connection`,
    });
  }

  // 查询OBS桶名
  queryObsBucketName(): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/obs-bucket-names`,
    });
  }

  // 查询OBS桶下面的文件路径
  queryObsBucketsDir(params: {bucketName: string, dir: string}): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/obs-bucket-objects`,
      params
    });
  }

  // 查询OBS执行记录
  queryObsExecuteRecords(obsConfigId: string, kbId: string, params: { offset: number, limit: number }): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/${kbId}/obs-configs/${obsConfigId}/execute-records`,
      query: params
    });
  }

  // 查询OBS配置
  queryObsConfigs(kbId: string): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.getAsync({
      url: `${v2Prefix}/knowledge-bases/${kbId}/obs-configs`,
    });
  }

  // 执行OBS文件上传任务
  executeObsFileUpload(kbId: string, obsConfigId: string) {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/${kbId}/obs-configs/${obsConfigId}/execute`,
      params: { action: "UPLOAD" },
    });
  }

  // 保存ObsConfig配置
  saveObsConfig(kbId: string, params: { obs_bucket_name: string, obs_input_directory:string }) {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.postAsync({
      url: `${v2Prefix}/knowledge-bases/${kbId}/obs-configs`,
      params,
    });
  }

  // 修改共享状态
  changeKbScope(kbId: string, params): Promise<any> {
    let v2Prefix = this.prefix.replaceAll('/v1/', '/v2/');
    return this.http.putAsync({
      url: `${v2Prefix}/knowledge-bases/${kbId}/permissions`,
      params,
    });
  }

  getKbConfig(kbId?: string): Promise<{ configs: KbConstantConfig[] }> {
    return this.http.getAsync({
      url: `${this.prefixV2}/knowledge-bases/configs`,
      query: kbId ? {
        knowledge_base_id :kbId,
      } : null
    });
  }

  getKbTags(kbId: string, query: KbTagQueryParams): Promise<KbTagListRes> {
    return this.http.getAsync({
      url: `${this.prefix}/knowledges/${kbId}/tags`,
      query,
    });
  }

  createKbTag(kbId: string, params: KbTagCreation): Promise<KbTagCreationRes> {
    return this.http.postAsync({
      url: `${this.prefix}/knowledges/${kbId}/tags`,
      params,
    });
  }

  delKbTag(kbId: string, tagId: string, params: { tag_name: string }) {
    return this.http.deleteAsync({
      url: `${this.prefix}/knowledges/${kbId}/tags/${tagId}`,
      params,
    });
  }

  editFileInfo(kbId: string, fileId: string, params: { tags: string[] }) {
    return this.http.putAsync({
      url: `${this.prefix}/knowledges/${kbId}/files/${fileId}`,
      params,
    });
  }
}
