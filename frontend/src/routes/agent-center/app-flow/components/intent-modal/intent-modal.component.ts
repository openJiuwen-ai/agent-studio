import { Component, ElementRef, EventEmitter, HostListener, Input, OnDestroy, OnInit, Output, ChangeDetectorRef, ViewChild } from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzPopoverModule } from 'ng-zorro-antd/popover';
import { GETVARIANT_REG } from '@constants/exp-tmpl-config.const';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { KnowledgeCardUsed } from '@routes/agent-center/components/knowledge-card-used/knowledge-card-used.component';
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { ICallbackFn } from '@routes/agent-center/types/common.types';
import { IntentPackageService } from '@routes/intent-package/intent-package.service';
import { KnowledgeBaseCreationComponent } from '@routes/knowledge-center/components/knowledge-base-creation/knowledge-base-creation.component';
import { KnowledgeBaseSelectorComponent } from '@routes/knowledge-center/components/knowledge-base-selector/knowledge-base-selector.component';
import { TagRuleBuilderComponent } from '@routes/knowledge-center/components/tag-rule-builder/tag-rule-builder.component';
import { KBScope, TagRule } from '@routes/knowledge-center/knowledge.types';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { ITmpl } from '@services/prompt.service';
import { type IModelParam, modelSettingsComponent } from '@shared/components/model-settings-tip';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective, ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep, isObject, unionBy } from 'lodash';
import { BehaviorSubject, debounceTime, Subject, Subscription, takeUntil, fromEvent } from 'rxjs';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import type { IIntentGroupItem, IModel, INodeMeta, INodeOutput } from '../../app-flow.types';
import { LAZY_LOAD_LIMIT, NODE_SAVE_DEBOUNCE_TIME, WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IIntentBranch, IIntentGroupConfig, IIntentNode, IKbConf, IParamRef, IWorkflowField } from '../../node.type';
import { FlowUtils } from '../../utils/flow-utils';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { ReadonlyParamsTreeComponent } from '../readonly-params/readonly-params-tree.component';
import { IntentAddTipModalComponent } from '@routes/knowledge-center/components/intent-add-tip-modal/intent-add-tip-modall.component';
import { NodeUtils } from '../utils';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { CmdTextareaComponent } from '@routes/agent-center/app-flow/components/cmd-textarea/cmd-textarea.component';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import { AssetIntelligentAddDisabledComponent } from '@shared/components/assets/asset-intelligent-add-disabled/asset-intelligent-add-disabled.component';
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
import { SaveTmplLibraryModalComponent } from '@routes/prompt/prompt-candidate-template/save-tmpl-library-modal/save-tmpl-library-modal.component';
import moment from 'moment';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { NzDrawerService } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'meta-intent-modal',
  templateUrl: './intent-modal.component.html',
  styleUrls: ['./intent-modal.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    RefSelectedRequireDirective,
    ReadonlyParamsTreeComponent,
    KnowledgeCardUsed,
    LLMSelectComponent,
    KnowledgeBaseCreationComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    TagRuleBuilderComponent,
    InputTreeSelect,
    CmdTextareaComponent,
    NzPopoverModule,
    modelSettingsComponent,
    AssetIntelligentAddComponent,
    AssetIntelligentAddDisabledComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzModalService,
    NzMessageService,
  ],
})
export class IntentModalComponent extends ModalBaseComponent implements OnInit, OnDestroy {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IIntentNode;

  @Input('meta') meta: INodeMeta;

  @Input('nodeOutputs') nodeOutputs: INodeOutput[];

  @Output('confirm') confirm = new EventEmitter<IIntentNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('classForm') classForm: NgForm;

  @ViewChild('nameForm') nameForm: NgForm;

  @ViewChild('intentModalRef') intentModalRef!: ElementRef;

  @ViewChild('kbCreation') kbCreation: KnowledgeBaseCreationComponent;

  @ViewChild('select') intentSelectRef: any;

  @ViewChild('modelSettingsRef')
  modelSettingsRef: any;

  protected override destroy$ = new Subject<void>();

  // 两类模式标签
  public typeTabs = [];

