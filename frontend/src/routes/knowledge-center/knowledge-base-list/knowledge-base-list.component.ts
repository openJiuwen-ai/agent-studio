import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, inject, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import { NzDrawerService, NzDrawerModule } from 'ng-zorro-antd/drawer';
import { FormsModule } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CreateThirdPartyComponent } from '@routes/knowledge-center/components/create-third-party/create-third-party.component';
import { DefaultConfigModalComponent } from '@routes/knowledge-center/components/default-config-modal/default-config-modal.component';
import { KbCardDisplayComponent } from '@routes/knowledge-center/components/kb-card-display/kb-card-display.component';
import { KnowledgeBaseAccessCardComponent } from '@routes/knowledge-center/components/knowledge-base-access-card/knowledge-base-access-card.component';
import { KbSourceConnectionComponent } from '@routes/knowledge-center/kb-source-connection/kb-source-connection.component';
import { KbCardDisplayConfig, KbItem, KbTagType } from '@routes/knowledge-center/knowledge-base.interface';
import { KnowledgeBaseType } from '@routes/knowledge-center/knowledge.types';
import { ReferenceModalComponent } from '@routes/knowledge-center/knowledge/reference-modal/reference-modal.component';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { KbOperationFilterService } from '@services/knowledge-center/kb-operation-filter.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { formatTime } from 'src/utils/commonFn';
import { PipesModule } from '../../../pipes/pipes.module';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { CommonUtils } from '../../../utils/common.util';
import { KnowledgeBaseEditComponent } from '../components/knowledge-base-edit/knowledge-base-edit.component';
import { SelectCreateTypeComponent } from '../components/select-create-type/select-create-type.component';
import { KnowledgeFormDrawerComponent } from '../knowledge-form-drawer/knowledge-form-drawer.component';
import { KnowledgeBaseExceedModalComponent } from '@routes/knowledge-center/components/knowledge-base-exceed-modal/knowledge-base-exceed-modal.component';
import { KnowledgeBaseListService } from './knowledge-base-list.component.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { knowledgeBaseDeleteTitleMap, knowledgeBaseSourceMap, knowledgeBaseStatusMap, KnowledgeType, KB_SHARE_SCOPE_NAME_MAP } from './knowledge-base-list.map';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';

export interface ActionMenuItem {
  label: string;
  key: string;
  disabled?: boolean;
}

export interface SearchboxItem {
  label: string;
  field: string;
  valueKey?: string;
  options?: any[];
}

