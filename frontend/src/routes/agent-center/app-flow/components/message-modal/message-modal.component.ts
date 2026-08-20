import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { AppFlowService } from '../../app-flow.service';
import { getInitInputParamConfig, WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IMessageNode, IParamRef, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { NodeUtils } from '../utils';
import { CmdTextareaComponent } from '../cmd-textarea/cmd-textarea.component';
import { StructOutputComponent } from '@routes/agent-center/app-flow/components/struct-output/struct-output.component';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
@Component({
  selector: 'meta-message-modal',
  templateUrl: './message-modal.component.html',
  styleUrls: ['./message-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    RefSelectedRequireDirective,
    ParamTreeComponent,
    StructOutputComponent,
    CmdTextareaComponent,
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
export class MessageModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IMessageNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('structOutput') structOutput: StructOutputComponent;

  public icon = WORKFLOW_SVGS.Message;

  public responseTemplate = '';

  public inputParams: IWorkflowField[] = [];

  public disabledSwitch = true;

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public nameRefOptions: IParamRef[] = [];

  public validationRules = [];

  public validation = {
    type: 'change',
  };

  readonly showVarListSubject$ = new Subject<boolean>();

  onShowVarList(event: Event, subject: Subject<boolean>) {
    event.preventDefault();
    event.stopPropagation();
    subject.next(true);
  }

  needValid = false;

  public enableHistory = true;
  public writeTypes = [
    {
      text: this.i18n.transform('qamodalcomponent_559'),
      id: true,
    },
    {
      text: this.i18n.transform('qamodalcomponent_560'),
      id: false,
    },
  ];
  public writeTip = this.i18n.transform('qamodalcomponent_565');
  get tipVals() {
    return this.inputParams.map(param => param.name);
  }

  isFirstInit = 0;
  updateTimeout: any = null;
  constructor(
    protected override nodeServ: NodeService,
    private i18n: I18NextEagerPipe,
    protected override appFlowServ: AppFlowService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    protected agentDataServe: AgentDataService
  ) {
    super(nodeServ, appFlowServ);
  }

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode).subscribe(info => {
        this.onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe(info => {
        this.onRefUpdate(info);
      });
    }
    this.enableHistory = this.nodeInfo.configs.enable_history;
    this.responseTemplate = this.nodeInfo.configs.template;
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(this.nodeInfo?.inputs, this.nameRefOptions);
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.isInit = false;
  }

  public addInputParam(): void {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSave();
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  public onTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  public trackByFn(index: number) {
    return index;
  }
  close(): void {}
  dismiss(): void {}

  validateNode() {
    if (this.inputForm?.form.invalid) {
      Object.keys(this.inputForm.form.controls).forEach(key => {
        this.inputForm.form.get(key)?.markAsDirty();
      });
    }
    this.needValid = true;
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.inputParams.map(p => p.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  onNameChange() {
    window.setTimeout(() => {
      if (this.inputForm?.form.invalid) {
        Object.keys(this.inputForm.form.controls).forEach(key => {
          this.inputForm.form.get(key)?.markAsDirty();
        });
      }
    });
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

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const struct_output_template = this.structOutput.struct_output_template;
    const isStructMessage = this.structOutput.structEnable;
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs: NodeUtils.getDtoInputs(this.inputParams),
        configs: {
          ...(this.nodeInfo as IMessageNode).configs,
          template: this.responseTemplate,
          struct_output_template,
          enable_history: this.enableHistory,
          isStructMessage,
        },
      },
    });
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    this.updateTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  structOnSave() {
    if (this.isFirstInit <= 0) {
      this.isFirstInit += 1;
      return;
    }
    this.onSave();
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }
}
