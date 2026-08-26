import {
  Component,
  Output,
  EventEmitter,
  ChangeDetectorRef,
  Input,
  SimpleChanges,
  ViewChildren,
  QueryList,
  ElementRef
} from "@angular/core";
import { MODULES } from "@shared/modules";
import {
  EPluginCategoryTabId,
  PAGINATION_LIMIT_NUM
} from "../../../types/my-workspace.types";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { Subject, Subscription, takeUntil } from "rxjs";
import { agentCommonLogic } from "../../common-logic-agent";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { McpServerCardComponent } from "./mcp-server-card.component";
import {
  AddMcpHalfModalComponent
} from "@routes/agent-center/app-mcp-service/components/add-mcp-half-modal/add-mcp-half-modal.component";
import {
  NewCommonNoDataWithBtnComponent
} from "@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component";
import { WindowResizeService } from "@shared/base/window-resize.service";
import { MCPService } from "@services/agent-center/mcp.service";
import { MasOperatorService } from "@services/mas-operator.service";
import { CommonService } from "@services/common.service";
import { SkillCardComponent } from "./skill-card/skill-card.component";
import { getMcpIcon } from "../../../utils";
import { NzDrawerModule, NzDrawerService } from "ng-zorro-antd/drawer";
import { NzModalService } from "ng-zorro-antd/modal";

enum mapKeys {
  toolPendingStatus = "toolPendingStatus"
}

@Component({
  selector: "add-mcp-servers",
  templateUrl: "./add-mcp-servers.component.html",
  styleUrls: ["./add-mcp-servers.component.scss"],
  standalone: true,
  imports: [
    MODULES,
    SkillCardComponent,
    McpServerCardComponent,
    NewCommonNoDataWithBtnComponent,
    NzDrawerModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    }
  ]
})
export class AddMcpServersComponent {
  @Input() agentId = "";
  @Input() mcpServers = [];
  @Input() isFromWorkflow: boolean = false; // 是否是在工作流中添加mcp
  @Input() isClickAddMcpToWorkflow: boolean = false; // 是否允许向工作流画布中添加MCP服务
  @Input() mcpCreateSub; // 是否是通过MCP创建的提示信息，添加的MCP服务

  @Output() mcpAdded = new EventEmitter<any[]>();
  @Output() mcpReduced = new EventEmitter<any[]>();
  @Output() backToMcpList = new EventEmitter<any[]>();
  @Output() closeMcpList = new EventEmitter<any[]>();
  @Output() createMcpRes = new EventEmitter<any>();

  @ViewChildren("presetTipHost") presetTipHosts!: QueryList<ElementRef>;
  @ViewChildren("personalTipHost") personalTipHost!: QueryList<ElementRef>;

  get searchNameIsEmpty(): boolean {
    return this.searchMarketVal.length === 0 && this.searchPersonVal.length === 0;
  }

  public mcpSelected: any = [];
  public agentMcpSelected: Map<string, any> = new Map();
  public mcpToolPendingIds: any = {};
  public tabs: any = [
    {
      title: this.i18n.transform("pre_mcp_service"),
      active: true,
      id: "inner",
      onActiveChange: (isActive: boolean, id: string): void => {
        if (isActive) {
        }
      }
    },
    {
      title: this.i18n.transform("personal_mcp_service"),
      active: false,
      id: "custom",
      onActiveChange: (isActive: boolean, id: string): void => {
        if (isActive) {
        }
      }
    }
  ];

  // 预置MCP服务Tab，对应的数据与分页
  public presetMcpServers: any = {
    list: [],
    isLoading: false
  };

  public curPageMarket = 1;
  public totalNumberMarket = 0;
  public searchMarketVal: string = "";

  // 个人MCP服务Tab，对应的数据与分页
  public customMcpServers: any = {
    list: [],
    isLoading: false
  };
  public curPagePersonal = 1;
  public totalNumberPersonal = 0;
  public searchPersonVal: string = "";
  public isClickMcpCard: boolean = false;

