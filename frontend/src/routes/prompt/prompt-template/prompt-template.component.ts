import { ChangeDetectorRef, Component, Injector, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { from, Observable, Subject } from 'rxjs';
import { I18nNamespace } from '@i18n';
import { ActivatedRoute, Router } from '@angular/router';
import { PromptService } from '@services/prompt.service';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { CreateTemplateComponent } from '@routes/prompt/prompt-template/create-template/create-template.component';
import { CommonNoDataComponent } from '@shared/components/common-no-data/common-no-data.component';
import { iconList, industryTagColor, ViewTemplateComponent } from '@routes/prompt/prompt-template/view-template/view-template.component';
import { SystemTemplateComponent } from '@routes/prompt/prompt-template/system-template/system-template.component';
import { PromptWritingRepoService } from '@services/repositories/prompt-writing-repo.service';
import { IPaginationListResp, ITmplCard, ITmplCardListResp } from '@interfaces/prompt/prompt-template.interface';
import { IBaseSelectItem, IBaseSelectResp } from '@interfaces/prompt/common.interface';
import { PromptTmplService } from '@services/prompt-template.service';
import { ConsoleFrameworkService } from '@core/services';
import { PromptOptimizeTaskListComponent } from '@routes/prompt/prompt-optimize-task-list/prompt-optimize-task-list.component';
import { PromptSaveComponent } from '@routes/prompt/prompt-save/prompt-save.component';
import { ExportHalfModalComponent } from '@shared/components/export-half-modal/export-half-modal.component';
import { ApplicationType } from '@enums/agent-center.enum';
import { CommonUtils } from 'src/utils/common.util';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { ImportTemplateModalComponent } from '@routes/prompt/prompt-template/import-template-modal/import-template-modal.component';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { CommonService } from '@services/common.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { HttpService } from '@services/http.service';
import { PipesModule } from '../../../pipes/pipes.module';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { FormsModule } from '@angular/forms';

interface MenuItem {
  id: string;
  title: string;
  disabled?: boolean;
}

interface PageSizeConfig {
  options: number[];
  size: number;
}

interface SearchboxItem {
  label: string;
  field: string;
  options?: any[];
}

interface SearchboxTag {
  field: string;
  value?: string;
}

@Component({
  selector: 'meta-prompt-template',
  templateUrl: './prompt-template.component.html',
  styleUrls: ['./prompt-template-common.scss', './prompt-template.component.scss', '../share/styles/common-styles.less'],
  standalone: true,
  imports: [
    COMMON_MODULES,
    MODULES,
    CommonNoDataComponent,
    SystemTemplateComponent,
    PromptOptimizeTaskListComponent,
    NewCommonNoDataWithBtnComponent,
    PipesModule,
    NoDataGuideComponentComponent,
    NzTableModule,
    NzTagModule,
    NzPaginationModule,
    NzSelectModule,
    NzInputModule,
    NzDropDownModule,
    NzSpinModule,
    NzTabsModule,
    NzIconModule,
    NzButtonModule,
    FormsModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM, I18nNamespace.GUIDE],
    },
    NzModalService,
    NzMessageService,
    NzDrawerService,
  ],
})
export class PromptTemplateComponent implements OnInit, OnDestroy {
  @ViewChild(SystemTemplateComponent) systemTemplate: SystemTemplateComponent;

  @ViewChild('promptOptimizeList')
  promptOptimizeList: PromptOptimizeTaskListComponent;
  private destroy$ = new Subject<void>();
  tabSelectedIndex = 0;
  protected readonly iconList = iconList;

  public typeImages = {
    text: cdnAssetUrl('assets/prompt/type-text-green.svg'),
    multi: cdnAssetUrl('assets/prompt/type-multi.svg'),
  };
  public isOpAccount = false;

  public tagOptions: IBaseSelectItem[];

  public industryOptions: IBaseSelectItem[] = [];

