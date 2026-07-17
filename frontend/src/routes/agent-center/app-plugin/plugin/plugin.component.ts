import { ChangeDetectorRef, Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { I18nNamespace } from '@i18n';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { MODULES } from '@shared/modules';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { CommonUtils } from 'src/utils/common.util';
import { IPluginWithTools, IRequestArgsView, IResponseArgsView } from '../app-plugin.interface';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { PluginHeaderComponent } from '../plugin-header/plugin-header.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { CreatePluginBaseComponent } from '@routes/agent-center/app-plugin/create-plugin-base/create-plugin-base';
import { CreateToolComponent } from '@routes/agent-center/app-plugin/create-tool/create-tool';
import { coverPluginInfo, initializeReqItem, pluginSchemaStr2Args, pluginSchemaStr2Path } from '@routes/agent-center/app-plugin/utils';
import { PluginDebugModalComponent } from '@routes/agent-center/app-plugin/components/plugin-debug-modal/plugin-debug-modal.component';
import { WindowResizeService } from '@shared/base/window-resize.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { MessageComponent } from '@shared/services/cfdata.service';
enum mapKeys {
  from = 'from',
  work_space_id = 'work_space_id',
}

@Component({
  selector: 'meta-plugin',
  templateUrl: './plugin.component.html',
  styleUrls: ['./plugin.component.scss'],
  imports: [MODULES, PluginHeaderComponent, NzTableModule, NzButtonModule, NzIconModule, NzDropDownModule, NzTabsModule, NzToolTipModule, NzSpaceModule],
  standalone: true,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.MODEL_ACCESS, I18nNamespace.REVIEW],
    },
    NzModalService,
    NzDrawerService,
  ],
})
export class PluginComponent implements OnInit {
  @ViewChild('ToolDeleteConfirmModal') toolDeleteConfirmModal: TemplateRef<any>;
  deleteContent: any = {};
  displayedData: Array<any> = [];
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  tabConfig = [
    {
      label: this.i18n.transform('plugincomponent_920'),
      active: true,
    },
    {
      label: this.i18n.transform('plugincomponent_921'),
      active: false,
    },
  ];
  srcData: any = {
    state: undefined,
    data: [],
  };
  toolsColumns: Array<any> = [
    {
      title: this.i18n.transform('plugincomponent_922'),
    },
    {
      title: this.i18n.transform('plugincomponent_923'),
    },
    {
      title: this.i18n.transform('plugincomponent_924'),
    },
    {
      title: this.i18n.transform('plugincomponent_925'),
    },
    {
      title: this.i18n.transform('plugincomponent_926'),
    },
    {
      title: this.i18n.transform('operation'),
    },
  ];
  toolsTableFn: Array<any> = this.toolsTableOptionBtn();
  public toolId = '';

  public isLoading = false;

  public name = '--';
  public iamMap = {
    'iam_url': this.i18n.transform('server_address'),
    'iam_domain': this.i18n.transform('account_name'),
    'iam_project': this.i18n.transform('project'),
    'iam_user': this.i18n.transform('iam_username'),
    'iam_password': this.i18n.transform('iam_user_password'),
    'iam_ak': 'Access Key ID',
    'iam_sk': 'Secret Access Key',
  };

  public authMap = {
    'no_auth': this.i18n.transform('no_auth'),
    'API Key': 'API Key',
    'HIS': 'HIS',
    'IAM': 'IAM',
    'SGOV': 'HisSGOV',
    'HIS_IAM': 'HisIAM',
    'CUSTOM_IAM': this.i18n.transform('hw_certificate'),
  };

  public plugin: IPluginWithTools = {} as IPluginWithTools;

  public customIamList = [];
  public lang = CommonUtils.getLanguage();

  public authInfo: {
    type: 'no_auth' | 'API Key' | 'HIS' | 'IAM' | 'SGOV' | 'HIS_IAM' | 'CUSTOM_IAM';
    location?: string;
    params?: {
      name: string;
      value: string;
    }[];
  } = {
    type: 'no_auth',
  };

  public authDisplayedTbd: any[] = [];
  public requestSrcData: any = {
    data: [],
    state: undefined,
  };
  public authTbd: any = {
    data: [],
    state: undefined,
  };

