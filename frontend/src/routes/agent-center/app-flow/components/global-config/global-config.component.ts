import { TextFieldModule } from "@angular/cdk/text-field";
import {
  ChangeDetectorRef,
  Component, ElementRef,
  EventEmitter, HostListener,
  Input,
  OnInit,
  Output,
  TemplateRef,
  ViewChild
} from "@angular/core";
import { NgForm } from "@angular/forms";
import { I18nNamespace } from "@i18n";
import { MemoryLibSelector } from "@routes/memory-lib/components/memory-lib-selector/memory-lib-selector";
import { MemoryLibSelectorTipType } from "@routes/memory-lib/memory-lib-enums";
import { IMemoryLibSelectData } from "@routes/memory-lib/memory-lib-interfaces";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective
} from "@shared/directives/variable-name-validator.directive";
import { MODULES } from "@shared/modules";
import { cloneDeep } from "lodash";
import { Subscription, takeUntil } from "rxjs";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { AppFlowService } from "../../app-flow.service";
import type { IFlowConfigs, IModel, WorkFlowType } from "../../app-flow.types";
import {
  flowConfig,
  getInitOutputParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes
} from "../../flow.const";
import { NodeService } from "../../node.service";
import { IContentReview, IWFView, IWFViewParentType, IWorkflowField, IWorkflowFieldType } from "../../node.type";
import { AccBlockComponent } from "../acc-block/acc-block.component";
import { AddPropsIconComponent } from "../add-props-icon/add-props-icon.component";
import { ModalBaseComponent } from "../base/modal-base.component";
import { SetDefaultComponent } from "../set-default/set-default.component";
import { NodeUtils } from "../utils";
import {
  AgentConfigService,
  ITimbreOption
} from "@routes/agent-center/agent-config.service";
import { AuditConfigModalComponent } from "@routes/agent-center/app-agent/components/audit-config-modal/audit-config-modal.component";
import { TtsPlayerService } from "@services/tts-player.service";
import { LLMSelectComponent } from "@routes/agent-center/app-flow/components/llm-select/llm-select.component";
import { EnvManagementService } from "@routes/platform-management/environment-management/env-management.service";
import { EnvVariableComponent } from "@routes/platform-management/environment-management/env-variable/env-variable.component";
import {
  StartImportJsonModalComponent
} from "@routes/agent-center/app-flow/components/start-import-json-modal/start-import-json-modal.component";
import { CommonService } from "@services/common.service";
import { NzModalService } from "ng-zorro-antd/modal";
import { NzMessageService } from "ng-zorro-antd/message";
import { ClickOutsideDirective } from "@shared/directives/click-outside.directive";
import { NzTreeNodeOptions } from "ng-zorro-antd/tree";
import { startSchemaStrField } from '@routes/agent-center/app-plugin/utils';
import { ObjectTemplateComponent } from '@routes/object-manage/component/object-template/object-template.component';

const QUES_LIMIT = 3;

