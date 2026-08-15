/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
import { ChangeDetectorRef, Component, computed, ElementRef, Input, OnInit, QueryList, signal, ViewChildren } from '@angular/core';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzModalService } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { agentCommonLogic, AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { IPlugin, IPluginWithTools } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject } from 'rxjs';
import { handleCommonReqError } from 'src/utils/utils';
import { CommonUtils } from 'src/utils/common.util';
import { PluginCredentialStatus } from '@enums/agent-center.enum';
import { AddPluginAuthComponent } from '@routes/plugin-market/add-plugin/add-plugin-auth.component';
import { ActivatedRoute, Router } from '@angular/router';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { WindowResizeService } from '@shared/base/window-resize.service';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import {
  AppCenterTabs,
  AppShareTabs,
  MARKET_TYPE,
  SHARE_CARD_MENU_TYPE,
  SHARE_TYPE,
  ShareTypeOptions,
  ShareTypeTag,
} from '@routes/app-center/app-center-management/app-center-management.config';
import { EditShareModalComponent } from '@routes/app-center/components/edit-share-modal/edit-share-modal.component';
import { SHARE_PAGE } from '@routes/app-center/components/edit-share-modal/edit-share-modal.config';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { IMemoParamExt } from '@routes/agent-center/app-agent/components/preview-memos/preview-memos.component';
import { PipesModule } from 'src/pipes/pipes.module';
import { ShareService } from '@routes/app-center/components/edit-share-modal/share.service';
import { ShareDeleteModalComponent } from '@routes/app-center/components/share-delete-modal/share-delete-modal.component';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { CardService } from '@routes/agent-center/my-card/card.service';
import { PromptService } from '@services/prompt.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { getQuotaTag } from '../../agent-center/utils';

enum mapKeys {
  credential_status = 'credential_status',
  auth_required = 'auth_required',
  pageType = 'pageType',
  releaseVersion = 'releaseVersion',
  category = 'category',
}
const OTHER_HEIGHT = 252;
const MAX_HEIGHT = 1270;

