import { Component, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, NgForm, Validators } from '@angular/forms';
import { NzModalService, NzModalRef } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzTooltipDirective } from 'ng-zorro-antd/tooltip';
import { I18nNamespace } from '@i18n';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { type IModelParam, modelSettingsComponent } from '@shared/components/model-settings-tip';
import { NonEmptyValidatorDirective, ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { BehaviorSubject, Subscription, takeUntil } from 'rxjs';
import { ParamLabelPipe } from 'src/pipes/param-label.pipe';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import type { IModel } from '../../app-flow.types';
import { getInitInputParamConfig } from '../../flow.const';
import { NodeService } from '../../node.service';
import { type IAgentRepo, IParamRef, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPluginHalfmodalComponent } from '../add-plugin-halfmodal/add-plugin-halfmodal.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { ReadonlyParamsTreeComponent } from '../readonly-params/readonly-params-tree.component';
import { NodeUtils } from '../utils';
import { CmdTextareaComponent } from '../cmd-textarea/cmd-textarea.component';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { ITmpl } from '@services/prompt.service';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import { AssetIntelligentAddDisabledComponent } from '@shared/components/assets/asset-intelligent-add-disabled/asset-intelligent-add-disabled.component';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { SaveTmplLibraryModalComponent } from '../../../../prompt/prompt-candidate-template/save-tmpl-library-modal/save-tmpl-library-modal.component';
import moment from 'moment';
import { ActivatedRoute } from '@angular/router';
import { GETVARIANT_REG } from '@constants/exp-tmpl-config.const';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { reqSchemaStr2Field, resSchemaStr2Field } from '@routes/agent-center/app-plugin/utils';
import { IRefInfo } from '../../app-flow.types';
import { IPluginParamConf, PluginConfigModalComponent } from '@routes/agent-center/app-flow/components/plugin-config-modal/plugin-config-modal.component';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';

@Component({
  selector: 'meta-agent-modal',
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    CmdTextareaComponent,
    ReadonlyParamsTreeComponent,
    ParamTreeComponent,
    LLMSelectComponent,
    AssetIntelligentAddComponent,
    AssetIntelligentAddDisabledComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
    modelSettingsComponent,
  ],
  templateUrl: './agent-modal.component.html',
  styleUrls: ['./agent-modal.component.scss', '../common-styles.less'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    ParamLabelPipe,
  ],
})
export class AgentModalComponent extends ModalBaseComponent implements OnInit, OnDestroy {
  @ViewChild('modelSettingsRef')
  modelSettingsRef: NzTooltipDirective;

  @ViewChild('inputForm') inputForm: NgForm;

  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IAgentRepo;

  @Output('confirm') confirm = new EventEmitter<any>();

  public changeUrl = cdnAssetUrl;

  public validationRules = [Validators.required];

  public nameRefOptions: IParamRef[] = [];

  public inputParams: IWorkflowField[] = [];

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public modelListSubscription: Subscription;

  // 模型配置的Tip弹窗
  public modelSetRefCmp = modelSettingsComponent;

  public showModelSetRef = false;

  public modelParams: IModelParam = {
    top_p: 0.5,
    temperature: 0.5,
    max_tokens: null,
    history_size: 3,
    frequency_penalty: 0,
  };