@Component({
  selector: "global-config-modal",
  templateUrl: "./global-config.component.html",
  styleUrls: ["./global-config.component.less"],
  standalone: true,
  imports: [
    MODULES,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    AccBlockComponent,
    AddPropsIconComponent,
    SetDefaultComponent,
    TextFieldModule,
    AuditConfigModalComponent,
    LLMSelectComponent,
    EnvVariableComponent,
    MemoryLibSelector,
    ClickOutsideDirective
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.MEMORY_LIB
      ]
    }
  ]
})
export class GlobalConfigComponent
  extends ModalBaseComponent
  implements OnInit {
  @Input() workflowType: WorkFlowType;

  @Input() flowId: string;

  @Input() configs: IFlowConfigs;

  @Output() configsChange = new EventEmitter<IFlowConfigs>();

  @Output() close = new EventEmitter<void>();

  @ViewChild('genPrologueTip') genPrologueTip: any;

  @ViewChild('autoGenePopover') autoGenePopover: any;

  @ViewChild('autoGenProloguePopover') autoGenProloguePopover: any;

  @ViewChild("genQuestionTip") genQuestionTip: any;

  @ViewChild("autoMemoForm") autoMemoForm: NgForm;

  @ViewChild("assignmentMemoForm") assignmentMemoForm: NgForm;

  @ViewChild("addMemoModal") addMemoModal: TemplateRef<HTMLDivElement>;

  @ViewChild(AuditConfigModalComponent) auditConfigModal: any;

  @Output() upDateEnv = new EventEmitter<any>();

  public changeUrl = cdnAssetUrl;

  public prologue = "";

  public questions: string[] = [];

  public isGenPrologueLoading = false;

  public isGenQuestionLoading = false;

  public showGenPrologueTip = false;

  public showAutoGeneQuestionTip = false;

  public longTermMemo = false;

  public voiceEnable = false;

  public timbreList = [];

  public voiceConfig = {
    language: "",
    timbre: "",
    name: "",
    type: "",
    scene: "",
    domain: ""
  };

  @ViewChild("voiceTip") voiceTip: any;

  public showVoiceTip = false;
  public voiceIcon = cdnAssetUrl("assets/agent-center/icons/voice.svg");
  public triggerAdded = {
    title: this.i18n.transform("trigger"),
    collapsed: false,
    list: [],
    imageClass: "common-img",
    isLoading: false
  };

  public modelListSubscription: Subscription;
  public modelOptions: IModel[] = [];
  public defaultModel = "";
  public modelSwitch = false;
  public autoMemos: IWorkflowField[] = [];
  public assignmentMemos: IWFView[] = [];
  public outputDataTypes = getOutputParamTypes();

  public noneObjDataTypes = getNoneObjOutputParamTypes();
  public isObjectLikeType = NodeUtils.isObjectLikeType;
  public isSimpleType = NodeUtils.isSimpleType;
  public ltmEnabled = false;
  public auditConfig: IContentReview = {
    enabled: false,
    filter: {
      keywords: ""
    },
    replace: [],
    reply: []
  };

  public securityConfig: boolean = false;

  override normalParamLableWidth = {
    name: "50%",
    type: "50%",
    desc: "152px"
  };

  override slimParamLableWidth = {
    name: "50%",
    type: "50%",
    desc: "86px"
  };

  public modelValidation: any = {
    errorMessage: {
      required: this.i18n.transform("select_model")
    },
    type: "changeAlert"
  };

  override getLayerIndexWidth(param: IWFView): string {
    return NodeUtils.getLayerIndexWidth(param, this.isNormalView, {
      widthArr: [185, 146]
    });
  }

  public envCfgOptions: any = [];
  public selectEnv = "";
  public showSafetyBarrier = false;
  public memoryLibData = {
    data: [],
    isLoading: false
  };
  public treeNodes: NzTreeNodeOptions[] = [];

  protected isHCS = false;
  public showSettingContentReview = false;
  public followupPlaceholder = `- ${this.i18n.transform(
    "followup_tip1"
  )}\n- ${this.i18n.transform("followup_tip_2")}\n- ${this.i18n.transform(
    "followup_tip_3"
  )}\n- ${this.i18n.transform("followup_tip_4")}`;

  public probeConfig = {
    enabled: true,
    tip: "",
    disable: true,
    title: this.i18n.transform("probe"),
    closeDesc: this.i18n.transform("probe_close_desc"),
    openDesc: this.i18n.transform("probe_open_desc"),
    followUpPrompt: this.i18n.transform("follow_up_prompt"),
    promptDescTip: this.i18n.transform("promptDescTip"),
    probeInputed: this.followupPlaceholder
  };


  protected readonly memoryLibSelectorTipType = MemoryLibSelectorTipType;

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private flowRepo: AppFlowRepoService,
    private nzModal: NzModalService,
    public i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    public configServ: AgentConfigService,
    private ttsPlayerServe: TtsPlayerService,
    private nzMessage: NzMessageService,
    private environmentManagementService: EnvManagementService,
    private el: ElementRef,
    private commonService: CommonService
  ) {
    super(nodeServ, appFlowServ);
    this.voiceEnable = this.configServ.voiceEnable();
  }

  override ngOnInit() {
    super.ngOnInit();

    if (!this.configs) {
      this.configs = flowConfig;
    }
    this.getTimbreList();
    this.getInitEnvOptions();
    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(models => {
        this.modelOptions = models ?? [];
      });
    this.defaultModel = this.configs?.default_model?.model_deployment_id ?? "";
    NodeUtils.checkModelExistence(
      this.i18n.transform("global_configuration"),
      this.configs?.default_model?.model_deployment_id ?? "",
      this.modelOptions
    );
    this.modelSwitch = this.configs?.default_model_switch;
    this.selectEnv = this.configs?.environment || "";

    this.questions = cloneDeep(this.configs?.suggest_queries) ?? [];
    if (this.questions.length < QUES_LIMIT) {
      this.questions.push("");
    }
    this.triggerAdded.list = this.configs?.trigger_list ?? [];
    this.prologue = this.configs?.prologue ?? "";
    this.longTermMemo = this.configs?.long_memory_enabled;
    if (this.configs?.content_review) {
      const { enabled, filter, replace, reply } = this.configs?.content_review;
      setTimeout(() => {
        this.auditConfig = {
          enabled: enabled ?? false,
          filter: {
            keywords: filter?.keywords ?? ""
          },
          replace: replace ?? [],
          reply: reply ?? []
        };
        this.setShowSettingContentReview();
      }, 0);
    }
    this.securityConfig = !!this.configs?.safety_barrier;
    this.autoMemos = cloneDeep(
      (this.configs?.memory || [])?.filter(
        (val) => val.storage_method === "auto"
      )
    );

    this.assignmentMemos = NodeUtils.fields2Views(
      (this.configs?.memory || [])?.filter(
        (val) => val.storage_method === "assignment"
      )
    );
    this.treeNodes = this.convertToTreeNodes(this.assignmentMemos);

    this.showSafetyBarrier =
      !!this.configServ.getConfigs()?.safety_barrier_display;

    this.memoryLibData.data = [this.configs.memory_config].filter(Boolean);
    this.probeConfig.enabled = this.configs.additional_questions_config?.enable ?? false;
    this.probeConfig.probeInputed = this.configs.additional_questions_config?.prompt || this.followupPlaceholder;
    this.resetProbeDisable();
  }

  getInitEnvOptions() {
    this.envCfgOptions = [];

    this.environmentManagementService
      .getEnvironmentList({
        offset: 0,
        limit: 99
      })
      .then((res) => {
        const selectEnv = res.env_info?.find((item) => item.id === this.selectEnv);
        if (!selectEnv && this.selectEnv) {
          this.selectEnv = "";
        }
        this.envCfgOptions = res?.env_info?.map((item) => {
          item.disabled = item.status !== "READY";
          return item;
        });
      });
  }

  private getTimbreList() {
    if (!this.voiceEnable) {
      return;
    }
    const { audio_chinese_timbre, audio_english_timbre } =
      this.configServ.getConfigs();
    if (!audio_chinese_timbre || !audio_english_timbre) {
      return;
    }
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
    const config = this.configs?.voice_interaction;
    const { language, timbre, domain } = config || {};
    if (!timbre && this.timbreList.length) {
      this.saveVoiceConfig(this.timbreList[0]);
      return;
    }
    const property = `${language}_${timbre}_${domain}`;
    const { name, type, scene } =
    this.timbreList.find((item) => item.property === property) || {};
    if (!name && this.timbreList.length) {
      this.saveVoiceConfig(this.timbreList[0]);
      return;
    }
    this.voiceConfig = {
      ...this.voiceConfig,
      ...config,
      name,
      type,
      scene
    };
  }

  private saveVoiceConfig(data: ITimbreOption) {
    const { language, property, name, type, scene } = data;
    if (!property) {
      return;
    }
    const [, timbre, domain] = property.split("_");
    const voice_interaction = {
      language,
      timbre,
      domain
    };
    this.voiceConfig = {
      ...this.voiceConfig,
      ...voice_interaction,
      name,
      type,
      scene
    };
  }

  public onAudition(e: Event, item) {
    e.stopPropagation();
    const { property, name, scene, language } = item;

    // 不用国际化
    const text =
      language === "chinese"
        ? this.i18n.transform("configtoolscomponent_51", { name: name, scene: scene })
        : "Welcome to Jiuwen, a one-stop development platform for big models. Here, you can develop models and Agent applications without any barriers";
    this.ttsPlayerServe.play(text, {
      property
    });
  }

  public voiceTipTrigger(e?: Event) {
    e?.stopPropagation();
    this.showVoiceTip = !this.showVoiceTip;
  }

  public onTimbreSelect(data: ITimbreOption) {
    this.saveVoiceConfig(data);
    this.voiceTipTrigger();
  }

  getmodelStatus(is_connecting) {
    if (is_connecting) {
      return this.i18n.transform("running");
    }

    return this.i18n.transform("call_failed");
  }

  public prologueAlterModal = {
    title: this.i18n.transform("replace_prologue"),
    description: this.i18n.transform("replace_prologue_description"),
    dismissTip: () => {
      this.hideGenPrologueTip();
    },
    confirmBtn: () => {
      this.confirmGenPrologue();
    }
  };

  public questionsAlterModal = {
    title: this.i18n.transform("replace_recommended_questions"),
    description: this.i18n.transform(
      "replace_recommended_questions_description"
    ),
    dismissTip: () => {
      this.hideGenQuestionTip();
    },
    confirmBtn: () => {
      this.confirmGenQuestions();
    }
  };

  private hideGenPrologueTip(): void {
    this.showGenPrologueTip = false;
  }

  private hideGenQuestionTip(): void {
    this.showAutoGeneQuestionTip = false;
  }

  public addChild(param: NzTreeNodeOptions) {
    const child = {
      ...getInitOutputParamConfig(),
      depth: param.depth + 1,
      parentType: param.type,
      aging_level: param.aging_level,
      storage_method: "assignment",
      source: "pre_defined",
      key: param.key + "-" + Date.now(),
      title: "",
      type: "string",
      isLeaf: true,
      desc: ""
    };
    if (param?.children) {
      param.children = [...param.children, child];
    } else {
      param.children = [child];
    }
    param.isLeaf = false;
    param.expanded = true;
    this.treeNodes = [...this.treeNodes];
    this.cdr.detectChanges();
  }

  private changeChildLevel(
    children: IWFView[],
    level: "session" | "permanent"
  ) {
    children.forEach((child) => {
      child.aging_level = level;

      if (child?.children) {
        this.changeChildLevel(child.children, level);
      }
    });
  }

  public onRootLevelChange(param: IWFView) {
    if (param?.children) {
      this.changeChildLevel(param.children, param.aging_level);
    }
  }

  onOutputParamTypeChange(param: NzTreeNodeOptions) {
    param.value.default = "";
    if (this.isSimpleType(param.type) && param?.children) {
      delete param?.children;
      param.isLeaf = true;
      return;
    }

    if (
      param.type.startsWith("array") &&
      param.type !== "array<object>" &&
      param?.children
    ) {
      delete param?.children;
      param.isLeaf = true;
    }

    if (this.isObjectLikeType(param.type)) {
      param.isLeaf = false;
      const children = param?.children;
      if (!children || (Array.isArray(children) && children.length === 0)) {
        this.addChild(param);
      }
    }
  }

  public handleGenPrologueTip() {
    if (!this.modelOptions.length) {
      return;
    }

    this.showGenPrologueTip = true;
  }

  public handleAutoGeneQuestionTip() {
    if (!this.modelOptions.length) {
      return;
    }
  }

  public tooltipClose = () => {
    this.showGenPrologueTip = false;
    this.showAutoGeneQuestionTip = false;
    this.autoGenePopover?.hide();
    this.autoGenProloguePopover?.hide();
  };

  public async confirmGenPrologue() {
    if (!this.modelOptions.length) {
      return;
    }

    this.hideGenPrologueTip();
    this.isGenPrologueLoading = true;

    try {
      const { prologue } = await this.flowRepo.generatePrologue(this.flowId);
      this.prologue = prologue;
    } finally {
      this.isGenPrologueLoading = false;
    }
  }

  public async confirmGenQuestions() {
    if (!this.modelOptions.length) {
      return;
    }

    this.hideGenQuestionTip();
    this.isGenQuestionLoading = true;

    try {
      const { questions } = await this.flowRepo.generateQuestions(this.flowId);
      this.questions = questions;
    } finally {
      this.isGenQuestionLoading = false;
    }
  }

  deleteQuestion(index: number) {
    if (index === this.questions.length - 1) {
      this.questions[index] = "";
    } else {
      this.questions.splice(index, 1);

      if (this.questions[this.questions.length - 1]) {
        this.questions.push("");
      }
    }
  }

  addMemo() {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform("add_memory_variables"),
      nzContent: this.i18n.transform("delete_variables_tip"),
      nzOkText: this.i18n.transform("ok"),
      nzCancelText: this.i18n.transform("cancel")
    });
  }

  addAutoMemo() {
    this.autoMemos.push({
      description: "",
      name: "",
      required: true,
      aging_level: "permanent",
      storage_method: "auto",
      source: "pre_defined",
      type: "string",
      value: {
        content: null,
        default: "",
        hint: "",
        type: "generated"
      }
    });
  }

  addAutoTriggers() {
    this.autoMemos.push({
      description: "",
      name: "",
      required: true,
      aging_level: "permanent",
      storage_method: "auto",
      source: "pre_defined",
      type: "string",
      value: {
        content: null,
        default: "",
        hint: "",
        type: "generated"
      }
    });
  }

  public showDelete(param: NzTreeNodeOptions) {
    if (param.source === "system") {
      return false;
    }

    if (param.depth > 0) {
      const parentNode = this.findParentNode(this.treeNodes, param);
      if (parentNode && parentNode.children.length === 1) {
        return false;
      }
    }

    return true;
  }

  private findParentNode(nodes: NzTreeNodeOptions[], target: NzTreeNodeOptions): NzTreeNodeOptions | null {
    for (const node of nodes) {
      if (node.children) {
        const found = node.children.find(child => child === target);
        if (found) {
          return node;
        }
        const parent = this.findParentNode(node.children, target);
        if (parent) {
          return parent;
        }
      }
    }
    return null;
  }

  public onQuesInput(index: number) {
    if (index < QUES_LIMIT - 1 && index === this.questions.length - 1) {
      this.questions.push("");
    }
  }

  public onQuesBlur(index: number) {
    if (!this.questions[index] && index !== this.questions.length - 1) {
      this.questions.splice(index, 1);

      if (this.questions[this.questions.length - 1]) {
        this.questions.push("");
      }
    }
  }

  public onDeleteMemoVar(index: number): void {
    this.autoMemos.splice(index, 1);
  }

  public onDeleteOutput(param: NzTreeNodeOptions) {
    this.removeNode(this.treeNodes, param);

    const parentNodeParam = this.findParentNode(
      this.treeNodes,
      param
    );
    if (
      this.isObjectLikeType(parentNodeParam?.type) &&
      parentNodeParam?.children?.length === 0
    ) {
      delete parentNodeParam.children;
      parentNodeParam.isLeaf = true;
    }
    this.assignmentMemos = this.convertToAssignMemos(this.treeNodes);
    this.treeNodes = [...this.treeNodes];
    this.cdr.detectChanges();
  }

  private removeNode(nodes: NzTreeNodeOptions[], target: NzTreeNodeOptions): boolean {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) {
        nodes.splice(i, 1);
        return true;
      }
      if (nodes[i].children) {
        const found = this.removeNode(nodes[i].children, target);
        if (found) {
          return true;
        }
      }
    }
    return false;
  }

  public addAssignmentMemos() {
    const child = {
      ...getInitOutputParamConfig(),
      title: "",
      key: this.treeNodes.length + "-",
      depth: 0,
      source: "pre_defined",
      aging_level: "session",
      storage_method: "assignment",
      parentType: "none",
      type: "string",
      desc: ""
    };
    this.treeNodes = [...this.treeNodes, child];
    this.cdr.detectChanges();
  }

  private convertToTreeNodes(nodes: IWFView[]): any[] {
    return nodes.map((node, index) => ({
      title: node.name,
      key: `${index}-${node.name}`,
      depth: node.depth,
      source: node.source,
      type: node.type,
      name: node.name,
      children: node.children ? this.convertToTreeNodes(node.children) : [],
      expanded: node.expanded,
      aging_level: node.aging_level,
      storage_method: node.storage_method,
      value: node.value,
      required: node.required,
      description: node.description,
      parentType: node.parentType,
      isDisabled: node.isDisabled
    }));
  }

  private convertToAssignMemos(nodes: NzTreeNodeOptions[]): any[] {
    return nodes.map((node, index) => ({
      title: node.name,
      key: `${index}-${node.name}`,
      depth: node.depth,
      source: node.source,
      type: node.type,
      name: node.name,
      children: node.children ? this.convertToAssignMemos(node.children) : [],
      expanded: node.expanded,
      aging_level: node.aging_level,
      storage_method: node.storage_method,
      value: node.value,
      required: node.required,
      description: node.description,
      parentType: node.parentType,
      isDisabled: node.isDisabled
    }));
  }

  public onSaveAuditConfig(param) {
    this.auditConfig = cloneDeep(param);
    this.setShowSettingContentReview();
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

  public openAuditHalfModal() {
    this.auditConfigModal.open();
  }

  public onSwitchChange($event: boolean) {
    this.auditConfig.enabled = $event;
    this.setShowSettingContentReview();
  }

  public securitySwitchChange($event: boolean) {
    this.securityConfig = $event;
    this.setShowSettingContentReview();
  }

  getAutoNames(index: number): {
    existingValues: string[];
  } {
    const names = this.autoMemos
      .map((p) => p.name)
      .concat(this.assignmentMemos.map((a) => a.name));
    names.splice(index, 1);
    return { existingValues: names };
  }

  getAssignmentNames(param: NzTreeNodeOptions): {
    existingValues: string[];
  } {
    let names = [];
    if (param.depth === 0) {
      names = this.treeNodes
        .map((arg) => arg.name)
        .concat(this.autoMemos.map((a) => a.name));
    } else {
      const parentNode = this.findParentNode(this.treeNodes, param);
      names = parentNode?.children.map((arg) => arg.name);
    }

    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  onNameChange() {
  }

  onConfirm(): void {
    this.assignmentMemos = this.convertToAssignMemos(this.treeNodes);
    const newConf: IFlowConfigs = cloneDeep(this.configs);
    newConf.environment = this.selectEnv || "";
    newConf.trigger_list = this.triggerAdded.list;
    newConf.prologue = this.prologue;
    newConf.suggest_queries = this.questions.filter((question) => question);
    newConf.default_model_switch = this.modelSwitch;
    newConf.long_memory_enabled = this.longTermMemo;
    newConf.memory = [
      ...NodeUtils.getDtoInputs(this.autoMemos),
      ...NodeUtils.views2Fields(this.assignmentMemos)
    ];
    newConf.content_review = this.auditConfig;
    newConf.safety_barrier = this.securityConfig;
    if (this.voiceEnable) {
      newConf.voice_interaction = {
        language: this.voiceConfig.language,
        timbre: this.voiceConfig.timbre,
        domain: this.voiceConfig.domain
      };
    }
    const choosenModel = this.modelOptions.find(
      (m) => m.model_deployment_id === this.defaultModel
    );
    if (choosenModel) {
      const { model_deployment_id, model_name, model_type, model, type } =
        choosenModel;
      newConf.default_model = {
        model_deployment_id,
        model_name,
        model_type: type === "router" ? "strategy" : model_type,
        model
      };
    } else {
      newConf.default_model = null;
    }
    if (this.configServ.isSupportUserPersona()) {
      newConf.memory_config = this.memoryLibData.data[0] ?? null;
    }
    newConf.additional_questions_config = {
      enable: this.probeConfig.enabled,
      prompt: this.probeConfig.enabled || this.probeConfig.probeInputed !== this.followupPlaceholder ? this.probeConfig.probeInputed : ""
    };
    this.configsChange.emit(newConf);
  }

  resetEnvList(e) {
    this.upDateEnv.emit(e);
  }

  updateModel(e) {
    this.defaultModel = e.id;
    this.resetProbeDisable();
  }

  updateModelOptions(options: any[]): void {
    const modelArr = options.flatMap(option => option.children);
    if (!modelArr.find(model => model.id === this.defaultModel)) {
      this.defaultModel = "";
      this.resetProbeDisable();
    }
  }

  dismiss(): void {
    this.close.emit();
  }

  trackByFn(index: number) {
    return index;
  }

  public showCard = false;

  importJson() {
    const modalRef = this.nzModal.create({
      nzTitle: this.i18n.transform("import_json"),
      nzContent: StartImportJsonModalComponent,
      nzClassName: "import-json-modal",
      nzFooter: null
    });
    const modalInstace=modalRef.componentInstance;
    modalInstace.cancel.subscribe(()=>{
      modalRef.close();
    })
    modalInstace.confirm.subscribe(data => {
      const req = startSchemaStrField(JSON.stringify(data));
      this.assignmentMemos = this.fields2Views(req);
      this.treeNodes=this.convertToTreeNodes(this.assignmentMemos);
      this.cdr.detectChanges();
      modalRef.close();
    })
  }

  chooseTemplate() {
    const modalRef = this.nzModal.create<ObjectTemplateComponent>({
      nzContent: ObjectTemplateComponent,
      nzWidth: 900,
      nzClosable: true,
      nzClassName: 'modal-custom900-class',
      nzFooter: null,
      nzTitle: this.i18n.transform('object_template'),
      nzData: {
        templatesSelected: (data) => {
          this.assignmentMemos = [...this.assignmentMemos, ...this.fields2Views(data)];
          this.treeNodes = this.convertToTreeNodes(this.assignmentMemos);
          this.cdr.detectChanges();
          modalRef.close();
        },
      },
    });
  }

  fields2Views(
    fields: IWorkflowField[],
    depth = 0,
    parentType: IWFViewParentType = "none"
  ): IWFView[] {
    const views: IWFView[] = fields.map((field) => {
      const {
        name,
        type,
        description = "",
        required,
        schema,
        source = "pre_defined",
        value,
        isDisabled,
        aging_level = "session",
        storage_method = "assignment"
      } = field;

      const view: IWFView = {
        name,
        type,
        description,
        required,
        source,
        depth,
        parentType,
        value,
        isLeaf: true,
        ...(isDisabled !== undefined && { isDisabled })
      };

      if (aging_level && storage_method) {
        view.aging_level = aging_level;
        view.storage_method = storage_method;
      }

      if (type === "array") {
        if ((schema as IWorkflowField).type === "object") {
          view.type = "array<object>";
          view.isLeaf = false;
          view.children = this.fields2Views(
            ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
            depth + 1,
            view.type
          );
          view.expanded = true;
        } else {
          if ((schema as IWorkflowField).type) {
            view.type = `array<${
              (schema as IWorkflowField).type
            }>` as IWorkflowFieldType;
          } else if ((field?.schema as any)?.type) {
            view.type = `array<${
              (field?.schema as any)?.type
            }>` as IWorkflowFieldType;
          }
        }
      }

      if (type === "object") {
        view.isLeaf = false;
        view.children = this.fields2Views(
          (schema ?? []) as IWorkflowField[],
          depth + 1,
          view.type
        );
        view.expanded = true;
      }

      return view;
    });

    return views;
  }

  envSelect($event) {
    this.showCard = false;
  }

  ngModelChange($event) {
    this.showCard = false;
  }

  @HostListener("document:click", ["$event"])
  onDocumentClick(event: Event) {
    if (!this.showCard) return;

    const target = event.target as HTMLElement;
    const button = this.el.nativeElement.querySelector("button[nz-button]");
    const card = this.el.nativeElement.querySelector(".card");

    if (!(button?.contains(target) || card?.contains(target))) {
      this.showCard = false;
    }
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  private resetProbeDisable(): void {
    this.probeConfig.disable = !this.defaultModel || this.isFlowReadonly;
    this.probeConfig.enabled = this.probeConfig.disable ? false : this.probeConfig.enabled;
    this.probeConfig.tip = !this.defaultModel ? this.i18n.transform("probe_need_model_tip") : "";
  }

  public memoryLibSelectChange(changeData: IMemoryLibSelectData) {
    const { reason, halfModalRef, data } = changeData;

    const memoryLib = data[0];
    const updatedData = memoryLib ? {
      memory_repo_id: memoryLib?.memory_repo_id,
      name: memoryLib.name,
      description: memoryLib.description
    } : { memory_repo_id: "" };

    if (reason) {
      this.memoryLibData.data = [updatedData];
    }
    halfModalRef?.destroy?.(reason);
  }
}
