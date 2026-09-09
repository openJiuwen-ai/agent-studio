import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { cloneDeep } from 'lodash';
import { IParamRef, IWorkflowField, type IHttpRepo } from '../../../node.type';
import { getInitInputParamConfig } from '../../../flow.const';
import { AccBlockComponent } from '../../acc-block/acc-block.component';
import { ModalBaseComponent } from '../../base/modal-base.component';
import { ParamTreeComponent } from '../../param-tree/param-tree.component';
import { InputTreeSelect } from '../../input-tree-select/input-tree-select';
import { NodeUtils } from '../../utils';
import { takeUntil } from 'rxjs';

@Component({
  selector: 'meta-config-input-output',
  standalone: true,
  imports: [
    MODULES,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    AccBlockComponent,
    ParamTreeComponent,
    InputTreeSelect,
  ],
  templateUrl: './config-input-output.component.html',
  styleUrl: './config-input-output.component.less',
})
export class ConfigInputOutputComponent extends ModalBaseComponent {
  @ViewChild('inputForm') inputForm!: NgForm;

  @Input() sourceOptions: any[] = [];
  @Input() nodeInfo!: IHttpRepo;
  @Input() inputParams: IWorkflowField[] = [];

  @Output() inputChange = new EventEmitter<IWorkflowField[]>();

  nameRefOptions: IParamRef[] = [];

  override ngOnInit(): void {
    this.setNodeBase(this.nodeInfo);
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode)
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => { this.nameRefOptions = info; });
    } else {
      this.getSelfRefs()
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => { this.nameRefOptions = info; });
    }
  }

  onTypeChange(row: IWorkflowField): void {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.inputChange.emit(this.inputParams);
  }

  deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.inputChange.emit(this.inputParams);
  }

  addInputParam(): void {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.inputChange.emit(this.inputParams);
  }

  onParamChange(): void {
    this.inputChange.emit(this.inputParams);
  }

  getInputNames(index: number): { existingValues: string[]; forbiddenValues: string[] } {
    const names = this.inputParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names, forbiddenValues: ['query', 'headers'] };
  }
}
