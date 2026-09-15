import { Clipboard } from "@angular/cdk/clipboard";
import { CommonModule } from "@angular/common";
import {
  ChangeDetectorRef,
  Component,
  Input,
  OnDestroy,
  OnInit,
  TemplateRef,
  ViewChild,
  ViewContainerRef
} from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { Subject, takeUntil } from "rxjs";
import * as uuid from "uuid";

import { NzModalService } from "ng-zorro-antd/modal";
import { NzMenuModule } from "ng-zorro-antd/menu";
import { I18nNamespace } from "@i18n";
import {
  AgentCenterHomeService,
  TabIndex
} from "@services/agent-center/agent-center-home.service";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { ImportModalComponent } from "@shared/components/import-modal/import-modal.component";
import { MODULES } from "@shared/modules";
import { agentCommonLogic } from "../app-agent/common-logic-agent";
import { ITmplCard } from "../interfaces/application.interface";
import { CommonService } from "@services/common.service";
import { AppCardComponent } from "../app-card/app-card.component";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { ExportModalComponent } from "@shared/components/export-modal/export-modal.component";
import { CommonUtils } from "src/utils/common.util";
import { ApplicationType } from "@enums/agent-center.enum";
import { IWorkflowUpdateData } from "@routes/agent-center/app-flow/app-flow.types";
import { AppFlowService } from "@routes/agent-center/app-flow/app-flow.service";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { NewCommonNoDataWithBtnComponent } from "@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { WindowResizeService } from "@shared/base/window-resize.service";
import { HttpService } from "@services/http.service";
import { SetSidebarVisibilityService } from "@shared/services/set-sidebar-visibility.service";
import { AppExceedModalComponent } from "@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component";
import { NoDataGuideComponentComponent } from "@shared/components/no-data-guide/no-data-guide.component";
import { PrevRouteService } from "@services/prev-route.service";
import { AppAgentHighCodeService } from "@services/agent-center/app-agent-high-code.service";
import { DifyImportModalComponent } from "../app-flow/components/dify-import-modal/dify-import-modal.component";
import { ExportResultModalComponent } from "@shared/components/export-modal/export-result-modal/export-result-modal.component";
import { MultiFieldSearchComponent } from '@shared/components/multi-field-search/multi-field-search.component';

enum mapKeys {
  FROM = "from",
}

@Component({
  selector: "meta-application-management",
  templateUrl: "./application-management.component.html",
  styleUrls: ["./application-management.component.less"],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    AppCardComponent,
    NewCommonNoDataWithBtnComponent,
    AppExceedModalComponent,
    NoDataGuideComponentComponent,
    NzMenuModule,
    MultiFieldSearchComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.GUIDE, I18nNamespace.TOOL]
    },
    NzModalService,
    agentCommonLogic
  ]
})
export class ApplicationManagementComponent implements OnInit, OnDestroy {
  @Input("appType") appType: string = "";

  @ViewChild("callModalTitle")
  readonly callModalTitle?: TemplateRef<HTMLDivElement>;

  @ViewChild("callModalContent")
  readonly callModalContent?: TemplateRef<HTMLDivElement>;

  @ViewChild("callModalFooter")
  readonly callModalFooter?: TemplateRef<HTMLDivElement>;

  @ViewChild("nodeModalTitle")
  readonly nodeModalTitle?: TemplateRef<HTMLDivElement>;

  @ViewChild("nodeModalContent")
  readonly nodeModalContent?: TemplateRef<HTMLDivElement>;

  @ViewChild("nodeModalFooter")
  readonly nodeModalFooter?: TemplateRef<HTMLDivElement>;

  @ViewChild("searchbox")
  readonly searchbox?: any;

  @ViewChild("appExceedModal")
  appExceedModal: AppExceedModalComponent;

  public currActivedTab = TabIndex.WORKFLOW;
  public TabIndex = TabIndex;
  public isLoading: boolean = false;
  public callUrl = "";
  public workInfo: IWorkflowUpdateData;

