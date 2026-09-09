import { TextFieldModule } from '@angular/cdk/text-field';
import { Clipboard } from '@angular/cdk/clipboard';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MaskComponent, MessageComponent } from '@shared/services/cfdata.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { I18nNamespace } from '@i18n';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import type { IPluginConfig } from '@routes/agent-center/app-flow/app-flow.types';
import { EViewType } from '@routes/agent-center/app-flow/app-flow.types';
import flowCommonLogic from '@routes/agent-center/app-flow/common-logic-workflow';
import { WORKFLOW_SVGS } from '@routes/agent-center/app-flow/flow.const';
import type { IStartNode } from '@routes/agent-center/app-flow/node.type';
import { isSystemTypeWithNames, getUsedUp } from '@routes/agent-center/utils';
import CommonLogic from '@routes/app-center/common-logic-app-center';
import { AppExceedModalComponent } from '@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { CommonService } from '@services/common.service';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import { PermissionService } from '@services/permission.service';
import { AppConversationRepoService } from '@services/repositories/app-conversation-repo.service';
import { WorkflowChatBaseComponent } from '@shared/base/workflow-chat-base.service';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AssetClearIconComponent } from '@shared/components/assets/asset-clear-icon/asset-clear-icon.component';
import { AssetConfigIconComponent } from '@shared/components/assets/asset-config-icon/asset-config-icon.component';
import { AssetDisabledClearIconComponent } from '@shared/components/assets/asset-disabled-chat-icon/asset-disabled-chat-icon.component';
import { AssetUserIconComponent } from '@shared/components/assets/asset-user-icon/asset-user-icon.component';
import { CustomPopconfirmComponent } from '@shared/components/custom-popconfirm/custom-popconfirm.component';
import { DynamicNodeParamsComponentChat } from '@shared/components/dynamic-node-params-chat/dynamic-node-params-chat.component';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { InputNodeParamsComponent } from '@shared/components/input-node-params/input-node-params.component';
import { MemoryManagementComponent } from '@shared/components/memory-management/memory-management.component';
import {
  ConversationState,
  IMemoryManagementData,
} from '@shared/components/memory-management/memory-management.interface';
import { MemoryUpdatedComponent } from '@shared/components/memory-updated/memory-updated.component';
import { SenderComponent } from "@shared/components/sender/sender.component";
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { isNaN, isNil } from 'lodash';
import { Subscription } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';
import {
  SHARE_TYPE,
  ShareTypeTag,
} from '../app-center-management/app-center-management.config';
import {
  SHARE_PAGE,
  SHARE_TOOL_TYPE,
} from '../components/edit-share-modal/edit-share-modal.config';
import { ShareService } from '../components/edit-share-modal/share.service';
import { PrologueQuestionsAreaComponent } from '../components/prologue-questions-area/prologue-questions-area.component';
import { RightOpPanelComponent } from '../components/right-op-panel/right-op-panel.component';
import { RightSharePanelComponent } from '../components/right-share-panel/right-share-panel.component';
import { ShareDetailBtnComponent } from '../components/share-detail-btn/share-detail-btn.component';
import { ERROR_CODE } from '@routes/agent-center/types/common.types';

