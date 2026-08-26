import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { NonEmptyValidatorDirective, ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import { getInitOutputParamConfig, getNoneObjOutputParamTypes, getOutputParamTypes, getInputParamTypes } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IInputNode, IParamRef, IWFView, IWFViewParentType, IWFViewWithMultiType, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { NodeUtils } from '../utils';
import { EditNameComponent } from '@routes/agent-center/app-flow/components/edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { mapTreeAddKeyIndex } from "@routes/agent-center/app-plugin/utils";
import { FlowUtils } from "@routes/agent-center/app-flow/utils/flow-utils";

function removeNodeFromTree(nodes: any[], target: any): boolean {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i] === target) {
      nodes.splice(i, 1);
      return true;
    }
    if (nodes[i].children && removeNodeFromTree(nodes[i].children, target)) {
      return true;
    }
  }
  return false;
}

function getParentNodeFromTree(nodes: any[], target: any, parent: any = null): any {
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i] === target) {
      return parent;
    }
    if (nodes[i].children) {
      const result = getParentNodeFromTree(nodes[i].children, target, nodes[i]);
      if (result !== null) {
        return result;
      }
    }
  }
  return null;
}

@Component({
  selector: 'meta-input-modal',
  templateUrl: './input-modal.component.html',
  styleUrls: ['./input-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    AddPropsIconComponent,
    EditNameComponent,
    NodeDescriptionComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class InputModalComponent extends ModalBaseComponent implements OnInit {
  @Input('nodeInfo') nodeInfo: IInputNode;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('outputForm') outputForm: NgForm;

  public inputNodeParams: any[] = [];

  public inputTypeOptions = getInputParamTypes();

  public standTypeOps = getOutputParamTypes();

  public inputTypeOp = getNoneObjOutputParamTypes();

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public isSimpleType = NodeUtils.isSimpleType;

  @ViewChild('descriptionDom') descriptionDom: any;

  @ViewChild('nameForm') nameForm: NgForm;

  public validation: any = {
    type: 'change',
  };

  get getParamWidth() {
    const width = (this.descriptionDom?.nativeElement?.offsetWidth | 0) + 2;
    return `${width}px`;
  }

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public nameRefOptions: IParamRef[] = [];
  updateTimeout: any = null;

  constructor(
    private i18n: I18NextEagerPipe,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService
  ) {
    super(nodeServ, appFlowServ);
  }

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    this.inputNodeParams = FlowUtils.fields2Views(this.nodeInfo.outputs);
  }

  get resetIndexParams() {
    return mapTreeAddKeyIndex(this.inputNodeParams,0);
  }

  public addNodeParam(): void {
    this.inputNodeParams = [
      ...this.inputNodeParams,
      {
        ...getInitOutputParamConfig(),
        depth: 0,
        parentType: 'none' as IWFViewParentType,
        type: ['string'],
      },
    ];
    this.onSave();
  }

  public onTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }

  dismiss(): void {}

  close(): void {}

  public showDelete(param: IWFView) {
    return NodeUtils.showDelete(param, this.inputNodeParams);
  }

  validateNode() {
    return;
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  getNodeInputNames(param: IWFView): {
    existingValues: string[];
  } {
    let names = [];
    if (param.depth === 0) {
      names = this.inputNodeParams.map(arg => arg.name);
    } else {
      const parentNode = getParentNodeFromTree(this.inputNodeParams, param);
      names = parentNode?.children.map(arg => arg.name);
    }

    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  hasNameError(origin: any): boolean {
    const control = this.outputForm?.form?.get('outputFormName' + origin.keyindex);
    return !!(control?.errors?.serviceName?.tiErrorMessage && (control.dirty || control.touched));
  }

  getNameErrorTip(origin: any): string {
    const control = this.outputForm?.form?.get('outputFormName' + origin.keyindex);
    if (control?.errors?.serviceName?.tiErrorMessage && (control.dirty || control.touched)) {
      return control.errors.serviceName.tiErrorMessage;
    }
    return '';
  }

  onNodeNameChange() {
    window.setTimeout(() => {
      this.outputForm?.form?.markAsDirty();
    });
  }

  public setTypeFromString(param: IWFViewWithMultiType, typeStr: string | string[]) {
    if (!typeStr) return;
    param.type =  Array.isArray(typeStr) ? typeStr : typeStr.split('/') as any;
    this.onOutputParamTypeChange(param);
  }

  onOutputParamTypeChange(param: any) {
    const type = param?.type;
    const typeStr = Array.isArray(type) ? type.join('/') : type;
    if (this.isSimpleType(typeStr) && param?.children) {
      delete param?.children;
      param.isLeaf = true;
      return;
    }

    if (typeStr.startsWith('array') && typeStr !== 'array<object>' && param?.children) {
      delete param?.children;
      param.isLeaf = true;
    }

    if (this.isObjectLikeType(typeStr)) {
      param.isLeaf = false;
      if (!param?.children) {
        this.addChild(param);
      }
    }
    this.onSave();
  }

  deleteNodeParam(param: IWFView) {
    removeNodeFromTree(this.inputNodeParams, param);

    const parentNodeParam = getParentNodeFromTree(this.inputNodeParams, param) as IWFView;
    if (this.isObjectLikeType(parentNodeParam?.type) && parentNodeParam?.children?.length === 0) {
      delete parentNodeParam.children;
      parentNodeParam.isLeaf = true;
    }
    this.inputNodeParams = [...this.inputNodeParams];
    this.onSave();
  }

  addChild(param: any) {
    const child = {
      ...getInitOutputParamConfig(),
      depth: param.depth + 1,
      parentType: param.type[0] as IWFViewParentType,
      isLeaf: true,
      type: ['string'],
    };

    if (param?.children) {
      param.children.push(child);
    } else {
      param.children = [child];
    }

    param.isLeaf = false;
    param.expanded = true;
    this.onSave();
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
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs: NodeUtils.multiTypeViews2Fields(this.inputNodeParams),
        outputs: NodeUtils.multiTypeViews2Fields(this.inputNodeParams),
        configs: {},
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

  onSave() {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }
}
