import {
  Component,
  EventEmitter,
  Input,
  NgZone,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
  ChangeDetectorRef,
} from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { I18nNamespace } from '@i18n';
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { ITmpl } from '@services/prompt.service';
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
import { BehaviorSubject, Subject, Subscription, takeUntil } from 'rxjs';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import type { IModel } from '../../app-flow.types';
import {
  getInitGeneratedInputParamConfig,
  getInitInputParamConfig,
  getInitOutputParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  WORKFLOW_SVGS,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import * as nodeType from '../../node.type';
import {
  IExtensionWorkflow,
  IParamExtractionNode,
  IParamRef,
  IProcessingWorkflow,
  type IWFView,
  IWorkflowField,
  IWorkflowFieldType,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamSelectorComponent } from '../param-selector/param-selector.component';
import { IRef2TreeConfig, NodeUtils } from '../utils';
import { CmdTextareaComponent } from '../cmd-textarea/cmd-textarea.component';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import { AssetIntelligentAddDisabledComponent } from '@shared/components/assets/asset-intelligent-add-disabled/asset-intelligent-add-disabled.component';
import {
  type IModelParam,
  modelSettingsComponent,
} from '@shared/components/model-settings-tip';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { ModelType } from '@enums/jiuwen-model.enum';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { isSystemTypeWithNames } from '@routes/agent-center/utils';
import { isNil } from 'lodash';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { ConfigureWorkflowModalComponent } from '@routes/agent-center/app-flow/components/param-extraction-modal/configure-workflow-modal/configure-workflow-modal.component';
import { ConditionModalComponent } from '@routes/agent-center/app-flow/components/param-extraction-modal/condition-modal/condition-modal.component';
import { BranchUtils } from '@routes/agent-center/app-flow/components/branch.utils';
import { SetValueComponent } from '@routes/agent-center/app-flow/components/param-extraction-modal/set-value/set-value.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { HttpService } from '@services/http.service';
import { CommonService } from '@services/common.service';
import { CdkDrag, CdkDropList, moveItemInArray } from '@angular/cdk/drag-drop';
import { removeHTMLTag } from 'src/utils/utils';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { MessageComponent } from "@shared/services/cfdata.service";
import { ObjectTemplateComponent } from "@routes/object-manage/component/object-template/object-template.component";
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
interface IWFViewP extends IWFView {
  processing_workflows?: IProcessingWorkflow[];
  children?: IWFViewP[];
}

@Component({
  selector: 'meta-param-extraction-modal',
  templateUrl: './param-extraction-modal.component.html',
  styleUrls: [
    './param-extraction-modal.component.less',
    '.././common-styles.less',
  ],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    ValueValidityValidatorDirective,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ParamSelectorComponent,
    RefSelectedRequireDirective,
    AddPropsIconComponent,
    CmdTextareaComponent,
    AssetIntelligentAddDisabledComponent,
    AssetIntelligentAddComponent,
    LLMSelectComponent,
    ConditionModalComponent,
    SetValueComponent,
    EditNameComponent,
    CdkDropList,
    CdkDrag,
    NodeDescriptionComponent,
    InputTreeSelect,
    modelSettingsComponent,
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
export class ParamExtractionModalComponent
  extends ModalBaseComponent
  implements OnInit, OnDestroy
{
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: nodeType.IParamExtractionNode;

  @Output('confirm') confirm =
    new EventEmitter<nodeType.IParamExtractionNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('domainForm') domainForm: NgForm;

  @ViewChild('nameForm') nameForm: NgForm;

  @ViewChild('midParamForm') midParamForm: NgForm;

  @ViewChild('fetchParamForm') fetchParamForm: NgForm;

  @ViewChild('exFlowForm') exFlowForm: NgForm;

  @ViewChild('modelSettingsRef')
  modelSettingsRef: any;

  @ViewChild('entryConditionModal')
  entryConditionModal: ConditionModalComponent;

  @ViewChild('breakConditionModal')
  breakConditionModal: ConditionModalComponent;

  @ViewChild('exceptionConditionModal')
  exceptionConditionModal: ConditionModalComponent;

  readonly showVarListSubject$ = new Subject<boolean>();

  protected override destroy$ = new Subject<void>();

  public validationRules: any[] = [];

  get tipVals() {
    return this.inputParams.map((param) => param.name);
  }

  @ViewChild('descriptionDom') descriptionDom: any;

  get getParamWidth() {
    const width = (this.descriptionDom?.nativeElement?.offsetWidth | 0) + 2;
    return `${width}px`;
  }

  @ViewChild('descriptionDomO') descriptionDomO: any;

  get getParamWidthO() {
    const width = (this.descriptionDomO?.nativeElement?.offsetWidth | 0) + 2;
    return `${width}px`;
  }

  public changeUrl = cdnAssetUrl;

  public validation: any = {
    type: 'change',
  };

  public modelValidation: any = {
    errorMessage: {
      required: this.i18n.transform('select_model'),
    },
    type: 'changeAlert',
  };

  showLlmSelectErrorClass = false;

  public iconUrl = WORKFLOW_SVGS.ParamExtraction;

  public nameRefOptions: nodeType.IParamRef[] = [];

  public modelListSubscription: Subscription;

  public outputDataTypes = getOutputParamTypes();

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public modelOptions: IModel[] = [];

  public inputParams: nodeType.IWorkflowField[] = [];

  public outputParams: nodeType.IWFView[] = [];

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public midParams: IWFView[] = []; //上下文变量

  public domainObjectsParams: IWFViewP[] = []; //领域对象

  public fetchParams: IWFView[] = []; //参数提取配置

  public conditionOps: IParamRef[] = [];

  // 模型配置的Tip弹窗
  public modelSetRefCmp = modelSettingsComponent;
  prompt = '';
  promptInvalid = false;
  enable_intent_break = true;
  intent_break_prompt = '';
  extension_workflows: nodeType.IExtensionWorkflow[] = [];
  //模型提取参数进入条件判断
  entry_condition: nodeType.IBranchConfigs =
    BranchUtils.getNewBranchBlankConfigs();
  // 节点跳出条件
  break_condition: nodeType.IBranchConfigs =
    BranchUtils.getNewBranchBlankConfigs();
  exception_config: any = {
    max_iterations: 20,
    exception_condition: BranchUtils.getNewBranchBlankConfigs(),
  };
  //备注信息
  description = '';

  openConditionConfig = false; //是否展开条件配置

  public modelFormGroup = this.fb.group({
    model: [''],
  });

  public modelParams = {
    top_p: 0.5,
    temperature: 0.5,
    history_size: 3,
    max_tokens: null,
    frequency_penalty: 0,
  };

  public showModelSetRef = false;

  public modelSetTipCtx = {
    param: this.modelParams,
    showThinkSwitch: true,
    isLlm: true,
    selectedModel: {},
    outputs: {
      updatedParam: ($event: IModelParam) => {
        this.modelParams = { ...$event };
        this.showModelSetRef = false;
        this.modelSettingsRef.hide();
        this.onSave();
      },
    },
  };

  public noneObjDataTypes = getNoneObjOutputParamTypes();

  public isSimpleType = NodeUtils.isSimpleType;

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public addChild(param: IWFView) {
    const child = {
      ...getInitOutputParamConfig(),
      depth: param.depth + 1,
      parentType: param.type,
      isLeaf: true,
      key: `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    };
    if (param?.children) {
      param.children = [...param.children, child];
    } else {
      param.children = [child];
    }
    param.isLeaf = false;
    param.expanded = true;
    this.refreshRootArray(this.midParams, param);
    this.refreshRootArray(this.fetchParams, param);
    if (this.findParentArr(param) === 'domainObjectsParams') {
      const idx = this.domainObjectsParams.findIndex((o) => this.isNodeInTree(o, param) || o === param);
      if (idx > -1) {
        this.domainObjectsParams[idx] = { ...this.domainObjectsParams[idx], children: [...(this.domainObjectsParams[idx].children ?? [])] };
        if (this.domainObjectsParams[idx].processing_workflows) {
          this.domainObjectsParams[idx].processing_workflows = [...this.domainObjectsParams[idx].processing_workflows];
        }
      }
      this.domainObjectsParams = this.updateImmutablePath(this.domainObjectsParams, param);
    }
    this.cdr.detectChanges();
    this.onSave();
  }

  public addChildForFetch(param: IWFView) {
    const child = {
      ...getInitOutputParamConfig(),
      depth: param.depth + 1,
      parentType: param.type,
      isLeaf: true,
      key: `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    };
    if (param?.children) {
      param.children = [...param.children, child];
    } else {
      param.children = [child];
    }
    param.isLeaf = false;
    param.expanded = true;
    this.fetchParams = this.updateImmutablePath(this.fetchParams, param);
    this.cdr.detectChanges();
    this.onSave();
  }

  private updateImmutablePath(rootArr: IWFView[], target: IWFView): IWFView[] {
    const path = this.getPathToNode(rootArr, target);
    if (!path.length) return rootArr;
    const result = [...rootArr];
    let current: IWFView[] = result;
    for (let i = 0; i < path.length; i++) {
      const idx = current.findIndex((n) => n === path[i]);
      if (idx === -1) break;
      const updated = i === path.length - 1
        ? { ...path[i] }
        : { ...path[i], children: [...(path[i].children ?? [])] };
      current[idx] = updated;
      current = (updated.children ?? []) as IWFView[];
    }
    return result;
  }

  private getPathToNode(nodes: IWFView[], target: IWFView, path: IWFView[] = []): IWFView[] {
    for (const node of nodes) {
      if (node === target) return [...path, node];
      if (node.children) {
        const result = this.getPathToNode(node.children, target, [...path, node]);
        if (result.length) return result;
      }
    }
    return [];
  }

  private refreshRootArray(rootArr: IWFView[], target: IWFView): void {
    const parentArr = this.findParentArr(target);
    if (parentArr === 'domainObjectsParams') {
      this.domainObjectsParams = this.updateImmutablePath(this.domainObjectsParams, target);
    } else if (parentArr === 'midParams') {
      this.midParams = this.updateImmutablePath(this.midParams, target);
    } else if (parentArr === 'fetchParams') {
      this.fetchParams = this.updateImmutablePath(this.fetchParams, target);
    }
  }

  private findParentArr(param: IWFView): string | null {
    if (this.isNodeInTreeArr(this.midParams, param)) {
      return 'midParams';
    }
    if (this.isNodeInTreeArr(this.fetchParams, param)) {
      return 'fetchParams';
    }
    if (this.isNodeInTreeArr(this.domainObjectsParams, param)) {
      return 'domainObjectsParams';
    }
    return null;
  }

  private isNodeInTreeArr(nodes: IWFView[], target: IWFView): boolean {
    for (const node of nodes) {
      if (this.isNodeInTree(node, target)) return true;
    }
    return false;
  }

  private isNodeInTree(node: IWFView, target: IWFView): boolean {
    if (node === target) return true;
    if (node.children) {
      for (const child of node.children) {
        if (this.isNodeInTree(child, target)) return true;
      }
    }
    return false;
  }

  override slimParamLableWidth = {
    name: '136px',
    desc: '92px',
    type: '106px',
  };

  override normalParamLableWidth = {
    name: '165px',
    desc: '152px',
    type: '150px',
  };

  public workspaceId = '';
  updateTimeout: any = null;

  constructor(
    private fb: FormBuilder,
    protected override appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private nzModal: NzModalService,
    protected override nodeServ: NodeService,
    protected agentDataServe: AgentDataService,
    private appFlowRepoServe: AppFlowRepoService,
    private appAgentRepoServe: AppAgentRepoService,
    private ngZone: NgZone,
    private nzMessage: NzMessageService,
    private http: HttpService,
    public commonService: CommonService,
    private configServ: AgentConfigService,
    private helpCenterService: HelpCenterService,
    private cdr: ChangeDetectorRef,
  ) {
    super(nodeServ, appFlowServ);
  }

  getInitOutputParamConfigPreDefined(): IWorkflowField {
    const config = getInitOutputParamConfig();
    return {
      ...config,
      source: 'pre_defined',
    };
  }

  onPreParamTypeChange(param) {
    NodeUtils.onOutputParamTypeChange(param);
    this.refreshRootArray(this.midParams, param);
    this.refreshRootArray(this.fetchParams, param);
    if (this.findParentArr(param) === 'domainObjectsParams') {
      const idx = this.domainObjectsParams.findIndex((o) => this.isNodeInTree(o, param) || o === param);
      if (idx > -1) {
        this.domainObjectsParams[idx] = { ...this.domainObjectsParams[idx], children: this.domainObjectsParams[idx].children ? [...this.domainObjectsParams[idx].children] : [] };
        if (this.domainObjectsParams[idx].processing_workflows) {
          this.domainObjectsParams[idx].processing_workflows = [...this.domainObjectsParams[idx].processing_workflows];
        }
      }
      this.domainObjectsParams = this.updateImmutablePath(this.domainObjectsParams, param);
    }
    this.cdr.detectChanges();
    this.onSave();
  }

  onInputValueTypeChange(row: nodeType.IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  override getLayerIndexWidth(param: nodeType.IWFView): string {
    return NodeUtils.getLayerIndexWidth(param, this.isNormalView, {
      widthArr: [165, 136],
    });
  }

  public override ngOnInit() {
    this.workspaceId = this.http.getWorkspaceId();
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.appFlowServ
      .resNodesUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((childFlowNodes) => {
        childFlowNodes.forEach((node) => {
          if (node.id === this.nodeBase.id) {
            if (!node.ref_workflows) {
              return;
            }
            const relationFlow = NodeUtils.getParamExtractionRelationFlow(
              this.nodeInfo,
            );
            relationFlow.forEach((r) => {
              const matchedFlow = node.ref_workflows?.find(
                (item) => item?.workflow_id === r.id,
              );
              if (
                matchedFlow &&
                matchedFlow.last_version_id &&
                (Number(matchedFlow.last_version_id) > Number(r.version_id) ||
                  !r.version_id)
              ) {
                r.showUpdate = true;
                r.last_version_id = matchedFlow.last_version_id;
                r.last_version_name = matchedFlow.last_version_name;
              } else {
                r.showUpdate = false;
                r.last_version_id = '';
              }
            });
          }
        });
      });
    this.nodeServ
      .refInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info) => {
        const requestVariables = this.appFlowServ.requestVariablesFn(info);
        const info_list = NodeUtils.refInfo2Tree(info);
        this.nameRefOptions = [...info_list, ...requestVariables];
        this.conditionOps = this.getFreshConditionOps();

        if (this.isInit) {
          this.midParams = this.getMidParams();
          if (this.midParams.length === 0) {
            this.addPreDefinedParam(this.midParams, this.nameRefOptions);
          }
          this.fetchParams = this.getFetchParams();
          this.domainObjectsParams = this.getDomainParams();
          if (this.domainObjectsParams.length === 0) {
            this.addDomainObjectsParam(
              this.domainObjectsParams,
              this.nameRefOptions,
            );
          }
          this.inputParams = this.getInputParams();
          this.updateConditionOps();
        } else {
          NodeUtils.reSelectRefsWithNewOps(this.midParams, this.nameRefOptions);
          NodeUtils.reSelectRefsWithNewOps(
            this.fetchParams,
            this.nameRefOptions,
          );
          NodeUtils.reSelectRefsWithNewOps(
            this.domainObjectsParams,
            this.nameRefOptions,
          );
          NodeUtils.reSelectRefsWithNewOps(
            this.inputParams,
            this.nameRefOptions,
          );
          this.updateConditionOps();
        }

        this.isInit = false;
      });

    this.onRefSubscribe(this.onRefUpdate.bind(this));

    this.validationRules.push(
      CommonValidation.nameUniquenessVerify(
        this.names,
        this.i18n.transform('name_uniqueness'),
        this.nodeInfo?.name,
      ),
    );

    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((models) => {
        this.modelOptions = models ?? []; // 接收新的模型列表
      });

    this.modelFormGroup.setValue({
      model: this.nodeInfo.configs?.model?.model_deployment_id ?? '',
    });

    this.prompt = this.nodeInfo.configs.prompt;

    NodeUtils.checkModelExistence(
      this.nodeInfo.name,
      this.nodeInfo.configs?.model?.model_deployment_id ?? '',
      this.modelOptions,
    );

    this.modelSetTipCtx.selectedModel = this.modelOptions.find(
      (model) =>
        model.model_deployment_id === this.modelFormGroup.get('model').value,
    );
    //初始化工作流
    this.getFlows();

    this.modelFormGroup.get('model').valueChanges.subscribe((value) => {
      const selectedModel = this.modelOptions.find(
        (model) => model.model_deployment_id === value,
      );
      this.modelSetTipCtx.selectedModel = selectedModel;
      this.agentDataServe.setPromptAndModelConfig({
        modelConfig: selectedModel,
      });
    });

    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.nodeInfo.configs?.model,
    });

    const config = cloneDeep(this.nodeInfo.configs);
    if (config) {
      if (config.domain_objects?.length) {
        this.domainObjectsParams.forEach((o) => {
          config.domain_objects.forEach((o2) => {
            if (o2.name === o.name) {
              o.processing_workflows = o2.processing_workflows;
            }
          });
        });
      }
      this.enable_intent_break = config.enable_intent_break ?? true;
      this.intent_break_prompt = config.intent_break_prompt ?? '';
      this.extension_workflows = config.extension_workflows ?? [];
      this.description = config.description ?? '';
      if (config.entry_condition) {
        this.entry_condition = config.entry_condition;
        this.openConditionConfig = true;
      }
      if (config.break_condition) {
        this.break_condition = config.break_condition;
        this.openConditionConfig = true;
      }
      if (config.exception_config) {
        this.exception_config = config.exception_config;
        this.openConditionConfig = true;
      }
      // 初始化模型参数信息
      const {
        top_p = 0.5,
        temperature = 0.5,
        history_size = 3,
        max_tokens = 2048,
        frequency_penalty = 0,
      } = this.nodeInfo.configs;
      this.modelParams = {
        top_p,
        temperature,
        history_size,
        max_tokens,
        frequency_penalty,
      };
    }
  }

  public drop(flowList: IProcessingWorkflow[], e: any) {
    moveItemInArray(flowList, e.previousIndex, e.currentIndex);
  }

  override ngOnDestroy(): void {
    this.helpCenterService.hideHelpPanel();
    this.modelCloseSave();
    if (this.modelListSubscription) {
      this.modelListSubscription.unsubscribe();
    }

    this.destroy$.next();
    this.destroy$.complete();
  }

  public onRefUpdate(info: nodeType.IParamRef[]) {
    this.nameRefOptions = info;
    if (this.isInit) {
      this.inputParams = this.getInputParams();
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.isInit = false;
  }

  isModelReachedParamLimit() {
    return this.isReachedParamLimit([...this.inputParams]);
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSave();
  }

  /** 点击展示模型配置的Tip弹窗 */
  public onShowModelSetTip() {
    if (!this.showModelSetRef) {
      this.showModelSetRef = true;
      this.modelSetTipCtx.param = this.modelParams;
      window.setTimeout(() => {
        this.modelSettingsRef.show();
      });
    } else {
      this.showModelSetRef = false;
      this.modelSettingsRef.hide();
    }
  }

  dismiss(): void {}

  close(): void {}

  getDtoInputs(params: IWorkflowField[]): IWorkflowField[] {
    const paramCopy = cloneDeep(params);
    paramCopy.forEach((param) => {
      if (param.value.type === 'ref') {
        const contentArr = (param.value.content as IParamRef[])?.[0];
        if (contentArr) {
          const { ref_node_id, ref_var_name, source, schema, type } =
            contentArr;
          param.value.content = {
            ref_node_id,
            ref_var_name,
            source,
          };
        }
      }
      if (
        param.value.type === 'literal' &&
        typeof param.value.content === 'string'
      ) {
        param.value.content = removeHTMLTag(param.value.content);
      }

      delete param?.refs;
    });

    return paramCopy;
  }

  onPromptChange() {
    this.promptInvalid = !this.prompt;
    this.onSave();
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  validateNode() {
    this.inputForm?.form?.markAllAsTouched();
    this.domainForm?.form?.markAllAsTouched();
    this.midParamForm?.form?.markAllAsTouched();
    this.exFlowForm?.form?.markAllAsTouched();
    if (this.prompt) {
      this.promptInvalid = false;
    } else {
      this.promptInvalid = true;
    }

    this.showLlmSelectErrorClass = this.modelFormGroup.invalid;

    if (this.isLoadingFlowData) {
      this.isTriggeredConfirm = true;
    } else {
      this.isTriggeredConfirm = false;
    }
  }

  showLlmSelectError(): boolean {
    const modalErr = this.modelFormGroup.invalid;
    if (modalErr) {
      this.showLlmSelectErrorClass = true;
    } else {
      this.showLlmSelectErrorClass = false;
    }
    return this.showLlmSelectErrorClass;
  }

  views2FieldsMid2Output(
    views: IWFView[],
    ref_var_name?: string,
  ): IWorkflowField[] {
    const fields: IWorkflowField[] = views.map((view) => {
      let {
        name,
        type,
        description,
        required,
        children,
        aging_level,
        value,
        storage_method,
        parentType,
      } = view;
      if (ref_var_name) {
        value = {
          type: 'ref',
          content: {
            ref_node_id: this.nodeInfo.id,
            ref_var_name: `${ref_var_name}.${name}`,
            source: 'pre_defined',
          },
          hint: '',
        };
      }
      const field: IWorkflowField = {
        name,
        type,
        description,
        required,
        source: 'user',
        value,
      };

      if (aging_level && storage_method) {
        field.aging_level = aging_level;
        field.storage_method = storage_method;
      }

      if (type.startsWith('array<')) {
        field.type = 'array';
        const itemType = type?.match(/array<(.+)>/)[1];
        (field.schema as IWorkflowField) = {
          name: '',
          type: itemType as IWorkflowFieldType,
        };
        if (itemType === 'object') {
          (field.schema as IWorkflowField).schema =
            this.views2FieldsMid2Output(children);
        }
      }
      if (type === 'object' && (view as any).schema) {
        field.schema = this.views2FieldsMid2Output((view as any).schema);
      }
      if (type === 'object' && children) {
        field.schema = this.views2FieldsMid2Output(children);
      }
      return field;
    });

    return fields;
  }

  //处理工作流数据
  resetProcessingFlow() {
    const children = this.domainObjectsParams ?? [];
    return children.map((o) => {
      if (!o.processing_workflows) {
        o.processing_workflows = [];
      }
      let processing_workflows = o.processing_workflows.map((f) => {
        if (f.id && f.name) {
          return f;
        }
        return null;
      });
      processing_workflows = processing_workflows.filter((f) => {
        if (f) {
          if (!f.entry_condition?.conditions?.length) {
            f.entry_condition = null;
          }
          delete f?.isNewSelected;
          delete f?.canConfigure;
          return true;
        }
        return false;
      });
      return {
        name: o.name,
        description: o.description,
        processing_workflows: processing_workflows,
      };
    });
  }

  //处理工作流数据
  resetExtensionFlow() {
    const extension_workflows = this.extension_workflows.map((f) => {
      if (f.id && f.name) {
        return f;
      }
      return null;
    });

    this.extension_workflows = extension_workflows.filter((f) => {
      if (f) {
        if (!f.entry_condition?.conditions?.length) {
          f.entry_condition = null;
        }
        delete f?.isNewSelected;
        delete f?.canConfigure;
        return true;
      }
      return false;
    }) as IExtensionWorkflow[];
  }

  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.inputParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: [...names] };
  }

  onNameChange() {
    this.inputForm?.form?.markAsDirty();
  }

  onDomainNameChange() {
    this.domainForm?.form?.markAsDirty();
  }

  public openRefModal() {
    const myModal = this.nzModal.create({
      nzContent: RefPromptComponent,
      nzWidth: 1000,
      nzData: {
        select: (tmpl: ITmpl) => {
          this.prompt = tmpl.content;
          this.onSave();
          this.cdr.markForCheck();
        },
      },
    });
  }

  public subFlowOps: any[] = [];
  public subFlowSelectOps: { label: string; value: string }[] = [];

  compareWithValue = (o1: any, o2: any): boolean => o1 === o2;
  isLoadingFlowData = false;
  isTriggeredConfirm = false;
  public isLoadingFlows = false;
  public flowOps: nodeType.IControllerFlow[] = [];

  public executionTimingOptions = [
    {
      label: this.i18n.transform('paramextractionlogcomponent_390'),
      value: 'BEFORE_ENTRY',
    },
    {
      label: this.i18n.transform('paramextractionlogcomponent_392'),
      value: 'AFTER_EXTRACTION',
    },
    {
      label: this.i18n.transform('paramextractionlogcomponent_391'),
      value: 'AFTER_QUIT',
    },
  ];

  private fillFlowDetail(flow: any) {
    const matched = this.subFlowOps.find((f) => f.id === flow.id);
    if (matched) {
      flow.name = matched.name;
      flow.version = matched.version;
      flow.version_id = matched.version_id;
      flow.version_name = matched.version_name;
      flow.description = matched.description;
      flow.code = matched.code;
      flow.type = matched.type;
    }
  }

  private async loadFlowDetail(flow: any) {
    this.fillFlowDetail(flow);
    if (!flow.id || !flow.version) {
      return;
    }
    this.isLoadingFlowData = true;
    const f = await this.appFlowRepoServe.getFlowVersionInfo(
      flow.id,
      flow.version,
    );
    this.isLoadingFlowData = false;
    const { nodes } = f.workflow_details;
    const inputs: nodeType.IWorkflowField[] = (
      nodes.find((item) => item.type === 'Start') as nodeType.IStartNode
    ).outputs.filter(
      (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
    );
    inputs.forEach((item) => {
      const { default: defaultValue } = item.value;
      const content = isNil(defaultValue) ? '' : defaultValue;
      const value: nodeType.IWorkflowFieldValue = {
        content,
        hint: '',
        type: 'literal',
      };
      if (!isNil(defaultValue)) {
        value.default = defaultValue;
      }
      item.value = value;
    });
    const memory = f?.workflow_details?.configs?.memory || [];
    flow.name = f.name;
    flow.description = '';
    flow.version_name = flow.version_name;
    flow.version_id = flow.version;
    flow.inputs = inputs;
    flow.outputs = (
      nodes.find((item) => item.type === 'End') as nodeType.IEndNode
    ).outputs;
    flow.entry_condition = BranchUtils.getNewBranchBlankConfigs();
    flow.memory = memory;
    flow.canConfigure = true;
  }

  async onSelectProcessingFlow(flow: any, list: any[]) {
    await this.loadFlowDetail(flow);
    this.onSave();
  }

  addProcessingFlow(param: IWFViewP) {
    const initFlow = { id: '' } as any;
    if (param.processing_workflows) {
      param.processing_workflows.push(initFlow);
    } else {
      param.processing_workflows = [initFlow];
    }
    this.onSave();
  }

  deleteProcessingFlow(list: any[], i: number) {
    list.splice(i, 1);
    this.onSave();
  }

  async onSelectExtensionFlow(flow: any, list: any[]) {
    await this.loadFlowDetail(flow);
    this.onSave();
  }

  onSelectExtensionFlowTiming(execution_timing: any, flow: any) {
    if (!flow.id) {
      return;
    }
    flow.execution_timing = execution_timing;
    this.onSave();
  }

  addExtensionFlow(list: any[]) {
    list.push({ id: '' });
  }

  deleteExtensionFlow(list: any[], i: number) {
    list.splice(i, 1);
    this.onSave();
  }

  //配置工作流
  async configureProcessingFlow(flow: any, domainObjectName: string) {
    console.log(flow)
    if (!domainObjectName) {
      MessageComponent.showWarn(
        this.i18n.transform('paramextractionmodalcomponent_522'),
      );
      return;
    }
    if (!flow || !flow.id) {
      MessageComponent.showWarn(
        this.i18n?.transform('paramextractionmodalcomponent_523'),
      );
      return;
    }
    if (!flow.inputs) {
      try {
        await this.loadFlowDetail(flow);
      } catch {
        return;
      }
    }
    if (!flow.inputs) {
      return;
    }
    const modalRef =  this.nzModal.create<ConfigureWorkflowModalComponent>({
      nzTitle: '',
      nzContent: ConfigureWorkflowModalComponent,
      nzClassName: 'configure-workflow-modal',
      nzFooter: null,
      nzData: {
        flow: flow,
        conditionRefOptions: this.conditionOps,
        domainObjectName: domainObjectName,
        nodeInfo: this.nodeInfo,
      },
      nzOnOk: () => {
        console.log(111111111)
      },
    } as any);

    const instance = modalRef.getContentComponent();
    instance.confirm.subscribe(() => {
      this.onSave();
    });
  }

  viewProcessingFlow(flow: any, domainObjectName: string) {
    if (!flow.id) {
      return;
    }
    let target = flow;
    if (!target) {
      MessageComponent.showWarn(
        this.i18n.transform('paramextractionmodalcomponent_523'),
      );
      return;
    }
    const prefixUrl = window.location.href?.split('/home')[0];
    const queryParams = `?id=${target.id}&versionId=${target.version_id}&workspace_id=${this.workspaceId}`;

    const newUrl = `${prefixUrl}/home/agent-center/app-flow/flow${queryParams}`;
    window.open(newUrl, '_blank');
  }

  async configureExtensionFlow(flow: any) {
    if (!flow || !flow.id) {
      return;
    }
    if (!flow.inputs) {
      try {
        await this.loadFlowDetail(flow);
      } catch {
        return;
      }
    }
    if (!flow.inputs) {
      return;
    }
    if (!flow.inputs) {
      await this.loadFlowDetail(flow);
    }
    if (!flow.inputs) {
      return;
    }
    this.nzModal.create<ConfigureWorkflowModalComponent>({
      nzTitle: '',
      nzContent: ConfigureWorkflowModalComponent,
      nzClassName: 'configure-workflow-modal',
      nzFooter: null,
      nzData: {
        flow: flow,
        nodeInfo: this.nodeInfo,
        conditionRefOptions: this.conditionOps,
      },
    } as any);
  }

  viewExtensionFlow(flow: any) {
    if (!flow.id) {
      return;
    }
    let target = flow;
    const prefixUrl = window.location.href?.split('/home')[0];
    const queryParams = `?id=${target.id}&versionId=${target.version_id}`;

    const newUrl = `${prefixUrl}/home/agent-center/app-flow/flow${queryParams}`;
    window.open(newUrl, '_blank');
  }

  public openUpdateFlowModal(flow, domainObjectName?: string) {
    if (!(flow && flow.showUpdate && flow.last_version_id)) {
      return;
    }
    this.ngZone.run(() => {
      this.nzModal.confirm({
        nzTitle: this.i18n.transform('update_flow_modal_title'),
        nzContent: flow?.version_name
          ? this.i18n.transform('update_flow_modal_content', {
              versionName: flow.version_name,
              latestVersionName: flow?.last_version_name,
            })
          : this.i18n.transform('paramextractionmodalcomponent_526', {
              last_version_name: flow?.last_version_name,
            }),
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOnOk: async () => {
          const childFlowInfo =
            await this.appAgentRepoServe.rollbackFlowVersion(
              flow?.id,
              flow?.last_version_id,
            );
          const startNode = childFlowInfo?.workflow_details?.nodes?.filter(
            (node) => node.type === 'Start',
          );
          const endNode = childFlowInfo?.workflow_details?.nodes?.filter(
            (node) => node.type === 'End',
          );
          const oldInputs: any[] = [];
          let oldMemoryInput: any = null;

          flow?.inputs?.forEach((i) => {
            if (i.name === 'memory') {
              oldMemoryInput = i;
            } else {
              oldInputs.push(i);
            }
          });
          const newInputs = startNode?.[0]?.outputs?.filter(
            (item) =>
              !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
          );
          const newMemory =
            childFlowInfo?.workflow_details?.configs?.memory || [];
          const newOutputs = endNode?.[0]?.outputs;
          const updatedInputs = this.fillPreviousInputs(newInputs, oldInputs);
          const updatedMemory = this.fillPreviousMemoryInputs(
            newMemory,
            oldMemoryInput,
          );
          flow.inputs = [...updatedInputs, updatedMemory];
          flow.outputs = newOutputs;
          flow.memory = newMemory;
          flow.name = childFlowInfo.name;
          flow.version_id = flow.last_version_id;
          flow.version_name = flow.last_version_name;
          flow.showUpdate = false;
          MessageComponent.showSuccess(
            this.i18n.transform('paramextractionmodalcomponent_524'),
          );
          if (domainObjectName) {
            this.configureProcessingFlow(flow, domainObjectName);
          } else {
            this.configureExtensionFlow(flow);
          }
          this.onSave();
        },
      });
    });
  }

  private fillPreviousInputs(
    newIputs: IWorkflowField[],
    oldInputs: IWorkflowField[],
  ) {
    return newIputs
      ?.map((item) => {
        const matchingItem = oldInputs?.find(
          (inputItem) =>
            inputItem.name === item?.name && inputItem.type === item?.type,
        );
        item.value.type = 'ref';
        return matchingItem ?? item;
      })
      .filter((input) => input.name !== 'sys');
  }

  /** 回填上一次更新版本前，同名且同类型的开始节点输出变量值 */
  private fillPreviousMemoryInputs(newInputs: IWorkflowField[], oldInput: any) {
    const inputs = newInputs?.map((item) => {
      const matchingItem = oldInput?.schema?.find(
        (inputItem) =>
          inputItem.name === item.name && inputItem.type === item.type,
      );
      return matchingItem ?? item;
    });
    return {
      name: 'memory',
      type: 'object',
      description: this.i18n.transform('memory_variable'),
      source: 'pre_defined',
      required: true,
      schema: inputs,
      reflection: false,
      value: {
        type: 'nested',
        content: null,
        hint: '',
        default: '',
      },
    };
  }

  async getFlows() {
    try {
      this.isLoadingFlows = true;

      const data = await this.appFlowRepoServe.getPublishedFlows({
        offset: 0,
        limit: 2000,
      });

      if (this.commonService.isSite()) {
        const _workflow_version_list =
          data?.workflow_version_list.map((w) => ({
            node_id: '',
            id: w.workflow_id,
            name: w.name,
            type: 'Normal',
            description: w.description,
            version: w.version_id,
            version_id: w.version_id,
            version_name: w.version_name,
            code: w.code,
          })) ?? [];

        const params = {
          offset: 0,
          limit: 1000,
          keyword: '',
          resource_type: 'workflow',
        };
        const share_data: any = await this.appFlowRepoServe.getShareFlows(
          params,
        );
        const resource_list = share_data?.resource_list.map((item) => {
          return {
            node_id: '',
            id: item.resource_id,
            name: item.resource_name_ch,
            type: 'Normal',
            description: item.resource_desc,
            version: item.version_info_list[0]?.version_id ?? '',
            version_id: item.version_info_list[0]?.version_id ?? '',
            version_name: item.version_info_list[0]?.version_name ?? '',
            code: item.resource_name_en,
          };
        });
        this.flowOps = [...resource_list, ..._workflow_version_list];
      } else {
        this.flowOps =
          data?.workflow_version_list.map((w) => ({
            node_id: '',
            id: w.workflow_id,
            name: w.name,
            type: 'Normal',
            version: w.version_id,
            version_id: w.version_id,
            version_name: w.version_name,
            description: w.description,
            code: w.code,
          })) ?? [];
      }

      this.subFlowOps = this.flowOps;
      this.subFlowSelectOps = this.flowOps.map((f) => ({
        label: f.name,
        value: f.id,
      }));
      this.cdr.detectChanges();
    } finally {
      this.isLoadingFlows = false;
    }
  }

  async onSelectFlow(flow: any, target: any) {
    target.isNewSelected = true;
    this.isLoadingFlowData = true;
    const f = await this.appFlowRepoServe.getFlowVersionInfo(
      flow.id,
      flow.version,
    );

    this.isLoadingFlowData = false;

    const { id, nodes } = f.workflow_details;

    const inputs: nodeType.IWorkflowField[] = (
      nodes.find((item) => item.type === 'Start') as nodeType.IStartNode
    ).outputs.filter(
      (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
    );
    inputs.forEach((item) => {
      const { default: defaultValue } = item.value;
      const content = isNil(defaultValue) ? '' : defaultValue;
      const value: nodeType.IWorkflowFieldValue = {
        content,
        hint: '',
        type: 'literal',
      };

      if (!isNil(defaultValue)) {
        value.default = defaultValue;
      }

      item.value = value;
    });

    const memory = f?.workflow_details?.configs?.memory || [];
    target.name = f.name;
    target.description = '';
    target.version_name = flow.version_name;
    target.version_id = flow.version;
    target.inputs = inputs;
    target.outputs = (
      nodes.find((item) => item.type === 'End') as nodeType.IEndNode
    ).outputs;
    target.entry_condition = BranchUtils.getNewBranchBlankConfigs();
    target.memory = memory;
    target.canConfigure = true;
    this.onSave();
  }

  public onIntelligentAdd(role) {
    if (this.isFlowReadonly) return;
    if (!this.prompt) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
        instruct: this?.prompt,
        isWorkflow: true,
        tipsChange: value => {
          this.prompt = value ?? '';
          this.onSave();
          this.cdr.markForCheck();
        },
      },
    });

  }

  public updateModel(modelInfo: any) {
    this.modelFormGroup?.controls?.model?.setValue(modelInfo.id);
    this.onSave();
  }

  public onModelSettingsUpdate(param: any) {
    this.modelParams = { ...param };
    this.showModelSetRef = false;
    this.onSave();
  }

  getNames(
    arr: IWorkflowField[],
    index: number,
  ): {
    existingValues: string[];
  } {
    const names = arr.map((p) => p.name);
    names?.splice(index, 1);
    return { existingValues: names };
  }

  getSiblingNames(rootArr: IWFView[], origin: IWFView): {
    existingValues: string[];
  } {
    if (origin.depth === 0) {
      const names = rootArr.map((p) => p.name);
      const idx = rootArr.indexOf(origin);
      if (idx > -1) names.splice(idx, 1);
      return { existingValues: names };
    }
    const parent = this.getParentNodeFromTree(rootArr, origin);
    if (parent?.children) {
      const names = parent.children.map((p) => p.name);
      const idx = parent.children.indexOf(origin);
      if (idx > -1) names.splice(idx, 1);
      return { existingValues: names };
    }
    return { existingValues: [] };
  }

  public updateConditionOps() {
    this.conditionOps = this.getFreshConditionOps();
  }

  private getFreshConditionOps() {
    return [
      ...cloneDeep(this.nameRefOptions),
      this.getParamExtractionRefs(this.nodeInfo),
    ];
  }

  protected getParamExtractionRefs(
    nodeInfo: IParamExtractionNode,
    configs?: IRef2TreeConfig,
  ) {
    if (nodeInfo && nodeInfo.type === 'ParamExtraction') {
      const loopRef = this.getEmptyParamExtractionRef(
        nodeInfo.id,
        nodeInfo.name,
      );

      // input refs
      const inputRefs = this.getParamExtractionMidVarRefs(
        nodeInfo,
        this.inputParams,
        'input',
        configs,
      );
      if (inputRefs.length) {
        loopRef.children.push(...cloneDeep(inputRefs));
      }

      // mid refs
      const midRefs = this.getParamExtractionMidVarRefs(
        nodeInfo,
        this.midParams,
        'intermediate_loop_var',
        configs,
      );
      if (midRefs.length) {
        loopRef.children.push(...cloneDeep(midRefs));
      }
      // mid refs
      const domainRefs = this.getParamExtractionMidVarRefs(
        nodeInfo,
        this.domainObjectsParams,
        'domain_objects',
        configs,
      );
      if (domainRefs.length) {
        loopRef.children.push(...cloneDeep(domainRefs));
      }

      // mid refs
      const modelOutRefs = this.getParamExtractionMidVarRefs(
        nodeInfo,
        this.fetchParams,
        'model_output_var',
        configs,
      );
      if (modelOutRefs.length) {
        loopRef.children.push(...cloneDeep(modelOutRefs));
      }

      return loopRef;
    }

    return null;
  }

  public getParamExtractionMidVarRefs(
    nodeInfo: IParamExtractionNode,
    params: IWFViewP[],
    name: string,
    configs?: IRef2TreeConfig,
  ) {
    if (nodeInfo && nodeInfo.type === 'ParamExtraction') {
      let mid: nodeType.IWorkflowField[];
      if (name === 'input') {
        mid = params;
      } else {
        mid = NodeUtils.views2Fields(params);
      }

      if (mid) {
        const midCopy = cloneDeep(mid);
        const midRef = this.getEmptyParamExtractionRef(
          nodeInfo.id,
          nodeInfo.name,
        );
        let intermediateObjRefs: nodeType.IParamRef[];
        if (name === 'input') {
          intermediateObjRefs = this.fields2RefParams(
            midCopy,
            midRef.ref_node_id,
            [],
            configs,
          );
        } else {
          intermediateObjRefs = this.fields2RefParams(
            midCopy,
            midRef.ref_node_id,
            [name],
            configs,
          );
        }

        return intermediateObjRefs;
      }
    }

    return [];
  }

  fields2RefParams(
    fields: IWorkflowField[],
    nodeId: string,
    preNames: string[] = [],
    configs: IRef2TreeConfig = {
      disableObj: false,
      disableArr: false,
      simpleArrRefFirst: false,
      strOnly: false,
      arrOnly: false,
      intOnly: false,
      appendName: '',
      refRootArrItem: false,
    },
  ) {
    const refs: IParamRef[] = fields.map((field) => {
      const { name, type, schema, source } = field;
      const names = [...preNames, name];

      const ref: IParamRef = {
        name,
        type: type ?? 'string',
        source: 'pre_defined',
        ref_node_id: nodeId,
        ref_var_name: names.join('.'),
        isTop: false,
      };

      if (type === 'array') {
        ref.schema = schema;

        if (configs?.refRootArrItem) {
          configs.refRootArrItem = false;
        } else {
          const lastIndex = names.length - 1;
          const last = names[lastIndex];
          names[lastIndex] = `${last}[0]`;
        }

        if ((schema as IWorkflowField)?.type === 'object') {
          ref.type = 'array<object>';

          ref.children = this.fields2RefParams(
            ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
            nodeId,
            names,
            configs,
          );
          ref.expanded = true;
        } else {
          ref.type = `array<${
            (schema as IWorkflowField)?.type
          }>` as IWorkflowFieldType;

          if (configs.simpleArrRefFirst) {
            ref.ref_var_name = names.join('.');
          }
        }
      }

      if (type === 'object') {
        ref.schema = schema;
        ref.children = this.fields2RefParams(
          (schema ?? []) as IWorkflowField[],
          nodeId,
          names,
          configs,
        );
        ref.expanded = true;

        if (configs.disableObj) {
          ref.disabled = true;
        }
      }

      if (configs?.intOnly && ref.type !== 'integer') {
        ref.disabled = true;
      }

      if (configs?.strOnly && ref.type !== 'string') {
        ref.disabled = true;
      }

      if (configs?.arrOnly && !ref.type.startsWith('array')) {
        ref.disabled = true;
      }

      if (configs?.disableArr && ref.type.startsWith('array')) {
        ref.disabled = true;
      }

      if (configs?.appendName) {
        ref.ref_var_name = `${ref.ref_var_name}.${configs.appendName}`;
      }

      if (ref.ref_node_id === 'node_start' && ref.name === 'sys') {
        ref.disabled = true;
      }

      return ref;
    });

    return refs;
  }

  protected getEmptyParamExtractionRef(
    loopId: string,
    loopName: string,
  ): IParamRef {
    return {
      ref_node_id: loopId,
      ref_var_name: '',
      name: loopName,
      isTop: true,
      type: 'ParamExtraction',
      source: 'user',
      expanded: true,
      children: [],
    };
  }

  onMidRefChange() {
    this.updateConditionOps();
    this.onSave();
  }

  midChooseTemplate() {
    const modalRef = this.nzModal.create<ObjectTemplateComponent>({
      nzContent: ObjectTemplateComponent,
      nzClassName: 'modal-custom900-class',
      nzFooter: null,
      nzTitle: this.i18n.transform('object_template'),
      nzData: {
        templatesSelected: (data) => {
          this.midParams = [
            ...this.midParams,
            ...FlowUtils.objectTempIWFields2Views(data),
          ];
          modalRef.close();
          this.onMidNameChange();
          this.onSave();
        },
      },
    });
  }

  domainObjectChooseTemplate() {
    const modalRef = this.nzModal.create<ObjectTemplateComponent>({
      nzContent: ObjectTemplateComponent,
      nzClassName: 'modal-custom900-class',
      nzFooter: null,
      nzTitle: this.i18n.transform('object_template'),
      nzData: {
        templatesSelected: (data) => {
          this.domainObjectsParams = [
            ...this.domainObjectsParams,
            ...FlowUtils.objectTempIWFields2Views(data),
          ];
          modalRef.close();
          this.onDomainNameChange();
          this.onSave();
        },
      },
    });
  }

  public addPreDefinedParam(arr: IWFView[], ops: IParamRef[]) {
    arr.push({
      ...getInitGeneratedInputParamConfig(),
      source: 'pre_defined',
      refs: cloneDeep(ops),
      type: 'string',
      depth: 0,
      parentType: 'none',
      key: `root_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    });
    if (arr === this.midParams) {
      this.midParams = [...this.midParams];
    } else if (arr === this.fetchParams) {
      this.fetchParams = [...this.fetchParams];
    }
    this.onSave();
  }

  public addDomainObjectsParam(arr: IWFViewP[], ops: IParamRef[]) {
    const rootKey = `root_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const childKey = `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    arr.push({
      ...getInitGeneratedInputParamConfig(),
      source: 'pre_defined',
      refs: cloneDeep(ops),
      type: 'object',
      depth: 0,
      parentType: 'none',
      expanded: true,
      key: rootKey,
      children: [
        {
          ...getInitGeneratedInputParamConfig(),
          source: 'pre_defined',
          refs: cloneDeep(ops),
          type: 'string',
          depth: 1,
          parentType: 'object',
          key: childKey,
        },
      ],
      processing_workflows: [],
    });
    this.domainObjectsParams = [...this.domainObjectsParams];
    this.onSave();
  }

  onMidNameChange() {
    this.midParamForm?.form?.markAsDirty();
  }

  onFetchNameChange() {
    this.fetchParamForm?.form?.markAsDirty();
  }

  public onDeleteParam(param: IWFView, paramView) {
    if (paramView === this.midParams) {
      this.midParams = this.removeNodeImmutable(this.midParams, param);
    } else if (paramView === this.fetchParams) {
      this.fetchParams = this.removeNodeImmutable(this.fetchParams, param);
    } else {
      this.domainObjectsParams = this.domainObjectsParams.map((o) => {
        if (this.isNodeInTree(o, param) || o === param) {
          const removed = this.removeNodeImmutable([o], param);
          const updated = removed.length > 0 ? removed[0] : null;
          if (updated && this.isObjectLikeType(updated.type) && updated.children?.length === 0) {
            updated.children = [];
          }
          return updated as IWFViewP;
        }
        return o;
      }).filter((o): o is IWFViewP => o !== null);
    }

    this.cdr.detectChanges();
    this.updateConditionOps();
    this.onSave();
  }

  private removeNodeImmutable(nodes: IWFView[], target: IWFView): IWFView[] {
    let changed = false;
    const result = nodes.map((n) => {
      if (n === target) {
        changed = true;
        return null;
      }
      if (n.children) {
        const newChildren = this.removeNodeImmutable(n.children, target);
        if (newChildren !== n.children) {
          changed = true;
          return { ...n, children: newChildren };
        }
      }
      return n;
    }).filter((n): n is IWFView => n !== null);
    return changed ? result : nodes;
  }

  private removeNodeFromTree(nodes: any[], target: any): boolean {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) {
        nodes.splice(i, 1);
        return true;
      }
      if (nodes[i].children && this.removeNodeFromTree(nodes[i].children, target)) {
        return true;
      }
    }
    return false;
  }

  private getParentNodeFromTree(nodes: any[], target: any, parent: any = null): any {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) {
        return parent;
      }
      if (nodes[i].children) {
        const result = this.getParentNodeFromTree(nodes[i].children, target, nodes[i]);
        if (result !== null) {
          return result;
        }
      }
    }
    return null;
  }

  public showDelete(param: IWFView, paramView) {
    if (param.source === 'system') {
      return false;
    }

    if (param.depth > 0) {
      const parentNode = this.getParentNodeFromTree(paramView, param);
      if (parentNode && parentNode.children.length === 0) {
        return false;
      }
    }

    return true;
  }

  public getMidParams(): IWFView[] {
    const currentParams = this.nodeInfo.inputs.find(
      (input) => input.name === 'intermediate_loop_var',
    );
    const schema = (currentParams?.schema as IWorkflowField[]) ?? [];
    return NodeUtils.fields2Views(schema);
  }

  public getFetchParams(): IWFView[] {
    const currentParams = this.nodeInfo.inputs.find(
      (input) => input.name === 'model_output_var',
    );
    const schema = (currentParams?.schema as IWorkflowField[]) ?? [];
    return NodeUtils.fields2Views(schema);
  }

  public getDomainParams(): IWFView[] {
    const currentParams = this.nodeInfo.inputs.find(
      (input) => input.name === 'domain_objects',
    );
    const schema = (currentParams?.schema as IWorkflowField[]) ?? [];
    return NodeUtils.fields2Views(schema);
  }

  public getInputParams(): IWorkflowField[] {
    const inputs = this.nodeInfo.inputs.filter(
      (input) =>
        input.name !== 'intermediate_loop_var' &&
        input.name !== 'domain_objects' &&
        input.name !== 'model_output_var',
    );

    if (inputs) {
      return NodeUtils.initInputs(inputs, this.nameRefOptions);
    }

    return [];
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

  get site() {
    return this.configServ.getConfigs().site;
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  handleNodeData(inputs, domain_objects, selectedModel) {
    let modelType = selectedModel?.model_type ?? ModelType.LLM;
    const nodeData: nodeType.IParamExtractionNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: inputs,
      outputs: this.outputParams,
      configs: {
        ...this.nodeInfo.configs,
        domain_objects: domain_objects,
        model: {
          ...(selectedModel?.model && { model: selectedModel.model }),
          model_id: selectedModel?.id ?? '',
          model_name: selectedModel?.model_name ?? '',
          model_type: modelType,
          model_deployment_id: selectedModel?.model_deployment_id ?? '',
          ...(selectedModel?.model && { model: selectedModel.model }),
        },
        ...this.modelParams,
        prompt: this.prompt,
        enable_intent_break: this.enable_intent_break,
        intent_break_prompt: this.intent_break_prompt,
        extension_workflows: this.extension_workflows,
        description: this.description,
      },
    };
    let entry_condition_temp = null;
    if (this.entryConditionModal?.entryCondition) {
      entry_condition_temp = BranchUtils.branchConfigsMapper(
        this.entryConditionModal?.entryCondition,
      );
    }
    let break_condition_temp = null;
    if (this.breakConditionModal?.entryCondition) {
      break_condition_temp = BranchUtils.branchConfigsMapper(
        this.breakConditionModal?.entryCondition,
      );
    }
    let exception_condition_temp = null;
    if (this.exceptionConditionModal?.entryCondition) {
      exception_condition_temp = BranchUtils.branchConfigsMapper(
        this.exceptionConditionModal?.entryCondition,
      );
    }

    if (entry_condition_temp?.conditions?.length) {
      nodeData.configs.entry_condition = entry_condition_temp;
    } else {
      nodeData.configs.entry_condition = null;
    }
    if (break_condition_temp?.conditions?.length) {
      nodeData.configs.break_condition = break_condition_temp;
    } else {
      nodeData.configs.break_condition = null;
    }
    if (exception_condition_temp?.conditions?.length) {
      nodeData.configs.exception_config = {
        max_iterations: 20,
        exception_condition: exception_condition_temp,
      };
    } else {
      nodeData.configs.exception_config = null;
    }
    return nodeData;
  }

  handelData() {
    const selectedModel = this.modelOptions.find(
      (model) =>
        model.model_deployment_id === this.modelFormGroup.controls.model.value,
    );
    this.outputParams = [];
    const inputs = NodeUtils.getDtoInputs(this.inputParams);
    if (this.midParams?.length) {
      let sc = NodeUtils.views2Fields(this.midParams);
      sc = this.getDtoInputs(sc);
      const value: any = {
        type: 'nested',
        hint: '',
        default: '',
        content: null,
      };
      inputs.push({
        name: 'intermediate_loop_var',
        type: 'object',
        description: this.i18n.transform('paramextractionlogcomponent_352'),
        required: true,
        source: 'pre_defined',
        value,
        schema: sc,
      });
      this.outputParams = [
        ...this.outputParams,
        ...this.views2FieldsMid2Output(this.midParams, 'intermediate_loop_var'),
      ];
    }

    let domain_objects = [];
    if (this.domainObjectsParams?.length) {
      const sc = NodeUtils.views2Fields(this.domainObjectsParams);
      inputs.push({
        name: 'domain_objects',
        type: 'object',
        description: this.i18n.transform('paramextractionlogcomponent_366'),
        source: 'pre_defined',
        required: true,
        value: {
          type: 'nested',
          hint: '',
          default: '',
          content: null,
        },
        schema: sc,
      });
      domain_objects = this.resetProcessingFlow();
      if (this.domainObjectsParams) {
        this.outputParams = [
          ...this.outputParams,
          ...this.views2FieldsMid2Output(
            this.domainObjectsParams,
            'domain_objects',
          ),
        ];
      }
    }

    if (this.fetchParams?.length) {
      const sc = NodeUtils.views2Fields(this.fetchParams);
      inputs.push({
        name: 'model_output_var',
        type: 'object',
        description: this.i18n.transform('paramextractionmodalcomponent_518'),
        required: true,
        source: 'pre_defined',
        value: {
          type: 'nested',
          content: null,
          hint: '',
          default: '',
        },
        schema: sc,
      });
    }
    this.resetExtensionFlow();
    const nodeData = this.handleNodeData(inputs, domain_objects, selectedModel);
    return nodeData;
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: this.handelData(),
    });
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    this.updateTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
