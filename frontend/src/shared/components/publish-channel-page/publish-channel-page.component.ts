import { Clipboard } from '@angular/cdk/clipboard';
import { ChangeDetectorRef, Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { StorageService } from '@shared/services/cfdata.service';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzModalService } from 'ng-zorro-antd/modal';
import { HelpDocKey } from '@constants/support-topic.const';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { IMemoParamExt } from '@routes/agent-center/app-agent/components/preview-memos/preview-memos.component';
import { PublishAgentModalComponent } from '@routes/agent-center/app-agent/components/publish-agent-modal/publish-agent-modal.component';
import { PublishFlowModalComponent } from '@routes/agent-center/app-agent/components/publish-flow-modal/publish-flow-modal.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { AppAgentDeploymentService } from '@services/agent-observatory/app-agent-deployment.service';
import { ContextService } from '@services/context.service';
import { MODULES } from '@shared/modules';
import { HelpLinksService } from '@shared/services/help-links.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { environment } from 'src/environment/environment';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonUtils } from 'src/utils/common.util';
import { PipesModule } from '../../../pipes/pipes.module';
import { APICallPageComponent } from '../API-call-page/API-call-page.component';
import { DeleteChannelModalComponent } from '../delete-channel-modal/delete-channel-modal.component';
import { UpdateVersionModalComponent } from '../update-version-modal/update-version-modal.component';
import {NzMessageService} from "ng-zorro-antd/message";

enum mapKeys {
  VISIBILITY_SCOPE = 'visibility_scope',
  CALL_COUNT = 'call_count',
  from = 'from',
}

@Component({
  selector: 'publish-channel-page',
  templateUrl: './publish-channel-page.component.html',
  styleUrls: ['./publish-channel-page.component.scss'],
  standalone: true,
  imports: [MODULES, APICallPageComponent, PipesModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT,
        I18nNamespace.AGENT_CENTER,
      ],
    },
  ],
})
export class PublishChannelPageComponent {
  @Input() publishParams = {
    agentId: '',
    workflowId: '',
    from: '',
    workflowType: 'chat',
  };

  public tabs: any = [
    { title: this.i18n.transform('release_management'), active: true },
    { title: this.i18n.transform('api_call'), active: false },
  ];

  public channelData: any = {
    data: [] as IMemoParamExt[],
    state: undefined,
  };

  public isPOC = environment.envType === 'poc';
  public displayedData: any[] = [];
  public lang = CommonUtils.getLanguage();
  public columns: any[] = [
    {
      title: this.i18n.transform('share_chanel'),
      width: '30%',
    },
    {
      title: this.i18n.transform('status'),
      width: '10%',
    },
    {
      title: this.i18n.transform('version'),
      width: '10%',
    },
    {
      title: this.i18n.transform('is_update_version'),
      width: '8%',
    },
    {
      title: this.i18n.transform('link_address'),
      width: '22%',
    },
    {
      title: this.i18n.transform('operation'),
      width: '20%',
    },
  ];
  public tableData: any = [];
  public transferTableData: any = [
    {
      type: 'WEB_PAGE',
      icon: cdnAssetUrl('assets/agent-center/images/api.svg'),
      name: 'API',
      desc: this.i18n.transform('api_sdk_tip'),
      status: this.i18n.transform('unpublished'),
      statusIcon: 'active',
      publish_time: '',
    },
  ];
  public fullScreenIcon = cdnAssetUrl(
    'assets/agent-center/images/full-screen.svg',
  );
  public exitFullScreenIcon = cdnAssetUrl(
    'assets/agent-center/images/exit-full-screen.svg',
  );
  public isLoading = false;
  public isOpAccount = false;
  public isFromAgentBuilder = false;
  public web_page_enable =
    this.configServ.getConfigs()?.web_page_enable ?? false;

