import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { Graph } from '@antv/x6';

import { I18nNamespace } from '@i18n';
import {
  IntegerStrValidatorDirective,
  NumberStrValidatorDirective,
  PositiveIntLoopValidatorDirective,
  PositiveIntValidatorDirective,
  RefSelectedRequireDirective,
} from '@shared/directives/common-validator.directive';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { takeUntil } from 'rxjs';
import { ParamLabelPipe } from 'src/pipes/param-label.pipe';
import { AppFlowService } from '../../app-flow.service';
import {
  getInitInputParamConfig,
  getInitRefParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  WORKFLOW_SVGS,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import {
  HasOutputsNode,
  IBranchCondition,
  IRefContentType,
  IWorkflowFieldType,
  LoopType,
  NodeInfo,
  NoOutputsNodeTypes,
  type ILoopNode,
  type IParamRef,
  type IWorkflowField,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { BranchUtils } from '../branch.utils';
import { ParamTreeSelectedComponent } from '../param-tree/param-tree-selected.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { NodeUtils } from '../utils';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';

@Component({
  selector: 'meta-loop-modal',
  templateUrl: './loop-modal.component.html',
  styleUrls: ['./loop-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    ParamLabelPipe,
    RefSelectedRequireDirective,
    AddPropsIconComponent,
    PositiveIntValidatorDirective,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    ParamTreeComponent,
    ParamTreeSelectedComponent,
    PositiveIntLoopValidatorDirective,
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
export class LoopModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: ILoopNode;

  @ViewChild('midParamForm') midParamForm: NgForm;

  @ViewChild('outputForm') outputForm: NgForm;

  @ViewChild('numLoopVarForm') numLoopVarForm: NgForm;

  @ViewChild('arrForm') arrForm: NgForm;

  @ViewChild('conditionForm') conditionForm: NgForm;

  @Output('confirm') confirm = new EventEmitter<any>();

  public icon = WORKFLOW_SVGS.Loop;

  public loopTypes = [
    {
      label: this.i18n.transform('using_array_loop'),
      value: 'arrayLoop',
    },
    {
      label: this.i18n.transform('specify_the_cycles'),
      value: 'numLoop',
    },
  ];

  public loopType: LoopType = 'numLoop';

  public nameRefOptions: IParamRef[] = [];

  public arrOnlyOptions: IParamRef[] = [];

  public intOnlyOptions: IParamRef[] = [];

  public outputOptions: IParamRef[] = [];

  public conditionOps: IParamRef[] = [];

  public midParams: IWorkflowField[] = [];

  public arrParams: IWorkflowField = {
    ...getInitInputParamConfig(),
    name: 'arr_loop_var',
    value: {
      type: 'ref',
      content: [],
      hint: '',
    },
    source: 'pre_defined',
  };

  public outputParams: IWorkflowField[] = [];

  public noneObjDataTypes = getNoneObjOutputParamTypes();

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public refOnlyOptions = [{ label: this.i18n.transform('ref'), value: 'ref' }];

  public outputDataTypes = getOutputParamTypes();

  onOutputParamTypeChange = NodeUtils.onOutputParamTypeChange;

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public isSimpleType = NodeUtils.isSimpleType;

  public addChild = NodeUtils.addChild;

  public loopTimes = 5;

  public numLoopVar: IWorkflowField = {
    name: 'num_loop_var',
    type: 'integer',
    description: this.i18n.transform('loop_num'),
    required: true,
    source: 'pre_defined',
    value: {
      type: 'literal',
      content: 5,
      hint: '',
      default: '',
    },
  };

  public graph: Graph = null;

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }

  public emptyModel = '';

  public strConditionOptions = BranchUtils.getStrConditionOptions(this.i18n);

  public arrConditionOptions = BranchUtils.getArrConditionOptions(this.i18n);

  public numConditionOptions = BranchUtils.getNumConditionOptions(this.i18n);

  public boolConditionOptions = BranchUtils.getBoolConditionOptions(this.i18n);

  public objConditionOptions = BranchUtils.getObjConditionOptions(this.i18n);

  public booleanOps = BranchUtils.getBooleanOps();

  public emptyOps = [];

  public conditionConf = BranchUtils.getNewBranchConfigs(this.conditionOps);

  public onExpChange = BranchUtils.onExpChange;

  public iconClassNameMap = BranchUtils.getConditionOpIconClassName;

  public requestVariables;
  updateTimeout: any = null;

  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
  ) {
    super(nodeServ, appFlowServ);
  }

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);

    super.ngOnInit();

    this.graph = this.appFlowServ.getGraph();

    this.nodeServ
      .refInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info) => {

        const info_list = NodeUtils.refInfo2Tree(info);
        this.requestVariables = this.appFlowServ.requestVariablesFn(info_list);

        this.nameRefOptions = [...info_list,...this.requestVariables];

        const arr_only_options = NodeUtils.refInfo2Tree(info, { arrOnly: true });
        this.arrOnlyOptions = [...arr_only_options,...this.requestVariables];

        const intOnly = NodeUtils.refInfo2Tree(info, { intOnly: true });
        this.intOnlyOptions =[...intOnly,...this.requestVariables];

        this.conditionOps = this.getFreshConditionOps(this.nodeInfo);

        if (this.isInit) {
          this.arrParams = this.getArrloopParam();
          this.midParams = this.getMidParams();
          this.numLoopVar = this.getNumLoopVar();

          this.initConditionRefs();
        } else {
          NodeUtils.reSelectRefWithNewOps(this.arrParams, this.arrOnlyOptions);
          NodeUtils.reSelectRefsWithNewOps(this.midParams, this.nameRefOptions);
          NodeUtils.reSelectRefWithNewOps(this.numLoopVar, this.intOnlyOptions);

          this.conditionConf.conditions.forEach((con) => {
            NodeUtils.reSelectRefWithNewOps(con.left, this.conditionOps);

            if (con.right?.value?.type === 'ref') {
              NodeUtils.reSelectRefWithNewOps(con.right, this.conditionOps);
            }
          });
        }

        this.isInit = false;
      });

    this.outputOptions = this.initOutputOptions();
    this.outputParams = this.getInitOutput();
    this.appFlowServ
      .loopInnerRalUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((updateAction) => {
        if (updateAction && updateAction.loopNodeId === this.nodeInfo.id) {
          if (updateAction.action === 'add') {
            const refTree = this.getNodeRefTree(updateAction.childNodeId);
            if (refTree) {
              this.outputOptions.push(refTree);
            }
          }

          if (updateAction.action === 'delete') {
            this.outputOptions = this.outputOptions.filter(
              (op) => op.ref_node_id === updateAction.childNodeId,
            );
          }
        }
      });

    this.loopType = this.nodeInfo.configs.loop_type;
    this.loopTimes =
      (this.nodeInfo.inputs.find((input) => input.name === 'num_loop_var')
        ?.value?.content as number) ?? 5;
    this.updateConditionOps();
    this.onMidRefChange(true);
  }

  ngAfterViewInit(): void {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  dismiss(): void { }

  close(): void { }

  public reSelectConditionRef() {
    this.conditionConf.conditions.forEach((con) => {
      NodeUtils.reSelectRefWithNewOps(con.left, this.conditionOps);

      if (con.right?.value?.type === 'ref') {
        NodeUtils.reSelectRefWithNewOps(con.right, this.conditionOps);
      }
    });
  }

  public updateConditionOps() {
    this.conditionOps = this.getFreshConditionOps(this.getNodeData());
    this.reSelectConditionRef();
  }

  public initConditionRefs() {
    const conditionConfCopy = cloneDeep(this.nodeInfo.configs?.break_condition);

    if (conditionConfCopy) {
      conditionConfCopy.conditions = conditionConfCopy.conditions.map(
        (condition) => {
          return BranchUtils.buildViewCondition(condition, this.conditionOps);
        },
      );

      this.conditionConf = conditionConfCopy;
    } else {
      this.conditionConf = {
        logic: 'and',
        conditions: [],
      };
    }
  }

  public leftTypeChange = BranchUtils.leftTypeChange;

  onTypeChange = BranchUtils.onTypeChange;

  public deleteExp(index: number): void {
    this.conditionConf.conditions.splice(index, 1);
    this.onSave();
  }

  private getFreshConditionOps(nodeInfo: ILoopNode) {
    return [...cloneDeep(this.nameRefOptions), this.getLoopRefs(nodeInfo)];
  }

  private getBranchConditionObj(): IBranchCondition {
    return BranchUtils.getBranchConditionObj(this.conditionOps);
  }

  public addIfCondition() {
    this.conditionConf.conditions.push(this.getBranchConditionObj());
    this.onSave();
  }

  public isStrType(type: IWorkflowFieldType) {
    if (type === 'string' || type?.startsWith('file')) {
      return true;
    }

    return false;
  }

  public opChange = BranchUtils.opChange;

  public canFillStr(type: IWorkflowFieldType) {
    if (
      ['string', 'object'].includes(type) ||
      type.toLowerCase().startsWith('file')
    ) {
      return true;
    }

    return false;
  }

  public onLoopTypeChange() {
    if (
      !(
        this.loopType === 'arrayLoop' &&
        !(this.arrParams.value.content as IParamRef[]).length
      )
    ) {
      this.updateConditionOps();
    }
    this.onSave();
  }

  validateNode() {
    if (this.loopType === 'arrayLoop') {
      this.arrForm.form.markAllAsTouched();
    }

    if (this.loopType === 'numLoop') {
      this.numLoopVarForm.form.markAllAsTouched();
    }

    this.midParamForm.form.markAllAsTouched();
    this.outputForm.form.markAllAsTouched();

    if (this.conditionConf.conditions.length) {
      this.conditionForm.form.markAllAsTouched();
    }
  }

  getNodeData(): ILoopNode {
    return {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      inputs: this.getInputsDSL(),
      outputs: this.getOutputsDSL(),
      configs: {
        loop_type: this.loopType,
        loop_body: this.getLoopBody(),
      },
    };
  }

  getLoopBody() {
    const children = this.graph.getCellById(this.nodeInfo.id).getChildren();
    if (children) {
      return children
        .filter(
          (child) =>
            this.graph.isNode(child) &&
            !['LoopInput', 'LoopOutput'].includes(
              // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
              (child?.data?.ngArguments?.nodeInfo as NodeInfo).type,
            ),
        )
        .map((child) => child.id);
    }

    return [];
  }

  getInputsDSL(): IWorkflowField[] {
    const inputs: IWorkflowField[] = [];

    if (this.loopType === 'arrayLoop') {
      inputs.push(NodeUtils.getDtoInput(cloneDeep(this.arrParams)));
    } else {
      const dto = NodeUtils.getDtoInput(cloneDeep(this.numLoopVar));
      if (
        dto.value.type === 'literal' &&
        typeof dto.value.content === 'string'
      ) {
        dto.value.content = Number(dto.value.content);
      }
      inputs.push(dto);
    }

    if (this.midParams && this.midParams.length) {
      inputs.push({
        name: 'intermediate_loop_var',
        type: 'object',
        description: this.i18n.transform('sharing_parameters_between_loops'),
        required: true,
        source: 'pre_defined',
        value: {
          type: 'nested',
          content: null,
          hint: '',
          default: '',
        },
        schema: NodeUtils.getDtoInputs(
          this.midParams.filter((param) => param.name),
        ),
      });
    }

    return inputs;
  }

  getOutputsDSL() {
    const outputs: IWorkflowField[] = [];
    this.outputParams.forEach((output) => {
      const outputCopy = cloneDeep(output);
      const content = outputCopy.value.content;

      if (
        Array.isArray(content) &&
        !(content[0] as IRefContentType).ref_var_name.startsWith(
          'intermediate_loop_var',
        )
      ) {
        const contentItem = content[0];
        const originType = contentItem.type as IWorkflowFieldType;
        contentItem.type = `array<${originType}>` as IWorkflowFieldType;

        const newSchema: IWorkflowField = {
          type: originType,
          name: '',
        };

        if (contentItem?.schema) {
          newSchema.schema = contentItem.schema;
        }

        contentItem.schema = newSchema;
      }
      if (
        Array.isArray(content) &&
        (content[0] as IRefContentType).ref_var_name.startsWith(
          'intermediate_loop_var',
        )
      ) {
        const contentItem = content[0];
        contentItem.source = 'pre_defined';
      }

      outputs.push(NodeUtils.getDtoInput(outputCopy));
    });

    return outputs;
  }

  onMidNameChange() {
    window.setTimeout(() => {
      this.midParamForm?.form.markAllAsTouched();
    });
  }

  onArrNameChange() {
    window.setTimeout(() => {
      this.arrForm?.form.markAllAsTouched();
    });
  }

  onOutputParamChange() {
    window.setTimeout(() => {
      this.outputForm?.form.markAllAsTouched();
    });
    this.onSave();
  }

  getNames(
    arr: IWorkflowField[],
    index: number,
  ): {
    existingValues: string[];
  } {
    const names = arr.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  public deleteParam(arr: IWorkflowField[], index: number): void {
    arr.splice(index, 1);
    this.onSave();
  }

  public deleteMidParam(arr: IWorkflowField[], index: number): void {
    const midRefs = this.getMidRefs();
    if (midRefs) {
      const targetIndex = midRefs.children.findIndex(
        (child) => child.name === arr[index].name,
      );

      if (targetIndex !== -1) {
        midRefs.children.splice(targetIndex, 1);
      }
    }

    this.deleteParam(arr, index);

    this.onMidParamUpdate();

    this.updateConditionOps();
  }

  onMidRefChange(init?: boolean) {
    const newMidRefs: IParamRef[] = [];
    this.midParams.forEach((param) => {
      if (
        (param.name && param.value.type === 'literal' && param.value.content) ||
        (param.value.type === 'ref' &&
          (param.value.content as IParamRef[]).length)
      ) {
        const paramCopy = cloneDeep(param);

        let willPush: Partial<IParamRef> = {
          ref_node_id: this.nodeInfo.id,
          ref_var_name: `intermediate_loop_var.${paramCopy.name}`,
          name: paramCopy.name,
          checked: false,
          isHover: false,
        };

        if (paramCopy.value.type === 'literal') {
          willPush.source = 'pre_defined';
          willPush.type = 'string';
        } else {
          willPush = {
            ...paramCopy.value.content[0],
            ...willPush,
          };
        }

        newMidRefs.push(willPush as IParamRef);
      }
    });

    const midRefObj = this.getMidRefs();

    if (midRefObj) {
      midRefObj.children = newMidRefs;
    } else {
      this.outputOptions.push({
        ...this.getEmptyLoopRef(this.nodeInfo.id, this.nodeInfo.name),
        children: newMidRefs,
      });
    }

    NodeUtils.reSelectRefsWithNewOps(this.outputParams, this.outputOptions);

    this.updateConditionOps();
    if (!init) {
      this.onSave();
    }
  }

  onParamTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  onMidParamTypeChange(row: IWorkflowField) {
    this.onParamTypeChange(row);
    if (row.value.type === 'literal') {
      row.type = 'string';
    }

    this.onMidRefChange();
  }

  onLoopNumTypeChange(row: IWorkflowField) {
    this.onParamTypeChange(row);
    if (row.value.type === 'literal') {
      row.value.content = 5;
      row.type = 'integer';
    }
    this.onSave();
  }

  public addMidParam(arr: IWorkflowField[], ops: IParamRef[]) {
    arr.push({
      ...getInitInputParamConfig(),
      source: 'pre_defined',
      refs: cloneDeep(ops),
    });
    this.onSave();
  }

  public addOutputParam(arr: IWorkflowField[], ops: IParamRef[]) {
    arr.push({
      ...getInitRefParamConfig(),
      refs: cloneDeep(ops),
    });
    this.onSave();
  }

  public getMidParams(): IWorkflowField[] {
    const currentParams = this.nodeInfo.inputs.find(input => input.name === 'intermediate_loop_var');

    if (currentParams) {
      const res = NodeUtils.initInputs(currentParams.schema as IWorkflowField[], this.nameRefOptions);
      let save = false;
      res?.forEach(resItem => {
        let paramsType = resItem.type;
        if (paramsType === 'array') {
          paramsType = `array<${(resItem as any)?.schema?.type}>` as IWorkflowFieldType;
        }
        if (resItem?.value?.content[0]) {
          if (resItem?.value?.content[0]?.type !== paramsType) {
            save = true;
          }
          resItem.type = resItem?.value?.content[0]?.type;
        }
      });
      if (save) {
        setTimeout(() => {
          this.changeUpdateTime();
          this.handelSave();
        }, 30);
      }
      return res;
    }

    return [];
  }

  allAreIntegerType(data) {
    // 首先确保传入的是数组
    if (!Array.isArray(data)) {
      return false;
    }
    // 检查数组是否为空
    if (data.length === 0) {
      return false;
    }
    // 使用 every() 方法判断每个对象的 type 是否为 "integer"
    return data.every((item) => item.type === 'integer');
  }

  public getNumLoopVar(): IWorkflowField {
    const numLoopVar = this.nodeInfo.inputs.find(
      (input) => input.name === 'num_loop_var',
    );

    if (numLoopVar) {
      const numLoopVarClone = cloneDeep(numLoopVar);
      numLoopVarClone.refs = cloneDeep(this.intOnlyOptions);
      NodeUtils.selectTreeNodeInRefsByValue(numLoopVarClone);
      if (!this.allAreIntegerType(numLoopVarClone.value.content)) {
        if (typeof numLoopVarClone.value.content !== 'number') {
          numLoopVarClone.value.content = null;
        }
      }
      return numLoopVarClone;
    }

    return {
      name: 'num_loop_var',
      type: 'integer',
      description: this.i18n.transform('loop_num'),
      required: true,
      source: 'pre_defined',
      value: {
        type: 'literal',
        content: 5,
        hint: '',
        default: '',
      },
      refs: cloneDeep(this.intOnlyOptions),
    };
  }

  public getArrloopParam(): IWorkflowField {
    const currentParams = this.nodeInfo.inputs.find(
      (input) => input.name === 'arr_loop_var',
    );
    const refs = cloneDeep(this.arrOnlyOptions);

    if (currentParams) {
      const loop = cloneDeep(currentParams);
      loop.refs = refs;
      NodeUtils.selectTreeNodeInRefsByValue(loop);
      return loop;
    }

    return {
      ...getInitInputParamConfig(),
      name: 'arr_loop_var',
      value: {
        type: 'ref',
        content: [],
        hint: '',
      },
      source: 'pre_defined',
      refs,
    };
  }

  public getMidRefs() {
    return this.outputOptions.find((op) => op.name === this.nodeInfo.name);
  }

  public onMidParamUpdate() {
    NodeUtils.reSelectRefsWithNewOps(this.outputParams, this.outputOptions);
  }

  private initOutputOptions() {
    const ops = [...this.getChildrenRefs(this.nodeInfo.id)];
    const mid = this.nodeInfo.inputs.find(
      (input) => input.name === 'intermediate_loop_var',
    );

    if (mid) {
      const midCopy = cloneDeep(mid);
      const midRef = this.getEmptyLoopRef(this.nodeInfo.id, this.nodeInfo.name);
      const intermediateObjRefs = NodeUtils.fields2RefParams(
        [midCopy],
        midRef.ref_node_id,
        [],
      );

      if (intermediateObjRefs.length) {
        midRef.children = intermediateObjRefs[0].children;
      }
      const newNidref = this.setNewMidRef(midRef);
      ops.push(newNidref);
    }
    if(this.requestVariables){
      ops.push(...this.requestVariables)
    }

    return ops;
  }

  private setNewMidRef(midRef) {
    midRef?.children?.forEach((midChild) => {
      const find = this.midParams?.find(
        (item) => item?.name === midChild?.name,
      );
      if (find) {
        midChild.type = find.type;
      }
    });
    return midRef;
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }

  // TODO merge with system feat
  private getChildrenRefs(id: string): IParamRef[] {
    const cell = this.graph.getCellById(id);
    if (cell) {
      const children = cell.getChildren();

      if (children) {
        return cell
          .getChildren()
          .map((child) => this.getNodeRefTree(child.id))
          .filter((child) => child !== null);
      }

      return [];
    }

    return [];
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  private getNodeRefTree(id: string): IParamRef {
    const cell = this.graph.getCellById(id);
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    const nodeData = cell?.getData()?.ngArguments?.nodeInfo as NodeInfo;

    if (
      cell &&
      nodeData &&
      !NoOutputsNodeTypes.includes(nodeData.type) &&
      (nodeData as HasOutputsNode).outputs.length
    ) {
      const { outputs, name, type } = nodeData as HasOutputsNode;

      return {
        ref_node_id: id,
        ref_var_name: '',
        name,
        isTop: true,
        type,
        source: 'user',
        expanded: true,
        children: NodeUtils.fields2RefParams(outputs, id, [], {
          disableArr: true,
        }),
      };
    }

    return null;
  }

  onSave() {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  private getInitOutput() {
    // unbox the arr type of children cmps
    const outputs = this.nodeInfo.outputs.map((output) => {
      const outputCopy = cloneDeep(output);
      const { ref_var_name } = outputCopy.value?.content as IRefContentType;

      if (
        ref_var_name &&
        !ref_var_name.startsWith('intermediate_loop_var') &&
        outputCopy.type.startsWith('array')
      ) {
        // unboxing
        outputCopy.type = (output.schema as IWorkflowField).type;
        if (outputCopy.type === 'object') {
          outputCopy.schema = (outputCopy.schema as IWorkflowField).schema;
        }
      }

      outputCopy.refs = cloneDeep(this.outputOptions);
      NodeUtils.selectTreeNodeInRefsByValue(outputCopy);

      return outputCopy;
    });

    if (!outputs.length) {
      outputs.push({
        ...getInitRefParamConfig(),
        refs: cloneDeep(this.outputOptions),
      });
    }

    return outputs;
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const nodeData: ILoopNode = this.getNodeData();

    if (this.conditionConf.conditions.length) {
      nodeData.configs.break_condition = BranchUtils.branchConfigsMapper(
        this.conditionConf,
      );
    }
    this.appFlowServ.setNodeSaveMonitor({
      nodeData,
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

}
