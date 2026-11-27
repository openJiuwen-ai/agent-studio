import { Component, EventEmitter, inject, OnInit, Output, SimpleChanges, ViewChild, } from '@angular/core';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { filter, takeUntil } from 'rxjs';
import { type IParamRef, type IWFView, IWorkflowField, } from '../../../node.type';
import { AccBlockComponent } from '@routes/agent-center/app-flow/components/acc-block/acc-block.component';
import { RefSelectedRequireDirective, } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { ParamTreeComponent } from '@routes/agent-center/app-flow/components/param-tree/param-tree.component';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import { ReadonlyParamsTreeComponent } from '@routes/agent-center/app-flow/components/readonly-params/readonly-params-tree.component';
import { NgForm } from '@angular/forms';
import * as nodeType from '@routes/agent-center/app-flow/node.type';
import { NODE_ACTIONS } from '@routes/agent-center/constants/workflow-common.const';
import { NodeService } from '@routes/agent-center/app-flow/node.service';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { NodeUtils } from '@routes/agent-center/app-flow/components/utils';
import { cloneDeep } from 'lodash';
import { ModalBaseComponent } from '@routes/agent-center/app-flow/components/base/modal-base.component';
import { ConditionModalComponent } from '@routes/agent-center/app-flow/components/param-extraction-modal/condition-modal/condition-modal.component';
import { BranchUtils } from '@routes/agent-center/app-flow/components/branch.utils';
import { MessageComponent } from "@shared/services/cfdata.service";
import { InputTreeSelect } from '@routes/agent-center/app-flow/components/input-tree-select/input-tree-select';

