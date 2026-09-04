/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
import { ChangeDetectorRef, Component, computed, Input, OnDestroy, OnInit, signal, ViewChild } from '@angular/core';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from '@i18n';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { Subject } from 'rxjs';
import { cloneDeep } from 'lodash';
import { AppCenterCardsComponent } from '../components/app-center-cards/app-center-cards.component';
import { CommonUtils } from 'src/utils/common.util';
import { WindowResizeService } from '@shared/base/window-resize.service';
import { AppCenterTabs, AppShareTabs, MARKET_TYPE, OFFICIAL_TYPE, SHARE_TYPE } from './app-center-management.config';
import { EditShareModalComponent } from '../components/edit-share-modal/edit-share-modal.component';
import { SHARE_PAGE } from '../components/edit-share-modal/edit-share-modal.config';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { CommonService } from '@services/common.service';
import { ApplicationManagementComponent } from '@routes/agent-center/home/application-management.component';

export enum ExpertTopTab {
  DIGITAL_EMPLOYEE = 'DIGITAL_EMPLOYEE',
  DIGITAL_SQUAD = 'DIGITAL_SQUAD',
}

@Component({
  selector: 'app-center-management',
  templateUrl: './app-center-management.component.html',
  styleUrls: ['./app-center-management.component.scss'],
  standalone: true,
  imports: [
    COMMON_MODULES,
    MODULES,
    AppCenterCardsComponent,
    ApplicationManagementComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
})
export class AppCenterManagementComponent implements OnInit, OnDestroy {
  // 首页需要按需展示
  @Input() isShowDom: boolean = true;
  @Input() limit: number = -1;
  @Input() offset: number = -1;
  @Input() isFromOverview: boolean = false;
  @ViewChild('centerCards') centerCards: AppCenterCardsComponent;

  /** 专家页面顶层 Tab：数字员工 / 数字小队 */
  public expertTopTab = ExpertTopTab.DIGITAL_EMPLOYEE;
  public ExpertTopTab = ExpertTopTab;
  /** 记录数字员工/数字小队 Tab 是否已被激活过，用于保持组件存活 */
  public digitalEmployeeActivated = true;
  public digitalSquadActivated = false;

  private destroy$ = new Subject<void>();
  public searchName = '';
  public appCenterTabs = cloneDeep(AppCenterTabs);

  public activeTabId = signal(MARKET_TYPE.OFFICIAL);
  public appCenterTabIndex = 0;

  public title = this.i18n.transform('platform_selection_template');

  public AppShareTabs = cloneDeep(AppShareTabs);
  public activeShareTabId = signal(SHARE_TYPE.OTHER_SHARE);
  public shareTabIndex = 0;

  public appTabs: any = [];
  public appTabIndex = 0;
  public keyword = '';

  public typeOptions = [
    {
      label: this.i18n.transform('all'),
      value: 'all',
    },
    {
      label: this.i18n.transform('Agent'),
      value: OFFICIAL_TYPE.Agent,
    },
    {
      label: this.i18n.transform('workflow_market'),
      value: OFFICIAL_TYPE.workflow,
    },
  ];

  // 工作流智能体
  public typeSelect = 'all';
  public appTagId = signal('');
  public lang = CommonUtils.getLanguage();
  public HWCloudTopHeight = 0;
  public isFreshData: boolean = false;

  public selectType = [
    {
      label: this.i18n.transform('all'),
      id: 'all',
    },
    {
      label: this.i18n.transform('Agent'),
      id: 'agent',
    },
    {
      label: this.i18n.transform('workflow'),
      id: 'workflow',
    }
  ];

  public selectedType = this.selectType[0];

  public isNotDefault = false;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  pageTitle = computed(() => {
    if (this.activeTabId() === MARKET_TYPE.OFFICIAL) {
      if (this.appTagId() === '') {
        return this.i18n.transform('all');
      }
      return this.getSelectTabName(this.appTabs, this.appTagId());
    }
    return this.getSelectTabName(this.AppShareTabs, this.activeShareTabId());
  });

  activeTabIsOfficial = computed(() => {
    return this.activeTabId() === MARKET_TYPE.OFFICIAL;
  });

  get pageCount() {
    const count = this.centerCards?.totalCardNumber ?? 0;
    if (!this.keyword && count === 0) {
      return '';
    }
    return `(${count})`;
  }

  constructor(
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private service: AppLibraryRepoService,
    private cdr: ChangeDetectorRef,
    private nzDrawerService: NzDrawerService,
    private windowResizeService: WindowResizeService,
    private commonService: CommonService,
  ) {
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();
  }

  ngOnInit() {
    const cur_space_option_str =
      StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
    if (cur_space_option_str !== '{}') {
      try {
        const cur_space_option_obj = JSON.parse(cur_space_option_str);
        this.isNotDefault = cur_space_option_obj.type !== 'PERSON'
      } catch {
        this.isNotDefault = false;
      }
    }
    if (this.windowResizeService.getSafeAreaEnv()) {
      this.windowResizeService.getSafeAreaEnv().onChange((e: any) => {
        this.HWCloudTopHeight = e.detail.top;
      });
    }
    const isTABShare = history.state.formTab === 'share';
    const isMyShare = history.state.myShare === true;
    if (isTABShare) {
      this.appCenterTabs[0].active = false;
      this.appCenterTabs[1].active = true;
      this.activeTabId.set(this.appCenterTabs[1].id);
      this.appCenterTabIndex = 1;
    }
    if (isMyShare) {
      this.AppShareTabs[0].active = false;
      this.AppShareTabs[1].active = true;
      this.activeShareTabId.set(this.AppShareTabs[1].id);
      this.shareTabIndex = 1;
    }
    this.getTagsInfo();
  }

  ngAfterViewInit() {
    this.initSessionStorage();
  }

  private initSessionStorage() {
    if (!StorageService.getSessionStorage('application_square_type')) {
      StorageService.setSessionStorage('application_square_type', 'all');
    } else {
      const applicationSquareType = StorageService.getSessionStorage('application_square_type');
      const filterData = this.selectType.filter((item: any) => item.id === applicationSquareType);
      if (filterData && filterData.length > 0) {
        this.selectedType = filterData[0];
      }
    }
  }

  private getTagsInfo() {
    this.appTabs = [
      {
        name: this.i18n.transform('all'),
        name_en: 'All',
        id: '',
        tag_id: '',
        active: true,
      }
    ];
    this.service.getTagList().then(
      (res: any) => {
        this.appTabs = [
          ...this.appTabs,
          ...cloneDeep(res),
        ].map(r => ({
          ...r,
          title: this.lang === 'zh-cn' ? r.name : r.name_en,
          id: r.tag_id
        }));
        this.cdr.markForCheck();
        this.initList();
      },
      () => {
        MessageComponent.showError(this.i18n.transform('failed_tip'), 3000);
      },
    );
  }

  initList($event?: any) {
    const params = {
      typeSelect: this.typeSelect,
      appTagId: this.appTagId(),
      keyword: this.keyword,
      activeTabId: this.activeTabId(),
      activeShareTabId: this.activeShareTabId(),
    }
    this.centerCards?.cardInit(params);
  }

  /** 专家页面顶层 Tab 切换 */
  public onExpertTopTabChange(index: number): void {
    if (index === 0) {
      this.expertTopTab = ExpertTopTab.DIGITAL_EMPLOYEE;
      this.digitalEmployeeActivated = true;
    } else {
      this.expertTopTab = ExpertTopTab.DIGITAL_SQUAD;
      this.digitalSquadActivated = true;
    }
  }

  public tabChangeByIndex(index: number): void {
    this.appCenterTabs.forEach(item => item.active = false);
    const tab = this.appCenterTabs[index];
    tab.active = true;
    if (tab && tab.active) {
      this.activeTabId.set(tab.id);
      this.AppShareTabs = cloneDeep(AppShareTabs);
      if (this.activeTabId() === MARKET_TYPE.OFFICIAL) {
        this.typeOptions[1].value = OFFICIAL_TYPE.Agent;
      } else {
        this.typeOptions[1].value = OFFICIAL_TYPE.controller;
      }
      this.initList();
    }
  }

  public shareTabChangeByIndex(index: number): void {
    this.AppShareTabs.forEach(item => item.active = false);
    const tab = this.AppShareTabs[index];
    tab.active = true;
    if (tab && tab.active) {
      this.activeShareTabId.set(tab.id);
      this.typeSelect = 'all';
      this.title = tab.title;
      if (this.keyword) {
        this.keyword = '';
      }
      this.initList();
    }
  }

  public changeAppTabByIndex(index: number): void {
    this.appTabs.forEach(item => item.active = false);
    const item = this.appTabs[index];
    item.active = true;
    if (item && item.active) {
      this.appTagId.set(item.id);
      this.initList();
    }
  }

  public clearSearchData() {
    this.keyword = "";
    this.initList();
  }

  public creatShare() {
    if (!this.subscribeBtnStatus) {
      return;
    }
    const drawerRef = this.nzDrawerService.create({
      nzTitle: '',
      nzFooter: null,
      nzWidth: 700,
      nzClosable: true,
      nzMaskClosable: false,
      nzPlacement: 'right',
      nzContent: EditShareModalComponent,
      nzContentParams: {
        sharePage: SHARE_PAGE.apply,
        isEdit: false,
      },
    });
    drawerRef.afterClose.subscribe(() => {
      this.appCenterTabs[0].active = false;
      this.appCenterTabs[1].active = true;
      this.activeTabId.set(MARKET_TYPE.SHARE);
      this.appCenterTabIndex = 1;
      this.AppShareTabs[0].active = false;
      this.AppShareTabs[1].active = true;
      this.activeShareTabId.set(this.AppShareTabs[1].id);
      this.shareTabIndex = 1;
      this.initList();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private getSelectTabName(list = [], id = '') {
    return list.find(t => t.id === id)?.title ?? list[0].title;
  }
}