@Component({
  selector: 'knowledge-base-list',
  templateUrl: './knowledge-base-list.component.html',
  styleUrls: ['./knowledge-base-list.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    KnowledgeBaseEditComponent,
    SelectCreateTypeComponent,
    CreateThirdPartyComponent,
    KnowledgeBaseAccessCardComponent,
    DefaultConfigModalComponent,
    NewCommonNoDataWithBtnComponent,
    KbSourceConnectionComponent,
    PipesModule,
    KnowledgeBaseExceedModalComponent,
    KbCardDisplayComponent,
    NoDataGuideComponentComponent,
    NzTabsModule,
    NzButtonModule,
    NzSelectModule,
    NzInputModule,
    NzTableModule,
    NzPaginationModule,
    NzDropDownModule,
    NzTagModule,
    NzBadgeModule,
    NzIconModule,
    NzSpinModule,
    NzTypographyModule,
    NzToolTipModule,
    NzModalModule,
    NzDrawerModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.KNOWLEDGE, I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER, I18nNamespace.GUIDE],
    },
    NzMessageService,
    NzModalService,
    NzDrawerService,
  ],
})
export class KnowledgeBaseListComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('selectCreateType') selectCreateType: SelectCreateTypeComponent;
  @ViewChild('createThirdPartyRef') createThirdPartyRef: any;
  @ViewChild('kbSourceConnection') kbSourceConnection: KbSourceConnectionComponent;
  @ViewChild('defaultConfigModalRef') defaultConfigModalRef: any;
  @ViewChild('knowledgeBaseEdit') knowledgeBaseEdit: KnowledgeBaseEditComponent;
  @ViewChild('exceedModal') exceedModal: KnowledgeBaseExceedModalComponent;

  public isShowGuide = true;
  public isFirstLoading = true;

  get isNoDataGuideShow() {
    if (this.currentSelectTab === this.tabs[0].id) {
      return this.srcData.data.length === 0 && this.loading === false && this.searchNameIsEmpty;
    } else {
      return this.accessSrcData.data.length === 0 && this.accessLoading === false && this.searchNameIsEmpty;
    }
  }

  tabs: Array<any> = [
    { title: this.i18n.transform('knowledge_base'), id: 'kb', active: true },
    { title: this.i18n.transform('external_knowledge_base_connection'), id: 'kbConnection', active: false },
  ];
  public currentSelectTabIndex: number = 0;
  public currentSelectTab: string = this.tabs[0].id;

  public onTabIndexChange(index: number) {
    this.tabs.forEach((t, i) => (t.active = i === index));
    this.handleTabChange(this.tabs[index]);
  }

  public handleTabChange(tab) {
    if (tab.active) {
      this.isFirstLoading = true;
      this.currentSelectTab = tab.id;
      if (this.currentSelectTab === this.tabs[0].id) {
        this.getSourceList();
        this.queryCreateList();
      }
      if (this.currentSelectTab === this.tabs[1].id) {
        this.createThirdPartyRef.clearValue();
        this.queryAccessList();
      }
    }
  }
  is_develop_space = CommonUtils.judeg_develop_space();

  allTypeOptions: Array<any> = [
    { label: this.i18n.transform('all_types'), value: '' },
    { label: this.i18n.transform('default'), value: 'internal' },
    { label: this.i18n.transform('third_party'), value: 'external' },
  ];

  // CUSTOM 模式下的知识库类型下拉选项（全部/个人/企业）
  kbTypeOptionsForCustom: Array<any> = [
    { label: this.i18n.transform('all_types'), value: null },
    { label: '个人知识库', value: KnowledgeBaseType.PERSONAL },
    { label: '企业知识库', value: KnowledgeBaseType.ENTERPRISE },
  ];

  typeValue: any = this.allTypeOptions[0];
  // CUSTOM 模式下选中的知识库类型（默认"全部"）
  knowledgeBaseTypeValue: any = this.kbTypeOptionsForCustom[0];

  public get isCustomSource() {
    return this.configServ.knowledgeSource() === 'CUSTOM';
  }
  public emptyPlaceholder: string = this.i18n.transform('cardlistcomponent_55');

  public searchName: string = '';
  public searchSource;

  public appliedSearchName;
  public appliedSearchSource;
  public appliedSearchType;

  public appliedAccessSearchName;
  public appliedAccessSearchType;

  public searchItems: SearchboxItem[] = [
    { label: this.i18n.transform('name'), field: 'name' },
    { label: this.i18n.transform('source'), field: 'knowledge_base_connection_id', valueKey: 'id', options: [] },
  ];

  public listPageSize = {
    options: [10, 20, 50, 100],
    size: this.knowledgeBaseService.listSize,
  };
  public cardPageSize = {
    options: [12, 24, 36, 48],
    size: this.knowledgeBaseService.cardSize,
  };

  srcData = { data: [], state: undefined };

  imageCol = { title: this.i18n.transform('icon'), width: '60px' };
  kbNameCol = { title: this.i18n.transform('knowledge_name') };
  typeCol = { title: this.i18n.transform('type') };
  descCol = { title: this.i18n.transform('description') };
  statusCol = { title: this.i18n.transform('status') };
  updaterCol = { title: this.i18n.transform('update_user_name') };
  updateTimeCol = { title: this.i18n.transform('updated_on') };
  opCol = { title: this.i18n.transform('operation'), fixed: 'right', width: '180px' };

  listColumns: Array<any> = [
    this.imageCol,
    this.kbNameCol,
    this.typeCol,
    { title: this.i18n.transform('source') },
    { title: this.i18n.transform('share_scope'), id: 'scope' },
    { title: this.i18n.transform('knowledge_repo_id'), width: '300px' },
    this.descCol,
    this.statusCol,
    this.updaterCol,
    this.updateTimeCol,
    this.opCol,
  ];
  public total = 0;
  public loading = false;
  // 知识库列表加载失败（如 CUSTOM 模式连不上 LakeSearch），本地展示，不弹全局 toast
  public loadError = false;

  public accessPlaceholder: string = this.i18n.transform('cardlistcomponent_55');

  public accessSearchName: string = '';
  public accessSearchType;
  public accessSearchItems: SearchboxItem[] = [
    { label: this.i18n.transform('name'), field: 'name' },
    { label: this.i18n.transform('type'), field: 'connector_id', valueKey: 'id', options: [] },
  ];

  public accessListPageSize = {
    options: [10, 20, 50, 100],
    size: this.knowledgeBaseService.accessListSize,
  };
  public accessCardPageSize = {
    options: [12, 24, 36, 48],
    size: this.knowledgeBaseService.accessCardSize,
  };

  accessSrcData = { data: [], state: undefined };
  accessListColumns: Array<any> = [this.imageCol, this.kbNameCol, this.typeCol, this.descCol, this.statusCol, this.updaterCol, this.updateTimeCol, this.opCol];
  public accessTotal = 0;
  public accessLoading = false;
  previousUrl;
  public isFromAgentBuilder: boolean = false;
  normalizeKbs: KbItem[] = [];

  cardDisplayConfig: KbCardDisplayConfig = {
    cardSize: 'middle',
    descriptionConfig: { enable: true, maxLine: 2 },
    tagsConfig: { enable: [KbTagType.INVALID, KbTagType.TYPE, KbTagType.STATUS, KbTagType.SOURCE] },
    footerConfig: { userShow: true, timeShow: true, kbOperation: true },
    detailLink: { enable: true },
  };
  private readonly kbOperationFilterService = inject(KbOperationFilterService);

  protected readonly knowledgeBaseStatusMap = knowledgeBaseStatusMap;
  protected readonly knowledgeBaseSourceMap = knowledgeBaseSourceMap;
  protected readonly changeUrl = cdnAssetUrl;
  protected readonly formatTime = formatTime;
  protected readonly KB_SHARE_SCOPE_NAME_MAP = KB_SHARE_SCOPE_NAME_MAP;

  constructor(
    public i18n: I18NextEagerPipe,
    private nzDrawer: NzDrawerService,
    private nzMessage: NzMessageService,
    private nzModal: NzModalService,
    private kbRepo: KnowledgeRepoService,
    public knowledgeBaseService: KnowledgeBaseListService,
    public router: Router,
    public configServ: AgentConfigService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private route: ActivatedRoute,
    public kbAbilitiesService: KbAbilitiesService,
    private agentRepoService: AppAgentRepoService
  ) {}

  get createBtnStr() {
    return this.isKBConnection ? this.i18n.transform('connect_external_knowledge_base') : this.i18n.transform('create_kb');
  }

  get noDataTip() {
    return this.isKBConnection
      ? this.i18n.transform('no_data_available_connect_knowledge_base')
      : this.i18n.transform('no_data_available_create_knowledge_base');
  }

  public onSearchNameChange(val: string): void {
    if (!val) {
      this.getKBInSearch();
    }
  }

  public onAccessSearchNameChange(val: string): void {
    if (!val) {
      this.getKBAccessInSearch();
    }
  }

  get searchNameIsEmpty() {
    if (this.isKBConnection) {
      return !this.appliedAccessSearchName && !this.appliedAccessSearchType;
    } else {
      return !this.appliedSearchName && !this.appliedSearchSource && !this.appliedSearchType;
    }
  }

  public get isList() {
    return this.isKBConnection ? this.knowledgeBaseService.isAccessShowList : this.knowledgeBaseService.isShowList;
  }

  private get isKBConnection() {
    return this.tabs.find(tab => tab.active)?.id === 'kbConnection';
  }

  public getBadgeStatus(iconType: string): string {
    const statusMap: any = {
      'success': 'success',
      'error': 'error',
      'warn': 'warning',
      'info': 'processing',
      'default': 'default',
    };
    return statusMap[iconType] || 'default';
  }

  public noDataSearch() {
    this.searchName = '';
    this.searchSource = '';
    this.typeValue = this.allTypeOptions[0];
    this.knowledgeBaseTypeValue = this.kbTypeOptionsForCustom[0];

    this.accessSearchName = '';
    this.accessSearchType = '';

    if (this.isKBConnection) {
      this.getKBAccessInSearch();
    } else {
      this.getKBInSearch();
    }
  }

  public async noDataCreate() {
    if (this.isKBConnection) {
      const isExceed = await this.isResourceExceed();
      if (isExceed) {
        return;
      }
      this.kbSourceConnection.showModal();
    } else {
      this.newAddKnowledge();
    }
  }

  ngOnInit(): void {
    this.listColumns = this.listColumns.filter(item => {
      if (item.id === 'scope') {
        return this.configServ.isSupportSharedKb();
      }
      return true;
    });
    this.route.queryParams.subscribe(params => {
      this.previousUrl = params.previousUrl ?? '';

      const newQueryParams = { ...params };
      let shouldNavigate = false;

      if (params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
        this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
      }

      if (this.previousUrl) {
        delete newQueryParams.previousUrl;
        shouldNavigate = true;
      }

      if (this.kbAbilitiesService.isDevelopSpace) {
        this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
      }

      if (shouldNavigate) {
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: newQueryParams,
          replaceUrl: true,
        });
      }

      this.getSourceList();
      this.queryCreateList();
    });
    document.addEventListener('copy', this.copyListen);
  }

  ngOnDestroy(): void {
    if (this.kbAbilitiesService.isDevelopSpace) {
      this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    }
    document.removeEventListener('copy', this.copyListen);
  }

  copyListen(e) {
    const sel = window.getSelection().toString();
    const cleaned = sel.replace(/[\s\u00A0]+$/g, '');
    e.clipboardData.setData('text/plain', cleaned);
    e.preventDefault();
  }

  getSourceList() {
    this.kbRepo.getThirdPartyKnowledgeBaseList({ offset: 0, limit: 1000 }).then(res => {
      this.searchItems[1].options = res.items.map(item => {
        return { label: item.name, id: item.id };
      });
    });
    this.kbRepo.getThirdPartyKnowledgeBaseConnectors().then(result => {
      this.accessSearchItems[1].options = result.connectors.map(connector => {
        return { label: connector.name, id: connector.id };
      });
    });
  }

  ngAfterViewInit() {
    const relevantPaths = ['/home/agent-center/app-flow/flow', '/home/agent-center/app-agent/detail', '/home/develop-space'];
    if (this.previousUrl && relevantPaths.some(path => this.previousUrl.includes(path))) {
      this.newAddKnowledge();
    }
  }

  trackByFn(index: number, item: any): number {
    return item.id;
  }

  newAddKnowledge() {
    // CUSTOM 模式：知识库来源为外部 LakeSearch，创建走本地库+LakeSearch 不可用，禁用创建入口
    if (this.isCustomSource) {
      return;
    }
    if (this.configServ.createKnowledgeBase()) {
      this.selectCreateType.show();
    } else {
      this.createThirdPartyRef.clearValue();
      this.createThirdPartyRef.showDrawer();
    }
  }

  public getKBInSearch() {
    this.knowledgeBaseService.listCurrentPage = 1;
    this.knowledgeBaseService.cardCurrentPage = 1;
    this.queryCreateList();
  }

  public getKBAccessInSearch() {
    this.knowledgeBaseService.accessListCurrentPage = 1;
    this.knowledgeBaseService.accessCardCurrentPage = 1;
    this.queryAccessList();
  }

  public queryCreateList() {
    if (this.isList) {
      this.getList();
    } else {
      this.getCard();
    }
  }

  getList() {
    this.knowledgeBaseService.isShowList = true;
    this.getData();
  }

  getCard() {
    this.knowledgeBaseService.isShowList = false;
    this.getData();
  }

  public async getData(): Promise<void> {
    this.srcData.data = [];
    this.normalizeKbs = [];
    this.total = 0;
    try {
      this.loading = true;
      this.loadError = false;
      let currentPage = this.isList ? this.knowledgeBaseService.listCurrentPage : this.knowledgeBaseService.cardCurrentPage;
      let pageSize = this.isList ? this.knowledgeBaseService.listSize : this.knowledgeBaseService.cardSize;

      this.appliedSearchName = this.searchName;
      this.appliedSearchSource = this.searchSource;
      this.appliedSearchType = this.typeValue?.value || '';

      const searchParams: any = {};
      if (this.searchName) searchParams.name = this.searchName;
      if (this.searchSource) searchParams[this.searchItems[1].field] = this.searchSource;

      // CUSTOM 模式按 knowledge_base_type（个人/企业）筛选；否则按 type（默认/第三方）
      const customParams = this.isCustomSource
        ? { knowledge_base_type: this.knowledgeBaseTypeValue?.value ?? null }
        : { type: this.typeValue?.value || '' };

      const result = await this.kbRepo.getKnowledgeBaseList({
        ...searchParams,
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        ...customParams,
        // 列表页静默全局 error toast，避免加载失败污染其他页面；失败时本地兜底展示重试 UI
        cancelGlobalError: true,
      });
      const kbs = this.kbAbilitiesService.normalizeKBList(result.items ?? []);
      this.srcData.data = kbs;
      this.srcData.data = this.srcData.data.map(item => {
        item.menu = this.dataToItemsFn(item);
        return item;
      });
      this.normalizeKbs = kbs;
      this.total = result.total;
    } catch (e) {
      // 知识库列表加载失败（如 CUSTOM 模式连不上 LakeSearch）：上方调用已显式传 cancelGlobalError，
      // 不会弹全局 toast 污染其他页面，这里本地兜底，标记 loadError 在列表区展示失败提示
      this.loadError = true;
      this.srcData.data = [];
      this.normalizeKbs = [];
      this.total = 0;
    } finally {
      this.loading = false;
      this.isFirstLoading = false;
    }
  }

  dataToItemsFn: (data: any) => Array<ActionMenuItem> = (data: any) => {
    return this.kbOperationFilterService.getKbOperations(data);
  };

  public listAction($event, row) {
    if ($event.disabled) return;

    if ($event.key === 'delete') {
      this.createListDeleteWarn(row);
    } else if ($event.key === 'runOrStop') {
      if (row.status === 'OPEN') {
        this.createListStopWarn(row);
      } else if (row.status === 'CLOSE') {
        this.kbRepo.startKb(row.knowledge_base_id).then(() => {
          this.queryCreateList();
          this.nzMessage.success(this.i18n.transform('knowledge_open_success'));
        });
      }
    } else if ($event.key === 'edit') {
      this.knowledgeBaseEdit.openEditKnowledgeBase(row);
    } else if ($event.key === 'test') {
      this.router.navigate([`/home/knowledge-center/knowledge/${row.knowledge_base_id}/hit-testing`], {
        queryParams: { display_name: row.name, id: row.knowledge_base_id, isFromLibraryHome: true },
      });
    } else if ($event.key === 'advanced') {
      this.openAdvancedHalfModal('advanced', row);
    } else if ($event.key === 'kbReference') {
      const thisDrawer = this.nzDrawer.create({
        nzTitle: '',
        nzContent: ReferenceModalComponent,
        nzWidth: '900px',
        nzMaskClosable: true,
        nzData: { kbId: row.knowledge_base_id },
      });
    }
  }

  createListDeleteWarn(data): void {
    const isInternal = data.type === KnowledgeType.INTERNAL;
    this.nzModal.confirm({
      nzTitle: `${knowledgeBaseDeleteTitleMap.get(data.type)}`,
      nzContent: this.i18n.transform('confirm_action_tip', {
        action: knowledgeBaseDeleteTitleMap.get(data.type),
        name: data.name,
      }),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: isInternal ? this.i18n.transform('cancel') : '',
      nzOnOk: () => {
        return this.kbRepo.deleteKb(data.knowledge_base_id).then(() => {
          this.queryCreateList();
          this.nzMessage.success(this.i18n.transform('delete_success'));
        });
      },
    });
  }

  createListStopWarn(data): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('confirm_disable_knowledge_base'),
      nzContent: this.i18n.transform('disable_knowledge_base_usage_hint'),
      nzOkText: this.i18n.transform('disable'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        return this.kbRepo.stopKb(data.knowledge_base_id).then(() => {
          this.queryCreateList();
          this.nzMessage.success(this.i18n.transform('knowledge_close_success'));
        });
      },
    });
  }

  public goKnowledgeDetail(row) {
    if (row.type === 'external') {
      window.open(row.source.detail_page_url, '_blank');
    } else {
      this.router.navigate([`/home/knowledge-center/knowledge/${row.knowledge_base_id}`], { queryParams: { previousUrl: this.router.url } });
    }
  }

  public async openAdvancedHalfModal(type: string, data): Promise<void> {
    let detail = await this.kbRepo.retrieveKb(data.knowledge_base_id);
    const drawerRef = this.nzDrawer.create({
      nzContent: KnowledgeFormDrawerComponent,
      nzWidth: '700px',
      nzMaskClosable: true,
      nzData: { type, formData: detail },
    });
    drawerRef?.afterOpen?.subscribe(() => {
      const instance = drawerRef?.getContentComponent();
      instance?.submitForm?.subscribe(async (ctx: any) => {
        const { form, setConfirmLoading } = ctx;
        try {
          setConfirmLoading(true);
          await this.kbRepo.modifyKb(data.knowledge_base_id, form);
          this.nzMessage.success(this.i18n.transform('update_success'));
          drawerRef.close();
          this.queryCreateList();
        } finally {
          setConfirmLoading(false);
        }
      });
      instance?.cancelForm?.subscribe(() => drawerRef.close());
    });
  }

  createPageUpdate($event) {
    if (this.knowledgeBaseService.isShowList) {
      this.knowledgeBaseService.listCurrentPage = $event.currentPage;
      this.knowledgeBaseService.listSize = $event.size;
      this.listPageSize.size = $event.size;
    } else {
      this.knowledgeBaseService.cardCurrentPage = $event.currentPage;
      this.knowledgeBaseService.cardSize = $event.size;
      this.cardPageSize.size = $event.size;
    }
    this.queryCreateList();
  }

  public queryAccessList() {
    if (this.isList) {
      this.getAccessList();
    } else {
      this.getAccessCard();
    }
  }

  getAccessList() {
    this.knowledgeBaseService.isAccessShowList = true;
    this.getAccessData();
  }

  getAccessCard() {
    this.knowledgeBaseService.isAccessShowList = false;
    this.getAccessData();
  }

  public async getAccessData(): Promise<void> {
    this.accessSrcData.data = [];
    this.accessTotal = 0;
    try {
      this.accessLoading = true;
      let currentPage = this.knowledgeBaseService.isAccessShowList
        ? this.knowledgeBaseService.accessListCurrentPage
        : this.knowledgeBaseService.accessCardCurrentPage;
      let pageSize = this.knowledgeBaseService.isAccessShowList ? this.knowledgeBaseService.accessListSize : this.knowledgeBaseService.accessCardSize;

      this.appliedAccessSearchName = this.accessSearchName;
      this.appliedAccessSearchType = this.accessSearchType;

      const searchParams: any = {};
      if (this.accessSearchName) searchParams.name = this.accessSearchName;
      if (this.accessSearchType) searchParams[this.accessSearchItems[1].field] = this.accessSearchType;

      const result = await this.kbRepo.getThirdPartyKnowledgeBaseList({
        ...searchParams,
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
      });
      this.accessSrcData.data = result.items || [];
      this.accessSrcData.data = this.accessSrcData.data.map(item => {
        item.menu = this.accessDtaToItemsFn(item);
        return item;
      });
      this.accessTotal = result.total;
    } finally {
      this.accessLoading = false;
      this.isFirstLoading = false;
    }
  }

  accessDtaToItemsFn: (data: any) => Array<ActionMenuItem> = (data: any) => {
    let items: Array<ActionMenuItem> = [
      { label: this.i18n.transform('edit'), key: 'edit', disabled: this.kbAbilitiesService.isResourceDisabled },
      {
        label: this.i18n.transform('delete'),
        key: 'delete',
        disabled: knowledgeBaseStatusMap.get(data.status).disabled || this.kbAbilitiesService.isResourceDisabled,
      },
    ];
    return items;
  };

  public accessListAction($event, row) {
    if ($event.disabled) return;

    if ($event.key === 'delete') {
      this.accessListDeleteWarn(row);
    } else if ($event.key === 'edit') {
      this.kbSourceConnection.showModal(row.id);
    }
  }

  accessListDeleteWarn(data): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('delete'),
      nzContent: this.i18n.transform('confirm_delete_item', { name: data.name }),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        return this.kbRepo.deleteThirdPartyKnowledgeBase(data.id).then(() => {
          this.nzMessage.success(this.i18n.transform('delete_success'));
          this.queryAccessList();
        });
      },
    });
  }

  editAccessKnowledgeBase(row) {
    this.kbSourceConnection.showModal(row.id);
  }

  deleteAccessKnowledgeBase(id) {
    this.kbRepo.deleteThirdPartyKnowledgeBase(id).then(() => {
      this.nzMessage.success(this.i18n.transform('delete_success'));
      this.queryAccessList();
    });
  }

  accessPageUpdate($event) {
    if (this.knowledgeBaseService.isAccessShowList) {
      this.knowledgeBaseService.accessListCurrentPage = $event.currentPage;
      this.knowledgeBaseService.accessListSize = $event.size;
      this.accessListPageSize.size = $event.size;
    } else {
      this.knowledgeBaseService.accessCardCurrentPage = $event.currentPage;
      this.knowledgeBaseService.accessCardSize = $event.size;
      this.accessCardPageSize.size = $event.size;
    }
    this.queryAccessList();
  }

  openAccessKnowledgeBase() {
    this.currentSelectTabIndex = 1;
    this.onTabIndexChange(1);
    this.kbSourceConnection.showModal();
  }

  openDefaultConfigModal(event) {
    this.defaultConfigModalRef.open(event);
  }

  public openHalfModel() {
    const drawerRef = this.nzDrawer.create({
      nzContent: KnowledgeFormDrawerComponent,
      nzWidth: '700px',
      nzMaskClosable: true,
    });

    // 等待抽屉打开/渲染完成后，再获取组件实例
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();

      // 加一个可选链判断，确保 instance 存在
      if (instance) {
        instance.submitForm.subscribe(async ({ form, setConfirmLoading }: any) => {
          try {
            setConfirmLoading(true);
            await this.kbRepo.createKb(form);
            drawerRef.close();
            this.queryCreateList();
          } finally {
            setConfirmLoading(false);
          }
        });

        instance.cancelForm.subscribe(() => drawerRef.close());
      }
    });
  }

  async connectExternal() {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }
    this.kbSourceConnection.showModal();
  }

  async isResourceExceed() {
    const res = await this.agentRepoService.getResourceQuantity('thirdPartyKnowledgeBaseConnection');
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount, type: 'external' };
        this.exceedModal.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }

  public isStatusError(row) {
    return !row.source?.knowledge_base_connection_id && row.type === 'external';
  }
}