  public emptyPlaceholder = this.i18n.transform("search_placeholder");
  private destroy$ = new Subject<void>();
  private tabLastActive!: EPluginCategoryTabId;
  // 创建新的MCP服务之前，上一次被选中但没有点确定，没有保存到后端数据库中的MCPs
  public MCPsLastClicked: any[] = [];
  // 添加MCP服务后，还是新建MCP服务后。默认是添加MCP服务后
  private addOrCreate: boolean = true;
  public showFormServerId = "";
  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  private resizeSub: Subscription;
  default_item = {
    id: "blank-creation",
    label: this.i18n.transform("blank-creation")
  };
  is_site = this.commonService.isSite();
  is_north4 = this.commonService.isNorth4();

  create_items: Array<any> = this.is_site ? [
    {
      id: "blank-creation",
      label: this.i18n.transform("blank-creation")
    },
    {
      id: "official-creation",
      label: this.i18n.transform("official-creation")
    }
  ] : [
    {
      id: "blank-creation",
      label: this.i18n.transform("blank-creation")
    },
    {
      id: "official-creation",
      label: this.i18n.transform("official-creation")
    },
    {
      id: "third-party-creation",
      label: this.i18n.transform("third-party-creation")
    }
  ];

  constructor(
    private commonLogic: agentCommonLogic,
    private agentDataServe: AgentDataService,
    private appAgentServe: AppAgentRepoService,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private windowResizeService: WindowResizeService,
    private mcpService: MCPService,
    private masOperatorService: MasOperatorService,
    private commonService: CommonService,
    private nzModal: NzModalService
  ) {
    this.agentDataServe
      .mcpsAndTabIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((mcpsAndCurrentTab: any) => {
        this.tabLastActive = mcpsAndCurrentTab.currentTabId;
        this.MCPsLastClicked = mcpsAndCurrentTab.list;
      });
  }