  public pageType: 'agents' | 'workflows' = 'agents';
  public id = '';
  public versionId = '';
  public isF1 = this.ctxServ.isF1ReqList();
  private typeTabs: any;
  // 是否来自于开发者空间
  private isFromDevelopSpace: boolean = false;
  // 获取配置文件
  public config: any;
  public changeUrl = cdnAssetUrl;
  public resourceConfigOptions = [
    {
      id: 'ALL',
      label: this.i18n.transform('all_tenants_available'),
      value: 'ALL',
    },
    {
      id: 'TENANT',
      label: this.i18n.transform('current_tenant_available'),
      value: 'TENANT'
    },
  ];
  resourceConfigData = {
    configOptions: this.resourceConfigOptions[0],
    isShow: false,
    left: 0,
    top: 0,
    selectedWebPageData: {
      call_count: 100,
      visibility_scope: this.resourceConfigOptions[0].id,
      channel_id: '',
      version_id: '',
    },
    times: 1,
    isLoading: false,
  };
  public isHcs: boolean = false; // 是否是hcs环境
  public isHc: boolean = false; // 是否是hc环境
  public isHalfModelExpand = false; // 是否展开半页屏
  public drawerVisible = false; // drawer可见性
  public drawerWidth = 1000; // drawer展开后的宽度
  private drawerRef: NzDrawerRef; // 当前打开的drawer引用
  runtime_api_endpoint_prefix = '';
  isDeepResearch: boolean = false;
  public rightSidebarWidth = 0; // 右侧栏宽度
  public isMultiAgent = false; // 是否为多智能体
  constructor(
    private router: Router,
    private agentRepoServe: AppAgentRepoService,
    private ctxServ: ContextService,
    private clipboard: Clipboard,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private agentDeploymentService: AppAgentDeploymentService,
    private appAgentRepoService: AppAgentRepoService,
    private appFlowRepoServ: AppFlowRepoService,
    private helpLinksService: HelpLinksService,
    private nzDrawerService: NzDrawerService,
    private nzModal: NzModalService,
    private message: NzMessageService
  ) {}

  ngOnInit() {
    this.initFn();
  }

  public expandModel() {
    this.isHalfModelExpand = !this.isHalfModelExpand;
    if (this.isHalfModelExpand) {
      const sidebarEl = document?.querySelector('#J_rightSidebar .js-cf-rightSidebar') as HTMLElement | null;
      this.rightSidebarWidth = sidebarEl?.offsetWidth || 0;
      this.drawerWidth = window.innerWidth - this.rightSidebarWidth;
    } else {
      this.drawerWidth = 1000;
    }
    this.cdr.markForCheck();
  }
  public async initFn() {
    this.isOpAccount = this.ctxServ.isOpAccount;
    this.isHcs = false;
    this.isHc = false;
    this.id = this.publishParams.agentId || this.publishParams.workflowId;
    if (
      this.publishParams.from &&
      this.publishParams.from === 'develop-space'
    ) {
      this.isFromDevelopSpace = true;
    }

    if (this.publishParams.from && this.publishParams.from === 'agentBuilder') {
      this.isFromAgentBuilder = true;
    }

    if (
      this.publishParams.agentId ||
      this.publishParams.workflowType === 'controller'
    ) {
      this.pageType = 'agents';
      this.isMultiAgent = this.publishParams.workflowType === 'controller';
    } else {
      this.pageType = 'workflows';
    }
    if (this.publishParams.from !== 'agentBuilder') {
      this.getShowAlert();
    }
    this.config = this.configServ.getConfigs();
    !this.isMultiAgent && this.initTableData();
    if (this.id && this.pageType === 'agents') {
      const res: any = await this.appAgentRepoService.fetchAgentDetail(this.id);
      if (res.sub_type === 'deepresearch') {
        this.isDeepResearch = true;
      }
      this.transferTableData[0].publish_time = res?.publish_time;
      this.transferTableData[0].status = this.i18n.transform(
        res?.status === 'published' ? 'published' : 'unpublished',
      );
    }
    if (
      this.id &&
      this.pageType === 'workflows'
    ) {
      const res: any = await this.appFlowRepoServ.getFlow(this.id);
      this.transferTableData[0].publish_time = res?.publish_time;
      this.transferTableData[0].status = this.i18n.transform(
        res?.status === 1 ? 'published' : 'unpublished',
      );
    }
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    this.initData();
  }
  alertShow = false;
  alertShowTip = this.configServ.getConfigs().agentops_deploy_display;
  getShowAlert() {
    try {
      if (this.alertShowTip) {
        let param = {
          pageNo: 1,
          pageSize: 10,
          keyword: this.publishParams.agentId || this.publishParams.workflowId,
        };
        this.agentDeploymentService
          .getAgentDeploymentList(param)
          .then((res: any) => {
            this.alertShow = res.items.length === 0;
          });
      }
    } catch (e) {}
  }

