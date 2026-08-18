import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
  ChangeDetectorRef,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import {
  IntegerStrValidatorDirective,
  NumberStrValidatorDirective,
  RefSelectedRequireDirective,
} from '@shared/directives/common-validator.directive';
import { MCPService } from '@services/agent-center/mcp.service';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IMcpNode, IParamRef, IWorkflowField } from '../../node.type';
import {
  reqSchemaStrMCPField, resSchemaDataField,
  resSchemaStrMCPField,
} from '@routes/agent-center/app-mcp-service/utils';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { NodeUtils } from '../utils';
import { ReadonlyParamsTreeComponent } from '../readonly-params/readonly-params-tree.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import { HttpService } from '@services/http.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { MCP_SERVER, NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { mapTreeAddKeyAndChildIndex, eachChildrenToRootObj, setAllChildrenVal } from '@routes/agent-center/app-plugin/utils';
import { cloneDeep } from 'lodash';

enum mapKeys {
  task_operators_console = 'task_operators_console',
  job_prompts = 'job_prompts'
}

@Component({
  selector: 'meta-mcp-service-modal',
  templateUrl: './mcp-service-modal.component.html',
  styleUrls: ['./mcp-service-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    RefSelectedRequireDirective,
    ReadonlyParamsTreeComponent,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    MonacoEditorModule,
    TypedJsonInputComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
    NonEmptyValidatorDirective,
    NzSelectModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class MCPServiceModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IMcpNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('inputForm') inputForm: NgForm;

  public icon = WORKFLOW_SVGS.Mcp;

  public toolName = '';

  public originalName = '';

  public headers: any = null;

  public headerParams: IWorkflowField[] = [];

  public inputParams: IWorkflowField[] = [];

  public nodeOperators = [];

  public outputParams: IWorkflowField[] = [];

  public disabledSwitch = true;

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

  public nameRefOptions: IParamRef[] = [];

  public validationRules = [];

  public validation: any = {
    type: 'change',
  };

  public serviceDesc = '';

  public toolList: any = [];

  public isValidated = false;
  workspaceId = '';
  updateTimeout: any = null;

  public mcpInputParams = null;

  constructor(
    private readonly i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    private readonly appFlowServe: AppFlowService,
    private readonly mcpService: MCPService,
    private readonly http: HttpService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    private cdr: ChangeDetectorRef
  ) {
    super(nodeServ, appFlowServe);
  }

  getType = NodeUtils.getFieldTypeView;

  onInputValueTypeChange(row: IWorkflowField, changeChild) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    if (changeChild) {
      (row as any).children = setAllChildrenVal((row as any).children, row.value);
    }
    this.onSave();
  }

  public override ngOnInit() {
    this.workspaceId = this.http.getWorkspaceId();
    this.icon = this.getIcon1();
    this.setNodeBase(this.nodeInfo);
    this.getServiceDeatil();
    this.initOriginalName();
    super.ngOnInit();

    this.toolName = this.nodeInfo.configs.tool_name;

    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo.name));
    this.outputParams = this.nodeInfo.outputs;
  }

  ngAfterViewInit(): void {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  registerNodeUpdateHander() {
    const parentNode = this?.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode)?.subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe(info => {
        this.onRefUpdate(info);
      });
    }
  }

  private getIcon1() {
    if (this.nodeInfo.type === 'Mcp') {
      return WORKFLOW_SVGS.Mcp;
    }
    if (this.nodeInfo.type === 'DataSynthesis') {
      return WORKFLOW_SVGS.DataSynthesis;
    }
    return WORKFLOW_SVGS.DataProcess;
  }

  initOriginalName() {
    if (this.nodeInfo.configs?.original_info) {
      const { name, name_en } = this.nodeInfo.configs.original_info;
      this.originalName = `${this.i18n.transform('original_name')}${name}（${name_en}）`;
    } else {
      this.originalName = `${this.i18n.transform('original_name')}${this.nodeInfo.name}`;
    }
  }

  override onClickAction(action: any) {
    if (action.id === 'detail') {
      const prefixUrl = window.location.href?.split('/home')[0];
      const newurl = `${prefixUrl}/home/agent-center/mcp-service/detail?id=${this.nodeInfo.configs.id}&workspace_id=${this.workspaceId}`;
      window.open(newurl, '_blank');
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  getServiceDeatil() {
    this.mcpService
      .getMcpToolInfo(this.nodeInfo.configs.id)
      .then((res: any) => {
        this.serviceDesc = res.description || this.i18n.transform(this.nodeDesci18nMap(this.nodeInfo.type));
        const data = res.tools || [];
        const key = 'task_operators';
        this.toolList = data.map(item => {
          let config =
            this.nodeInfo.type === 'DataProcess'
              ? resSchemaDataField(item.config)[mapKeys.task_operators_console]
              : resSchemaDataField(item.config)[mapKeys.job_prompts];
          return {
            label: item.name,
            value: item.name,
            ...item,
            config: config,
          };
        });
        console.log('toolList loaded:', this.toolList);
        this.getToolInfo(this.toolName);
        if (res.server_config) {
          try {
            const serverConfig = JSON.parse(res.server_config);
            this.headers = serverConfig?.mcpServers?.[MCP_SERVER[res.org_type]]?.headers || {};
          } catch {
            // do nth
          }
        }
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.registerNodeUpdateHander();
        this.cdr.detectChanges();
      });
  }

  getToolInfo(name: string) {
    const item = this.toolList.find(item => item.name === name);
    if (!item || !item?.config) {
      return;
    }
    this.nodeOperators = item.config.map(item => {
      return {
        ...item,
        name: this.nodeInfo.type === 'DataProcess' ? item.operator_name : item.prompt_name,
        description: this.nodeInfo.type === 'DataProcess' ? item.operator_desc : '',
      };
    });
  }

  inputParamsFormatter() {
    this.inputParams.forEach(v => {
      v.location = Object.prototype.hasOwnProperty.call(this.headers, v.name) ? 'Headers' : 'Input';
      v.options = [
        { label: this.i18n.transform('ref'), value: 'ref' },
        { label: this.getType(v), value: 'literal' },
      ];
    });
  }

  onToolChange(name: string) {
    let key = 'value';
    if (['DataProcess', 'DataSynthesis'].includes(this.nodeInfo.type)) {
      key = 'name';
    }
    const item = this.toolList.find(item => item[key] === name);
    if (!item) {
      return;
    }
    this.inputParams = [
      ...this.inputParams.filter(item => item.location === 'Headers'),
      ...NodeUtils.initInputs(reqSchemaStrMCPField(item.input), this.nameRefOptions),
    ];

    if (item?.config) {
      this.getToolInfo(name);
    }
    this.inputParamsFormatter();
    this.outputParams = resSchemaStrMCPField(item.output);
    this.onSave();
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(this.nodeInfo.inputs, this.nameRefOptions);
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }
    this.inputParamsFormatter();
    this.mcpInputParams = mapTreeAddKeyAndChildIndex(cloneDeep(this.inputParams.filter(item => item.location === 'Input')), 0);
    this.isInit = false;
  }

  validateNode() {
    this.isValidated = true;
  }

  dismiss(): void {}

  changeChildVal(origin) {
    if (origin.isChild) {
      const index = Number(origin.key.split('_')[0]);
      if (this.mcpInputParams[index].value.type === 'literal') {
        const aaa = eachChildrenToRootObj((this.mcpInputParams[index] as any).children, origin);
        this.mcpInputParams[index].value.content = JSON.stringify(aaa);
      }
    }
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    let inputsHeard = (cloneDeep(this.inputParams) || []).filter(item => item.location === 'Headers');
    let inputsTools = cloneDeep(this.mcpInputParams);
    const inputs = NodeUtils.getDtoInputs([...inputsHeard, ...inputsTools], {
      useContentType: false,
    });

    inputs.forEach(input => {
      delete (input as any).children;
      const isTrue =
        input.value.type === 'literal' && ['number', 'integer'].includes(input.type) && input.value.content !== null && typeof input.value.content !== 'number';
      if (isTrue) {
        input.value.content = Number(input.value.content);
      }
      if (input.type === 'object' && input.value.content === '') {
        input.value.content = '{}';
      }
      if (input.type === 'array' && input.value.content === '') {
        input.value.content = '[]';
      }
    });
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs,
        outputs: this.outputParams,
        configs: {
          ...this.nodeInfo.configs,
          tool_name: this.toolName,
        },
      },
    });
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    this.updateTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }

  onSave() {
    this.changeUpdateTime();
    // 只有当前有校验问题时，才失焦保存，其他时候要抽屉关闭保存
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