  public tabs = [
    {
      show: true,
      id: ApplicationType.SINGLE_AGENT,
      title: this.i18n.transform("single_agent"),
      hash: "#/home/agent-center/single",
      active: true,
      disabledImport: false,
      disabledExport: false
    },
    {
      show: true,
      id: ApplicationType.WORKFLOW,
      title: this.i18n.transform("workflow"),
      hash: "#/home/agent-center/workflow",
      active: false,
      disabledImport: false,
      disabledExport: false
    },
    {
      show: true,
      id: ApplicationType.MULTI_AGENT,
      title: this.i18n.transform("multiple_agent"),
      hash: "#/home/agent-center/multi",
      active: false,
      disabledImport: false,
      disabledExport: false,
      showType: false
    }
  ];

  get visibleTabs() {
    // 当嵌入到专家页面时（appType 有值），隐藏工作流 Tab
    if (this.appType) {
      return this.tabs.filter(t => t.show && t.id !== ApplicationType.WORKFLOW);
    }
    return this.tabs.filter(t => t.show);
  }

  get activeVisibleTabIndex() {
    const index = this.visibleTabs.findIndex(t => t.id === this.tabs[this.currActivedTab]?.id);
    return index >= 0 ? index : 0;
  }

  public handleVisibleTabChange(visibleIndex: number) {
    this.hasSearched = false;
    const tab = this.visibleTabs[visibleIndex];
    const logicalIndex = this.tabs.findIndex(t => t.id === tab?.id);
    if (logicalIndex >= 0) {
      this.handleTabChange(logicalIndex);
    }
  }

  public highOptions = [
    {
      label: this.i18n.transform("agent_all"),
      value: ""
    },
    {
      label: this.i18n.transform("agent_new"),
      value: "agent_new"
    }
  ];

  public highValue = this.highOptions[0];
  public importItems: Array<{ id: string; label: string; click: () => void }> = [
    {
      id: "importJiuwen",
      label: this.i18n.transform("import_jiuwen_dsl"),
      click: () => {
        this.importTool();
      }
    },
    {
      id: "importDify",
      label: this.i18n.transform("import_dify_dsl"),
      click: () => {
        this.nzModal.create({
          nzTitle: null,
          nzFooter: null,
          nzContent: DifyImportModalComponent,
          nzViewContainerRef: this.viewContainerRef,
          nzWidth: 700
        });
      }
    }
  ];

  public searchItems: { label: string; field: string; options?: { label: string; id: string }[] }[] = [];
  public searchTags: { field: string; value: string; id?: string; label: string }[] = [];
  public searchField: string = 'name';

  public get searchNameIsEmpty(): boolean {
    return this.searchTags.length === 0;
  }

  public currentCardPage = 1;

  public totalCardNumber = 0;

  public isLoadingCard = false;

  public cards: ITmplCard[] = [];

  public cardPageSize: any = {
    options: [12, 24, 48, 64],
    size: 12
  };

  public warnAlertText = "";

  /** 控制 alert 警告的显隐。dismissOnTimeout属性会把open置为false */
  public open = false;

  public warnOpen = false;

  private destroy$ = new Subject<void>();

  public openAPIUrl: string = "";

  private nodeModalRef: { destroy: () => void };

  public isShowGuide = true; // 控制新手引导折叠

  public isNewExport = true; // 是否走新导出逻辑, 默认走新的

  public hasSearched = false; // 是否进行过搜索操作

  get getHeightClass() {
    if (this.open) {
      return this.warnOpen ? "h-[calc(100%-200px)]" : "h-[calc(100%-150px)]";
    } else {
      return "h-[calc(100%-130px)]";
    }
  }

  private isRecursiveCall = false;

  get createBtnText() {
    let text = "";
    if (this.currActivedTab === TabIndex.SINGLE_AGENT) {
      text = this.i18n.transform("homecomponent_1215");
    }

    if (this.currActivedTab === TabIndex.WORKFLOW) {
      text = this.i18n.transform("addchildflowmodalcomponent_243");
    }

    if (this.currActivedTab === TabIndex.MULTI_AGENT) {
      text = this.i18n.transform("homecomponent_1217");
    }

    if (this.currActivedTab === TabIndex.HIGH) {
      text = this.i18n.transform("homecomponent_1230");
    }

    return text;
  }