  /** 发布按钮 */
  public publish(item) {
    if (item.type !== 'APP_STORE') {
      // 网页版发布
      const params = {
        version_id: item.latest_version_id,
        channel_type: item.type,
      };
      if (item.type === 'WEB_PAGE') {
        params[mapKeys.CALL_COUNT] = 100;
        params[mapKeys.VISIBILITY_SCOPE] = 'TENANT';
      }
      this.agentRepoServe
        .publishVersionForChannel(this.pageType, this.id, params)
        .then(() => {
          this.message.create('success', `${this.i18n.transform('published_to')}${item.name}`);
          this.getPublishChannelList();
        });
    } else {
      // 应用百宝箱发布
      this.openPublishAppStoreModal(item.latest_version_id);
    }
  }

  /** 更新版本按钮 */
  public updateVersion(item) {
    const modalRef = this.nzModal.create({
      nzTitle: '',
      nzContent: UpdateVersionModalComponent,
      nzWidth: 400,
      nzFooter: null,
      nzClosable: false,
    });
    modalRef.componentInstance.close = (): void => {
      modalRef.close();
      if (item.type === 'APP_STORE') {
        this.editConfig(item, true);
      } else {
        this.updateVersionChannel(item);
      }
    };
  }

  deploy() {
    this.router.navigate(['/home/agent-observatory/agentDeployment']);
  }

  updateVersionChannel(item) {
    this.agentRepoServe
      .updateVersionChannel(
        this.pageType,
        this.id,
        item.channel_id,
        item.latest_version_id,
      )
      .then(() => {
        this.message.create('success', this.i18n.transform('channel_updated_latest'));
        this.getPublishChannelList();
      });
  }

  /** 立即访问按钮 */
  public visitNow(item) {
    const cur_space_options_str =
      StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
    let cur_space_options: any = {};
    if (cur_space_options_str) {
      cur_space_options = JSON.parse(
        StorageService.getSessionStorage('CUR_SPACE_OPTIONS'),
      );
    }
    if (item.type === 'WEB_PAGE') {
      window.open(
        `${item.link}?workspace_id=${cur_space_options?.id}`,
        '_blank',
      );
    } else if (item.type === 'CLOUD_STORE') {
      window.open(item.link, '_blank');
    } else {
      window.open(this.openAppInNewTab(item), '_blank');
    }
  }

