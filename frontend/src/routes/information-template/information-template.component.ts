import { CommonModule } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { UntypedFormControl, UntypedFormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MonacoEditorComponent, MonacoEditorConstructionOptions, MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { InformationTemplateService } from '@routes/information-template/information-template.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { CommonUtils } from '../../utils/common.util';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { visibilityItemsMap, uploadStatusMap } from '@routes/information-template/information-template.map';
import { CommonValidation } from '@shared/validation/commonValidation';
import { CommonService } from '@services/common.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { HttpService } from '@services/http.service';
import { Subscription } from 'rxjs';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzModalModule, NzModalService, NzModalRef } from 'ng-zorro-antd/modal';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzUploadModule } from 'ng-zorro-antd/upload';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzUploadFile } from 'ng-zorro-antd/upload';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'information-template',
  templateUrl: './information-template.component.html',
  styleUrls: ['./information-template.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    FormsModule,
    ReactiveFormsModule,
    MonacoEditorModule,
    NewCommonNoDataWithBtnComponent,
    NoDataGuideComponentComponent,
    NzButtonModule,
    NzIconModule,
    NzInputModule,
    NzTableModule,
    NzPaginationModule,
    NzDropDownModule,
    NzModalModule,
    NzDrawerModule,
    NzFormModule,
    NzRadioModule,
    NzToolTipModule,
    NzUploadModule,
    NzAlertModule,
    NzBadgeModule,
    NzSpinModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.KNOWLEDGE, I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.GUIDE],
    },
    NzModalService,
  ],
})
export class InformationTemplateComponent implements OnInit, OnDestroy {
  @ViewChild('editorCmp') editorCmp!: MonacoEditorComponent;
  @ViewChild('jsonEditor') jsonEditor!: MonacoEditorComponent;

  private subscriptions = new Subscription();
  private modalTimeout: any;

  showEdit = false;
  isFullScreen = false;
  loading = false;
  showUpload = false;
  isDrawerVisible = false;

  displayedData = [];
  srcData = {
    data: [],
    state: undefined,
  };

  checkedList: any[] = [];
  allChecked = false;
  indeterminate = false;

  importSrcData = {
    data: [],
    state: undefined,
  };

  currentPage = 1;
  totalNumber = 0;
  readonly pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  searchValue = '';
  modalTypeName = '';
  structuredMessagesId = '';
  informationTemplateFile: any = null;
  formGroup = new UntypedFormGroup({
    name: new UntypedFormControl({ value: '', disabled: false }, [
      Validators.required,
      CommonValidation.customVerify(/^[A-Za-z0-9\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_-]{1,64}$/, this.i18n.transform('validation_name_tip')),
      Validators.minLength(2),
      Validators.maxLength(64),
    ]),
  });

  readonly listColumns = [
    { title: '' },
    { title: this.i18n.transform('message_name') },
    { title: this.i18n.transform('message_body') },
    { title: this.i18n.transform('message_category') },
    { title: this.i18n.transform('visible_scope') },
    {
      title: this.i18n.transform('operation'),
      fixed: 'right' as const,
      width: '120px',
    },
  ];

  readonly messageClassItems = [
    { text: this.i18n.transform('exception'), disabled: false },
    {
      text: this.i18n.transform('custom'),
      disabled: true,
      tipContent: this.i18n.transform('not_open_yet'),
      tipPosition: 'right',
    },
  ];

  readonly visibilityItems = [
    {
      id: 'tenant',
      label: this.i18n.transform('in_tenant'),
      value: 'tenant',
    },
    {
      id: 'workspace',
      label: this.i18n.transform('in_workspace'),
      value: 'workspace',
    },
    {
      id: 'personal',
      label: this.i18n.transform('in_personal'),
      value: 'personal',
    },
  ];
  importModalRef = null;

  readonly importColumns = [
    { title: this.i18n.transform('check1') },
    { title: this.i18n.transform('name') },
    { title: this.i18n.transform('message_body') },
    { title: this.i18n.transform('message_category') },
    { title: this.i18n.transform('visible_scope') },
    { title: '失败原因' },
  ];

  readonly editorOptions: MonacoEditorConstructionOptions = {
    theme: 'vs',
    language: 'json',
    minimap: { enabled: false },
    formatOnPaste: true,
    formatOnType: true,
  };

  // 状态
  messageClassSelectedText = this.messageClassItems[0].text;
  visibilitySelected = 'workspace';
  jsonData = '';
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  public isShowGuide = true;
  public isShowNoDataGuide = false;
  public isFirstLoading = true;