  public selectedtags: IBaseSelectItem[] = [];

  public selectedIndustry: IBaseSelectItem[] = [];

  public isHideList = true;

  public isHideCard = false;

  public tmpName = '';

  public cards: ITmplCard[] = [];

  public cardChecked: string[] | Set<string> = [];

  public currentCardPage = 1;

  public totalCardNumber = 0;

  public isLodingCard = false;

  public taskId = '';

  public cardPageSize: PageSizeConfig = {
    options: [12, 24, 48, 64],
    size: 12,
  };
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public setTotalCardNumber(number: number) {
    this.totalCardNumber = number;
  }

  public items: MenuItem[] = this.items_list();

  public searchItems: SearchboxItem[] = [
    {
      label: this.i18n.transform('base_name'),
      field: 'template_name',
    },
    {
      label: this.i18n.transform('base_content'),
      field: 'content',
    },
    {
      label: 'ID',
      field: 'template_id',
      options: [],
    },
  ];

  public searchedItems = '';

  public language = this.consoleFrameworkService?.dataService?.getLocale() ?? 'zh-cn';

  public currActiveTab = 0;

  public tabs = [
    {
      active: true,
      header: this.i18n.transform('my_prompt'),
    },
    {
      active: false,
      header: this.i18n.transform('prompt_tmpl_optimize'),
    },
  ];
  private openModalRef: any;

  public subTabs: Array<any> = [
    {
      title: this.i18n.transform('prompt'),
      id: 'prompt',
      active: true,
    },
    {
      title: this.i18n.transform('optimization_task'),
      id: 'optimize',
      active: false,
    },
  ];
  public buttonGroupSelected: string = this.subTabs[0].id;
  public isShowGuide = true;
  public isFirstLoading = true;
  get isShowNoDataGuide() {
    return !this.cards?.length && !this.isLodingCard && this.searchNameIsEmpty;
  }

  get searchNameIsEmpty() {
    return this.searchedItems.length === 0 && this.selectedtags.length === 0 && this.selectedIndustry.length === 0;
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private nzModal: NzModalService,
    private service: PromptService,
    private injector: Injector,
    private router: Router,
    private promptWritingRepoServ: PromptWritingRepoService,
    private promptTmplServ: PromptTmplService,
    private nzDrawerService: NzDrawerService,
    private commonLogic: agentCommonLogic,
    private readonly consoleFrameworkService: ConsoleFrameworkService,
    private commonService: CommonService,
    private nzMessage: NzMessageService,
    private readonly http: HttpService,
    private route: ActivatedRoute,
    protected cdr: ChangeDetectorRef
  ) {
    this.http.getCurrentUserResourceStatus().subscribe(res => {
      this.items = this.items_list();

      this.cdr.markForCheck();
    });
    const activeTab = StorageService.getSessionStorage('activeTab');
    if (activeTab) {
      StorageService.delSessionStorage('activeTab');
      this.tabSelectedIndex = 1;
      this.subTabs[0].active = false;
      this.subTabs[1].active = true;
      this.buttonGroupSelected = this.subTabs[activeTab].id;
    }
  }

  public items_list(): MenuItem[] {
    return [
      {
        id: 'optimize',
        title: this.i18n.transform('writing_menu_optimize'),
        disabled: !this.subscribeBtnStatus,
      },
      {
        id: 'edit',
        title: this.i18n.transform('base_edit'),
        disabled: !this.subscribeBtnStatus,
      },
      {
        id: 'delete',
        title: this.i18n.transform('base_remove'),
        disabled: !this.subscribeBtnStatus,
      },
    ];
  }

  handleClickClearSearch() {
    this.searchedItems = '';
    this.selectedtags = [];
    this.selectedIndustry = [];
    this.currentCardPage = 1;
    this.getData();
  }

  public ngOnInit(): void {
    this.currActiveTab = this.router.url.indexOf('prompt-template') > -1 ? 0 : 1;
    this.getData();

    window.addEventListener('WorkspaceChange', () => {
      this.getData();
    });
  }

