import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
} from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { isNil, isNaN } from 'lodash';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageComponent } from '@shared/services/cfdata.service';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { AppConversationRepoService } from '@services/repositories/app-conversation-repo.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { RightOpPanelComponent } from '../components/right-op-panel/right-op-panel.component';
import { getUsedUp, isSystemTypeWithNames } from '@routes/agent-center/utils';
import { v4 as uuidV4 } from 'uuid';
import type {
  IWorkflowField,
  IWorkflowFieldType,
} from '@routes/agent-center/app-flow/node.type';
import { WorkflowChatBaseComponent } from '@shared/base/workflow-chat-base.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import CommonLogic from '../../app-center/common-logic-app-center';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import flowCommonLogic from '../../agent-center/app-flow/common-logic-workflow';
import { IChatFlowAppDetail } from '@routes/agent-center/app-flow/app-flow.types';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { Subscription } from "rxjs";
import { PermissionService } from "@services/permission.service";
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { SHARE_PAGE, SHARE_TOOL_TYPE } from '../components/edit-share-modal/edit-share-modal.config';
import { RightSharePanelComponent } from '../components/right-share-panel/right-share-panel.component';
import { ShareDetailBtnComponent } from '../components/share-detail-btn/share-detail-btn.component';
import { SHARE_TYPE, ShareTypeTag } from '../app-center-management/app-center-management.config';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { ShareService } from '../components/edit-share-modal/share.service';
import { ContextService } from '@services/context.service';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';
import { AppExceedModalComponent } from '@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component';
import { ERROR_CODE } from '@routes/agent-center/types/common.types';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';