  constructor(
    private informationTemplateService: InformationTemplateService,
    public router: Router,
    private nzModal: NzModalService,
    private message: NzMessageService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private commonLogic: agentCommonLogic,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private i18n: I18NextEagerPipe
  ) {}

  ngOnInit(): void {
    this.getStructuredMessagesListData();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    if (this.modalTimeout) {
      clearTimeout(this.modalTimeout);
    }
  }

  get searchNameIsEmpty(): boolean {
    return this.searchValue.length === 0;
  }

  handleClickClearSearch() {
    this.searchValue = '';
    this.searchList();
  }

  trackByFn(index: number, item: any) {
    return item.id;
  }

  pageUpdate(event) {
    this.currentPage = event.currentPage;
    this.pageSize.size = event.size;
    this.getStructuredMessagesListData();
  }

  searchList() {
    this.currentPage = 1;
    this.pageSize.size = 10;
    this.getStructuredMessagesListData();
  }

  listAction($event: any, row: any) {
    if ($event.key === 'delete') {
      this.deleteStructuredMessagesData(row);
    } else if ($event.key === 'edit') {
      this.showModal('edit', row);
    }
  }

  onAllChecked(checked: boolean): void {
    this.srcData.data.forEach(item => this.updateCheckedSet(item, checked));
    this.refreshCheckedStatus();
  }

  onItemChecked(item: any, checked: boolean): void {
    this.updateCheckedSet(item, checked);
    this.refreshCheckedStatus();
  }

  updateCheckedSet(item: any, checked: boolean): void {
    if (checked) {
      if (!this.checkedList.includes(item) && !item.disabled) {
        this.checkedList.push(item);
      }
    } else {
      this.checkedList = this.checkedList.filter(i => i !== item);
    }
  }

  refreshCheckedStatus(): void {
    const validData = this.srcData.data.filter(item => !(item as any).disabled);
    this.allChecked = validData.length > 0 && validData.every(item => this.checkedList.includes(item));
    this.indeterminate = this.checkedList.length > 0 && !this.allChecked;
  }