  // 当前选中的模式
  public modeId: 'normal' | 'advanced' = 'advanced';

  public advancedModeTip = this.i18n.transform('advanced_mode_tip');

  public showModelSetRef = false;

  private storageSub?: Subscription;

  public modelParams: IModelParam = {
    top_p: 0.5,
    temperature: 0.5,
    history_size: 3,
    max_tokens: null,
    frequency_penalty: 0,
    enable_thinking: true,
  };

  public modelSetTipCtx = {
    param: this.modelParams,
    showThinkSwitch: false,
    selectedModel: {},
    isLlm: false,
    outputs: {
      updatedParam: ($event: IModelParam) => {
        this.modelParams = { ...$event };
        this.showModelSetRef = false;
        this.onSave();
      },
    },
  };

  public changeUrl = cdnAssetUrl;

  public intentImgUrl = WORKFLOW_SVGS.IntentDetection;

  public nameRefOptions: IParamRef[] = [];

  public modelListSubscription: Subscription;

  public inputParams: IWorkflowField[] = [];

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public modelOptions: any[] = [];

  public intentGroupOptions: any[] = [];

  get intentGroupSelectOptions() {
    return this.intentGroupOptions.map(item => ({
      label: item.merge_name,
      value: item.intent_id,
    }));
  }

  public classList: IIntentBranch[] = [];

  public otherClass: IIntentBranch = {
    id: 'branch_0',
    configs: {
      category: this.i18n.transform('uncertain_other_intentions'),
    },
  };

  public hasOtherClass = false;

  public modelFormGroup = this.fb.group({
    model: [''],
    prompt: [''],
    chat_history_max_turn: [0],
    enable_knowledge: [false],
    recall_threshold: [0.8],
    intent_group: [null as string | null],
    enableMemory: [false],
    tags: [],
  });

  public validationRules: any[] = [];

  public validation: any = {
    type: 'change',
  };

  intentValidation: any = {
    errorMessage: {
      required: this.i18n.transform('please_select_intent_package'),
    },
    type: 'changeAlert',
  };

  public modelValidation: any = {
    errorMessage: {
      required: this.i18n.transform('select_model'),
    },
    type: 'changeAlert',
  };

  public kbs: IKbConf[] = [];

  public icon = WORKFLOW_SVGS.KnowledgeRepo;

  public outputsParams = [];

  public get getChatHistoryMaxTurn() {
    return this.modelFormGroup.controls.chat_history_max_turn.value;
  }

  public set getChatHistoryMaxTurn(value: number) {
    this.modelFormGroup.controls.chat_history_max_turn.setValue(value);
  }

  public get getRecallThreshold() {
    return this.modelFormGroup.controls.recall_threshold.value;
  }

  public set getRecallThreshold(value: number) {
    this.modelFormGroup.controls.recall_threshold.setValue(value);
  }

  public hasParentNode = false;

  public site = this.configServ.getConfigs().site ?? '';

  public selectedModelSubscription: Subscription;

  private totalIntentGroups: number = 0;

  private paramsId: string;
  formCode$: Subscription;

  errorIntentMsg: string = '';

  tagRule: TagRule = {
    basic: null,
    advancedRules: null,
  };

  isFirstInit = 0;
  updateTimeout: any = null;

  constructor(
    private fb: FormBuilder,
    protected override appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private nzModal: NzModalService,
    protected override nodeServ: NodeService,
    private nzMessage: NzMessageService,
    public configServ: AgentConfigService,
    private intentRepoServe: IntentPackageService,
    protected agentDataServe: AgentDataService,
    private route: ActivatedRoute,
    public kbAbilitiesService: KbAbilitiesService,
    private knowledgeRepoService: KnowledgeRepoService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    private candidateTemplateListServe: CandidateTemplateListService,
    private cdr: ChangeDetectorRef,
    private drawerService: NzDrawerService
  ) {
    super(nodeServ, appFlowServ);
  }
  readonly showVarListSubject$ = new Subject<boolean>();
  public get thresholdLimit() {
    const { knowledge_recall_threshold_min, knowledge_recall_threshold_max } = this.configServ.getConfigs();
    return {
      min: knowledge_recall_threshold_min ?? 0,
      max: knowledge_recall_threshold_max ?? 1,
    };
  }

