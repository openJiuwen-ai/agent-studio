import { CommonModule } from "@angular/common";
import { ChangeDetectorRef, Component, HostListener, OnDestroy, OnInit, ViewChild, ViewContainerRef } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { NzMessageService } from "ng-zorro-antd/message";
import { NzDrawerRef, NzDrawerService } from "ng-zorro-antd/drawer";
import { NzModalService } from "ng-zorro-antd/modal";
import { I18nNamespace } from "@i18n";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { AgentBotPageService } from "@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.service";
import { AiAnswerListService } from "@routes/agent-center/app-agent/components/chat-item/ai-answer.component.service";
import { ModelConfigTipService } from "@routes/agent-center/app-agent/components/model-config-tip/model-config-tip.service";
import { PreviewDebugPlanComponent } from "@routes/agent-center/app-agent/components/preview-debug-plan/preview-debug-plan.component";
import { TriggerHalfmodalComponent } from "@routes/agent-center/app-agent/components/trigger-modal/trigger-modal.component";
import { AgentDeepResearch } from "@routes/agent-center/app-deep-research/developing/agent-deep-research";
import { AppFlowService } from "@routes/agent-center/app-flow/app-flow.service";
import { IContentReview } from "@routes/agent-center/app-flow/node.type";
import { MemoryVariableInputParamType } from "@routes/agent-center/interfaces/agent/app-agent.interface";
import { IMemoryLibBaseInfo } from "@routes/memory-lib/memory-lib-interfaces";
import { AgentCenterHomeService, TabIndex } from "@services/agent-center/agent-center-home.service";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { MCPService } from "@services/agent-center/mcp.service";
import { ContextService } from "@services/context.service";
import { ModelManagementService } from "@services/repositories/model-management-new";
import { WindowResizeService } from "@shared/base/window-resize.service";
import { PublishVersionModalComponent } from "@shared/components/publish-version-modal/publish-version-modal.component";
import { ReleaseHistoryHalfmodalComponent } from "@shared/components/release-history-halfmodal/release-history-halfmodal.component";
import { ITabHeader, TabsHeaderComponent } from "@shared/components/tabs-header/tabs-header.component";
import { MODULES } from "@shared/modules";
import { SetSidebarVisibilityService } from "@shared/services/set-sidebar-visibility.service";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { Subject, takeUntil } from "rxjs";
import { environment } from "src/environment/environment";
import { PublishChannelPageComponent } from "src/shared/components/publish-channel-page/publish-channel-page.component";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { PipesModule } from "../../../../pipes/pipes.module";
import { AgentVarInfo, InputVarInfo, IPromptTagItem, ISingleAgentQueryResp, IUpdateSingleAgentConfig } from "../../types/my-workspace.types";
import { agentCommonLogic } from "../common-logic-agent";
import { AgentLogModalComponent } from "../components/agent-log-modal/agent-log-modal.component";
import { ConfigToolsComponent } from "../components/config-tools/config-tools.component";
import { IKbParam } from "../components/config-tools/kb-conf.component";
import { IMemoParam } from "../components/create-memo/types";
import { InfoAndPromptBuilderComponent } from "../components/info-and-prompt-builder/info-and-prompt-builder.component";
import { PreviewDebugComponent } from "../components/preview-debug/preview-debug.component";
import { AGENT_MODE_CODE, DISPATCH_MODE, URL_FROM_MULTI_AGENT } from "./agent-bot-page.constant";
import { ToolListComponent } from "@routes/agent-center/app-agent/components/tool-list/tool-list.component";

enum mapKeys {
  from = "from",
}

@Component({
  selector: "agent-bot-page",
  templateUrl: "./agent-bot-page.component.html",
  styleUrls: ["./agent-bot-page.component.less"],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    InfoAndPromptBuilderComponent,
    ConfigToolsComponent,
    PreviewDebugComponent,
    TabsHeaderComponent,
    AgentDeepResearch,
    PipesModule,
    PublishChannelPageComponent,
    PreviewDebugPlanComponent,
    ToolListComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.KNOWLEDGE, I18nNamespace.COMMON, I18nNamespace.REVIEW, I18nNamespace.MEMORY_LIB]
    },
    agentCommonLogic,
    NzModalService
  ]
})
export class AgentBotPageComponent implements OnInit, OnDestroy {
  @ViewChild(ConfigToolsComponent) childConfigToolCom: ConfigToolsComponent;
  @ViewChild("publishChannelPage")
  publishChannelPage: PublishChannelPageComponent;
  @ViewChild("triggerSettingModal") triggerSettingModal: any;
  public headerTabs: ITabHeader[] = [
    {
      id: "agent",
      title: this.i18n.transform("skill_arrangement"),
      active: true
    },
    {
      id: "analyze",
      title: this.i18n.transform("data_analysis"),
      active: false,
      disabled: true,
      tips: this.i18n.transform("release_first")
    }
  ];
  // 定义常量映射表
  public DISPATCH_MODE_MAP = {
    ReAct: this.i18n.transform("model_priority"),
    RAG: this.i18n.transform("knowledge_priority"),
    ToolUse: this.i18n.transform("tool_priority")
  };
  public agentInfo: ISingleAgentQueryResp = {
    icon: "",
    name: "",
    description: "",
    status: "",
    promptTags: [] as IPromptTagItem[],
    agentType: "",
    agentSubType: ""
  };
  public allAgentInfo: any = {};
  public promptInputed = "";
  public memos: IMemoParam[] = [];
  public knowledge_retrieve_policy: IKbParam = {
    top_k: 3,
    recall_threshold: 0.5,
    search_mode: "doc",
    faq_threshold: 0.9,
    need_extras_faq_search: false,
    extra_params: []
  };
  public agent_variables: Array<AgentVarInfo> = [];
  public input_variables: Array<InputVarInfo> = [];

