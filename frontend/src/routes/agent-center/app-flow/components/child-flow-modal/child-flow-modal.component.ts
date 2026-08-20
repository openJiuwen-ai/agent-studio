import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { filter, takeUntil } from 'rxjs';
import { AppFlowService } from '../../app-flow.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IFlowNode, IParamRef } from '../../node.type';
import * as nodeType from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { ReadonlyParamsTreeComponent } from '../readonly-params/readonly-params-tree.component';
import { NodeUtils } from '../utils';
import { NODE_ACTIONS } from '@routes/agent-center/constants/workflow-common.const';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import { ExceptionHandlingComponent } from '@routes/agent-center/app-flow/components/exception-handling/exception-handling.component';
import { HttpService } from '@services/http.service';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { mapTreeAddKeyAndChildIndex, eachChildrenToRootObj, setAllChildrenVal } from '@routes/agent-center/app-plugin/utils';
@Component({
  selector: 'meta-child-flow-modal',
  templateUrl: './child-flow-modal.component.html',
  styleUrls: ['./child-flow-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    TypedJsonInputComponent,
    RefSelectedRequireDirective,
    ExceptionHandlingComponent,
    ReadonlyParamsTreeComponent,
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
export class ChildFlowModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IFlowNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('exceptionHandling') exceptionHandling: ExceptionHandlingComponent;

  public isParamFold = false;

  public icon = WORKFLOW_SVGS.Workflow;

  public responseTemplate = '';

  public inputParams: nodeType.IWorkflowField[] = [];

  public disabledSwitch = true;

  public nameRefOptions: nodeType.IParamRef[] = [];

  public validationRules: any[] = [];

  public validation: any = {
    type: 'change',
  };

  get tipVals() {
    return this.inputParams.map(param => param.name);
  }

  public originalName = '';
  updateTimeout: any = null;

  override actions = [
    {
      id: 'detail',
      label: this.i18n.transform('sub_workflow_details'),
    },
    ...NODE_ACTIONS,
  ];

  public isValidated = false;

  workspaceId = '';

  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    private appFlowServe: AppFlowService,
    private readonly http: HttpService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    private nzModal: NzModalService,
    private nzMessage: NzMessageService
  ) {
    super(nodeServ, appFlowServe);
  }

  getType = NodeUtils.getFieldTypeView;

  initOriginalName() {
    if (this.nodeInfo.configs?.original_info) {
      const { name, name_en } = this.nodeInfo.configs.original_info;
      this.originalName = `${this.i18n.transform('original_name')}${name}（${name_en}）`;
    } else {
      this.originalName = `${this.i18n.transform('original_name')}${this.nodeInfo.name}`;
    }
  }

  public override ngOnInit() {
    this.workspaceId = this.http.getWorkspaceId();
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.initOriginalName();
    this.subNodeActions();
    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo?.name));

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { strOnly: true }).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs({ strOnly: true }).subscribe(info => {
        this.onRefUpdate(info);
      });
    }
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(this.nodeInfo?.inputs, this.nameRefOptions);
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.inputParams.forEach(v => {
      v.options = [
        { label: this.i18n.transform('ref'), value: 'ref' },
        { label: this.getType(v), value: 'literal' },
      ];
    });
    this.inputParams = mapTreeAddKeyAndChildIndex(this.inputParams, 0);
    this.isInit = false;
  }

  override onClickAction(action: any) {
    if (action.id === 'detail') {
      const config = this.nodeInfo.configs;
      const prefixUrl = window.location.href?.split('/home')[0];
      const queryParams = `?id=${config.id}&versionId=${config.version_id}&versionName=${config.version_name}&workspace_id=${this.workspaceId}`;
      const newurl = `${prefixUrl}/home/agent-center/app-flow/flow${queryParams}`;
      window.open(newurl, '_blank');
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  public onTypeChange(row: nodeType.IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    (row as any).children = setAllChildrenVal((row as any).children, row.value);
    this.onSave();
  }

  public originalOrder(): number {
    return 0;
  }

  public trackByFn(index: number) {
    return index;
  }

  public filterNaN(event: KeyboardEvent): void {
    if (['e', 'E', '+'].includes(event.key)) {
      event.preventDefault();
    }
  }

  validateNode() {
    if (!this.exceptionHandling.validate()) {
      return;
    }
    this.isValidated = true;
  }

  public subNodeActions() {
    this.appFlowServe.nodeActionUpdate$().pipe(
      filter(action => action && action.id === this.nodeInfo.id),
      takeUntil(this.destroy$)
    );
  }
  dismiss(): void {}
  close(): void {}
  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
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

  changeChildVal(origin) {
    if (origin.isChild) {
      const index = Number(origin.key.split('_')[0]);
      if (this.inputParams[index].value.type === 'literal') {
        this.inputParams[index].value.content = JSON.stringify(eachChildrenToRootObj((this.inputParams[index] as any).children, origin));
      }
    }
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const inputs = cloneDeep(this.inputParams);
    inputs.forEach(param => {
      delete param.children;
      if (param.value?.type === 'ref') {
        const contentArr = (param.value.content as IParamRef[])?.[0];

        if (contentArr) {
          const { ref_node_id, ref_var_name, source } = contentArr;
          param.value.content = {
            ref_var_name,
            ref_node_id,
            source,
          };
        }
      }

      delete param?.refs;
    });

    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs,
        configs: this.nodeInfo.configs,
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

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }
}
