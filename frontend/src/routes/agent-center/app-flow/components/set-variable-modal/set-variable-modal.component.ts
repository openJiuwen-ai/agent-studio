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
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
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
 * 语义有双重性，改动时须同时看 applyLeftTypeToParam 的两个分支：
 * 1. **operator 可用性**：命中即把 commonOperatorOptions 并入 typeOpts；
 * 2. **literal 可用性**：未命中则整组来源退化为 refOnly（连 operator 也没有）。
 * 例外：'object' 虽在此表内（literal 实际不可用），但 operator 对 object 可用；
 * 其 literal 由 isComplex 守卫强制剔除（baseOpts 退回 refOnly 后再由 shouldRevertToRef 回退来源）。
 * 因此调整此表 ≠ 仅决定"literal 能否选"，还同时影响 operator 菜单。
 */
const hasEmptyType = ['integer', 'number', 'string', 'boolean', 'object', 'array<string>', 'array<number>', 'array<integer>', 'array<boolean>'];
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
    TypedJsonInputComponent,
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
    const { type } = (param.value.content?.[0] as IParamRef) || {};
    return type;
  }

  public getParamType(param: IWorkflowField) {
    if (
      param.value.type === 'ref' &&
      Array.isArray(param.value.content) &&
      param.value.content.length
    ) {
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
        NodeUtils.selectTreeNodeInRefsChhangeByValue(left, true);

        // 左值引用已失效（目标变量被删除/改名或尚未加载完成）时，isGetLeftType 取不到实时类型，
        // 若继续按陈旧的 left.type 收敛，会生成与实际左值不符的来源菜单/运算符，并把右值
        // 按旧类型改写后落库，形成不一致数据。故此处跳过本轮收敛，待用户重选左值后再处理。
        if (!this.isGetLeftType(left)) {
          return;
        }

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
    // 复杂类型对象只暴露 ref；array<scalar> 允许字面量（复用 typed-json-input 输入 JSON，与 loop-modal / global-memory 一致）。
    // object / array<object> 因无 addChild 定义子结构能力，仍仅暴露 ref（与 loop-modal midVarDataTypes 口径一致）。
    const isComplex = liveType === 'object';
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
    // ref 来源维持所选引用节点的真实类型（由 getDtoInput 按引用节点类型回写），
    // 不在此强制同步为左值类型，避免 string 左值 + file/* 右值等兼容但类型串不同的引用
    // 每次打开被改写为左值类型、触发 tagCompareNoChange 判脏、反复保存/未保存提示。
    //
    // 落库时 operator 来源会把 array<X>/object<X> 的 right.type 归一为通用 'array'/'object'
    // （见 getNodeParamData），而重新打开时 liveLeftType 仍是具体的 'array<X>'。若按字串严格比较，
    // 二者永远不等 → 每次打开都回写 liveLeftType 并标记 changed → tagCompareNoChange 恒 false →
    // 用户未编辑也提示未保存、反复落库；保存后又写回 'array'，下次打开再次触发，形成永久脏标记。
    // 故按「类型族」归并比较（array*⇔array、object*⇔object），仅在类型族真正变化时才同步并标记 changed。
    if (
      liveLeftType &&
      param.right.value.type !== 'ref' &&
      !this.isSameTypeGroup(param.right.type, liveLeftType, param.right.value.type)
    ) {
      const oldRightType = param.right.type;
      param.right.type = liveLeftType;
      if (param.right.value.type === 'literal') {
        // 旧内容可转换为新类型时尽量保留（如 string '123' → integer 123），
        // 仅在确实非法时回退默认值，避免静默数据丢失（意见④）。
        param.right.value.content = this.coerceLiteralContent(
          param.right.value.content,
          oldRightType,
          liveLeftType,
        );
      }
      changed = true;
    }

    // array/object 字面量内容兜底：空串/空白不是合法 JSON（typed-json-input 与运行期都要求
    // 合法 JSON 数组/对象），来源切换或历史脏数据都可能留下空串，且类型相同时上面的
    // coerceLiteralContent 分支不会触发，故此处独立归一（与 loop-modal 的
    // normalizeTypedLiteralContent 口径一致），仅对空串回退默认，不覆盖用户已填内容。
    if (liveLeftType && param.right.value.type === 'literal') {
      const content = param.right.value.content;
      if (
        typeof content === 'string' &&
        content.trim() === '' &&
        this.isComplexLiteralType(liveLeftType)
      ) {
        param.right.value.content = this.defaultLiteralContent(liveLeftType);
        changed = true;
      }
    }

    // 收敛「值」来源：已非 ref 且（来源不在可选集合，或复杂左值下 literal 不可选）→ 回退 ref，
    // 同步重置内容并清除旧 operator（避免被 onRefUpdate 重新置回）
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
      delete param.right.value.operator;
      changed = true;
    }

    // 收敛引用：选中的引用节点被窄化为 disabled 时，仅当它与左值类型**真正不兼容**才清空。
    // narrowRefOption 的 disabled 是"类型串精确不等"，比真实兼容性更严（如 string ⊇ file/*），
    // 故用 getCompatibleTypes 复核，避免误清兼容引用。
    if (param.right?.value?.type === 'ref') {
      const selected = Array.isArray(param.right.value.content)
        ? (param.right.value.content[0] as any)
        : (param.right.value.content as any);
      const selectedType = selected?.type;
      const compatible =
        selectedType != null &&
        (this.getCompatibleTypes(liveLeftType) as string[]).includes(
          String(selectedType).toLowerCase(),
        );
      if (selected?.disabled && !compatible) {
        param.right.value.content = NodeUtils.getChangeContent('ref');
        changed = true;
      }
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

  /**
   * 类型族比较：array* 与 'array' 视为同族、object* 与 'object' 视为同族，其余按全等。
   * 仅 operator 来源按类型族归并：getNodeParamData 落库时会把 operator 来源的 array<X>/object<X>
   * 的 right.type 归一为通用 'array'/'object'，重新打开时 liveLeftType 仍是 'array<X>'，若按字串严格比较
   * 会永远不等、反复标记 changed（永久脏标记）；故仅 operator 来源需要族归并。
   * literal/ref 来源按完整类型（含元素类型）持久化，必须精确比较，否则 array<string>↔array<number>
   * 元素类型改型会被误判同族而漏同步 right.type，导致值输入控件/校验/落库类型错误（检视意见 B）。
   */
  private isSameTypeGroup(a?: string, b?: string, source?: string): boolean {
    if (!a || !b) {
      return false;
    }
    const x = a.toLowerCase();
    const y = b.toLowerCase();
    if (x === y) {
      return true;
    }
    if (source === 'operator' && x.startsWith('array') && y.startsWith('array')) {
      return true;
    }
    if (source === 'operator' && x.startsWith('object') && y.startsWith('object')) {
      return true;
    }
    return false;
  }

  /** 是否为需要合法 JSON 承载的字面量类型（array* / object），即 typed-json-input 覆盖的范围 */
  private isComplexLiteralType(type: IWorkflowFieldType): boolean {
    if (!type) {
      return false;
    }
    return (
      type === 'object' ||
      (typeof type === 'string' && type.startsWith('array'))
    );
  }

  /**
   * 校验 array/object 字面量内容是否为与目标类型匹配的合法 JSON。
   * 空串/空白、非字符串、解析失败、或类型不符（array 收到 object 等）均视为非法。
   * 解析内核复用 NodeUtils.parseLiteralContent（与 loop-modal 归一同源，避免重复实现）。
   */
  private isValidJsonLiteral(content: unknown, type: IWorkflowFieldType): boolean {
    const kind: 'array' | 'object' =
      type === 'object' ? 'object' : 'array';
    return NodeUtils.parseLiteralContent(content, kind) !== null;
  }

  /** literal 各类型默认内容：integer/number→0、boolean→false、object→'{}'、array*→'[]'(JSON 字符串)、其余→'' */
  private defaultLiteralContent(type: IWorkflowFieldType): string | number | boolean {
    if (type === 'boolean') {
      return false;
    }
    if (type === 'integer' || type === 'number') {
      return 0;
    }
    if (type === 'object') {
      // 与 loop-modal.component.defaultLiteralContent 保持一致：typed-json-input 期望合法 JSON 字符串，
      // 若返回 ''，将来放开 object 字面量时会拿到空内容而非 '{}'。当前 object 走 isComplex 仅 ref，此处为口径对齐。
      return '{}';
    }
    if (typeof type === 'string' && type.startsWith('array')) {
      // array/object 字面量以 JSON 字符串存储（typed-json-input 的 formatText 对 content 做 .replace，
      // 且历史上占位即字符串 '[]'），故返回字符串 '[]' 而非空数组对象，避免与 FieldValueContent 类型冲突。
      return '[]';
    }
    return '';
  }

  /**
   * literal 来源内容随左值类型变化时的转换：旧内容可转为新类型时尽量保留，
   * 仅当确实非法（如非数值字符串落到 integer）才回退类型默认值，避免静默数据丢失（意见④）。
   */
  private coerceLiteralContent(
    oldContent: unknown,
    oldType: IWorkflowFieldType,
    newType: IWorkflowFieldType,
  ): string | number | boolean {
    if (oldType === newType) {
      return (oldContent ?? this.defaultLiteralContent(newType)) as
        | string
        | number
        | boolean;
    }
    // array<scalar> / object：标量旧内容无法安全转换，回退 JSON 字符串默认值
    if (newType === 'object' || (typeof newType === 'string' && newType.startsWith('array'))) {
      return this.defaultLiteralContent(newType) as string | number | boolean;
    }
    // 目标为 string：数字/布尔转其字面量，字符串原样保留
    if (newType === 'string') {
      if (typeof oldContent === 'string') {
        return oldContent;
      }
      if (typeof oldContent === 'number' || typeof oldContent === 'boolean') {
        return String(oldContent);
      }
      return '';
    }
    // 目标为 boolean：仅 'true'/'false' 字符串可转，否则回退 false
    if (newType === 'boolean') {
      if (oldContent === true || oldContent === 'true') {
        return true;
      }
      if (oldContent === false || oldContent === 'false') {
        return false;
      }
      return false;
    }
    // 目标为 integer / number：数字字符串或数字可转，无法转换回退 0
    const num =
      typeof oldContent === 'string'
        ? Number(oldContent)
        : typeof oldContent === 'number'
          ? oldContent
          : NaN;
    if (!Number.isFinite(num)) {
      return 0;
    }
    return newType === 'integer' ? Math.trunc(num) : num;
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

      NodeUtils.selectTreeNodeInRefsChhangeByValue(left, true);

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
      // 传 true：初始化时左值类型已定，按新类型收窄后的引用树中未命中的右值引用即已失效，
      // 清空避免落旧 ref_var_name（意见②）。其余调用点（onLeftSelect 重选、新建参数）沿用默认不清空。
      NodeUtils.selectTreeNodeInRefsByValue(right, true);

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
    // 来源切换时重置内容：ref/operator 走既有重置；literal 需按左值实时类型给默认值，
    // 不能统一用 getChangeContent('literal') 的空串——左值为 array*/object 时空串不是合法 JSON，
    // 且下方的 applyLeftTypeToParam 仅在 right.type 与左值类型不同时才调 coerceLiteralContent 补默认值，
    // 二者类型相同（如从 ref/operator 切回 literal）时会被跳过，导致数组字面量以空串落库、
    // 用户已配内容被静默清空（typed-json-input 也拿不到合法 JSON 数组）。
    if (param.right.value.type === 'literal') {
      const liveLeftType = (this.isGetLeftType(param.left) ||
        param.left.type) as IWorkflowFieldType;
      param.right.value.content = this.defaultLiteralContent(
        liveLeftType ?? param.right.type,
      );
    } else {
      param.right.value.content = NodeUtils.getChangeContent(param.right.value.type);
    }
    if (param.right.value.type === 'operator') {
      let leftType = this.getParamType(param.left);
      if (leftType === 'emptyNum') {
        param.right.value.operator = 'increment';
      } else {
        param.right.value.operator = 'empty';
      }
    }
    // 来源切换后（尤其是 ref → literal/operator）右值 field 类型需同步为左值实时类型：
    // 新建时 right.type 默认 string，且 ref 阶段 applyLeftTypeToParam 会跳过 right.type 同步
    // （保留引用节点真实类型，意见⑥），故切到 literal/operator 时 right.type 仍残留旧值，
    // 会导致值输入控件、校验和落库类型错误（如 integer 左值被保存成 string literal/operator）。
    // 复用 applyLeftTypeToParam：ref 来源下其 type 同步被 guard 跳过，不影响意见⑥；
    // literal/operator 来源下则把 right.type 收敛为 liveLeftType（含 array 元素类型精确匹配）。
    this.applyLeftTypeToParam(param);
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
      // array/object 字面量以 JSON 字符串承载，保存前须保证是合法 JSON：
      // typed-json-input 在用户清空输入或键入非法 JSON 后失焦会把 content 置为空串并触发 onSave，
      // 而 applyLeftTypeToParam 的空串兜底只挂在 init/onRefUpdate/onLeftSelect/onIntegerTypeChange，
      // 覆盖不到保存这一刻；若原样落库，运行期会拿到非法 JSON。
      // 这里只对空串/非法 JSON 回退类型默认值，用户已填的合法 JSON 原样保留（对齐 loop-modal 的 getInputsDSL 口径）。
      if (this.isComplexLiteralType(type) && !this.isValidJsonLiteral(value.content, type)) {
        value.content = this.defaultLiteralContent(type);
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