  /** 修改配置按钮 */
  public editConfig(item, isUpdated?) {
    this.typeTabs = this.typeTabs?.map((item: any) => ({
      ...item,
      selected: item.metadata?.includes(item.tag_id),
    }));
    if (this.pageType === 'workflows') {
      const drawerRef = this.nzDrawerService.create({
        nzTitle: '',
        nzPlacement: 'right',
        nzWidth: 700,
        nzClosable: false,
        nzMaskClosable: false,
        nzMask: false,
        nzContent: PublishFlowModalComponent,
        nzContentParams: {
          workflowId: this.id,
          tagList: this.typeTabs,
          versionId: isUpdated ? item.latest_version_id : item.version_id,
        },
      });
      const instance = drawerRef.getContentComponent();
      instance.confirm.subscribe(async (params) => {
        await this.updateFlowAppConfig(params, item.version_id);
        this.message.create('success', `${this.i18n.transform('published_to')}${this.i18n.transform(
          'application_box',
        )}`);
        if (isUpdated) {
          this.updateVersionChannel(item);
        }
        drawerRef.close();
      });
    } else {
      const modalRef = this.nzModal.create({
        nzTitle: '',
        nzContent: PublishAgentModalComponent,
        nzWidth: 400,
        nzFooter: null,
        nzClosable: false,
      });
      const instance = modalRef.getContentComponent();
      instance.tagList = this.typeTabs;
      instance.close = (): void => {
        const { tagsSelected } = instance;
        const params = {
          version_id: item.latest_version_id,
          channel_type: 'APP_STORE',
          metadata: tagsSelected,
        };
        modalRef.close();
        this.agentRepoServe
          .publishVersionForChannel(this.pageType, this.id, params)
          .then(
            () => {
              this.message.create('success', this.i18n.transform('app_category_updated'));
              this.getPublishChannelList();
            },
            () => {
              // 恢复所有tags的selected属性为false
              this.typeTabs?.forEach((tag: any) => {
                tag.selected = false;
              });
            },
          );
      };
    }
  }

  showManage(item, content) {
    const modalRef = this.nzModal.create({
      nzTitle: `${this.i18n.transform('manage')}-${item.name}`,
      nzContent: content,
      nzWidth: 500,
      nzFooter: null,
      nzClosable: true,
    });
  }

  /** 停止分发按钮 */
  public stopDistribution(item) {
    const modalRef = this.nzModal.create({
      nzTitle: '',
      nzContent: DeleteChannelModalComponent,
      nzWidth: 400,
      nzFooter: null,
      nzClosable: false,
    });
    const instance = modalRef.getContentComponent();
    instance.name = item.name;
    instance.type = 'APP_STORE';
    instance.close = (): void => {
      this.agentRepoServe
        .deleteVersionChannel(this.pageType, this.id, item.channel_id)
        .then(() => {
          this.message.create('success', this.i18n.transform('app_distribution_stopped'));
          this.getPublishChannelList();
        });
      modalRef.close();
    };
  }

  /** 复制链接按钮 */
  public copyUrl(link: string) {
    const cur_space_options_str =
      StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
    let cur_space_options: any = {};
    if (cur_space_options_str) {
      cur_space_options = JSON.parse(
        StorageService.getSessionStorage('CUR_SPACE_OPTIONS'),
      );
    }
    // 带workspace_id 会报空间不存在
    this.clipboard.copy(`${link}`);
    this.message.create('success', this.i18n.transform('copy_successful'));
  }

  /** 重新生成按钮 */
  public regenerate(version_id: string) {
    const params = {
      version_id,
      channel_type: 'WEB_PAGE',
      call_count: 100,
      visibility_scope: 'TENANT',
    };
    this.agentRepoServe
      .publishVersionForChannel(this.pageType, this.id, params)
      .then(() => {
        this.message.create('success', this.i18n.transform('app_regenerated'));
        this.getPublishChannelList();
      });
  }

  /** 打开发布到应用百宝箱的分类弹窗 */
  private openPublishAppStoreModal(latest_version_id: string) {
    // 重置tagList的选中状态，默认选中"通用"分类
    this.typeTabs = this.typeTabs?.map((item) => ({
      ...item,
      selected: item?.name === this.i18n.transform('universal'),
    }));
    if (this.pageType === 'workflows') {
      const drawerRef = this.nzDrawerService.create({
        nzTitle: '',
        nzPlacement: 'right',
        nzWidth: 700,
        nzClosable: false,
        nzMaskClosable: false,
        nzMask: false,
        nzContent: PublishFlowModalComponent,
        nzContentParams: {
          workflowId: this.id,
          tagList: this.typeTabs,
          versionId: latest_version_id,
        },
      });
      const instance = drawerRef.getContentComponent();
      instance.confirm.subscribe(async (params) => {
        await this.updateFlowAppConfig(params, latest_version_id);
        this.message.create('success', `${this.i18n.transform('published_to')}${this.i18n.transform(
          'application_box',
        )}`);
        this.getPublishChannelList();
        drawerRef.close();
      });
    } else {
      const modalRef = this.nzModal.create({
        nzTitle: '',
        nzContent: PublishAgentModalComponent,
        nzWidth: 400,
        nzFooter: null,
        nzClosable: false,
      });
      const instance = modalRef.getContentComponent();
      instance.tagList = this.typeTabs;
      instance.close = (): void => {
        const { tagsSelected } = instance;
        const params = {
          version_id: latest_version_id,
          channel_type: 'APP_STORE',
          metadata: tagsSelected,
        };
        modalRef.close();
        this.agentRepoServe
          .publishVersionForChannel(this.pageType, this.id, params)
          .then(
            () => {
              this.message.create('success', `${this.i18n.transform('published_to')}${this.i18n.transform(
                'application_box',
              )}`);
              this.getPublishChannelList();
            },
            () => {
              // 恢复所有tags的selected属性为false
              this.typeTabs?.forEach((tag: any) => {
                tag.selected = false;
              });
            },
          );
      };
    }
  }