  ngOnInit() {
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe((width) => {
      this.windowWidth = width;
    });

    this.agentDataServe
      .clickFlagMCPUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((clickFlag: string) => {
        this.clearSearchboxValue();
        if (clickFlag === "add") {
          // 添加MCP服务后
          this.addOrCreate = true;
          this.initData(EPluginCategoryTabId.MARKET);
          /** 点击外部的添加MCP服务按钮，以父组件的@Input属性为准*/
          this.mcpSelected = [...this.mcpServers];
          /**
           * 同步刷新service中的值。
           * 避免新建MCP服务后，关闭抽屉，service记录了上一次的用户操作，但接口没保存，两处不一致
           */
          this.agentDataServe.setMCPsAndTabId(
            this.commonLogic.getCurrentTabId(
              this.tabs,
              EPluginCategoryTabId.MARKET,
              EPluginCategoryTabId.PERSONAL,
              EPluginCategoryTabId.SHARE
            ),
            this.mcpSelected
          );
          this.loadMCPsPreset().then();
          this.loadMCPsCustom().then();
        }
        if (clickFlag === "create") {
          // 新建MCP服务后
          this.addOrCreate = false;
          this.initData(this.tabLastActive);
          /** 点击内部的创建MCP服务按钮，以service存储的值为准 */
          this.mcpSelected = this.MCPsLastClicked;
          this.loadMCPsPreset().then();
          this.loadMCPsCustom().then();
        }
        this.cdr.markForCheck();
      });
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  setSelectedMcp(data: Array<any>) {
    this.agentMcpSelected.clear();
    data.forEach(mcp => {
      mcp.selectedTools = mcp.selectedTools ?? new Set(mcp.mcp_choose_tools ?? []);
      this.agentMcpSelected.set(mcp.server_id, mcp);
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.agentId?.currentValue && changes.agentId.currentValue !== this.agentId) {
      this.getAgent();
    }
    /**
     * 增加addOrCreate变量进行判断。如果是添加MCP服务，则由父组件传入；
     * 如果是创建完新MCP服务后，则由service传入。
     */
    if (changes.mcpServers && this.addOrCreate) {
      this.setSelectedMcp(changes.mcpServers.currentValue);
      // 创建副本，避免同步修改父组件中的mcpServers.list
      this.mcpSelected = [...changes.mcpServers.currentValue];
      // 页面被强制刷新后，一定要用get接口传入的输入属性值更新service，给service赋初值
      this.agentDataServe.setMCPsAndTabId(
        this.commonLogic.getCurrentTabId(
          this.tabs,
          EPluginCategoryTabId.MARKET,
          EPluginCategoryTabId.PERSONAL,
          EPluginCategoryTabId.SHARE
        ),
        this.mcpSelected
      );
    }
  }

  ngOnDestroy(): void {
    this.resizeSub?.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
  }

  get mcpLimit() {
    return this.configServ.getConfigs()?.agent_mcp_bound_limit ?? 5;
  }

  get activeTab() {
    return this.tabs.filter((item: any) => item.active)[0].id;
  }

  /** 根据名称，搜索MCP服务 */
  public async getMCPsBySearch(type = "inner"): Promise<void> {
    this.curPagePersonal = 1;
    if (type === "inner") {
      await this.loadMCPsPreset();
    } else {
      await this.loadMCPsCustom();
    }
  }

  /** 当页码改变时，查询组件 */
  public async getMCPListByPage(type = "inner") {
    if (type === "inner") {
      await this.loadMCPsPreset();
    } else {
      await this.loadMCPsCustom();
    }
  }

  public isShowNoDataInner() {
    return !this.presetMcpServers.isLoading && this.totalNumberMarket;
  }

  public isShowNoDataCustom() {
    return !this.customMcpServers.isLoading && this.totalNumberPersonal;
  }

  private async loadMCPsPreset() {
    const params = {
      "name": this.searchMarketVal,
      "tool_desc": this.searchMarketVal,
      "tool_chinese_name": this.searchMarketVal
    };
    const requestParams = {
      offset: ((this.curPageMarket || 1) - 1) * PAGINATION_LIMIT_NUM,
      limit: PAGINATION_LIMIT_NUM,
      ...params,
      type: "inner"
    };

    this.presetMcpServers.isLoading = true;
    try {
      const res = await this.appAgentServe.getMCPServerList(requestParams);
      this.handleTip();
      this.presetMcpServers.isLoading = false;
      const { mcps, total } = res || {};
      if (Array.isArray(mcps)) {
        for (let index = 0; index < mcps.length; index++) {
          mcps[index].server_id = mcps[index].id;
        }
      }
      this.presetMcpServers.list = mcps || [];
      this.totalNumberMarket = total || 0;
      this.cdr.markForCheck();
    } finally {
      this.presetMcpServers.isLoading = false;
      this.cdr.markForCheck();
    }
  }

  private async getAgent() {
    const agentRes = await this.appAgentServe.fetchAgentDetail(this.agentId);
    this.setSelectedMcp(agentRes.mcp_servers);
  }

  private async loadMCPsCustom() {
    const params = {
      "name": this.searchPersonVal,
      "tool_desc": this.searchPersonVal,
      "tool_chinese_name": this.searchPersonVal
    };
    const currentMasOperator = this.masOperatorService.getCurrentMasOperators();
    const externalMapFlag = currentMasOperator.externalMappingInfo?.length;

    const requestParams: any = {
      offset: (this.curPagePersonal - 1 || 0) * PAGINATION_LIMIT_NUM,
      limit: PAGINATION_LIMIT_NUM,
      ...params,
      type: "custom"
    };
    if (externalMapFlag && this.isFromWorkflow) {
      requestParams.visibility = "global";
    }

    this.customMcpServers.isLoading = true;
    try {
      const res = await this.appAgentServe.getMCPServiceList(requestParams);
      this.handleTip();
      this.customMcpServers.isLoading = false;
      const { mcps, total } = res || {};
      if (Array.isArray(mcps)) {
        mcps.forEach(mcp => {
          mcp.server_id = mcp.id;
          mcp.icon = getMcpIcon(mcp.icon);
          mcp.tag = [this.getStatusTag(mcp?.fc_instance_status)];
          const selectedData = this.agentMcpSelected.get(mcp.id);
          mcp.oldDataSelectAll = Boolean(selectedData && !selectedData.mcp_choose_tools);
          mcp.selectedTools = new Set(selectedData?.mcp_choose_tools || []);
        });
      }
      this.customMcpServers.list = mcps;
      this.updateToolPendingStatus();
      this.totalNumberPersonal = total;
      this.cdr.markForCheck();
    } finally {
      this.customMcpServers.isLoading = false;
      this.cdr.markForCheck();
    }
  }

  // 当用户切换到第二页的时候，然后在切换到第一页，需要回显工具状态
  private updateToolPendingStatus() {
    for (let index = 0; index < this.customMcpServers.list.length; index++) {
      if (this.mcpToolPendingIds[this.customMcpServers.list[index].id]) {
        this.customMcpServers.list[index][mapKeys.toolPendingStatus]
          = this.mcpToolPendingIds[this.customMcpServers.list[index].id];
      }
    }
  }


  private initData(tabNameActive = EPluginCategoryTabId.MARKET) {
    if (tabNameActive === EPluginCategoryTabId.MARKET) {
      this.tabs[0].active = true;
      this.tabs[1].active = false;
    } else {
      this.tabs[0].active = false;
      this.tabs[1].active = true;
    }
    this.curPageMarket = 1;
    this.totalNumberMarket = 0;
    this.presetMcpServers = {
      list: [],
      isLoading: false
    };
    this.curPagePersonal = 1;
    this.totalNumberPersonal = 0;
    this.customMcpServers = {
      isLoading: false,
      list: []
    };
    this.cdr.markForCheck();
  }

  private createTip(tipHost: any): void {
  }

  /** 清空搜索框的输入值 */
  private clearSearchboxValue() {
    this.searchMarketVal = "";
    this.searchPersonVal = "";
  }


  /**
   * 在【添加MCP服务】抽屉里，当某个卡片的描述超长时，显示tip
   * 通过服务的方式生成tip，且tip内容为自定义模板。
   */
  private handleTip() {
    setTimeout(() => {
      this.presetTipHosts
        .toArray()
        .forEach((item: any) => this.createTip(item));
      this.personalTipHost
        .toArray()
        .forEach((item: any) => this.createTip(item));
    }, 0);
  }

  public showForm(data) {
    this.showFormServerId = data.server_id;
  }

  public selectMcp({ data, tools }) {
    tools.forEach(tool => {
      if (tool.selected) {
        data.selectedTools.add(tool.name);
      } else {
        data.selectedTools.delete(tool.name);
      }
    });
    this.agentMcpSelected.set(data.id, data);
    const list = [...this.agentMcpSelected.values()];
    this.mcpSelected = list.filter(mcp => mcp?.selectedTools?.size > 0);
    this.mcpAdded.emit(this.mcpSelected);
  }

  public async createMcp(data, tab) {
    const { server_id } = data;
    await this.getMCPListByPage(tab);
    const list =
      tab === "inner"
        ? this.presetMcpServers.list
        : this.customMcpServers.list;
    const selected = list.find((item) => item.server_id === server_id);
    this.mcpSelected.push(selected);
    this.mcpAdded.emit(this.mcpSelected);
  }

  public async handleSelectChange(
    { type, data, noNeedTool },
    tab: string
  ) {
    if (type === "form") {
      this.showForm(data);
      return;
    }
    if (type === "add") {
      this.addMcp(data, noNeedTool);
      return;
    }
    if (type === "remove") {
      const i = this.mcpSelected.findIndex(
        (item: any) => item.server_id === data.server_id
      );
      this.removeMcp(data);
      this.mcpSelected.splice(i, 1);
      this.mcpReduced.emit(this.mcpSelected);
      return;
    }
    if (type === "create") {
      this.createMcp(data, tab);
    }
  }

  // 点击取消MCP的时候
  private removeMcp(mcpData: any) {
    this.mcpToolPendingIds[mcpData.id] = true;
    setTimeout(() => {
      this.mcpToolPendingIds[mcpData.id] = false;
    }, 300);
  }

  // 点击MCP的时候需要获取下MCP的工具列表信息
  private addMcp(mcpData: any, noNeedTool: boolean = false) {
    if (this.mcpToolPendingIds[mcpData.id]) {
      return;
    }
    // 如果不需要获取工具接口
    if (noNeedTool) {
      this.addMcpDataInPendingIds(mcpData, true);
      this.isClickMcpCard = !this.isClickMcpCard;
      this.mcpSelected.push(mcpData);
      this.mcpAdded.emit(this.mcpSelected);
      setTimeout(() => {
        this.addMcpDataInPendingIds(mcpData, false);
      }, 500);
      return;
    }
    // 需要获取工具接口
    this.addMcpDataInPendingIds(mcpData, true);
    this.mcpService.getMcpToolInfo(mcpData.id).then(() => {
      this.isClickMcpCard = !this.isClickMcpCard;
      mcpData.fc_instance_status = "success";
      this.mcpSelected.push(mcpData);
      this.mcpAdded.emit(this.mcpSelected);
    }).catch(() => {
      mcpData.fc_instance_status = "pendingTools";
    })
      .finally(() => {
        this.addMcpDataInPendingIds(mcpData, false);
      });
  }

  // 当待添加的MCP数据没有存在mcpToolPendingIds中时，就添加进去
  private addMcpDataInPendingIds(mcpData: any, status: boolean) {
    this.mcpToolPendingIds[mcpData.id] = status;
  }

  private getStatusTag(status) {
    if (status === "success") {
      return {
        text: "deployed",
        color: "green"
      };
    } else if (status === "creatingStack") {
      return {
        text: "deploying",
        color: "orange"
      };
    } else if (status === "pendingTools") {
      return {
        text: "pendingTools",
        color: "orange"
      };
    } else {
      return {
        text: "deployFailed",
        color: "red"
      };
    }
  }

  // 把创建MCP的Tab移动到【个人服务】
  public addMcpToAgent(context: any) {
    if (this.activeTab !== "custom") {
      for (let index = 0; index < this.tabs.length; index++) {
        this.tabs[index].active = false;
      }
      this.tabs[1].active = true;
    }
    context.dismiss();
  }

  /** 刷新数据 **/
  public refreshData(type: string) {
    if (type === "inner") {
      this.handleClickClearSearchWithInner();
    } else {
      this.handleClickClearSearchWithCustom();
    }
  }

  /** 清除custom，搜索没有数据时，清空搜索框 **/
  public handleClickClearSearchWithCustom() {
    this.clearSearchboxValue();
    this.loadMCPsCustom();
  }

  public handleClickClearSearchWithInner() {
    this.clearSearchboxValue();
    this.loadMCPsCustom();
  }

  /** 编辑某个MCP服务 **/
  public editMcpService(data: any) {

    if (["inner", "custom"].includes(data.resource)) {
      const thisNzModal: any = this.nzModal.create({
        nzContent: AddMcpHalfModalComponent,
        nzWidth: "1000px"
      });
      const instance = thisNzModal.getContentComponent();
      instance.type = "service";
      instance.selectMcpData = data;
      instance.action = "edit";
      instance.close.subscribe(() => {
        this.loadMCPsCustom().then();
        this.backToMcpList.emit();
      });
    }
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return "800px";
    } else {
      return "600px";
    }
  }
}