@Component({
  selector: 'meta-chat-flow-page',
  standalone: true,
  templateUrl: './chat-flow-page.component.html',
  styleUrls: ['./chat-flow-page.component.scss'],
  imports: [
    MODULES,
    NzIconModule,
    NzSelectModule,
    NzTagModule,
    NzAlertModule,
    NzButtonModule,
    NzToolTipModule,
    NzCollapseModule,
    DynamicNodeParamsComponent,
    TextFieldModule,
    AppMarkdownAnswerComponent,
    CustomPopconfirmComponent,
    InputNodeParamsComponent,
    AssetUserIconComponent,
    AssetClearIconComponent,
    AssetDisabledClearIconComponent,
    PrologueQuestionsAreaComponent,
    RightOpPanelComponent,
    RightSharePanelComponent,
    ShareDetailBtnComponent,
    MemoryManagementComponent,
    MemoryUpdatedComponent,
    DynamicNodeParamsComponentChat,
    AppExceedModalComponent,
    AssetConfigIconComponent,
    SenderComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
      ],
    },
  ],
})
export class ChatFlowPageComponent
  extends WorkflowChatBaseComponent
  implements OnInit
{
  @ViewChild('dynamicNodeParams')
  override dynamicNodeParams!: DynamicNodeParamsComponent;

  @ViewChild('inputNodeParams')
  inputNodeParamsComp!: InputNodeParamsComponent;

  @ViewChild('pluginAreaRef') pluginAreaRef!: ElementRef;

  @ViewChild('pluginForm') override pluginForm: NgForm;

  @ViewChild('chatContainerRef') override chatContainerRef!: ElementRef;

  @ViewChild('chatFlowTextarea') override chatTextarea!: ElementRef;

  @ViewChild('appExceedModalChat') appExceedModalChat: AppExceedModalComponent;

  // 引用输入组件
  @ViewChild('metaSenderComponent') metaSenderRef: SenderComponent;

  public flowInfo = {
    title: '',
    prologue: '',
    icon: '',
    cardList: [],
    tags: [],
    model_name: '',
    workflows: [],
    tools: [],
    creator: '',
    description: '',
    knowledge_repos: [],
    publish_time: '',
    free_trial_quota: null,
  };
  public usedUp = false;

  public shareInfo: any = {};

  conversationId = uuidV4();

  // 用户输入的问题
  public questionInputed = '';

  public nodes: any;

  public validateAlertIcon = WORKFLOW_SVGS.ValidateAlert;

  public isShowStopIcon = false;

  // 底部的textarea框是否存在渐变框动效
  public isAnimating = false;

  public isF1 = this.ctxServ.isF1ReqList();

  // textarea框是否聚焦
  private isFocusState = false;

  // 试运行接口的入参version
  private version: number = 0;

  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;

  public start_time: number;

  public shortCode = '';

  public flowId = '';

  private routeType = '';

  public showBackIcon = true;

  public showPanel = true;

  public dynamicNodeParamsPass = false;

  public currentPermissions: any;
  private permissionSubscription: Subscription;
  public isShare = false;
  public canEditShare = false;
  public visionsOptions = [];
  public visionSelected = '';
  shareTag = '';
  toolType = SHARE_TOOL_TYPE.workflow;
  pageType = SHARE_PAGE.apply;
  public isLoadingCopyBtn: boolean = false;
  public isMultipleAgent = false;
  public is_agreement = true;
  public isKnowledge = false;

  conversationState: ConversationState = {
    isExtract: true,
    isRetrieve: true,
  };
  private isFromOverview: boolean = false;

  protected memoryLibId = '';

  constructor(
    protected override appFlowServe: AppFlowService,
    protected override appAgentServe: AppAgentRepoService,
    protected override configServ: AgentConfigService,
    protected override commonLogic: agentCommonLogic,
    protected override pluginRepoServe: AppPluginRepoService,
    protected override monacoLoader: MonacoEditorLoaderService,
    protected override i18n: I18NextEagerPipe,
    protected override cdr: ChangeDetectorRef,
    protected override agentDataServe: AgentDataService,
    private conversationServe: AppConversationRepoService,
    private appLibraryRepoServe: AppLibraryRepoService,
    private route: ActivatedRoute,
    private router: Router,
    private ctxServ: ContextService,
    private fb: FormBuilder,
    private sidebarServ: SetSidebarVisibilityService,
    private permissionService: PermissionService,
    private shareService: ShareService,
    private appAgentRepoServ: AppAgentRepoService,
    private commonService: CommonService,
    private readonly http: HttpService,
    private modalService: NzModalService,
    private clipboard: Clipboard,
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

    this.shortCode = this.route.snapshot.params.id;
    this.flowId = this.route.snapshot.queryParams.appId;
    this.versionId = this.route.snapshot.queryParams.versionId;
    this.isShare = this.route.snapshot.queryParams.isShare === 'true';
    this.isKnowledge = this.route.snapshot.routeConfig?.path?.includes('knowledge-bot');
    if (this.isShare) {
      this.versionId = this.route.snapshot.queryParams.releaseVersion;
      this.isMultipleAgent =
        this.route.snapshot.queryParams.isMultipleAgent === 'true';
      if (this.isMultipleAgent) {
        this.toolType = SHARE_TOOL_TYPE.multipleAgent;
      }
    }
    this.visionSelected = this.route.snapshot.queryParams.releaseVersion;
  }

  override async ngOnInit() {
    super.ngOnInit();
    this.route.queryParams.subscribe((params) => {
      if (params.from && params.from === 'overview') {
        this.isFromOverview = true;
      }
    });
    if (this.isShare) {
      this.getShareDetail();
    } else {
      this.getFlowInfo();
    }
    this.sidebarServ.setSidebarsVisibilityByState('init');
    this.permissionSubscription = this.permissionService.permissions$.subscribe(
      (permissions) => {
        this.currentPermissions = permissions;
      },
    );
  }

  override onParamsValid() {
    this.showPanel = false;
    this.dynamicNodeParamsPass = true;
    this.updateCurAndChatView();
  }

  // 在对话型工作流的网页版和百宝箱这2处场景下，无需调用test-status接口。因此重写shouldUpdatePublishBtn，始终返回false
  override shouldUpdatePublishBtn(): boolean {
    return false;
  }

  override onError(curIndex: number, error: any) {
    if (error.data) {
      try {
        const errInfo = JSON.parse(error.data);
        this.usedUp = errInfo?.error_code === ERROR_CODE.QUOTA_USED_UP;
      } catch {

      }
    }
  }

  async getFlowInfo() {
    const url = this.router.url;
    MaskComponent.show();
    let res;
    // 查询已发布的网页版应用详情
    if (url.includes('chat')) {
      this.showBackIcon = false;
      this.routeType = 'web-page';
      this.shortCode = this.route.snapshot.params.id;
      res = await this.appAgentServe.getWebPageInfo(
        this.shortCode,
        'short_code',
        'WEB_PAGE',
      );
      this.workflow_id = res.app_id;
      this.memoryLibId = res.memory_repo_id;
      this.updateInputParams(res.nodes);
    }

    // 查询百宝箱中，对话型应用详情
    if (url.includes('knowledge-bot')) {
      this.showBackIcon = true;
      this.routeType = 'knowledge-bot';
      try {
        res = await this.appLibraryRepoServe.getKnowledgeInfo(this.flowId);
      } catch {
        MaskComponent.hide();
        return
      }
      this.workflow_id = res.workflow_id;
      this.versionId = res.version_id;
      this.updateAppInputParams(res.inputs);
    }

    const {
      icon,
      name,
      prologue,
      suggest_queries,
      model_name,
      tags,
      workflows,
      tools,
      creator,
      description,
      desc,
      knowledge_repos,
      publish_time,
      share_tor,
      free_trial_quota,
    } = res;
    this.flowInfo = {
      icon,
      title: name,
      prologue: prologue || '',
      cardList: suggest_queries?.map((item: any) => ({
        isOverflow: false,
        question: item,
      })),
      model_name,
      tags,
      workflows,
      tools,
      creator,
      description: description || desc,
      knowledge_repos,
      publish_time,
      free_trial_quota,
    };
    this.usedUp = getUsedUp(free_trial_quota),
    this.shareTag = ShareTypeTag(SHARE_TYPE.CAN_USE);
    MaskComponent.hide();
  }

  async getShareDetail() {
    MaskComponent.show();
    this.shareService
      .getShareDetail(this.flowId, {
        release_version: this.visionSelected,
        resource_type: this.isMultipleAgent ? 'controller' : 'workflow',
      })
      .then((res) => {
        this.shareInfo = res || {};
        this.visionsOptions = res.version_info_list || [];
        this.flowInfo.icon = res.icon;
        this.workflow_id = res.resource_id;
        this.flowInfo.title = res.resource_name;
        this.versionId = this.visionSelected;
        this.routeType = 'web-page';
        if (res.workflow_inputs?.length) {
          this.updateInputParams([
            {
              id: 'node_start',
              type: 'Start',
              name: this.i18n.transform('chat_flow_page_1'),
              outputs: res.workflow_inputs,
            },
          ]);
        }
        if (res.controller_inputs) {
          this.updateAppInputParams(res.controller_inputs);
        }
        // 只有共享者能编辑分享内容
        this.canEditShare =
          res.resource_workspace_id === this.http.getWorkspaceId();
      })
      .finally(() => {
        MaskComponent.hide();
      });
  }

  togglePanel() {
    if(!this.dynamicNodeParamsPass){
      return
    }
    this.showPanel = !this.showPanel;
  }

  public getTrimmedQuestion(question: string) {
    return question.trim();
  }

  public hasPermission(): boolean {
    return this.currentPermissions && this.currentPermissions.OPERATOR;
  }

  /** 对话的相关函数 */
  public canClear() {
    return (
      this.chatLoop.length !== 0 &&
      this.chatLoop[0].showAnswer !== undefined &&
      !this.isShowStopIcon
    );
  }

  /** 点击底部的清空对话，开启新聊天 */
  public clearChat() {
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.chatView = EViewType.CHAT_EMPTY;
    this.questionInputed = ''; // 置空textarea中的问题
    this.chatLoop = []; // 置空页面主体的多轮对话
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.conversationId = uuidV4();
    this.appFlowServe.setAnswerInputForm(this.fb.group({}));
  }

  public stopChat() {
    this.sseInstance.close();
    this.isRequesting = false;
    this.isShowStopIcon = false;
    const lastIndex = this.chatLoop.length - 1;
    this.chatLoop[lastIndex].thinkLoading = false;
    const end_time = new Date().getTime();
    const currentAns = this.chatLoop[lastIndex].showAnswer[this.index];
    currentAns.text = `${currentAns.text || ''}${
      currentAns.text ? '<br>' : ''
    }${this.i18n.transform('stopped_generating')}`;
    currentAns.loading = false;
    this.chatLoop[lastIndex].latency = flowCommonLogic.calcElapsedTime(
      this.start_time,
      end_time,
    );
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  public handleInputStart() {
    if (this.isFocusState) {
      this.isAnimating = true;
      this.isFocusState = false;
      this.cdr.markForCheck();
      setTimeout(() => {
        this.isAnimating = false;
        this.cdr.markForCheck();
      }, 4000);
    }
  }

  public handleFocusStart() {
    this.isFocusState = true;
  }

  public canSend(): boolean {
    if(this.metaSenderRef?.content){
      this.questionInputed = this.metaSenderRef.content
    }
    const hasUnconfirmedAnswer = this.chatLoop.some((item: any) =>
      item.showAnswer.some(
        (answer: any) => answer.isConfirmed === 'not-confirmed',
      ),
    );
    if (hasUnconfirmedAnswer) {
      return false;
    }

    return !this.usedUp && !this.isRequesting && !!this.questionInputed.trim();
  }

  public quickSend(content: string) {
    this.questionInputed = content;
    this.sendQuestion();
  }

  public sendQuestion(e?:any) {
    if(e && e.content){
      this.questionInputed  = e.content
    }
    if (!this.canSend()) {
      return;
    }
    this.curView = EViewType.CHAT;
    this.chatView = EViewType.CHAT_NOT_EMPTY;

    this.chatLoop.push(
      CommonLogic.createFlowChatItem({
        query: this.questionInputed,
        dialogId: uuidV4(),
      }),
    );
    // 把开始节点输入参数列表key-value，组装成流式接口入参
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
    startInputsList.query = this.questionInputed;
    this.debugWorkflow(startInputsList, [], this.chatLoop.length - 1);
    this.questionInputed = '';
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  public changeCollapsedState(pluginForm: any) {
    const collapsed = pluginForm.collapsed;
    pluginForm.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  /** 点赞按钮 */
  public likeAnswer(answer: any) {
    this.appAgentServe
      .feedback(this.workflow_id, {
        event_type: 'like',
        app_type: 'workflow',
        channel: 'api',
      })
      .then(() => {
        // 检查当前想点赞的回答是否已经点踩，如果是，则取消点踩
        if (answer?.isDislike) {
          answer.isDislike = false;
        }
        // 将点赞按钮设置为实心状态
        answer.isLike = true;
      });
  }

  /** 点踩抽屉的确定按钮 */
  public submitDislike(answer: any) {
    if (answer.isLike) {
      answer.isLike = false;
    }

    answer.isDislike = true;
  }

  /** 当调用点踩接口完成时，关闭Tip弹窗 */
  public closeDislikeTip() {
    document.dispatchEvent(new Event('tiScroll'));
  }

  /** 点击输入节点的确定按钮 */
  public onConfirm(ans: any, item: any) {
    // 根据输入节点必填 非必填，动态进行校验
    let inputNodeParamsPass = true;

    let inputList;
    item.showAnswer?.forEach((item) => {
      if (item?.inputList && item.inputList.length > 0) {
        inputList = item.inputList;
      }
    });
    inputNodeParamsPass = this.inputNodeParamsComp
      ? this.inputNodeParamsComp.checkInput(inputList)
      : true;
    if (!inputNodeParamsPass) {
      return;
    }

    const allInputFormGroup = this.appFlowServe.getAnswerInputForm();
    this.appFlowServe.setAnswerInputForm(allInputFormGroup);

    ans.isConfirmed = 'confirmed';
    const inputData = this.inputNodeParamsComp?.getDynamicParams(item.dialogId);
    this.chatLoop.push(
      CommonLogic.createFlowChatItem({
        query: this.getFormattedData(inputData),
        dialogId: uuidV4(),
      }),
    );

    this.debugWorkflow(
      { query: this.getFormattedData(inputData) },
      [],
      this.chatLoop.length - 1,
    );
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  /** 点踩抽屉的取消按钮 */
  public cancelDislike() {
    document.dispatchEvent(new Event('tiScroll'));
  }

  public onFileUploadStatus(state: string, ans: any) {
    if (state === 'loading') {
      ans.isConfirmed = 'not-prepared';
    } else {
      ans.isConfirmed = 'not-confirmed';
    }
  }

  /** 更新开始节点的入参列表 */
  private updateInputParams(nodes) {
    // 存储已填的开始节点入参，确保在自动更新时不会丢失数据
    const startNode = nodes?.find(
      (node) => node.type === 'Start',
    ) as IStartNode;
    if (!startNode) {
      return;
    }

    this.startNodeParams = startNode.outputs
      .map((param: any) => {
        if (param.type === 'array' && param.schema) {
          param.type = `${param.type}<${param.schema.type}>`;
        }

        return { ...param };
      })
      .filter(
        (item: any) =>
          !isSystemTypeWithNames(item, [
            'conversation_history',
            'sys',
            'query',
          ]),
      );
    this.startNodeParams = this.addControlValueField(this.startNodeParams);

    // 若开始节点仅有一个系统入参query并且没有【插件鉴权参数】，直接展示对话页面，否则先展示配置页面
    if (!this.startNodeParams.length) {
      this.updateCurAndChatView();
    }
  }

  /** 更新百宝箱开始节点的入参列表 */
  private updateAppInputParams(inputs) {
    this.startNodeParams = inputs
      .map((param: any) => {
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
      })
      .filter((item: any) => !['query', 'conversation_history', 'sys'].includes(item.name));

    this.startNodeParams = this.addControlValueField(this.startNodeParams);
    // 若开始节点仅有一个系统入参query并且没有【插件鉴权参数】，直接展示对话页面，否则先展示配置页面
    if (!this.startNodeParams.length) {
      this.updateCurAndChatView();
    }
  }

  private debugWorkflow(
    inputs: any,
    pluginConfigs: IPluginConfig[],
    curIndex: number,
  ) {
    this.isRequesting = true;
    this.isShowStopIcon = true;
    this.index = 0;
    this.nodeIdBlock = {};
    this.previousNodeId = '';
    this.hasSetPreviousNodeId = false;
    this.inputList = [];
    this.isUserScrolling = false;
    this.start_time = new Date().getTime();
    const longTermMemory = this.configServ.isSupportUserPersona()
      ? {
        long_term_memory: {
          // 记忆提取配置：未关联记忆库时关闭 retrieve/extract，避免后端空ID报错
          enable_retrieve: this.memoryLibId ? this.conversationState.isRetrieve : false,
          enable_extract: this.memoryLibId ? this.conversationState.isExtract : false,
          memory_repo_id: this.memoryLibId,
        },
      }
      : {};
    let messages = {
      inputs,
      globals: {},
      plugin_configs: pluginConfigs,
      version: this.version,
      ...longTermMemory,
    };

    if (this.routeType === 'knowledge-bot' || this.isShare) {
      if (this.isMultipleAgent) {
        this.sseInstance = this.appAgentServe.debugMultiAgentSSE(
          {
            inputs,
            ...longTermMemory,
          },
          this.workflow_id,
          this.conversationId,
          this.lang,
          this.handleSSEEvents(curIndex, () => {
            this.isShowStopIcon = false;
          }),
          this.versionId,
          true,
        );
      } else {
        this.sseInstance = this.conversationServe.debugWorkflowSSE(
          messages,
          this.workflow_id,
          this.conversationId,
          this.isShare ? 'DEBUG' : 'PUBLISHED',
          this.lang,
          this.handleSSEEvents(curIndex, () => {
            this.isShowStopIcon = false;
          }),
          this.versionId,
          true,
        );
      }
    } else {
      this.sseInstance = this.appAgentServe.webPageChatSSE(
        messages,
        'workflows',
        this.shortCode,
        this.conversationId,
        'PUBLISHED',
        this.lang,
        this.handleSSEEvents(curIndex, () => {
          this.isShowStopIcon = false;
        }),
      );
    }
  }

  /** 开始节点的输入参数列表通过校验后，点击【开始运行】，获取表单key-value，作为run接口的入参 */
  private getRunWorkflowParams() {
    return this.dynamicNodeParams?.getDynamicParams();
  }

  public onClickBack() {
    let state: any = {
      formTab: this.isShare ? 'share' : '',
    };
    if (this.isFromOverview) {
      this.router.navigate(['/home/overview']);
      return;
    }
    if (this.canEditShare) {
      state.myShare = true;
    }
    this.router.navigate([`home/app-library`], {
      state,
    });
  }

  override ngOnDestroy() {
    this.sidebarServ.setSidebarsVisibilityByState('destroy');
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  /** 一键复制本轮回答，保留原始 markdown 结构（全部 answer 块拼接） */
  public handleCopyAnswer(item: any) {
    const content = (item.showAnswer || [])
      .map((sub: any) => sub.text || '')
      .join('\n\n')
      .trim();
    if (!content) {
      return;
    }
    this.clipboard.copy(content);
    MessageComponent.showSuccess(this.i18n.transform('copy_success'), 3000);
  }

  // 复制到工作台
  async copyToWorkbench(): Promise<void> {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    if (this.isLoadingCopyBtn) {
      return;
    }
    this.isLoadingCopyBtn = true;
    this.appLibraryRepoServe
      .copyToWorkbench(this.flowId, 'workflow')
      .then((res: any) => {
        if (res.resource_id) {
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
      })
      .finally(() => {
        this.isLoadingCopyBtn = false;
      });
  }

  async isResourceExceed() {
    const res = await this.appAgentRepoServ.getResourceQuantity('agent');
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount };
        this.appExceedModalChat.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    const currentScrollTop = target.scrollTop;

    // 判断是否向上滚动
    if (currentScrollTop < this.lastScrollTop) {
      this.isUserScrolling = true;
    } else if (
      currentScrollTop + target.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false; // 滚动条手动滚到底部，再次自动滚动
    }
    this.lastScrollTop = currentScrollTop - 3;
  }

  visionSelectedChange(id: string) {
    this.visionSelected = id;
    // 重新请求详情
    this.getShareDetail();
  }

  memoryConfirm(memoryData: IMemoryManagementData) {
    this.conversationState.isRetrieve = memoryData?.enable_retrieve ?? true;
    this.conversationState.isExtract = memoryData?.enable_extract ?? true;
  }


  getAITip() {
    if (!this.isShare && this.isKnowledge) {
      return this.i18n.transform('ai_generated_disclaimer_five')
    } else {
      return this.i18n.transform('ai_generated_disclaimer_three')
    }
  }
}
