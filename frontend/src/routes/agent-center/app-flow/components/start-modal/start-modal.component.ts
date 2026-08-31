import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
  ChangeDetectorRef,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import {
  getInitOutputParamConfig,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  getInputParamTypes,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import type {
  IEndNode,
  IParamRef,
  IStartNode,
  IWFView,
  IWFViewParentType,
  IWFViewWithMultiType,
  IWorkflowField,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { SetDefaultComponent } from '../set-default/set-default.component';
import { StartImportJsonModalComponent } from '../start-import-json-modal/start-import-json-modal.component';
import { ObjectTemplateComponent } from '@routes/object-manage/component/object-template/object-template.component';
import { NodeUtils } from '../utils';
import { FlowUtils } from '../../utils/flow-utils';
import { startSchemaStrField } from '../../../app-plugin/utils';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { HelpCenterService } from '@services/help-center.service';
import { CommonService } from '@services/common.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { mapTreeAddKeyIndex } from '@routes/agent-center/app-plugin/utils';
@Component({
  selector: 'meta-start-modal',
  templateUrl: './start-modal.component.html',
  styleUrls: ['./start-modal.component.less', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    ValueValidityValidatorDirective,
    AddPropsIconComponent,
    SetDefaultComponent,
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
export class StartModalComponent extends ModalBaseComponent implements OnInit {
  @Input('nodeInfo') nodeInfo: IStartNode | IEndNode;

  @Input() workflowType: string;

  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('outputForm') outputForm: NgForm;

  public changeUrl = cdnAssetUrl;

  public responseTemplate = '';

  public startNodeParams: IWFViewWithMultiType[] = [];

  public startTypeOptions = getInputParamTypes();

  public standTypeOps = getOutputParamTypes();

  public startTypeOp = getNoneObjOutputParamTypes();

  public isObjectLikeType = NodeUtils.isObjectLikeType;

  public isSimpleType = NodeUtils.isSimpleType;

  public disabledSwitch = true;

  public sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public nameRefOptions: IParamRef[] = [];
  updateTimeout: any = null;

  get removeSysFromNode() {
    return mapTreeAddKeyIndex(this.startNodeParams.filter(
      (param) => param.name !== 'sys' && param.name !== 'env',
    ),0);
  }

  @ViewChild('descriptionDom') descriptionDom: any;

  get getParamWidth() {
    const width = (this.descriptionDom?.nativeElement?.offsetWidth | 0) + 2;
    return `${width}px`;
  }

  constructor(
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private configServ: AgentConfigService,
    private helpCenterService: HelpCenterService,
    protected commonService: CommonService,
    private nzModal: NzModalService,
    private nzMessage: NzMessageService,
    private cdr: ChangeDetectorRef,
  ) {
    super(nodeServ, appFlowServ);
  }

  public override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.startNodeParams = FlowUtils.fields2Views(
      (this.nodeInfo as IStartNode).outputs,
    );
  }

  ngAfterViewInit() {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => {
        this.validateNode();
      });
    }
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.modelCloseSave();
    this.helpCenterService.hideHelpPanel();
  }

  chooseTemplate() {
    const modalRef = this.nzModal.create<ObjectTemplateComponent>({
      nzContent: ObjectTemplateComponent,
      nzWidth: 900,
      nzClosable: true,
      nzClassName: 'modal-custom900-class',
      nzFooter: null,
      nzTitle: this.i18n.transform('object_template'),
      nzData: {
        templatesSelected: (data) => {
          console.log(data)
          const objectTemplateData = FlowUtils.objectTempStartNodeFields2Views(data);
          this.startNodeParams = [
            ...this.startNodeParams,
            ...objectTemplateData,
          ];
          modalRef.close();
          this.changeUpdateTime();
          this.cdr.detectChanges();
          this.onStartNodeNameChange();
        },
      },
    });
  }

  importJson() {
    const modal = this.nzModal.create({
      nzTitle: this.i18n.transform('import_json'),
      nzContent: StartImportJsonModalComponent,
      nzWidth: 600,
      nzClosable: true,
      nzFooter: null,
      nzClassName: 'import-json-modal',
    });
    modal.componentInstance.confirm.subscribe((data) => {
      const req = startSchemaStrField(JSON.stringify(data));
      const item = this.startNodeParams.slice(0, 1);
      this.startNodeParams = [...item, ...FlowUtils.fields2Views(req)];
      modal.destroy();
      this.changeUpdateTime();
      this.cdr.detectChanges();
      this.handelSave();
    });
  }

  public addStartNodeParam(): void {
    this.startNodeParams = [
      ...this.startNodeParams,
      {
        ...getInitOutputParamConfig(),
        depth: 0,
        parentType: 'none' as IWFViewParentType,
        isLeaf: true,
        type: ['string'],
      },
    ];
    this.onSave();
  }

  public onTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }

  public getTypeString(type: string[]): string {
    return type.join('/');
  }

  public setTypeFromString(param: IWFViewWithMultiType, typeStr: string | string[]) {
    if (!typeStr) return;
    param.type =  Array.isArray(typeStr) ? typeStr : typeStr.split('/') as any;
    this.onStartOutputParamTypeChange(param);
  }

  public originalOrder(): number {
    return 0;
  }

  public trackByFn(index: number) {
    return index;
  }

  dismiss(): void { }

  close(): void { }

  public showDelete(param: IWFView) {
    return NodeUtils.showDelete(param, this.startNodeParams);
  }

  showSetDefault(param: IWFViewWithMultiType) {
    return (
      param.source !== 'system' &&
      param.source !== 'environment' &&
      param.depth === 0
    );
  }


  validateNode() {
    this.outputForm?.form?.markAllAsTouched();
  }

  getStartNodeInputNames(param: IWFView): {
    existingValues: string[];
  } {
    let names = [];
    if (param.depth === 0) {
      names = this.startNodeParams.map((arg) => arg.name);
    } else {
      const parentNode = this.getParentNodeFromTree(this.startNodeParams, param);
      names = parentNode?.children.map((arg) => arg.name);
    }

    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  getNameErrorTip(origin: any): string {
    const control = this.outputForm?.form?.get('outputFormName' + origin.keyindex);
    if (control?.errors?.serviceName?.tiErrorMessage && (control.dirty || control.touched)) {
      return control.errors.serviceName.tiErrorMessage;
    }
    return '';
  }

  hasNameError(origin: any): boolean {
    const control = this.outputForm?.form?.get('outputFormName' + origin.keyindex);
    return !!(control?.errors?.serviceName?.tiErrorMessage && (control.dirty || control.touched));
  }

  onStartNodeNameChange() {
    this.outputForm?.form?.markAsDirty();
  }

  onStartOutputParamTypeChange(param: IWFViewWithMultiType) {
    const type = param.type.join('/');
    if (this.isSimpleType(type) && param?.children) {
      delete param?.children;
      param.isLeaf = true;
      return;
    }

    if (
      type.startsWith('array') &&
      type !== 'array<object>' &&
      param?.children
    ) {
      delete param?.children;
      param.isLeaf = true;
    }

    if (this.isObjectLikeType(param.type)) {
      param.isLeaf = false;
      if (!param?.children) {
        this.addChild(param);
      }
    }

    if (param.value.default) {
      param.value.default = null;
    }
    this.onSave();
  }

  deleteStartNodeParam(param: IWFView) {
    this.removeNodeFromTree(this.startNodeParams, param);

    const parentNodeParam = this.getParentNodeFromTree(
      this.startNodeParams,
      param,
    ) as IWFView;
    if (
      this.isObjectLikeType(parentNodeParam?.type) &&
      parentNodeParam?.children?.length === 0
    ) {
      delete parentNodeParam.children;
      parentNodeParam.isLeaf = true;
    }
    this.onSave();
  }

  private removeNodeFromTree(nodes: any[], target: any): boolean {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) {
        nodes.splice(i, 1);
        return true;
      }
      if (nodes[i].children && this.removeNodeFromTree(nodes[i].children, target)) {
        return true;
      }
    }
    return false;
  }

  private getParentNodeFromTree(nodes: any[], target: any, parent: any = null): any {
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i] === target) {
        return parent;
      }
      if (nodes[i].children) {
        const result = this.getParentNodeFromTree(nodes[i].children, target, nodes[i]);
        if (result !== null) {
          return result;
        }
      }
    }
    return null;
  }

  addChild(param: IWFViewWithMultiType) {
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

  disableSysEdit(param: IWFViewWithMultiType) {
    return param.source === 'system';
  }

  get site() {
    return this.configServ.getConfigs().site;
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
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        outputs: NodeUtils.multiTypeViews2Fields(this.startNodeParams),
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
    // 只有当前有校验问题时，才失焦保存，其他时候要抽屉关闭保存
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  tipSave() {
    this.changeUpdateTime();
    this.handelSave();
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }
}