  public get noDataStr() {
    return this.getNoDataStr();
  }

  public get isShowNoDataGuide() {
    return !this.cards.length && !this.isLoadingCard && !this.isLoading && this.searchNameIsEmpty && !this.hasSearched;
  }

  private getNoDataStr() {
    return this.i18n.transform("create_app");
  }

  get tipType() {
    return (
      this.i18n.transform("componentlibrarycomponent_1175") +
      this.tabs[this.currActivedTab].title
    );
  }

  get tutorialType() {
    return this.getTutorialType();
  }

  private getTutorialType() {
    if (this.currActivedTab === TabIndex.SINGLE_AGENT) {
      return "singleQuestion";
    }
    if (this.currActivedTab === TabIndex.WORKFLOW) {
      return "workflow";
    }
    if (this.currActivedTab === TabIndex.HIGH) {
      return "high";
    }
    return "multiQuestion";
  }

  private get appTypes() {
    return [
      ApplicationType.SINGLE_AGENT,
      ApplicationType.WORKFLOW,
      ApplicationType.MULTI_AGENT,
      ApplicationType.AGENT_NEW
    ];
  }

  pathTip: string = "";
  is_HC = false;
  public HWCloudTopHeight: number = 0;
  isSite = this.commonService.isSite();
  subscribeBtnStatus = true;
  _agent_export_import_enable = this.is_HC ? false : true;
  _cross_space_replication_enable = this.is_HC ? false : true;
  is_develop_space = CommonUtils.judeg_develop_space();

  constructor(
    private clipboard: Clipboard,
    private i18n: I18NextEagerPipe,
    private service: AppAgentRepoService,
    private flowServ: AppFlowRepoService,
    private nzModal: NzModalService,
    private viewContainerRef: ViewContainerRef,
    private router: Router,
    private ppServ: AgentCenterHomeService,
    private commonService: CommonService,
    private commonLogic: agentCommonLogic,
    private appFlowServe: AppFlowService,
    private configServ: AgentConfigService,
    private windowResizeService: WindowResizeService,
    private readonly http: HttpService,
    private route: ActivatedRoute,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private appAgentRepoServ: AppAgentRepoService,
    private prev: PrevRouteService,
    protected cdr: ChangeDetectorRef,
    private highCodeService: AppAgentHighCodeService
  ) {
    this.route.queryParams.subscribe((params) => {
      let curSpaceId = params.curSpaceId;
      if (curSpaceId && location.hash.includes("home/agent-center/workflow")) {
        let spaceOptions = JSON.parse(StorageService.getSessionStorage("SPACE_OPTIONS"));
        let curSpace = spaceOptions.find((item) => {
          return item.id === curSpaceId;
        });
        StorageService.setSessionStorage(
          "CUR_SPACE_OPTIONS",
          JSON.stringify(curSpace)
        );
        location.hash = "#/home/agent-center/workflow";
        location.reload();
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
          inner_plugins_msg,
          auth_plugins_msg,
          auth_mcps_msg,
          isShow
        } = result;
        if (isShow === "success") {
          if (succeed_len >= 0 && failed_len === 0) {
            MessageComponent.showSuccess(
              this.i18n.transform("imported_succeeded_count_content", {
                succeed_len,
                failed_len
              }),
              3000
            );
          } else if (failed_len > 0) {
            MessageComponent.showError(
              this.i18n.transform("imported_failed_count_content", {
                succeed_len,
                failed_len
              }),
              3000
            );
          }
          this.open = true;

          if (
            inner_plugins_msg?.length ||
            auth_plugins_msg?.length ||
            auth_mcps_msg?.length
          ) {
            let innerMsg = "";
            let authMsgPlugin = "";
            let authMsgMcp = "";
            if (inner_plugins_msg?.length > 0) {
              const names = inner_plugins_msg
                .map((plugin) => plugin.name)
                .filter((name) => name)
                .join("、");
              innerMsg = this.i18n.transform("lack_plugin_msg", {
                lackCount: inner_plugins_msg.length,
                names
              });
            }

            if (auth_plugins_msg?.length > 0) {
              const needModNames = auth_plugins_msg
                .map((msg) => msg?.name)
                .filter((name) => name)
                .join("、");
              authMsgPlugin = this.i18n.transform(
                "key_value_need_reconfigured",
                {
                  type: this.i18n.transform("plugin"),
                  names: needModNames
                }
              );
            }

            if (auth_mcps_msg?.length > 0) {
              const needModNames = auth_mcps_msg
                .map((msg) => msg?.name)
                .filter((name) => name)
                .join("、");
              authMsgMcp = this.i18n.transform("key_value_need_reconfigured", {
                type: this.i18n.transform("mcp"),
                names: needModNames
              });
            }

            const alterMsgs = [innerMsg, authMsgPlugin, authMsgMcp]
              .filter((item) => item)
              .map((item, index, arr) =>
                arr.length === 1 ? item : `(${index + 1}) ${item}`
              );
            this.warnAlertText = alterMsgs.join("；");
            this.warnOpen = true;
          } else {
            this.warnOpen = false;
          }
          this.getCardData();
        } else {
          this.open = false;
          this.warnOpen = false;
        }
      });
  }