  public memory_config: IMemoryLibBaseInfo = null;
  public plugins = [];
  public knowledges = [];
  public workflows = [];
  public skills = [];
  public mcp_servers = [];
  public sceneList = [];
  public workflowSwitchEnabled = false;

  public trigger_list = [];
  public content_review: IContentReview;
  public safety_barrier: boolean;
  public openTextAndQuestions: any = {
    prologue: "",
    suggest_queries: [],
    name: "", // 智能生成开场白的接口，需要传递应用name和desc
    description: ""
  };

  public previewDebugData = {
    name: "",
    icon: "",
    openText: "",
    openQuestions: [],
    deploymentId: ""
  };
  public isLoading = false;
  public isF1 = this.ctxServ.isF1ReqList();
  public agentId = "";
  public autoSaveTime = "";
  public availableModels: any = [];
  public modelSelected = ""; // 当前选择的模型
  public modelSelectedId = "";
  public modelConfig: any = {};
  public dispatchSelectedName = "";
  public dispatchSelectedType = ""; // ReAct:模型优先、RAG：知识库优先、ToolUse：工具优先

  public additional_questions_config: any = {};
  public collapsed = false;
  public collapsedDispatch = false;

  // 模型配置弹窗tip是否显示
  public showModelConfigTip = false;
  public showDispatchConfig = false;

  // Agent调试抽屉是否显示
  public isShowLogModal = false;
  public drawerLog: NzDrawerRef;
  public drawerHistory: NzDrawerRef;
  public drawerTrigger: NzDrawerRef;
  public historyModalTop = "";
  public showHistoryModal = false;
  public showTriggerModal = false;
  public agentStatus = "";
  public changeUrl = cdnAssetUrl;
  public curActiveTabId = "agent";

  // 发布管理按钮是否置灰。未首次发布前，查不到latest_version_id
  public isVersionListEmpty = false;
  // 应用百宝箱的发布渠道。只有F1环境 或 op账号能看到，非F1环境的最终租户无法看到
  public isOpAccount = false;
  public historyVersionList = [];
  public isPOC = environment.envType === "poc";
  private modelType: string;

  private destroy$ = new Subject<void>();
  private originTitle = "";
  public isFlowReadonly = false;
  public versionName = "";
  public isExpandDialog = false;

  public dispatchModes = [
    {
      type: "ReAct",
      img: cdnAssetUrl("assets/agent-center/images/model-priority.png"),
      title: this.DISPATCH_MODE_MAP.ReAct,
      description: "dispatch_react"
    },
    {
      type: "RAG",
      img: cdnAssetUrl("assets/agent-center/images/knowledge-priority.png"),
      isHide: false,
      title: this.DISPATCH_MODE_MAP.RAG,
      description: "dispatch_rag"
    }
  ];

  // 是否来自于开发者空间
  public isFromDevelopSpace: boolean = false;
  private isFromOverview: boolean = false;
  private isFromFeatured: boolean = false;
  public createNewMcpData: any = {};
  public isShowSuccessAlert: boolean = false;
  public isShowFailAlert: boolean = false;

  subscribeBtnStatus = true;
  isShowDeepResearch: boolean = false;
  isDeepResearchLoading: boolean = false;

  agentModeList = [
    {
      name: this.i18n.transform("agent_mode_gen"),
      description: this.i18n.transform("agent_mode_gen_description"),
      icon: "assets/agent/general_mode.svg",
      value: AGENT_MODE_CODE.GENERAL_MODE,
      showFn: () => true
    },
    {
      name: this.i18n.transform("agent_planning_mode"),
      description: this.i18n.transform("agent_planning_mode_desc"),
      icon: "assets/agent/planning_mode.svg",
      value: AGENT_MODE_CODE.PLANNING_MODE,
      showFn: () => true
    }
  ];
  agentMode = {
    [AGENT_MODE_CODE.GENERAL_MODE]: this.agentModeList[0],
    [AGENT_MODE_CODE.PLANNING_MODE]: this.agentModeList[1],
    [AGENT_MODE_CODE.DEEP_MODE]: {
      name: this.i18n.transform("agent_mode_deep"),
      description: this.i18n.transform("agent_mode_deep_description"),
      icon: "assets/agent/deepResearch.svg",
      value: AGENT_MODE_CODE.DEEP_MODE,
      showFn: () => false
    }
  };
  curAgentModeCode: AGENT_MODE_CODE;
  isShowAgentModeSelector: boolean = false;
  isClickChangeMode: boolean = false; // 是否修改智能体的类型
  isDisabledReleaseBtn: boolean = false;
  public publishParams: any = {};
  public configHeaderTabs: ITabHeader[] = [
    {
      id: "appConfig",
      title: this.i18n.transform("single_agent_config"),
      active: true
    },
    {
      id: "releaseManage",
      title: this.i18n.transform("channel_management"),
      active: false,
      disabled: this.isVersionListEmpty,
      tips: ""
    }
  ];
  public curActiveConfigTabId = this.configHeaderTabs[0].id;