  updateFlowAppConfig(params, version_id) {
    const { tagsSelected, inputs, outputs, prologue, suggest_queries } = params;
    const param = {
      version_id: version_id,
      channel_type: 'APP_STORE',
      metadata: tagsSelected,
      inputs: inputs,
      outputs: outputs,
      prologue,
      suggest_queries,
    };
    return this.agentRepoServe.publishVersionForChannel(
      this.pageType,
      this.id,
      param,
    );
  }

  async initData() {
    this.isLoading = true;
    await this.getTagsInfo();
    this.getPublishChannelList();
    this.isLoading = false;
    this.cdr.markForCheck();
  }

  private getTagsInfo() {
    return this.agentRepoServe.getTagList().then((res: any) => {
      this.typeTabs = res?.map((item: any) => ({
        ...item,
        selected: item?.name === this.i18n.transform('universal'),
      }));
      this.cdr.markForCheck();
    });
  }

  private getPublishChannelList() {
    this.isLoading = true;
    this.agentRepoServe
      .getPublishChannels(this.pageType, this.id)
      .then((result) => {
        this.isLoading = false;
        this.updateTableData(result);
        this.cdr.markForCheck();
      })
      .catch(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  private updateTableData(result: any): void {
    this.versionId = result?.latest_version_id;
    this.tableData.forEach((item: any) => {
      const channel = result?.channel_list?.find(
        (channel: any) => channel.channel_type === item.type,
      );
      if (channel) {
        item.latest_version_id = result?.latest_version_id;
        item.status = this.i18n.transform('published');
        item.statusIcon = 'active';
        item.release_time = channel.release_time || '--';
        item.version_name = channel.version_name;
        item.call_count =
          channel.call_count === 0 ? 0 : channel.call_count || 100;
        this.resourceConfigData.selectedWebPageData.call_count =
          item.call_count;
        item.visibility_scope = channel.visibility_scope || 'TENANT';
        const filterData = this.resourceConfigOptions.filter(
          (_item) => _item.id === channel.visibility_scope,
        );
        if (filterData.length > 0) {
          this.resourceConfigData.configOptions = filterData[0];
        } else {
          this.resourceConfigData.configOptions = this.resourceConfigOptions[1];
        }
        // 判断是否为"最新版本"还是"有新版本"
        item.isUpdated = parseInt(result.latest_version_id) > parseInt(channel.version_id);
        if (channel?.short_code) {
          if (channel?.channel_type === 'WEB_PAGE') {
            item.link = this.getWebPageUrl(channel.short_code);
          } else {
            item.url = this.getStorePageLink();
            item.link = this.getStorePageUrl(channel.short_code);
          }
        }
        item.channel_id = channel.id;
        item.version_id = channel.version_id;
        item.metadata = channel?.metadata;
        item.entry_point = channel.entry_point;
        item.short_code = channel.short_code;
        item.tagList = this.typeTabs?.filter((item) =>
          channel?.metadata?.includes(item.tag_id),
        );
        item.app_id = channel?.app_id;
      } else {
        item.latest_version_id = result?.latest_version_id;
        item.status = this.i18n.transform('unpublished');
        item.statusIcon = 'cancel';
        item.release_time = '';
        item.version_name = '';
        item.isUpdated = false;
        item.channel_id = '';
        item.version_id = '';
        item.metadata = [];
        item.tagList = [];
        item.url = '';
        item.call_count = 100;
        item.visibility_scope = 'TENANT';
        this.resourceConfigData.configOptions = this.resourceConfigOptions[1];
      }
    });
  }

  /** 在新的Tab页签，体验已发布应用的网页版 */
  private getWebPageUrl(short_code: string) {
    const url = window.location.href?.split('/home');
    const prefixUrl = url[0];

    if (this.pageType === 'workflows') {
      // 工作流任务型跳转
      if (this.publishParams.workflowType === 'task') {
        return `${prefixUrl}/home/app-library/scenario-bot/web-page/${short_code}`;
      }
      // 工作流对话型跳转
      return `${prefixUrl}/home/chat/flow/${short_code}`;
    }
    // agent
    return `${prefixUrl}/home/chat/${short_code}`;
  }

  /** 在新的Tab页签，体验已发布云商店的网页版 */
  private getStorePageLink() {
    this.runtime_api_endpoint_prefix =
      this.configServ.getConfigs()?.runtime_api_endpoint_prefix ?? '';
    let projectId = this.ctxServ.projectId;
    let host = `https://${this.runtime_api_endpoint_prefix}`;
    let path = `/v1/${projectId}/${this.pageType}/${
      this.id
    }/conversations/{conversation_id}?${
      this.isDeepResearch ? 'agent_type=deepresearch&' : ''
    }version=${this.versionId}`;
    return `${host}${path}`;
  }

  /** 在新的Tab页签，体验已发布云商店的网页版 */
  private getStorePageUrl(short_code: string) {
    let location = window.location;
    const url = location.href?.split('/home');
    let prefixUrl = url[0];
    prefixUrl = prefixUrl.replace(
      location.origin + location.pathname,
      location.origin + '/marketplace/tenant/',
    );
    return `${prefixUrl}/market/order/purchasedProducts/${short_code}`;
  }
  /** 在新的Tab页签，体验已发布应用的对话型应用 */
  private openAppInNewTab(item) {
    const url = window.location.href?.split('/home');
    const prefixUrl = url[0];
    const queryParams = `?appId=${item.app_id}&versionId=${item.latest_version_id}`;
    if (this.pageType === 'workflows') {
      if (this.publishParams.workflowType === 'task') {
        return `${prefixUrl}/home/app-library/scenario-bot/scene/${item.app_id}`;
      }

      return `${prefixUrl}/home/app-library/flow/knowledge-bot${queryParams}`;
    }
    return `${prefixUrl}/home/app-library/knowledge-bot${queryParams}`;
  }

  /** 获取云商店的提示 */
  private getCloudChannelTip() {
    const url = this.helpLinksService.getHelpCenterLink(
      HelpDocKey.CHANNEL_CLOUD_STORE,
    );
    if (url) {
      return `<a href="${url}" tiNavIcon target="_blank" class="link-icon" rel="noopener noreferrer">${this.i18n.transform(
        'cloud_shop_tip',
      )} </a>`;
    }
    return '';
  }

  /**
   * poc环境可以使用网页版和应用百宝箱
   */
  private initTableData() {
    // 网页版
    const webChannel = [
      {
        type: 'WEB_PAGE',
        icon: cdnAssetUrl('assets/agent-center/images/web-page.svg'),
        name: this.i18n.transform('webpage'),
        desc: this.i18n.transform('web_page_desc'),
      },
    ];

    const cloudChannel = [
      {
        type: 'CLOUD_STORE',
        icon: cdnAssetUrl('assets/agent-center/images/app-store.svg'),
        name: this.i18n.transform('cloud_store'),
        desc: this.i18n.transform('openapi_url_in_cloud_store'),
        tip: this.getCloudChannelTip(),
      },
    ];

    // 微信相关
    const wechatChannels = [
      {
        type: 'WECHAT_MINI_PROGRAM',
        icon: cdnAssetUrl('assets/agent-center/images/mini-program.svg'),
        name: this.i18n.transform('wechat_mini_program'),
        desc: this.i18n.transform('wechat_mini_program_desc'),
      },
      {
        type: 'WECHAT_OFFICIAL_ACCOUNTS',
        icon: cdnAssetUrl('assets/agent-center/images/WeChat.svg'),
        name: this.i18n.transform('wechat_official_account'),
        desc: this.i18n.transform('wechat_official_account_desc'),
      },
    ];

    // 应用百宝箱
    const appChannel = [
      {
        type: 'APP_STORE',
        icon: cdnAssetUrl('assets/agent-center/images/app-store.svg'),
        name: this.i18n.transform('application_box'),
        desc: this.i18n.transform('app_box_desc'),
      },
    ];

    const env = environment.envType; // HC/HCS/HCSO/POC环境
    const channels = [];

    // 网页发布渠道：F1 或 web_page_enable配置开启 || this.web_page_enable
    if (this.isF1 || true) {
      channels.push(...webChannel);
    }

    if (env === 'hc') {
      channels.push(...cloudChannel);
    }

    // 微信相关：仅 F1 能看
    if (this.isF1) {
      channels.push(...wechatChannels);
    }

    if (
      this.configServ.getConfigs()?.env_publish_app_store_enable &&
      this.ctxServ.isOpAccount
    ) {
      channels.push(...appChannel);
    }
    this.tableData = channels;
  }

  handleClickResourceConfigBtn(event: MouseEvent, data: any) {
    this.resourceConfigData.isShow = !this.resourceConfigData.isShow;
    const filterData = this.resourceConfigOptions.filter(
      (_item) => _item.id === data.visibility_scope,
    );
    if (filterData.length > 0) {
      this.resourceConfigData.configOptions = filterData[0];
    } else {
      this.resourceConfigData.configOptions = this.resourceConfigOptions[1];
    }

    this.resourceConfigData.selectedWebPageData.call_count = data.call_count;
    this.resourceConfigData.selectedWebPageData.visibility_scope =
      this.resourceConfigData.configOptions.id;
    this.resourceConfigData.selectedWebPageData.channel_id = data.channel_id;
    this.resourceConfigData.selectedWebPageData.version_id = data.version_id;

    this.resourceConfigData.left = event.clientX + 5;
    this.resourceConfigData.top = event.clientY + 20;
  }

  // 判断调用次数是不是正数
  isPositiveNumber(str: any): boolean {
    return /^(10000|[1-9]\d{0,3}|0)$/.test(str) || str === '-1' || str === -1;
  }

  handleClickUpdateResourceConfig() {
    this.resourceConfigData.selectedWebPageData.visibility_scope =
      this.resourceConfigData.configOptions.id;
    const params = {
      call_count: this.resourceConfigData.selectedWebPageData.call_count,
      visibility_scope:
        this.resourceConfigData.selectedWebPageData.visibility_scope,
      version_id: this.resourceConfigData.selectedWebPageData.version_id,
    };
    this.resourceConfigData.isLoading = true;
    this.agentRepoServe
      .updateSourceConfigForChannel(
        this.id,
        this.pageType,
        this.resourceConfigData.selectedWebPageData.channel_id,
        params,
      )
      .then(() => {
        this.resourceConfigData.isLoading = false;
        this.resourceConfigData.isShow = false;
        this.message.create('success', this.i18n.transform('config_update_success'));
        this.getPublishChannelList();
      })
      .catch(() => {
        this.resourceConfigData.isLoading = false;
      });
  }

  handleClickCancelSourceConfig() {
    this.resourceConfigData.isShow = false;
  }

  showApiInfo() {
    this.isHalfModelExpand = false;
    this.drawerVisible = true;
  }

  closeHalfModel() {
    this.drawerVisible = false;
  }
}