  showBetaTip = false;
  isBetaLoading = true;

  ngOnInit() {
    let curHashFlag = this.prev.previousUrl !== this.prev.currentUrl;
    let previousUrl = this.prev.previousUrl;
    const isFromAgentCenterTab = curHashFlag && (previousUrl.includes("agent-center/single") || previousUrl.includes("agent-center/workflow") || previousUrl.includes("agent-center/multi") || previousUrl.includes("agent-center/high"));
    if (isFromAgentCenterTab) {
      StorageService.delSessionStorage("JIUWEN_SEARCH_PARAMS");
    }

    if (this.appType) {
      // 嵌入到专家页面时，不隐藏侧边栏
      this.sidebarVisibilityServ.setSidebarsVisibilityByState(null);
    } else {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState(null);
    }
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();

    if (this.windowResizeService.getSafeAreaEnv()) {
      this.windowResizeService?.getSafeAreaEnv().onChange((e: any) => {
        this.HWCloudTopHeight = e.detail.top;
      });
    }
    let index = this.getIndexOfTab();
    this.tabs[index].active = true;
    // 从详情页返回时恢复搜索条件，从其它 agent-center tab 切换时则重置
    if (!this.appType && !isFromAgentCenterTab && curHashFlag) {
      this.restoreSearchState(index);
    } else {
      this.handleTabChange(index);
    }
    this.getLicenseRueryFn().then();
  }

  /** 保存当前搜索条件到 sessionStorage，在离开列表页时调用 */
  private saveSearchParamsToStorage(): void {
    StorageService.setSessionStorage("JIUWEN_SEARCH_PARAMS", {
      searchTags: this.searchTags,
      searchField: this.searchField,
      currentCardPage: this.currentCardPage,
      hasSearched: this.hasSearched
    });
  }

  /** 从 sessionStorage 恢复搜索条件（从详情页返回时调用） */
  private restoreSearchState(index: number): void {
    const savedParams = StorageService.getSessionStorage("JIUWEN_SEARCH_PARAMS");
    if (!savedParams) {
      this.handleTabChange(index);
      return;
    }
    try {
      const params = JSON.parse(savedParams);
      this.tabs.forEach((itm, idx) => {
        itm.active = idx === index;
      });
      this.open = false;
      this.warnOpen = false;
      this.currActivedTab = index;
      this.totalCardNumber = 0;
      this.initSearchItems(index);
      this.searchTags = params.searchTags || [];
      this.searchField = params.searchField || "name";
      this.currentCardPage = params.currentCardPage || 1;
      this.hasSearched = params.hasSearched || false;
      this.getCardData();
    } catch {
      this.handleTabChange(index);
    }
  }

