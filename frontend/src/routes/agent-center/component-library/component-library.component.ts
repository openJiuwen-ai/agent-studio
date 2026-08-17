import { Clipboard } from '@angular/cdk/clipboard';
import { CommonModule } from '@angular/common';
import { Component, Input, OnDestroy, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from '@i18n';
import { AgentCenterHomeService, TabIndex } from '@services/agent-center/agent-center-home.service';
import { CommonNoDataWithBtnComponent } from '@shared/components/common-no-data-with-btn/common-no-data-with-btn.component';
import { ImportModalComponent } from '@shared/components/import-modal/import-modal.component';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject, takeUntil, Subscription } from 'rxjs';
import { agentCommonLogic } from '../app-agent/common-logic-agent';
import { ITmplCard } from '../interfaces/application.interface';
import { CommonService } from '@services/common.service';
import { ComponentCardComponent } from './component-card/component-card.component';
import { MCPService } from '@services/agent-center/mcp.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';

import { ActivatedRoute, Router } from '@angular/router';
import { CommonUtils } from 'src/utils/common.util';
import { ApplicationType } from '@enums/agent-center.enum';

import { IPlugin } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { AddMcpHalfModalComponent } from '@routes/agent-center/app-mcp-service/components/add-mcp-half-modal/add-mcp-half-modal.component';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { CreatePluginBaseComponent } from '@routes/agent-center/app-plugin/create-plugin-base/create-plugin-base';
import { WindowResizeService } from '@shared/base/window-resize.service';
import { ExportHalfModalComponent } from '@shared/components/export-half-modal/export-half-modal.component';
import { HttpService } from '@services/http.service';
import { AddMcpThirdPartyModal } from '@routes/agent-center/app-mcp-service/components/add-mcp-third-party-modal/add-mcp-third-party-modal';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';
import { DebounceDecorators } from '@shared/decorators/debouncing-throttling.directive';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
enum mapKeys {
  TYPE = 'type',
  VISIBILITY = 'visibility',
  LANGUAGE = 'language',
  WORK_SPACE_ID = 'work_space_id',
  entry_point = 'entry_point',
}

@Component({
  selector: 'meta-component-library',
  templateUrl: './component-library.component.html',
  styleUrls: ['./component-library.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    CommonNoDataWithBtnComponent,
    ComponentCardComponent,
    NewCommonNoDataWithBtnComponent,
    NoDataGuideComponentComponent,
    MultiFieldSearchComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.GUIDE],
    },
    NzModalService,
    agentCommonLogic,
  ],
})
export class ComponentLibraryComponent implements OnInit, OnDestroy {
  @Input() isFromDevelopSpace = false;
  @Input() appType: string = '';

  @ViewChild('callModal')
  readonly callModal?: TemplateRef<HTMLDivElement>;

  @ViewChild('nodeModal')
  readonly nodeModal?: TemplateRef<HTMLDivElement>;

  @ViewChild('searchbox')
  readonly searchbox?: any;

  public openAPIUrl: string = '';

  public createItems = [
    {
      id: TabIndex.MCP_SERVICE,
      label: this.i18n.transform('create_mcp_service'),
    },
    {
      id: TabIndex.PLUGIN,
      label: this.i18n.transform('create_plugin'),
    },
  ];

  public callUrl = '';
  public pluginInfo: IPlugin;
  public searchItems: any[] = [
    {
      label: this.i18n.transform('service_name'),
      field: 'name',
      options: [],
    },
  ];
  public currActivedTab = TabIndex.MCP_SERVICE;
  public tabs: any[] = [
    {
      show: true,
      id: 'mcp',
      title: this.i18n.transform('mcp'),
      active: false,
    },
    {
      show: true,
      id: 'plugin',
      title: this.i18n.transform('plugin'),
      active: false,
    },
  ];

  public searchName = '';
  public searchTags: ISearchTag[] = [];
  public searchField: string = 'name';
  public currentCardPage = 1;
  public isLoadingCard = false;
  public cards: ITmplCard[] = [];
  public lang: string;

  public cardPageSize: any = {
    options: [12, 24, 48, 64],
    size: 12,
  };
  public alertType: 'error' | 'success' | 'warn' | 'prompt' | 'simple' = 'success';
  public alertText = '';
  public totalCardNumber = 0;