  public responseSrcData: any = {
    data: [],
    state: undefined,
  };

  public res: IResponseArgsView[] = [];

  public req: IRequestArgsView[] = [];

  public path: IRequestArgsView[] = [];

  public previewVersionId = '';

  public previewVersionName = '';

  public isPluginMarket = true;

  private destroy$ = new Subject<void>();
  public windowWidth: number;
  private resizeSub: Subscription;

  public isFromAgentBuilder: boolean = false;
  public isFromDevelopSpace: boolean = false;
  public changeUrl = cdnAssetUrl;
  workSpaceId = '';

  tabSelectIndex = 0;

  constructor(
    private i18n: I18NextEagerPipe,
    private route: ActivatedRoute,
    private appPluginRepoServ: AppPluginRepoService,
    private router: Router,
    private nzDrawerService: NzDrawerService,
    private agentDataServe: AgentDataService,
    private agentRepoServe: AppAgentRepoService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private nzModal: NzModalService,
    private cdr: ChangeDetectorRef,
    private windowResizeService: WindowResizeService,
    private commonService: CommonService,
    private readonly http: HttpService
  ) {
    this.http.getCurrentUserResourceStatus().subscribe(res => {
      this.toolsTableFn = this.toolsTableOptionBtn();
      this.cdr.markForCheck();
    });
    this.toolId = this.route.snapshot.queryParams.id;
    this.isPluginMarket = this.router.url.indexOf('plugin-market/detail') > -1;
    this.agentDataServe
      .getPreviewVersion()
      .pipe(takeUntil(this.destroy$))
      .subscribe(versionInfo => {
        this.previewVersionId = versionInfo?.version_id;
        this.previewVersionName = versionInfo?.version_name;

        if (versionInfo?.version_id) {
          this.getPluginVersion(versionInfo.version_id);
        } else {
          this.getPluginDetails();
        }
      });

    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
      if (params[mapKeys.work_space_id]) {
        this.workSpaceId = params[mapKeys.work_space_id];
      }
    });
  }

  toolsTableOptionBtn(): Array<any> {
    return [
      {
        label: this.i18n.transform('edit'),
        disabled: !this.subscribeBtnStatus,
      },
      {
        label: this.i18n.transform('debugging'),
        disabled: !this.subscribeBtnStatus,
      },
      {
        label: this.i18n.transform('delete'),
        disabled: !this.subscribeBtnStatus,
      },
    ];
  }

  async exitViewHistory() {
    this.agentDataServe.setPreviewVersion(undefined);
  }

  async ngOnInit() {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe(width => {
      this.windowWidth = width;
    });
    const from = this.route.snapshot.queryParams.from;
    if (from === 'agent' || from === 'flow' || from === 'common') {
      this.setCurrentTab(1);
    }
    await this.getPluginDetails();
  }

  ngOnDestroy(): void {
    this.agentDataServe?.setPreviewVersion(undefined);
    this.setSidebarVisibilityService?.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }

  getPluginVersion(version_id) {
    this.agentRepoServe.getPluginVersion(this.toolId, version_id).then(res => {
      this.plugin = res?.data;
      this.coverPluginInfo();
    });
  }

  listDataLoading = false;
  noDataTitle: string = this.i18n.transform('plugincomponent_931');
  noDataDesc: Array<any> = [
    {
      id: 'pligin-desc',
      type: 'html',
      html: this.i18n.transform('plugincomponent_932'),
    },
  ];

  buttons: Array<any> = [
    {
      id: 'item-action',
      type: 'button',
      button: {
        label: this.i18n.transform('plugincomponent_915'),
      },
      click: (): void => {
        this.createTool();
      },
    },
  ];
  coverPluginInfo() {
    this.listDataLoading = true;
    coverPluginInfo(this);
    this.listDataLoading = false;
  }
  async getPluginDetails() {
    this.previewVersionId = '';
    this.previewVersionName = '';
    try {
      this.isLoading = true;
      let value = await this.appPluginRepoServ.getPluginById(this.toolId);
      this.plugin = value.data;
      this.coverPluginInfo();
    } finally {
      this.isLoading = false;
    }
  }

  createTool() {
    if (this.previewVersionId) {
      MessageComponent.showPrompt('预览状态无法操作', 3000);
      return;
    }
    const thisNzModal: any = this.nzModal.create({
      nzContent: CreateToolComponent,
      nzWidth: '1000px',
      nzClosable: true,
    });
    const instance = thisNzModal.getContentComponent();
    instance.pluginInfo = this.plugin;
    instance.lockedStep = 0;
    instance.confirm.subscribe(() => {
      this.getPluginDetails();
    });
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return '800px';
    } else {
      return '600px';
    }
  }

  editTool(toolInfo) {
    const thisNzModal: any = this.nzModal.create({
      nzContent: CreateToolComponent,
      nzWidth: '1000px',
      nzClosable: true,
    });
    const instance = thisNzModal.getContentComponent();
    instance.pluginInfo = this.plugin;
    instance.toolId = toolInfo.tool_id;
    instance.toolInfo = toolInfo;
    instance.lockedStep = 0;
    instance.confirm.subscribe(() => {
      this.getPluginDetails();
    });
  }
  modifyPlugin(stepIndex: number) {
    if (this.previewVersionId) {
      MessageComponent.showPrompt('预览状态无法操作', 3000);
      return;
    }
    if (this.subscribeBtnStatus) {
      const thisNzModal: any = this.nzModal.create({
        nzContent: CreatePluginBaseComponent,
        nzWidth: '1000px',
        nzClosable: true,
      });
      const instance = thisNzModal.getContentComponent();
      instance.pluginInfo = this.plugin;
      instance.pluginId = this.plugin.plugin_id;
      instance.lockedStep = stepIndex;
      instance.confirm.subscribe(() => {
        this.getPluginDetails();
      });
    }
  }

  private getFlatData(nodes: any[], isPath: boolean, level?: number): any[] {
    let result: any[] = [];
    if (!nodes) {
      return result;
    }

    nodes.forEach((item: any): void => {
      item.level = level ? level : 0;
      item.hasChildren = item.children && item.children.length > 0;
      if ((isPath && item.location === 'Path') || (!isPath && item.location !== 'Path')) {
        result.push(item);
      }
      if (item.expand && item.hasChildren) {
        result = result.concat(this.getFlatData(item.children, isPath, item.level + 1));
      }
    });

    return result;
  }

  toggle(node: any, type: 'req' | 'res'): void {
    node.expand = !node.expand;

    if (type === 'req') {
      this.requestSrcData.data = this.getFlatData(this.req, false);
    } else {
      this.responseSrcData.data = this.getFlatData(this.res, false);
    }
  }

  getLevelStyle(node: any): { 'padding-left': string } {
    return {
      'padding-left': `${node.level * 24 + 10}px`,
    };
  }
  getDebuggingStatus(debuggingStatus: number): string {
    switch (debuggingStatus) {
      case 0:
        return this.i18n.transform('flowtasklistcomponent_646');
      case 1:
        return this.i18n.transform('success_1');
      case 2:
        return this.i18n.transform('plugincomponent_936');
      default:
        return this.i18n.transform('plugincomponent_937');
    }
  }
  public openDebugModal(toolInfo) {
    let requestArgs = [...pluginSchemaStr2Args(toolInfo.input_schema), ...pluginSchemaStr2Path(toolInfo.input_schema)];
    const { tool_id, tool_display_name, tool_desc, tool_chinese_name, intf_type, input_schema, output_schema } = toolInfo;
    const { visibility, is_input_list, is_output_list, auth_info, request_info } = this.plugin;
    let pluginBodyParams = {
      plugin_id: this.plugin.plugin_id,
      tool_id,
      tool_display_name,
      tool_desc,
      visibility,
      tool_chinese_name,
      request_info,
      auth_info,
      is_output_list,
      is_input_list,
      intf_type,
      input_schema,
      output_schema,
      icon: undefined,
    };
    const thisNzModal = this.nzModal.create({
      nzContent: PluginDebugModalComponent,
      nzWidth: '1000px',
      nzStyle: { top: '20px' },
      nzOnCancel: () => {
        const instance = thisNzModal.getContentComponent();
        const result = instance.debugResult;
        if (!result) {
          return;
        }

        if (result?.success) {
          toolInfo.test_status = 'SUCCESS';
        }

        if (result?.success === false) {
          toolInfo.test_status = 'FAILED';
        }
        const { protocol, host, path } = pluginBodyParams.request_info.basic_info;
        const cleanToolUrl = toolInfo.path;
        const params = {
          data: {
            ...pluginBodyParams,
            is_input_list: toolInfo.is_input_list,
            is_output_list: toolInfo.is_output_list,
            request_info: {
              method: toolInfo.method,
              url: `${protocol}://${host}${path}${cleanToolUrl}`,
            },
            test_status: toolInfo.test_status,
            plugin_id: this.plugin.plugin_id,
          },
          id: toolInfo.tool_id,
        };
        delete params.data.auth_info;
        this.appPluginRepoServ.updateTool(params).then(res => {
          this.getPluginDetails();
        });
        this.cdr.markForCheck();
      },
    });
    const instance = thisNzModal.getContentComponent();
    instance.hideParseBtn = true;
    instance.requestArgs = requestArgs.map(item => initializeReqItem(item));
    instance.pluginBodyParams = pluginBodyParams;
  }
  openToolDeleteConfirmModal(tool) {
    const thisNzModal: any = this.nzModal.create({
      nzContent: this.toolDeleteConfirmModal,
      nzWidth: '1000px',
      nzOnOk: () => {
        this.isLoading = true;
        this.appPluginRepoServ
          .deleteTool(this.plugin.plugin_id, tool.tool_id)
          .then(res => {
            this.getPluginDetails();
          })
          .finally(() => {
            this.isLoading = false;
          });
        thisNzModal.destroy();
      },
    });

    this.deleteContent.toolName = tool.toolDisplayname;
    this.deleteContent.toolDependency = tool.toolDependency;
  }
  goDetail(row) {
    if (this.previewVersionId) {
      MessageComponent.showPrompt('预览状态无法操作', 3000);
      return;
    }
    let queryParams = {
      plugin_id: this.plugin.plugin_id,
      tool_id: row.tool_info.tool_id,
    };
    if (this.isFromDevelopSpace) {
      queryParams[mapKeys.from] = 'develop-space';
    }
    const routeQueryParams = this.route.snapshot.queryParams;
    let _queryParams: Record<string, string> = {};
    if (routeQueryParams.from === 'agentBuilder') {
      Object.keys(routeQueryParams).forEach((key: string) => {
        if (key === 'from' || key === 'work_space_id') {
          _queryParams[key] = routeQueryParams[key];
        }
      });
    }
    this.router.navigate(['/home/agent-center/custom-plugin/tool/detail'], {
      queryParams: {
        ...queryParams,
        ..._queryParams,
      },
    });
  }
  handleToolsAction(item: any, row: any) {
    if (this.previewVersionId) {
      MessageComponent.showPrompt('预览状态无法操作', 3000);
      return;
    }
    if (item.label === this.i18n.transform('edit')) {
      this.editTool(row.tool_info);
    } else if (item.label === this.i18n.transform('debugging')) {
      this.openDebugModal(row.tool_info);
    } else if (item.label === this.i18n.transform('delete')) {
      this.openToolDeleteConfirmModal(row);
    } else if (item.label === this.i18n.transform('plugincomponent_938')) {
      let queryParams = {
        plugin_id: this.plugin.plugin_id,
        tool_id: row.tool_info.tool_id,
      };
      if (this.workSpaceId) {
        queryParams[mapKeys.work_space_id] = this.workSpaceId;
      }
      if (this.isFromDevelopSpace) {
        queryParams[mapKeys.from] = 'develop-space';
      }
      if (this.isFromAgentBuilder) {
        queryParams[mapKeys.from] = 'agentBuilder';
      }
      this.router.navigate(['/home/agent-center/custom-plugin/tool/detail'], {
        queryParams: queryParams,
      });
    }
  }
  setCurrentTab(tabId: number) {
    this.tabConfig.forEach((tab, index) => {
      tab.active = index === tabId;
    });
    this.tabSelectIndex = this.tabConfig.findIndex(item => item.active);
  }
}
