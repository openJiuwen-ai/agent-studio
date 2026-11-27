import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, NgForm, Validators } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { MODULES } from '@shared/modules';
import { ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { debounceTime, Subject, Subscription } from 'rxjs';
import { InputTreeSelect } from '../input-tree-select/input-tree-select';
import { EditNameComponent } from '../edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AppFlowService } from '../../app-flow.service';
import { getInitInputParamRefConfig, NODE_SAVE_DEBOUNCE_TIME, WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IParamRef, ITemplateTransformNode, IWorkflowField } from '../../node.type';
import { ModalBaseComponent } from '../base/modal-base.component';
import { NodeUtils } from '../utils';
import { rewriteTemplateInputRefs } from './rewrite-template-input-refs';

@Component({
  selector: 'meta-template-transform-modal',
  templateUrl: './template-transform-modal.component.html',
  styleUrls: ['./template-transform-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    MonacoEditorModule,
    AccBlockComponent,
    ValueValidityValidatorDirective,
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
export class TemplateTransformModalComponent extends ModalBaseComponent implements OnInit {
  @Input('nodeInfo') nodeInfo: ITemplateTransformNode;

  @ViewChild('inputForm') inputForm: NgForm;

  protected override destroy$ = new Subject<void>();

  public icon = WORKFLOW_SVGS.TemplateTransform;

  public inputParams: IWorkflowField[] = [];

  public nameRefOptions: IParamRef[] = [];

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public editorOptions = {
    theme: 'vs',
    language: 'plaintext',
    minimap: { enabled: false },
  };

  public modelFormGroup = this.fb.group({
    template: ['', Validators.required],
  });

  private formSub: Subscription;

  private nameSnapshot: string[] = [];

  private skipFirstChange = true;

  constructor(
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
  ) {
    super(nodeServ, appFlowServ);
  }

  public override async ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode).subscribe(info => this.onRefUpdate(info));
    } else {
      this.getSelfRefs().subscribe(info => this.onRefUpdate(info));
    }
    this.modelFormGroup.controls.template.setValue(this.nodeInfo.configs?.template || '');
    this.formSub = this.modelFormGroup.valueChanges.pipe(debounceTime(NODE_SAVE_DEBOUNCE_TIME)).subscribe(() => {
      if (this.skipFirstChange) {
        this.skipFirstChange = false;
        return;
      }
      this.changeUpdateTime();
      this.handelSave();
    });
  }

  override ngOnDestroy(): void {
    this.modelCloseSave();
    this.destroy$.next();
    this.destroy$.complete();
    this.formSub?.unsubscribe();
  }

  public onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;
    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(this.nodeInfo.inputs, this.nameRefOptions);
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }
    this.isInit = false;
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamRefConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.changeUpdateTime();
    this.handelSave();
  }

  public deleteInputParam(index: number) {
    this.inputParams.splice(index, 1);
    this.changeUpdateTime();
    this.handelSave();
  }

  public rememberName(index: number) {
    this.nameSnapshot[index] = this.inputParams[index]?.name || '';
  }

  public onNameBlur(index: number) {
    const oldName = this.nameSnapshot[index];
    const newName = this.inputParams[index]?.name;
    if (oldName && newName && oldName !== newName) {
      const current = this.modelFormGroup.controls.template.value || '';
      const next = rewriteTemplateInputRefs(current, oldName, newName);
      if (next !== current) {
        this.modelFormGroup.controls.template.setValue(next);
      }
    }
    this.changeUpdateTime();
    this.handelSave();
  }

  public onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.changeUpdateTime();
    this.handelSave();
  }

  public treeSelect() {
    this.changeUpdateTime();
    this.handelSave();
  }

  public getInputNames(index: number) {
    const names = this.inputParams.map(item => item.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    if (this.inputForm?.invalid || this.modelFormGroup.invalid) {
      return;
    }
    const nodeData: ITemplateTransformNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: 'TemplateTransform',
      inputs: NodeUtils.getDtoInputs(this.inputParams),
      outputs: this.nodeInfo.outputs,
      configs: {
        ...this.nodeInfo.configs,
        template: this.modelFormGroup.controls.template.value || '',
      },
    };
    this.appFlowServ.setNodeSaveMonitor({ nodeData });
    setTimeout(() => this.updateChangeAndInitTime(), 200);
  }
}
