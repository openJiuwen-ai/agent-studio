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

/**
 * 语义有双重性，改动时须同时看 refreshMenusByLiveType / onLeftSelect 的两个分支：
 * 1. **operator 可用性**：命中即把 commonOperatorOptions 并入 typeOpts；
 * 2. **来源可用性**：未命中则整组来源退化为 refOnly（连 operator 也没有）。
 * 例外：'object' 虽在此表内，但其字面量已被 getLeftParamsType(param.left) === 'complex'
 * 收窄为 refOnlyOptions，故命中本表对 object 而言只意味着「保留 operator 选项」，
 * 并非允许选字面量。调整此表 ≠ 仅决定「字面量能否选」，还同时影响 operator 菜单。
 */
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
            // 用左值实时引用类型（循环中间变量改型后 left.type 仍是落库旧值）
            type: (this.isGetLeftType(left) || left.type) as IWorkflowFieldType,
          })
        );

        // 引用刷新后按实时类型重算来源/运算菜单：中间变量改型后无需重选变量名称即可拿到新选项
        this.refreshMenusByLiveType(param);
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
      // 按实时类型收窄后，若该右值引用在树中已彻底不存在（节点被删除/改名），则清空。
      // 注意：narrowRefOption 只把类型不匹配的节点置为 disabled（节点仍在树中），
      // 而 reSelectRefWithNewOps 仅按 ref_node_id/ref_var_name 匹配、不检查 disabled，
      // 因此被置灰的引用仍会保留为选中态 —— 这是全仓各节点既有行为，本处不做改动。
      NodeUtils.reSelectRefWithNewOps(
        right,
        cloneDeep(NodeUtils.narrowRefOption(this.rightRefs, { type: queryType })),
      );

      if (right.value.operator) {
        right.value.type = 'operator';
      }

      // 菜单按左值「实时类型」计算（queryType 已取自left.value.content[0].type）。
      // 原实现误用 setting.left.type（落库的旧类型），导致循环中间变量改型后重开节点，
      // 运算下拉仍停留在旧类型的选项集合（如 string→integer 后缺少「变量自增/自减」），
      // 必须重选一遍变量名称才会更新。
      const param: IVal = { left, right, typeOpts: [], operatorOpts: [] };
      this.refreshMenusByLiveType(param);
      return param;
    });
  }

  /**
   * 依据左值当前引用类型刷新「值」来源选项与运算赋值菜单。
   * 左值（循环中间变量等）在外部改型后，重开节点或引用刷新即可得到正确选项，无需重选左值；
   * 旧运算符若已不被新类型支持，则归一到 null(empty)，避免脏值入库。
   */
  private refreshMenusByLiveType(param: IVal) {
    param.operatorOpts = this.getOperatorOptions(param);

    const liveType = (
      this.isGetLeftType(param.left) ||
      param.left.type ||
      ''
    ).toLowerCase();
    // 复合类型判定与上面的 hasEmptyType 判定同源，均取自 liveType：
    // 等价于 getLeftParamsType 的 object/array 判定，但在左值引用内容缺失时不会退化为 normal
    // （上游 initParams 原按落库 setting.left.type 判定，此处以 `|| param.left.type` 保留同等兜底）。
    const baseOpts =
      liveType === 'object' || liveType.startsWith('array')
        ? this.refOnlyOptions
        : this.sourceOptions;
    param.typeOpts = hasEmptyType.includes(liveType)
      ? [...baseOpts, ...this.commonOperatorOptions]
      : baseOpts;

    // 与 onLeftSelect（其中 `param.right.type = selectedVal[0].type`）对齐：
    // 右值字段类型同步为左值实时类型。否则中间变量改型后重开节点，right.type 仍是落库旧值
    // （如 string），却已能选到新类型的运算符（increment），保存出类型矛盾的配置；
    // literal 分支也会继续按旧类型渲染与转换。
    if (liveType) {
      param.right.type = liveType as IWorkflowFieldType;
    }

    this.normalizeValueByMenus(param);
  }

  /**
   * 菜单（typeOpts / operatorOpts）刷新后校正已存值，供 initParams / onRefUpdate / onLeftSelect 三条路径共用。
   *
   * 1. 来源下拉已不含「运算赋值」→ 清除残留运算符，并把 operator 态回退为 ref。
   *    只回退 type 而不删 operator 是不够的：initParams / onRefUpdate 里
   *    `if (right.value.operator) { right.value.type = 'operator'; }` 会把节点重新拉回运算态，
   *    而此时运算下拉里并没有这个运算符。
   * 2. 来源仍支持运算，但旧运算符不被新类型支持（如 integer→string 后残留「变量自增」）
   *    → 归一到 'empty'，避免脏运算符随节点保存。
   */
  private normalizeValueByMenus(param: IVal) {
    const operatorAvailable = param.typeOpts.some((option) => option.value === 'operator');
    const currentType = param.right?.value?.type;
    const currentSupported = param.typeOpts.some((option) => option.value === currentType);

    // 1. 来源下拉已不含「运算赋值」→ 清除残留运算符。
    //    只回退 type 而不删 operator 是不够的：initParams / onRefUpdate 里
    //    `if (right.value.operator) { right.value.type = 'operator'; }` 会把节点重新拉回运算态，
    //    而此时运算下拉里并没有这个运算符。
    if (!operatorAvailable) {
      delete param.right.value.operator;
    }

    // 2. 当前来源已不在选项中 → 回退为 ref 并重置内容。
    //    覆盖两种情形：类型不再支持运算赋值（operator 被剔除）、左值变为 complex 后 literal 被剔除。
    //    后者若不处理，模板的来源下拉没有 literal 选项却仍渲染字面量输入框，保存出与左值不匹配的字面量。
    if (!currentSupported) {
      param.right.value.type = 'ref';
      param.right.value.content = NodeUtils.getChangeContent('ref');
      return;
    }

    // 3. 来源仍支持运算，但旧运算符不被新类型支持（如 integer→string 后残留「变量自增」）
    //    → 归一到 'empty'，避免脏运算符随节点保存。
    if (currentType !== 'operator') {
      return;
    }

    const operatorStillValid = param.operatorOpts.some(
      (option) => option.value === param.right.value.operator
    );
    if (!operatorStillValid) {
      param.right.value.operator = 'empty';
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

    // 按新类型收窄后，若该右值引用在树中已彻底不存在（节点被删除/改名），则清空。
    // 注意：narrowRefOption 只把类型不匹配的节点置为 disabled（节点仍在树中），
    // 而 reSelectRefWithNewOps 仅按 ref_node_id/ref_var_name 匹配、不检查 disabled，
    // 因此被置灰的引用仍会保留为选中态 —— 这是全仓各节点既有行为，本处不做改动。
    NodeUtils.reSelectRefWithNewOps(param.right, param.right.refs);

    if (this.getLeftParamsType(param.left) === 'complex' && param.right.value.type === 'literal') {
      param.right.value.type = 'ref';
      this.onIntegerTypeChange(param);
    }

    // 与 initParams / onRefUpdate 对齐：菜单按实时类型重算后，旧的运算符值若已不被支持则归一，
    // 来源已不含「运算赋值」时清掉残留运算符（否则重开节点会被 `if (value.operator)` 拉回运算态）。
    this.normalizeValueByMenus(param);
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
