import { Component, ElementRef, EventEmitter, Input, OnInit, Output, TemplateRef, ViewChild } from '@angular/core';
import { FormBuilder, NgForm, Validators } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { ActivatedRoute } from '@angular/router';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';
import { HelpDocKey } from '@constants/support-topic.const';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { ExceptionHandlingComponent } from '@routes/agent-center/app-flow/components/exception-handling/exception-handling.component';
import { SwaggerTreeConvertService } from '@routes/agent-center/app-plugin/plugin-action-detail/swagger-tree-convert.service';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { EnvManagementService } from '@routes/platform-management/environment-management/env-management.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { CommonService } from '@services/common.service';
import { HelpCenterService } from '@services/help-center.service';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { HelpLinksService } from '@shared/services/help-links.service';
import { CommonValidation } from '@shared/validation/commonValidation';
import { cloneDeep } from 'lodash';
import { debounceTime, Subject, Subscription } from 'rxjs';
import { ParamLabelPipe } from 'src/pipes/param-label.pipe';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { CommonUtils } from 'src/utils/common.util';
import { AppFlowService } from '../../app-flow.service';
import {
  getInitInputParamConfig,
  getInitOutputParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  NODE_SAVE_DEBOUNCE_TIME,
  WORKFLOW_SVGS,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import type { ICodeNode, IParamRef, IWFView, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { NodeUtils } from '../utils';
import { NodeDescriptionComponent } from '../node-description/node-description.component';

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
  selector: 'meta-code-modal',
  templateUrl: './code-modal.component.html',
  styleUrls: ['./code-modal.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    MonacoEditorModule,
    AccBlockComponent,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    ParamLabelPipe,
    AddPropsIconComponent,
    RefSelectedRequireDirective,
    ParamTreeComponent,
    TypedJsonInputComponent,
    ExceptionHandlingComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
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
export class CodeModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: ICodeNode;

  @Output('confirm') confirm = new EventEmitter<ICodeNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('outputForm') outputForm: NgForm;

  @ViewChild('nameForm') nameForm: NgForm;

  @ViewChild('editorContainer', { static: false }) editorContainer: ElementRef;

  @ViewChild('exceptionHandling') exceptionHandling: ExceptionHandlingComponent;

  protected override destroy$ = new Subject<void>();

  public nameRefOptions: IParamRef[] = [];

  public expanded = false;

  fgId = '';

  editorOptions = {
    theme: 'vs',
    language: 'python',
    minimap: {
      enabled: false,
    },
    scrollbar: {
      horizontalScrollbarSize: 0,
      verticalScrollbarSize: 0,
      verticalSliderSize: 8,
      horizontalSliderSize: 8,
      useShadows: false,
    },
  };

  get site() {
    return this.configServ.getConfigs().site;
  }

  get codeOptions() {
    return this.configServ.getConfigs().code_env_options;
  }

  get codeDef() {
    return this.configServ.getConfigs().code_def_env;
  }
  get sandboxEnable() {
    return this.configServ.getConfigs().env_sandbox_enable;
  }

  @ViewChild('descriptionDom') descriptionDom: any;
  @ViewChild('actionDom') actionDom: any;

  get getParamWidth() {
    const width = this.descriptionDom?.nativeElement?.offsetWidth | 0;
    return `${width}px`;
  }
  get getActionWidth() {
    const width = this.actionDom?.nativeElement?.offsetWidth | 0;
    return `${width}px`;
  }

  public modelFormGroup = this.fb.group({
    code: ['', Validators.required],
  });

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public inputParams: IWorkflowField[] = [];

  public outputParams: IWFView[] = [];

  public outputDataTypes = getOutputParamTypes();

  public noneObjDataTypes = getNoneObjOutputParamTypes();

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public isSimpleType = NodeUtils.isSimpleType;

  public addChild = NodeUtils.addChild;

  public codeImgUrl = WORKFLOW_SVGS.Code;

  public validationRules: any[] = [];

  public orginRadioList: Array<{ label: string; value: string; tips?: string }> = [
    {
      label: this.i18n.transform('codemodalcomponent_280'),
      value: 'sandbox',
    },
    {
      label: 'FunctionGraph',
      value: 'fg',
    },
    {
      label: this.i18n.transform('codemodalcomponent_281'),
      value: 'local',
    },
  ];
  public radioList: Array<{ label: string; value: string; tips?: string }> = [];
  public radioList_tip: string[] = [];
  public isFgAuth: boolean = false;
  public projectId = '';

  public selectedExecutionMethod: string = 'sandbox';

  getEntrustList = [];
  public fgData: any = null;

  public selectFunctionGraphLable = this.i18n.transform('codemodalcomponent_282');

  formCode$: Subscription;
  public notOpenFunction: boolean = false;
  isFirstInit = 0;
  codeTimeout: any = null;

  constructor(
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private elementRef: ElementRef<HTMLDivElement>,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private appFlowRepoServ: AppFlowRepoService,
    private route: ActivatedRoute,
    private nzModal: NzModalService,
    private swaggerTreeConvertService: SwaggerTreeConvertService,
    private nzMessage: NzMessageService,
    public commonService: CommonService,
    private configServ: AgentConfigService,
    private environmentManagementService: EnvManagementService,
    private helpCenterService: HelpCenterService,
    private helpLinksService: HelpLinksService
  ) {
    super(nodeServ, appFlowServ);
  }

  onOutputParamTypeChange = NodeUtils.onOutputParamTypeChange;

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  public override async ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    const isCodeDef = this.nodeInfo?.configs && this.nodeInfo?.configs.enable_sandbox === false ? 'local' : this.codeDef;
    const isSandbox = this.nodeInfo?.configs && this.nodeInfo?.configs.enable_sandbox ? 'sandbox' : isCodeDef;
    this.selectedExecutionMethod = this.nodeInfo?.configs.exec_env ? this.nodeInfo?.configs.exec_env : isSandbox;
    super.ngOnInit();

    if (this.codeOptions?.length > 0) {
      this.codeOptions.forEach(item => {
        let radio = this.orginRadioList.filter(e => e.value === item);
        this.radioList = this.radioList.concat(radio);
        this.selectedExecutionMethod = this.selectedExecutionMethod ? this.selectedExecutionMethod : this.radioList[0].value;
      });
    } else if (this.codeOptions?.length === 0) {
      this.radioList = [];
      this.selectedExecutionMethod = '';
    } else {
      this.radioList = this.orginRadioList.slice(0, 2);
      this.selectedExecutionMethod = this.selectedExecutionMethod ? this.selectedExecutionMethod : this.radioList[0].value;
    }
    if (this.radioList && this.radioList.length > 0) {
      this.radioList = this.radioList.filter(e => this.configServ.getConfigs()?.studio_btn_show || e.value !== 'local');
      const hasItem = this.radioList.find(item => item.value === this.selectedExecutionMethod);
      if (!hasItem) {
        this.selectedExecutionMethod = this.radioList[0].value;
      }
    }

    this.radioList.forEach(item => {
      if (item.value === 'sandbox') {
        this.radioList_tip.push(this.i18n.transform('codemodalcomponent_283'));
      }
      if (item.value === 'fg') {
        this.radioList_tip.push(this.i18n.transform('codemodalcomponent_284'));
      }
      if (item.value === 'local') {
        this.radioList_tip.push(this.i18n.transform('codemodalcomponent_285'));
      }
    });

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

    this.outputParams = NodeUtils.fields2Views(this.nodeInfo.outputs);
    this.modelFormGroup.controls.code.setValue(this.nodeInfo.configs.code);

    this.formCode$ = this.modelFormGroup.valueChanges.pipe(debounceTime(NODE_SAVE_DEBOUNCE_TIME)).subscribe(value => {
      if (this.isFirstInit <= 0) {
        this.isFirstInit += 1;
        return;
      }
      this.onSave();
    });
    this.initFgItemTips();
  }

  initFgItemTips() {
    const fgItem = this.radioList.find(item => item.value === 'fg');
    if (fgItem && fgItem.tips) {
      fgItem.tips = this.helpLinksService.processHelpLinkTipWithI18n(this.i18n, 'codemodalcomponent_288', HelpDocKey.FG_GRANT_PERMISSION);
    }
  }

  ngAfterViewInit(): void {
    if (this.nodeInfo?.configs) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  refreshingDta() {
    this.outputParams = [...this.outputParams];
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
    this.helpCenterService.hideHelpPanel();
    this.modelCloseSave();
    this.destroy$.next();
    this.destroy$.complete();
    this.formCode$.unsubscribe();
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

  public addOutputParam() {
    this.outputParams.push({
      ...getInitOutputParamConfig(),
      depth: 0,
      parentType: 'none',
    });
    this.outputParams = [...this.outputParams];
    this.onSave();
  }

  public showDelete(param: IWFView) {
    if (param.source === 'system') {
      return false;
    }

    if (param.depth === 0 && this.outputParams.length === 1) {
      return false;
    }

    if (param.depth > 0) {
      const parentNode = getParentNodeFromTree(this.outputParams, param);
      if (parentNode && parentNode.children.length === 0) {
        return false;
      }
    }

    return true;
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSave();
  }

  dismiss(): void {}

  close(): void {}

  expandAllTreeNode(tree: IWFView[]) {
    tree.forEach(item => {
      item.expanded = true;
      if (item.children && item.children.length > 0) {
        this.expandAllTreeNode(item.children);
      }
    });
  }

  validateNode() {
    if (!this.exceptionHandling.validate()) {
      return;
    }
    if (this.selectedExecutionMethod === 'sandbox' || this.selectedExecutionMethod === 'local' || this.selectedExecutionMethod === '') {
      if (this.inputForm.invalid || this.outputForm.invalid) {
        return;
      }
    }

    if (CommonUtils.checkAndFocusFirstError(this.elementRef, this.modelFormGroup)) {
      this.nzMessage.error(this.i18n.transform('code_cant_empty_tip'));
      return;
    }
  }

  expandWindow(e: Event) {
    e.stopPropagation();
    this.expanded = true;
  }

  collapseWindow(e: Event) {
    e.stopPropagation();
    this.expanded = false;
  }

  getOutputNames(param: IWFView): {
    existingValues: string[];
  } {
    let outputNames = [];
    if (param.depth === 0) {
      outputNames = this.outputParams.map(arg => arg.name);
    } else {
      const parentNode = getParentNodeFromTree(this.outputParams, param);
      outputNames = parentNode?.children.map(arg => arg.name);
    }

    outputNames.splice(outputNames.indexOf(param.name), 1);
    return { existingValues: outputNames };
  }

  onNameChange() {}

  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.inputParams.map(p => p.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  onoutputNameChange() {}

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }

  public getFGAuth() {
    this.appFlowRepoServ.getAuth().then(res => {
      this.isFgAuth = res?.data === 'all';
    });
  }

  public doFGAuth() {}

  public showAuthModal(content: TemplateRef<any>): void {
    this.nzModal.create({
      nzTitle: this.i18n.transform('codemodalcomponent_276'),
      nzContent: content,
      nzOkText: this.i18n.transform('codemodalcomponent_279'),
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        this.doFGAuth();
      },
    });
  }

  radiomodeChange(event) {
    this.selectedExecutionMethod = event;
    if (this.inputParams.length < 1) {
      this.addInputParam();
    }
    if (this.outputParams.length < 1) {
      this.addOutputParam();
    }
    this.changeUpdateTime();
    this.handelSave();
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const inputs = NodeUtils.getDtoInputs(this.inputParams);

    const outputs = NodeUtils.views2Fields(this.outputParams);

    const nodeData: ICodeNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: inputs,
      outputs: outputs,
      configs: {
        ...this.nodeInfo.configs,
        code: this.modelFormGroup.controls.code.value,
        exec_env: this.selectedExecutionMethod ? this.selectedExecutionMethod : '',
      },
    };

    if (this.selectedExecutionMethod === '') {
      delete nodeData.configs.exec_env;
    }

    this.appFlowServ.setNodeSaveMonitor({
      nodeData,
    });
    if (this.codeTimeout) {
      clearTimeout(this.codeTimeout);
      this.codeTimeout = null;
    }
    this.codeTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  editCodeFun(data) {
    this.editCodeEvent.emit(true);
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  onClickDebuggerTest() {
    const hasDom = document.getElementsByTagName('function-graph-code');
    if (hasDom && hasDom.length > 0) {
      setTimeout(() => {
        this.editCodeEvent.emit(true);
      }, 2100);
    }
    this.onClickTest();
  }

  setTipStatus(event) {
    this.notOpenFunction = event;
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  onSave() {
    this.changeUpdateTime();
    this.editCodeEvent.emit(false);
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
