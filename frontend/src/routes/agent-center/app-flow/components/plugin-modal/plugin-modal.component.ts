import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { I18nNamespace } from '@i18n';
import {
  MonacoEditorComponent,
  MonacoEditorLoaderService,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { NODE_ACTIONS } from '@routes/agent-center/constants/workflow-common.const';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import {
  IntegerStrValidatorDirective,
  NumberStrValidatorDirective,
  RefSelectedRequireDirective,
} from '@shared/directives/common-validator.directive';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import {I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule} from 'angular-i18next';
import { NzTreeSelectModule } from 'ng-zorro-antd/tree-select';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzTreeModule } from 'ng-zorro-antd/tree';
import { FormsModule } from '@angular/forms';
import { cloneDeep } from 'lodash';
import { filter, Subject, take, takeUntil } from 'rxjs';
import { AppFlowService } from '../../app-flow.service';
import type { INodeOutput } from '../../app-flow.types';
import { getOutputParamTypes, WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type {
  IParamRef,
  IPluginNode,
  IWFView,
  IWorkflowField,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { EditorOptions, NodeUtils } from '../utils';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { JSONSchemaFaker } from 'json-schema-faker';
import { AddPluginAuthComponent } from '@routes/plugin-market/add-plugin/add-plugin-auth.component';
import { IPlugin } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { PluginCredentialStatus } from '@enums/agent-center.enum';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import {
  ExceptionHandlingComponent
} from '@routes/agent-center/app-flow/components/exception-handling/exception-handling.component';
import { HttpService } from '@services/http.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { getPluginQuota, getQuotaTip } from '../../../utils';

type MonacoUri = monaco.Uri;

const normalParamLableWidth = {
  name: '178px',
  type: '178px',
  desc: '178px',
};

const slimParamLableWidth = {
  name: '136px',
  type: '136px',
  desc: '120px',
};

enum mapKeys {
  location = 'location',
  credential_status = 'credential_status'
}

@Component({
  selector: 'meta-api-modal',
  templateUrl: './plugin-modal.component.html',
  styleUrls: ['./plugin-modal.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    MonacoEditorModule,
    AssetFormatIconComponent,
    ObjTypeValidatorDirective,
    ParamTreeComponent,
    TypedJsonInputComponent,
    ExceptionHandlingComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
    I18NextModule,
    NzAlertModule,
    NzSelectModule,
    NzInputModule,
    NzIconModule,
    NzToolTipModule,
    NzDropDownModule,
    NzTreeModule,
    FormsModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IPluginNode;

  @Input('nodeOutputs') nodeOutputs: INodeOutput[];

  @Output('confirm') confirm = new EventEmitter<IPluginNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('inputFormContent') inputFormContent: NgForm;

  @ViewChild('outputForm') outputForm: NgForm;

  @ViewChild('editorCmp') editorCmp: MonacoEditorComponent;

  @ViewChild('exceptionHandling') exceptionHandling: ExceptionHandlingComponent;

  protected override destroy$ = new Subject<void>();
  public pluginInfo: any = {};
  public icon = WORKFLOW_SVGS.Plugin;

  public nameRefOptions: IParamRef[] = [];

  public inputParams: IWorkflowField[] = [];

  public outputParams: any[] = [];

  public editorOps = EditorOptions;

  public outputDataTypes = getOutputParamTypes();

  public validationRules: any[] = [];

  public validation: any = {
    type: 'change',
  };

  public booleanOps = [
    {
      label: 'true',
      value: true,
    },
    {
      label: 'false',
      value: false,
    },
  ];

  getType = NodeUtils.getFieldTypeView;

  public originalName = '';

  public editorUri: MonacoUri = null;

  public ignoreMsg = '{}';

  override labelWidth = normalParamLableWidth;

  override actions = [...NODE_ACTIONS];

  public isValidated = false;
  workspaceId = ''

  public inputSchema: any = '';

  public isShowHeaders: boolean = false;

  public quotaConfig = null;
  updateTimeout: any = null;

  constructor(
    private i18n: I18NextEagerPipe,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private monacoLoader: MonacoEditorLoaderService,
    private configServ: AgentConfigService,
    private tiModal: NzModalService,
    private nzMessage: NzMessageService,
    private pluginService: AppPluginRepoService,
    private readonly http: HttpService,
    private appFlowRepoServe: AppFlowRepoService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
  ) {
    super(nodeServ, appFlowServ);
  }

  isComplexType = NodeUtils.isComplexType;

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  public override ngOnInit() {
    this.workspaceId = this.http.getWorkspaceId()
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    if (this.configServ.getConfigs()?.studio_btn_show) {
      this.actions.unshift({
        id: 'detail',
        label: this.i18n.transform('plugin_details'),
      });
    }
  
    this.initOriginalName();
    this.labelWidth = this.isNormalView
      ? normalParamLableWidth
      : slimParamLableWidth;

    this.monacoLoader.isMonacoLoaded$
      .pipe(
        filter((isLoaded) => isLoaded),
        take(1),
      )
      .subscribe(async () => {
        this.editorUri = monaco.Uri.parse(
          `agent://flow/plugin/${this.nodeInfo.id}/exception_suppression.json`,
        );
        if (this.nodeInfo.configs?.exception_suppression) {
          this.ignoreMsg = this.nodeInfo.configs.exception_suppression;
        } else {
          try {
            const schema = JSON.parse(this.nodeInfo.configs?.output_schema);
            JSONSchemaFaker.option({
              maxItems: 1,
            });
            const defaultMsg = await JSONSchemaFaker.resolve(schema);
            this.ignoreMsg = JSON.stringify(defaultMsg, null, 2);
          } catch (e) {
            this.ignoreMsg = '{}';
          }
        }
      });

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode).subscribe((info) => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe((info) => {
        this.onRefUpdate(info);
      });
    }

    this.validationRules.push(
      CommonValidation.nameUniquenessVerify(
        this.names,
        this.i18n.transform('name_uniqueness'),
        this.nodeInfo.name,
      ),
    );
    this.outputParams = NodeUtils.fields2Views(this.nodeInfo.outputs);
  }

  ngAfterViewInit(): void {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      }, 1000);
    }
    //流式异常需要限制
    this.exceptionHandling.changeStream(this.nodeInfo.configs.streaming);
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.setInputSchema().then(() => {
        this.inputSchema = JSON.parse(this.inputSchema);
        this.inputParams = NodeUtils.initInputs(
          this.nodeInfo.inputs,
          this.nameRefOptions,
        );
        setTimeout(() => {
          this.inputParams.forEach((param, index) => {
            if (this.inputSchema.properties[param.name]) {
              param[mapKeys.location] = this.inputSchema.properties[param.name].location;
              if (param[mapKeys.location] === 'Headers') {
                this.isShowHeaders = true;
              }
            }
            if (!param.required) {
              const control = this.inputForm?.form?.get(`inputFormValue${index}`);
              if (control) {
                control.clearValidators();
                control.updateValueAndValidity();
              }
              const controlContent = this.inputFormContent?.form?.get(`inputFormContent${index}`);
              if (controlContent) {
                controlContent.clearValidators();
                controlContent.updateValueAndValidity();
              }
            }
          });
        });
        this.inputParams.forEach((v) => {
          v.options = [
            { label: this.i18n.transform('ref'), value: 'ref' },
            { label: this.getType(v), value: 'literal' },
          ];
        });
        this.isInit = false;
      })
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
      this.inputParams.forEach((v) => {
        v.options = [
          { label: this.i18n.transform('ref'), value: 'ref' },
          { label: this.getType(v), value: 'literal' },
        ];
      });
      this.isInit = false;
    }
  }

  private setQuotaConfig(plugin) {
    const quota = getPluginQuota(plugin, false);
    const text = getQuotaTip(this.i18n, quota, plugin.limit || 0, true);
    this.quotaConfig = text ? {
      type: quota > 0 ? 'warn' : 'error',
      text,
    } : null;
  }

  private async setInputSchema() {
    if (!this.nodeInfo.configs.version_id) {
      const res = await this.pluginService.getPluginList({id:this.nodeInfo.configs?.id, type: this.nodeInfo.configs.type});
      const { plugin_list, count } = res || {};
      if (!Array.isArray(plugin_list) || plugin_list.length <= 0) {
        return;
      }
      if (this.nodeInfo.configs.tool_id) {
        const filterData =  plugin_list[0].input_schema.filter((item: any) => item.tool_id === this.nodeInfo.configs.tool_id);
        if (filterData.length > 0) {
          this.inputSchema = filterData[0].input_schema;
        }
      } else {
        this.inputSchema = plugin_list[0].input_schema[0].input_schema;
      }
      this.pluginInfo = plugin_list[0];
      this.setQuotaConfig(this.pluginInfo);
      return;
    }


    const res = await this.appFlowRepoServe
      .getPluginVersionInfo(this.nodeInfo.configs?.id, this.nodeInfo.configs?.version_id);
    this.pluginInfo = res.data;
      this.setQuotaConfig(this.pluginInfo);
    if (this.nodeInfo.configs.tool_id) {
      const filterData =  res.data.input_schema.filter((item: any) => item.tool_id === this.nodeInfo.configs.tool_id);
      if (filterData.length > 0) {
        this.inputSchema = filterData[0].input_schema;
      }
    } else {
      this.inputSchema = res.data.input_schema[0].input_schema;
    }
  }

  override ngOnDestroy(): void {
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
    this.destroy$.next();
    this.destroy$.complete();
  }

  dismiss(): void {}

  close(): void {}

  formatContent() {
    this.editorCmp?.editor?.getAction('editor.action.formatDocument')?.run();
  }

  initOriginalName() {
    if (this.nodeInfo.configs?.original_info) {
      const { name, name_en } = this.nodeInfo.configs.original_info;
      this.originalName = `${this.i18n.transform(
        'original_name',
      )}${name}（${name_en}）`;
    } else {
      this.originalName = `${this.i18n.transform('original_name')}${
        this.nodeInfo.name
      }`;
    }
  }

  override onClickAction(action: any) {
    if (action.id === 'detail') {
      const prefixUrl = window.location.href?.split('/home')[0];

      if (this.nodeInfo.configs?.original_info?.type === 'inner') {
        window.open(`${prefixUrl}/home/plugin-market`, '_blank');
      } else {
        window.open(
          `${prefixUrl}/home/agent-center/custom-plugin/detail?id=${this.nodeInfo.configs.id}&workspace_id=${this.workspaceId}`,
          '_blank',
        );
      }
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  validateNode() {
    this.exceptionHandling.validate();
    this.isValidated = true;
    const isJsonTypeInvalid = this.inputParams.some(
      (obj) =>
        this.isArrOrObj(obj.type) && obj.value?.content === '' && obj.required,
    );
  }

  getIndexWidth(param: IWFView): string {
    const map = {
      0: '178px',
      1: '154px',
      2: '130px',
      3: '106px',
    };

    const slimMap = {
      0: '136px',
      1: '112px',
      2: '88px',
      3: '64px',
    };

    const mapWithChildren = {
      0: '158px',
      1: '134px',
      2: '110px',
    };

    const slimMapWithChildren = {
      0: '116px',
      1: '92px',
      2: '68px',
    };

    const useMap = this.isNormalView ? map : slimMap;
    const useWithChildrenMap = this.isNormalView
      ? mapWithChildren
      : slimMapWithChildren;

    return param?.children
      ? useWithChildrenMap[param.depth]
      : useMap[param.depth];
  }

  onNameChange() {
    window.setTimeout(() => {
      this.outputForm?.form?.markAsDirty();
    });
  }

  getOutputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.outputParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }
  public isShowAuthConfigBtn() {
    return this.pluginInfo[mapKeys.credential_status] === PluginCredentialStatus.UNAUTHENTICATED;
  }
  public handleClickAddAuthConfig(e) {
    e.stopPropagation();
    const modal = this.tiModal.create({
      nzTitle: '',
      nzContent: AddPluginAuthComponent,
      nzClassName: 'createPluginAuth',
      nzOnOk: () => {
        this.pluginInfo[mapKeys.credential_status] = PluginCredentialStatus.AUTHENTICATED;
      },
    });
    const instance = modal.getContentComponent();
    instance.pluginInfo = this.pluginInfo;
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
    const inputs = NodeUtils.getDtoInputs(this.inputParams, {
      useContentType: false,
    });

    inputs.forEach((input) => {
      if (input.value.type === 'literal' && ['number', 'integer'].includes(input.type)) {
        if (typeof input.value.content !== 'number') {
          if (input.value.content === '' || input.value.content == null) {
            input.value.content = null; // 空值置 null，运行时跳过该参数
          } else {
            input.value.content = Number(input.value.content);
          }
        }
      }
      if (input.options) {
        delete input.options;
      }
    });

    const configs = cloneDeep(this.nodeInfo.configs);

    const nodeData: IPluginNode = {
      ...this.nodeInfo,
      inputs,
      configs,
    };
    this.appFlowServ.setNodeSaveMonitor({
      nodeData
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

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  onSave() {
    this.changeUpdateTime();
    // 只有当前有校验问题时，才失焦保存，其他时候要抽屉关闭保存
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