  // 单个删除
  deleteStructuredMessagesData(data: any): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('delete_message_template'),
      nzContent: this.i18n.transform('delete_warn', { name: data.name }),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        this.informationTemplateService.deleteStructuredMessages([data]).then(() => {
          this.message.success(this.i18n.transform('delete_success'));
          this.searchList();
          this.checkedList = [];
          this.refreshCheckedStatus();
        });
      },
    });
  }

  // 批量删除
  patchDeleteStructuredMessagesData(): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('delete_message_template'),
      nzContent: this.i18n.transform('confirm_delete_message_templates_desc'),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        this.informationTemplateService.deleteStructuredMessages(this.checkedList).then(() => {
          this.searchList();
          this.message.success(this.i18n.transform('deleted_successfully'));
          this.checkedList = [];
          this.refreshCheckedStatus();
        });
      },
    });
  }

  showModal(type: 'create' | 'edit', data?: any): void {
    this.showEdit = true;

    if (type === 'create') {
      this.modalTypeName = this.i18n.transform('create_message_template');
      this.resetForm();
    } else if (type === 'edit' && data) {
      this.modalTypeName = this.i18n.transform('edit_message_template');
      this.structuredMessagesId = data.id || '';
      this.formGroup.setValue({ name: data.name });
      this.messageClassSelectedText = this.messageClassItems.find(item => item.text === data.category)?.text || this.messageClassItems[0].text;
      this.jsonData = typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2);
      this.visibilitySelected = visibilityItemsMap.get(data.visibility) || 'workspace';
    }

    this.isDrawerVisible = true;
    this.modalTimeout = setTimeout(() => this.formatCode(), 300);
  }

  hideModal(): void {
    this.resetForm();
    this.showEdit = false;
    this.isDrawerVisible = false;
  }

  private resetForm(): void {
    this.formGroup.reset();
    this.messageClassSelectedText = this.messageClassItems[0].text;
    this.visibilitySelected = 'workspace';
    this.jsonData = '';
    this.structuredMessagesId = '';
  }

  createOrEdit(): void {
    if (!this.jsonData) {
      this.message.error(this.i18n.transform('input_message_body'), { nzDuration: 3000 });
      return;
    }

    Object.values(this.formGroup.controls).forEach(control => {
      if (control.invalid) {
        control.markAsDirty();
        control.updateValueAndValidity({ onlySelf: true });
      }
    });

    if (this.formGroup.invalid) {
      return;
    }

    try {
      JSON.parse(this.jsonData);
    } catch (e) {
      this.message.error('Invalid JSON format');
      return;
    }

    this.structuredMessagesId ? this.editStructuredMessages() : this.createStructuredMessagesData();
  }

  private createStructuredMessagesData(): void {
    const params = {
      name: this.formGroup.get('name')?.value,
      category: this.messageClassSelectedText,
      content: JSON.parse(this.jsonData),
      visibility: this.visibilitySelected,
    };

    this.informationTemplateService.createStructuredMessages(params).then(() => {
      this.searchList();
      this.hideModal();
    });
  }

  private editStructuredMessages(): void {
    const params = {
      id: this.structuredMessagesId,
      name: this.formGroup.get('name')?.value,
      category: this.messageClassSelectedText,
      content: JSON.parse(this.jsonData),
      visibility: this.visibilitySelected,
    };

    this.informationTemplateService.editStructuredMessages(params).then(() => {
      this.searchList();
      this.checkedList = [];
      this.refreshCheckedStatus();
      this.hideModal();
    });
  }

  async getStructuredMessagesListData(): Promise<void> {
    try {
      this.loading = true;
      const params = {
        limit: this.pageSize.size,
        offset: (this.currentPage - 1) * this.pageSize.size,
        ...(this.searchValue.trim() && { name: this.searchValue.trim() }),
      };

      const result = await this.informationTemplateService.getStructuredMessagesList(params);
      this.srcData.data = result.message_list || [];
      this.totalNumber = result.count;

      this.checkedList = [];
      this.refreshCheckedStatus();
    } finally {
      this.loading = false;
      this.isShowNoDataGuide = !this.srcData.data?.length && !this.loading && this.searchNameIsEmpty;
      this.isFirstLoading = false;
    }
  }

  importTemplate(content: TemplateRef<any>): void {
    this.importModalRef = this.nzModal.create({
      nzTitle: this.i18n.transform('import_info_template'),
      nzContent: content,
      nzFooter: null,
      nzWidth: 900,
      nzOnCancel: () => {
        this.cleanupImport();
      },
    });
  }

  beforeUpload = (file: NzUploadFile): boolean => {
    if (file.size && file.size > 5242880) {
      this.message.error(this.i18n.transform('file_size_error'));
      return false;
    }
    this.informationTemplateFile = file;
    return false;
  };

  public processImport(modalRef: NzModalRef): void {
    if (!this.informationTemplateFile) return;

    const formData = new FormData();
    formData.append('file', this.informationTemplateFile as any);

    this.informationTemplateService.importStructuredMessages(formData).then(res => {
      this.importSrcData.data = [];

      const successList = res.success_list.map(item => ({ ...item, status: 'success' }));
      const failList = res.failed_list.map(item => ({ ...item, status: 'error' }));

      this.importSrcData.data.push(...successList, ...failList);
      if (successList.length > 0 && failList.length > 0) {
        this.message.info(this.i18n.transform('partial_import_success'));
      } else if (successList.length > 0) {
        this.message.success(this.i18n.transform('import_info_template_success'));
      } else if (failList.length > 0) {
        this.message.error(this.i18n.transform('import_failed'));
      }

      this.showUpload = !this.showUpload;
      this.informationTemplateFile = null;
      this.searchList();
    });
  }

  cleanupImport(): void {
    this.checkedList = [];
    this.refreshCheckedStatus();
    this.informationTemplateFile = null;
    this.importSrcData.data = [];
    this.importModalRef?.destroy();
  }

  exportTemplate(): void {
    const params = {
      messages_ids: this.checkedList.map(item => item.id),
    };

    this.informationTemplateService.exportStructuredMessages(params).then(res => {
      CommonUtils.downloadFile(new Blob([res], { type: 'application/json' }), `${this.commonLogic.getFormattedDateTime()}.xlsx`, true);
      this.checkedList = [];
      this.refreshCheckedStatus();
    });
  }

  downloadTemplate() {
    this.informationTemplateService.downloadTemplate().then(res => {
      CommonUtils.downloadFile(new Blob([res], { type: 'application/json' }), `${this.i18n.transform('message_template')}.xlsx`, true);
    });
  }

  formatCode() {
    this.editorCmp?.editor?.getAction('editor.action.formatDocument')?.run();
  }

  expandScreen() {
    this.isFullScreen = true;
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.isDrawerVisible = false;
  }

  closeScreen() {
    this.isFullScreen = false;
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.isDrawerVisible = true;
  }

  readonly uploadStatusMap = uploadStatusMap;
}
