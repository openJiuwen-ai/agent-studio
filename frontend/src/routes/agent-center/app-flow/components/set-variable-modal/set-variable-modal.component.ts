import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { IntegerStrValidatorDirective, NumberStrValidatorDirective, RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { AppFlowService } from '../../app-flow.service';
import { IRefInfo } from '../../app-flow.types';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { ILoopNode, IParamRef, IRefContentType, ISetVariableNode, IWorkflowField, IWorkflowFieldType } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { NodeUtils } from '../utils';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { takeUntil } from 'rxjs';

interface IVal {
  left: IWorkflowField;
  right: IWorkflowField;
  operatorOpts?: any;
  typeOpts?: any;
}

const hasEmptyType = ['integer', 'number', 'string', 'boolean', 'object', 'array<string>', 'array<number>', 'array<integer>'];
@Component({
  selector: 'meta-set-variable-modal',
  templateUrl: './set-variable-modal.component.html',
  styleUrls: ['./set-variable-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SetVariableModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: ISetVariableNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('paramForm') paramForm: NgForm;

  public icon = WORKFLOW_SVGS.SetVariable;

  public inputParams: IWorkflowField[] = [];

  public disabledSwitch = true;

  public leftRefs: IParamRef[] = [];

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public refOnlyOptions = [{ label: this.i18n.transform('ref'), value: 'ref' }];

  public commonOperatorOptions = [{ label: this.i18n.transform('operator'), value: 'operator' }];

  public operatorOptions = [
    {
      label: this.i18n.transform('increment'),
      value: 'increment',
    },
    { label: this.i18n.transform('decrement'), value: 'decrement' },
  ];

  public nullOperator = [
    {
      label: 'null',
      value: 'empty',
    },
  ];

  public EmptyStrOperator = [
    {
      label: this.i18n.transform('empty_data_label'),
      value: 'empty_str',
    },
  ];

  public EmptyArrOperator = [
    {
      label: '[]',
      value: 'empty_arr',
    },
  ];

  public getLeftParamsType(param: IWorkflowField) {
    if (param.value.type === 'ref' && (param.value.content as IParamRef[]).length) {
      const { type } = (param.value.content[0] as IParamRef) || {};
      if (type === 'object' || type.startsWith('array')) {
        return 'complex';
      } else {
        return 'normal';
      }
    }
    return 'normal';
  }

  public isGetLeftType(param: IWorkflowField) {
    const { type } = (param.value.content[0] as IParamRef) || {};
    return type;
  }

  public getParamType(param: IWorkflowField) {
    if (param.value.type === 'ref' && (param.value.content as IParamRef[]).length) {
      const { type } = (param.value.content[0] as IParamRef) || {};
      if (type.startsWith('array')) {
        return 'emptyArr';
      } else if (['number', 'integer'].includes(type)) {
        return 'emptyNum';
      } else if (['string'].includes(type)) {
        return 'emptyStr';
      }
    }
    return 'emptyNormal';
  }

  public innerPreOptions: IParamRef[] = [];

  public parentPreOptions: IParamRef[] = [];

  public loopNodeInfo: ILoopNode = null;

  public rightRefs: IParamRef[] = [];

  public validationRules: any[] = [];

  public params: IVal[] = [];

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

  workflowType: string = 'chat';
  public requestVariables;
  updateTimeout: any = null;

  get tipVals() {
    return this.inputParams.map(param => param.name);
  }

  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService
  ) {
    super(nodeServ, appFlowServ);
    this.nodeServ
      .refInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(info => {
        const new_info = NodeUtils.refInfo2Tree(info);
        this.requestVariables = appFlowServ.requestVariablesFn(new_info);
      });
  }

  graph: any = null;

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.workflowType = this.appFlowServ.getWorkflowType();
    this.validationRules.push(CommonValidation.nameUniquenessVerify(this.names, this.i18n.transform('name_uniqueness'), this.nodeInfo.name));

    this.graph = this.appFlowServ.getGraph();
    this.loopNodeInfo = this.getParentNodeInfo(this.graph);

    const assignmentMemos = (this.appFlowServ.getFlowConfigs()?.memory ?? [])
      .filter(memo => memo.storage_method === 'assignment')
      .map(memo => {
        return {
          ...memo,
          name: `memory.${memo.name}`,
        };
      });

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());

    const refs = parentNode ? this.getLoopMidVarRefs(this.loopNodeInfo) : [];
    if (assignmentMemos.length) {
      const assignmentMemosRefs = NodeUtils.refInfo2Tree(
        [
          {
            ...this.getNewMemo(),
            outputs: assignmentMemos,
          },
        ],
        {
          hideArrObjChildren: true,
        }
      );
      refs.unshift(...assignmentMemosRefs);
    }
    if (this.requestVariables) {
      refs.push(...this.requestVariables);
    }
    this.leftRefs = refs;

    if (parentNode) {
      this.getLoopInnerNodeRefs(this.loopNodeInfo).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe(info => {
        this.onRefUpdate(info);
      });
    }
  }

  ngAfterViewInit(): void {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  public onRefUpdate(info: IParamRef[]) {
    this.rightRefs = info;

    if (this.isInit) {
      this.initParams();
    } else {
      this.params.forEach(param => {
        const { left, right } = param;

        if (right.value.operator) {
          right.value.type = 'operator';
        }

        NodeUtils.reSelectRefWithNewOps(
          right,
          NodeUtils.narrowRefOption(this.rightRefs, {
            type: left.type,
          })
        );
      });
    }

    this.isInit = false;
  }

  public initParams() {
    if (!this.nodeInfo.inputs.length) {
      this.addParam();
      return;
    }

    this.params = this.nodeInfo.inputs.map((input: any, index) => {
      const left: IWorkflowField = {
        ...cloneDeep(input),
        refs: cloneDeep(this.leftRefs),
      };

      NodeUtils.selectTreeNodeInRefsChhangeByValue(left);

      const setting = this.nodeInfo.configs.settings[index];

      let queryType = left.type;
      if (queryType.startsWith('array')) {
        queryType = `${queryType}<${(left.schema as IWorkflowField).type}>` as IWorkflowFieldType;
        if (left?.value?.content && (left as any)?.schema.type !== left.value.content[0]?.schema.type) {
          queryType = `${left.type}<${left.value.content[0]?.schema.type}>` as IWorkflowFieldType;
        }
      }

      if (left.value?.content[0]?.type && left.type !== left.value.content[0].type) {
        queryType = left.value.content[0].type;
      }

      const right: IWorkflowField = {
        ...cloneDeep(setting.right),
        refs: cloneDeep(
          NodeUtils.narrowRefOption(this.rightRefs, {
            type: queryType,
          })
        ),
      };
      NodeUtils.selectTreeNodeInRefsByValue(right);

      let operatorOpts = this.initOperatorOptions(setting.left.type);
      let typeOpts = setting.left.type === 'object' || setting.left.type.startsWith('array') ? this.refOnlyOptions : this.sourceOptions;
      let leftType = setting.left.type.toLowerCase();
      if (leftType === 'array') {
        let typeName = 'type';
        leftType = `array<${setting.left.schema?.[typeName]?.toLowerCase()}>`;
      }
      if (hasEmptyType.includes(leftType)) {
        typeOpts = [...typeOpts, ...this.commonOperatorOptions];
      }
      if (right.value.operator) {
        right.value.type = 'operator';
      }

      return {
        typeOpts,
        operatorOpts,
        left,
        right,
      };
    });
  }

  public initParentInfo() {
    const parentCell = this.graph.getCellById(this.nodeInfo.id).getParent();
    const parentData = parentCell?.data?.ngArguments?.nodeInfo as ILoopNode;

    this.loopNodeInfo = parentData;
  }

  public isRightDisabled(param: IVal) {
    if (!param.left.value.content) {
      return true;
    }

    if (Array.isArray(param.left.value.content)) {
      if (!param.left.value.content[0].ref_var_name) {
        return true;
      }

      return false;
    }

    if (!(param.left.value.content as IRefContentType).ref_var_name) {
      return true;
    }

    return false;
  }

  public onLeftSelect(selectedVal: IParamRef[], param: IVal) {
    param.operatorOpts = this.getOperatorOptions(param);
    let typeOpts = this.getLeftParamsType(param.left) === 'complex' ? this.refOnlyOptions : this.sourceOptions;
    if (hasEmptyType.includes(this.isGetLeftType(param.left).toLowerCase())) {
      param.typeOpts = [...typeOpts, ...this.commonOperatorOptions];
    } else {
      param.typeOpts = typeOpts;
      param.right.value.type = 'ref';
    }
    param.right.refs = cloneDeep(
      NodeUtils.narrowRefOption(this.rightRefs, {
        type: selectedVal[0].type as IWorkflowFieldType,
      })
    );
    param.right.type = selectedVal[0].type as IWorkflowFieldType;

    NodeUtils.selectTreeNodeInRefsByValue(param.right);

    if (this.getLeftParamsType(param.left) === 'complex' && param.right.value.type === 'literal') {
      param.right.value.type = 'ref';
      this.onIntegerTypeChange(param);
    }
  }

  public addParam() {
    const left: IWorkflowField = {
      name: '',
      type: 'string',
      description: this.i18n.transform('sharing_parameters_between_loops'),
      required: true,
      source: 'user',
      value: {
        type: 'ref',
        content: '',
        hint: '',
      },
      refs: cloneDeep(this.leftRefs),
    };
    NodeUtils.selectTreeNodeInRefsByValue(left);

    const right: IWorkflowField = {
      type: 'string',
      value: {
        type: 'ref',
        content: '',
        hint: '',
      },
      refs: cloneDeep(
        NodeUtils.narrowRefOption(this.rightRefs, {
          type: left.type,
        })
      ),
    };
    NodeUtils.selectTreeNodeInRefsByValue(right);

    this.params.push({
      left,
      right,
    });
  }

  public deleteParam(index: number): void {
    this.params.splice(index, 1);
    this.onSave();
  }

  public onIntegerTypeChange(param: any, event?) {
    param.right.value.content = NodeUtils.getChangeContent(param.right.value.type);
    if (param.right.value.type === 'operator') {
      let leftType = this.getParamType(param.left);
      if (leftType === 'emptyNum') {
        param.right.value.operator = 'increment';
      } else {
        param.right.value.operator = 'empty';
      }
    }
    this.onSave();
  }

  dismiss(): void {}

  close(): void {}

  validateNode() {}

  getOperatorOptions(param) {
    let leftType = this.getParamType(param.left);
    if (leftType === 'emptyArr') {
      return [...this.EmptyArrOperator, ...this.nullOperator];
    } else if (leftType === 'emptyStr') {
      return [...this.EmptyStrOperator, ...this.nullOperator];
    } else if (leftType === 'emptyNum') {
      return [...this.operatorOptions, ...this.nullOperator];
    } else {
      return [...this.nullOperator];
    }
  }

  getLeftType(type) {
    let leftType = 'emptyNormal';
    if (type.startsWith('array')) {
      leftType = 'emptyArr';
    } else if (['number', 'integer'].includes(type)) {
      leftType = 'emptyNum';
    } else if (['string'].includes(type)) {
      leftType = 'emptyStr';
    }
    return leftType;
  }
  initOperatorOptions(type) {
    let leftType = this.getLeftType(type);
    if (leftType === 'emptyArr') {
      return [...this.EmptyArrOperator, ...this.nullOperator];
    } else if (leftType === 'emptyStr') {
      return [...this.EmptyStrOperator, ...this.nullOperator];
    } else if (leftType === 'emptyNum') {
      return [...this.operatorOptions, ...this.nullOperator];
    } else {
      return [...this.nullOperator];
    }
  }

  private getNodeParamData() {
    const inputs: IWorkflowField[] = [];
    const configs = {
      settings: [],
    };

    this.params.forEach(param => {
      const { left, right } = cloneDeep(param);
      const input = NodeUtils.getDtoInput(left);
      input.name = (input.value.content as IRefContentType).ref_var_name?.split('.')?.pop();

      const rightVal = NodeUtils.getDtoInput(right);

      inputs.push(input);
      const leftSetting = this.getMetaInfoFromField(input);
      const rightSetting = this.getMetaInfoFromField(rightVal);
      if (rightSetting.value.type === 'operator') {
        rightSetting.value.type = 'ref';
        if (rightSetting.type.startsWith('array')) {
          rightSetting.type = 'array';
          rightSetting.schema = leftSetting.schema;
        }
        if (rightSetting.type.startsWith('object')) {
          rightSetting.type = 'object';
          rightSetting.schema = leftSetting.schema;
        }
        rightSetting.value.content = leftSetting.value.content;
      } else {
        delete rightSetting.value.operator;
      }
      configs.settings.push({
        left: leftSetting,
        right: rightSetting,
      });
    });

    return {
      inputs,
      configs,
    };
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.helpCenterService.hideHelpPanel();
    this.modelCloseSave();
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  private getMetaInfoFromField(param: IWorkflowField) {
    const { type, value, schema } = param;

    if (value.type !== 'ref') {
      if (['number', 'integer'].includes(type)) {
        value.content = Number(value.content);
      }
    }

    if (schema) {
      return {
        type,
        value,
        schema,
      };
    }

    return {
      type,
      value,
    };
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

  private getNewMemo(): IRefInfo {
    return {
      refNodeId: 'node_start',
      refNodeName: this.i18n.transform('memory_variable'),
      type: 'MemoVal',
      outputs: [],
    };
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const nodeData: ISetVariableNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      ...this.getNodeParamData(),
    };
    this.appFlowServ.setNodeSaveMonitor({ nodeData });
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