  //获取是否是 ‘有尚未发布的修改’ 的状态
  get releaseStatusBar() {
    if (this.allAgentInfo?.status === "published") {
      return this.allAgentInfo?.publish_time < this.allAgentInfo?.update_time;
    }
    return false;
  }

  get statusBarInfo() {
    let backUpInfo;
    backUpInfo = this.appFlowServ.AgentStatusMap.get(this.allAgentInfo?.status);
    return {
      icon: backUpInfo?.icon ? backUpInfo?.icon : cdnAssetUrl("assets/agent-center/flow/loading.gif"),
      text: backUpInfo?.text
    };
  }

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private commonLogic: agentCommonLogic,
    private service: AppAgentRepoService,
    private agentDataServe: AgentDataService,
    private nzModalService: NzModalService,
    private ppServ: AgentCenterHomeService,
    private ctxServ: ContextService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    private modelManagementService: ModelManagementService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private aiAnswerListService: AiAnswerListService,
    public modelConfigTipService: ModelConfigTipService,
    private nzDrawerService: NzDrawerService,
    private mcpService: MCPService,
    private windowResizeService: WindowResizeService,
    private appFlowRepoServ: AppFlowRepoService,
    private appFlowServ: AppFlowService,
    private readonly agentBotPageService: AgentBotPageService,
    private viewContainerRef: ViewContainerRef,
    private messageServ: NzMessageService
  ) {
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();
    this.originTitle = document.title;
    this.isOpAccount = this.ctxServ.isOpAccount;

    this.route.queryParams.subscribe(async params => {
      this.agentId = params.agentId;
      if (params.from && params.from === "develop-space") {
        this.isFromDevelopSpace = true;
      }
      if (params.from && (params.from === "overview" || params.from === "experience-creation")) {
        this.isFromOverview = true;
      }
      if (params.from && params.from === "featured") {
        this.isFromFeatured = true;
      }
      this.isDefaultDeepResearch = !!params.default_deepresearch;
      let { versionId, versionName } = params;
      if (versionId) {
        if (!versionName) {
          const res = await this.service.getAgentVersionList(this.agentId);
          const { version_list } = res || {};
          const version = version_list.find(v => {
            return v.version_id === versionId;
          });
          if (version) {
            versionName = version.version_name;
          }
        }
        this.agentDataServe.setRollbackId({
          version_id: versionId,
          version_name: versionName ?? "",
          isFlowReadonly: true
        });
      }
    });

    if (this.configServ.getConfigs().agent_tool_priority_enable) {
      this.dispatchModes.push({
        type: "ToolUse",
        img: cdnAssetUrl("assets/agent-center/images/tooluse-priority.png"),
        title: this.DISPATCH_MODE_MAP.ToolUse,
        description: "dispatch_tooluse"
      });
    }
    this.agentDataServe
      .getTriggerUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((triggerAdded: any) => {
        const { trigger_id, name, type, cron, prompt, hook_url } = triggerAdded;
        if (type === "TIMER") {
          const is_has = this.triggerAdded.list.some(item => item.trigger_id === trigger_id);
          if (is_has) {
            for (let i = 0; i < this.triggerAdded.list.length; i++) {
              const cur = this.triggerAdded.list[i];
              if (cur.trigger_id === trigger_id) {
                this.triggerAdded.list[i] = triggerAdded;
                break;
              }
            }
          } else {
            this.triggerAdded.list = [
              ...this.triggerAdded.list,
              {
                trigger_id,
                name,
                type,
                cron,
                prompt
              }
            ];
          }
        }
        if (type === "EVENT") {
          this.triggerAdded.list = [
            ...this.triggerAdded.list,
            {
              trigger_id,
              name,
              type,
              prompt,
              hook_url
            }
          ];
        }
      });
    this.agentDataServe
      .autoSaveTimeUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((autoSaveTime: any) => {
        // get接口成功返回时，增加调用了setAutoSaveTime。增加当加载态未完成时，不会给autoSaveTime赋值
        if (!this.isLoading) {
          this.autoSaveTime = autoSaveTime;
          this.allAgentInfo.update_time = autoSaveTime;
          this.agentBotPageService.agentDetail.set(this.allAgentInfo);
          this.cdr.markForCheck();
        }
      });

    this.agentDataServe
      .promptAndModelConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((promptAndModelConfig: any) => {
        const { modelConfig } = promptAndModelConfig;
        if (modelConfig?.model_name) {
          this.modelSelectedId = modelConfig.model_deployment_id;
          this.modelSelected = modelConfig.service_name;
        }
      });

    // 订阅agent insight抽屉是否打开
    this.agentDataServe
      .insightBtnUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isClicked: any) => {
        if (isClicked) {
          this.isShowLogModal = true;
          this.drawerLog = this.nzDrawerService.create({
            nzTitle: this.i18n.transform("debugging"),
            nzContent: AgentLogModalComponent,
            nzPlacement: "right",
            nzWidth: 700,
            nzClosable: true,
            nzMaskClosable: false,
            nzMask: true,
            nzContentParams: {
              showLogModal: this.isShowLogModal,
              conversationId: this.agentDataServe.getCurrentConversationId()
            }
          });
          this.drawerLog.afterClose.subscribe(() => {
            this.isShowLogModal = false;
            this.agentDataServe.setInsightBtnClicked(false);
          });
        } else {
          this.isShowLogModal = false;
        }
      });

    // 订阅还原版本的agent详情
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(version => {
        this.isFlowReadonly = version.isFlowReadonly;
        this.versionName = version.version_name;
        if (version.version_id) {
          this.rollbackVersion(version);
        }

        if (version?.draft) {
          this.loadAgent(this.agentId);
        }
      });

    // 订阅get和put接口返回体中的status字段值
    this.agentDataServe
      .agentStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        this.agentStatus = status;
      });

    // 在跳转到"发布管理"页面之前展示loading效果
    this.agentDataServe
      .publishStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        if (status === "loading") {
          this.isLoading = true;
        }
        if (status === "succeeded") {
          this.isLoading = false;
        }
      });

    // 删光某个应用的发布历史后，置灰查询发布通道入口
    this.agentDataServe
      .versionListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list: any) => {
        this.isVersionListEmpty = list.length === 0;
        this.setReleaseManageTab();
        this.historyVersionList = list;
      });
  }

  public HWCloudTopHeight: number = 0;
  public isDefaultDeepResearch: boolean = false;

  get runtime_api_endpoint_prefix() {
    return this.configServ.getConfigs().runtime_api_endpoint_prefix;
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  ngOnInit() {
    this.modelSelected = "";
    this.modelSelectedId = "";
    this.setSidebarVisibilityService.setSidebarsVisibilityByState("init");
    this.getAgentVersions();
    const queryParams = this.route.snapshot?.queryParams || {};
    if (!(queryParams.versionId && queryParams.from === URL_FROM_MULTI_AGENT)) {
      this.loadAgent(this.agentId);
    }
  }

  ngAfterViewInit(): void {
    this.initTab();
  }

  ngOnDestroy(): void {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState("destroy");
    this.destroy$.next();
    this.destroy$.complete();
    this.agentDataServe.setInsightBtnClicked(false);
    this.agentDataServe.setPublishStatus("");
    this.agentDataServe.setRollbackId({
      version_id: "",
      isFlowReadonly: false
    });
    this.agentDataServe.setHasQAFlag(false);
    this.agentDataServe.setLatestPluginList([]);
    this.agentDataServe.setPluginAndFlowList({});
    document.title = this.originTitle;
    this.agentDataServe.setAutoSaveTime("");
    this.agentDataServe.setAgentCachedVarMap({});
    this.agentDataServe.setAgentVars([]);
    this.aiAnswerListService.aiAnswerList = [];
    this.modelConfigTipService.detail = null;
  }

  public initTab() {
    this.route.queryParams.subscribe(async params => {
      if (params.tabId && params.tabId === this.configHeaderTabs[1].id) {
        this.configHeaderTabs[0].active = false;
        this.configHeaderTabs[1].active = true;
        this.configHeaderTabs[1].disabled = false;
        this.configTabActiveChange(this.configHeaderTabs[1].id);
      }
    });
  }

  public onPageBack() {
    if (this.isFromFeatured) {
      this.router.navigate(["/home/app-library"]);
      return;
    }
    if (this.isFromOverview) {
      this.router.navigate(["/home/overview"]);
      return;
    }
    if (this.isFromDevelopSpace) {
      this.router.navigate(["/home/develop-space"]);
      return;
    }
    this.ppServ.goHome("single", TabIndex.MULTI_AGENT);
    this.agentDataServe.setTriggerBtnClicked(false);
  }

  /** 打开模型配置的非遮罩层弹窗 */
  public handleModelConfigTip($event: Event) {
    $event.stopPropagation();
    this.showDispatchConfig = false;
    this.collapsedDispatch = false;
    this.collapsed = !this.showModelConfigTip;
    this.showModelConfigTip = !this.showModelConfigTip;
  }

  public triggerAdded = {
    title: this.i18n.transform("trigger"),
    collapsed: false,
    list: [],
    imageClass: "common-img",
    isLoading: false
  };

  public triggerEmptyText = this.i18n.transform("triggerEmptyText");

  /** 点击触发器的添加按钮 */
  public openTriggerHalfmodal(his): void {
    if (this.isFlowReadonly) {
      return;
    }
    const modal = this.nzModalService.create<TriggerHalfmodalComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzContent: TriggerHalfmodalComponent,
      nzWidth: "736px",
      nzViewContainerRef: this.viewContainerRef,
      nzData: {
        historyTriggers: this.triggerAdded.list,
        edit_data: his ? [his] : []
      },
      nzOnOk: () => {
        modal.destroy();
      }
    });
  }

  public click(): void {
    this.showTriggerModal = true;
  }

  public openTriggerDrawer(): void {
    this.triggerSettingModal.open();
  }

  public deleteTrigger(info: any) {
    this.service.deleteOneTrigger(this.agentId, info.trigger_id).then(() => {
      const index = this.triggerAdded.list.findIndex((item: any) => item.trigger_id === info.trigger_id);
      if (index > -1) {
        this.triggerAdded.list.splice(index, 1);
      }
      this.messageServ.success(this.i18n.transform("successfully_deleted_trigger"), { nzDuration: 3000 });
    });
  }

  public changeCollapsedState(configInfo: any) {
    try {
      const collapsed = configInfo;
      configInfo = !collapsed;
      this.cdr.markForCheck();
    } catch {
    }
  }

  public publishAgent() {
    const drawerRef = this.nzModalService.create({
      nzTitle: this.i18n.transform(this.historyVersionList.length > 0 ? "update_version" : "submit_version"),
      nzContent: PublishVersionModalComponent,
      nzWidth: 600,
      nzMaskClosable: false,
      nzFooter: null,
    });

    Object.assign(drawerRef.componentInstance, {
      app_id: this.agentId,
      app_type: "agent",
      isFromDevelopSpace: this.isFromDevelopSpace,
    });

    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      instance.publishSuccess.subscribe(() => {
        this.getAgentVersions();
        this.loadAgent(this.agentId);
      });
      instance.clickShare.subscribe(() => {
        if (this.curActiveConfigTabId === this.configHeaderTabs[1].id) {
          this.publishChannelPage.initFn();
        } else {
          if (this.isVersionListEmpty) {
            this.getAgentVersions(() => {
              this.configHeaderTabs[0].active = false;
              this.configHeaderTabs[1].active = true;
              this.configTabActiveChange(this.configHeaderTabs[1].id);
            });
          } else {
            this.configHeaderTabs[0].active = false;
            this.configHeaderTabs[1].active = true;
            this.configTabActiveChange(this.configHeaderTabs[1].id);
          }
        }
      });
    });
  }

  public openReleaseHistoryModal() {
    this.showHistoryModal = true;
    this.drawerHistory = this.nzDrawerService.create({
      nzTitle: this.i18n.transform("release_history"),
      nzContent: ReleaseHistoryHalfmodalComponent,
      nzPlacement: "right",
      nzWidth: 700,
      nzClosable: true,
      nzMaskClosable: false,
      nzMask: true,
      nzContentParams: {
        type: "agent",
        isShowHistory: this.showHistoryModal
      }
    });
    this.drawerHistory.afterClose.subscribe(() => {
      this.showHistoryModal = false;
    });
  }

  public onUpdateName(name: string) {
    this.agentInfo.name = name;
  }

  public onUpdateLogo(logo: string) {
    this.agentInfo.icon = logo;
    this.previewDebugData = {
      ...this.previewDebugData,
      icon: logo
    };
  }

  public tabActiveChange(id: string) {
    this.curActiveTabId = id;
  }

  public goToChannelPage() {
    const queryParams = {
      agentId: this.agentId
    };
    if (this.isFromDevelopSpace) {
      queryParams[mapKeys.from] = "develop-space";
    }
    this.publishParams = queryParams;
  }

  get isPublishBtnDisabled(): boolean {
    return this.modelSelected === this.i18n.transform("model_nodata") || !this.modelSelected;
  }

  get publishBtnTip(): string {
    if (this.modelSelected === this.i18n.transform("model_nodata") || !this.modelSelected) {
      return this.i18n.transform("model_invailable");
    }
    return "";
  }

  /** 获取已创建的Agent信息 */
  private async loadAgent(agentId: string) {
    this.isLoading = true;
    try {
      const res: any = await this.service.fetchAgentDetail(agentId);
      this.agentBotPageService.agentDetail.set(res);
      this.allAgentInfo = res;
      const params = {
        showlatest: true,
        version: "latest"
      };
      const resApp: any = await this.appFlowRepoServ.getAppRefs(agentId, params);
      const relations: any = resApp.relations || [];
      (res.workflows || []).forEach((item: any) => {
        const findID: any = relations.find(finditem => finditem.resource_id === item.workflow_id && finditem.resource_type === "workflow");
        if (!findID) {
          item.resource_version = null;
          item.app_last_version_obj = null;
          item.isShare = false;
        } else {
          item.isShare = findID.reference_type === "share";
          item.resource_version_name = findID.resource_version_name || null;
          item.resource_version = findID.resource_version || null;
          item.app_last_version_obj = findID || null;
        }
      });

      (res.tools || []).forEach((item: any) => {
        const findID: any = relations.find(finditem => item.tool_id.indexOf(`${finditem.resource_id}#`) === 0 && finditem.resource_type === "tool");
        if (!findID) {
          item.resource_version = null;
          item.app_last_version_obj = null;
          item.isShare = false;
        } else {
          item.resource_version = findID.resource_version || null;
          item.resource_version_name = findID.resource_version_name || null;
          item.app_last_version_obj = findID || null;
          item.isShare = findID.reference_type === "share";
        }
      });

      (res.skills || []).forEach(item => {
        const skillItem = relations.find(finditem => finditem.resource_id === item.skill_id && finditem.resource_type === "skill");
        item.app_last_version_obj = skillItem || null;
      });

      if (res.sub_type === "deepresearch" || this.isDefaultDeepResearch) {
        document.title = res.name;
        this.agentDataServe.setAutoSaveTime(res.update_time);
        this.initDeepResearch(res);
        this.setAgentMode(this.isDefaultDeepResearch);
        this.modelSelected = res.service_name || "";
        return;
      }
      this.displayAgentData(res);
      this.historyModalTop = `${this.getContainerclientTop()}px`;
    } finally {
      this.isLoading = false;
      this.cdr.markForCheck();
    }
  }

  private initDeepResearch(data: any) {
    this.agentInfo.name = data.name;
    this.agentInfo.icon = data.icon;
    this.agentInfo.description = data.description;
    this.agentInfo.status = data.status;
    this.agentInfo.agentType = data.type;
    this.agentInfo.agentSubType = data.sub_type;
    this.allAgentInfo = data;
    this.agentBotPageService.agentDetail.set(data);
  }

  private async getModelList(id: string) {
    try {
      const res = await this.modelManagementService.getAvailableModelList({
        model_type: "LLM,IMAGE-TO-TEXT",
        with_router: true,
        publish_status: "online"
      });
      this.modelType = res.data.find(item => item.id === id)?.model_type;
      this.availableModels = res.data.map((item: any) => ({
        ...item,
        merge_name: item.model_name,
        model_name: item.model_name,
        model_nickname: item.model_name,
        model_type: item.model_type,
        model_deployment_id: item.id,
        model_provider: item.icon
      }));
    } catch {
      this.availableModels = [];
    } finally {
      this.isLoading = false;
      this.cdr.markForCheck();
    }
  }

  public exitViewHistory() {
    this.agentDataServe.setRollbackId({
      version_id: "",
      isFlowReadonly: false
    });
    this.showHistoryModal = false;
    this.loadAgent(this.agentId);
  }

  private getContainerclientTop() {
    const container = document.getElementById("agent-container");
    return container?.getBoundingClientRect()?.top + 1;
  }

  private rollbackVersion(version) {
    this.isLoading = true;
    this.service
      .rollbackAgentVersion(this.agentId, version.version_id)
      .then((res: any) => {
        this.allAgentInfo = res;
        this.displayAgentData(res);
        if (version.revert) {
          this.messageServ.success(this.i18n.transform("version_restored_succ"), { nzDuration: 3000 });
          const data = this.getUpdatedData(res);
          //图标字段长度限制，还原版本时不传base64图标
          if (data.icon && data.icon.startsWith("data:image") && data.icon.length > 64) {
            delete data.icon;
          }
          this.doTriggerSave({
            data
          });
        }
      })
      .finally(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  public turnEnabledEvent(val: boolean) {
    this.workflowSwitchEnabled = val;
  }

  private getUpdatedData(data: any): any {
    const { status, ...agentData } = data;
    if (agentData.tools) {
      agentData.tools = agentData.tools.map(tool => tool.tool_id);
    }
    if (agentData.workflows) {
      agentData.workflows = agentData.workflows.map(flow => flow.workflow_id);
    }
    if (agentData.knowledge_repos) {
      agentData.knowledge_repos = agentData.knowledge_repos.map(item => item.knowledge_repo_id);
    }
    if (agentData.mcp_servers) {
      agentData.mcp_servers = agentData.mcp_servers.map(mcp => mcp.mcp_server_id);
    }
    return agentData;
  }

  private doTriggerSave(
    config: IUpdateSingleAgentConfig = {
      data: {},
      successCb: () => {
      },
      failCb: () => {
      },
      finallyCb: () => {
      }
    }
  ) {
    this.commonLogic.doTriggerSave(this.agentId, config);
  }

  private async displayAgentData(data: any): Promise<void> {
    if (data.type === "deepresearch" || this.isDefaultDeepResearch) {
      document.title = data.name;
      this.agentDataServe.setAutoSaveTime(data.update_time);
      this.initDeepResearch(data);
      this.agentInfo.agentSubType = "deepresearch";
      this.agentInfo.agentType = "agent";
      this.setAgentMode(this.isDefaultDeepResearch);
      this.modelSelected = data.service_name || "";
      return;
    }
    const { icon, name, description, status, model_deployment_id, model_name, model_config, service_name, is_template, writing_template, reference, ...rest } =
      data;
    const {
      instructions,
      knowledge_repos,
      prologue,
      suggest_queries,
      additional_questions_config,
      memory_variables,
      tools,
      trigger_list,
      workflows,
      workflow_switch_enabled,
      scheduling_mode,
      mcp_servers,
      knowledge_retrieve_policy,
      voice_interaction,
      content_review,
      safety_barrier,
      agent_variables,
      input_variables,
      memory_config,
      scenes,
      skills
    } = this.commonLogic.handleDefaultValues(rest);

    this.commonLogic.setAgentCreatorId(rest.creator_id || "");

    let agentType = data.type || "";
    let agentSubType = data.sub_type || ""; // deep-research的类型
    this.modelSelected = service_name;
    document.title = name;
    this.agentDataServe.setAutoSaveTime(data.update_time);

    const analyzeIndex = this.headerTabs.findIndex(tab => tab.id === "analyze");
    if (analyzeIndex !== -1) {
      this.headerTabs[analyzeIndex].disabled = status !== "published";
    }

    this.knowledge_retrieve_policy = knowledge_retrieve_policy;
    //非模型优先 不赋值记忆变量
    if ([DISPATCH_MODE.KNOWLEDGE_PRIORITY, DISPATCH_MODE.MODEL_PRIORITY, DISPATCH_MODE.TOOL_PRIORITY].includes(scheduling_mode)) {
      this.agent_variables = agent_variables;
      this.agentDataServe.setAgentMemeryVars(agent_variables);
      this.input_variables = input_variables || [];
      this.agentDataServe.setInputMemoryVars(this.input_variables);
      this.setInputMemoryToPreview();
    }
    this.memory_config = memory_config;
    this.content_review = content_review;
    this.safety_barrier = safety_barrier;
    const { filter, replace, reply } = content_review;
    this.agentDataServe.setContentReviewConfig({
      enabled: content_review?.enabled ?? false,
      filter: filter ?? { keywords: "" },
      replace: replace ?? [],
      reply: reply ?? [],
      safety_barrier: safety_barrier
    });

    this.agentInfo = {
      icon,
      name,
      description,
      status,
      agentType,
      agentSubType
    };
    this.setAgentMode();
    // 一定要加 .trim()，因为提示词优化的流式接口返回的开始和结尾都包含两个空字符，
    // 导致在页面上手动删除prompt之后，页面上不显示placeholder，出现异常
    this.promptInputed = instructions ? instructions.trim() : "";
    this.agentInfo.promptTags = this.commonLogic.handlePrompttags(instructions);
    this.plugins = tools.map((toolItem: any) => ({
      tool_id: toolItem.tool_id,
      tool_display_name: toolItem.tool_display_name,
      tool_chinese_name: toolItem.tool_chinese_name,
      plugin_display_name: toolItem.plugin_display_name,
      plugin_chinese_name: toolItem.plugin_chinese_name,
      icon: toolItem.tool_icon,
      desc: toolItem.desc,
      tool_parameter: toolItem.tool_parameter,
      auth_info: toolItem.auth_info,
      credential_status: toolItem.credential_status,
      last_version_id: toolItem.last_version_id,
      last_version_name: toolItem.last_version_name,
      app_last_version_obj: toolItem.app_last_version_obj,
      resource_version: toolItem.resource_version,
      resource_version_name: toolItem.resource_version_name,
      metadata: toolItem.metadata,
      isShare: toolItem.isShare,
      is_free: toolItem.is_free,
      limit: toolItem.limit,
      usage: toolItem.usage
    }));
    this.mcp_servers = mcp_servers.map(item => ({
      server_id: item.mcp_server_id,
      avatar: item.mcp_server_icon,
      name: item.mcp_server_name,
      valid: item.valid,
      desc: item.desc,
      mcp_choose_tools: item.mcp_choose_tools,
      mcp_parameter: item.mcp_parameter
    }));
    this.agentDataServe.setLatestPluginList(this.plugins);
    this.agentDataServe.setPluginAndFlowList({
      plugins: tools,
      flows: workflows,
      kbs: knowledge_repos
    });
    this.workflows = workflows.map((item: any) => ({
      workflow_id: item.workflow_id,
      name: item.workflow_name,
      avatar: item.workflow_icon,
      last_version_id: item.last_version_id,
      desc: item.desc,
      workflow_parameter: item.workflow_parameter,
      last_version_name: item.last_version_name,
      app_last_version_obj: item.app_last_version_obj,
      resource_version: item.resource_version,
      resource_version_name: item.resource_version_name,
      isShare: item.isShare,
      code: item.code
    }));
    this.skills = skills;
    this.sceneList = scenes;
    this.workflowSwitchEnabled = workflow_switch_enabled;
    this.dispatchSelectedType = scheduling_mode;
    this.modelConfigTipService.isShowAdvancedConfig = this.dispatchSelectedType === "ToolUse";
    this.modelConfigTipService.detail = data;
    this.dispatchSelectedName = this.dispatchSelectedType ? this.DISPATCH_MODE_MAP[this.dispatchSelectedType] : "";
    this.knowledges = knowledge_repos.map((item: any) => ({
      ...item,
      icon: item.knowledge_repo_icon
    }));
    this.memos = memory_variables;
    this.trigger_list = trigger_list;
    this.triggerAdded.list = trigger_list;
    this.openTextAndQuestions = {
      prologue,
      suggest_queries,
      name,
      description
    };
    this.additional_questions_config = additional_questions_config;
    this.previewDebugData = {
      name,
      icon,
      openText: prologue,
      openQuestions: suggest_queries,
      deploymentId: model_deployment_id
    };
    const { prompt, enable } = additional_questions_config;
    this.agentDataServe.setNameAndPromptConfig({
      name,
      prompt,
      enable
    });
    this.agentDataServe.setVoiceConfig(voice_interaction);

    if (reference) {
      this.agentDataServe.setReferenceConfig({
        switch: reference.switch || false,
        json_format: reference.json_format || false
      });
    } else {
      this.agentDataServe.setReferenceConfig({
        switch: false,
        json_format: false
      });
    }

    this.agentDataServe.setAgentStatus(status);
    const modelConfig = {
      model_deployment_id,
      model_name,
      model_type: this.modelType
    };
    await this.getModelList(model_deployment_id);
    const { modelConfigUpdated, modelSelected } = this.commonLogic.updateModelConfig(modelConfig, this.availableModels);
    this.modelConfig = {
      ...modelConfigUpdated,
      temperature: parseFloat(model_config?.temperature),
      top_p: parseFloat(model_config?.top_p),
      history_size: model_config?.history_size,
      max_tokens: model_config?.max_tokens,
      frequency_penalty: model_config?.frequency_penalty,
      output_format: model_config?.output_format,
      enable_thinking: model_config?.enable_thinking
    };

    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.modelConfig
    });
    this.agentDataServe.setAgentConfig({
      name,
      description,
      modelConfig: this.modelConfig
    });
    if (!this.modelSelected) {
      this.modelSelected = modelSelected;
    }
  }

  // 在这里发送数据给预览调试
  public setInputMemoryToPreview() {
    const data: MemoryVariableInputParamType[] = [];
    for (let index = 0; index < this.input_variables.length; index++) {
      data.push({
        key: this.input_variables[index].variable_key,
        value: this.input_variables[index].default_value,
        type: this.input_variables[index].input_type,
        description: this.input_variables[index].description,
        isRight: true
      });
    }
    this.agentDataServe.setInputMemoryInPreviewDebugger(data);
  }

  private setAgentMode(defaultIsDeep: boolean = false) {
    if (this.agentInfo.agentSubType === "deepresearch" || defaultIsDeep) {
      this.curAgentModeCode = AGENT_MODE_CODE.DEEP_MODE;
      this.isShowDeepResearch = true;
    } else {
      const agentSubType = this.agentInfo.agentSubType as AGENT_MODE_CODE;
      this.curAgentModeCode = agentSubType === AGENT_MODE_CODE.PLANNING_MODE ? AGENT_MODE_CODE.PLANNING_MODE : AGENT_MODE_CODE.GENERAL_MODE;
      this.isShowDeepResearch = false;
    }
  }

  private getAgentVersions(callBackFn?) {
    this.service.getAgentVersionList(this.agentId).then(
      (res: any) => {
        const { version_list } = res || {};
        this.isVersionListEmpty = version_list.length === 0;
        this.setReleaseManageTab();
        this.historyVersionList = version_list;
        this.cdr.markForCheck();
        if (callBackFn) {
          callBackFn();
        }
      },
      () => {
        this.isVersionListEmpty = false;
        this.setReleaseManageTab();
        this.historyVersionList = [];
        this.cdr.markForCheck();
        if (callBackFn) {
          callBackFn();
        }
      }
    );
  }

  @HostListener("document:click", ["$event"])
  public onClick(): void {
    this.collapsed = false;
    this.collapsedDispatch = false;
    this.showModelConfigTip = false;
    this.showDispatchConfig = false;
    this.isShowAgentModeSelector = false;
    this.isClickChangeMode = false;
  }

  /** 当MCP删除时，需要更新下数据 **/
  public updateMcp(data: any) {
    this.mcp_servers = data || [];
  }

  /** 当MCP创建任务提交后，需要把信息继续往父元素上升 **/
  public createMcpResEmit(event: any) {
    if (event.result === "success") {
      this.mcpService
        .getMcpToolInfo(event.data.id)
        .then(() => {
          this.isShowSuccessAlert = true;
          this.createNewMcpData = event.data || {};
          this.autoCloseAlert();
        })
        .catch(() => {
          this.isShowFailAlert = true;
        });
    } else if (event.result === "fail") {
      this.isShowFailAlert = true;
    }
  }

  /** 直接在父组件添加新创建的MCP服务 **/
  public handleClickAddNewMcpService() {
    const filterData = this.mcp_servers.filter(item => item.id === this.createNewMcpData.id);
    if (filterData && filterData.length > 0) {
      return;
    }
    this.isShowSuccessAlert = false;
    this.childConfigToolCom.parentUpdateMcpData(this.createNewMcpData);
  }

  /** 当添加MCP之后需要更新下Agent **/
  public addMcpUpdateAgent(data) {
    this.saveAgent(data);
  }

  /** 保存插件工作流后更新 **/
  public saveAgent(data: any) {
    this.loadAgent(this.agentId);
  }

  // 是否是deepResearch正在加载
  public isDeepLoading(data: boolean) {
    this.isDeepResearchLoading = data;
  }

  // 开启模式选择
  handleClickOpenMode(event: any) {
    if (event) {
      event.stopPropagation();
    }
    this.isClickChangeMode = true;
    this.isShowAgentModeSelector = !this.isShowAgentModeSelector;
  }

  // 选择模式
  async handleClickSelectMode(modeCode: string, event: any) {
    if (event) {
      event.stopPropagation();
    }
    if (this.curAgentModeCode === modeCode) {
      return;
    }
    this.curAgentModeCode = modeCode as AGENT_MODE_CODE;
    this.isShowDeepResearch = this.curAgentModeCode === AGENT_MODE_CODE.DEEP_MODE;
    this.isShowAgentModeSelector = false;
    this.isClickChangeMode = false;
    await this.updateAgentInfo();
  }

  private async updateAgentInfo() {
    this.isDeepResearchLoading = true;
    const data: {
      type: AGENT_MODE_CODE;
      workflow_details?: any[];
      mcp_servers?: any[];
    } = {
      type: this.curAgentModeCode || AGENT_MODE_CODE.GENERAL_MODE
    };
    // 如果切换到规划模式，删除配置的mcp。防止看不见的工具失效导致保存报错
    if (this.curAgentModeCode === AGENT_MODE_CODE.PLANNING_MODE) {
      data.mcp_servers = [];
    }
    this.doTriggerSave({
      data,
      successCb: async () => {
        try {
          await this.loadAgent(this.agentId);
        } finally {
          this.isDeepResearchLoading = false;
        }
      },
      finallyCb: () => {
        this.isDeepResearchLoading = false;
      }
    });
  }

  public isDisabledUpdateBtn(data: number) {
    this.isDisabledReleaseBtn = data <= 0 && this.agentInfo && this.agentInfo.agentSubType === "deepresearch";
  }

  public isShowDREnter() {
    return true;
  }

  public handleClickExpandDialog(data) {
    this.isExpandDialog = data;
  }

  public configTabActiveChange(id: string) {
    if (id === this.configHeaderTabs[1].id) {
      this.goToChannelPage();
      this.triggerSettingModal.close();
    }
    this.curActiveConfigTabId = id;
  }

  public setReleaseManageTab() {
    this.configHeaderTabs[1].disabled = this.isVersionListEmpty;
    this.configHeaderTabs[1].tips = this.isVersionListEmpty ? this.i18n.transform("submit_version_first") : "";
  }

  private autoCloseAlert() {
    setTimeout(() => {
      this.isShowSuccessAlert = false;
    }, 5000);
  }
}
