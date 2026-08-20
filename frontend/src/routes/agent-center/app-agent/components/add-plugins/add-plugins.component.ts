import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  Output,
  QueryList,
  SimpleChanges,
  ViewChildren
} from "@angular/core";
import { MODULES } from "@shared/modules";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import {
  EPluginCategoryTabId,
  PAGINATION_LIMIT_NUM
} from "../../../types/my-workspace.types";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { Subject, takeUntil } from "rxjs";
import { agentCommonLogic, AssertSquareTagType } from "../../common-logic-agent";
import {
  IPluginWithTools,
  ITool
} from "@routes/agent-center/app-plugin/app-plugin.interface";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { CommonUtils } from "src/utils/common.util";
import { AppPluginRepoService } from "@services/agent-center/app-plugin-repo.service";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { WORKFLOW_SVGS } from "@routes/agent-center/app-flow/flow.const";
import { CreatePluginBaseComponent } from "@routes/agent-center/app-plugin/create-plugin-base/create-plugin-base";
import { PluginCredentialStatus } from "@enums/agent-center.enum";
import { NewCommonNoDataWithBtnComponent } from "@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component";
import { ShareService } from "@routes/app-center/components/edit-share-modal/share.service";
import { PromptService } from "@services/prompt.service";
import { SkillCardComponent } from "../add-mcp-servers/skill-card/skill-card.component";
import { AddPluginAuthComponent } from "@routes/plugin-market/add-plugin/add-plugin-auth.component";
import { CommonService } from "@services/common.service";
import { NzDrawerService } from "ng-zorro-antd/drawer";
import { NzModalService } from "ng-zorro-antd/modal";
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';
import { getQuotaTag } from "../../../utils";

enum mapKeys {
  category = "category",
}

@Component({
  selector: "auth-config",
  template: `<p>{{ 'click' | i18nextEager }}<a class="cursor-pointer" (click)="handleClickAddAuthConfig()">{{ 'configAuth' | i18nextEager }}</a></p>`,
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    }
  ]
})
export class AuthConfigComponent {
  @Input() data: any;
  @Output() readonly confirm: EventEmitter<boolean> = new EventEmitter();

  constructor(
    private nzModal: NzModalService
  ) {}

  public handleClickAddAuthConfig() {
    const modalRef = this.nzModal.create({
      nzTitle: null,
      nzFooter: null,
      nzContent: AddPluginAuthComponent,
      nzWidth: 700,
    });
    modalRef.componentInstance.pluginInfo = this.data;
    modalRef.afterClose.subscribe(() => {
      this.confirm.emit(true);
    });
  }
}

@Component({
  selector: "add-plugins",
  templateUrl: "./add-plugins.component.html",
  styleUrls: ["./add-plugins.component.scss"],
  standalone: true,
  imports: [MODULES, NewCommonNoDataWithBtnComponent, SkillCardComponent, MultiFieldSearchComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    }
  ]
})
export class AddPluginsComponent {
  @Input() plugins = [];

  @Output() pluginAdded = new EventEmitter<any[]>();

  @Output() pluginReduced = new EventEmitter<any[]>();

  @Input() usedFrom: string = "agent";

  @Input() agentNode = ""; // 用于工作流里agent节点里的新建插件

  @ViewChildren("presetTipHost") presetTipHosts!: QueryList<ElementRef>;

  @ViewChildren("personalTipHost") personalTipHost!: QueryList<ElementRef>;

  @ViewChildren("ShareTipHost") ShareTipHost!: QueryList<ElementRef>;
  public tabId = {
    market: "market",
    personal: "personal",
    share: "share"
  };

