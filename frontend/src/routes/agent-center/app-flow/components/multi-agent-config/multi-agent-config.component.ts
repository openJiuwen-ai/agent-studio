/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { MemoryLibSelector } from '@routes/memory-lib/components/memory-lib-selector/memory-lib-selector';
import { MemoryLibSelectorTipType } from '@routes/memory-lib/memory-lib-enums';
import { IMemoryLibBaseInfo, IMemoryLibSelectData } from '@routes/memory-lib/memory-lib-interfaces';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
  LengthValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import { getInitInputParamConfig, getLLMLikeOutputParamTypes } from '../../flow.const';
import { NodeService } from '../../node.service';
import { IWFView, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { SetDefaultComponent } from '../set-default/set-default.component';
import { NodeUtils } from '../utils';

@Component({
  selector: 'multi-agent-config-modal',
  templateUrl: './multi-agent-config.component.html',
  styleUrls: ['./multi-agent-config.component.less'],
  standalone: true,
  imports: [
    MODULES,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    AccBlockComponent,
    SetDefaultComponent,
    MemoryLibSelector,
    LengthValidatorDirective,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.MEMORY_LIB],
    },
  ],
})
export class MultiAgentConfigComponent extends ModalBaseComponent implements OnInit {
  @Input() inputs: IWorkflowField[];

  @Input() globalVariables: IWorkflowField[];

  @Input() memoryConfig: any;

  @Input() flowId: string;

  @Output() configsChange = new EventEmitter<{
    inputs: IWorkflowField[];
    global_variables: IWorkflowField[];
    memory_config: IMemoryLibBaseInfo | null;
  }>();

  @ViewChild('inputsForm') inputsForm: NgForm;

  @ViewChild('globalValForm') globalValForm: NgForm;

  @Output() close = new EventEmitter<void>();

  public changeUrl = cdnAssetUrl;

  public paramTypes = getLLMLikeOutputParamTypes();

  public inputParams: IWorkflowField[] = [];

  public variables: IWorkflowField[] = [];

  public memoryLibData: {
    enable: boolean;
    data: IMemoryLibBaseInfo[] | null;
    isLoading: boolean;
  } = {
    enable: false,
    data: null,
    isLoading: false,
  };

  override getLayerIndexWidth(param: IWFView): string {
    return NodeUtils.getLayerIndexWidth(param, this.isNormalView, {
      widthArr: [165, 136],
    });
  }

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    public configServ: AgentConfigService,
  ) {
    super(nodeServ, appFlowServ);
  }

  override ngOnInit() {
    super.ngOnInit();

    this.inputParams = cloneDeep(this.inputs ?? []);
    this.variables = cloneDeep(this.globalVariables ?? []);
    this.memoryLibData.data = this.memoryConfig?.memory_repo_id ? [this.memoryConfig] : [];
  }

  get removeSysFromInputs() {
    return this.inputParams.filter(p => p.source !== 'system');
  }

  showValidity(ct: any) {
    Object.keys(ct).map(item => {
      ct[item].markAsDirty();
    });
  }

  onConfirm(): void {
    this.showValidity(this.inputsForm.controls);
    this.showValidity(this.globalValForm.controls);
    if ((this.inputsForm && this.inputsForm.invalid) || this.globalValForm.invalid) {
      return;
    }
    this.inputParams.forEach(item => {
      if (item.type === 'number' || item.type === 'integer') {
        item.value.default = item.value.default ? item.value.default : null;
      }
    });
    this.variables.forEach(item => {
      if (item.type === 'number' || item.type === 'integer') {
        item.value.default = item.value.default ? item.value.default : null;
      }
    });

    this.configsChange.emit({
      inputs: this.inputParams,
      global_variables: this.variables,
      memory_config: this.memoryLibData.data[0],
    });
  }

  dismiss(): void {
    this.close.emit();
  }

  trackByFn(index: number) {
    return index;
  }

  onNameChange() {
    window.setTimeout(() => {
      this.inputsForm && this.inputsForm.control.markAllAsTouched();
      this.globalValForm.control.markAllAsTouched();
    });
  }

  getInputNames(param: IWorkflowField): {
    existingValues: string[];
    forbiddenValues: string[];
  } {
    const names = this.inputParams.map(arg => arg.name);

    names.splice(names.indexOf(param.name), 1);
    return {
      existingValues: names,
      forbiddenValues: ['query'],
    };
  }

  getVarNames(param: IWorkflowField): {
    existingValues: string[];
  } {
    const names = this.variables.map(arg => arg.name);

    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  deleteInput(param: IWorkflowField) {
    this.inputParams = this.inputParams.filter(item => item.name !== param.name);
  }

  deleteVar(index: number) {
    this.variables.splice(index, 1);
  }

  addInput() {
    this.inputParams.push({ ...getInitInputParamConfig(), type: 'string' });
  }

  addVar() {
    this.variables.push({ ...getInitInputParamConfig(), type: 'string' });
  }
  onSelectParams(val, index_num: number) {
    this.inputParams.forEach((item: any, index: number) => {
      if (item.type === val && index === index_num) {
        item.value.default = '';
      }
    });
  }
  onSelectGlobal(val, index_num: number) {
    this.variables.forEach((item, index) => {
      if (item.type === val && index === index_num) {
        item.value.default = '';
      }
    });
  }

  public memoryLibSelectChange(changeData: IMemoryLibSelectData) {
    const { reason, halfModalRef, data } = changeData;

    const memoryLib = data[0];
    const updatedData: IMemoryLibBaseInfo = memoryLib
      ? {
          memory_repo_id: memoryLib?.memory_repo_id,
          name: memoryLib.name,
          description: memoryLib.description,
        }
      : { memory_repo_id: '' };

    if (reason) {
      this.memoryLibData.data = [updatedData];
    }
    halfModalRef?.destroy?.(reason);
  }

  protected readonly memoryLibSelectorTipType = MemoryLibSelectorTipType;
}
