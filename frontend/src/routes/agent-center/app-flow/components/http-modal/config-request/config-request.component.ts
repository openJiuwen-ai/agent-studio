import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { HttpHeadersOrQueryKeyDirective } from '@shared/directives/common-validator.directive';
import { MODULES } from '@shared/modules';
import { cloneDeep } from 'lodash';
import { IHttpConfig, IParamRef, IWorkflowField, type IHttpRepo } from '../../../node.type';
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
  }

  onRefUpdate(info: IParamRef[]): void {
    this.nameRefOptions = info;
    const inputs = this.nodeInfo.inputs;
    const querySchema = inputs.find((item) => item.name === 'query')?.schema as IWorkflowField[];
    this.queryParams = NodeUtils.initInputs(querySchema, this.nameRefOptions);
    const headerSchema = inputs.find((item) => item.name === 'headers')?.schema as IWorkflowField[];
    this.headerParams = NodeUtils.initInputs(headerSchema, this.nameRefOptions);
  }

  ngOnChanges(): void {
    this.tipVals = this.inputParams.map((param) => param.name);
  }

  onTypeChange(row: IWorkflowField): void {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSaveChange();
  }

  addQueryParam(): void {
    this.queryParams.push({
      ...getInitInputParamConfig('pre_defined'),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSaveChange();
  }

  deleteQueryParam(index: number): void {
    this.queryParams.splice(index, 1);
    this.onSaveChange();
  }

  addHeaderParam(): void {
    this.headerParams.push({
      ...getInitInputParamConfig('pre_defined'),
      refs: cloneDeep(this.nameRefOptions),
    });
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
}
