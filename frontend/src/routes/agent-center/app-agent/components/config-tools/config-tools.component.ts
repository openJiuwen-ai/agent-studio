import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  OnInit,
  Output,
  Renderer2,
  SimpleChanges,
  ViewChild, ViewContainerRef
} from "@angular/core";
import { KbAddModalAfterCreateComponent } from "@routes/knowledge-center/components/kb-add-modal-after-create/kb-add-modal-after-create.component";
import { KnowledgeBaseCreationComponent } from "@routes/knowledge-center/components/knowledge-base-creation/knowledge-base-creation.component";
import { KnowledgeBaseSelectorComponent } from "@routes/knowledge-center/components/knowledge-base-selector/knowledge-base-selector.component";
import { MemoryLibSelector } from "@routes/memory-lib/components/memory-lib-selector/memory-lib-selector";
import { MemoryLibSelectorTipType } from "@routes/memory-lib/memory-lib-enums";
import type { IMemoryLibBaseInfo, IMemoryLibSelectData } from "@routes/memory-lib/memory-lib-interfaces";
import { KbAbilitiesService } from "@services/knowledge-center/kb-abilities.service";
import { MODULES } from "@shared/modules";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import { AddPluginsComponent } from "../add-plugins/add-plugins.component";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { debounceTime, Subject, Subscription, takeUntil } from "rxjs";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { TextFieldModule } from "@angular/cdk/text-field";
import { FormArray, FormBuilder, FormControl, FormGroup } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";
import { Network } from "@model";
import {
  AgentVarInfo,
  EPluginCategoryTabId,
  InputVarInfo,
  IPrologueAndQuestionsParams,
  IUpdateSingleAgentConfig
} from "../../../types/my-workspace.types";
import {
  agentCommonLogic,
  autoGenerateTipInsideList,
  getCardBgColor,
  prologueBtnClassList,
  questionsBtnClassList
} from "../../common-logic-agent";
import { IMemoModalUpdate, IMemoParam } from "../create-memo/types";
import { CreateMemoComponent } from "../create-memo/create-memo.component";
import { environment } from "src/environment/environment";
import { TriggerHalfmodalComponent } from "../trigger-modal/trigger-modal.component";
import { SkillListComponent } from "@shared/components/skill-list/skill-list.component";
import { AddWorkflowsComponent } from "../add-workflows/add-workflows.component";
import { NzTooltipDirective } from "ng-zorro-antd/tooltip";
import { type IKbParam, KbConfComponent } from "./kb-conf.component";
import { AssetIntelligentAddComponent } from "@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component";
import { ContextService } from "@services/context.service";
import { KB_DEFAULT_ICON_BASE64_STR } from "@routes/agent-center/app-knowledge/create-knowledge/default-icon-base64";
import { WORKFLOW_DEFAULT_ICON_BASE64_STR } from "@routes/agent-center/app-flow/components/create-workflow/default-icon-base64";
import { MCP_DEFAULT_ICON_BASE64_STR } from "@shared/config/default-icons-base64";
import { AddMcpServersComponent } from "../add-mcp-servers/add-mcp-servers.component";
import { PluginConfigModalComponent } from "@routes/agent-center/app-flow/components/plugin-config-modal/plugin-config-modal.component";
import { SetHalfmodalPropsService } from "@shared/services/set-halfmodal-props.service";
import { KnowledgeRepoStatus } from "@enums/knowledge-repo.enum";
import {
  AgentConfigService,
  ITimbreOption
} from "@routes/agent-center/agent-config.service";
import {
  IContentReview,
  IWorkflowField
} from "@routes/agent-center/app-flow/node.type";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { ClickOutsideDirective } from "@shared/directives/click-outside.directive";
import { TtsPlayerService } from "@services/tts-player.service";
import { cloneDeep } from "lodash";
import { AuditConfigModalComponent } from "../audit-config-modal/audit-config-modal.component";
import { WindowResizeService } from "@shared/base/window-resize.service";
import { UpdateNodeModalComponent } from "@routes/agent-center/app-agent/components/update-node-modal/update-node-modal.component";

import { AppPluginRepoService } from "@services/agent-center/app-plugin-repo.service";
import { CommonUtils } from "../../../../../utils/common.util";
import { CollapseText } from "@routes/agent-center/app-plugin/components/collapse-text/collapse-text";
import { VarMemoryModalComponent } from "@routes/agent-center/app-agent/components/var-memory-modal/var-memory-modal.component";
import { knowledgeBaseStatusMap } from "@routes/knowledge-center/knowledge-base-list/knowledge-base-list.map";
import { AddPluginAuthComponent } from "@routes/plugin-market/add-plugin/add-plugin-auth.component";
import { ModelConfigTipComponent } from "@routes/agent-center/app-agent/components/model-config-tip/model-config-tip.component";
import { ModelConfigTipService } from "@routes/agent-center/app-agent/components/model-config-tip/model-config-tip.service";
import { LLMSelectComponent } from "@routes/agent-center/app-flow/components/llm-select/llm-select.component";
import { AddToolsComponent } from "../add-tools/add-tools.component";
import { TaskPlanningComponent } from "./components/task-planning/task-planning.component";
import {
  AGENT_MODE_CODE,
  DISPATCH_MODE
} from "../../agent-bot-page/agent-bot-page.constant";
import { ScenarioGuideModalService } from "@routes/knowledge-center/components/scenario-guide-modal/scenario-guide-modal.service";
import { SKILL_TYPE } from "@routes/knowledge-center/components/scenario-guide-modal/scenario-guide-modal.constant";
import { DeleteSkillModalComponent } from "./components/delete-skill-modal/delete-skill-modal.component";
import { pluginFormatter } from "../../../utils";
import { SkillsConfigComponent } from "@shared/components/skills-config/skills-config.component";
import { NzDrawerRef, NzDrawerService } from "ng-zorro-antd/drawer";
import { NzModalService } from "ng-zorro-antd/modal";
import { NzMessageService } from "ng-zorro-antd/message";
import { StorageService } from '@shared/services/cfdata.service';

enum mapKeys {
  inputVars = "inputVars",
  userVars = "userVars",
  agent_variables = "agent_variables",
  input_variables = "input_variables",
  style = "style",
}

