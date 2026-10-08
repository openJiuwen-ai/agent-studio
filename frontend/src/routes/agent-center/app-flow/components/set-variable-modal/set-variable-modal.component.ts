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
import { defaultLiteralContent, HAS_EMPTY_TYPE, isComplexLeftType, isMismatchedRefSelected, isOperatorOptionValid, shouldRevertSourceToRef } from '../../utils/set-variable.util';
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

const hasEmptyType = HAS_EMPTY_TYPE;
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
    // 用最新的 parentNode 而非 ngOnInit 时缓存的 loopNodeInfo：父循环节点保存后
    // onRefUpdate 重建左值选项时，需拿到最新的中间变量 inputs 才能实时刷新类型
    const refs = parentNode ? this.getLoopMidVarRefs(parentNode) : [];

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

        if (this.applyLeftTypeToParam(param)) {
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
   * 单一归一函数：按左值实时类型统一收敛「值」来源/类型/内容、引用与运算菜单。
   * init / onRefUpdate / onLeftSelect 全部走此函数，避免多处镜像实现漂移。
   * - 右值 type 同步为左值实时类型；类型变化且来源为 literal 时内容归一到新类型默认值；
   * - 来源已不在可选集合、或左值复杂后 literal 不可选 → 回退 ref（并清除旧 operator）；
   * - 选中引用被窄化为 disabled（类型不匹配）→ 清空；
   * - 旧运算符不被新类型支持 → null(empty)。
   * 返回是否发生了收敛（供调用方标记脏、触发落库）。
   */
  private applyLeftTypeToParam(param: IVal): boolean {
    const liveLeftType = (this.isGetLeftType(param.left) ||
      param.left.type) as IWorkflowFieldType;
    const liveType = (liveLeftType || '').toLowerCase();
    const isComplex = isComplexLeftType(liveLeftType);
    // 支持"空值/运算"的类型才暴露 literal/operator；复杂类型只暴露 ref
    const sourceAllowed = hasEmptyType.includes(liveType);
    const baseOpts =
      isComplex || !sourceAllowed ? this.refOnlyOptions : this.sourceOptions;
    param.typeOpts = sourceAllowed
      ? [...baseOpts, ...this.commonOperatorOptions]
      : baseOpts;
    param.operatorOpts = this.getOperatorOptions(param);

    let changed = false;

    // 右值类型同步为左值实时类型；类型变化且来源为 literal 时内容归一到新类型默认值，
    // 避免 Number('abc')=NaN / 非布尔字符串等脏值随 menusChanged 自动落库。
    if (liveLeftType && param.right.type !== liveLeftType) {
      param.right.type = liveLeftType;
      if (param.right.value.type === 'literal') {
        param.right.value.content = defaultLiteralContent(liveLeftType);
      }
      changed = true;
    }

    // 收敛「值」来源：回退 ref 时同步重置内容并清除旧 operator，
    // 避免旧 literal 内容被误当引用、以及 operator 被 onRefUpdate 重新置回。
    const rightSource = param.right?.value?.type;
    const sourceStillValid = param.typeOpts.some(
      (option) => option.value === rightSource
    );
    if (shouldRevertSourceToRef(rightSource, sourceStillValid, isComplex)) {
      param.right.value.type = 'ref';
      param.right.value.content = NodeUtils.getChangeContent('ref');
      delete param.right.value.operator;
      changed = true;
    }

    // 收敛引用：选中节点被窄化为 disabled（类型不再匹配）→ 清空
    if (
      param.right?.value?.type === 'ref' &&
      isMismatchedRefSelected(param.right.value.content)
    ) {
      param.right.value.content = NodeUtils.getChangeContent('ref');
      changed = true;
    }

    // 收敛运算符：旧运算符已被新类型菜单剔除 → null(empty)
    if (
      param.right?.value?.type === 'operator' &&
      !isOperatorOptionValid(param.operatorOpts, param.right.value.operator)
    ) {
      param.right.value.operator = 'empty';
      changed = true;
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
        // 元素类型仅取 schema（left.schema / 引用节点 schema）；refContent.type 是完整类型
        // （如 array<string>），不能当元素类型，否则会先算出 array<array<string>>。
        const elementType = leftSchema?.type ?? refContent?.schema?.type;
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
      if (this.applyLeftTypeToParam(param)) {
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
    // 按新选中左值收窄右值引用选项并重选
    param.right.refs = cloneDeep(
      NodeUtils.narrowRefOption(this.rightRefs, {
        type: selectedVal[0].type as IWorkflowFieldType,
      })
    );
    NodeUtils.selectTreeNodeInRefsByValue(param.right);
    // 统一归一：菜单 + 右值类型/内容/来源/运算符（与 init / onRefUpdate 共用同一实现）
    if (this.applyLeftTypeToParam(param)) {
      this.onSave();
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