  // 改变每页条数时，ng-zorro 会同步夹页并触发一次 nzPageIndexChange，与本次重查重复，用此 flag 屏蔽
  private _sizeChangeSuppressClamp = false;

  public open = false;
  public warnOpen = false;
  public warnAlertText = '';

  private destroy$ = new Subject<void>();
  private isRecursiveCall = false;
  public isLoading: boolean = false;
  public isShowGuide = true;

  public get noDataBtn() {
    if (this.subscribeBtnStatus) {
      return this.currActivedTab === TabIndex.MCP_SERVICE ? 'create_mcp' : 'create_plugin';
    }
    return '';
  }

  public get tipType() {
    return this.currActivedTab === TabIndex.MCP_SERVICE ? 'mcp' : 'plugin';
  }

  public get isShowNoDataGuide() {
    return !this.cards.length && !this.isLoadingCard && !this.isLoading && !this.isFromDevelopSpace && this.searchNameIsEmpty;
  }

  public isFirstLoading = true; // 是否为初次加载
  public isFromAgentBuilder = false;
  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  private resizeSub: Subscription;
  // 兼容agentBuilder
  workSpaceId: string = '';
  public HWCloudTopHeight: number = 0;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  is_develop_space = CommonUtils.judeg_develop_space();
  is_site = this.commonService.isSite();
  showBetaTip = false;

  create_items: Array<any> = this.is_site ? this.getSiteCreateItem() : this.getNonSiteCreateItem();