  getIndexOfTab() {
    let index = 0;
    if (this.appType) {
      // 当嵌入到专家页面时，根据 appType 设置正确的 Tab
      if (this.appType === 'controller') {
        index = 1; // MULTI_AGENT（隐藏工作流后，多智能体是第 2 个）
      } else {
        index = 0; // SINGLE_AGENT
      }
    } else {
      const tempIndex = this.router.url.indexOf('workflow') > -1 ? 1 : 2;
      index = this.router.url.indexOf('single') > -1 ? 0 : tempIndex;
    }
    return index;
  }

  ngOnDestroy(): void {
    if (!this.appType) {
      this.saveSearchParamsToStorage();
      this.sidebarVisibilityServ.setSidebarsVisibilityByState("destroy");
    }
    this.destroy$.next();
    this.destroy$.complete();
    this.ppServ.setImportRes();
  }

  public onImportMenuClick(item: any): void {
    item?.click?.();
  }

  async getLicenseRueryFn() {
    if (this.is_HC) {
      const resData: any = await this.service.getLicenseRuery();
      const obj_import_export = resData.find(
        (item) => item.attr_code === "agent_export_import_enable"
      );
      const obj_cross_space_replication_enable = resData.find(
        (item) => item.attr_code === "cross_space_replication_enable"
      );
      this._agent_export_import_enable =
        obj_import_export.current_value === "true";
      this._cross_space_replication_enable =
        obj_cross_space_replication_enable.current_value === "true";
    }
    StorageService.setSessionStorage(
      "agent_export_import_enable",
      this._agent_export_import_enable
    );
    StorageService.setSessionStorage(
      "cross_space_replication_enable",
      this._cross_space_replication_enable
    );
  }

  handleClickClearSearch(): void {
    this.searchTags = [];
    this.searchField = 'name';
    this.onUserSearch();
  }

  public onSearchContentChange(): void {
    this.currentCardPage = 1;
    this.getCardData();
  }

  public onUserSearch(): void {
    this.hasSearched = true;
    this.onSearchContentChange();
  }

  private async getAppList(params, offset, limit) {
    const { agent_list, count } = await this.service.getAgentList(
      {
        ...params,
        type:
          this.currActivedTab === TabIndex.SINGLE_AGENT
            ? ApplicationType.SINGLE_AGENT
            : ApplicationType.MULTI_AGENT
      },
      offset,
      limit
    );
    return {
      list: agent_list || [],
      count
    };
  }

  private async getHighList(params, offset, limit) {
    const { code_agent_list, count } = await this.highCodeService.getHighAgentList(
      params,
      offset,
      limit
    );
    return {
      list: code_agent_list || [],
      count
    };
  }

  private async getWorflowList(params, offset, limit) {
    const { workflow_list, count } = await this.flowServ.getFlows({
      offset,
      limit,
      ...params
    });
    return {
      list: workflow_list || [],
      count
    };
  }

  public async getCardData() {
    try {
      if (!this.isRecursiveCall) {
        this.isLoadingCard = true;
      }

      const params: any = {};
      this.searchTags.forEach(tag => {
        if (tag.field === 'workflow_type' || tag.field === 'status') {
          params[tag.field] = tag.id || tag.value;
        } else {
          params[tag.field] = tag.value;
        }
      });
      if (this.currActivedTab === TabIndex.HIGH && this.highValue.value) {
        params.type = this.highValue.value;
      }
      const keys = Object.keys(params);
      let isError = false;
      for (let index = 0; index < keys.length; index++) {
        if (params[keys[index]]?.length > 64) {
          MessageComponent.showError(
            this.i18n.transform("homecomponent_1219"),
            3000
          );
          isError = true;
          break;
        }
      }
      if (isError) {
        return;
      }
      const { size } = this.cardPageSize;
      const offset = (this.currentCardPage - 1) * size;
      const api = this.getApi();
      this.isLoading = true;
      const { list, count } = await api.call(this, params, offset, size);
      if (list.length === 0 && offset !== 0) {
        const totalPage = Math.ceil(count / size);
        this.currentCardPage = Math.min(this.currentCardPage, totalPage);
        this.isRecursiveCall = true;
        this.getCardData();
        return;
      }
      this.isLoading = false;
      this.isRecursiveCall = false;
      this.totalCardNumber = count;
      this.cards = list;
    } finally {
      // 只有完成递归调用后，才将isLoadingCard设置为false，避免因递归调用出现中间的加载状态
      if (!this.isRecursiveCall) {
        this.isLoadingCard = false;
      }
      this.commonService.FurionReportCustomTime();
    }
  }