@Component({
  selector: 'plugin-market',
  templateUrl: './plugin-market.component.html',
  styleUrls: ['./plugin-market.component.less'],
  standalone: true,
  imports: [COMMON_MODULES, MODULES, NewCommonNoDataWithBtnComponent, PipesModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.TOOL, I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class PluginMarketComponent implements OnInit {
  @Input() needRefresh = '';
  @Input() isShowDom: boolean = true;
  @Input() limit: number = -1;
  @Input() offset: number = -1;
  // 是否来自于首页
  @Input() isFromOverview: boolean = false;

  @ViewChildren('pluginDescTipHost') descTipHost!: QueryList<ElementRef>;

  private isHC = false;
  private toolFormatter = tool => {
    return {
      ...tool,
      quotaTag: getQuotaTag(tool, this.i18n, false),
    };
  };

  public marketTabs = JSON.parse(JSON.stringify(AppCenterTabs));
  public activeTabId = signal(MARKET_TYPE.OFFICIAL);
  appMarketTabIndex = 0;
  appOfficialTabIndex = 0;
  appShareTabIndex = 0;

  public searchName: string = '';
  public searchItems: any[] = [
    {
      label: this.i18n.transform('display_name'),
      field: 'tool_chinese_name',
      options: [],
    },
    {
      label: this.i18n.transform('name'),
      field: 'name',
      options: [],
    },
    {
      label: this.i18n.transform('plugin_description'),
      field: 'tool_desc',
      options: [],
    },
  ];
  public platformSearchName: string = '';

  // 这里已有国际化，无需用i18n
  public pluginLabels = [
    {
      zh: '无需鉴权',
      en: 'Needless Auth',
      style: {
        color: 'rgba(20, 118, 255, 1)',
        backgroundColor: 'rgba(222, 236, 255, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
      id: PluginCredentialStatus.NONE,
    },
    {
      zh: '已鉴权',
      en: 'Authenticated',
      style: {
        color: 'rgba(2, 153, 49, 1)',
        backgroundColor: 'rgba(213, 242, 220, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
      id: PluginCredentialStatus.AUTHENTICATED,
    },
    {
      zh: '需鉴权',
      en: 'Unauthenticated',
      style: {
        color: 'rgba(25, 25, 25, 1)',
        backgroundColor: 'rgba(230, 230, 230, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
      id: PluginCredentialStatus.UNAUTHENTICATED,
    },
  ];

  public textMap = {
    0: '',
    1: this.i18n.transform('tag_free'),
    2: this.i18n.transform('tag_not_free'),
  };
  public searchedItem: any[] = [];

  private destroy$ = new Subject<void>();

  public isLoading = true;

  public currentCardPage: number = 1;

  public totalCardNumber: number = 0;

  public cardPageSize: any = {
    options: [24, 48, 64],
    size: 24,
  };

  hasMore = true;

  public plugins = [];

  public lang: string = '';
  public HWCloudTopHeight = 0;

  get activeTabIsOfficial() {
    return this.activeTabId() === MARKET_TYPE.OFFICIAL;
  }

  public displayedData: Array<any> = [];

  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public AppShareTabs = JSON.parse(JSON.stringify(AppShareTabs));
  public activeShareTabId = signal(SHARE_TYPE.OTHER_SHARE);
  public keyword = '';
  shareMenus = [
    {
      label: this.i18n.transform('sharedetailbtn-1'),
      id: SHARE_CARD_MENU_TYPE.CANCEL_SHARE,
    },
  ];
  public controller = new AbortController();
  public controllerShare = new AbortController();
  public controllerMyShare = new AbortController();
  public isNotDefault = false;

  appPluginTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform('all'),
      name_en: 'All',
      id: 'all',
      active: true,
      description: '',
      library_type: '',
      created_on: 0,
      updated_on: 0,
    },
  ];
  selectedTagId = signal('');

  get otherShare() {
    return this.activeShareTabId() === SHARE_TYPE.OTHER_SHARE;
  }

  pageTitle = computed(() => {
    const suffix = this.isZH() ? '' : ' ';
    let title = '';
    if (this.activeTabId() === MARKET_TYPE.OFFICIAL) {
      if (this.selectedTagId() === '') {
        title = this.i18n.transform('all');
      } else {
        title = this.getSelectTabName(this.appPluginTabs, this.selectedTagId());
      }
    } else {
      title = this.getSelectTabName(this.AppShareTabs, this.activeShareTabId());
    }
    return `${title}${suffix}`;
  });

  get totalCount() {
    if (this.totalCardNumber === 0) {
      if ((this.activeTabIsOfficial && this.searchedItem.length === 0) || (!this.activeTabIsOfficial && !this.keyword)) {
        return '';
      }
    }
    return ` (${this.totalCardNumber})`;
  }
  constructor(
    private pluginMarketService: AppPluginRepoService,
    private i18n: I18NextEagerPipe,
    private commonLogic: agentCommonLogic,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private windowResizeService: WindowResizeService,
    private appPluginRepoServ: AppPluginRepoService,
    private halfModalserv: NzDrawerService,
    public commonService: CommonService,
    private shareService: ShareService,
    private cardService: CardService,
    private nzModalService: NzModalService,
    private promptService: PromptService,
    private sidebarServ: SetSidebarVisibilityService
  ) {
    this.isHC = false;
    this.lang = CommonUtils.getLanguage();
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();
  }

  ngOnInit() {
    this.sidebarServ.setSidebarsVisibilityByState('hideSidebar');
    const cur_space_option_str = StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
    if (cur_space_option_str !== '{}') {
      try {
        const cur_space_option_obj = JSON.parse(cur_space_option_str);
        this.isNotDefault = cur_space_option_obj.type !== 'PERSON';
      } catch {
        this.isNotDefault = false;
      }
    }
    if (this.windowResizeService.getSafeAreaEnv()) {
      this.windowResizeService?.getSafeAreaEnv().onChange((e: any) => {
        this.HWCloudTopHeight = e.detail.top;
      });
    }
    const isTABShare = history.state.formTab === 'share';
    const isMyShare = history.state.myShare === true;
    if (isTABShare) {
      this.marketTabs[0].active = false;
      this.marketTabs[1].active = true;
      this.appMarketTabIndex = 1;
      this.activeTabId.set(this.marketTabs[1].id);
    }
    if (isMyShare) {
      this.AppShareTabs[0].active = false;
      this.AppShareTabs[1].active = true;
      this.appShareTabIndex = 1;
      this.activeShareTabId.set(this.AppShareTabs[1].id);
    }
    if (isTABShare) {
      this.initShareList();
    } else {
      this.getPluginTagData();
      this.getCardData();
    }
  }

  private getPluginTagData() {
    const params = {
      library_type: 'plugin',
    };
    this.promptService
      .getAssertTagAsync(params)
      .then(response => {
        this.appPluginTabs = [...this.appPluginTabs, ...response].map(r => ({
          ...r,
          title: this.isZH() ? r.name : r.name_en,
        }));
      })
      .catch();
  }

  public getPluginLabels(data: string) {
    const filterData = this.pluginLabels.filter(item => item.id === data);
    if (filterData && filterData.length > 0) {
      return filterData[0];
    }
    return this.pluginLabels[0];
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  public getPluginName(plugin: IPluginWithTools) {
    if (this.isZH()) {
      return plugin.plugin_chinese_name || plugin.plugin_display_name;
    }
    return plugin.plugin_display_name || plugin.plugin_chinese_name || '--';
  }

  public isShowAuthConfigBtn(plugin: IPlugin) {
    return !!(
      plugin[mapKeys.credential_status] === PluginCredentialStatus.AUTHENTICATED ||
      plugin[mapKeys.credential_status] === PluginCredentialStatus.UNAUTHENTICATED ||
      plugin[mapKeys.auth_required]
    );
  }

  public authConfigName(plugin: IPlugin) {
    if (plugin[mapKeys.credential_status] === PluginCredentialStatus.AUTHENTICATED) {
      return this.i18n.transform('remove_auth');
    }
    return this.i18n.transform('configAuth');
  }

  // 获取平台精选的数据
  public async getCardData() {
    if (this.controllerShare) {
      this.controllerShare.abort();
    }
    if (this.controllerMyShare) {
      this.controllerMyShare.abort();
    }
    if (this.controller) {
      this.controller.abort();
    }
    if (window.innerHeight - OTHER_HEIGHT > MAX_HEIGHT) {
      this.cardPageSize.size = this.cardPageSize.options[1];
    } else {
      this.cardPageSize.size = this.cardPageSize.options[0];
    }
    this.controller = new AbortController();
    const tool_chinese_name = this.platformSearchName;
    const params = {
      offset: tool_chinese_name ? 0 : ((this.currentCardPage || 1) - 1) * this.cardPageSize.size,
      limit: this.cardPageSize.size,
      tool_chinese_name,
      type: 'inner',
      published: 1,
    };
    if (this.selectedTagId()) {
      params[mapKeys.category] = this.selectedTagId();
    }
    if (this.limit >= 0) {
      params.limit = this.limit;
    }
    if (this.offset >= 0) {
      params.offset = this.offset;
    }
    this.isLoading = true;

    try {
      const value = await this.pluginMarketService.getPluginList(params, this.controller.signal);
      const plugins = (value?.plugin_list ?? []).map(this.toolFormatter);
      plugins.forEach((item, index) => {
        item.shareTag = ShareTypeTag('');
      });
      if (value.count) {
        this.plugins.push(...plugins);
        this.currentCardPage++;
        this.hasMore = this.currentCardPage < Math.ceil(value.count / this.cardPageSize.size) + 1;
      } else {
        this.plugins = [];
        this.hasMore = false;
      }
      this.totalCardNumber = value.count;
    } catch (error: any) {
      handleCommonReqError(error);
    } finally {
      this.isLoading = false;
      this.cdr.detectChanges();
    }
  }

  // 搜索平台精选的数据
  public onSearch() {
    this.currentCardPage = 1;
    this.plugins.length = 0;
    this.totalCardNumber = this.plugins.length;
    this.getCardData().then();
  }

  ngOnDestroy(): void {
    this.sidebarServ.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }

  public handleDetailView(item) {
    if (!this.subscribeBtnStatus) {
      return;
    }
    const queryParams: any = {
      id: item.plugin_id,
    };
    if (this.isFromOverview) {
      queryParams.from = 'overview';
    }
    if (!this.activeTabIsOfficial) {
      queryParams[mapKeys.pageType] = 'share';
      queryParams[mapKeys.releaseVersion] = item.version_id;
    }
    this.router.navigate(['/home/plugin-market/market-detail'], {
      queryParams: queryParams,
    });
  }

  /**
   * 配置认证信息
   * **/
  public handleClickAddAuthConfig(item, e) {
    e.stopPropagation();
    const modalRef = this.nzModalService.create({
      nzTitle: this.i18n.transform('add_plugin_auth'),
      nzContent: AddPluginAuthComponent,
      nzFooter: null,
      nzWidth: 500,
    });
    modalRef.componentInstance.pluginInfo = item;
    modalRef.afterClose.subscribe(() => {
      this.onSearch();
    });
  }

  public copyToWorkbench(data, e) {
    e.stopPropagation();
    this.appPluginRepoServ
      .copyFunction(data.plugin_id)
      .then(res => {
        if (res.code === 200) {
          MessageComponent.showSuccess(this.i18n.transform('copy_plugin_success'));
        }
      })
      .catch(error => {});
  }

  protected readonly PluginCredentialStatus = PluginCredentialStatus;

  get searchNameIsEmpty() {
    return this.searchedItem.length === 0;
  }

  public handleClickClearData() {
    this.searchedItem = [];
    this.currentCardPage = 1;
    this.getCardData();
  }

  public tabChange(tab: any): void {
    if (tab.active) {
      this.activeTabId.set(tab.id);
      this.plugins = [];
      this.currentCardPage = 1;
      if (this.activeTabIsOfficial) {
        this.handleClickClearData();
      } else {
        this.initShareList();
      }
    }
  }

  onMarketTabChange(index: number): void {
    const tab = this.marketTabs[index];
    if (tab && !tab.active) {
      this.marketTabs.forEach((t, i) => (t.active = i === index));
      this.tabChange(tab);
    }
  }

  onOfficialTabChange(index: number): void {
    const tab = this.appPluginTabs[index];
    if (tab && !tab.active) {
      this.appPluginTabs.forEach((t, i) => (t.active = i === index));
      this.changeAppTab(tab);
    }
  }

  onShareTabChange(index: number) {
    const tab = this.AppShareTabs[index];
    if (tab && !tab.active) {
      this.AppShareTabs.forEach((t, i) => (t.active = i === index));
      this.shareTabChange(tab);
    }
  }

  public creatShare() {
    const drawerRef = this.halfModalserv.create({
      nzWidth: 700,
      nzTitle: this.i18n.transform('pluginmarket_1'),
      nzPlacement: 'right',
      nzClosable: true,
      nzMaskClosable: false,
      nzContent: EditShareModalComponent,
      nzContentParams: {
        sharePage: SHARE_PAGE.plugin,
        isEdit: false,
      },
    });
    drawerRef.afterClose.subscribe(() => {
      this.AppShareTabs[0].active = false;
      this.AppShareTabs[1].active = true;
      this.activeShareTabId.set(this.AppShareTabs[1].id);
      this.initShareList();
    });
  }

  public shareTabChange(tab: any): void {
    if (tab.active) {
      this.keyword = '';
      this.activeShareTabId.set(tab.id);
      this.currentCardPage = 1;
      this.initShareList();
    }
  }

  // 获取共享的数据
  getShareList() {
    if (this.controllerShare) {
      this.controllerShare.abort();
    }
    if (this?.controllerMyShare) {
      this.controllerMyShare.abort();
    }
    if (this.controller) {
      this.controller.abort();
    }
    this.controllerShare = new AbortController();
    this.controllerMyShare = new AbortController();
    if (window.innerHeight - OTHER_HEIGHT > MAX_HEIGHT) {
      this.cardPageSize.size = this.cardPageSize.options[1];
    } else {
      this.cardPageSize.size = this.cardPageSize.options[0];
    }
    if (this.limit >= 0) {
      this.currentCardPage = this.limit;
    }
    if (this.offset >= 0) {
      this.cardPageSize.size = this.offset;
    }
    const params = {
      resource_name: this.keyword,
      offset: ((this.currentCardPage || 1) - 1) * (this.cardPageSize.size as number),
      limit: this.cardPageSize.size as number,
      resource_type: 'plugin',
    };
    this.plugins.length = 0;
    this.totalCardNumber = 0;
    this.isLoading = true;
    const req = this.otherShare
      ? this.shareService.getShareList(params, this.controllerShare.signal)
      : this.shareService.getMyShareList(params, this.controllerMyShare.signal);
    req
      .then(
        res => {
          this.isLoading = false;
          this.totalCardNumber = res.count;
          const plugins = (res.resource_list || []).map(this.toolFormatter);
          plugins?.forEach(v => {
            v.icon = v.resource_icon;
            v.plugin_id = v.resource_id;
            v.plugin_desc = v.resource_desc;
            v.plugin_chinese_name = v.resource_name_ch;
            v.shareTag = ShareTypeTag('');
            if (!this?.otherShare) {
              this.shareMenus.forEach((menu: any) => {
                menu.disabled = !this.subscribeBtnStatus;
              });
              v.shareMenus = [this.shareMenus[0]];
            }
            v.version_id = v.version_info_list?.[0].version_id;
            v.version_name = v.version_info_list?.[0].version_name;
          });
          if (res.count) {
            this.currentCardPage++;
            this.hasMore = this.currentCardPage < Math.ceil(res.count / this.cardPageSize.size) + 1;
            this.plugins.push(...plugins);
          } else {
            this.plugins = [];
            this.hasMore = false;
          }
        },
        () => {
          this.isLoading = false;
        }
      )
      .finally(() => {});
  }

  // 搜索团队共享的数据
  public initShareList() {
    this.currentCardPage = 1;
    this.plugins.length = 0;
    this.totalCardNumber = this.plugins.length;
    this.getShareList();
  }

  public shareMenuOnClick(event: Event, menus: any, plugin): void {
    event.stopPropagation();
    if (menus[0].id === SHARE_CARD_MENU_TYPE.CANCEL_SHARE) {
      this.getReferList(plugin);
    }
  }

  public shareMenuSelect(event: any, plugin: any): void {
    if (event.id === SHARE_CARD_MENU_TYPE.CANCEL_SHARE) {
      // 取消共享应用
      this.getReferList(plugin);
    }
  }

  private getReferList(data) {
    const param = {
      offset: 0,
      limit: 100,
      reference_type: 'share',
      resource_type: 'tool',
    };
    this.cardService
      .selectQuoteList(data.resource_id, param)
      .then(res => {
        let count = res.count;
        if (count) {
          this.openShareDelModal(data);
        } else {
          this.delShareModal(data);
        }
      })
      .finally(() => {});
  }

  private openShareDelModal(data) {
    const modalRef = this.nzModalService.create({
      nzTitle: '',
      nzFooter: null,
      nzWidth: 700,
      nzClosable: false,
      nzMaskClosable: false,
      nzContent: ShareDeleteModalComponent,
    });
    modalRef.componentInstance.shareData = data;
    modalRef.componentInstance.pageType = SHARE_PAGE.plugin;
    modalRef.afterClose.subscribe((result) => {
      if (result) {
        this.initShareList();
      }
    });
  }

  private delShareModal(data) {
    this.nzModalService.confirm({
      nzTitle: this.i18n.transform('app_center_cards_3'),
      nzContent: this.i18n.transform('app_center_cards_2'),
      nzOkText: this.i18n.transform('ok'),
      nzOnOk: () => {
        this.delShare(data);
      },
    });
  }

  private delShare(data) {
    this.shareService
      .deleteShare(data.resource_id, {
        resource_type: data.resource_type,
      })
      .then(res => {
        this.initShareList();
      });
  }

  loadMore(): void {
    if (this.isLoading || !this.hasMore) {
      return;
    }

    this.isLoading = true;
    if (this.activeTabIsOfficial) {
      this.getCardData();
    } else {
      this.getShareList();
    }
  }

  onScroll(): void {
    const scrollableElement = document.querySelector('.card-container');
    if (scrollableElement) {
      const { scrollTop, scrollHeight, clientHeight } = scrollableElement;
      if (scrollHeight - (scrollTop + clientHeight) < 100) {
        this.loadMore();
      }
    }
  }

  changeAppTab(data: AssertSquareTagType) {
    if (data.active) {
      this.plugins = [];
      this.currentCardPage = 1;
      this.totalCardNumber = this.plugins.length;
      if (data.id === 'all') {
        this.selectedTagId.set('');
      } else {
        this.selectedTagId.set(data.id);
      }
      this.getCardData().then();
    }
  }

  getCategoryLabel(tagId: string): string {
    if (!tagId || this.appPluginTabs.length <= 0) {
      return '';
    }
    const filterData = this.appPluginTabs.filter(item => item.id === tagId);
    if (filterData && filterData.length > 0) {
      return this.isZH() ? filterData[0].name : filterData[0].name_en;
    }
    return '';
  }

  // 刷新平台精选数据
  handleClickRefreshOfficialBtn() {
    this.onSearch();
  }

  // 刷新团队共享数据
  handleClickRefreshTeamBtn() {
    this.initShareList();
  }

  getComCardBottomMenu(plugin: any) {
    return (this.isShowAuthConfigBtn(plugin) && this.subscribeBtnStatus) || (plugin?.call_mode === 'functiongraph' && this.subscribeBtnStatus);
  }

  getBottomAreaHaveMenuWithOfficial(plugin: any) {
    return (this.isShowAuthConfigBtn(plugin) && this.subscribeBtnStatus) || (plugin?.call_mode === 'functiongraph' && this.subscribeBtnStatus);
  }

  getBottomAreaHaveMenuWithNotOfficial(plugin: any) {
    return (
      plugin.shareMenus?.length ||
      (this.isShowAuthConfigBtn(plugin) && this.subscribeBtnStatus) ||
      (plugin?.call_mode === 'functiongraph' && this.subscribeBtnStatus)
    );
  }

  private getSelectTabName(list = [], id = '') {
    return list.find(t => t.id === id)?.title ?? list[0].title;
  }
}