  private textMap = {
    0: "",
    1: this.i18n.transform("editcardmodal_83"),
    2: this.i18n.transform("editcardmodal_84")
  };
  protected readonly PluginCredentialStatus = PluginCredentialStatus;
  public pluginLabels = [
    {
      zh: this.i18n.transform("no_auth"),
      en: "Needless Auth",
      id: PluginCredentialStatus.NONE,
      style: {
        color: "rgba(2, 153, 49, 1)",
        backgroundColor: "rgba(213, 242, 220, 1)",
        display: "inline-block",
        padding: "4px",
        borderRadius: "4px",
        fontSize: "12px"
      }
    },
    {
      zh: this.i18n.transform("editcardmodal_85"),
      en: "Authenticated",
      id: PluginCredentialStatus.AUTHENTICATED,
      style: {
        color: "rgba(2, 153, 49, 1)",
        backgroundColor: "rgba(213, 242, 220, 1)",
        display: "inline-block",
        padding: "4px",
        borderRadius: "4px",
        fontSize: "12px"
      }
    },
    {
      zh: this.i18n.transform("editcardmodal_86"),
      en: "Unauthenticated",
      id: PluginCredentialStatus.UNAUTHENTICATED,
      style: {
        color: "rgba(25, 25, 25, 1)",
        backgroundColor: "rgba(230, 230, 230, 1)",
        display: "inline-block",
        padding: "4px",
        borderRadius: "4px",
        fontSize: "12px"
      }
    }
  ];
  public isShow = "";

  public pluginSelected: any = [];

  public tabs: any = [
    { title: this.i18n.transform("pre_installed_plugins"), active: false },
    { title: this.i18n.transform("component_plugin"), active: true },
    { title: this.i18n.transform("addpluginmodal_1"), active: false }
  ];

  getActivceIndex() {
    return this.tabs.findIndex(itm => itm.active);
  }

  // 预置插件Tab，对应的数据与分页
  public stateMarket: any = {
    pluginList: [],
    isLoading: false
  };

  public curPageMarket = 1;

  public totalNumberMarket = 0;

  public searchItemsMarket = [
    { label: this.i18n.transform('plugin_name'), field: 'tool_chinese_name' },
    { label: this.i18n.transform('plugin_en_name'), field: 'name' },
    { label: this.i18n.transform('plugin_description'), field: 'tool_desc' },
  ];
  public searchTagsMarket: ISearchTag[] = [];
  public searchFieldMarket: string = 'tool_chinese_name';

  public searchItemsPersonal = [
    { label: this.i18n.transform('plugin_name'), field: 'tool_chinese_name' },
    { label: this.i18n.transform('plugin_en_name'), field: 'name' },
    { label: this.i18n.transform('plugin_description'), field: 'tool_desc' },
  ];
  public searchTagsPersonal: ISearchTag[] = [];
  public searchFieldPersonal: string = 'tool_chinese_name';

  public searchItemsShare = [
    { label: this.i18n.transform('name'), field: 'resourceName' },
  ];
  public searchTagsShare: ISearchTag[] = [];
  public searchFieldShare: string = 'resourceName';

  public lang = CommonUtils.getLanguage();

  // 个人插件Tab，对应的数据与分页
  public statePersonal: any = {
    pluginList: [],
    isLoading: false
  };
  public curPagePersonal = 1;
  public totalNumberPersonal = 0;

  // 共享插件Tab，对应的数据与分页
  public stateShare: any = {
    pluginList: [],
    isLoading: false
  };
  public curPageShare = 1;
  public totalNumberShare = 0;
  public activeTabName = this.tabId.personal;
  public pluginTip = "";

  get searchNameIsEmpty(): boolean {
    return (
      (this.activeTabName === this.tabId.market &&
        this.searchTagsMarket.length === 0) ||
      (this.activeTabName === this.tabId.personal &&
        this.searchTagsPersonal.length === 0) ||
      (this.activeTabName === this.tabId.share &&
        this.searchTagsShare.length === 0)
    );
  }

  private destroy$ = new Subject<void>();
  private tabLastActive!: EPluginCategoryTabId;
  // 创建新插件之前，上一次被选中但没有点确定，没有保存到后端数据库中的plugins
  public pluginsLastClicked: any[] = [];
  // 添加插件后，还是新建插件后。默认是添加插件后
  private addOrCreate: boolean = true;

  appPluginTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform("all"),
      name_en: "all",
      id: "all",
      active: true,
      description: "",
      library_type: "",
      created_on: 0,
      updated_on: 0
    }
  ];
  selectedTagId: string = "";

  get site() {
    return this.configServ.getConfigs().site;
  }

  public updateShareTools = (pluginId, tools) => {
    return tools.map(item => ({
      id: item.tool_id,
      name: this.getToolName(item),
      description: item.tool_desc,
      selected: this.isSelectedTool(pluginId, item.tool_id),
      canAdd: true,
      tip: ""
    }));
  };

  constructor(
    private commonLogic: agentCommonLogic,
    private agentDataServe: AgentDataService,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private pluginRepoServe: AppPluginRepoService,
    private shareService: ShareService,
    private readonly commonService: CommonService,
    public promptService: PromptService,
    private drawerServ: NzDrawerService,
  ) {
    this.agentDataServe
      .pluginsAndTabIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((pluginsAndCurrentTab: any) => {
        this.tabLastActive = pluginsAndCurrentTab.currentTabId;
        this.pluginsLastClicked = pluginsAndCurrentTab.plugins;
      });

    this.agentDataServe
      .clickFlagPluginUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((clickFlag: string) => {
        this.clearSearchboxValue();
        if (clickFlag === "add") {
          // 添加插件后
          this.addOrCreate = true;
          this.initData(EPluginCategoryTabId.PERSONAL);
          /** 点击外部的添加插件按钮，以父组件的@Input属性为准*/
          this.pluginSelected = this.plugins.map((plugin: any) => {
            return {
              ...plugin,
              id: plugin.id || plugin.tool_id
            };
          });
          /**
           * 同步刷新service中的值。
           * 避免新建插件后，关闭抽屉，service记录了上一次的用户操作，但接口没保存，两处不一致
           */
          this.agentDataServe.setPluginsAndTabId(
            this.commonLogic.getCurrentTabId(
              this.tabs,
              EPluginCategoryTabId.PERSONAL,
              EPluginCategoryTabId.MARKET,
              EPluginCategoryTabId.SHARE
            ),
            this.pluginSelected
          );
          this.loadPluginMarket();
          this.loadPluginPersonal();
          this.loadPluginShare();
        }
        if (clickFlag === "create") {
          // 新建插件后
          this.addOrCreate = false;
          this.initData(this.tabLastActive);
          /** 点击内部的创建插件按钮，以service存储的值为准 */
          this.pluginSelected = this.pluginsLastClicked;
          this.loadPluginMarket();
          this.loadPluginPersonal();
          this.loadPluginShare();
        }
        this.cdr.markForCheck();
      });
  }

  ngOnInit() {
    this.pluginTip = `${this.i18n.transform("addplugincomponent_1")}${
      this.agentNode
        ? this.i18n.transform("addplugincomponent_2")
        : this.i18n.transform("addplugincomponent_3")
    }`;
    this.getPluginTagData();
  }

  ngOnChanges(changes: SimpleChanges) {
    /**
     * 增加addOrCreate变量进行判断。如果是添加插件，则由父组件传入；
     * 如果是创建完新插件后，则由service传入。
     */
    if (changes.plugins && this.addOrCreate) {
      // 创建副本，避免同步修改父组件中的pluginAdded.list
      this.pluginSelected = [...changes.plugins.currentValue];
      // 页面被强制刷新后，一定要用get接口传入的输入属性值更新service，给service赋初值
      this.agentDataServe.setPluginsAndTabId(
        this.commonLogic.getCurrentTabId(
          this.tabs,
          EPluginCategoryTabId.PERSONAL,
          EPluginCategoryTabId.MARKET,
          EPluginCategoryTabId.SHARE
        ),
        this.pluginSelected
      );
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** 获取tag的数据 **/
  private getPluginTagData() {
    const params = {
      library_type: "plugin"
    };
    this.promptService.getAssertTagAsync(params).then(
      (res) => {
        const firstTab = this.appPluginTabs[0];
        this.appPluginTabs.length = 0;
        this.appPluginTabs.push(firstTab);
        for (let index = 0; index < res.length; index++) {
          this.appPluginTabs.push(res[index]);
        }
      }
    ).catch();
  }

  get useUnpublishedPlugin(){
    return this.configServ.getConfigs().plugin_publish_choice;
  }

  get pluginLimit() {
    return this.configServ.getConfigs()?.agent_tool_bound_limit ?? 20;
  }

  /** 点击创建插件按钮，进入创建个人插件的抽屉 */
  public createPersonalPlugin() {
    // 使用service存储状态，用于创建完新插件后，回显上一次的Tab和已选中的插件
    this.agentDataServe.setPluginsAndTabId(
      this.commonLogic.getCurrentTabId(
        this.tabs,
        EPluginCategoryTabId.PERSONAL,
        EPluginCategoryTabId.MARKET,
        EPluginCategoryTabId.SHARE
      ),
      this.pluginSelected
    );
    this.drawerServ.create({
      nzTitle: null,
      nzFooter: null,
      nzContent: CreatePluginBaseComponent,
      nzWidth: 700,
      nzContentParams: {
        usedFrom: this.usedFrom,
        agentNode: this.agentNode
      }
    });
  }

  public isShowAuthConfigBtn(plugin) {
    return (
      plugin.auth_required && plugin?.credential_status === "UNAUTHENTICATED"
    );
  }

  public updatePluginAuthConfig(event, plugin) {
    if (event === "dismiss") {
      this.isShow = "";
      this.cdr.detectChanges();
      return;
    }
    plugin.credential_status = "AUTHENTICATED";
  }

  /** 根据名称 或 描述 或作者，搜索插件 */
  public getPluginListBySearch(type = this.tabId.market): void {
    if (type === this.tabId.market) {
      this.curPageMarket = 1;
      this.loadPluginMarket();
    } else if (type === this.tabId.personal) {
      this.curPagePersonal = 1;
      this.loadPluginPersonal();
    } else if (type === this.tabId.share) {
      this.curPagePersonal = 1;
      this.loadPluginShare();
    }
  }

  /** 当页码改变时，查询组件 */
  public getPluginListByPage(type = this.tabId.market) {
    if (type === this.tabId.market) {
      this.loadPluginMarket();
    } else if (type === this.tabId.personal) {
      this.loadPluginPersonal();
    } else if (type === this.tabId.share) {
      this.loadPluginShare();
    }
  }

  public isShowNoDataInner() {
    return !this.stateMarket.isLoading && this.stateMarket?.pluginList?.length;
  }

  public isShowNoDataPersonal() {
    return (
      !this.statePersonal.isLoading && this.statePersonal?.pluginList?.length
    );
  }

  public isShowNoDataShare() {
    return !this.stateShare.isLoading && this.stateShare?.pluginList?.length;
  }

  public onActiveChange(isActive: boolean, tabName: string) {
    if (isActive) {
      this.getPluginListBySearch(tabName);
      this.activeTabName = tabName;
    }
  }

  public selectTool({ data, tools }) {
    tools.forEach(tool => {
      const combinedId = `${data.id}#${tool.id}`;
      if (tool.selected) {
        this.pluginSelected.push({
          ...tool,
          icon: data.icon,
          last_version_id: data.last_version_id,
          id: combinedId
        });
      } else {
        this.pluginSelected = this.pluginSelected.filter(item => item.id !== combinedId);
      }
    });
    this.pluginAdded.emit(this.pluginSelected);
    this.cdr.markForCheck();
  }

  private getStatusTag(plugin: IPluginWithTools) {
    const status = plugin.credential_status;
    const pluginLabels = this.getPluginLabels(status);
    const text = this.isZH() ? pluginLabels.zh : pluginLabels.en;
    let color = "green";
    let tip = null;
    let tipContext: any = {};
    if (status === PluginCredentialStatus.UNAUTHENTICATED) {
      color = "orange";
      tip = AuthConfigComponent;
      tipContext.data = plugin,
        tipContext.outputs = {
          confirm: () => {
            this.initData(this.tabLastActive);
          }
        };
    }
    return { text, color, tip, tipContext };
  }

  private getCategoryTag(category: string) {
    let categoryText = this.getCategoryLabel(category);

    return categoryText ?
      {
        text: categoryText,
        color: "default",
        style: {
          "background-color": "rgb(245, 245, 245)",
          "color": "rgb(25, 25, 25)",
          "font-weight": "400"
        }
      } : null;
  }

  private getUnpublishTag(versionId: string) {
    if (!versionId) {
      return {
        text: this.i18n.transform("unpublished"),
        color: "default"
      };
    }
    return null;
  }

  private getTags(type: string, plugin: IPluginWithTools, env) {
    let tags = [];
    if (type === "public") {
      tags.push(getQuotaTag(plugin, this.i18n, env));
      tags.push(this.getStatusTag(plugin));
      tags.push(this.getCategoryTag(plugin.category));
    } else if (type === "personal") {
      tags.push(this.getUnpublishTag(plugin.last_version_id));
    }

    return tags.filter(item => item);
  }

  private pluginFormatter(list: Array<IPluginWithTools>, type: string) {
    return list.map(plugin => {
      const isShare = type === "share";
      const isPersonal = type === "personal";
      const toolInfo = isShare ? plugin.extend_attribute.request_info.tool_info : plugin.request_info.tool_info;
      if (isShare) {
        plugin.plugin_id = plugin.resource_id;
        plugin.icon = plugin.resource_icon;
        plugin.plugin_desc = plugin.resource_desc;
        plugin.plugin_chinese_name = plugin.resource_name_ch;
        plugin.plugin_display_name = plugin.resource_name_en;
      }

      const canAdd = !isPersonal || plugin.last_version_id || this.useUnpublishedPlugin;
      let data: any = {
        id: plugin.plugin_id,
        name: this.getPluginName(plugin),
        icon: plugin.icon || WORKFLOW_SVGS.Plugin,
        description: plugin.plugin_desc,
        last_version_id: plugin.last_version_id,
        tag: this.getTags(type, plugin, false),
        tools: toolInfo.map(item => ({
          id: item.tool_id,
          name: this.getToolName(item),
          description: item.tool_desc,
          selected: this.isSelectedTool(plugin.plugin_id, item.tool_id),
          canAdd,
          tip: canAdd ? "" : this.pluginTip
        }))
      };
      if (isShare) {
        data.workspace_id = plugin.workspace_id;
        data.workspace_name = plugin.workspace_name;
        data.last_version_id = plugin.version_info_list?.[0]?.version_id;
        data.version_info_list = plugin.version_info_list;
      }
      return data;
    });
  }

  /** 入参表示: 用户是否切换了tab类型 **/
  private loadPluginMarket(isChangeTab = false) {
    const params: any = {};
    this.searchTagsMarket.forEach(tag => {
      params[tag.field] = tag.value;
    });
    const requestParams = {
      offset: !isChangeTab ? ((this.curPageMarket || 1) - 1) * PAGINATION_LIMIT_NUM : 0,
      limit: PAGINATION_LIMIT_NUM,
      ...params,
      type: "inner",
      published: 1
    };
    if (isChangeTab) {
      this.curPageMarket = 1;
    }
    if (this.selectedTagId) {
      requestParams[mapKeys.category] = this.selectedTagId;
    }

    this.stateMarket.isLoading = true;
    this.pluginRepoServe.getPluginList(requestParams).then(
      (res) => {
        this.processTip();
        this.stateMarket.isLoading = false;
        const { plugin_list, count } = res || {};
        this.stateMarket.pluginList = this.pluginFormatter(plugin_list, "public");
        this.isShow = "";
        this.totalNumberMarket = count;
        this.cdr.markForCheck();
      },
      () => {
        this.stateMarket.isLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  private loadPluginPersonal() {
    const params: any = {};
    this.searchTagsPersonal.forEach(tag => {
      params[tag.field] = tag.value;
    });
    const requestParams = {
      offset: (this.curPagePersonal - 1 || 0) * PAGINATION_LIMIT_NUM,
      limit: PAGINATION_LIMIT_NUM,
      ...params
    };

    this.statePersonal.isLoading = true;
    this.pluginRepoServe.getPluginList(requestParams).then(
      (res) => {
        this.processTip();
        this.statePersonal.isLoading = false;
        const { plugin_list, count } = res || {};
        this.statePersonal.pluginList = this.pluginFormatter(plugin_list, "personal");
        this.totalNumberPersonal = count;
        this.cdr.markForCheck();
      },
      () => {
        this.statePersonal.isLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  private loadPluginShare() {
    const nameTag = this.searchTagsShare.find(t => t.field === 'resourceName');
    let requestParams: any = {
      offset: (this.curPageShare - 1 || 0) * PAGINATION_LIMIT_NUM,
      limit: PAGINATION_LIMIT_NUM,
      resource_type: "plugin"
    };
    if (nameTag?.value) {
      requestParams.resourceName = nameTag.value;
    }
    this.stateShare.isLoading = true;
    this.shareService.getShareList(requestParams).then(
      (res) => {
        this.processTip();
        this.stateShare.isLoading = false;
        const { resource_list, count } = res || {};
        this.stateShare.pluginList = this.pluginFormatter(resource_list, "share");
        this.totalNumberShare = count;
        this.cdr.markForCheck();
      },
      () => {
        this.stateShare.isLoading = false;
        this.cdr.markForCheck();
      }
    );
  }

  private initData(tabNameActive = EPluginCategoryTabId.PERSONAL) {
    if (tabNameActive === EPluginCategoryTabId?.MARKET) {
      this.tabs[0].active = true;
      this.tabs[1].active = false;
    } else {
      this.tabs[0].active = false;
      this.tabs[1].active = true;
    }
    this.curPageMarket = 1;
    this.totalNumberMarket = 0;
    this.stateMarket = {
      pluginList: [],
      isLoading: false
    };
    this.searchTagsMarket = [];
    this.curPagePersonal = 1;
    this.totalNumberPersonal = 0;
    this.statePersonal = {
      pluginList: [],
      isLoading: false
    };
    this.searchTagsPersonal = [];
    this.curPageShare = 1;
    this.totalNumberShare = 0;
    this.stateShare = {
      pluginList: [],
      isLoading: false
    };
    this.searchTagsShare = [];
    this.cdr.markForCheck();
  }

  /** 清空搜索框的输入值 */
  private clearSearchboxValue() {
    this.searchTagsMarket = [];
    this.searchTagsPersonal = [];
    this.searchTagsShare = [];
  }

  /**
   * 在【添加组件】抽屉里，当某个组件卡片的描述超长时，显示tip
   * 通过服务的方式生成tip，且tip内容为自定义模板。
   */
  private processTip() {
    setTimeout(() => {
      this.presetTipHosts
        .toArray()
        .forEach((item: any) => this.createTip(item));
      this.personalTipHost
        .toArray()
        .forEach((item: any) => this.createTip(item));
      this.ShareTipHost.toArray().forEach((item: any) => this.createTip(item));
    }, 0);
  }

  private createTip(tipHost: any): void {
  }

  /**
   * 根据语言获取插件的名称
   * @param plugin
   */
  public getPluginName(plugin: IPluginWithTools): string {
    if (this.lang === "zh-cn") {
      return plugin.plugin_chinese_name
        ? `${plugin.plugin_chinese_name} ( ${plugin.plugin_display_name} )`
        : plugin.plugin_display_name;
    } else {
      return plugin.plugin_display_name;
    }
  }

  /**
   * 根据语言获取工具的名称
   * @param tool
   */
  public getToolName(tool: ITool): string {
    if (this.lang === "zh-cn") {
      return tool.tool_chinese_name
        ? `${tool.tool_chinese_name} ( ${tool.tool_display_name} )`
        : tool.tool_display_name;
    } else {
      return tool.tool_display_name;
    }
  }

  public getToolNumOfPlugin(plugin) {
    return plugin.request_info?.tool_info?.length;
  }

  public getCardIcon(plugin: IPluginWithTools) {
    return plugin.icon || WORKFLOW_SVGS.Plugin;
  }

  public isSelectedTool(pluginId: string, toolId: string): boolean {
    const combinedId = `${pluginId}#${toolId}`;
    return this.pluginSelected.some((plugin) => plugin.id === combinedId);
  }

  protected readonly changeUrl = cdnAssetUrl;

  handleClickClearSearch(): void {
    if (this.activeTabName === this.tabId.market) {
      this.searchTagsMarket = [];
    } else if (this.activeTabName === this.tabId.personal) {
      this.searchTagsPersonal = [];
    } else if (this.activeTabName === this.tabId.share) {
      this.searchTagsShare = [];
    }

    this.getPluginListBySearch(this.activeTabName);
  }

  isZH(): boolean {
    return this.lang === "zh-cn";
  }

  public getPluginLabels(data: string) {
    const filterData = this.pluginLabels.filter((item) => item.id === data);
    if (filterData && filterData.length > 0) {
      return filterData[0];
    }
    return this.pluginLabels[0];
  }

  changeAppTab(tab: AssertSquareTagType) {
    this.stateMarket.pluginList.length = 0;
    this.totalNumberMarket = this.stateMarket.pluginList.length;
    if (tab.id === "all") {
      this.selectedTagId = "";
    } else {
      this.selectedTagId = tab.id;
    }
    this.loadPluginMarket(true);
  }

  /** 获取卡片的标签 **/
  getCategoryLabel(tagId: string): string {
    if (tagId) {
      const tab = this.appPluginTabs.filter(item => item.id === tagId);
      if (tab?.length > 0) {
        return this.isZH() ? tab[0].name : tab[0].name_en;
      }
    }

    return "";
  }
}