@Component({
  selector: 'meta-scenario-example-page',
  templateUrl: './scenario-example-page.component.html',
  styleUrls: ['./scenario-example-page.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    DynamicNodeParamsComponent,
    AppMarkdownAnswerComponent,
    RightOpPanelComponent,
    RightSharePanelComponent,
    ShareDetailBtnComponent,
    AppExceedModalComponent,
    NzIconModule,
    NzButtonModule,
    NzSelectModule,
    NzAlertModule,
    NzSpinModule,
    NzToolTipModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class ScenarioExamplePageComponent
  extends WorkflowChatBaseComponent
  implements OnInit {
  @ViewChild('dynamicNodeParams')
  override dynamicNodeParams!: DynamicNodeParamsComponent;

  @ViewChild('chatContainerRef') override chatContainerRef!: ElementRef;

  @ViewChild('appExceedModalScenario') appExceedModalScenario: AppExceedModalComponent;

  public scenarioExampleInfo: IChatFlowAppDetail = {
    title: '',
    icon: '',
    model_name: '',
    tags: [],
    workflows: [],
    tools: [],
    creator: '',
    description: '',
    knowledge_repos: [],
    published_on: '',
    free_trial_quota: null,
  };
  public usedUp = false;

  /** 管理查询场景型对话基本信息接口的loading。最前置的loading，完成后，才能操作场景型体验页 */
  public isLoading = false;

  /** 控制 alert 警告的显隐。dismissOnTimeout属性会把open置为false */
  public open = true;

  public alertText = '';

  public isShowStopIcon = false;

  override chatLoop = [
    CommonLogic.createFlowChatItem({
      query: '',
      dialogId: uuidV4(),
      options: { showCopiedTip: false },
    }),
  ];

  public showBackIcon = true;

  public appId = '';

  private uuid = uuidV4();

  private appType = '';
  public currentPermissions: any;
  private permissionSubscription: Subscription;

  private workflowFailedMsg = '';
  public isShare = false;
  public canEditShare = false;
  public visionsOptions = [
  ];
  public visionSelected = '';
  toolType = SHARE_TOOL_TYPE.workflow;
  pageType = SHARE_PAGE.apply;
  public shareInfo: any = {};
  public placeholder1 = this.i18n.transform('select_placeholder');
  private isFromOverview: boolean = false;
  constructor(
    protected override appFlowServe: AppFlowService,
    protected override appAgentServe: AppAgentRepoService,
    protected override configServ: AgentConfigService,
    protected override commonLogic: agentCommonLogic,
    protected override monacoLoader: MonacoEditorLoaderService,
    protected override i18n: I18NextEagerPipe,
    protected override cdr: ChangeDetectorRef,
    protected override agentDataServe: AgentDataService,
    protected override pluginRepoServe: AppPluginRepoService,
    private router: Router,
    private clipboard: Clipboard,
    private route: ActivatedRoute,
    private appLibraryRepoServe: AppLibraryRepoService,
    private conversationServe: AppConversationRepoService,
    private agentRepoServe: AppAgentRepoService,
    private permissionService: PermissionService,
    private sidebarServ: SetSidebarVisibilityService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private shareService: ShareService,
    private messageService: NzMessageService,
    private modalService: NzModalService,
  ) {
    super(
      appFlowServe,
      appAgentServe,
      configServ,
      commonLogic,
      monacoLoader,
      i18n,
      cdr,
      agentDataServe,
      pluginRepoServe,
    );

    this.route.paramMap.subscribe((params) => {
      this.appId = params.get('appId');
      this.appType = params.get('appType');
    });
    this.isShare = this.route.snapshot.queryParams.isShare === 'true';
    this.visionSelected = this.route.snapshot.queryParams.releaseVersion;
  }

  override ngOnInit() {
    this.route.queryParams.subscribe(async (params) => {
      let { from } = params;
      if (from && from === 'overview') {
        this.isFromOverview = true;
      }
    });
    this.sidebarServ.setSidebarsVisibilityByState('init');
    if (this.isShare) {
      this.getShareDetail();
    } else{
      if (this.appType === 'web-page') {
        this.showBackIcon = false;
        this.getWebPageInfo(this.appId);
      } else {
        this.showBackIcon = true;
        this.getScenarioBotInfo();
      }
    }

    this.permissionSubscription = this.permissionService.permissions$.subscribe(
      permissions => {
        this.currentPermissions = permissions;
      }
    );
  }

  // 在任务型工作流的网页版和百宝箱这2处场景下，无需调用test-status接口。因此重写shouldUpdatePublishBtn，始终返回false
  override shouldUpdatePublishBtn(): boolean {
    return false;
  }

  override onParamsValid() {
    // 把右侧【结果生成】的数据恢复默认值
    this.chatLoop = [
      CommonLogic.createFlowChatItem({
        query: '',
        dialogId: uuidV4(),
        options: { showCopiedTip: false },
      }),
    ];

    let startInputsList = this.getRunWorkflowParams() || {};
    // 试运行里，针对非必填参数，若不填，则body体不带。避免出现{ 可选变量名:null }或{ 可选变量名:'' }
    startInputsList = Object.entries(startInputsList).reduce(
      (acc, [key, value]) => {
        if (!(isNil(value) || value === '' || isNaN(value))) {
          acc[key] = value;
        }
        return acc;
      },
      {},
    );
    this.debugWorkflow(startInputsList, this.chatLoop.length - 1);
    this.cdr.markForCheck();
  }

  override onMessage(curIndex: number, token: any) {
    super.onMessage(curIndex, token);

    const chunkObj = token.data && flowCommonLogic.stringToObject(token.data);
    const { event, data } = chunkObj;
    const { message } = data;

    if (event === 'error') {
      this.isStreamFail = true;
      this.workflowFailedMsg = message;
    }
  }

  override onDone(curIndex: number, token: any) {
    super.onDone(curIndex, token);

    if (this.isStreamFail) {
      this.showErrorState(this.workflowFailedMsg);
    } else {
      this.isShowStopIcon = false;
    }
  }

  override onError(curIndex: number, error: any) {
    this.isRequesting = false;
    let failedMsg = '';
    let quotaUsedUp = false;
    if (error.data) {
      try {
        const errInfo = JSON.parse(error.data);
        quotaUsedUp = errInfo?.error_code === ERROR_CODE.QUOTA_USED_UP;
        if (errInfo?.error_msg) {
          failedMsg = errInfo.error_msg;
        } else {
          failedMsg = this.i18n.transform('NetErrorTips');
        }
      } catch {
        failedMsg = this.i18n.transform('NetErrorTips');
      }
    }
    this.isStreamFail = true;
    if (quotaUsedUp) {
      this.usedUp = true;
    } else {
      this.showErrorState(failedMsg);
    }
  }

  override onTimeout(curIndex: number) {
    this.isRequesting = false;
    this.sseInstance?.close();
    this.isStreamFail = true;
    this.showErrorState(this.i18n.transform('streaming_timeout'));
  }

  private getWebPageInfo(shortCode: string) {
    this.isLoading = true;
    this.agentRepoServe
      .getWebPageInfo(shortCode, 'short_code', 'WEB_PAGE')
      .then((res) => {
        this.scenarioExampleInfo = {
          icon: res.icon,
          title: res.name,
          model_name: res.model_name,
          tags: res.tags,
          workflows: res.workflows,
          tools: res.tools,
          creator: res.creator,
          description: res.description || res.desc,
          knowledge_repos: res.knowledge_repos,
          published_on: res.published_on,
          free_trial_quota: res.free_trial_quota,
        };
        this.usedUp = getUsedUp(res.free_trial_quota);
        const startNode = res.nodes?.find((node) => node.type === 'Start');
        this.startNodeParams = startNode.outputs
          .map((param: IWorkflowField) => {
            if (!param?.value?.default) {
              param.value = {
                default: '',
                type: 'generated',
                hint: '',
                content: '',
              };
            }
            const schema = param.schema as IWorkflowField;

            if (param.type === 'array' && schema) {
              param.type =
                `${param.type}<${schema.type}>` as IWorkflowFieldType;
            }

            return { ...param };
          })
          .filter(
            (item: any) =>
              !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
          );
      })
      .finally(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  public onClickBack() {
    if (this.isFromOverview) {
      this.router.navigate(['/home/overview']);
      return;
    }
    let state: any = {
      formTab: this.isShare ? 'share':'',
    }
    if (this.canEditShare) {
      state.myShare = true;
    }
    this.router.navigate([`home/app-library`],{
      state
    });
  }

  // 复制到工作台
  async copyToWorkbench(): Promise<void> {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    this.appLibraryRepoServe
      .copyToWorkbench(this.appId, 'workflow')
      .then((res: any) => {

        if (res.resource_id){
          const modalInstance = this.modalService.create({
            nzTitle: this.i18n.transform('copy_tip1'),
            nzContent: '',
            nzFooter: [
              {
                label: this.i18n.transform('cancel'),
                onClick: () => modalInstance.destroy()
              },
              {
                label: this.i18n.transform('confirm'),
                type: 'primary',
                onClick: () => {
                  this.router.navigate(['/home/agent-center/app-flow/flow'], {
                    queryParams: {
                      id: res.resource_id,
                    },
                  });
                  modalInstance.destroy();
                },
              },
            ],
          });
        }

      });
  }

  async isResourceExceed() {
    const res = await this.appAgentServe.getResourceQuantity('agent');
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount };
        this.appExceedModalScenario.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }

  /** 复制按钮disabled属性，要使用相反的返回值（流式生成中/失败/无内容均不可复制） */
  public canCopyAnswer() {
    return (
      !this.isRequesting &&
      !this.isStreamFail &&
      !!this.chatLoop[0]?.showAnswer?.[0]?.text?.trim()
    );
  }

  /** 开始节点的输入参数列表通过校验后，点击【开始运行】，获取表单key-value，作为run接口的入参 */
  private getRunWorkflowParams() {
    return this.dynamicNodeParams?.getDynamicParams();
  }

  public stopChat() {
    this.sseInstance.close();
    this.isRequesting = false;
    this.isShowStopIcon = false;
    this.cdr.markForCheck();
  }

  /** 复制整体答案 */
  public copyAnswer(messages: any) {
    // 拼接全部 answer 块（task 型含循环/多节点输出时 showAnswer 可能多块），块间空行分隔
    const content = (messages[0]?.showAnswer || [])
      .map((sub: any) => sub.text || '')
      .join('\n\n')
      .trim();
    if (!content) {
      return;
    }
    this.clipboard.copy(content);
    MessageComponent.showSuccess(this.i18n.transform('copy_success'), 3000);
  }

  public changeCollapsedState(configInfo: any) {
    configInfo.collapsed = !configInfo.collapsed;
  }

  public hasPermission(): boolean {
    return this.currentPermissions && this.currentPermissions.OPERATOR;
  }

  override ngOnDestroy(): void {
    this.sidebarServ.setSidebarsVisibilityByState('destroy');
    // 子类新增的清理逻辑
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }

    // 调用父类的 ngOnDestroy 逻辑
    super.ngOnDestroy();
  }

  private getScenarioBotInfo() {
    this.isLoading = true;
    return this.appLibraryRepoServe.getScenarioBot(this.appId).then(
      (value) => {
        this.isLoading = false;
        const {
          inputs,
          name,
          icon,
          model_name,
          tags,
          workflows,
          tools,
          creator,
          description,
          desc,
          knowledge_repos,
          published_on,
          publish_time,
          free_trial_quota
        } = value;
        this.startNodeParams = inputs.map((param: any) => {
          if (!param?.value?.default) {
            param.value = {
              default: '',
              type: 'generated',
              hint: '',
            };
          }

          if (param.type === 'array' && param.schema) {
            param.type = `${param.type}<${param.schema.type}>`;
          }

          return { ...param };
        });
        this.scenarioExampleInfo = {
          title: name,
          icon,
          model_name,
          tags: tags || [],
          workflows: workflows || [],
          tools: tools || [],
          creator,
          description: description || desc,
          knowledge_repos: knowledge_repos || [],
          published_on,
          publish_time,
          free_trial_quota,
        };
        this.usedUp = getUsedUp(free_trial_quota);

        this.cdr.markForCheck();
      },
      (error: any) => {
        this.isLoading = false;
        if (error?.data?.error_code) {
          MessageComponent.showError(error.data.error_msg, 3000);
        }
        this.cdr.markForCheck();
      },
    );
  }

  private debugWorkflow(inputs: any, curIndex: number) {
    this.isRequesting = true;
    this.isShowStopIcon = true;
    this.isStreamFail = false;
    this.nodeIdBlock = {};
    this.previousNodeId = '';
    this.hasSetPreviousNodeId = false;

    if (this.appType === 'web-page') {
      this.sseInstance = this.agentRepoServe.webPageChatSSE(
        {
          inputs,
        },
        'workflows',
        this.appId,
        this.uuid,
        'PUBLISHED',
        this.lang,
        this.handleSSEEvents(curIndex),
      );
    } else {
      this.sseInstance = this.conversationServe.debugWorkflowSSE(
        {
          inputs,
        },
        this.appId,
        `${this.appId}_bbx`,
        this.isShare? 'DEBUG':'PUBLISHED',
        this.lang,
        this.handleSSEEvents(curIndex),
        this.isShare? this.versionId : '',
        true
      );
    }
  }

  private showErrorState(errorAlertText: string) {
    this.alertText = errorAlertText;
    this.open = true; // 使用了dismissOnTimeout后，需要在更新alert内容时，更新open值
    this.isShowStopIcon = false;
  }

  getShareDetail() {
    this.isLoading = true;
    this.shareService.getShareDetail(this.appId,
      { release_version: this.visionSelected, resource_type: 'workflow' }).then((res) => {
      this.shareInfo = res || {};
      this.visionsOptions = res.version_info_list || [];
      this.scenarioExampleInfo.icon = res.icon;
      this.workflow_id = res.resource_id;
      this.scenarioExampleInfo.title = res.resource_name;
      this.versionId = this.visionSelected;
       // 只有共享者能编辑分享内容
       this.canEditShare = res.resource_workspace_id === this.http.getWorkspaceId();
      this.startNodeParams = (res.workflow_inputs || [])
      .map((param: IWorkflowField) => {
        if (!param?.value?.default) {
          param.value = {
            default: '',
            type: 'generated',
            hint: '',
            content: '',
          };
        }
        const schema = param.schema as IWorkflowField;

        if (param.type === 'array' && schema) {
          param.type =
            `${param.type}<${schema.type}>` as IWorkflowFieldType;
        }

        return { ...param };
      })
      .filter(
        (item: any) =>
          !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
      );
    }).finally(()=>{
      this.isLoading = false;
    });
  }

  visionSelectedChange(id: string) {
    this.visionSelected = id;
    // 重新请求详情
    this.getShareDetail();
  }

}
