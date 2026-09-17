import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { HttpHeadersOrQueryKeyDirective } from '@shared/directives/common-validator.directive';
import { MODULES } from '@shared/modules';
import { cloneDeep } from 'lodash';
import { type IHttpConfig, IParamRef, IWorkflowField, type IHttpRepo } from '../../../node.type';
import { getInitInputParamConfig } from '../../../flow.const';
import { AccBlockComponent } from '../../acc-block/acc-block.component';
import { ModalBaseComponent } from '../../base/modal-base.component';
import { ParamTreeComponent } from '../../param-tree/param-tree.component';
import { InputTreeSelect } from '../../input-tree-select/input-tree-select';
import { CmdTextareaComponent } from '../../cmd-textarea/cmd-textarea.component';
import { NodeUtils } from '../../utils';
import { takeUntil } from 'rxjs';

@Component({
  selector: 'meta-config-request',
  standalone: true,
  imports: [
    MODULES,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    HttpHeadersOrQueryKeyDirective,
    AccBlockComponent,
    ParamTreeComponent,
    InputTreeSelect,
    CmdTextareaComponent,
  ],
  templateUrl: './config-request.component.html',
  styleUrl: './config-request.component.less',
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: I18nNamespace.AGENT_CENTER,
    },
  ],
})
export class ConfigRequestComponent extends ModalBaseComponent {
  @Input() nodeInfo!: IHttpRepo;
  @Input() configs!: IHttpConfig;
  @Input() inputParams: IWorkflowField[] = [];
  @Input() sourceOptions: any[] = [];

  @ViewChild('requestForm') requestForm!: NgForm;

  @Output() valueChange = new EventEmitter<void>();
  @Output() inputChange = new EventEmitter<void>();
  @Output() timeChange = new EventEmitter<void>();

  queryParams: IWorkflowField[] = [];
  headerParams: IWorkflowField[] = [];
  nameRefOptions: IParamRef[] = [];

  bodyOptions = [
    { label: 'none', value: 'NONE' },
    { label: 'json', value: 'JSON' },
  ];

  tipVals: string[] = [];

  /** FB-4 ②：JSON 类型 body 模板合法性标志（仅显示层，非阻断）。 */
  bodyJsonInvalid = false;

  override ngOnInit(): void {
    this.setNodeBase(this.nodeInfo);
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { disableObj: true, disableArr: true })
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => this.onRefUpdate(info));
    } else {
      this.getSelfRefs({ disableObj: true, disableArr: true })
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => this.onRefUpdate(info));
    }
    this.validateBody();
  }

  onRefUpdate(info: IParamRef[]): void {
    this.nameRefOptions = info;
    if (this.isInit) {
      const inputs = this.nodeInfo.inputs ?? [];
      const querySchema = inputs.find((item) => item.name === 'query')?.schema as IWorkflowField[];
      this.queryParams = NodeUtils.initInputs(querySchema, this.nameRefOptions);
      const headerSchema = inputs.find((item) => item.name === 'headers')?.schema as IWorkflowField[];
      this.headerParams = NodeUtils.initInputs(headerSchema, this.nameRefOptions);
      this.isInit = false;
    } else {
      // MR 检视意见 #3：对齐父组件 http-modal.onRefUpdate 的 isInit 守卫——
      // 后续 ref 事件只刷新既有行（含用户新增行）的引用选项，不从
      // nodeInfo.inputs 重建行，避免覆盖用户在面板中未保存的修改
      NodeUtils.reSelectRefsWithNewOps(this.queryParams, this.nameRefOptions);
      NodeUtils.reSelectRefsWithNewOps(this.headerParams, this.nameRefOptions);
    }
  }

  private createBlankRow(): IWorkflowField {
    return {
      ...getInitInputParamConfig('pre_defined'),
      refs: cloneDeep(this.nameRefOptions),
    };
  }

  ngOnChanges(): void {
    this.tipVals = this.inputParams.map((param) => param.name);
  }

  onTypeChange(row: IWorkflowField): void {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSaveChange();
  }

  addQueryParam(): void {
    this.queryParams.push(this.createBlankRow());
    this.onSaveChange();
  }

  deleteQueryParam(index: number): void {
    this.queryParams.splice(index, 1);
    this.onSaveChange();
  }

  addHeaderParam(): void {
    this.headerParams.push(this.createBlankRow());
    this.onSaveChange();
  }

  deleteHeaderParam(index: number): void {
    this.headerParams.splice(index, 1);
    this.onSaveChange();
  }

  getQueryNames(index: number): { existingValues: string[]; isHttp: boolean } {
    const names = this.queryParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names, isHttp: true };
  }

  getQueryExistingNames(index: number): string[] {
    const names = this.queryParams.map((p) => p.name);
    names.splice(index, 1);
    return names;
  }

  getHeaderNames(index: number): { existingValues: string[]; isHttp: boolean } {
    const names = this.headerParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names, isHttp: true };
  }

  getHeaderExistingNames(index: number): string[] {
    const names = this.headerParams.map((p) => p.name);
    names.splice(index, 1);
    return names;
  }

  onSaveChange(): void {
    this.valueChange.emit();
  }

  onInputSave(): void {
    this.inputChange.emit();
  }

  treeSelect(): void {
    setTimeout(() => this.onSaveChange());
  }

  changeUpdate(): void {
    this.timeChange.emit();
  }

  /** FB-4 ②：body 内容变化时先校验 JSON 合法性，再触发原 changeUpdate。 */
  onBodyChange(): void {
    this.validateBody();
    this.changeUpdate();
  }

  /** FB-4 ②：body 类型切换时先校验，再触发原 onSaveChange。 */
  onBodyTypeChange(): void {
    this.validateBody();
    this.onSaveChange();
  }

  /**
   * FB-4 ②：JSON 类型 body 模板合法性校验（仅显示层，非阻断；与 FB-2 预期提示理念一致）。
   * body 含 {{var}} 占位符，本身不是合法 JSON，先替换成合法占位再 JSON.parse：
   *   - "{{var}}"（整段被引号包裹）→ "__ph__"（保持字符串，覆盖占位符即整个串值的场景）
   *   - 裸 {{var}}（可能是数组/对象/数字/布尔值）→ null（合法 JSON 字面量）
   * 这样 "{{x}}" / {"a": {{x}}} / "pre{{x}}post" 均能通过，而坏模板（占位符落到引号外、
   * 逗号重复等）会 JSON.parse 失败 → 显示提示。刻意不阻断：试运行门在后端 validateFlow，
   * 前端硬阻断会因启发式局限误伤合法占位符形态。
   */
  validateBody(): void {
    this.bodyJsonInvalid = false;
    if (this.configs?.request_type !== 'JSON') {
      return;
    }
    const raw = (this.configs.request_body ?? '').trim();
    if (!raw) {
      return;
    }
    const probe = raw
      .replace(/"\{\{[^{}\n\r]+?\}\}"/g, '"__ph__"')
      .replace(/\{\{[^{}\n\r]+?\}\}/g, 'null');
    try {
      JSON.parse(probe);
    } catch {
      this.bodyJsonInvalid = true;
    }
  }
}