@Component({
  selector: 'configure-workflow-modal',
  templateUrl: 'configure-workflow-modal.component.html',
  styleUrls: [
    'configure-workflow-modal.component.less',
    '../../common-styles.less',
  ],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    ReadonlyParamsTreeComponent,
    ParamTreeComponent,
    TypedJsonInputComponent,
    ConditionModalComponent,
    InputTreeSelect,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.COMMON,
      ],
    },
  ],
})
export class ConfigureWorkflowModalComponent
  extends ModalBaseComponent
  implements OnInit
{
  readonly nzModalData = inject<any>(NZ_MODAL_DATA);
  private readonly modalRef = inject(NzModalRef);

  nodeInfo: nodeType.IFlowNode = this.nzModalData.nodeInfo;

  flow: nodeType.IProcessingWorkflow = this.nzModalData.flow;

  domainObjectName: string = this.nzModalData.domainObjectName;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('contextForm') contextForm: NgForm;

  conditionRefOptions: nodeType.IParamRef[] = this.nzModalData.conditionRefOptions || [];

  @ViewChild('conditionModal') conditionModal: ConditionModalComponent;

  public inputParams: nodeType.IWorkflowField[] = [];

  public nameRefOptions: nodeType.IParamRef[] = [];

  contextParams: nodeType.IWorkflowField[] = [];

  public validationRules: any[] = [];

  public validation: any = {
    type: 'change',
  };

  options = [{ label: this.i18n.transform('ref'), value: 'ref' }];

  override actions = [
    {
      id: 'detail',
      label: this.i18n.transform('sub_workflow_details'),
    },
    ...NODE_ACTIONS,
  ];

  public isValidated = false;

  entry_condition: nodeType.IBranchConfigs =
    BranchUtils.getNewBranchBlankConfigs();

  typeList = [
    'string',
    'integer',
    'number',
    'boolean',
    'object',
    'array<string>',
    'array<number>',
    'array<integer>',
    'array<boolean>',
    'array<object>',
  ];

  fillCount  = 0 //自动填入参数数量

  placeholder_1: string = this.i18n.transform('param_ex_fill_tip');


  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    private appFlowServe: AppFlowService,
  ) {
    super(nodeServ, appFlowServe);
  }

  getType = NodeUtils.getFieldTypeView;

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    this.subNodeActions();

    this.onRefUpdate();

    if (this.flow?.entry_condition) {
      this.entry_condition = this.flow.entry_condition;
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (
      changes.conditionRefOptions &&
      changes.conditionRefOptions.currentValue
    ) {
      this.onRefUpdate();
    }
  }

  public onInputTypeChange(row: nodeType.IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }

  public onRefUpdate() {
    if (this.isInit) {
      this.inputParams = this.getInputParams();
      this.inputParams.forEach((v) => {
        v.options = [
          { label: this.i18n.transform('ref'), value: 'ref' },
          { label: this.getType(v), value: 'literal' },
        ];
      });
      this.contextParams = this.getContextParams();
    } else {
      NodeUtils.reSelectRefsWithNewOps(
        this.inputParams,
        this.filterRefOptions(this.conditionRefOptions, 'input'),
      );
      NodeUtils.reSelectRefsWithNewOps(
        this.contextParams,
        this.filterRefOptions(this.conditionRefOptions, 'context'),
      );
    }

    this.inputParams.forEach((v) => {
      v.options = [
        { label: this.i18n.transform('ref'), value: 'ref' },
        { label: this.getType(v), value: 'literal' },
      ];
    });

    this.isInit = false;
  }

  onConfirm(): void {
    this.isValidated = true;
    this.inputForm?.form?.markAllAsTouched();
    this.contextForm?.form?.markAllAsTouched();
    const isJsonTypeInvalid = this.inputParams.some(
      (obj) =>
        this.isArrOrObj(obj.type) && obj.value?.content === '' && obj.required,
    );
    const isContextInvalid = this.contextParams.some(
      (obj) => obj.required && !obj.value?.content,
    );
    if (this.inputForm?.form?.invalid || isJsonTypeInvalid || this.contextForm?.form?.invalid || isContextInvalid) {
      return;
    }

    const memoryParam = this.getMemoryParam();
    const inputs = cloneDeep(this.inputParams);
    inputs.forEach((param) => {
      if (param.value.type === 'ref') {
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
      delete param?.options;
    });
    this.flow.inputs = [...inputs, memoryParam];
    if (this.conditionModal?.entryCondition) {
      this.flow.entry_condition = BranchUtils.branchConfigsMapper(
        this.conditionModal?.entryCondition,
      );
    }
    this.confirm.emit();
    this.modalRef.close();
  }

  cancel() {
    if (this.conditionModal?.entryCondition) {
      this.flow.entry_condition = BranchUtils.branchConfigsMapper(
        this.conditionModal?.entryCondition,
      );
    }
    this.modalRef.destroy();
  }

  override ngOnDestroy() {
    if (this.conditionModal?.entryCondition) {
      this.flow.entry_condition = BranchUtils.branchConfigsMapper(
        this.conditionModal?.entryCondition,
      );
    }
    super.ngOnDestroy();
  }

  public getContextParams(): IWFView[] {
    const currentParams = this.flow.inputs.find(
      (input) => input.name === 'memory',
    );
    const inputs = [];
    const memory = this.flow?.memory ?? [];
    memory.forEach((m) => {
      let input = m;
      if (currentParams?.schema) {
        (currentParams.schema as IWorkflowField[]).some((s) => {
          if (m.name === s.name) {
            input = s;
            return true;
          }
          return false;
        });
      }
      input.value.type = 'ref';
      inputs.push(input);
    });
    return NodeUtils.initInputs(
      inputs as IWorkflowField[],
      this.filterRefOptions(this.conditionRefOptions, 'context'),
    );
  }

  public getInputParams(): IWorkflowField[] {
    const inputs = this.flow.inputs.filter((input) => input.name !== 'memory');

    if (inputs) {
      return NodeUtils.initInputs(
        inputs,
        this.filterRefOptions(this.conditionRefOptions, 'input'),
      );
    }

    return [];
  }

  /**
   * 过滤ref
   *  a.领域对象内子工作流：
   *    子工作流上下文变量可引用：节点输入、模型输入、节点上下文、节点当前领域对象
   *    子工作流输入可引用：节点输入、模型输入、节点上下文、节点当前领域对象
   *  b.领域对象外子工作流（拓展工作流）：
   *    子工作流上下文变量可引用：节点输入、模型输入、节点上下文
   *    子工作流输入可引用：节点输入、模型输入、节点上下文
   * @param refOptions
   * @param type
   */
  filterRefOptions(
    refOptions: nodeType.IParamRef[],
    type: 'input' | 'context',
  ) {
    return cloneDeep(refOptions);
  }

  getMemoryParam() {
    let inputs = cloneDeep(this.contextParams);
    inputs.forEach((param) => {
      if (param.value.type === 'ref') {
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
      delete param?.options;
    });
    inputs = inputs.filter((i) => {
      return i.value.content;
    });
    return {
      name: 'memory',
      type: 'object',
      description: this.i18n.transform('configureworkflowmodalcomponent_455'),
      required: true,
      source: 'pre_defined',
      reflection: false,
      schema: inputs,
      value: {
        type: 'nested',
        content: null,
        hint: '',
        default: '',
      },
    };
  }

  public subNodeActions() {
    this.appFlowServe.nodeActionUpdate$().pipe(
      filter((action) => action && action.id === this.nodeInfo.id),
      takeUntil(this.destroy$),
    );
  }

  fillInputParam() {
    this.fillCount = 0
    this.inputParams.forEach((input) => {
      this.fillParamRecursion(input, input.refs);
    });
    MessageComponent.showSuccess(this.i18n.transform('param_ex_fill_success', { count:this.fillCount }))
  }

  fillContextParam() {
    this.fillCount = 0
    this.contextParams.forEach((input) => {
      this.fillParamRecursion(input, input.refs);
    });
    MessageComponent.showSuccess(this.i18n.transform('param_ex_fill_success',{ count:this.fillCount }))
  }

  fillParamRecursion(input: IWorkflowField, refs: IParamRef[]) {
    refs.forEach((ref) => {
      if (this.typeList.includes(ref.type)) {
        if (
          !input.value.content &&
          ref.type === input.type &&
          ref.name === input.name
        ) {
          const { ref_node_id, ref_var_name, source, name, type } = ref;
          input.value.content = [
            {
              ref_node_id,
              ref_var_name,
              source,
              type,
              name,
            },
          ] as any;
          input.value.type = 'ref';
          this.fillCount ++
        }
      }
      if (ref.children && ref.children.length) {
        this.fillParamRecursion(input, ref.children);
      }
    });
  }

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }

  dismiss(): void {
    this.modalRef.destroy();
  }

  close(): void {
    this.modalRef.close();
  }
}