  public modelSetTipCtx = {
    param: this.modelParams,
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

  public modelOptions: IModel[] = [];

  public agentFormGroup = this.fb.group({
    model: ['', [Validators.required]],
  });

  public pluginsLoading = false;

  public myPlugins = [];

  public prompt = '';

  public scales = [1, 5, 10, 15, 20];

  public ratios = [0.25, 0.25, 0.25, 0.25];

  public sliderMarks: Record<number, string> = {
    1: '1',
    5: '5',
    10: '10',
    15: '15',
    20: '20',
  };

  public selectedModelSubscription: Subscription;

  private paramsId: string;

  codeTimeout: any = null;

  get tipVals() {
    return this.inputParams.map(param => param.name);
  }

  constructor(
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private appAgentServe: AppAgentRepoService,
    private cdr: ChangeDetectorRef,
    private nzModal: NzModalService,
    private nzDrawer: NzDrawerService,
    protected agentDataServe: AgentDataService,
    private pluginRepoServe: AppPluginRepoService,
    private route: ActivatedRoute,
    private candidateTemplateListServe: CandidateTemplateListService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService
  ) {
    super(nodeServ, appFlowServ);
  }
  readonly showVarListSubject$ = new BehaviorSubject<boolean>(false);

  public override ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.paramsId = params.id;
    });
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo.name));
    this.myPlugins = this.nodeInfo.configs.plugins;
    this.getPluginList();
    this.selectedModelSubscription = this.agentFormGroup.get('model').valueChanges.subscribe(value => {
      this.modelSetTipCtx.selectedModel = this.modelOptions.find(model => model.model_deployment_id === value);
    });
    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(models => {
        if (models.length > 0) {
          this.modelOptions = models ?? [];
          this.agentFormGroup.setValue({
            model: this.nodeInfo.configs?.model?.model_deployment_id ?? '',
          });
        }
      });
    const { temperature, top_p, max_tokens } = this.nodeInfo.configs;
    this.modelParams = {
      top_p,
      temperature,
      max_tokens,
      history_size: 3,
      frequency_penalty: 0,
    };

    this.prompt = this.nodeInfo.configs.system_prompt?.trim() ?? '';
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { strOnly: true }).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe(info => {
        this.onRefUpdate(info);
      });
    }

    // 设置提示词优化的参数
    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.nodeInfo.configs?.model,
    });
  }

  public getPluginList() {
    this.pluginsLoading = true;
    const requestParams = {
      ids: [],
      type: 'all',
    };
    this.pluginRepoServe.getPluginList(requestParams).then(res => {
      this.pluginsLoading = false;
      this.myPlugins.forEach(plugin => {
        const find = res.plugin_list.find(item => item.plugin_id === plugin.id);
        if (find) {
          plugin.icon = find.icon;
        } else {
          plugin.deleted = true;
          plugin.icon = cdnAssetUrl('assets/agent-center/agent/plugin-gray.svg');
        }
      });
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

  /** 点击展示模型配置的Tip弹窗 */
  public onShowModelSetTip() {
    if (this.showModelSetRef) {
      this.showModelSetRef = false;
      this.modelSettingsRef.hide();
    } else {
      this.showModelSetRef = true;
      this.modelSetTipCtx.param = this.modelParams;
      window.setTimeout(() => {
        this.modelSettingsRef.show();
      });
    }
  }

  getmodelStatus(is_connecting) {
    if (is_connecting) {
      return this.i18n.transform('running');
    }

    return this.i18n.transform('call_failed');
  }

  compareModel = (a: any, b: any): boolean => (a && b ? a.model_deployment_id === b.model_deployment_id : a === b);

  compareType = (a: any, b: any): boolean => a === b;

  getInputNames(index: number): {
    existingValues: string[];
    forbiddenValues: string[];
  } {
    const names = this.inputParams.map(p => p.name);
    names.splice(index, 1);
    return { existingValues: names, forbiddenValues: ['query'] };
  }

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  onNameChange() {
    window.setTimeout(() => {
      this.inputForm?.form?.updateValueAndValidity?.();
    });
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  public deletePlugin(_item, index: number): void {
    this.myPlugins.splice(index, 1);
    this.onSave();
  }

  public addPlugin() {
    this.agentDataServe.setClickFlagPlugin('add');
    const drawerRef = this.nzDrawer.create({
      nzContent: AddPluginHalfmodalComponent,
      nzWidth: '700px',
      nzMaskClosable: false,
      nzData: {
        pluginAdded: this.myPlugins,
        agentNode: this.nodeInfo.id,
        dismiss: () => {
          drawerRef.close();
        },
        afterClose: confirmSavePlugins => {
          this.myPlugins = confirmSavePlugins.map(item => ({
            type: item.type,
            id: item.id,
            tool_id: item.tool_id,
            name: item.tool_chinese_name || item.name,
            description: item.tool_desc || item.description,
            icon: item.icon,
            ...(item?.last_version_id && {
              version_id: item.last_version_id,
            }),
          }));
          this.onSave();
          drawerRef.close();
          this.cdr.markForCheck();
        },
      },
    });
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
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
    this.inputForm?.form?.updateValueAndValidity?.();
  }

  // 提示词
  public onIntelligentAdd() {
    if (!this.prompt || this.isFlowReadonly) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
        instruct: this.prompt,
        isWorkflow: true,
        tipsChange: value => {
          this.prompt = value ?? '';
        },
      },
    });
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
    if (this.modelListSubscription) {
      this.modelListSubscription.unsubscribe();
    }
    if (this.selectedModelSubscription) {
      this.selectedModelSubscription.unsubscribe();
    }
  }

  public updateModel(modelInfo: any) {
    this.agentFormGroup.controls.model.setValue(modelInfo.id);
    // 设置提示词优化的参数
    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: modelInfo.modelInfo,
    });
    this.onSave();
  }

  dismiss(): void {}

  close(): void {}

  /** 处理"保存候选模板作为正式模板"接口中的入参variables */
  public processString(input: string): string {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map(match => match.slice(2, -2));
      return extractedValues.join(',');
    }
    return '';
  }

  public openRefModal() {
    this.nzModal.create({
      nzContent: RefPromptComponent,
      nzWidth: 1000,
      nzData: {
        select: (tmpl: ITmpl) => {
          this.prompt = tmpl.content;
        },
      },
    });
  }

  public showSaveTmplModal() {
    if (this.prompt.length > 0) {
      const modalRef: NzModalRef = this.nzModal.create({
        nzContent: SaveTmplLibraryModalComponent,
        nzWidth: 600,
        nzData: {
          currentTmpl: {
            is_workflow: true,
            created_on: moment().format('YYYY-MM-DD HH:mm:ss'),
            content: this.prompt,
            model_config: {
              temperature: null,
              top_p: null,
              max_tokens: null,
              presence_penalty: null,
            },
          },
          modalClose: form => {
            const params = {
              id: '',
              task_id: this.paramsId,
              name: form.value?.templateName,
              tags: form.value?.tags,
              industry_id: form.value?.industrys,
              content: this.prompt,
              source: 'PLAYGROUND',
              variables: this.processString(this.prompt),
            };
            this.candidateTemplateListServe.saveFormalTmpl(params).subscribe({
              next: () => {
                MessageComponent.showSuccess(this.i18n.transform('single_tmpl_save_success_tip'));
              },
            });
          },
        },
      });
    }
  }

  /** 配置插件参数 */
  public configPlugin(pluginItem) {
    let inputParams: IWorkflowField[] = [];
    let outputParams: IWorkflowField[] = [];
    const { inputs, outputs, input_schema, output_schema, tool_id } = pluginItem;

    if (inputs && outputs) {
      inputParams = inputs;
      outputParams = outputs;
    } else if (input_schema && output_schema) {
      inputParams = reqSchemaStr2Field(input_schema);
      outputParams =
        pluginItem?.intf_type === 'streaming'
          ? [
              {
                name: 'raw_output',
                description: this.i18n.transform('plug_in_streaming_output'),
                required: false,
                type: 'string',
                value: {
                  type: 'literal',
                  content: '',
                  hint: '',
                },
                source: 'user',
                isDisabled: false,
              },
              ...resSchemaStr2Field(output_schema),
            ]
          : resSchemaStr2Field(output_schema);
    } else {
      inputParams = null;
      outputParams = null;
    }

    const refInfos: IRefInfo[] = [
      {
        refNodeId: '',
        refNodeName: this.i18n.transform('var'),
        type: 'System',
        outputs: [],
      },
    ];
    const drawerRef = this.nzDrawer.create({
      nzContent: PluginConfigModalComponent,
      nzWidth: 700,
      nzPlacement: 'right',
      nzMaskClosable: false,
      nzContentParams: {
        inputParams,
        isFlowReadonly: this.isFlowReadonly,
        outputParams,
        refInfos,
      },
    });

    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      instance.confirm.subscribe((conf: IPluginParamConf) => {
        pluginItem.inputs = conf.inputs;
        pluginItem.outputs = conf.outputs;
        drawerRef.close();
      });
      instance.cancelEvt.subscribe(() => {
        drawerRef.close();
      });
    });
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

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const selectedModel = this.modelOptions.find(model => model.model_deployment_id === this.agentFormGroup.controls.model.value);

    const plugins = this.myPlugins.map(item => ({
      id: item.id,
      tool_id: item.tool_id,
      type: item.type,
      icon: item.icon,
      name: item.name,
      description: item.description,
      ...(item?.version_id && {
        version_id: item.version_id,
      }),
    }));

    // 兼容旧草稿：保存时清理已下线的终止条件，避免继续写回后端。
    const agentConfigs = { ...this.nodeInfo.configs } as any;
    delete agentConfigs.break_plugin_ids;
    delete agentConfigs.enable_intent_break;

    const nodeData: IAgentRepo = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: NodeUtils.getDtoInputs(this.inputParams),
      outputs: this.nodeInfo.outputs,
      configs: {
        ...agentConfigs,
        model: {
          model_name: selectedModel?.model_name ?? '',
          model_type: selectedModel?.model_type ?? '',
          model_deployment_id: selectedModel?.model_deployment_id ?? '',
        },
        temperature: Number(this.modelParams.temperature),
        top_p: Number(this.modelParams.top_p),
        max_tokens: Number(this.modelParams.max_tokens),
        plugins,
        system_prompt: this.prompt,
      },
    };
    this.appFlowServ.setNodeSaveMonitor({
      nodeData,
    });
    this.codeTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