@Component({
  selector: "config-tools",
  templateUrl: "./config-tools.component.html",
  styleUrls: [
    "./config-tools.component.scss",
    "../../../../../styles/text-field-prebuilt.css"
  ],
  standalone: true,
  imports: [
    MODULES,
    AddPluginsComponent,
    TextFieldModule,
    SkillListComponent,
    AddWorkflowsComponent,
    AssetIntelligentAddComponent,
    AddMcpServersComponent,
    ClickOutsideDirective,
    AuditConfigModalComponent,
    CollapseText,
    VarMemoryModalComponent,
    KnowledgeBaseCreationComponent,
    KbAddModalAfterCreateComponent,
    ModelConfigTipComponent,
    LLMSelectComponent,
    TaskPlanningComponent,
    MemoryLibSelector,
    SkillsConfigComponent,
    KbConfComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.COMMON,
        I18nNamespace.MODEL_ACCESS,
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.MEMORY_LIB
      ]
    }
  ]
})
export class ConfigToolsComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild("kbCreation") kbCreation: KnowledgeBaseCreationComponent;
  @Output() turnEnabled = new EventEmitter<boolean>();
  @Output() createMcpRes = new EventEmitter<any>();
  @Output() deleteOneMcpEvent = new EventEmitter<any>();
  @Output() saveAgent = new EventEmitter<any>();
  // 当从抽屉添加MCP的时候，需要返回给父组件事件，然后刷新整个Agent的数据
  @Output() addMcpEvent = new EventEmitter<any>();
  @Output() modelTrigger = new EventEmitter<any>();

  // 合一模式相关属性
  @Input() modelSelected: string = "";
  @Input() collapsed: boolean = false;
  @Input() availableModels: any[] = [];
  @Input() modelConfig: any = {};
  @Input() showModelConfigTip: boolean = false;

  // 独立模式相关属性
  @Input() curAgentModeCode: AGENT_MODE_CODE;
  @Input() planModelSelected: string = "";
  @Input() planModelConfig: any = {};
  @Input() showPlanModelConfigTip: boolean = false;
  @Input() plugins = [];
  @Input() flows = [];
  @Input() skills = [];
  @Input() sceneList = [];
  @Input() workflowSwitchEnabled = false;
  @Input() knowledges = [];
  @Input() mcp_servers = [];
  @Input() trigger_list = [];
  @Input() memos: IMemoParam[] = [];
  @Input() knowledge_retrieve_policy: IKbParam = {
    top_k: 3,
    recall_threshold: 0.5,
    search_mode: "",
    faq_threshold: 0.9,
    need_extras_faq_search: false,
    extra_params: []
  };
  @Input() dispatchSelectedType = "";
  @Input() agent_variables: Array<AgentVarInfo> = [];
  @Input() input_variables: Array<InputVarInfo> = [];
  @Input() memory_config: IMemoryLibBaseInfo;
  @Input() openTextAndQuestions = {
    openText: "",
    openQuestions: []
  };
  @Input() additional_questions_config = {
    enable: true,
    prompt: ""
  };

  @Input() loadingFromParent = false;
  @Input() content_review: any;
  @Input() safety_barrier: boolean;
  @ViewChild("pluginAddModal") pluginModal: any;
  @ViewChild("autoGenerateTip") autoGeneTipDirective: any;
  @ViewChild("defaultConfigModalRef") defaultConfigModalRef: any;
  @ViewChild("autoGeneQuestionTip") questionTipDirective: any;
  @ViewChild(TriggerHalfmodalComponent) triggerComponent: any;
  @ViewChild(AddWorkflowsComponent) flowComponent: any;
  @ViewChild("mainContainerRef") mainContainerRef!: ElementRef;

  @ViewChild("voiceTip") voiceTip: NzTooltipDirective;
  @ViewChild(AuditConfigModalComponent) auditConfigModal: any;
  @ViewChild(VarMemoryModalComponent) varMemoryModal: any;
  @ViewChild("mcpModal") mcpModal: any;
  public AGENT_MODE_CODE = AGENT_MODE_CODE;
  public lang = CommonUtils.getLanguage();
  public isAfterCreatePlugin = false;
  public AfterCreatePluginInfo = {
    pluginId: ""
  };
  public pluginAdded: any = {
    title: this.i18n.transform("plugin"),
    collapsed: true, // 默认就是展开状态
    list: [],
    imageClass: "plugin-common-img",
    isLoading: false
  };

  public flowAdded = {
    title: this.i18n.transform("workflow"),
    collapsed: true,
    workflowSwitchEnabled: false,
    list: []
  };

  public flowLoading = false;
  public knowledgeAdded: any = {
    title: this.i18n.transform("knowledge"),
    collapsed: true,
    list: [],
    imageClass: "knowledge-common-img",
    isLoading: false
  };
  public memoryParamAdded: any = {
    title: this.i18n.transform("variable-memory-tip7"),
    collapsed: true,
    list: [],
    imageClass: "knowledge-common-img",
    isLoading: false
  };
  public inputParamAdded = {
    title: this.i18n.transform("variable-memory-tip3"),
    collapsed: true,
    list: [],
    imageClass: "knowledge-common-img",
    isLoading: false
  };
  public LongMemoryAdded: any = {
    title: this.i18n.transform("LTM"),
    collapsed: false,
    list: [],
    imageClass: "knowledge-common-img",
    isLoading: false
  };
  public triggerAdded = {
    title: this.i18n.transform("trigger"),
    collapsed: false,
    list: [],
    imageClass: "common-img",
    isLoading: false
  };
  public flowEmptyText = this.i18n.transform("flow_limit", {
    number: this.flowLimit
  });
  public memosAdded: {
    title: string;
    collapsed: boolean;
    list: IMemoParam[];
  } = {
    title: this.i18n.transform("memory_parameters"),
    collapsed: false,
    list: []
  };
  public mcpServersAdded = {
    title: this.i18n.transform("mcp_service"),
    collapsed: true,
    list: []
  };
  public mcpServerLoading = false;
  public mcpServerEmptyText = this.i18n.transform("mcpLimit", {
    number: this.mcpLimit
  });
  public openingDialogInfo = {
    collapsed: true, // 默认就是收起状态
    name: "", // 智能生成开场白的接口，需要传递应用name和description
    description: "",
    isAutoLoading: false
  };
  // 开场白
  public openingInputed = "";
  // 表示开场白和推荐问题这两处输入，所绑定的Subject
  public inputChanged = new Subject<string>();
  // 推荐问题的表单数据
  public questionListForm: FormGroup;

  public modelSelectedId = "";
  public prologueAlterModal = {
    title: this.i18n.transform("replace_statement"),
    description: this.i18n.transform("replace_statement_desc"),
    dismissTip: () => {
      this.hideAutoGenerateTip();
    },
    confirmBtn: () => {
      this.confirmAutoGenerate();
    }
  };

  public questionsAlterModal = {
    title: this.i18n.transform("question_alert_title"),
    description: this.i18n.transform("question_alert_desc"),
    dismissTip: () => {
      this.hideAutoGeneQuestionTip();
    },
    confirmBtn: () => {
      this.confirmAutoGeneQuestions();
    }
  };

  public probeInfo: any = {
    title: this.i18n.transform("probe"),
    collapsed: true,
    closeDesc: this.i18n.transform("probe_close_desc"),
    openDesc: this.i18n.transform("probe_open_desc")
  };
  // 追问
  public probeInputed = "";
  // 表示追问输入框的输入，所绑定的Subject
  public probeInputChanged = new Subject<string>();
  // 追问placeholder
  public followupPlaceholder = `- ${this.i18n.transform(
    "followup_tip1"
  )}\n- ${this.i18n.transform("followup_tip_2")}\n- ${this.i18n.transform(
    "followup_tip_3"
  )}\n- ${this.i18n.transform("followup_tip_4")}`;

  public switchState: boolean = true;
  public promptDescTip = this.i18n.transform("promptDescTip");
  public agentId = "";
  public alertIcon = `${Network.ASSETS_PATH}agent-center/agent/alert.svg`;
  public optimizeIcon = `${Network.ASSETS_PATH}agent-center/agent/optimize-prompt-icon.svg`;
  public isHCSO = false;
  public isHC = false;

  @ViewChild("kbConfRef") kbConfRef: NzTooltipDirective;
  public showKbConfRef = false;
  public kbParams: IKbParam = {
    top_k: 3,
    recall_threshold: 0.5,
    faq_threshold: 0.9,
    search_mode: "",
    need_extras_faq_search: false,
    extra_params: []
  };
  public isF1 = this.ctxServ.isF1ReqList();
  public isPOC = environment.envType === "poc";
  public kbDefaultIcon = KB_DEFAULT_ICON_BASE64_STR;
  public mcpDefaultIcon = MCP_DEFAULT_ICON_BASE64_STR;
  public flowDefaultIcon = WORKFLOW_DEFAULT_ICON_BASE64_STR;
  public modalTop = "";
  public isFlowReadonly = false;
  public voiceConfig = {
    collapsed: true,
    language: "",
    timbre: "",
    name: "",
    type: "",
    scene: ""
  };

  public changeUrl = cdnAssetUrl;
  public voiceIcon = cdnAssetUrl("assets/agent-center/icons/voice.svg");
  public voiceEnable = false;
  public timbreList = [];
  public securityCfg = { title: this.i18n.transform("llmmodalcomponent_418"), collapsed: false };
  // 插件抽屉点击确定时，已选中的插件列表
  private confirmSavePlugins: any = [];
  // 工作流抽屉点击确定时，新增的工作流列表
  private confirmSaveFlows: any = [];
  // 知识库抽屉点击确定时，已选中的知识库列表
  private confirmSaveKnowledges: any = [];
  // MCP服务抽屉点击确定时，已选中的MCP列表
  private confirmSaveMCPs: any = [];
  // 智能生成开场白tip是否显示
  private showAutoGenerateTip: boolean = false;
  // 智能生成推荐问题tip是否显示
  private showAutoGeneQuestionTip: boolean = false;
  // 每个推荐问题textarea框是否处于组合输入状态（输入中文时，拼音输入法会有中间状态）
  private isCompositionActive = false;
  private subscription!: Subscription;
  private probeSubscription!: Subscription;
  private destroy$ = new Subject<void>();
  private showVoiceTip = false;
  public auditConfig: IContentReview = {
    enabled: false,
    filter: {
      keywords: ""
    },
    replace: [],
    reply: []
  };

  public securityConfig: boolean = false;
  public showSafetyBarrier = false;
  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  private resizeSub: Subscription;
  public openLongMemory = false;
  public isShowLongMemory = false;
  public kbSelectorHalfModal: NzDrawerRef;
  public showAddBtn = true;
  public showSettingContentReview = false;
  public referenceConfig = {
    collapsed: true,
    enabled: false,
    json_formate: false
  };

  // 模型模式开关 - true:合一模式, false:独立模式
  public modelUseState = true;

  private toolFormatter = (tool) => {
    return pluginFormatter(tool, this.i18n, false);
  };

  // 选择查看的插件参数Id
  public selectedPluginId = "";


  public memoryLibData = {
    title: "记忆库",
    list: [],
    isLoading: false
  };

  public memoryLibSelectorTipType = MemoryLibSelectorTipType;

  // 当前agent的skill
  public selectedSkills = [];

  constructor(
    private appPluginRepoServ: AppPluginRepoService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private commonLogic: agentCommonLogic,
    private agentDataServe: AgentDataService,
    private appAgentServe: AppAgentRepoService,
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private renderer2: Renderer2,
    private ctxServ: ContextService,
    private halfmodalPropsServe: SetHalfmodalPropsService,
    public configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private ttsPlayerServe: TtsPlayerService,
    public kbAbilitiesService: KbAbilitiesService,
    private windowResizeService: WindowResizeService,
    public modelConfigTipService: ModelConfigTipService,
    private scenarioGuideModalServ: ScenarioGuideModalService,
    private nzModal: NzModalService,
    private viewContainerRef: ViewContainerRef,
    public drawerServ: NzDrawerService,
    private messageServ: NzMessageService
  ) {
    this.isHC = false;
    this.isShowLongMemory = this.configServ.longTermMemoryEnable();
    this.voiceEnable = this.configServ.voiceEnable();
    this.modalTop = `${this.halfmodalPropsServe.calcHalfmodalPosition().top}px`;
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version) => {
        this.isFlowReadonly = version.isFlowReadonly;
        if (this.isFlowReadonly) {
          this.questionListForm?.disable();
        } else {
          this.questionListForm && this.questionListForm.enable();
        }
      });
    this.agentDataServe
      .refAgentUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info) => {
        if (info && info?.id) {
          setTimeout(() => {
            this.addAgent(info);
          }, 0);
          this.agentDataServe
            .addAgentInfo({});
        }
      });

    this.route.queryParams.subscribe((params) => {
      this.agentId = params.agentId;
    });

    this.agentDataServe
      .knowledgesUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((response: any) => {
        this.confirmSaveKnowledges = [...response.knowledges];
      });

    this.agentDataServe
      .pluginsAndTabIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((pluginsAndCurrentTab: any) => {
        this.confirmSavePlugins = [...pluginsAndCurrentTab.plugins];
      });

    this.agentDataServe.mcpsAndTabIdUpdate$().pipe(takeUntil(this.destroy$))
      .subscribe((mcpsAndCurrentTab: any) => {
        this.confirmSaveMCPs = [...mcpsAndCurrentTab.list];
      });

    this.agentDataServe.contentReviewConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((config) => {
        const { enabled, filter, replace, reply, safety_barrier } = config;
        this.securityConfig = safety_barrier;
        this.auditConfig = {
          enabled: enabled ?? false,
          filter: { keywords: filter?.keywords ?? "" },
          replace: replace ?? [],
          reply: reply ?? []
        };
      });
    this.agentDataServe.getTriggerUpdate$().pipe(takeUntil(this.destroy$))
      .subscribe((triggerAdded: any) => {
        const { trigger_id, name, type, cron, prompt, hook_url } = triggerAdded;
        if (type === "TIMER") {
          const is_has = this.triggerAdded.list?.some(
            (item) => item.trigger_id === trigger_id
          );
          if (is_has) {
            for (let i = 0; i < this.triggerAdded.list?.length; i++) {
              const cur = this.triggerAdded.list[i];
              if (cur.trigger_id === trigger_id) {
                this.triggerAdded.list[i] = triggerAdded;
                break;
              }
            }
          } else {
            this.triggerAdded.list = [
              ...this.triggerAdded.list,
              { trigger_id, name, type, cron, prompt }
            ];
          }
        }
        if (type === "EVENT") {
          this.triggerAdded.list = [
            ...this.triggerAdded.list,
            {
              trigger_id, name,
              type,
              prompt,
              hook_url
            }
          ];
        }
      });

    this.agentDataServe?.contentReviewConfigUpdate$().pipe(takeUntil(this.destroy$))
      .subscribe((config) => {
        const { enabled, filter, replace, reply, safety_barrier } = config;
        this.securityConfig = safety_barrier;
        this.auditConfig = {
          enabled: enabled ?? false,
          filter: { keywords: filter?.keywords ?? "" },
          replace: replace ?? [],
          reply: reply ?? []
        };
        this.setShowSettingContentReview();
      });

    this.questionListForm = this.fb.group({
      headers: fb.array([])
    });

    this.agentDataServe.referenceConfigUpdate$().pipe(takeUntil(this.destroy$)).subscribe((config) => {
      if (config) {
        this.referenceConfig.enabled = config.switch;
        this.referenceConfig.json_formate = config.json_format;
      }
    });

    const pluginSates = JSON.parse(StorageService.getSessionStorage("pluginState") ?? "{}");
    StorageService.delSessionStorage("pluginState");
    const CurrentModal = pluginSates.currentModal ?? "";
    const pluginId =
      pluginSates?.new_plugin_id ?? "";
    if (CurrentModal === "plugin") {
      this.isAfterCreatePlugin = true;
      this.AfterCreatePluginInfo.pluginId = pluginId;
    }
    if (!this.voiceEnable) {
      return;
    }

    this.getTimbreList();
  }

  public setShowSettingContentReview() {
    this.showSettingContentReview =
      this.auditConfig.enabled &&
      !(
        this.auditConfig?.replace?.length > 0 ||
        this.auditConfig?.reply?.length > 0 ||
        this.auditConfig?.filter?.keywords
      );
  }

  ngAfterViewInit(): void {
    this.renderer2.listen(this.mainContainerRef.nativeElement, "scroll", () => {
      //中 Util.trigger(document, "tiScroll");

      if (this.showKbConfRef) {
        this.showKbConfRef = false;
        this.kbConfRef.hide();
      }
    });
  }

  ngOnInit() {
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe((width) => {
      this.windowWidth = width;
    });

    this.isHCSO = false;
    this.subscription = this.inputChanged
      .pipe(debounceTime(500))
      .subscribe(() => {
        this.saveAndUpdateOpeningDialogInfo();
      });
    this.probeSubscription = this.probeInputChanged
      .pipe(debounceTime(500))
      .subscribe(() => {
        this.updateAgentFollowUpPrompt();
      });

    this.showSafetyBarrier =
      !!this.configServ.getConfigs()?.safety_barrier_display && false;

    if (this.isAfterCreatePlugin) {
      this.afterCreatePlugin(this.AfterCreatePluginInfo.pluginId);
    }
    this.setShowSettingContentReview();

    this.probeInfo.collapsed = false;
  }

  ngOnDestroy() {
    this.resizeSub?.unsubscribe();
    this.subscription.unsubscribe();
    this.probeSubscription.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.plugins) {
      this.pluginAdded.list = changes.plugins.currentValue.map(this.toolFormatter);
      this.pluginAdded.collapsed = !this.pluginAdded.list;
    }

    if (changes.flows) {
      this.flowAdded.list = changes.flows.currentValue;
      this.flowAdded.collapsed = !this.flowAdded.list.length;
    }

    if (changes.skills) {
      this.selectedSkills = changes.skills.currentValue;
    }

    if (changes.workflowSwitchEnabled) {
      this.flowAdded.workflowSwitchEnabled =
        changes.workflowSwitchEnabled.currentValue;
    }

    if (changes.knowledges) {
      this.knowledgeAdded.list = changes.knowledges.currentValue;
    }

    if (changes.mcp_servers) {
      this.mcpServersAdded.list = changes.mcp_servers.currentValue;
      this.mcpServersAdded.collapsed = !this.mcpServersAdded.list.length;
    }

    if (changes.trigger_list) {
      this.triggerAdded.list = changes.trigger_list.currentValue;
    }

    if (changes.memos) {
      this.memosAdded.list = changes.memos.currentValue;
      this.agentDataServe.setMemos(this.memosAdded.list);
    }

    if (changes.knowledge_retrieve_policy) {
      this.kbParams = changes.knowledge_retrieve_policy.currentValue;
    }

    if (changes.openTextAndQuestions) {
      const { prologue, suggest_queries, name, description } =
        changes.openTextAndQuestions.currentValue;
      this.openingDialogInfo.name = name;
      this.openingDialogInfo.description = description;
      this.showHistoryOpening({
        prologue,
        suggest_queries
      });
      // 修复bug：刷新页面后，把查询接口返回的开场白和推荐问题信息，同步到service中
      this.agentDataServe.setOpenTextAndQuestions({
        prologue,
        suggest_queries
      });
    }

    if (changes?.additional_questions_config) {
      const { enable, prompt } =
        changes?.additional_questions_config?.currentValue;
      this.switchState = enable;
      this.probeInputed = prompt;
    }

    if (changes?.memory_config?.currentValue) {
      this.memoryLibData.list = [changes?.memory_config.currentValue].filter(Boolean);
    }

    if (changes?.agent_variables || changes?.input_variables) {
      if (this.agent_variables.length) {
        this.memoryParamAdded.collapsed = false;
      }
      if (this.input_variables.length) {
        this.inputParamAdded.collapsed = false;
        this.agentDataServe.setInputMemoryVars(this.input_variables);
      }
    }
  }

  get pluginLimit() {
    return this.configServ.getConfigs()?.agent_tool_bound_limit ?? 20;
  }

  get flowLimit() {
    return this.configServ.getConfigs()?.agent_workflow_bound_limit ?? 5;
  }

  get kbLimit() {
    return this.configServ.getConfigs()?.agent_knowledge_bound_limit ?? 1;
  }

  get mcpLimit() {
    return this.configServ.getConfigs()?.agent_mcp_bound_limit ?? 5;
  }

  /** 使用tiny tip点击触发，打开智能生成开场白的提示Tip */
  public handleAutoGenerateTip() {
    if (this.isFlowReadonly) {
      return;
    }
    if (this.showAutoGenerateTip) {
      this.hideAutoGenerateTip();
    } else {
      this.showAutoGenerateTip = true;
      this.autoGeneTipDirective.show();
    }
  }

  /** 使用tiny tip点击触发，打开智能生成推荐问题的提示Tip */
  public handleAutoGeneQuestionTip() {
    if (this.isFlowReadonly) {
      return;
    }
    if (this.showAutoGeneQuestionTip) {
      this.hideAutoGeneQuestionTip();
    } else {
      setTimeout(() => {
        this.showAutoGeneQuestionTip = true;
        this.questionTipDirective.show();
      }, 0);

    }
  }

  /** 检查每个推荐问题输入框是否超出最大字符512的限制。若超出，则设置错误css样式 */
  public isControlInvalid(control: any): boolean {
    const keyControl = control.get("key");
    return (
      keyControl &&
      keyControl?.invalid &&
      (keyControl?.dirty || keyControl?.touched)
    );
  }

  /** 获取推荐问题的表单数据 */
  public getHeadersControls(): FormArray {
    return this.questionListForm.get("headers") as FormArray;
  }

  checkQuestionLength(length) {
    return this.getHeadersControls().controls.length === length;
  }

  /** 删除一个推荐问题，删除后调用接口保存，如果删除最后一个自动折叠起来 */
  public deleteOneQuestion(i: any) {
    this.getHeadersControls().removeAt(i);

    this.saveAndUpdateOpeningDialogInfo();
    if (this.checkQuestionLength(0)) {
      this.openingDialogInfo.collapsed = true;
    }
  }

  /** 用户点击加号时，下方会自动增加一个空输入框，最多三个，新增时如果处于折叠状态，自动展开 */
  public onCompositionStart() {
    if (this.checkQuestionLength(3)) {
      return;
    }
    if (this.openingDialogInfo.collapsed) {
      this.openingDialogInfo.collapsed = false;
    }
    this.addOneQuestion();
  }


  // 输入后，调用接口更新推荐问题
  public onInputChange(event: any, index: number): void {
    this.inputChanged.next(event);
  }

  // 如果已经有未填写的输入框则不让新增
  public hasBlankItem() {
    const controls = this.getHeadersControls().controls;
    return Boolean(controls.find((item) => !item.value.key));
  }

  public isAllTextareasEmpty(): boolean {
    const controls = this.getHeadersControls().controls;
    return controls.every((item) => !item.value.key);
  }

  /** 增加一个推荐问题 */
  public addOneQuestion() {
    if (this.isFlowReadonly) {
      return;
    }
    (this.questionListForm.get("headers") as FormArray).push(
      this.fb.group({
        key: new FormControl("")
      })
    );
  }

  // 收起和折叠
  public changeCollapsedState(configInfo: any) {
    const collapsed = configInfo.collapsed;
    configInfo.collapsed = !collapsed;
    if (this.checkQuestionLength(0)) {
      this.addOneQuestion();
    }
    this.cdr.markForCheck();
  }

  /** 点击插件的添加按钮 */
  public handleAddPlugin(drawerRef: NzDrawerRef): void {
    if (this.isFlowReadonly) {
      return;
    }
    this.agentDataServe.setClickFlagPlugin("add");
    drawerRef.open();

  }

  public closePluginDrawer(drawerRef: NzDrawerRef): void {
    drawerRef.close();
  }

  /**
   * 根据插件id，添加插件下的所有工具
   * @param pluginId
   */
  public addAllToolsByPluginId(pluginId: string) {
    if (!pluginId) {
      return;
    }
    this.appPluginRepoServ.getPluginById(pluginId).then((res) => {
      const plugin = res?.data;
      const toolList = plugin?.request_info?.tool_info?.map((item) => {
        return {
          tool_id: `${pluginId}#${item.tool_id}`,
          tool_display_name: item.tool_display_name,
          tool_chinese_name: item.tool_chinese_name,
          plugin_display_name: plugin?.plugin_display_name,
          desc: item.tool_desc,
          icon: plugin.icon,
          plugin_chinese_name: plugin.plugin_chinese_name,
          auth_info: item.auth_info,
          credential_status: item.credential_status,
          is_free: item.is_free,
          limit: item.limit,
          usage: item.usage
        };
      });

      toolList.forEach((item) => {
        this.pluginAdded?.list.push(item);
      });
      this.pluginAdded.list = this.pluginAdded.list.map(item => {
        return {
          ...this.toolFormatter(item),
          id: item.tool_id
        };
      });
      this.triggerSavePlugins(this.pluginAdded.list, true);
    });
  }

  /** 创建插件后 */
  public afterCreatePlugin(pluginId) {
    this.nzModal.info({
      nzTitle: this.i18n.transform("plug_created_success"),
      nzContent: this.i18n.transform("plug_created_success_text"),
      nzOnOk: () => {
        this.addAllToolsByPluginId(pluginId);
      }
    });
  }

  /** 接收子组件每增加一个插件发出的信号 */
  public handlePluginAdded(pluginAdded: any[]) {
    this.confirmSavePlugins = [...pluginAdded];
  }

  /** 接收子组件每减少一个插件发出的信号 */
  public handlePluginReduced(pluginReduced: any[]) {
    this.confirmSavePlugins = [...pluginReduced];
  }

  /** 点击插件抽屉的确定按钮 */
  public closeAndSavePlugins(drawerRef: NzDrawerRef): void {
    drawerRef.close();
    this.pluginAdded.isLoading = true;
    this.triggerSavePlugins(this.confirmSavePlugins, true);
  }

  public deleteOnePluginPre(pluginItem): void {
    const pluginOption = this.scenarioGuideModalServ.getSkillOption(
      pluginItem,
      SKILL_TYPE.PLUGIN
    );
    if (this.curAgentModeCode === AGENT_MODE_CODE.PLANNING_MODE) {
      const quotaData = [];
      this.sceneList?.forEach((scene) => {
        scene?.guidelines?.forEach((guide) => {
          if (guide?.tools?.find((item) => item.id === pluginOption.id)) {
            quotaData.push({
              sceneName: scene.name,
              guideName: guide.condition
            });
          }
        });
      });
      if (quotaData.length) {
        const modalRef = this.nzModal.create({
          nzTitle: null,
          nzFooter: null,
          nzContent: DeleteSkillModalComponent,
          nzViewContainerRef: this.viewContainerRef,
          nzWidth: 700,
          nzData: {
            quotaData
          }
        });
        modalRef.afterClose.subscribe(() => {
          this.deleteOnePlugin(pluginItem);
        });
        return;
      }
    }
    this.deleteOnePlugin(pluginItem);
  }

  /** 删除一个插件 */
  public deleteOnePlugin(pluginItem: any) {
    this.pluginAdded.isLoading = true;
    const pluginList = this.pluginAdded.list.filter(
      (item: any) => item.tool_id !== pluginItem.tool_id
    );
    const data = {
      tools: pluginList.map((item: any) => item.tool_id)
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        this.pluginAdded.list = pluginList.map(this.toolFormatter);
        // 在Agent创编页，每删除一个插件，数据库保存成功后，同步刷新service的值
        this.agentDataServe.setPluginsAndTabId(
          EPluginCategoryTabId.MARKET,
          this.pluginAdded.list
        );
        this.agentDataServe.setLatestPluginList(this.pluginAdded.list);
        this.agentDataServe.setPluginAndFlowList({
          plugins: pluginList
        });
        this.messageServ.success(this.i18n.transform("successfully_deleted_plugin"), { nzDuration: 3000 });
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.pluginAdded.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /** 配置插件/工作流参数 */
  public configParams(type, item) {
    let inputParams: IWorkflowField[] = [];
    let outputParams: IWorkflowField[] = [];
    let parameter = "";
    let id = null;
    if (type === "tool") {
      const { tool_parameter, tool_id } = item;
      parameter = tool_parameter;
      id = tool_id;
    } else if (type === "workflow") {
      const { workflow_parameter, workflow_id } = item;
      parameter = workflow_parameter;
      id = workflow_id;
    } else if (type === "mcp") {
      const { mcp_parameter, server_id } = item;
      parameter = mcp_parameter;
      id = server_id;
    }
    if (parameter) {
      inputParams = JSON.parse(parameter);
    } else {
      inputParams = [];
    }
    const refs = [
      {
        name: this.i18n.transform("variable-memory-tip7"),
        _label: this.i18n.transform("variable-memory-tip7"),
        expanded: true,
        children: [],
        checked: "indeterminate",
        hidden: true
      },
      {
        name: this.i18n.transform("variable-memory-tip8"),
        _label: this.i18n.transform("variable-memory-tip8"),
        expanded: true,
        children: [],
        checked: "indeterminate"
      }
    ];
    // 收集agent_variables中的引用数据
    this.agent_variables.forEach((item: any) => {
      item.name = item.variable_key;
      refs[0].children.push(item);
    });
    // 收集input_variables中的引用数据
    this.input_variables.forEach((item: any) => {
      item.name = item.variable_key;
      refs[1].children.push(item);
    });
    const refInfos: any[] = [DISPATCH_MODE.KNOWLEDGE_PRIORITY, DISPATCH_MODE.MODEL_PRIORITY, DISPATCH_MODE.TOOL_PRIORITY].includes(this.dispatchSelectedType as any) ? cloneDeep(refs) : [];
    const drawerRef = this.drawerServ.create<PluginConfigModalComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzContent: PluginConfigModalComponent,
      nzWidth: this.halfModalWidth,
      nzContentParams: {
        type: type,
        detail: item,
        inputParams,
        isFlowReadonly: this.isFlowReadonly,
        outputParams,
        refInfos
      }
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();

      // 监听子组件Output事件
      instance.confirm.subscribe((info) => {
        const { conf, type } = info;
        if (type === "tool") {
          this.pluginAdded.list.forEach((item) => {
            if (item.tool_id === id) {
              item.id = id;
              item.tool_parameter = JSON.stringify(conf.params);
            }
          });
          this.triggerSavePlugins(this.pluginAdded.list, true);
        } else if (type === "workflow") {
          this.flowAdded.list.forEach((item) => {
            if (item.workflow_id === id) {
              item.workflow_id = id;
              item.workflow_parameter = JSON.stringify(conf.params);
            }
          });
          this.triggerSaveFlows(this.flowAdded.list, true, this.i18n.transform("successfully_update_workflow"));
        } else if (type === "mcp") {
          const data = [];
          for (let index = 0; index < this.mcp_servers.length; index++) {
            if (this.mcp_servers[index].server_id === id) {
              data.push({
                ...this.mcp_servers[index],
                id: id,
                mcp_parameter: JSON.stringify(conf.params)
              });
            } else {
              data.push(this.mcp_servers[index]);
            }
          }
          this.triggerSaveMcp(data, true);
        }
        drawerRef.close();
      });

      instance.cancelEvt.subscribe(() => {
        drawerRef.close();
      });

    });
  }

  public generatePlugins() {
    const existingCount = this.pluginAdded.list.length;
    if (this.isFlowReadonly) {
      return;
    }

    if (existingCount >= 20) {
      this.messageServ.warning(this.i18n.transform("up_to_plugin_limit"), { nzDuration: 3000 });
      return;
    }
    this.pluginAdded.isLoading = true;
    this.appAgentServe.generatePlugins(this.agentId).then(
      (res) => {
        this.pluginAdded.isLoading = false;
        const { tools } = res || {};
        if (!tools.length) {
          this.messageServ.warning(this.i18n.transform("no_recommended_plugins"), { nzDuration: 3000 });
          return;
        }
        // 根据 tool_id 去重
        const uniqueTools = tools.filter((item) => {
          const exists = this.pluginAdded?.list.some(
            (existingItem) => existingItem.tool_id === item.tool_id
          );
          return !exists;
        });
        // 截取 uniqueTools 列表，确保插件总数不超过20
        const remainingCount = 20 - existingCount;
        const toolsToAdd = uniqueTools.slice(0, remainingCount);
        // 追加
        const pluginsAutoAdded = toolsToAdd.map((item) => ({
          tool_id: item.tool_id,
          tool_display_name: item.tool_name,
          icon: item.tool_icon,
          is_free: item.is_free,
          limit: item.limit,
          usage: item.usage
        }));
        pluginsAutoAdded.forEach((item) => {
          this.pluginAdded?.list.push(item);
        });
        this.messageServ.success(this.i18n.transform("intelligent_plugin_added"), { nzDuration: 3000 });
        this.triggerSavePlugins(this.pluginAdded?.list, false);
        this.cdr.markForCheck();
      },
      () => {
        this.pluginAdded.isLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  /**
   * 获取插件名（国际化）
   */
  public getPluginName(pluginItem) {
    if (this.lang === "zh-cn") {
      return pluginItem?.plugin_chinese_name ?? "--";
    } else {
      return pluginItem?.plugin_display_name ?? "--";
    }
  }

  /**
   * 获取工具名（国际化）
   */
  public getToolName(pluginItem): string {
    if (this.lang === "zh-cn") {
      return pluginItem?.tool_chinese_name ?? "--";
    } else {
      return pluginItem?.tool_display_name ?? "--";
    }
  }

  /** 点击工作流的添加按钮 */
  public openFlowHalfmodal(drawerRef: NzDrawerRef): void {
    if (this.isFlowReadonly) {
      return;
    }

    this.agentDataServe.setClickFlagWorkflow("add");
    drawerRef.open();
  }

  public closeFlowDrawer(drawerRef: NzDrawerRef): void {
    drawerRef.close();
  }

  /** 接收子组件每增加一个工作流发出的信号 */
  public handleFlowAdded(knowledgeAdded: any[]) {
    this.confirmSaveFlows = [...knowledgeAdded];
  }

  /** 接收子组件每减少一个工作流发出的信号 */
  public handleFlowReduced(knowledgeReduced: any[]) {
    this.confirmSaveFlows = [...knowledgeReduced];
  }

  /** 点击【添加工作流】抽屉的确定按钮 */
  public closeAndSaveFlows(drawerRef: NzDrawerRef): void {
    drawerRef.close();
    this.flowLoading = true;
    this.triggerSaveFlows(this.confirmSaveFlows, true);
  }

  /** 删除一个工作流 */
  public deleteOneFlow(flowItem: any) {
    this.flowLoading = true;
    const flowList = this.flowAdded.list.filter(
      (item: any) => item.workflow_id !== flowItem.workflow_id
    );
    const data = {
      workflows: flowList.map((item: any) => item.workflow_id)
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        this.flowAdded.list = flowList;
        this.agentDataServe.setPluginAndFlowList({
          flows: flowList
        });
        this.messageServ.success(this.i18n.transform("successfully_deleted_workflow"), { nzDuration: 3000 });
        this.deleteFlowUpdateConfirm(flowItem);
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.flowLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  public deleteFlowUpdateConfirm(flowItem) {

    const index = this.confirmSaveFlows.findIndex(
      (workflowItem: any) => workflowItem.workflow_id === flowItem.workflow_id
    );
    if (index > -1) {
      this.confirmSaveFlows.splice(index, 1);
    }
  }

  public generateFlows() {
    if (this.isFlowReadonly) {
      return;
    }

    const existingCount = this.flowAdded.list.length;
    if (existingCount >= 5) {
      this.messageServ.warning(this.i18n.transform("up_to_workflow_limit"), { nzDuration: 3000 });
      return;
    }
    this.flowLoading = true;
    this.appAgentServe.generateFlows(this.agentId).then(
      (res) => {
        this.flowLoading = false;
        const { workflows } = res || {};
        if (!workflows.length) {
          this.messageServ.warning(this.i18n.transform("no_recommended_workflows"), { nzDuration: 3000 });
          return;
        }
        // 根据 workflow_id 去重
        const uniqueFlows = workflows.filter((item) => {
          const exists = this.flowAdded?.list.some(
            (existingItem) => existingItem.workflow_id === item.workflow_id
          );
          return !exists;
        });
        // 截取 uniqueFlows 列表，确保工作流总数不超过5
        const remainingCount = 5 - existingCount;
        const flowsToAdd = uniqueFlows.slice(0, remainingCount);
        // 追加
        const flowsAutoAdded = flowsToAdd.map((item) => ({
          workflow_id: item.workflow_id,
          name: item.workflow_name,
          avatar: item.workflow_icon,
          code: item.code
        }));
        flowsAutoAdded.forEach((item) => {
          this.flowAdded?.list.push(item);
        });
        this.messageServ.success(
          this.i18n.transform("intelligent_workflow_added"),
          { nzDuration: 3000 }
        );
        this.triggerSaveFlows(this.flowAdded?.list, false);
        this.cdr.markForCheck();
      },
      () => {
        this.flowLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  /** 取消MCP创建的时候会返回MCP列表页面 **/
  public backToMcpListEmit(drawerRef: NzDrawerRef) {
    drawerRef.open();
  }

  /** 点击MCP服务的添加按钮 */
  public openMCPHalfmodal(drawerRef: NzDrawerRef): void {
    if (this.isFlowReadonly) {
      return;
    }
    this.agentDataServe.setClickFlagMCP("add");
    drawerRef.open();
  }

  public closeMcpDrawer(drawerRef: NzDrawerRef): void {
    drawerRef.close();
  }

  /** 当用户去查看MCP的详情时，需要把MCP的列表侧边栏给隐藏 **/
  public hideMcpHalfModal(drawerRef: NzDrawerRef): void {
    drawerRef.close();
  }

  /** 接收子组件每增加一个MCP服务发出的信号 */
  public handleMCPsAdded(mcpAdded: any[]) {
    this.confirmSaveMCPs = [...mcpAdded];
  }

  /** 接收子组件每减少一个MCP服务发出的信号 */
  public handleMCPsReduced(mcpReduced: any[]) {
    this.confirmSaveMCPs = [...mcpReduced];
  }

  /** 点击【添加MCP服务】抽屉的确定按钮 */
  public closeAndSaveMCPs(drawerRef: NzDrawerRef): void {
    drawerRef.close();
    this.mcpServerLoading = true;
    this.triggerSaveMCPs(this.confirmSaveMCPs, true);
  }

  public selectTool(mcp: any) {
    const drawerRef = this.drawerServ.create<AddToolsComponent, any>({
      nzTitle: this.i18n.transform('select_tool'),
      nzFooter: null,
      nzContent: AddToolsComponent,
      nzWidth: this.halfModalWidth,
      nzContentParams: {
        mcp,
        agentId: this.agentId
      }
    });
    drawerRef.afterClose.subscribe(() => {
      this.addMcpEvent.emit();
    });
  }

  /** 删除一个MCP服务 */
  public deleteOneMCP(mcpItem: any) {
    this.mcpServerLoading = true;
    const list = this.mcpServersAdded.list.filter(
      (item: any) => item.server_id !== mcpItem.server_id
    );
    const data = {
      mcp_servers: list.map((item: any) => item.server_id)
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        this.mcpServersAdded.list = list;
        this.messageServ.success(
          this.i18n.transform("successfully_deleted_mcp"),
          { nzDuration: 3000 }
        );
        this.deleteOneMcpEvent.emit(this.mcpServersAdded.list);
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.mcpServerLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  public showAddMemo(selectedName = "") {
    if (!selectedName && this.isFlowReadonly) {
      return;
    }

    const drawerRef = this.drawerServ.create<CreateMemoComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzContent: CreateMemoComponent,
      nzWidth: this.halfModalWidth,
      nzContentParams: {
        memoInput: {
          agentId: this.agentId,
          memos: this.memosAdded.list,
          selectedName,
          isFlowReadonly: this.isFlowReadonly
        }
      }
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();

      // 监听子组件Output事件
      instance.confirm.subscribe((memoUpdate: IMemoModalUpdate) => {
        if (memoUpdate.isUpdated) {
          this.memosAdded.list = memoUpdate.memos;
          this.agentDataServe.setMemos(this.memosAdded.list);
        }
      });

    });
  }

  /** 点击记忆-变量的添加按钮 */
  public handleAddMemoryParam(type: "userVars" | "inputVars"): void {
    if (this.isFlowReadonly) {
      return;
    }
    console.log("xxx");
    if (type === "userVars") {
      this.varMemoryModal.open(this.agent_variables, true, false);
    } else {
      this.varMemoryModal.open(this.input_variables, false, true);
    }
  }

  public saveMemoryVarsFn(data) {
    const userVarAndInputVar = this.getUserVariableAndInputVariable(data);
    let _data = {};
    if (userVarAndInputVar[mapKeys.userVars]) {
      _data[mapKeys.agent_variables] = userVarAndInputVar[mapKeys.userVars];
    }
    if (userVarAndInputVar[mapKeys.inputVars]) {
      _data[mapKeys.input_variables] = userVarAndInputVar[mapKeys.inputVars];
    }
    this.doTriggerSave({
      data: _data,
      successCb: () => {
        this.messageServ.success(
          this.i18n.transform("addplugincomponent_5"),
          { nzDuration: 3000 }
        );
        this.varMemoryModal.dismiss();
        if (userVarAndInputVar[mapKeys.userVars]) {
          this.agent_variables = userVarAndInputVar[mapKeys.userVars];
          this.memoryParamAdded.collapsed = false;
          this.agentDataServe.setAgentMemeryVars(userVarAndInputVar[mapKeys.userVars]);
        }
        if (userVarAndInputVar[mapKeys.inputVars]) {
          this.input_variables = userVarAndInputVar[mapKeys.inputVars];
          this.inputParamAdded.collapsed = false;
          this.agentDataServe.setInputMemoryVars(userVarAndInputVar[mapKeys.inputVars]);
        }
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.cdr.markForCheck();
        this.varMemoryModal.dismiss();
      }
    });
  }

  // 获取用户变量和入参变量
  private getUserVariableAndInputVariable(data) {
    let result = {};
    if (data[mapKeys.userVars]) {
      result[mapKeys.userVars] = [];
      for (let index = 0; index < data[mapKeys.userVars].length; index++) {
        result[mapKeys.userVars].push({
          variable_key: data[mapKeys.userVars][index].key,
          description: data[mapKeys.userVars][index].description,
          default_value: data[mapKeys.userVars][index].value
        });
      }
    }
    if (data[mapKeys.inputVars]) {
      result[mapKeys.inputVars] = [];
      for (let index = 0; index < data[mapKeys.inputVars].length; index++) {
        result[mapKeys.inputVars].push({
          variable_key: data[mapKeys.inputVars][index].key,
          description: data[mapKeys.inputVars][index].description,
          default_value: data[mapKeys.inputVars][index].value,
          input_type: data[mapKeys.inputVars][index].type
        });
      }
    }
    return result;
  }

  public isDisabledPlugin() {
    return this.confirmSavePlugins.length > this.pluginLimit || this.confirmSavePlugins.length === 0;
  }

  public isDisabledFlow() {
    return this.confirmSaveFlows.length > this.flowLimit || this.confirmSaveFlows.length === 0;
  }

  public isDisabledMCP() {
    return this.confirmSaveMCPs.length > this.mcpLimit || this.confirmSaveMCPs.length === 0;
  }

  /** 删除一个知识库 */
  public deleteOneKnowledge(knowledgeItem: any) {
    if (this.kbAbilitiesService.isResourceDisabled) {
      return;
    }
    this.knowledgeAdded.isLoading = true;
    const knowledgeList = this.knowledgeAdded.list.filter(
      (item: any) =>
        this.kbAbilitiesService.getKbId(item) !==
        this.kbAbilitiesService.getKbId(knowledgeItem)
    );
    const kbIds =
      knowledgeList?.map((kb) => this.kbAbilitiesService.getKbId(kb)) ?? [];
    const data = {
      knowledge_repos: kbIds
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        this.knowledgeAdded.list = knowledgeList;
        this.agentDataServe.setPluginAndFlowList({
          kbs: knowledgeList
        });
        this.messageServ.success(
          this.i18n.transform("successfully_deleted_knowledge"),
          { nzDuration: 3000 }
        );
        this.cdr.markForCheck();
        this.kbParams.show_source = false;
        this.kbTipCtx.outputs.updatedParam(this.kbParams);
      },
      finallyCb: () => {
        this.knowledgeAdded.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  /** 点击插件和知识库抽屉的取消按钮 */
  public dismiss(halfmodal: NzDrawerRef): void {
    halfmodal.close();
  }

  public confirmAutoGenerate() {
    if (this.isFlowReadonly) {
      return;
    }

    if (this.prologueInfo.collapsed) {
      this.changeCollapsedPrologue(this.prologueInfo);
    }
    this.hideAutoGenerateTip();
    this.prologueInfo.isAutoLoading = true;
    this.appAgentServe.generatePrologue(this.agentId).then(
      (res: any) => {
        this.prologueInfo.isAutoLoading = false;
        const { prologue } = res;
        this.showHistoryOpening({ prologue });
        this.cdr.markForCheck();
        this.messageServ.success(
          this.i18n.transform("intelligent_generate_remark"),
          { nzDuration: 3000 }
        );
        const data = {
          prologue
        };

        this.doTriggerSave({
          data,
          successCb: () => {
            // 同步刷新service中开场白信息
            this.agentDataServe.setOpenTextAndQuestions({
              prologue
            });
          }
        });
      },
      () => {
        this.prologueInfo.isAutoLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  public confirmAutoGeneQuestions() {
    if (this.isFlowReadonly) {
      return;
    }
    if (this.openingDialogInfo.collapsed) {
      this.changeCollapsedState(this.openingDialogInfo);
    }
    this.hideAutoGeneQuestionTip();
    this.openingDialogInfo.isAutoLoading = true;
    this.appAgentServe.generateQuestions(this.agentId).then(
      (res: any) => {
        this.openingDialogInfo.isAutoLoading = false;
        const { questions } = res;
        this.showHistoryOpening({ suggest_queries: questions });
        this.cdr.markForCheck();
        if (questions.length === 0) {
          this.addOneQuestion();
          this.messageServ.warning(
            this.i18n.transform("no_recommended_questions"),
            { nzDuration: 3000 }
          );
        } else {
          this.messageServ.success(
            this.i18n.transform("intelligent_generate_questions"),
            { nzDuration: 3000 }
          );
        }
        const data = {
          suggest_queries: questions
        };

        this.doTriggerSave({
          data,
          successCb: () => {
            // 同步刷新service中推荐问题信息
            this.agentDataServe.setOpenTextAndQuestions({
              suggest_queries: questions
            });
          }
        });
      },
      () => {
        this.openingDialogInfo.isAutoLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  public onSwitchChange($event: boolean) {
    this.scrollToBottom();
    this.switchState = $event;
    this.agentDataServe.setNameAndPromptConfig({
      enable: $event
    });
    this.updateAgentFollowUpPrompt();
  }

  public updateFollowUpPrompt(event: string) {
    this.agentDataServe.setNameAndPromptConfig({
      prompt: event
    });
    this.probeInputChanged.next(event);
  }

  public onContentReviewSwitchChange($event: boolean) {
    event?.stopPropagation?.();
    this.saveChangeSecurity($event, this.securityConfig);
  }

  public securitySwitchChange($event: boolean) {
    event?.stopPropagation?.();
    this.saveChangeSecurity(this.auditConfig.enabled, $event);
  }

  public saveChangeSecurity(auditConfigEnable, securityVal) {
    this.scrollToBottom();
    const param = {
      enabled: auditConfigEnable
    };
    const config = this.auditConfig;
    const data = {
      content_review: { ...config, ...param },
      safety_barrier: securityVal
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        this.agentDataServe.setContentReviewConfig({
          ...param,
          safety_barrier: this.securityConfig
        });
      },
      finallyCb: () => {
        this.cdr.markForCheck();
      }
    });
  }

  // 保存内容审核配置
  public onSaveAuditConfig(param) {
    const data = {
      content_review: param
    };
    this.doTriggerSave({
      data,
      successCb: () => {
        this.agentDataServe.setContentReviewConfig({
          ...param,
          safety_barrier: this.securityConfig
        });
      },
      finallyCb: () => {
        this.cdr.markForCheck();
      }
    });
  }

  /** 调用接口保存开场白和推荐问题，并同步刷新service中的值 */
  private saveAndUpdateOpeningDialogInfo() {
    let questionList: any = [];
    const headers = this.questionListForm.get("headers")?.value;

    if (headers) {
      headers.forEach((item: any) => {
        if (item.key.trim() !== "") {
          questionList.push(item.key);
        }
      });
    }

    // 同步刷新service中开场白信息
    this.agentDataServe.setOpenTextAndQuestions({
      prologue: this.openingInputed,
      suggest_queries: questionList
    });

    const data = {
      prologue: this.openingInputed,
      suggest_queries: questionList
    };
    this.doTriggerSave({
      data
    });
  }

  /** 调用接口保存追问配置 */
  public updateAgentFollowUpPrompt() {
    const data = {
      additional_questions_config: {
        enable: this.switchState,
        prompt: this.probeInputed
      }
    };
    this.doTriggerSave({
      data
    });
  }

  public kbTipCtx = {
    kbId: "",
    selectedNum: 0,
    outputs: {
      updatedParam: ($event: IKbParam) => {
        this.kbParams = { ...$event };
        this.showKbConfRef = false;
        this.kbConfRef?.hide();

        this.doTriggerSave({
          data: {
            knowledge_retrieve_policy: {
              ...$event
            }
          }
        });
      }
    }
  };

  public onClickKbConf(event: MouseEvent) {
    event.stopPropagation();

    if (this.isFlowReadonly || this.kbAbilitiesService?.isResourceDisabled || !this.knowledgeAdded?.list?.length) {
      return;
    }

    setTimeout(()=>{
      this.showKbConfRef = !this.showKbConfRef;
      if (this.showKbConfRef) {
        this.kbTipCtx.kbId = this.kbAbilitiesService?.getKbId(
          this.knowledgeAdded?.list?.[0]
        );
        this.kbTipCtx.selectedNum = this.knowledgeAdded?.list?.length || 0;
        this.kbConfRef.show();
      } else {
        this.kbConfRef.hide();
      }
    })

  }

  public getBgColor(item, type) {
    switch (type) {
      case "kb": {
        const { status, hover } = item;
        const valid = KnowledgeRepoStatus?.CLOSE !== status;
        return getCardBgColor({ valid, hover, isKnowledge: true });
      }
      case "plugin": {
        return getCardBgColor({ valid: !item.unauthenticated, hover: item.hover });
      }
      default: {
        return getCardBgColor(item);
      }
    }
  }

  public openAuditHalfModal($event) {
    $event?.stopPropagation?.();
    this.auditConfigModal.open();
  }

  /** 展示历史的开场白和推荐问题信息。页面强制刷新后 和 智能生成成功时调用 */
  private showHistoryOpening(params: IPrologueAndQuestionsParams) {
    const { prologue, suggest_queries } = params;

    if (prologue) {
      this.openingInputed = prologue;
    }

    if (suggest_queries?.length) {
      (this.questionListForm.controls.headers as FormArray).clear();
      suggest_queries?.forEach((qHistory) => {
        (this.questionListForm.controls.headers as FormArray).push(
          this.fb.group({
            key: new FormControl(qHistory)
          })
        );
      });
    }
  }

  /** 关闭覆盖开场白的提示Tip */
  private hideAutoGenerateTip(): void {
    this.showAutoGenerateTip = false;
    this.autoGeneTipDirective?.hide();
  }

  /** 关闭覆盖推荐问题的提示Tip */
  private hideAutoGeneQuestionTip(): void {
    this.showAutoGeneQuestionTip = false;
    this.questionTipDirective?.hide();
  }


  private scrollToBottom() {
    setTimeout(() => {
      this.mainContainerRef.nativeElement.scrollTop =
        this.mainContainerRef.nativeElement.scrollHeight;
    }, 0);
  }

  private triggerSaveMcp(tools: any[], isShowMessage: boolean): void {
    const data = {
      mcp_details: tools.map((item) => {
        return {
          mcp_id: item.server_id || item.id,
          mcp_param: item.mcp_parameter
        };
      })
    };
    this.doTriggerSave({
      data,
      successCb: () => {
        if (isShowMessage) {
          this.messageServ.success(
            this.i18n.transform("successfully_update_mcp"),
            { nzDuration: 3000 }
          );
        }
        this.saveAgent.emit({});
        this.cdr.markForCheck();
      }
    });

  }

  private triggerSavePlugins(tools: any[], isShowMessage: boolean): void {
    const data = {
      //添加插件取id 更新配置取tool_id
      tool_details: tools.map((item: any) => {
        return {
          tool_id: item.id || item.tool_id,
          tool_version: item.resource_version,
          tool_param: item.tool_parameter
        };
      })
    };

    this.doTriggerSave({
      data,
      successCb: () => {
        // 在添加插件的抽屉里，点击确定，数据库保存成功后，同步刷新service的值
        this.agentDataServe.setPluginsAndTabId(
          EPluginCategoryTabId.MARKET,
          tools
        );
        this.agentDataServe.setPluginAndFlowList({ plugins: tools });
        this.agentDataServe.setLatestPluginList(tools);
        if (isShowMessage) {
          this.messageServ.success(
            this.i18n.transform("successfully_update_plugin"),
            { nzDuration: 3000 }
          );
        }
        this.saveAgent.emit({});
        this.pluginAdded.list = tools.map(this.toolFormatter);
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.pluginAdded.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  private triggerSaveFlows(tools: any[], isShowMessage: boolean, message?: string): void {
    const connectionsCount = tools.filter((toolItem) =>
      this.flowAdded.list.find(
        (flowsitem) => flowsitem.workflow_id === toolItem.workflow_id
      )
    ).length;
    const addCount = tools.length - connectionsCount;
    const deleteCount = this.flowAdded.list.length - connectionsCount;
    let msg = "";
    if (addCount > 0 && deleteCount > 0) {
      msg = `${this.i18n.transform("addplugincomponent_8")}${addCount}，${this.i18n.transform("addplugincomponent_9")}${deleteCount}`;
    } else if (addCount > 0) {
      msg = this.i18n.transform("addplugincomponent_10");
    } else if (deleteCount > 0) {
      msg = this.i18n.transform("addplugincomponent_11");
    } else {
      msg = this.i18n.transform("addplugincomponent_10");
    }

    const data = {
      workflow_details: tools.map((item) => {
        return {
          workflow_id: item.workflow_id,
          workflow_version: item.resource_version,
          workflow_param: item.workflow_parameter
        };
      })
    };
    this.doTriggerSave({
      data,
      successCb: () => {
        this.agentDataServe.setPluginAndFlowList({ flows: tools });
        this.flowAdded.list = tools;
        this.flowAdded.collapsed = !tools.length;
        if (isShowMessage) {
          this.messageServ.success(
            message ? message : msg,
            { nzDuration: 3000 }
          );
        }
        this.saveAgent.emit({});
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.flowLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  private triggerSaveMCPs(tools: any[], isShowMessage: boolean): void {
    const data = {
      mcp_servers: [],
      mcp_choose_tools: {}
    };
    tools.forEach(item => {
      data.mcp_servers.push(item.server_id);
      data.mcp_choose_tools[item.server_id] = [...item.selectedTools];
    });

    this.doTriggerSave({
      data,
      successCb: () => {
        // 在添加MCP服务的抽屉里，点击确定，数据库保存成功后，同步刷新service的值
        this.agentDataServe.setMCPsAndTabId(EPluginCategoryTabId.MARKET, tools);
        if (isShowMessage) {
          this.messageServ.success(
            this.i18n.transform("successfully_update_mcp"),
            { nzDuration: 3000 }
          );
        }
        this.addMcpEvent.emit({});
        this.mcpServersAdded.list = tools.map((item) => ({
          avatar: item?.icon,
          ...item,
          desc: item.description,
          mcp_choose_tools: [...item.selectedTools]
        }));
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.mcpServerLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  public doTriggerSaveSkill(e): void {
    this.doTriggerSave({
      data: e.data,
      successCb: () => {
        e.successCb?.();
        this.saveAgent.emit({});
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        e.finallyCb?.();
      }
    });
  }

  public doTriggerSaveScenes($event): void {
    this.doTriggerSave({
      data: $event.data,
      successCb: () => {
        $event.successCb?.();
        this.saveAgent.emit({});
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        $event.finallyCb?.();
      }
    });
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

  private async getTimbreList() {
    if (!this.voiceEnable) {
      return;
    }
    const { audio_chinese_timbre, audio_english_timbre } =
      this.configServ.getConfigs();
    this.timbreList = [
      ...audio_chinese_timbre?.map((item) => {
        return {
          ...item,
          language: "chinese"
        };
      }),
      ...audio_english_timbre?.map((item) => {
        return {
          ...item,
          language: "english"
        };
      })
    ];
    this.agentDataServe
      .voiceConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((config) => {
        if (!config) {
          return;
        }
        const { language, timbre, domain } = config;
        if (!timbre && this.timbreList.length) {
          setTimeout(() => {
            this.saveVoiceConfig(this.timbreList[0]);
          }, 3000);
          return;
        }
        const property = `${language}_${timbre}_${domain}`;
        const { name, type, scene } =
        this.timbreList.find((item) => item.property === property) || {};
        if (!name && this.timbreList.length) {
          setTimeout(() => {
            this.saveVoiceConfig(this.timbreList[0]);
          }, 3000);
          return;
        }
        this.voiceConfig = {
          ...this.voiceConfig,
          ...config,
          name,
          type,
          scene
        };
      });
  }

  private saveVoiceConfig(data: ITimbreOption) {
    const { language, property } = data;
    if (!property) {
      return;
    }
    const [, timbre, domain] = property.split("_");
    const voice_interaction = {
      language: language,
      timbre,
      domain
    };
    this.doTriggerSave({
      data: {
        voice_interaction
      },
      successCb: () => this.agentDataServe.setVoiceConfig(voice_interaction)
    });
  }

  public voiceTipTrigger(e?: Event) {
    if (this.isFlowReadonly) {
      return;
    }
    e?.stopPropagation();
    this.showVoiceTip ? this.voiceTip.hide() : this.voiceTip.show();
    this.showVoiceTip = !this.showVoiceTip;
  }

  public onTimbreSelect(data: ITimbreOption) {
    this.saveVoiceConfig(data);
    this.voiceTipTrigger();
  }

  public onAudition(e: Event, item) {
    e.stopPropagation();
    const { property, name, scene, language } = item;

    // 不用国际化
    const text =
      language === "chinese"
        ? `我是${name}，适用于${scene}`
        : "Welcome to openJiuwen , a one-stop development platform for big models. Here, you can develop models and Agent applications without any barriers";
    this.ttsPlayerServe.play(text, {
      property
    });
  }

  @HostListener("window:resize", ["$event"])
  onResize() {
    this.showAutoGenerateTip = false;
    this.showAutoGeneQuestionTip = false;
  }

  @HostListener("document:click", ["$event"])
  public onClick(event: MouseEvent): void {
    const targetElement = event.target as HTMLElement;
    const autoGeneModalClassNames = autoGenerateTipInsideList;
    const prologueClassNames = prologueBtnClassList;
    if (this.commonLogic.hasTargetClass(targetElement, questionsBtnClassList)) {
      this.hideAutoGenerateTip();
      return;
    }
    if (this.commonLogic.hasTargetClass(targetElement, prologueClassNames)) {
      this.hideAutoGeneQuestionTip();
      return;
    }
    if (this.commonLogic.hasTargetClass(targetElement, autoGeneModalClassNames))
      return;
    this.hideAutoGenerateTip();
    this.hideAutoGeneQuestionTip();
  }

  /**
   * 切换浏览器页签时，tiny tip会自动关闭，但没有修改 this.show 值
   * 规避先去别的页签，再切回来，要点击两次示例按钮，才能展示tip的问题
   */
  @HostListener("window:visibilitychange", ["$event"])
  onVisibilityChange() {
    if (document.hidden) {
      this.showAutoGenerateTip = false;
      this.showAutoGeneQuestionTip = false;
    }
  }

  /** 当MCP创建任务提交后，需要把信息继续往父元素上升 **/
  public createMcpResEmit(event: any) {
    this.createMcpRes.emit(event);
  }

  /** 父组件中调用子组件的方法 **/
  public parentUpdateMcpData(addedMcpData: any) {
    const ids = Array.from(this.mcpServersAdded.list, item => item.id);
    if (ids.indexOf(addedMcpData.id) === -1) {
      this.triggerSaveMCPs([...this.mcpServersAdded.list, addedMcpData], true);
    } else {
      this.triggerSaveMCPs(this.mcpServersAdded.list, true);
    }
  }

  public addAgent(info) {
    const modalRef = this.nzModal.create({
      nzTitle: null,
      nzFooter: null,
      nzContent: UpdateNodeModalComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzWidth: 700,
      nzData: {
        title: this.i18n.transform("configtoolscomponent_45"),
        context: this.i18n.transform("addplugincomponent_12")
      }
    });
    modalRef.afterClose.subscribe((result) => {
      if (!result) return;
      const item: any = { ...info, workflow_id: info.id };
      this.flowAdded.list.push(item);
      this.confirmSaveFlows = [...this.flowAdded.list];
      this.triggerSaveFlows(this.confirmSaveFlows, true, this.i18n.transform("addplugincomponent_10"));
    });

  }

  createWorkflow(halfmodal: NzDrawerRef) {
    this.router.navigate(["/home/agent-center/create"], {
      queryParams: {
        from: "edit-flow",
        agentId: this.agentId
      }
    });
  }

  showKBSelectorHalfModal(event) {
    event?.stopPropagation();
    if (this.isFlowReadonly || this.kbAbilitiesService.isResourceDisabled) {
      return;
    }
    const drawerRef = this.drawerServ.create({
      nzContent: KnowledgeBaseSelectorComponent,
      nzPlacement: 'right',
      nzWidth: '700px',
      nzClosable: true,
      nzMaskClosable: true,
      nzKeyboard: true,
      nzData: {
        existedKbs: this.knowledgeAdded.list.map(kb => this.kbAbilitiesService.getKbId(kb)),
      },
    });
    drawerRef.afterOpen.subscribe(() => {
      const comp = drawerRef.getContentComponent();
      if (comp) {
        comp.createKB.subscribe(() => {
          drawerRef.close();
          this.kbCreation.createKb();
        });
        comp.addKB.subscribe(() => {
          const selectedKbIds = drawerRef.getContentComponent()?.selectedIds ?? [];
          const selectedKbs = drawerRef.getContentComponent()?.selectedKbs ?? [];
          this.knowledgeAdded.isLoading = true;
          const data = {
            knowledge_repos: selectedKbIds,
          };
          this.updateKBConfig(data, selectedKbs);
        });
      }
    });
  }

  confirmAddKb(kbDetail: Record<string, any>) {
    if (this.knowledgeAdded.list.length === this.kbLimit) {
      this.messageServ.error(this.i18n.transform("add_limit_error"));
      return;
    }
    if (this.knowledgeAdded.list.find(kb => this.kbAbilitiesService.getKbId(kb) === this.kbAbilitiesService.getKbId(kbDetail))) {
      this.messageServ.error(this.i18n.transform("add_due_error"));
      return;
    }

    const presentKb = this.knowledgeAdded.list[0];
    if (presentKb) {
      if (this.kbAbilitiesService.getConnectionId(kbDetail) !== this.kbAbilitiesService.getConnectionId(presentKb)) {
        this.messageServ.error(this.i18n.transform("add_diff_source_error"));
        return;
      }
    }

    const selectedKbIds = [...this.knowledgeAdded.list.map(kb => this.kbAbilitiesService.getKbId(kb)), this.kbAbilitiesService.getKbId(kbDetail)];
    const selectedKbs = [...this.knowledgeAdded.list, kbDetail];
    this.knowledgeAdded.isLoading = true;
    const data = {
      knowledge_repos: selectedKbIds
    };
    this.updateKBConfig(data, selectedKbs);
  }

  private updateKBConfig(data: { knowledge_repos: string[] }, selectedKbs: Record<string, any>[]) {
    this.doTriggerSave({
      data,
      successCb: () => {
        // 在添加知识库的抽屉里，点击确定，数据库保存成功后，同步刷新service的值
        this.agentDataServe.setKnowledges(selectedKbs);
        this.agentDataServe.setPluginAndFlowList({
          kbs: selectedKbs
        });
        this.messageServ.success(
          this.i18n.transform("successfully_update_knowledge"),
          { nzDuration: 3000 }
        );
        this.knowledgeAdded.list = selectedKbs;
        this.cdr.markForCheck();
      },
      finallyCb: () => {
        this.knowledgeAdded.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  protected readonly knowledgeBaseStatusMap = knowledgeBaseStatusMap;

  public handleClickAddAuthConfig(e) {
    e.plugin_id = e.tool_id.slice(0, e.tool_id.indexOf("#"));
    const modalRef = this.nzModal.create({
      nzTitle: null,
      nzFooter: null,
      nzContent: AddPluginAuthComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzWidth: this.halfModalWidth,
    });
    modalRef.componentInstance.pluginInfo = e;
    modalRef.afterClose.subscribe(() => {
      this.saveAgent.emit({});
    });
  }

  onConfirmPluginUpdate(pluginItem) {
    this.nzModal.warning({
      nzTitle: this.i18n.transform("update_flow_modal_title"),
      nzContent: this.i18n.transform("update_flow_modal_content", {
        versionName: pluginItem.resource_version_name,
        latestVersionName:
        pluginItem?.app_last_version_obj.resource_latest_version_name
      }),
      nzOnOk: () => {
        const id = pluginItem.tool_id?.split("#")?.[0] ?? "";
        const list = this.pluginAdded.list.map((item) => {
          if (item.tool_id.startsWith(`${id}#`)) {
            item.resource_version =
              pluginItem.app_last_version_obj.resource_latest_version;
            item.resource_version_name =
              pluginItem.app_last_version_obj.resource_latest_version_name;
          }
          return item;
        });
        this.triggerSavePlugins(list, true);
      }
    });
  }

  generateUpdateFlowsV(flowItem) {
    this.nzModal.info({
      nzTitle: this.i18n.transform("update_flow_modal_title"),
      nzContent: this.i18n.transform("update_flow_modal_content", {
        versionName: flowItem.resource_version_name,
        latestVersionName: flowItem?.app_last_version_obj.resource_latest_version_name
      }),
      nzOnOk: () => {
        const list = this.flowAdded?.list.map(item => {
          if (item.workflow_id === flowItem.workflow_id) {
            item.resource_version =
              flowItem.app_last_version_obj.resource_latest_version;
            item.resource_version_name =
              flowItem.app_last_version_obj.resource_latest_version_name;
          }
          return item;
        });
        this.triggerSaveFlows(list, true, this.i18n.transform("successfully_update_workflow"));
      }
    });
  }

  /** 开启引用配置 **/
  public enableAgentReference() {
    this.updateAgentReference();
  }

  /** 选择引用模式 **/
  public handleClickSelectReferenceMode(type: string) {
    this.referenceConfig.enabled = true;
    this.referenceConfig.json_formate = type !== "text";
    this.updateAgentReference();
  }

  /** 调用接口保存引用配置 */
  public updateAgentReference() {
    const data = {
      reference: {
        switch: this.referenceConfig.enabled,
        json_format: this.referenceConfig.json_formate
      }
    };
    this.doTriggerSave({
      data
    });
  }

  public changeCollapsedPrologue(configInfo: any) {
    const collapsed = configInfo.collapsed;
    configInfo.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  public prologueInfo = {
    collapsed: true, // 默认就是收起状态
    name: "", // 智能生成开场白的接口，需要传递应用name和description
    description: "",
    isAutoLoading: false
  };

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return "800px";
    } else {
      return "600px";
    }
  }

  triggerModel(event, type) {
    if (type === "question") {
      this.modelConfigTipService.useModelMode = "question";
    } else if (type === "one") {
      this.modelConfigTipService.useModelMode = "one";
    } else if (type === "plan") {
      this.modelConfigTipService.useModelMode = "plan";
    }
    this.modelTrigger.emit(event);
  }

  public changeModelSelected(item) {
    if (item && item.modelInfo) {
      // 更新 modelSelected
      this.modelSelectedId = item.modelInfo.id || item.modelInfo.model_deployment_id;
    }
    this.saveConfig();
  }

  private saveConfig(): void {
    let data: any = {};
    const modelConfigSelected = this.availableModels.find(
      (item) => item.model_deployment_id === this.modelSelectedId
    );
    if (!modelConfigSelected || !this.modelSelectedId) {
      return;
    }
    const { model_name, model_version, model_type, model, service_name, type } = modelConfigSelected;
    data = {
      model_name,
      model_deployment_id: this.modelSelectedId,
      model_version,
      model_type,
      model,
      service_name,
      plan_qa_independent: false // 合一模式
    };
    if (type === "router") {
      data.strategy_flag = true;
    }
    this.doTriggerSave({
      data,
      successCb: () => {
        // 保存成功后触发页面更新
        this.agentDataServe.setPromptAndModelConfig({
          modelConfig: {
            model_deployment_id: data.model_deployment_id,
            model_type: data.model_type,
            model_name: data.model_name,
            service_name: data.service_name,
            enable_thinking: data.model_config?.enable_thinking
          }
        });
      }
    });
  }

  get getInputParams() {
    const result = [];
    let filterData = this.pluginAdded.list.filter(item => item.hover);
    if (this.selectedPluginId && filterData.length <= 0) {
      for (let index = 0; index < this.pluginAdded.list.length; index++) {
        if (this.pluginAdded.list[index].tool_id === this.selectedPluginId) {
          this.pluginAdded.list[index].hover = true;
          filterData = [this.pluginAdded.list[index]];
        }
      }
      return filterData;
    }
    if (filterData.length <= 0) {
      return [];
    }

    this.selectedPluginId = filterData[0].tool_id;
    for (let index = 0; index < filterData.length; index++) {
      if (filterData[index].tool_parameter) {
        const params = JSON.parse(filterData[index].tool_parameter);
        for (let i = 0; i < params.length; i++) {
          result.push(params[i]);
        }
      }
    }
    return result;
  }

  public getParamsType(data: string): string {
    if (!data) {
      return "";
    }
    if (data === "ref" || data === "input_ref") {
      return "reference";
    }
    return "";
  }

  // 当yoghurt移入弹框的时候
  public showInputParamsHoverEnterTip() {
    for (let index = 0; index < this.pluginAdded.list.length; index++) {
      if (this.pluginAdded.list[index].tool_id === this.selectedPluginId) {
        this.pluginAdded.list[index].hover = true;
      }
    }
  }

  // 当用户移出弹框的时候
  public showInputParamsHoverLeaveTip() {
    for (let index = 0; index < this.pluginAdded.list.length; index++) {
      if (this.pluginAdded.list[index].tool_id === this.selectedPluginId) {
        this.pluginAdded.list[index].hover = false;
      }
    }
    this.selectedPluginId = "";
  }

  // 获取默认值
  public getDefaultValue(value) {
    if (value?.type === "literal") {
      return value?.content || "--";
    }
    if (value?.type === "ref" && value?.content[0]?.variable_key) {
      return value?.content[0].variable_key + " " + value?.content[0].default_value;
    }
    if (value?.type === "input_ref" && value?.content[0]?.variable_key && value?.content[0].default_value) {
      return value?.content[0].variable_key + " " + value?.content[0].default_value;
    }
    return "--";
  }

  public memoryLibSelectChange(changeData: IMemoryLibSelectData) {
    const { reason, halfModalRef, data } = changeData;
    if (reason) {
      this.memoryLibData.isLoading = true;
      const memoryLib = data[0];
      const updatedData = memoryLib ? {
        memory_repo_id: memoryLib?.memory_repo_id,
        name: memoryLib.name,
        description: memoryLib.description
      } : { memory_repo_id: "" };
      halfModalRef?.destroy?.(reason);
      this.doTriggerSave({
        data: {
          memory_config: updatedData
        },
        successCb: () => {
          this.messageServ.success(
            this.i18n.transform("agent.update.tip.updateSelectedMemoryLib"),
            { nzDuration: 3000 }
          );
          this.memoryLibData.list = data;
          this.cdr.markForCheck();
        },
        finallyCb: () => {
          this.memoryLibData.isLoading = false;
          this.cdr.markForCheck();
        }
      });
    } else {
      halfModalRef?.destroy?.(reason);
    }
  }
}
