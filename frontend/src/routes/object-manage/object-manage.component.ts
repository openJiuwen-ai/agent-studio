import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { NgForm, UntypedFormControl, UntypedFormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MonacoEditorComponent, MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { CommonValidation } from '@shared/validation/commonValidation';
import { AddPropsIconComponent } from '@routes/agent-center/app-flow/components/add-props-icon/add-props-icon.component';
import { NodeUtils } from '@routes/agent-center/app-flow/components/utils';
import * as nodeType from '@routes/agent-center/app-flow/node.type';
import { ModalBaseComponent } from '@routes/agent-center/app-flow/components/base/modal-base.component';
import { NodeService } from '@routes/agent-center/app-flow/node.service';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { getInputParamTypes, getNoneObjOutputParamTypes, getOutputParamTypes } from '@routes/agent-center/app-flow/flow.const';
import { ObjectManageService } from '@routes/object-manage/object-manage.service';
import { SetDefaultComponent } from '@routes/agent-center/app-flow/components/set-default/set-default.component';
import { ObjectField, ObjectFieldType, ObjectParentType, ObjectType } from '@routes/object-manage/object.type';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { PipesModule } from '../../pipes/pipes.module';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzCascaderModule } from 'ng-zorro-antd/cascader';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'object-manage',
  templateUrl: './object-manage.component.html',
  styleUrls: ['./object-manage.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    FormsModule,
    ReactiveFormsModule,
    MonacoEditorModule,
    AddPropsIconComponent,
    SetDefaultComponent,
    ValueValidityValidatorDirective,
    NewCommonNoDataWithBtnComponent,
    PipesModule,
    NoDataGuideComponentComponent,
    NzButtonModule,
    NzIconModule,
    NzInputModule,
    NzTableModule,
    NzPaginationModule,
    NzDrawerModule,
    NzModalModule,
    NzFormModule,
    NzCascaderModule,
    NzToolTipModule,
    NzSpinModule,
    NzDividerModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.KNOWLEDGE, I18nNamespace.COMMON, I18nNamespace.AGENT, I18nNamespace.GUIDE],
    },
    NzModalService,
  ],
})
export class ObjectManageComponent extends ModalBaseComponent implements OnInit {
  @ViewChild('editorCmp') editorCmp: MonacoEditorComponent;
  @ViewChild('jsonEditor') jsonEditor: MonacoEditorComponent;
  showEdit = false;
  @ViewChild('objectForm') objectForm: NgForm;
  @Input('nodeInfo') nodeInfo: nodeType.IParamExtractionNode;

  searchValue = '';
  loading = false;

  srcData = {
    data: [],
    state: undefined,
  };

  listColumns = [
    { title: this.i18n.transform('object_name') },
    { title: this.i18n.transform('object_variable') },
    { title: this.i18n.transform('operator1') },
    { title: this.i18n.transform('operation_time') },
    { title: this.i18n.transform('operation'), fixed: 'right', width: '120px' },
  ];

  currentPage: number = 1;
  totalNumber: number = 0;
  pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  modalTypeName = '';

  formGroup = new UntypedFormGroup({
    name: new UntypedFormControl({ value: '', disabled: false }, [
      Validators.required,
      CommonValidation.customVerify(/^[A-Za-z0-9\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_-]{0,49}$/, this.i18n.transform('validation_name_tip')),
      Validators.minLength(2),
      Validators.maxLength(64),
    ]),
  });

  structuredObjectId = '';
  isFullScreen = false;

  public changeUrl = cdnAssetUrl;
  public objectsParams: ObjectType[] = [];
  public startTypeOptions = getInputParamTypes();
  public standTypeOps = getOutputParamTypes();
  public startTypeOp = getNoneObjOutputParamTypes();

  public isSimpleType = NodeUtils.isSimpleType;
  public isObjectLikeType = NodeUtils.isObjectLikeType;

  get searchNameIsEmpty() {
    return this.searchValue.length === 0;
  }
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  public isShowGuide = true;
  public isShowNoDataGuide = false;
  public isFirstLoading = true;

  constructor(
    private objectManageService: ObjectManageService,
    public router: Router,
    private nzModal: NzModalService,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private commonService: CommonService,
    private readonly http: HttpService,
    private message: NzMessageService
  ) {
    super(nodeServ, appFlowServ);
    this.http.getCurrentUserResourceStatus().subscribe(res => {});
  }

  override ngOnInit(): void {
    this.getObjectsListData();
  }

  trackByFn(index: number, item: any): number {
    return item.id;
  }

  handleClickClearSearch() {
    this.searchValue = '';
    this.searchList();
  }

  pageUpdate(event) {
    this.currentPage = event.currentPage;
    this.pageSize.size = event.size;
    this.getObjectsListData();
  }

