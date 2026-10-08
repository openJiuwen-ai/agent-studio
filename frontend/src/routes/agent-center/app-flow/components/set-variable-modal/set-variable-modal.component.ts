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
      const { type = '' } = (param.value.content[0] as IParamRef) || {};
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
      const { type = '' } = (param.value.content[0] as IParamRef) || {};
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

    this.leftRefs = this.buildLeftRefs();

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
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

  /**
   * 构建左值（目标变量）引用选项：循环中间变量 + 赋值型记忆变量 + 请求变量。
   * 抽出以便引用变化时重建，令左值类型随变量改型实时刷新。
   */
  private buildLeftRefs(): IParamRef[] {
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
    return refs;
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
      // 引用变化时左值选项可能已更新（如循环中间变量改型）：重建并重选左值，
      // 令 left.value.content/type 反映当前类型，再据此收敛右值与菜单。
      this.leftRefs = this.buildLeftRefs();
      let menusChanged = false;
      this.params.forEach(param => {
        const { left, right } = param;

        left.refs = cloneDeep(this.leftRefs);
        NodeUtils.selectTreeNodeInRefsChhangeByValue(left);

        if (right.value.operator) {
          right.value.type = 'operator';
        }

        NodeUtils.reSelectRefWithNewOps(
          right,
          NodeUtils.narrowRefOption(this.rightRefs, {
            type: (this.isGetLeftType(left) || left.type) as IWorkflowFieldType,
          })
        );

        if (this.refreshMenusByLiveType(param)) {
          menusChanged = true;
        }
      });
      if (menusChanged) {
        this.changeUpdateTime();
      }
    }

    this.isInit = false;
  }

  /**
   * 依据左值当前引用类型刷新「值」选项与运算赋值菜单，并收敛右侧来源/运算符：
   * - 外部（循环中间变量/记忆变量等）改型后，重开节点或引用刷新即可得到正确选项，无需重选左值；
   * - 右侧来源(type)已不在可选集合、或左值变为 complex 后 literal 不可选时，回退 ref；
   * - 旧运算符已不被新类型支持时归一到 null(empty)，避免脏值入库。
   * 返回是否发生了收敛（供调用方据此标记脏、触发落库，避免归一结果不写回）。
   */
  private refreshMenusByLiveType(param: IVal): boolean {
    param.operatorOpts = this.getOperatorOptions(param);

    const liveLeftType = (this.isGetLeftType(param.left) ||
      param.left.type) as IWorkflowFieldType;
    const liveType = (liveLeftType || '').toLowerCase();
    const isComplex = this.getLeftParamsType(param.left) === 'complex';
    const baseOpts = isComplex ? this.refOnlyOptions : this.sourceOptions;
    param.typeOpts = hasEmptyType.includes(liveType)
      ? [...baseOpts, ...this.commonOperatorOptions]
      : baseOpts;

    let changed = false;

    // 右值类型同步为左值实时类型：否则模板仍按旧类型渲染字面量输入、
    // getMetaInfoFromField 也按旧类型转换内容，写出与左值类型不一致的右侧配置
    if (liveLeftType && param.right.type !== liveLeftType) {
      param.right.type = liveLeftType;
      changed = true;
    }

    // 收敛「值」来源：当前模式已不在可选集合，或左值变 complex 后 literal 不可选 → 回退 ref；
    // 同时用 getChangeContent 重置内容（与 onLeftSelect 对齐），避免旧的 literal 内容
    // 在保存时被 getDtoInput 误当引用、写出 ref_node_id/ref_var_name 为 undefined 的脏 ref
    const rightSource = param.right?.value?.type;
    const sourceStillValid = param.typeOpts.some(
      (option) => option.value === rightSource
    );
    const shouldRevertToRef =
      rightSource !== 'ref' &&
      (!sourceStillValid || (isComplex && rightSource === 'literal'));
    if (shouldRevertToRef) {
      param.right.value.type = 'ref';
      param.right.value.content = NodeUtils.getChangeContent('ref');
      changed = true;
    }

    // 收敛运算符：旧运算符已被新类型菜单剔除 → null(empty)
    if (param.right?.value?.type === 'operator') {
      const operatorStillValid = param.operatorOpts.some(
        (option) => option.value === param.right.value.operator
      );
      if (!operatorStillValid) {
        param.right.value.operator = 'empty';
        changed = true;
      }
    }

    return changed;
  }

  public initParams() {
    if (!this.nodeInfo.inputs.length) {
      this.addParam();
      return;
    }

    let menusChanged = false;

    this.params = this.nodeInfo.inputs.map((input: any, index) => {
      const left: IWorkflowField = {
        ...cloneDeep(input),
        refs: cloneDeep(this.leftRefs),
      };

      NodeUtils.selectTreeNodeInRefsChhangeByValue(left);

      const setting = this.nodeInfo.configs.settings[index];

      let queryType = left.type;
      if (typeof queryType === 'string' && queryType.startsWith('array')) {
        // left.schema 可能缺失（如复杂类型中间变量经 getDtoInput 保存后 type='array' 且无 schema），
        // 需回退引用节点的 schema/type，否则访问 left.schema.type 会抛错导致面板初始化失败
        const leftSchema = left.schema as IWorkflowField | undefined;
        const refContent = left.value?.content?.[0] as any;
        const elementType =
          leftSchema?.type ?? refContent?.schema?.type ?? refContent?.type;
        if (elementType) {
          queryType = `${queryType}<${elementType}>` as IWorkflowFieldType;
        }
        const refSchemaType = refContent?.schema?.type;
        if (refSchemaType && leftSchema?.type !== refSchemaType) {
          queryType = `${left.type}<${refSchemaType}>` as IWorkflowFieldType;
        }
      }

      if (left.value?.content?.[0]?.type && left.type !== left.value.content[0].type) {
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

      if (right.value.operator) {
        right.value.type = 'operator';
      }

      const param: IVal = { left, right };
      if (this.refreshMenusByLiveType(param)) {
        menusChanged = true;
      }
      return param;
    });

    if (menusChanged) {
      this.changeUpdateTime();
    }
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
    if (hasEmptyType.includes((this.isGetLeftType(param.left) || '').toLowerCase())) {
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
        if (rightSetting.type?.startsWith('array')) {
          rightSetting.type = 'array';
          rightSetting.schema = leftSetting.schema;
        }
        if (rightSetting.type?.startsWith('object')) {
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