  public getData(): void {
    if (this.currActiveTab === 1) {
      this.getTagList();
      this.getCardData();
    }
  }

  public ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    window.removeEventListener('WorkspaceChange', () => {
      this.getData();
    });
  }

  public showCard() {
    this.isHideList = true;
    this.isHideCard = false;
  }

  public showList() {
    this.isHideList = false;
    this.isHideCard = true;
  }

  public getTableData(requestParams: any): Observable<any> {
    return this.service.getPromptTemplateList(requestParams);
  }

  public getTagList = () => {
    const params = {
      limit: 1000,
      offset: 0,
    };
    this.service.getIndustryList().subscribe({
      next: (data: IBaseSelectResp[]) => {
        this.industryOptions = data.map(ind => {
          return {
            id: ind.id,
            label: this.language === 'en-us' ? ind.name_en || ind.name : ind.name,
          };
        });
      },
    });
    this.service.getTagList(params).subscribe({
      next: (res: IPaginationListResp) => {
        this.tagOptions = res.data.map(tag => {
          return {
            id: tag.id,
            label: this.language === 'en-us' ? tag.nameEn || tag.name : tag?.name,
          };
        });
      },
    });
  };

  public handleSearch() {
    setTimeout(() => {
      this.getData();
    }, 0);
  }

  public getCardData() {
    this.isLodingCard = true;
    this.setTotalCardNumber(0);
    this.cards = [];
    const params = {
      limit: this.cardPageSize.size,
      offset: ((this.currentCardPage || 1) - 1) * this.cardPageSize.size,
      template_name: this.searchedItems,
      template_id: '',
      content: '',
      tag_list: this.selectedtags || [],
      industry_list: this.selectedIndustry || [],
    };

    from(this.getTableData(params)).subscribe({
      next: (res: ITmplCardListResp) => {
        this.cards = res.data;
        this.searchItems.find(item => item.field === 'template_id').options = res.data.map(d => ({ label: d.template_id }));
        this.setTotalCardNumber(res?.count);
        this.isLodingCard = false;
      },
      error: () => {
        this.isLodingCard = false;
        this.cards = [];
      },
      complete: () => {
        this.isLodingCard = false;
        this.isFirstLoading = false;
      },
    });
  }

  public toOptimize(row: ITmplCard) {
    this.router.navigate(['/home/prompt/optimize/create'], {
      queryParams: {
        prompt_id: row.template_id,
      },
    });
  }
  public toDelNew(row?: Array<any>): void {
    const modalInstance = this.nzModal.confirm({
      nzTitle: this.i18n.transform('confirm_delete_prompt_desc'),
      nzContent: this.i18n.transform('confirm_delete_data_unrecoverable_desc'),
      nzCancelText: this.i18n.transform('cancel'),
      nzOkText: this.i18n.transform('ok'),
      nzOkDanger: true,
      nzOnOk: (): void => {
        this.deleteTemplates(row as ITmplCard[]);
      },
    });
  }
  public toDel(row?: Array<any>): void {
    const confirmText = `${this.i18n.transform('prompt_tmpl_confirm_text').replace('{0}', `${row?.length ?? 0}`)}`;

    this.nzModal.confirm({
      nzTitle: this.i18n.transform('prompt_tmpl_confirm'),
      nzContent: confirmText,
      nzCancelText: this.i18n.transform('cancel'),
      nzOkText: this.i18n.transform('ok'),
      nzOkDanger: true,
      nzOnOk: (): void => {
        this.deleteTemplates(row as ITmplCard[]);
      },
    });
  }

  public deleteTemplates(params: ITmplCard[]) {
    this.service.deletePromptTemplate(params[0].template_id).subscribe({
      next: () => {
        this.cardChecked = this.promptTmplServ.deleteCheckedTmplId(this.cardChecked as string[], params[0].template_id);
        MessageComponent.showSuccess(this.i18n.transform('base_delete_success'));
        this.getCardData();
      },
    });
  }

  public onPreferenceConfigChangeOutput($event: any) {
    if ($event.preferenceView === 'card') {
      this.showCard();
    }
  }

  private setCreateBtnByOpAccount(isOpAccount) {
    if (isOpAccount) {
      this.isOpAccount = true;
    } else {
      this.isOpAccount = false;
    }
  }

  public onActiveChange(isActive) {
    if (isActive) {
      this.setIsOpAccount();
    } else {
      this.isOpAccount = false;
    }
  }

  public setMouseEnter(tmpId: string) {
    document.getElementById(`menu-labelkey${tmpId}`).style.display = 'block';
  }

  public setMouseLeave(tmpId: string) {
    document.getElementById(`menu-labelkey${tmpId}`).style.display = 'none';
  }

  public onClick(event: Event) {
    event.stopPropagation();
  }

  public isExportDisabled(): boolean {
    return (this.cardChecked as string[]).length === 0;
  }

  public onSelect(event: MenuItem, item: ITmplCard) {
    if (event.id === 'edit') {
      this.openSaveModal(item);
    }
    if (event.id === 'delete') {
      this.toDelNew([item]);
    }
    if (event.id === 'optimize') {
      this.toOptimize(item);
    }
  }

  public onPageUpdate(page: number): void {
    this.currentCardPage = page;
    this.getCardData();
  }

  public onPageSizeChange(e): void {
    this.cardPageSize.size = e;
    this.getCardData();
  }

  public openCardDetail(card: any) {
    if (this.subscribeBtnStatus) {
      const modalRef: NzModalRef = this.nzModal.create({
        nzContent: ViewTemplateComponent,
        nzClassName: 'modal-view-template',
        nzWidth: 800,
      });
      const instance = modalRef.componentInstance;
      instance.currentTmpl = card;
    }
  }

  public exportCardData(): void {
    this.service.exportPromptTmpl(this.cardChecked as string[]).subscribe({
      next: res => {
        CommonUtils.downloadFile(
          new Blob([res.data], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          }),
          res.headers.get('Content-Disposition')
        );
      },
    });
  }

  public getCheckedBorderStyle(id: string): Record<string, string> {
    return this.promptTmplServ.getCheckedCardStyle(this.cardChecked as string[], id);
  }

  private openEditTemplate(params: any) {
    const modalRef: NzModalRef = this.nzModal.create({
      nzTitle: this.i18n.transform('prompt_tmpl_edit_prompt'),
      nzContent: CreateTemplateComponent,
      nzClassName: 'modal-large1000-class',
      nzWidth: 1000,
      nzData: {
        data: params,
      },
      nzOnOk: (res): void => {
        modalRef.destroy(res);
      },
    });
    modalRef.afterClose.subscribe(() => {
      this.getCardData();
    });
  }

  private setIsOpAccount(): void {
    this.promptWritingRepoServ.isOpAccount().subscribe(res => {
      this.setCreateBtnByOpAccount(res);
    });
  }

  public handleTabChange(selectIndex: number) {
    this.subTabs.forEach((item, index) => {
      item.active = selectIndex === index;
    });
    const tab = this.subTabs[selectIndex];
    if (tab.active) {
      this.isFirstLoading = true;
      this.buttonGroupSelected = tab.id;
      if (this.buttonGroupSelected === this.subTabs[0]?.id) {
        this.getData();
      }
      if (this.buttonGroupSelected === this.subTabs[1]?.id) {
        this.isFirstLoading = true;
        this.promptOptimizeList.listTasks();
      }
    }
  }

  public changePromptButton() {
    this.subTabs[0].active = true;
    this.subTabs[1].active = false;
    this.handleTabChange(0);
  }

  private closeCurrentModal() {
    this.openModalRef?.close();
  }

  public openSaveModal(template: ITmplCard = null) {
    this.closeCurrentModal();
    let InitInfo = {};
    let title = this.i18n.transform('prompt_tmpl_create_prompt');
    let isUpdate = false;
    if (template) {
      title = this.i18n.transform('prompt_tmpl_edit_prompt');
      isUpdate = true;
      let variableList: any[];
      try {
        variableList = JSON.parse(template?.variables || '[]').map(item => {
          return {
            type: item.type === 'text' ? 'text' : 'image',
            value: item.name,
          };
        });
      } catch (e) {
        variableList = [];
      }
      InitInfo = {
        promptId: template.template_id,
        name: template.template_name,
        desc: template.description,
        prompt: template.content,
        tags: template.tag_list,
        industry: template.industry,
        type: template.pt_type,
        variableList: variableList,
      };
    }
    const drawerRef = this.nzDrawerService.create({
      nzWidth: '700px',
      nzContent: PromptSaveComponent,
      nzClosable: true,
      nzData: {
        promptSaveInitInfo: InitInfo,
        savePromptTemplate: promptTemplate => {
          if (isUpdate) {
            this.service.updatePromptV2(promptTemplate).then(res => {
              MessageComponent.showSuccess(this.i18n.transform('modify_prompt_template_success'));
              this.closeCurrentModal();
              this.getCardData();
            });
          } else {
            this.service.createPromptV2(promptTemplate).then(res => {
              MessageComponent.showSuccess(this.i18n.transform('create_prompt_template_success'));
              this.closeCurrentModal();
              this.getCardData();
            });
          }
        },
      },
    });

    this.openModalRef = drawerRef;
  }

  public exportTemplate() {
    this.closeCurrentModal();
    const drawerRef = this.nzDrawerService.create({
      nzWidth: '700px',
      nzContent: ExportHalfModalComponent,
      nzData: {
        exportType: ApplicationType.PROMPT,
        exportTypeOptions: [
          {
            id: ApplicationType.PROMPT,
            text: this.i18n.transform('export_template'),
            desc: '',
            colName: this.i18n.transform('base_prompt'),
            rowKey: 'template_id',
          },
        ],
        confirm: ({ rows }: any) => {
          this.service.exportPromptTmplV2(rows.map((row: any) => row.template_id)).subscribe({
            next: (res: any) => {
              CommonUtils.downloadFile(
                new Blob([res.data], {
                  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }),
                res.headers.get('Content-Disposition')
              );
            },
          });
        },
      },
      nzClosable: true,
      nzMaskClosable: true,
      nzZIndex: 10000,
    });
    this.cdr.detectChanges();
  }

  public importTemplate() {
    this.closeCurrentModal();
    const modalRef: NzModalRef = this.nzModal.create({
      nzTitle: '',
      nzWidth: '600px',
      nzContent: ImportTemplateModalComponent,
      nzFooter: null,
    });
    modalRef.afterClose.subscribe(() => {
      this.getCardData();
    });
  }

  public handleGuideClick(e) {
    if (!this.subscribeBtnStatus) {
      return;
    }
    if (e === 'create') {
      this.openSaveModal();
    }
    if (e === 'import') {
      this.importTemplate();
    }
    if (e === 'createTask') {
      this.tabSelectedIndex = 1;
      this.subTabs.forEach((item, index) => {
        item.active = index === 1;
      });
      this.buttonGroupSelected = this.subTabs[1].id;
      this.promptOptimizeList.handleGuideClick('createTask');
    }
    if (e === 'taskList') {
      this.tabSelectedIndex = 1;
      this.subTabs.forEach((item, index) => {
        item.active = index === 1;
      });
      this.buttonGroupSelected = this.subTabs[1].id;
      this.promptOptimizeList.handleGuideClick('taskList');
    }
  }

  protected readonly changeUrl = cdnAssetUrl;
  protected readonly industryTagColor = industryTagColor;
  protected readonly length = length;
}