  searchList() {
    this.currentPage = 1;
    this.pageSize.size = 10;
    this.getObjectsListData();
  }

  listAction($event: any, row: any) {
    if ($event.key === 'delete') {
      this.deleteObjectsData(row);
    } else if ($event.key === 'edit') {
      this.showModal('edit', row);
    }
  }

  deleteObjectsData(data: any): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('delete_object_prompt'),
      nzContent: this.i18n.transform('delete_object_content'),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        return this.objectManageService.deleteObjects(data.id).then(() => {
          this.message.success(this.i18n.transform('delete_success'));
          this.searchList();
        });
      },
    });
  }

  getParentNode(nodes: ObjectType[], target: ObjectType, parent: ObjectType | null = null): ObjectType | null {
    for (const node of nodes) {
      if (node === target) return parent;
      if (node.children) {
        const found = this.getParentNode(node.children, target, node);
        if (found) return found;
      }
    }
    return null;
  }

  removeNode(nodes: ObjectType[], target: ObjectType): boolean {
    const index = nodes.indexOf(target);
    if (index !== -1) {
      nodes.splice(index, 1);
      return true;
    }
    for (const node of nodes) {
      if (node.children && this.removeNode(node.children, target)) {
        return true;
      }
    }
    return false;
  }

  public showDelete(param: ObjectType, ops: ObjectType[]) {
    if (param.depth === 0 && ops.length === 1) {
      return false;
    }
    if (param.depth > 0) {
      const parentNode = this.getParentNode(ops, param);
      if (parentNode && parentNode.children.length === 1) {
        return false;
      }
    }
    return true;
  }

  // 修复1：使用扩展运算符重新赋值来触发 Angular 的深层视图变更检测
  deleteObjectNodeParam(param: ObjectType) {
    const parentNodeParam = this.getParentNode(this.objectsParams, param);
    this.removeNode(this.objectsParams, param);

    if (parentNodeParam && this.isObjectLikeType(parentNodeParam?.type) && parentNodeParam?.children?.length === 0) {
      delete parentNodeParam.children;
    }

    this.objectsParams = [...this.objectsParams];
  }

  onObjectParamTypeChange(param: ObjectType) {
    const type = param?.type?.join('/');
    if (this.isSimpleType(type) && param?.children) {
      delete param?.children;
      return;
    }

    if (type.startsWith('array') && type !== 'array<object>' && param?.children) {
      delete param?.children;
    }

    if (this?.isObjectLikeType(param?.type)) {
      if (!param?.children) {
        this.addChild(param);
      }
    }

    if (param.value.default) {
      param.value.default = null;
    }
  }

  addChild(param: ObjectType) {
    const child = {
      ...this.getInitParamConfig(),
      depth: param.depth + 1,
      parentType: param.type[0] as ObjectParentType,
      type: ['string'],
    };

    if (param?.children) {
      param.children.push(child);
    } else {
      param.children = [child];
    }
    param.expanded = true;
  }

  onObjectNameChange() {
    window.setTimeout(() => {
      if (this.objectForm && this.objectForm.control) {
        this.objectForm.control.updateValueAndValidity();
      }
    });
  }

  getObjectInputNames(param: ObjectType): { existingValues: string[] } {
    let names = [];
    if (param.depth === 0) {
      names = this.objectsParams.map(arg => arg.name);
    } else {
      const parentNode = this.getParentNode(this.objectsParams, param);
      names = parentNode?.children.map(arg => arg.name) || [];
    }

    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  showSetDefault(param: ObjectType) {
    return param.depth === 0;
  }

  showModal(type: string, data?: any): void {
    if (type === 'create') {
      this.addObjectsParam();
      this.modalTypeName = this.i18n.transform('create_object');
    } else if (type === 'edit') {
      this.modalTypeName = this.i18n.transform('edit_object');
      this.structuredObjectId = data.id;
      this.formGroup.setValue({ name: data.name });
      this.objectsParams = this.objectFields2Views(JSON.parse(data.schemas));
    }
    this.showEdit = true;
  }

  public addObjectsParam(): void {
    this.objectsParams.push({
      ...this.getInitParamConfig(),
      depth: 0,
      parentType: 'none' as ObjectParentType,
      type: ['string'],
    });
  }

  getInitParamConfig(): ObjectField {
    return {
      name: '',
      type: 'string',
      description: '',
      reflection: false,
      value: {
        type: 'generated',
        default: '',
        content: null,
        hint: '',
      },
    };
  }

  hideModal(): void {
    this.clearValue();
    this.formGroup.reset();
    this.showEdit = false;
  }

  private getInvalidVarTip(): string {
    const first = this.objectForm
      ? Object.values(this.objectForm.controls).find(c => c.invalid)
      : undefined;
    const errors = first?.errors as { serviceName?: { tiErrorMessage?: string } } | null;
    return errors?.serviceName?.tiErrorMessage || this.i18n.transform('check_form_error');
  }

  createOrEdit() {
    Object.values(this.formGroup.controls).forEach(c => {
      c.markAsDirty();
      c.updateValueAndValidity({ onlySelf: true });
    });

    if (this.formGroup.invalid) {
      this.message.warning(this.i18n.transform('validation_name_tip'));
      return;
    }

    if (this.objectForm && this.objectForm.invalid) {
      Object.values(this.objectForm.controls).forEach(c => {
        c.markAsDirty();
        c.updateValueAndValidity({ onlySelf: true });
      });
      this.message.warning(this.getInvalidVarTip());
      return;
    }

    if (this.structuredObjectId) {
      this.editStructuredObject();
    } else {
      this.createStructuredObject();
    }
  }

  createStructuredObject() {
    let params = {
      name: this.formGroup.get('name').value,
      schemas: JSON.stringify(this.objectTypeViews2Fields(this.objectsParams)),
    };
    setTimeout(() => {
      this.objectManageService.createObject(params).then(() => {
        this.searchList();
        this.hideModal();
      });
    });
  }

  objectFields2Views(fields: ObjectField[], depth = 0, parentType: ObjectParentType = 'none'): ObjectType[] {
    const views: ObjectType[] = fields.map(field => {
      const { name, type, description, schema, value } = field;
      const view: ObjectType = {
        name,
        type: type.split('/'),
        description,
        depth,
        parentType,
        value,
      };

      if (type === 'array') {
        if ((schema as ObjectField).type === 'object') {
          view.type = ['array<object>'];
          view.children = this.objectFields2Views(((schema as ObjectField)?.schema ?? []) as ObjectField[], depth + 1, view.type[0] as ObjectParentType);
          view.expanded = true;
        } else {
          const subType = (schema as ObjectField).type;
          if (subType.includes('file')) {
            const fileType = subType.split('/')[1];
            view.type = [`${type}<file>`, fileType];
          } else {
            view.type = [`array<${subType}>`];
          }
        }
      }

      if (type === 'object') {
        view.children = this.objectFields2Views((schema ?? []) as ObjectField[], depth + 1, view.type[0] as ObjectParentType);
        view.expanded = true;
      }
      return view;
    });
    return views;
  }

  objectTypeViews2Fields(views: ObjectType[]): ObjectField[] {
    const fields: ObjectField[] = views.map(view => {
      const { name, description, children, value } = view;
      const type = view.type.join('/') as ObjectFieldType;
      const field: ObjectField = { name, type, description, value };

      if (type.startsWith('array<')) {
        field.type = 'array';
        let itemType;
        if (type.includes('file')) {
          itemType = `${type.match(/array<(.+)>/)[1]}/${view.type[1]}`;
        } else {
          itemType = type.match(/array<(.+)>/)[1];
        }
        (field.schema as ObjectField) = { name: '', type: itemType as ObjectFieldType };

        if (itemType === 'object') {
          (field.schema as ObjectField).schema = this.objectTypeViews2Fields(children);
        }
      }

      if (field.type === 'object') {
        field.schema = this.objectTypeViews2Fields(children);
      }
      return field;
    });
    return fields;
  }

  editStructuredObject() {
    let params = {
      id: this.structuredObjectId,
      name: this.formGroup.get('name').value,
      schemas: JSON.stringify(this.objectTypeViews2Fields(this.objectsParams)),
    };
    this.objectManageService.editObjects(params).then(() => {
      this.searchList();
      this.hideModal();
    });
  }

  clearValue() {
    this.formGroup.setValue({ name: '' });
    this.objectsParams = [];
    this.structuredObjectId = '';
  }

  async getObjectsListData(): Promise<void> {
    try {
      this.loading = true;
      const result = await this.objectManageService.getObjectsList({
        limit: this.pageSize.size,
        offset: (this.currentPage - 1) * this.pageSize.size,
        ...(this.searchValue && { name: this.searchValue }),
      });
      this.srcData.data = result.objects || [];
      this.srcData.data.forEach(i => {
        try {
          const r = JSON.parse(i.schemas);
          i.schemasFormat = JSON.stringify(r, null, 2);
        } catch (e) {
          //暂不处理
        }
      });
      this.totalNumber = result.count;
    } finally {
      this.loading = false;
      this.isShowNoDataGuide = !this.srcData.data?.length && !this.loading && this.searchNameIsEmpty;
      this.isFirstLoading = false;
    }
  }

  protected readonly JSON = JSON;

  public onSearchChange(value: string): void {
    if (!value) {
      this.searchList();
    }
  }
}