  private getApi() {
    if (this.currActivedTab === TabIndex.HIGH) {
      return this.getHighList;
    }
    return this.currActivedTab === TabIndex.WORKFLOW
      ? this.getWorflowList
      : this.getAppList;
  }

  public copyUrl() {
    this.clipboard.copy(this.callUrl);
    MessageComponent.showSuccess(this.i18n.transform("copy_successful"));
  }

  public async toCreate() {
    if (this.subscribeBtnStatus) {
      const isExceed = await this.isResourceExceed();
      if (isExceed) {
        return;
      }
    }

    const types = [
      ApplicationType.SINGLE_AGENT,
      ApplicationType.CHAT_WORKFLOW,
      ApplicationType.MULTI_AGENT,
      ApplicationType.AGENT_NEW
    ];
    const queryParams = {
      type: types[this.currActivedTab]
    };
    if (this.appType) {
      queryParams[mapKeys.FROM] = "develop-space";
    }
    const routeQueryParams = this?.route.snapshot.queryParams;
    let _queryParams: Record<string, string> = {};
    if (routeQueryParams.from === "agentBuilder") {
      Object.keys(routeQueryParams).forEach((key: string) => {
        if (key === "from" || key === "work_space_id") {
          _queryParams[key] = routeQueryParams[key];
        }
      });
    }
    this.router.navigate(["/home/agent-center/create"], {
      queryParams: {
        ...queryParams,
        ...routeQueryParams
      }
    });
  }