  size: any = 'large';
  constructor(
    private clipboard: Clipboard,
    private i18n: I18NextEagerPipe,
    private mcpService: MCPService,
    private appPluginRepoServ: AppPluginRepoService,
    private ppServ: AgentCenterHomeService,
    private commonService: CommonService,
    private route: ActivatedRoute,
    private commonLogic: agentCommonLogic,
    private router: Router,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private windowResizeService: WindowResizeService,
    private readonly http: HttpService,
    private nzModal: NzModalService,
    private nzDrawerService: NzDrawerService
  ) {
    this.lang = CommonUtils.getLanguage();
    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
      if (params[mapKeys.WORK_SPACE_ID]) {
        this.workSpaceId = params[mapKeys.WORK_SPACE_ID];
      }
    });
    /** 订阅导入工作流或插件的结果，展示在父组件的header上方 */
    this.ppServ
      .importResUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((result: any) => {
        const {
          succeed_len,
          failed_len,
          imported_len,
          updated_len,
          skipped_len,
          inner_plugins_msg,
          isShow,
          importType,
          auth_plugins_msg,
          auth_mcps_msg,
        } = result;
        if (isShow === 'success') {
          const hasDetailedCounts = importType === 'plugin' && [imported_len, updated_len, skipped_len]
            .some((count) => typeof count === 'number');
          if (hasDetailedCounts) {
            this.alertType = failed_len > 0 ? 'error' : 'success';
            this.alertText = this.getPluginImportResultMsg(
              imported_len ?? 0,
              updated_len ?? 0,
              skipped_len ?? 0,
              failed_len ?? 0,
            );
          } else if (succeed_len > 0 && failed_len === 0) {
            this.alertType = 'success';
            this.alertText = this.getSuccessMsg(succeed_len, failed_len);
          } else if (failed_len > 0) {
            this.alertType = 'error';
            this.alertText = this.getFailedMsg(succeed_len, failed_len);
          }

          this.open = true;

          if (inner_plugins_msg?.length || auth_plugins_msg?.length || auth_mcps_msg?.length) {
            const alterMsgs = this.buildMsg(inner_plugins_msg, auth_plugins_msg, auth_mcps_msg)
              .filter(item => item)
              .map((item, index, arr) => (arr.length === 1 ? item : `(${index + 1}) ${item}`));
            this.warnOpen = true;
            this.warnAlertText = alterMsgs.join('；');
          } else {
            this.warnOpen = false;
          }

          this.getCardData();
        } else {
          this.warnOpen = false;
          this.open = false;
        }
      });
  }

  ngOnInit() {
    // 来自agentBuilder页面屏蔽菜单
    if (this.isFromAgentBuilder || this.isFromDevelopSpace) {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    }
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();
    if (this.windowResizeService.getSafeAreaEnv()) {
      this.windowResizeService.getSafeAreaEnv().onChange((e: any) => {
        this.HWCloudTopHeight = e.detail.top;
      });
    }

    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe(width => {
      this.windowWidth = width;
    });

    let index = this.router.url.indexOf('plugin') > -1 ? 1 : 0;
    if (this.appType === 'Plugin') {
      index = 1;
    } else if (this.appType === 'MCP') {
      index = 0;
    }
    this.tabs[index].active = true;
    this.currActivedTab = index;
    this.searchName = '';
    this.getCardData();
    this.handleTabChange(index);
  }

  ngOnDestroy(): void {
    if (this.isFromAgentBuilder) {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
    }
    this.resizeSub?.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
    this.ppServ.setImportRes();
  }

  private getSiteCreateItem() {
    return [
      {
        id: 'blank-creation',
        label: this.i18n.transform('blank-creation'),
      },
      {
        id: 'official-creation',
        label: this.i18n.transform('official-creation'),
      },
    ];
  }

  private getNonSiteCreateItem() {
    return [
      {
        id: 'blank-creation',
        label: this.i18n.transform('blank-creation'),
      },
      {
        id: 'official-creation',
        label: this.i18n.transform('official-creation'),
      },
      {
        id: 'third-party-creation',
        label: this.i18n.transform('third-party-creation'),
      },
    ];
  }

  create_items_action(item) {
    if (['blank-creation', 'official-creation'].includes(item.id)) {
      const thisNzModal: any = this.nzModal.create({
        nzContent: AddMcpHalfModalComponent,
        nzWidth: '1000px',
      });
      const instance = thisNzModal.getContentComponent();
      instance.type = 'service';
      instance.teamplateType = item.id;
      instance.title = item.label;
      instance.mcpModalSelectedData.subscribe(() => {
        this.getCardData();
      });
    }
    if (item.id === 'third-party-creation') {
      const thisNzModal: any = this.nzModal.create({
        nzContent: AddMcpThirdPartyModal,
        nzWidth: '1000px',
      });
      const instance = thisNzModal.getContentComponent();
      instance.type = 'service';
      instance.teamplateType = item.id;
      instance.title = item.label;
      instance.close.subscribe(() => {
        this.getCardData();
      });
    }
  }

  get searchNameIsEmpty(): boolean {
    return this.searchTags.length === 0;
  }

  @DebounceDecorators()
  handleClickClearSearch(): void {
    this.searchTags = [];
    this.onSearchContentChange();
  }

  public onSearchContentChange(): void {
    this.currentCardPage = 1;
    this.getCardData();
  }

  private async getMcpList(params, offset, limit) {
    params[mapKeys.TYPE] = 'custom';
    params[mapKeys.entry_point] = 'partial';
    const { mcps, total } = await this.mcpService.getServiceList(params, {
      offset,
      limit,
    });
    return {
      list: mcps || [],
      total_count: total || 0,
    };
  }

  private async getPluginList(params, offset, limit) {
    params[mapKeys.entry_point] = 'partial';
    const { plugin_list, count } = await this.appPluginRepoServ.getPluginList({
      offset,
      limit,
      ...params,
    });
    return {
      list: plugin_list || [],
      total_count: count,
    };
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  public async getCardData() {
    try {
      if (!this.isRecursiveCall) {
        this.isLoadingCard = true;
      }
      let isDisableSearch = false;
      const params: any = { entry_point: 'partial' };

      if (this.appType === 'MCP') {
        params.type = 'custom';
      }
      const { size } = this.cardPageSize;

      this.searchTags.forEach(tag => {
        params[tag.field] = tag.value;
      });
      if (isDisableSearch) {
        MessageComponent.showWarn(this.i18n.transform('componentlibrarycomponent_1176'), 3000);
        return;
      }
      const offset = (this.currentCardPage - 1) * size;
      this.isLoading = true;
      setTimeout(async () => {
        const api = this.currActivedTab === TabIndex.MCP_SERVICE ? this.getMcpList : this.getPluginList;
        const { list, total_count } = await api.call(this, params, offset, size);
        if (list.length === 0 && offset !== 0) {
          const totalPage = Math.ceil(total_count / size);
          this.currentCardPage = Math.min(this.currentCardPage, totalPage);
          this.isRecursiveCall = true;
          this.getCardData();
          return;
        }
        this.isRecursiveCall = false;
        this.totalCardNumber = total_count;
        this.cards = list;
        this.isLoading = false;
        this.isFirstLoading = false;
      });
    } finally {
      // 只有完成递归调用后，才将isLoadingCard设置为false，避免因递归调用出现中间的加载状态
      if (!this.isRecursiveCall) {
        this.isLoadingCard = false;
      }
      this.commonService.FurionReportCustomTime();
    }
  }

  public onCardPageIndexChange(page: number): void {
    this.currentCardPage = page;
    // ng-zorro 改变每页条数时会同步夹页并触发 nzPageIndexChange，该次与改 size 的请求重复，跳过
    if (this._sizeChangeSuppressClamp) {
      return;
    }
    this.getCardData();
  }

  public onCardPageSizeChange(size: number): void {
    this.cardPageSize.size = size;
    // 改每页条数应回到第 1 页，避免用旧页码 × 新 size 算出越界 offset（如第2页 offset=(2-1)*24=24）
    this.currentCardPage = 1;
    this._sizeChangeSuppressClamp = true;
    // flag 仅在当前同步周期有效：夹页的 nzPageIndexChange 会同步紧随其后触发并被屏蔽；
    // 若页码本就有效未触发夹页，则由下一微任务清除，避免误屏蔽后续真实翻页
    Promise.resolve().then(() => {
      this._sizeChangeSuppressClamp = false;
    });
    this.getCardData();
  }

  public copyUrl() {
    this.clipboard.copy(this.callUrl);
    MessageComponent.showSuccess(this.i18n.transform('copy_successful'));
  }

  public handleCreate(_val: any) {
    const { id, data } = _val;
    if (id === TabIndex.MCP_SERVICE) {
      const thisNzModal: any = this.nzModal.create({
        nzContent: AddMcpHalfModalComponent,
        nzWidth: '1000px',
      });
      const instance = thisNzModal.getContentComponent();
      instance.type = 'service';
      instance.close.subscribe(() => {
        this.getCardData();
      });
    }
    if (id === TabIndex.PLUGIN) {
      const thisNzModal: any = this.nzModal.create({
        nzContent: CreatePluginBaseComponent,
        nzWidth: '1000px',
      });
      const instance = thisNzModal.getContentComponent();
      instance.pluginInfo = data;
      instance.pluginId = data?.tool_id;
      instance.confirm.subscribe(() => {
        if (!data?.tool_id) {
          this.searchTags = [];
          this.currentCardPage = 1;
        }
        this.getCardData().then();
      });
      return;
    }
  }

  /** 导入工作流或插件 */
  public importTool() {
    const thisNzModal: any = this.nzModal.create({
      nzContent: ImportModalComponent,
      nzWidth: '700px',
      nzData: {
        importToolType: ApplicationType.PLUGIN,
        importTypeOptions: [],
      },
    });
    const instance = thisNzModal.getContentComponent();
    instance.importToolType = ApplicationType.PLUGIN;
    instance.importTypeOptions = [];
  }

  /** 导出工作流或插件 */
  public exportTool() {
    const drawerRef = this.nzDrawerService.create({
      nzContent: ExportHalfModalComponent,
      nzWidth: this.halfModalWidth,
      nzData: {
        exportType: ApplicationType.PLUGIN,
        exportTypeOptions: [
          {
            id: ApplicationType.PLUGIN,
            text: this.i18n.transform('plugin_export'),
            desc: '',
            colName: this.i18n.transform('plugin'),
            rowKey: 'plugin_id',
          },
        ],
        confirm: ({ rows }) => {
          this.appPluginRepoServ
            .exportPlugins({
              tool_ids: rows.map(row => row.plugin_id),
            })
            .then(res => {
              if (!res) {
                return;
              }
              CommonUtils.downloadFile(new Blob([res], { type: 'application/json' }), `plugin-${this.commonLogic.getFormattedDateTime()}.jsonl`, true);
            });
        },
      },
    });
  }

  public handleTabChange(index: number) {
    const { id, active } = this.tabs[index];
    if (!active) {
      return;
    }
    this.searchTags = [];
    this.searchItems = id === 'mcp' ? this.getMcpSearchItems() : this.getPluginSearchItems();
    this.searchField = this.searchItems[0]?.field || '';
    this.open = false;
    this.warnOpen = false;
    this.currActivedTab = index;
    this.onSearchContentChange();
  }

  private getMcpSearchItems() {
    return [
      {
        label: this.i18n.transform('service_name'),
        field: 'name',
        options: [],
      },
    ];
  }

  private getPluginSearchItems() {
    return [
      {
        label: this.i18n.transform('name'),
        field: 'tool_chinese_name',
        options: [],
      },
      {
        label: this.i18n.transform('plugin_description'),
        field: 'tool_desc',
        options: [],
      },
    ];
  }

  public handleAction(val) {
    const { action, data } = val;
    if (action === 'update') {
      this.handleCreate({
        id: TabIndex.PLUGIN,
        data,
      });
      return;
    }
    if (action === 'delete') {
      const currentPageCount = this.cards.length;
      if (currentPageCount === 1 && this.currentCardPage !== 1) {
        this.currentCardPage -= 1;
      }
    }

    if (action === 'customizeNode') {
      this.pluginInfo = val.data;
      if (!this.pluginInfo.customize_node) {
        const thisNzModal: any = this.nzModal.create({
          nzContent: this.nodeModal,
          nzWidth: '500px',
          nzClosable: true,
          nzTitle: this.i18n.transform('set_node'),
        });
      } else {
        this.setNode();
      }
      return;
    }
    this.getCardData();
  }

  private buildMsg(inner, auth_plugins, auth_mcps) {
    let innerMsg = '';
    let authPluginMsg = '';
    let authMcpMsg = '';
    if (inner?.length > 0) {
      innerMsg = this.i18n.transform('lack_plugin_msg', {
        lackCount: inner.length,
        names: inner
          .map(plugin => plugin.name)
          .filter(name => name)
          .join('、'),
      });
    }

    if (auth_plugins?.length > 0) {
      authPluginMsg = this.i18n.transform('key_value_need_reconfigured', {
        type: this.i18n.transform('plugin'),
        names: auth_plugins
          .map(msg => msg?.name)
          .filter(name => name)
          .join('、'),
      });
    }

    if (auth_mcps?.length > 0) {
      authMcpMsg = this.i18n.transform('key_value_need_reconfigured', {
        type: this.i18n.transform('mcp'),
        names: auth_mcps
          .map(msg => msg?.name)
          .filter(name => name)
          .join('、'),
      });
    }

    return [innerMsg, authPluginMsg, authMcpMsg];
  }

  private getSuccessMsg(succeed_len: number, failed_len: number) {
    return this.i18n.transform('imported_succeeded_count_content', {
      succeed_len,
      failed_len,
    });
  }

  private getPluginImportResultMsg(
    imported_len: number,
    updated_len: number,
    skipped_len: number,
    failed_len: number,
  ) {
    return this.i18n.transform('plugin_import_result_content', {
      imported_len,
      updated_len,
      skipped_len,
      failed_len,
    });
  }

  private getFailedMsg(succeed_len: number, failed_len: number) {
    return this.i18n.transform('imported_failed_count_content', {
      succeed_len,
      failed_len,
    });
  }

  public async setNode(event?: any) {
    const params = {
      data: {
        ...this.pluginInfo,
        icon: undefined,
        customize_node: !this.pluginInfo?.customize_node,
      },
      id: this.pluginInfo.tool_id,
    };
    let response = await this.appPluginRepoServ.updatePlugins(params);
    if (event) {
      event.close();
    }
    if (response) {
      this.getCardData();
      MessageComponent.showSuccess(this.i18n.transform(!!this.pluginInfo?.customize_node ? 'remove_successful' : 'setting_successful'));
    }
  }

  public clickOpenAPILink() {
    window.open(this.openAPIUrl, '_blank');
  }

  validateUserInput(userInput: string): boolean {
    const regex = /^[\u4e00-\u9fa5a-zA-Z0-9_ -]{1,64}$/;
    return regex.test(userInput);
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return '800px';
    } else {
      return '600px';
    }
  }
}
