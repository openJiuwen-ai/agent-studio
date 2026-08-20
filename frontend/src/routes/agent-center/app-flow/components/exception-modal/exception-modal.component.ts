import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import { NODE_SAVE_DEBOUNCE_TIME, WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IMessageNode, IParamRef } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { MonacoEditorModule, MonacoEditorComponent } from '@materia-ui/ngx-monaco-editor';
import { ExTempComponent } from '@routes/agent-center/app-flow/components/exception-modal/ex-temp.component';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { CodeFullScreenEditorComponent } from '@routes/agent-center/app-flow/components/code-full-screen-editor/code-full-screen-editor.component';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { NodeTypeTopic } from '@routes/agent-center/types/common.types';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-exception-modal',
  templateUrl: './exception-modal.component.html',
  styleUrls: ['./exception-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    MonacoEditorModule,
    ObjTypeValidatorDirective,
    CodeFullScreenEditorComponent,
    EditNameComponent,
    NodeDescriptionComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzModalService,
    NzMessageService,
  ],
})
export class ExceptionModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IMessageNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('tempForm') tempForm: NgForm;

  @ViewChild(MonacoEditorComponent) monacoEditor: MonacoEditorComponent;

  public icon = WORKFLOW_SVGS.StructuredMessagesException;

  public responseTemplate = '';

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public nameRefOptions: IParamRef[] = [];

  public validationRules: any[] = [];

  public validation: any = {
    type: 'change',
  };

  editorOptions = {
    theme: 'vs',
    language: 'json',
    minimap: {
      enabled: false,
    },
  };

  isFullScreen = false;
  validError = false;

  codeTimeout: any = null;
  isWrite = 0;
  updateTimeout: any = null;

  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private nzModal: NzModalService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService
  ) {
    super(nodeServ, appFlowServ);
  }

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.isWrite = 0;

    this.responseTemplate = this.nodeInfo.configs.template ?? '';
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  public trackByFn(index: number) {
    return index;
  }

  dismiss(): void {}

  close(): void {}

  validateNode() {
    const value = this.responseTemplate;
    if (!value || value.trim() === '') {
      this.validError = false;
      return;
    }
    try {
      const obj = JSON.parse(value);
      this.validError = typeof obj !== 'object' || obj === null || Array.isArray(obj);
    } catch {
      this.validError = true;
    }
  }

  handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs: [],
        configs: {
          template: this.responseTemplate,
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

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  editorOnSave() {
    if (this.isWrite <= 0) {
      this.isWrite += 1;
      return;
    }
    this.validateNode();
    if (this.codeTimeout) {
      clearTimeout(this.codeTimeout);
      this.codeTimeout = null;
    }
    this.codeTimeout = setTimeout(() => {
      this.onSave();
    }, NODE_SAVE_DEBOUNCE_TIME);
  }

  onSave() {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  public openRefModal() {
    const modal = this.nzModal.create({
      nzTitle: this.i18n.transform('extempcomponent_331'),
      nzContent: ExTempComponent,
      nzWidth: 900,
      nzClosable: true,
      nzFooter: null,
      nzClassName: 'ref-prompt-modal',
    });
    modal.componentInstance.select.subscribe((tmpl: any) => {
      this.responseTemplate = tmpl.content;
      this.changeUpdateTime();
      this.handelSave();
      setTimeout(() => {
        this.monacoEditor?.editor?.setValue(this.responseTemplate);
        modal.destroy();
      });
    });
  }

  openFullScreen() {
    this.isFullScreen = true;
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }
}