  async isResourceExceed() {
    const resourceType = ["agent", "workflow", "controller", "agent_new"];
    const res = await this.service.getResourceQuantity(
      resourceType[this.currActivedTab]
    );
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount };
        this.appExceedModal.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }

  /** 导入工作流或插件 */
  public async importTool() {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    const modalRef = this.nzModal.create({
      nzContent: ImportModalComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzWidth: 700,
      nzData: {
        importToolType: this.appTypes[this.currActivedTab],
        importTypeOptions: []
      }
    });

    const instance = modalRef.getContentComponent();
    instance.importSuccess.subscribe(() => {
      this.getCardData();
    });
  }

  /** 导出工作流或插件 */
  public exportTool() {
    const modalRef = this.nzModal.create({
      nzTitle: null,
      nzFooter: null,
      nzContent: ExportModalComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzWidth: 700,
      nzData: {
        exportType: this.appTypes[this.currActivedTab],
        exportTypeOptions: this.getExportTypeOptions()
      },
    });

    const instance = modalRef.getContentComponent();
    instance.confirm.subscribe(({ type, rows }) => {
      if (this.isNewExport) {
        this.newExportFn(type, rows, modalRef);
      } else {
        this.oldExportFn(type, rows, modalRef);
      }
    });
  }

  public newExportFn(type, rows, modalRef: { destroy: () => void }) {
    const idMap = {
      agent: "agent_id",
      workflow: "workflow_id",
      controller: "agent_id"
    };
    this.service.newExportAgents({
      resource_type: type,
      resource_versions: rows.map((row) => ({ resource_id: row[idMap[type]] }))
    }).then(res => {
      modalRef.destroy();
      this.nzModal.create({
        nzTitle: null,
        nzFooter: null,
        nzContent: ExportResultModalComponent,
        nzViewContainerRef: this.viewContainerRef,
        nzWidth: 700,
        nzData: {
          exportResult: res
        }
      });
    });
  }

  private oldExportFn(type, rows, modalRef: { destroy: () => void }) {
    modalRef.destroy();
    if (type === ApplicationType.WORKFLOW) {
      this.flowServ
        .exportWorkflows({
          workflow_ids: rows.map((row) => row.workflow_id)
        })
        .then((res) => {
          if (res !== undefined) {
            CommonUtils.downloadFile(
              new Blob([res], { type: "application/json" }),
              `workflow-${this.commonLogic.getFormattedDateTime()}.jsonl`,
              true
            );
          }
        });
      return;
    }
    this.service
      .exportAgents({
        agent_ids: rows.map((row) => row.agent_id)
      })
      .then((res) => {
        if (!res) {
          return;
        }
        CommonUtils.downloadFile(
          new Blob([res], { type: "application/json" }),
          `agent-${this.commonLogic.getFormattedDateTime()}.jsonl`,
          true
        );
      });
  }

  private getExportTypeOptions() {
    if (this.currActivedTab === TabIndex.MULTI_AGENT) {
      return [
        {
          id: ApplicationType.MULTI_AGENT,
          text: this.i18n.transform("export_multi_agent_app"),
          desc: "multi_agent_export_desc",
          colName: this.i18n.transform("multi_agent_app"),
          rowKey: "agent_id"
        }
      ];
    }
    if (
      this.currActivedTab === TabIndex.WORKFLOW
    ) {
      return [
        {
          id: ApplicationType.WORKFLOW,
          text: this.i18n.transform("export_workflow_app"),
          desc: "workflow_export_desc",
          colName: this.i18n.transform("workflow_app"),
          rowKey: "workflow_id"
        }
      ];
    }
    if (this.currActivedTab === TabIndex.SINGLE_AGENT) {
      return [
        {
          id: ApplicationType.SINGLE_AGENT,
          text: this.i18n.transform("export_single_agent_app"),
          desc: "app_export_desc",
          colName: this.i18n.transform("single_agent_app"),
          rowKey: "agent_id"
        }
      ];
    }
    return [];
  }

  public handleTabChange(index: number) {
    this.tabs.forEach((itm, idx) => {
      if (idx === index) {
        itm.active = true;
      } else {
        itm.active = false;
      }
    });
    this.open = false;
    this.warnOpen = false;
    this.currActivedTab = index;
    this.totalCardNumber = 0;
    this.searchTags = [];
    this.searchField = 'name';
    this.initSearchItems(index);
    this.onSearchContentChange();
  }

  private initSearchItems(index: number) {
    this.searchTags = [];
    if (index === TabIndex.WORKFLOW) {
      this.searchItems = [
        { label: this.i18n.transform('name'), field: 'name' },
        { label: this.i18n.transform('description'), field: 'description' },
        { label: this.i18n.transform('homecomponent_1222'), field: 'author' },
        {
          label: this.i18n.transform('type'), field: 'workflow_type',
          options: [
            { label: this.i18n.transform('chat'), id: 'chat' },
            { label: this.i18n.transform('task'), id: 'task' },
          ],
        },
        {
          label: this.i18n.transform('status'), field: 'status',
          options: [
            { label: this.i18n.transform('submitted'), id: 'published' },
            { label: this.i18n.transform('not_submitted'), id: 'draft' },
          ],
        },
      ];
    } else if (index === TabIndex.SINGLE_AGENT) {
      this.searchItems = [
        { label: this.i18n.transform('name'), field: 'name' },
        {
          label: this.i18n.transform('status'), field: 'status',
          options: [
            { label: this.i18n.transform('submitted'), id: 'published' },
            { label: this.i18n.transform('not_submitted'), id: 'draft' },
          ],
        },
        { label: this.i18n.transform('description'), field: 'description' },
        { label: this.i18n.transform('homecomponent_1222'), field: 'creator' },
      ];
    } else if (index === TabIndex.MULTI_AGENT) {
      this.searchItems = [
        { label: this.i18n.transform('name'), field: 'name' },
        {
          label: this.i18n.transform('status'), field: 'status',
          options: [
            { label: this.i18n.transform('submitted'), id: 'published' },
            { label: this.i18n.transform('not_submitted'), id: 'draft' },
          ],
        },
        { label: this.i18n.transform('description'), field: 'description' },
        { label: this.i18n.transform('homecomponent_1222'), field: 'creator' },
      ];
    } else {
      this.searchItems = [
        { label: this.i18n.transform('name'), field: 'name' },
      ];
    }
  }

  public setNode(context?: any) {
    this.flowServ.modifyFlow({
      update_time: this.workInfo.updated_on,
      workflow_id: this.workInfo.workflow_id,
      customize_node: !this.workInfo?.customize_node
    }).then((response) => {
      if (this.nodeModalRef) {
        this.nodeModalRef.destroy();
      }
      if (response) {
        this.getCardData();
        MessageComponent.showSuccess(
          this.i18n.transform(
            !!this.workInfo?.customize_node
              ? "remove_successful"
              : "setting_successful"
          )
        );
      }
    });
  }

  public closeNodeModal(): void {
    if (this.nodeModalRef) {
      this.nodeModalRef.destroy();
    }
  }

  public handleAction(data) {
    const { action, id, status } = data;
    if (action === "call") {
      const prefix =
        this.configServ.getConfigs()?.runtime_api_endpoint_prefix ?? "";
      const protocol = id.match(/^https?:\/\//)?.[0] ?? 'https://';
      let tempId = id.substring(
        id.indexOf("/v1/"),
        id.indexOf(":conversation_id")
      );
      const _id = `${protocol}${prefix}${tempId}`;
      const uuid = this.getUUID();
      this.pathTip = this.i18n.transform("homecomponent_1228", { uuid: uuid });

      if (this.currActivedTab === TabIndex.MULTI_AGENT) {
        this.callUrl =
          _id +
          `${uuid}${
            status === 1 || status === "published"
              ? "?version=latest&type=controller"
              : "?type=controller"
          }`;
      } else {
        this.callUrl =
          _id +
          `${uuid}${
            status === 1 || status === "published" ? "?version=latest" : ""
          }`;
      }

      this.nzModal.create({
        nzTitle: this.callModalTitle,
        nzContent: this.callModalContent,
        nzFooter: this.callModalFooter,
        nzMaskClosable: false,
        nzClosable: true
      });
      return;
    }
    if (action === "delete") {
      const currentPageCount = this.cards.length;
      if (currentPageCount === 1 && this.currentCardPage !== 1) {
        this.currentCardPage -= 1;
      }
    }

    if (action === "customizeNode") {
      this.workInfo = data.data;
      if (!this.workInfo.customize_node) {
        this.nodeModalRef = this.nzModal.create({
          nzTitle: this.nodeModalTitle,
          nzContent: this.nodeModalContent,
          nzFooter: this.nodeModalFooter,
          nzMaskClosable: false,
          nzClosable: true
        });
      } else {
        this.setNode();
      }

      return;
    }

    this.getCardData();
  }

  public getButton() {
    return [
      {
        label: this.i18n.transform("import"),
        click: () => this.importTool(),
        color: "default"
      },
      {
        label: this.i18n.transform("export"),
        click: () => this.exportTool(),
        color: "default"
      },
      {
        label: this.i18n.transform("creating_app"),
        color: "danger",
        click: () => this.toCreate()
      }
    ];
  }

  public clickOpenAPILink() {
    window.open(this.openAPIUrl, "_blank");
  }

  getUUID() {
    return uuid.v4();
  }

  public handleGuideClick(e) {
    if (e === "create") {
      this.toCreate();
    }
    if (e === "aiCreate") {
      this.aiCreateFn();
    }
  }

  public async aiCreateFn() {
    if (this.subscribeBtnStatus) {
      const isExceed = await this.isResourceExceed();
      if (isExceed) {
        return;
      }
    }
    const types = [
      ApplicationType.SINGLE_AGENT,
      ApplicationType.CHAT_WORKFLOW
    ];
    let appType = "agent";
    if (types[this.currActivedTab] === "agent") {
      appType = "agent";
    } else if (types[this.currActivedTab] === "chat") {
      appType = "workflow";
    }
    this.router.navigate(["/home/ai-assist-create-home"], {
      queryParams: {
        appType: appType
      }
    });
  }

  protected readonly changeUrl = cdnAssetUrl;
}
