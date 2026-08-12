import { Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { BehaviorSubject, Subject, Subscription, takeUntil, debounceTime } from 'rxjs';
import { CommonUtils } from 'src/utils/common.util';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import type { IModel } from '../../app-flow.types';
import {
  getInitInputParamConfig,
  getInitOutputParamConfig,
  getInitRefParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  NODE_SAVE_DEBOUNCE_TIME,
  WORKFLOW_SVGS,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import type { ILLMNode, IParamRef, IWFView, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamSelectorComponent } from '../param-selector/param-selector.component';
import { NodeUtils } from '../utils';
import { CmdTextareaComponent } from '../cmd-textarea/cmd-textarea.component';
import { type IModelParam, modelSettingsComponent } from '@shared/components/model-settings-tip';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { ExceptionHandlingComponent } from '@routes/agent-center/app-flow/components/exception-handling/exception-handling.component';
import { ModelType } from '@enums/jiuwen-model.enum';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { GETVARIANT_REG } from '@constants/exp-tmpl-config.const';
import { ActivatedRoute } from '@angular/router';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { MessageComponent } from '@shared/services/cfdata.service';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import { AssetIntelligentAddDisabledComponent } from '@shared/components/assets/asset-intelligent-add-disabled/asset-intelligent-add-disabled.component';
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
import { SaveTmplLibraryModalComponent } from '@routes/prompt/prompt-candidate-template/save-tmpl-library-modal/save-tmpl-library-modal.component';
import { ITmpl } from '@services/prompt.service';
import moment from 'moment';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
function removeNodeFromTree(nodes: any[], target: any): boolean {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i] === target) {
      nodes.splice(i, 1);
      return true;
    }
    if (nodes[i].children && removeNodeFromTree(nodes[i].children, target)) {
      return true;
    }
  }
  return false;
}

function getParentNodeFromTree(nodes: any[], target: any, parent: any = null): any {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i] === target) {
      return parent;
    }
    if (nodes[i].children) {
      const result = getParentNodeFromTree(nodes[i].children, target, nodes[i]);
      if (result !== null) {
        return result;
      }
    }
  }
  return null;
}