  public onModelSettingsUpdate(param: any) {
    this.modelParams = { ...param };
    this.showModelSetRef = false;
    this.onSave();
  }

  getmodelStatus(is_connecting) {
    if (is_connecting) {
      return this.i18n.transform('running');
    }

    return this.i18n.transform('call_failed');
  }

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  public override ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.paramsId = params.id;
    });
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.intentImgUrl = WORKFLOW_SVGS[this.nodeInfo.type];
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.hasParentNode = true;
      this.getLoopInnerNodeRefs(parentNode, {
        simpleArrRefFirst: true,
      }).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.hasParentNode = false;
      this.getSelfRefs({
        simpleArrRefFirst: true,
      }).subscribe(info => {
        this.onRefUpdate(info);
      });
    }

    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo.name));

    this.outputsParams = this.nodeInfo.outputs.filter(output => output.name === 'classification_id' || output.name === 'name');

    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(models => {
        if (models.length > 0) {
          this.modelOptions = models ?? [];
        }
      });

    // 查询意图包列表
    if (FlowUtils.isAdvancedModeNew(this.nodeInfo)) {
      this.getIntentSelectList();
    }

    this.classList = cloneDeep(this.nodeInfo.branches);
    if (this.classList.length > 0 && this.classList[0].id === 'branch_0') {
      this.classList.shift();
      this.hasOtherClass = true;
    }

    const { repos, common_tags = null, advanced_tags = null } = this.nodeInfo.configs;
    this.kbs = cloneDeep(repos) ?? [];
    this.batchKbDetails();
    this.tagRule = {
      basic: common_tags,
      advancedRules: advanced_tags,
    };

    const { model, temperature, top_p, max_tokens } = this.nodeInfo.configs.llm;
    this.modelParams = {
      top_p,
      temperature,
      max_tokens,
      history_size: 3,
      frequency_penalty: 0,
      enable_thinking: true,
    };

    const intentGroupConfig = this.nodeInfo.configs?.intent;
    const intentGroupFormValue = intentGroupConfig?.id ?? null;

    this.selectedModelSubscription = this.modelFormGroup.get('model').valueChanges.subscribe(value => {
      this.modelSetTipCtx.selectedModel = this.modelOptions.find(model => model.model_deployment_id === value);
    });

    this.modelFormGroup.setValue({
      prompt: this.nodeInfo.configs.prompt ?? '',
      model: model?.model_deployment_id ?? '',
      chat_history_max_turn: this.nodeInfo.configs?.chat_history_max_turn ?? 0,
      enable_knowledge: !!this.nodeInfo.configs?.enable_knowledge,
      recall_threshold: this.nodeInfo.configs?.recall_threshold ?? 0.8,
      intent_group: intentGroupFormValue ?? null,
      enableMemory: Boolean(this.nodeInfo.configs?.enable_memory),
      tags: repos?.[0]?.tags ?? [],
    });

    NodeUtils.checkModelExistence(this.nodeInfo.name, model?.model_deployment_id ?? '', this.modelOptions);

    // 高级模式
    if (FlowUtils.isAdvancedModeNew(this.nodeInfo)) {
      this.typeTabs = [
        {
          name: this.i18n.transform('normal_mode'),
          id: 'normal',
          active: false,
        },
        {
          name: this.i18n.transform('advanced_mode'),
          id: 'advanced',
          active: true,
        },
      ];
      this.modeId = 'advanced';
    } else {
      this.typeTabs = [
        {
          name: this.i18n.transform('normal_mode'),
          id: 'normal',
          active: true,
        },
        {
          name: this.i18n.transform('advanced_mode'),
          id: 'advanced',
          active: false,
        },
      ];
      this.modeId = 'normal';
    }
    // 设置提示词优化的参数
    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.nodeInfo.configs?.llm?.model,
    });

    // 表单下有隐藏节点的渲染，异步加0.1秒再加入监听事件，否则ngIf隐藏节点渲染前加入监听会导致初始化就触发自动保存
    setTimeout(() => {
      this.formCode$ = this.modelFormGroup.valueChanges.pipe(debounceTime(NODE_SAVE_DEBOUNCE_TIME)).subscribe(value => {
        this.onSave();
      });
    }, 100);

    this.storageSub = fromEvent<StorageEvent>(window, 'storage')
      .pipe(debounceTime(300))
      .subscribe(event => {
        if (event.key === 'intentAdded' && event.newValue) {
          try {
            const data = JSON.parse(event.newValue);
            if (data.type === 'success') {
              this.handleIntentAdd(data);
            }
          } catch (e) {}
        }
      });
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(this.nodeInfo.inputs, this.nameRefOptions);
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.isInit = false;
  }

  override ngOnDestroy(): void {
    this.modelCloseSave();
    if (this.modelListSubscription) {
      this.modelListSubscription.unsubscribe();
    }
    if (this.selectedModelSubscription) {
      this.selectedModelSubscription.unsubscribe();
    }
    if (this.storageSub) {
      this.storageSub.unsubscribe();
    }
    this.formCode$.unsubscribe();
    this.helpCenterService.hideHelpPanel();
    this.destroy$.next();
    this.destroy$.complete();
  }

  public addClass() {
    this.classList.push({
      id: `branch_${this.classList.length + 1}`,
      configs: {
        category: '',
      },
    });
    this.onSave();
  }

  public onDeleteClass(index: number) {
    this.classList.splice(index, 1);

    for (let i = index; i < this.classList.length; ++i) {
      this.classList[i].id = `branch_${i + 1}`;
    }
    this.onSave();
  }

  dismiss(): void {}

  close(): void {}

  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.variants;
    names.splice(index, 1);
    return { existingValues: names };
  }
  get variants() {
    return this.inputParams.map(param => param.name);
  }

  /** 后台搜索 */
  public searchWord = '';

  public onBeforeSearch(searchValue: string) {
    this.searchWord = searchValue;
    this.getIntentGroups({ offset: 0, name: searchValue });
  }

  public loadMore() {
    if (this.intentGroupOptions.length >= this.totalIntentGroups) {
      return;
    }

    const offset = this.intentGroupOptions.length;
    this.isLoadingIntentGroups = true;

    this.intentRepoServe
      .getIntentGroupList({
        offset,
        limit: LAZY_LOAD_LIMIT,
        name: this.searchWord,
      })
      .then(result => {
        this.intentGroupOptions = [...this.intentGroupOptions, ...result.intents].map(item => ({
          ...item,
          merge_name: `${item.name}（${item.branches_cnt}${this.i18n.transform('intentions')}）`,
        }));
        this.totalIntentGroups = result.count;
        this.isLoadingIntentGroups = false;
      });
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  validateNode() {
    const inputErr = this.inputForm?.form?.valid === false;
    let classErr = null;
    if (this.modeId === 'normal') {
      // 普通模式会校验意图分支
      classErr = this.classForm?.form?.valid === false;
    }
    this.updateModelFormValidator();
    const modelErr = this.modelFormGroup?.valid === false;
    if (inputErr || classErr || modelErr) {
      return;
    }
  }

  getKbTagRule() {
    if (!this.modelFormGroup.controls.enable_knowledge.value || !this.kbs.length) {
      return {
        common_tags: null,
        advanced_tags: null,
      };
    }
    return {
      common_tags: this.tagRule.basic,
      advanced_tags: this.tagRule.advancedRules,
    };
  }

  public openRefModal() {
    const thisNzModal: any = this.nzModal.create({
      nzTitle: '',
      nzContent: RefPromptComponent,
      nzClassName: 'ref-prompt-modal',
    });
    const instance = thisNzModal.getContentComponent();
    instance.select.subscribe((tmpl: ITmpl) => {
      this.modelFormGroup.controls.prompt.setValue(tmpl.content);
    });
  }

  public onIntelligentAdd() {
    if (!this.modelFormGroup.controls.prompt.value || this.isFlowReadonly) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
        instruct: this.modelFormGroup.controls.prompt.value,
        isWorkflow: true,
        tipsChange: value => {
          this.modelFormGroup.controls.prompt.setValue(value);
          this.cdr.markForCheck();
        },
      },
    });
  }

  public showSaveTmplModal() {
    if (this.modelFormGroup?.controls?.prompt?.value?.length > 0) {
      const thisMOdal = this.nzModal.create({
        nzContent: SaveTmplLibraryModalComponent,
        nzWidth: 600,
        nzData: {
          currentTmpl: {
            is_workflow: true,
            created_on: moment().format('YYYY-MM-DD HH:mm:ss'),
            content: this.modelFormGroup?.controls?.prompt?.value,
            model_config: {
              temperature: null,
              top_p: null,
              max_tokens: null,
              presence_penalty: null,
            },
          },
          // 调用接口，保存候选模板作为正式模板
          modalClose: form => {
            const params = {
              task_id: this.paramsId,
              id: '',
              name: form.value.templateName,
              tags: form.value.tags,
              industry_id: form.value.industrys,
              content: this.modelFormGroup?.controls?.prompt?.value,
              source: 'PLAYGROUND',
              variables: this.processString(this.modelFormGroup?.controls?.prompt?.value),
            };
            this.candidateTemplateListServe.saveFormalTmpl(params).subscribe({
              next: res => {
                MessageComponent.showSuccess(this.i18n.transform('single_tmpl_save_success_tip'));
              },
            });
          },
        },
      });
    }
  }

  public openAddKbModal() {
    if (this.kbAbilitiesService.isResourceDisabled) {
      return;
    }
    const drawerRef = this.drawerService.create({
      nzPlacement: 'right',
      nzWidth: '700px',
      nzClosable: true,
      nzMaskClosable: true,
      nzKeyboard: true,
      nzContent: KnowledgeBaseSelectorComponent,
      nzData: {
        existedKbs: this.kbs.map(kb => this.kbAbilitiesService.getKbId(kb)),
      },
    });

    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      instance.createKB.subscribe(() => {
        drawerRef.close();
        this.kbCreation.createKb();
      });
      instance.addKB.subscribe(() => {
        this.kbs = drawerRef.getContentComponent().selectedKbs ?? [];
        this.cdr.detectChanges();
        this.onSave();
      });
    });
  }

  public cleanKb(index: number) {
    this.kbs.splice(index, 1);
    this.onSave();
  }

  public changeAuxState() {
    this.scrollToBottom();
  }

  private scrollToBottom() {
    setTimeout(() => {
      this.intentModalRef.nativeElement.scrollTop = this.intentModalRef.nativeElement.scrollHeight;
    }, 0);
  }

  public isLoadingIntentGroups = false;

  public onBeforeOpenIntentGroup(isOpen: boolean) {
    if (!isOpen) {
      return;
    }
    this.isLoadingIntentGroups = true;
    this.getIntentGroups({ offset: 0 }, null, {
      successCb: () => {
        this.isLoadingIntentGroups = false;
      },
      failCb: () => {
        this.intentGroupOptions = [];
        this.totalIntentGroups = 0;
        this.isLoadingIntentGroups = false;
      },
    });
  }

  /** 点击展示模型配置的Tip弹窗 */
  public onShowModelSetTip() {
    if (this.showModelSetRef) {
      this.showModelSetRef = false;
      this.modelSettingsRef.hide();
    } else {
      this.showModelSetRef = true;
      this.modelSetTipCtx.param = { ...this.modelParams };
      window.setTimeout(() => {
        this.modelSettingsRef.show();
      });
    }
  }

  /** 切换意图的模式 */
  public changeTab(item: any) {
    if (this.hasParentNode) {
      return;
    }

    // 检测当前模式和目标模式是否不同，若相同，则不执行任何操作
    if (this.modeId === item.id) {
      return;
    }

    this.nzMessage.warning(this.modeId === 'normal' ? this.i18n.transform('content_advanced_mode') : this.i18n.transform('content_normal_mode'));
    this.typeTabs.forEach((tab: any) => {
      tab.active = false;
    });
    item.active = true;
    this.modeId = item.id;
    this.showModelSetRef = false;

    if (this.modeId === 'normal') {
      this.resetNormalMode();
    }
  }

  public isObject(value): boolean {
    return isObject(value);
  }

  /** 从高级切换为普通模式，初始化意图分类配置 */
  private resetNormalMode() {
    // 表示在dsl中，该意图节点为高级模式，需要初始化。其余情况下，不会丢失已填写但未点确定的意图分类信息
    if (!this.classList.length) {
      this.classList = [
        {
          id: 'branch_0',
          configs: {
            category: this.i18n.transform('uncertain_other_intentions'),
          },
        },
        {
          id: 'branch_1',
          configs: {
            category: '',
          },
        },
      ];
    }

    if (this.classList.length > 0 && this.classList[0].id === 'branch_0') {
      this.classList.shift();
      this.hasOtherClass = true;
    }
  }

  /** 普通模式，不会校验意图包是否非空 */
  private updateModelFormValidator() {
    const intentGroupControl = this.modelFormGroup.get('intent_group');
    intentGroupControl?.updateValueAndValidity();
  }

  private getIntentGroups(
    params: { offset: number; name?: string },
    selectComp?: any,
    configs: ICallbackFn = {
      successCb: () => {},
      failCb: () => {},
      finallyCb: () => {},
    }
  ): Promise<void> {
    selectComp?.setLoading?.(true);

    const reqParams: any = {
      offset: params.offset,
      limit: LAZY_LOAD_LIMIT,
    };
    if (params.name !== undefined) {
      reqParams.name = params.name;
    }
    return this.intentRepoServe
      .getIntentGroupList(reqParams)
      .then(result => {
        selectComp?.setLoading?.(false);
        this.intentGroupOptions = result.intents.map(item => ({
          ...item,
          merge_name: `${item.name}（${item.branches_cnt}${this.i18n.transform('intentions')}）`,
        }));
        this.totalIntentGroups = result.count;
        configs?.successCb?.();
      })
      .catch(() => {
        configs?.failCb?.();
      })
      .finally(() => {
        configs?.finallyCb?.();
      });
  }

  public updateModel(modelInfo: any) {
    this.modelFormGroup.controls.model.setValue(modelInfo.id);
    // 设置提示词优化的参数
    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: modelInfo.modelInfo,
    });
  }

  @HostListener('window:resize', ['$event'])
  onResize() {
    this.showModelSetRef = false;
  }

  /**
   * 切换浏览器页签时，tiny tip会自动关闭，但没有修改 this.show 值
   * 规避先去别的页签，再切回来，要点击两次示例按钮，才能展示tip的问题
   */
  @HostListener('window:visibilitychange', ['$event'])
  onVisibilityChange() {
    if (document.hidden) {
      this.showModelSetRef = false;
    }
  }

  @HostListener('scroll', ['$event'])
  onScroll() {
    this.showModelSetRef = false;
  }

  /** 处理“保存候选模板作为正式模板”接口中的入参variables */
  public processString(input: string): string {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map(match => match.slice(2, -2));
      return extractedValues.join(',');
    }
    return '';
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const selectedModel = this.modelOptions.find(model => model.model_deployment_id === this.modelFormGroup.controls.model.value);

    let nodeData: IIntentNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: NodeUtils.getDtoInputs(this.inputParams),
      outputs: this.nodeInfo.outputs,
      configs: {
        prompt: this.modelFormGroup.controls.prompt.value,
        llm: {
          temperature: Number(this.modelParams.temperature),
          top_p: Number(this.modelParams.top_p),
          max_tokens: Number(this.modelParams.max_tokens),
          model: {
            model_name: selectedModel?.model_name ?? '',
            model_type: selectedModel?.model_type ?? '',
            model_deployment_id: selectedModel?.model_deployment_id ?? '',
            ...(selectedModel?.model && { model: selectedModel.model }),
          },
        },
        chat_history_max_turn: this.modelFormGroup.controls.chat_history_max_turn.value,
        ...(this.configServ.isSupportUserPersona() ? { enable_memory: this.modelFormGroup.get('enableMemory').value } : {}),
        ...this.getKbTagRule(),
      },
      branches: [],
    };

    if (this.modeId === 'normal') {
      nodeData.configs.enable_knowledge = this.modelFormGroup.controls.enable_knowledge.value;
      nodeData.branches = this.hasOtherClass ? [this.otherClass, ...this.classList] : this.classList;

      if (this.modelFormGroup.controls.enable_knowledge.value) {
        nodeData.configs.repos = this.kbs.map(kb => ({
          name: kb.name,
          id: this.kbAbilitiesService.getKbId(kb),
          description: kb.description,
        }));
        nodeData.configs.recall_threshold = this.modelFormGroup.controls.recall_threshold.value;
      }
    } else {
      const intentGroupId = this.modelFormGroup.controls.intent_group.value;
      const intentGroupInfo = this.intentGroupOptions.find(item => item.intent_id === intentGroupId);
      if (!nodeData.configs.intent) {
        nodeData.configs.intent = {
          id: '',
          name: '',
          branches_cnt: 0,
        };
      }
      nodeData.configs.intent.id = intentGroupId ?? '';
      nodeData.configs.intent.name = intentGroupInfo?.name ?? '';
      nodeData.configs.intent.branches_cnt = intentGroupInfo?.branches_cnt ?? 0;
      nodeData.branches = [this.otherClass];
    }

    this.appFlowServ.setModeOfIntentNode({
      node_id: this.nodeInfo.id,
      mode: this.modeId,
    });
    this.appFlowServ.setNodeSaveMonitor({
      nodeData,
    });
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    this.updateTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  onSave() {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  ruleComplete(tagRule: TagRule) {
    this.tagRule = tagRule;
  }

  batchKbDetails() {
    if (this.kbs.length) {
      this.knowledgeRepoService
        .getKnowledgeBaseList({
          knowledge_base_ids: this.kbs.map(kb => this.kbAbilitiesService.getKbId(kb)),
          limit: 100,
          offset: 0,
          share_scope: KBScope.ALL,
        })
        .then(res => {
          const kbItems = this.kbAbilitiesService.normalizeKBList(res.items);
          this.kbs = [
            ...this.kbs.map(kb => {
              const actualKb = kbItems.find(kbRes => kbRes.id === kb.id);
              return actualKb ?? kb;
            }),
          ];
        });
    }
  }

  toCreatePackage() {
    const { id, workspace_id } = this.route.snapshot.queryParams;
    const URL = `${location.protocol}//${location.host}${location.pathname}#/home/intent-package/intent-detail?previousUrl=agent&flowId=${id}&workspaceId=${workspace_id}`;
    window.open(URL, 'window_create_intent');
  }

  getIntentSelectList() {
    this.intentRepoServe
      .getIntentGroupList({
        offset: 0,
        limit: LAZY_LOAD_LIMIT,
      })
      .then(result => {
        this.intentGroupOptions = result.intents.map(item => ({
          ...item,
          merge_name: `${item.name}（${item.branches_cnt}${this.i18n.transform('intentions')}）`,
        }));
        this.totalIntentGroups = result.count;
      })
      .catch(() => {
        this.intentGroupOptions = [];
        this.totalIntentGroups = 0;
      });
  }

  handleIntentAdd(data) {
    const { name, intentId } = data;
    const thisNzModal = this.nzModal.create({
      nzTitle: '',
      nzContent: IntentAddTipModalComponent,
      nzClassName: 'intent-add-class',
      nzFooter: null,
    });
    const instance = thisNzModal.getContentComponent();
    instance.packageName = name;
    instance.intentId = intentId;
    thisNzModal.afterClose.subscribe(() => {
      if (FlowUtils.isAdvancedModeNew(this.nodeInfo)) {
        this.intentRepoServe
          .getIntentGroupList({
            offset: 0,
            limit: LAZY_LOAD_LIMIT,
          })
          .then(result => {
            this.intentGroupOptions = result.intents.map(item => ({
              ...item,
              merge_name: `${item.name}（${item.branches_cnt}${this.i18n.transform('intentions')}）`,
            }));
            this.totalIntentGroups = result.count;
            const intent = result.intents.find(item => item.intent_id === intentId);
            if (!intent) {
              return;
            }
            this.modelFormGroup.controls.intent_group.setValue(intent.intent_id);
          })
          .catch(() => {
            this.intentGroupOptions = [];
            this.totalIntentGroups = 0;
          });
      }
    });
  }
}
