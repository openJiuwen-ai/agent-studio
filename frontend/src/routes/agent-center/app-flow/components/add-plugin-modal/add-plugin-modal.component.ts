import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output,inject } from '@angular/core';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { Router } from '@angular/router';
import { MODULES } from '@shared/modules';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { IPlugin, IPluginWithTools, ITool } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { MessageComponent } from '@shared/services/cfdata.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { CommonUtils } from 'src/utils/common.util';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CreatePluginBaseComponent } from '@routes/agent-center/app-plugin/create-plugin-base/create-plugin-base';
import { PluginCredentialStatus } from '@enums/agent-center.enum';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { Subject, takeUntil } from 'rxjs';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { ShareService } from '@routes/app-center/components/edit-share-modal/share.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { PromptService } from '@services/prompt.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';
import { getQuotaTag } from '../../../utils';
import { CommonService } from '@services/common.service';
import { AddPluginAuthComponent } from '@routes/plugin-market/add-plugin/add-plugin-auth.component';

enum mapKeys {
  category = 'category',
}

@Component({
  selector: 'meta-add-plugin-modal',
  templateUrl: './add-plugin-modal.component.html',
  styleUrls: ['./add-plugin-modal.component.less'],
  standalone: true,
  imports: [MODULES, NewCommonNoDataWithBtnComponent, MultiFieldSearchComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AddPluginModalComponent implements OnInit {
  @Input() addedPluginList;
  @Input() outputs: { pluginChange: (plugin: IPlugin) => void };
  @Output('pluginChange') pluginChange = new EventEmitter<IPlugin>();
  readonly drawerRef = inject(NzDrawerRef);
  public controller = new AbortController();
  public isShowCreatePluginModal = false;
  public isAddingTool = false;
  public changeUrl = cdnAssetUrl;
  public tabs = [
    {
      id: 'custom',
      title: this.i18n.transform('component_plugin'),
      active: true,
    },
    {
      id: 'inner',
      title: this.i18n.transform('pre_installed_plugins'),
      active: false,
    },
    {
      id: 'share',
      title: this.i18n.transform('addpluginmodal_1'),
      active: false,
    },
  ];
  protected readonly PluginCredentialStatus = PluginCredentialStatus;
  public searchItemsForInner = [
    { label: this.i18n.transform('plugin_name'), field: 'tool_chinese_name' },
    { label: this.i18n.transform('plugin_en_name'), field: 'name' },
    { label: this.i18n.transform('plugin_description'), field: 'tool_desc' },
  ];
  public searchTagsInner: ISearchTag[] = [];
  public searchFieldInner: string = 'tool_chinese_name';

  public searchItemsForCustom = [
    { label: this.i18n.transform('plugin_name'), field: 'tool_chinese_name' },
    { label: this.i18n.transform('plugin_en_name'), field: 'name' },
    { label: this.i18n.transform('plugin_description'), field: 'tool_desc' },
  ];
  public searchTagsCustom: ISearchTag[] = [];
  public searchFieldCustom: string = 'tool_chinese_name';

  public searchItemsForShare = [
    { label: this.i18n.transform('name'), field: 'resourceName' },
  ];
  public searchTagsShare: ISearchTag[] = [];
  public searchFieldShare: string = 'resourceName';
  public refMap = new Map<string, number>();
  public plugins: Array<IPluginWithTools> = [];
  public currentPage = 1;
  public totalNumber = 0;
  public lang = CommonUtils.getLanguage();
  public pageSize = 10;
  public pageSizeOptions = [10, 20, 30, 40, 50, 100];
  public isShow = '';
  public isLoading = false;
  public addedCnt = 0;
  public addedToolsTypeCnt = 0;
  public addedNumMap: Record<string, number> = {};
  public currTab = 'custom';
  private destroy$ = new Subject<void>();
  public isHC = false;
  tabSelectIndex = 1;
  childTabSelectIndex = 1;
  get searchNameIsEmpty(): boolean {
    if (this.currTab === 'share') {
      return this.searchTagsShare.length === 0;
    } else if (this.currTab === 'inner') {
      return this.searchTagsInner.length === 0;
    }
    return this.searchTagsCustom.length === 0;
  }
  public pluginLabels = [
    {
      zh: this.i18n.transform('no_auth'),
      en: 'Needless Auth',
      id: PluginCredentialStatus.NONE,
      style: {
        color: 'rgba(20, 118, 255, 1)',
        backgroundColor: 'rgba(222, 236, 255, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
    },
    {
      zh: this.i18n.transform('editcardmodal_85'),
      en: 'Authenticated',
      id: PluginCredentialStatus.AUTHENTICATED,
      style: {
        color: 'rgba(2, 153, 49, 1)',
        backgroundColor: 'rgba(213, 242, 220, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
    },
    {
      zh: this.i18n.transform('editcardmodal_86'),
      en: 'Unauthenticated',
      id: PluginCredentialStatus.UNAUTHENTICATED,
      style: {
        color: 'rgba(25, 25, 25, 1)',
        backgroundColor: 'rgba(230, 230, 230, 1)',
        display: 'inline-block',
        padding: '4px',
        borderRadius: '4px',
        fontSize: '12px',
      },
    },
  ];
  appPluginTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform('all'),
      name_en: 'all',
      id: 'all',
      active: true,
      description: '',
      library_type: '',
      created_on: 0,
      updated_on: 0,
    },
  ];
  selectedTagId: string = '';

  constructor(
    private router: Router,
    private appFlowRepoServe: AppFlowRepoService,
    private drawerService: NzDrawerService,
    private configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private pluginRepoServe: AppPluginRepoService,
    private cdr: ChangeDetectorRef,
    private appFlowServe: AppFlowService,
    private shareService: ShareService,
    private agentRepoServe: AppAgentRepoService,
    private commonService: CommonService,
    public promptService: PromptService,
    private modalService: NzModalService
  ) {}

  get site() {
    return this.configServ.getConfigs().site;
  }

  get useUnpublishedPlugin() {
    return this.configServ.getConfigs().plugin_publish_choice;
  }

  ngOnInit() {
    this.appFlowServe
      .refresPluginListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((pluginList: any) => {
        this.addedPluginList = pluginList;
        this.addedCnt = pluginList.length;
        this.addedToolsTypeCnt = new Set(pluginList.map(item => item.configs.id)).size;
      });
    this.addedCnt = this.addedPluginList.length;
    this.addedToolsTypeCnt = new Set(this.addedPluginList.map(item => item.configs.id)).size;
    this.getPluginTagData();
    this.initApiList();
  }

  public async initApiList(type?: string, isChangeTab = false) {
    if (this.controller) {
      this.controller.abort();
    }

    this.controller = new AbortController();
    this.isLoading = true;

    if ('search' === type) {
      this.currentPage = 1;
    }
    try {
      let data: any = null;
      const params: any = {
        offset: ((this.currentPage || 1) - 1) * this.pageSize,
        limit: this.pageSize,
      };
      if (this.currTab === 'share') {
        params.resource_type = 'plugin';
        const nameTag = this.searchTagsShare.find(t => t.field === 'resourceName');
        if (nameTag?.value) {
          params.resourceName = nameTag.value;
        }
        data = await this.shareService.getShareList(params);
        data.plugin_list = (data?.resource_list || []).map((item: any) => {
          const last_version_id = item.version_info_list[0].version_id;
          return {
            plugin_id: item.resource_id,
            icon: item.resource_icon,
            plugin_desc: item.resource_desc,
            plugin_chinese_name: item.resource_name_ch,
            plugin_display_name: item.resource_name_en,
            auth_required: null,
            credential_status: null,
            last_version_id: last_version_id,
            version_info_list: item.version_info_list,
            request_info: item.extend_attribute.request_info,
            workspace_id: item.workspace_id,
            workspace_name: item.workspace_name,
          };
        });
      } else {
        const params: any = {
          offset: !isChangeTab ? ((this.currentPage || 1) - 1) * this.pageSize : 0,
          limit: this.pageSize,
        };
        const activeSearchTags = this.currTab === 'inner' ? this.searchTagsInner : this.searchTagsCustom;
        activeSearchTags.forEach(tag => {
          params[tag.field] = tag.value;
        });
        if (this.currTab !== 'custom') {
          params.published = 1;
          params.type = this.currTab;
        }

        if (this.currTab === 'inner' && this.selectedTagId) {
          params[mapKeys.category] = this.selectedTagId;
        }

        data = await this.pluginRepoServe.getPluginList(params, this.controller.signal);
      }

      this.plugins = data?.plugin_list ?? [];
      const isHC = false;
      this.plugins.forEach((item, index) => {
        //付费免费字段
        item.quotaTag = getQuotaTag(item, this.i18n, false);
      });
      if (this.currTab === 'share') {
      } else {
        for (const plugin of this.plugins) {
          for (const tool of plugin.request_info?.tool_info) {
            tool.ref_num = this.countRefNum(plugin.plugin_id, tool.tool_id);
          }
        }
      }

      this.totalNumber = data.count;
    } catch (error) {
      // do nth
    } finally {
      this.isLoading = false;
      this.cdr.markForCheck();
    }
  }

  public onPageSizeChange(size: number) {
    this.pageSize = size;
    this.currentPage = 1;
    this.initApiList();
  }

  public countRefNum(pluginId: string, toolId: string) {
    const key = `${pluginId}#${toolId}`;
    if (this.refMap.has(key)) {
      return this.refMap.get(key) as number;
    }
    const refNum = this.addedPluginList.reduce((count, addedPlugin) => {
      return addedPlugin.configs.id === pluginId && addedPlugin.configs.tool_id === toolId ? count + 1 : count;
    }, 0);
    this.refMap.set(key, refNum);
    return refNum;
  }
  public addPlugin(e: Event, plugin: IPlugin) {
    e.stopPropagation();
    ++this.addedCnt;
    this.addedNumMap[plugin.tool_id] = this.addedNumMap[plugin.tool_id] ? ++this.addedNumMap[plugin.tool_id] : 1;

    const { tool_id, last_version_id } = plugin;
    if (last_version_id) {
      this.appFlowRepoServe.getPluginVersionInfo(tool_id, last_version_id).then((pluginVersion: IPlugin) => {
        const result = { ...pluginVersion, last_version_id, request_info: pluginVersion.request_info };
        this.pluginChange.emit(result);
        this.outputs?.pluginChange?.(result);
      });
    } else {
      const result = { ...plugin, request_info: plugin.request_info };
      this.pluginChange.emit(result);
      this.outputs?.pluginChange?.(result);
    }
  }

  public addTool(e: Event, plugin, tool) {
    e.stopPropagation();
    if (this.isAddingTool) {
      return;
    }
    if (this.tabSelectIndex === 1 && !plugin.last_version_id && !this.useUnpublishedPlugin) {
      return;
    }
    this.isAddingTool = true;
    const { plugin_id, last_version_id } = plugin;

    const key = `${plugin.plugin_id}#${tool.tool_id}`;
    this.refMap.set(key, (this.refMap.get(key) ?? 0) + 1);
    if (last_version_id) {
      this.appFlowRepoServe
        .getPluginVersionInfo(plugin_id, last_version_id)
        .then(res => {
          const pluginVersion = res.data;
          let toolList = pluginVersion.intf_type.find(toolIntfType => toolIntfType.tool_id === tool.tool_id);
          if (!toolList) {
            this.isAddingTool = false;
            MessageComponent.showError(this.i18n.transform('addpluginmodalcomponent_260'));
            return;
          }
          tool.ref_num++;
          const toolInfo = {
            ...tool,
            plugin_chinese_name: plugin.plugin_chinese_name,
            id: pluginVersion.plugin_id,
            intf_type: pluginVersion.intf_type.find(toolIntfType => toolIntfType.tool_id === tool.tool_id).intf_type,
            input_schema: pluginVersion.input_schema.find(toolInputSchema => toolInputSchema.tool_id === tool.tool_id).input_schema,
            output_schema: pluginVersion.output_schema.find(toolOutputSchema => toolOutputSchema.tool_id === tool.tool_id).output_schema,
            type: pluginVersion.type,
          };
          const result = { ...toolInfo, last_version_id, request_info: plugin.request_info };
          this.pluginChange.emit(result);
          this.outputs?.pluginChange?.(result);
          this.drawerRef.close();
        })
        .catch(() => {
          this.isAddingTool = false;
        });
    } else {
      const toolInfo = {
        ...tool,
        plugin_chinese_name: plugin.plugin_chinese_name,
        id: plugin.plugin_id,
        intf_type: plugin.intf_type.find(toolIntfType => toolIntfType.tool_id === tool.tool_id).intf_type,
        input_schema: plugin.input_schema.find(toolInputSchema => toolInputSchema.tool_id === tool.tool_id).input_schema,
        output_schema: plugin.output_schema.find(toolOutputSchema => toolOutputSchema.tool_id === tool.tool_id).output_schema,
        type: plugin.type,
      };
      tool.ref_num++;
      const result = { ...toolInfo, request_info: plugin.request_info };
      this.pluginChange.emit(result);
      this.outputs?.pluginChange?.(result);
      this.drawerRef.close();
    }
  }

  public onActiveChange(tab: { title: string; active: boolean; id: string }, isActive: boolean) {
    if (isActive) {
      this.totalNumber = 0;
      this.currentPage = 1;
      this.pageSize = 10;
      this.currTab = tab.id;
      this.initApiList();
    }
  }

  public getCardIcon(plugin: IPluginWithTools) {
    return plugin.icon || WORKFLOW_SVGS.Plugin;
  }

  navigate() {
    this.router.navigate(['/home/agent-center/component-library'], {
      queryParams: {
        tab: 'plugin',
      },
    });
  }

  public showAddPluginModal() {
    if (this.isShowCreatePluginModal) {
      return;
    }
    this.isShowCreatePluginModal = true;
    const modalContainer = document.querySelector('#addPluginModalComponent > div');
    const thisNzModal: any = this.modalService.create({
      nzWidth: '1000px',
      nzClosable: false,
      nzMaskClosable: false,
      nzMask: true,
      nzBodyStyle: { top: '0px' },
      nzContent: CreatePluginBaseComponent,
    });
    const instance = thisNzModal.getContentComponent();
    instance.usedFrom = 'flow';
    instance.confirm.subscribe(() => {
      this.drawerRef.close();
      if (this.currTab === 'custom') {
        this.initApiList();
      }
    });
    thisNzModal.afterClose.subscribe(() => {
      this.isShowCreatePluginModal = false;
    });
  }

  public getPluginName(plugin: IPluginWithTools): string {
    if (this.lang === 'zh-cn') {
      return plugin.plugin_chinese_name ? `${plugin.plugin_chinese_name} ( ${plugin.plugin_display_name} )` : plugin.plugin_display_name;
    } else {
      return plugin.plugin_display_name;
    }
  }

  public getToolName(plugin: ITool): string {
    if (this.lang === 'zh-cn') {
      return plugin.tool_chinese_name ? `${plugin.tool_chinese_name} ( ${plugin.tool_display_name} )` : plugin.tool_display_name;
    } else {
      return plugin.tool_display_name;
    }
  }
  public getToolNumOfPlugin(plugin) {
    return plugin.request_info?.tool_info?.length;
  }

  handleClickClearSearch() {
    if (this.currTab === 'share') {
      this.searchTagsShare = [];
    } else if (this.currTab === 'inner') {
      this.searchTagsInner = [];
    } else {
      this.searchTagsCustom = [];
    }
    this.currentPage = 1;
    this.initApiList();
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  public getPluginLabels(data: string) {
    const filterData = this.pluginLabels.filter(item => item.id === data);
    if (filterData && filterData.length > 0) {
      return filterData[0];
    }
    return this.pluginLabels[0];
  }

  public onVersionClick(event: any) {
    event.stopPropagation();
  }

  onVersionSelect(plugin: any) {
    if (this.isShow !== plugin.plugin_id) {
      this.isShow = plugin.plugin_id;
    }
    this.getPluginVersion(plugin, plugin.last_version_id);
  }

  getShareTool(plugin: any) {
    this.isShow = this.isShow === plugin.plugin_id ? '' : plugin.plugin_id;
    if (this.isShow) {
      this.getPluginVersion(plugin, plugin.last_version_id);
    }
  }

  getPluginVersion(plugin, version_id) {
    const requestId = (plugin.toolRequestId ?? 0) + 1;
    plugin.toolRequestId = requestId;
    plugin.toolIsReady = false;
    this.agentRepoServe
      .getPluginVersion(plugin.plugin_id, version_id)
      .then(res => {
        if (plugin.toolRequestId === requestId) {
          plugin.tool_info = res?.data?.request_info?.tool_info || [];
        }
      })
      .finally(() => {
        if (plugin.toolRequestId === requestId) {
          plugin.toolIsReady = true;
          this.cdr.markForCheck();
        }
      });
  }

  private getPluginTagData() {
    const params = {
      library_type: 'plugin',
    };
    this.promptService
      ?.getAssertTagAsync(params)
      .then(response => {
        const firstTab = this.appPluginTabs[0];
        this.appPluginTabs.length = 0;
        this.appPluginTabs.push(firstTab);
        for (let index = 0; index < response.length; index++) {
          this.appPluginTabs.push(response[index]);
        }
      })
      .catch();
  }

  changeAppTab(index: any) {
    this.appPluginTabs.forEach((item, i) => {
      item.active = i === index;
    });
    const tab = this.appPluginTabs[index];
    if (tab.active) {
      this.plugins.length = 0;
      if (tab.id === 'all') {
        this.selectedTagId = '';
      } else {
        this.selectedTagId = tab.id;
      }
      this.initApiList('search').then();
    }
  }
  getTagTitle(plugin) {
    const time = plugin.limit - plugin.uasge;
    return this.i18n.transform('app_center_tag_1', { time: time });
  }

  getTagTip(plugin) {
    const time = plugin.limit - plugin.uasge;
    return this.i18n.transform('app_center_tag_2', { total: plugin.limit, time: time });
  }

  /** 获取卡片的标签 **/
  getCategoryLabel(tagId: string): string {
    if (!tagId || this.appPluginTabs.length <= 0) {
      return '';
    }
    const filterData = this.appPluginTabs?.filter(item => item.id === tagId);
    if (filterData && filterData.length > 0) {
      return this.isZH() ? filterData[0].name : filterData[0].name_en;
    }
    return '';
  }

  public handleClickAddAuthConfig(item) {
    const thisNzModal = this.modalService.create({
      nzTitle: 'createPluginAuth',
      nzWidth: 1000,
      nzContent: AddPluginAuthComponent,
      nzClosable: true,
      nzOnOk: () => {
        this.initApiList();
      },
    });
    const instance = thisNzModal.getContentComponent();
    instance.pluginInfo = item;
  }
}