@Component({
  selector: 'meta-llm-modal',
  templateUrl: './llm-modal.component.html',
  styleUrls: ['./llm-modal.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    ParamSelectorComponent,
    AddPropsIconComponent,
    CmdTextareaComponent,
    ExceptionHandlingComponent,
    LLMSelectComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
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
export class LLMModalComponent extends ModalBaseComponent implements OnInit, OnDestroy {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: ILLMNode;

  @Output('confirm') confirm = new EventEmitter<ILLMNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('inputFormVision') inputFormVision: NgForm;

  @ViewChild('outputForm') outputForm: NgForm;

  @ViewChild('nameForm') nameForm: NgForm;

  @ViewChild('modelSettingsRef')
  modelSettingsRef: any;

  @ViewChild('exceptionHandling') exceptionHandling: ExceptionHandlingComponent;

  protected override destroy$ = new Subject<void>();

  public validationRules: any[] = [];

  get tipVals() {
    return this.inputParams.map(param => param.name);
  }

  public originFormats: any[] = [
    {
      id: 'text',
      title: this.i18n.transform('text'),
    },
    {
      id: 'markdown',
      title: 'Markdown',
    },
    {
      id: 'json',
      title: 'JSON',
    },
  ];

  public outputFormats: any[] = [...this.originFormats];

  public changeUrl = cdnAssetUrl;

  public outputFormat = this.outputFormats[0];

  public validation: any = {
    type: 'change',
  };

  public modelValidation: any = {
    errorMessage: {
      required: this.i18n.transform('select_model'),
    },
    type: 'changeAlert',
  };

  public llmIconUrl = WORKFLOW_SVGS.LLM;

  public nameRefOptions: IParamRef[] = [];
  public visionNameRefOptions: IParamRef[] = [];

  public modelListSubscription: Subscription;

  public outputDataTypes = getOutputParamTypes();

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public modelOptions: IModel[] = [];

  public inputParams: IWorkflowField[] = [];

  //视觉理解输入
  public visionInputParams: IWorkflowField[] = [];

  //视觉理解Name,唯一
  public visionLastId = 1;

  public isVisionModel = false;

  public outputParams: IWFView[] = [];

  // 模型配置的Tip弹窗
  public modelSetRefCmp = modelSettingsComponent;
  public showSafetyBarrier = false;
  prompt = '';
  systemPrompt = '';

  public modelFormGroup = this.fb.group({
    model: [''],
    enableHistory: [false],
    enableMemory: [false],
    stream: [true],
  });

  public showModelSetRef = false;

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
    showThinkSwitch: true,
    selectedModel: {} as IModel,
    isLlm: true,
    outputs: {
      updatedParam: ($event: IModelParam) => {
        this.modelParams = { ...$event };
        this.showModelSetRef = false;
        this.modelSettingsRef.hide();
        this.onSave();
      },
    },
  };

  errorMsgBaseConfig: any = {
    errorMessage: {
      notContains: this.i18n.transform('param_name_notcontains'),
    },
  };

  public noneObjDataTypes = getNoneObjOutputParamTypes();

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public isSimpleType = NodeUtils.isSimpleType;

  public addChild(param: IWFView) {
    NodeUtils.addChild(param);
    this.outputParams = [...this.outputParams];
  }

  public spinnerValue = 1;

  private paramsId: string;

  @ViewChild('descriptionDom') descriptionDom: any;

  get getParamWidth() {
    const width = (this.descriptionDom?.nativeElement?.offsetWidth | 0) + 2;
    return `${width}px`;
  }

  public safety_barrier = false;

  showLlmSelectErrorClass = false;

  readonly showSystemVarListSubject$ = new Subject<boolean>();
  readonly showUserVarListSubject$ = new Subject<boolean>();

  onShowVarList(event: Event, subject: Subject<boolean>) {
    event.preventDefault();
    event.stopPropagation();
    subject.next(true);
  }

  needValid = false;
  updateTimeout: any = null;

  trackByFn(index: number, item: any): string {
    return item.key || item.origin?.name || index;
  }

  constructor(
    private fb: FormBuilder,
    protected override appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private elementRef: ElementRef<HTMLDivElement>,
    private nzModal: NzModalService,
    protected override nodeServ: NodeService,
    protected agentDataServe: AgentDataService,
    private route: ActivatedRoute,
    public configServ: AgentConfigService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    private candidateTemplateListServe: CandidateTemplateListService,
    private cdr: ChangeDetectorRef
  ) {
    super(nodeServ, appFlowServ);
  }

  onOutputParamTypeChange(param) {
    NodeUtils.onOutputParamTypeChange(param);
    this.outputParams = [...this.outputParams];
    this.onSave();
  }

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  override getLayerIndexWidth(param: IWFView): string {
    return NodeUtils.getLayerIndexWidth(param, this.isNormalView, {
      widthArr: [165, 136],
    });
  }

  public override ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.paramsId = params.id;
    });
    this.showSafetyBarrier = !!this.configServ.getConfigs()?.safety_barrier_display;
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    this.safety_barrier = !!this.nodeInfo.configs?.safety_barrier;

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe(info => {
        this.onRefUpdate(info);
      });
    }

    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo.name));

    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(models => {
        this.modelOptions = models ?? []; // 接收新的模型列表
        const selectedModel = this.modelOptions.find(model => model.model_deployment_id === this.nodeInfo.configs?.model?.model_deployment_id);
        this.isVisionModel = selectedModel?.model_type === ModelType.IMAGE_TO_TEXT;
        this.safety_barrier = !!this.nodeInfo.configs?.safety_barrier;
      });
    this.outputParams = NodeUtils.fields2Views(this.nodeInfo.outputs);

    this.modelFormGroup.setValue({
      model: this.nodeInfo.configs?.model?.model_deployment_id ?? '',
      enableHistory: this.nodeInfo.configs.enable_history ?? false,
      stream: this.nodeInfo.configs?.stream ?? true,
      enableMemory: Boolean(this.nodeInfo.configs?.enable_memory),
    });

    this.prompt = this.nodeInfo.configs.template_content;
    this.systemPrompt = this.nodeInfo.configs.system_prompt || '';

    NodeUtils.checkModelExistence(this.nodeInfo.name, this.nodeInfo.configs?.model?.model_deployment_id ?? '', this.modelOptions);

    this.modelSetTipCtx.selectedModel = this.modelOptions.find(model => model.model_deployment_id === this.modelFormGroup.get('model').value);

    // 初始化模型参数信息
    const { top_p, temperature, history_size = 3, max_tokens, frequency_penalty = 0, enable_thinking = true } = this.nodeInfo.configs;
    this.modelParams = {
      top_p,
      temperature,
      history_size,
      max_tokens,
      frequency_penalty,
      enable_thinking,
    };

    this.outputFormat = this.outputFormats.find(format => format.id === this.nodeInfo.configs.response_format) ?? this.outputFormat;

    if (this.outputFormat.id === 'json') {
      this.modelFormGroup.controls.stream.setValue(false);
      this.modelFormGroup.get('stream')?.disable();
    }

    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.nodeInfo.configs?.model,
    });

    this.modelFormGroup.get('model').valueChanges.subscribe(value => {
      const selectedModel = this.modelOptions.find(model => model.model_deployment_id === value);
      this.modelSetTipCtx.selectedModel = selectedModel;
      this.agentDataServe.setPromptAndModelConfig({
        modelConfig: selectedModel,
      });
      this.isVisionModel = selectedModel?.model_type === ModelType.IMAGE_TO_TEXT;
      if (!this.isVisionModel) {
        this.visionInputParams = [];
      }
    });

    this.modelFormGroup.get('stream').valueChanges.subscribe(value => {
      this.exceptionHandling.changeStream(value);
    });
  }

  ngAfterViewInit(): void {
    this.exceptionHandling.changeStream(this.modelFormGroup.controls.stream.value);
    this.exceptionHandling.changeResponseFormat(this.outputFormat.id);
    // 表单下有隐藏节点的渲染，异步加0.1秒再加入监听事件，否则隐藏节点渲染前加入监听会导致初始化就触发自动保存
    setTimeout(() => {
      this.modelFormGroup.valueChanges.pipe(debounceTime(NODE_SAVE_DEBOUNCE_TIME)).subscribe(values => {
        this.onSave();
      });
    }, 100);
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  override ngOnDestroy(): void {
    if (this.modelListSubscription) {
      this.modelListSubscription.unsubscribe();
    }
    this.helpCenterService.hideHelpPanel();
    this.modelCloseSave();
    this.destroy$.next();
    this.destroy$.complete();
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;
    this.visionNameRefOptions = this.getVisionNameRefOptions();
    if (this.isInit) {
      const visionInput = [];
      const input = [];
      const visionList: string[] = this.nodeInfo.configs?.vision ?? [];
      this.nodeInfo.inputs.forEach(i => {
        if (visionList.includes(i.name)) {
          visionInput.push(i);
        } else {
          input.push(i);
        }
      });
      this.inputParams = NodeUtils.initInputs(input, this.nameRefOptions);
      this.visionInputParams = NodeUtils.initInputs(visionInput, this.visionNameRefOptions);
      this.resetVisionLastId();
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
      NodeUtils.reSelectRefsWithNewOps(this.visionInputParams, this.visionNameRefOptions);
    }
    this.isInit = false;
  }

  public securitySwitchChange($event: boolean) {
    let content = this.i18n.transform('configtoolscomponent_47');
    let title = this.i18n.transform('configtoolscomponent_41');

    if (!$event) {
      this.nzModal.confirm({
        nzTitle: title,
        nzContent: content,
        nzOkText: this.i18n.transform('determined'),
        nzCancelText: this.i18n.transform('to_cancel'),
        nzOnOk: (): void => {
          this.safety_barrier = false;
          this.onSave();
        },
        nzOnCancel: (): void => {
          this.safety_barrier = !$event;
        },
      });
    } else {
      this.safety_barrier = $event;
      this.onSave();
    }
  }

  resetVisionLastId() {
    this.visionInputParams.forEach(i => {
      if (i.name.startsWith('_vision_') || i.name.startsWith('_image_vision_') || i.name.startsWith('_video_vision_')) {
        let curId = Number(i.name.split('_vision_')[1] ?? '1');
        if (isNaN(curId)) {
          curId = 1;
        }
        this.visionLastId = Math.max(this.visionLastId, curId);
        this.visionLastId++;
      }
    });
  }

  isModelReachedParamLimit() {
    return this.isReachedParamLimit([...this.inputParams, ...this.visionInputParams]);
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  public deleteVisionInputParam(index: number): void {
    this.visionInputParams.splice(index, 1);
    this.onSave();
  }

  public showDelete(param: IWFView) {
    return NodeUtils.showDelete(param, this.outputParams);
  }

  public onDeleteOutput(param: IWFView) {
    removeNodeFromTree(this.outputParams, param);

    const parentNodeParam = getParentNodeFromTree(this.outputParams, param) as IWFView;
    if (this.isObjectLikeType(parentNodeParam?.type) && parentNodeParam?.children?.length === 0) {
      delete parentNodeParam.children;
    }
    this.outputParams = [...this.outputParams];
    this.onSave();
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSave();
  }

  getVisionNameRefOptions() {
    const visionNameRefOptions = [];
    const visionParmaTypes = ['array<file/image>', 'array<file/video>', 'array<string>', 'file/image', 'file/video'];
    this.nameRefOptions.forEach(o => {
      const target = cloneDeep(o);
      if (target.type !== 'System') {
        const children = [];
        target.children.forEach(c => {
          if (visionParmaTypes.includes(c.type)) {
            children.push(c);
          }
        });
        target.children = children;
        visionNameRefOptions.push(target);
      }
    });
    return visionNameRefOptions;
  }

  public addVisionInputParam() {
    const visionNameRefOptions = this.getVisionNameRefOptions();
    const config = getInitRefParamConfig();
    config.name = this.handelDuplicateInputName();
    this.visionInputParams.push({
      ...config,
      refs: cloneDeep(visionNameRefOptions),
    });
    this.onSave();
  }

  public handelVisionSelect($event, i) {
    const inputs = NodeUtils.getDtoInputs(this.visionInputParams);
    setTimeout(() => {
      let newVisionInputParams: IWorkflowField[] = [];
      newVisionInputParams = this.visionInputParams;
      inputs.forEach((item, j) => {
        const name = 'ref_var_name';
        if (item.value.content && item.value.content[name]) {
          if (j !== i && item.value.content[name] === $event.ref_var_name) {
            newVisionInputParams[i].value.content = '';
            MessageComponent.showError(this.i18n.transform('llmmodalcomponent_423'));
          }
        }
      });
      this.visionInputParams = newVisionInputParams;
      this.onSave();
    }, 0);
  }

  handelDuplicateInputName() {
    const names = this.inputParams.map(p => p.name);
    let name = '_vision_' + this.visionLastId;
    //重复直接加上时间戳
    if (names.includes(name)) {
      const date = new Date();
      name = '_vision_' + this.visionLastId + date.getTime();
    } else {
      this.visionLastId++;
    }
    return name;
  }

  public addOutputParam() {
    this.outputParams = [
      ...this.outputParams,
      {
        ...getInitOutputParamConfig(),
        depth: 0,
        parentType: 'none',
        key: `output_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        name: ``,
      },
    ];
    this.onSave();
  }

  /** 点击展示模型配置的Tip弹窗 */
  public onShowModelSetTip() {
    this.showModelSetRef = !this.showModelSetRef;
    if (this.showModelSetRef) {
      this.modelSetTipCtx.param = { ...this.modelParams };
    }
  }

  public onModelSettingsUpdate(param: any) {
    this.modelParams = { ...param };
    this.showModelSetRef = false;
    this.onSave();
  }

  dismiss(): void {}

  close(): void {}

  changeFormat(format: any) {
    this.outputFormat = format;
    if (['text', 'markdown'].includes(format.id as string)) {
      const param = this.outputParams.shift();
      param.type = 'string';
      param.description = this.i18n.transform('original_output');
      delete param?.children;

      this.outputParams = [param];
    }
    if (format.id === 'json') {
      this.modelFormGroup.controls.stream.setValue(false);
      this.modelFormGroup.get('stream')?.disable();
    } else {
      this.modelFormGroup.get('stream')?.enable();
    }
    this.exceptionHandling.changeResponseFormat(format.id);
  }

  showLlmSelectError() {
    const modalErr = this.modelFormGroup.invalid;
    if (modalErr) {
      this.showLlmSelectErrorClass = true;
    } else {
      this.showLlmSelectErrorClass = false;
    }
    return this.showLlmSelectErrorClass;
  }

  validateNode() {
    this.exceptionHandling.validate();
    CommonUtils.checkAndFocusFirstError(this.elementRef, this.modelFormGroup);
    this.needValid = true;
  }

  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.inputParams.map(p => p.name);
    names.splice(index, 1);
    const visionNames = this.visionInputParams.map(p => p.name);
    return { existingValues: [...names, ...visionNames] };
  }

  getOutputNames(param: IWFView): {
    existingValues: string[];
  } {
    let names = [];
    if (param.depth === 0) {
      names = this.outputParams.map(arg => arg.name);
    } else {
      const parentNode = getParentNodeFromTree(this.outputParams, param);
      names = parentNode?.children.map(arg => arg.name);
    }

    if (names && names.indexOf(param.name) > -1) {
      names.splice(names.indexOf(param.name), 1);
    }
    return { existingValues: names };
  }

  onNameChange() {
    window.setTimeout(() => {
      this.inputForm?.form?.markAsDirty();
      this.outputForm?.form?.markAsDirty();
      if (this.isVisionModel) {
        this.inputFormVision?.form?.markAsDirty();
      }
    });
  }

  public onIntelligentAdd(role) {
    if (this.isFlowReadonly) return;
    if (role === 'system' && !this.systemPrompt) return;
    if (role === 'user' && !this.prompt) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
        instruct: role === 'system' ? this.systemPrompt : this.prompt,
        isWorkflow: true,
        tipsChange: value => {
          if (role === 'system') {
            this.systemPrompt = value ?? '';
          } else {
            this.prompt = value ?? '';
          }
          this.onSave();
          this.cdr.markForCheck();
        },
      },
    });
  }

  public openRefModal(type) {
    const myModal = this.nzModal.create({
      nzContent: RefPromptComponent,
      nzWidth: 1000,
      nzData: {
        select: (tmpl: ITmpl) => {
          const content = tmpl.content;
          if (type === 'user') {
            this.prompt = content;
          }
          if (type === 'system') {
            this.systemPrompt = content;
          }
          this.onSave();
          this.cdr.markForCheck();
        },
      },
    });
  }

  public showSaveTmplModal(type: 'user' | 'system') {
    let prompt = '';
    if (type === 'system' && this.systemPrompt && this.systemPrompt.length > 0) {
      prompt = this.systemPrompt;
    } else if (type === 'user' && this.prompt && this.prompt.length > 0) {
      prompt = this.prompt;
    } else {
      return;
    }
    const thisMOdal = this.nzModal.create({
      nzContent: SaveTmplLibraryModalComponent,
      nzWidth: 600,
      nzData: {
        currentTmpl: {
          is_workflow: true,
          created_on: moment().format('YYYY-MM-DD HH:mm:ss'),
          content: prompt,
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
            content: this.systemPrompt,
            source: 'PLAYGROUND',
            variables: this.processString(this.systemPrompt),
          };
          this.candidateTemplateListServe.saveFormalTmpl(params).subscribe({
            next: res => {
              MessageComponent.showSuccess(this.i18n.transform('single_tmpl_save_success_tip'));
            },
          });
          this.cdr.markForCheck();
        },
      },
    });
  }

  public updateModel(modelInfo: any) {
    this.modelFormGroup.controls.model.setValue(modelInfo.id);
    this.modelParams.enable_thinking = true;
    this.showLlmSelectError();
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

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const selectedModel = this.modelOptions.find(model => model.model_deployment_id === this.modelFormGroup.controls.model.value);
    const vision = [];
    const targetInputParams = [...this.inputParams, ...this.visionInputParams];

    const inputs = NodeUtils.getDtoInputs(targetInputParams);
    inputs.forEach(i => {
      const schema: IWorkflowField = i.schema as IWorkflowField;
      if (i.name.startsWith('_vision_') || i.name.startsWith('_image_vision_') || i.name.startsWith('_video_vision_')) {
        const index = i.name.split('_vision_')[1] ?? '1';
        if (schema?.type === 'file/video' || i.type === 'file/video') {
          // 视频数组（schema.type）与单个 file/video（getDtoInput 后 schema 被删除，用 i.type 兜底）均归入视频
          i.name = `_video_vision_${index}`;
        } else if (schema?.type === 'file/image' || schema?.type === 'string' || i.type === 'file/image') {
          // 字符串数组默认为图片地址；单个 file/image 经 getDtoInput 后 schema 被删除，用 i.type 兜底
          i.name = `_image_vision_${index}`;
        }
        vision.push(i.name);
      }
    });

    let modelType = selectedModel?.type === 'router' ? 'strategy' : (selectedModel?.model_type ?? ModelType.LLM);
    const nodeData: ILLMNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: inputs,
      outputs: NodeUtils.views2Fields(this.outputParams),
      configs: {
        ...this.nodeInfo.configs,
        enable_history: this.modelFormGroup.controls.enableHistory.value,
        stream: this.modelFormGroup.controls.stream.value,
        template_content: this.prompt,
        system_prompt: this.systemPrompt,
        model: {
          ...(selectedModel?.model && { model: selectedModel.model }),
          model_id: selectedModel?.id ?? '',
          model_name: selectedModel?.model_name ?? '',
          model_type: modelType,
          model_deployment_id: selectedModel?.model_deployment_id ?? '',
          ...(selectedModel?.model && { model: selectedModel.model }),
        },
        temperature: Number(this.modelParams.temperature),
        top_p: Number(this.modelParams.top_p),
        response_format: this.outputFormat.id,
        history_size: Number(this.modelParams.history_size),
        max_tokens: Number(this.modelParams.max_tokens),
        frequency_penalty: Number(this.modelParams.frequency_penalty),
        enable_thinking: this.modelParams.enable_thinking,
        vision,
        safety_barrier: !!this.safety_barrier,
        ...(this.configServ.isSupportUserPersona() ? { enable_memory: this.modelFormGroup.get('enableMemory').value } : {}),
      },
    };
    if (!selectedModel?.is_support_close_reasoning) {
      delete nodeData.configs.enable_thinking;
    }
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

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
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
}
