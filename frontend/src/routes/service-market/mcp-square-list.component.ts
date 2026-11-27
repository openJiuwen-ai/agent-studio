import { Component, OnInit } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { McpCardComponent } from './mcp-card/mcp-card.component';
import { McpAllService } from './mcp-all.service';
import { CommonUtils } from '../../utils/common.util';
import { MessageComponent } from '@shared/services/cfdata.service';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { CommonService } from '@services/common.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { PromptService } from '@services/prompt.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { PublishAssetModalComponent } from '@routes/agent-center/component-library/shelf-modal/publish-asset-modal.component';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { ContextService } from '@services/context.service';

enum mapKeys {
  language = 'language',
  category = 'category',
  offset = 'offset',
  limit = 'limit',
  name = 'name'
}
const OTHER_HEIGHT = 252;
const MAX_HEIGHT = 1270;

@Component({
  selector: 'mcp-square-list',
  templateUrl: './mcp-square-list.component.html',
  styleUrls: ['./mcp-square-list.component.less'],
  standalone: true,
  imports: [
    MODULES,
    McpCardComponent,
    NewCommonNoDataWithBtnComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.PLATFORM_MANAGEMENT],
    },
  ],
})
export class McpSquareListComponent implements OnInit {
  public canPublish = true;
  tabs: any = [
    {
      title: this.i18n.transform('platform_selection_1'),
      active: this.mcpAllService.tabPageType === 'official',
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.thirdCurrentPage = 1;
          this.officialCurrentPage = 1;
          this.mcpAllService.tabPageType = 'official';
          this.getOfficialCardData();
        }
      },
    },
    {
      title: this.i18n.transform('third_party_1'),
      active: this.mcpAllService.tabPageType === 'third',
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.thirdCurrentPage = 1;
          this.officialCurrentPage = 1;
          this.mcpAllService.tabPageType = 'third';
          this.getSquareThirdCardData();
        }
      },
    },
  ];

  public officialSearchName: string = '';
  public officialCurrentPage: number = 1;
  public officialPageSize: any = {
    options: [24, 48, 64],
    size: 24,
  };
  officialCardData = [];
  officialTotal = 0;
  officialLoading = false;

  public thirdSearchName: string[] = [];
  public thirdCurrentPage: number = 1;
  public thirdPageSize: any = {
    options: [24, 48, 64],
    size: 24,
  };
  thirdCardData = [];
  thirdTotal = 0;
  thirdLoading = false;

  appTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform('all'),
      name_en: 'all',
      id: 'all',
      active: true,
      description: '',
      library_type: '',
      created_on: 0,
      updated_on: 0,
    }
  ];
  // 无数据状态提示
  noDataTitle: string = this.i18n.transform('no_env_data');
  noDataDesc: Array<any> = [
    {
      type: 'html',
      html: this.i18n.transform('no_env_data_tip'),
    },
  ];

  public lang: string = '';

  // 第三方下拉框选项
  thirdOptions: any[] = [];
  thirdValue: any = null;
  hasMore = true;

  public placeholderStr: string = this.i18n.transform('select-resource-type');
  private selectedTagId: string = '';

  pageTitle = this.i18n.transform('all');

  get totalCount() {
    if (this.officialSearchName.length === 0 && this.officialTotal === 0) {
      return '';
    }
    return ` (${this.officialTotal})`;
  }

  get thirdTotalCount() {
    if (this.thirdSearchName.length === 0 && this.thirdTotal === 0) {
      return '';
    }
    return ` (${this.thirdTotal})`;
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private mcpAllService: McpAllService,
    public commonService: CommonService,
    public promptService: PromptService,
    private sidebarServ: SetSidebarVisibilityService,
    private nzModal: NzModalService,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private ctxServ: ContextService,
  ) {
    this.lang = CommonUtils.getLanguage();
  }

  openPublishModal(): void {
    this.nzModal.create({
      nzContent: PublishAssetModalComponent,
      nzWidth: 560,
      nzTitle: this.i18n.transform('plaza_onshelf'),
      nzFooter: null,
      nzData: {
        assetType: 'mcp',
        onPublished: () => {
          // 上架成功后重置到第一页刷新（getOfficialCardData 为滚动分页，直接调用会按旧页码拉取不生效）
          this.officialCurrentPage = 1;
          this.officialCardData.length = 0;
          this.officialTotal = 0;
          this.getOfficialCardData();
        },
      },
    });
  }

  async checkPublishPermission() {
    try {
      const res = await this.spaceTeamManagementService.getWorkspaceDetial(this.ctxServ.currentWorkspaceId);
      if (res?.type === 'TEAM' && res?.role && res.role !== 'OWNER' && res.role !== 'ADMIN') {
        this.canPublish = false;
      }
    } catch {
      this.canPublish = false;
    }
  }

  ngOnInit() {
    this.sidebarServ.setSidebarsVisibilityByState('hideSidebar');
    this.checkPublishPermission();
    this.initThirdOptions();
    this.getMcpTagData();
    this.getOfficialCardData();
    if (this.mcpAllService.tabPageType === 'third') {
      this.getSquareThirdCardData();
    }
  }

  ngOnDestroy(): void {
    this.sidebarServ.setSidebarsVisibilityByState('destroy');
  }

  private getMcpTagData() {
    const params = {
      library_type: 'mcp'
    }
    this.promptService.getAssertTagAsync(params).then(
      (response) => {
        const firstTab = this.appTabs[0];
        this.appTabs.length = 0;
        this.appTabs.push(firstTab);
        for (let index = 0; index < response.length; index++) {
          this.appTabs.push(response[index]);
        }
      }
    ).catch()
  }

  get activeTabIsOfficial() {
    return this.mcpAllService.tabPageType === 'official';
  }

  changeAppTab(data: AssertSquareTagType) {
    if (data.active) {
      this.officialCurrentPage = 1;
      this.officialCardData = [];
      this.officialTotal = this.officialCardData.length;
      if (data.id === 'all') {
        this.selectedTagId = '';
      } else {
        this.selectedTagId = data.id;
      }
      this.pageTitle = this.lang === 'zh-cn' ? data.name : data.name_en;
      this.getOfficialCardData();
    }
  }

  // 初始化第三方选项
  initThirdOptions() {
    this.thirdOptions = [
      {
        label: this.i18n.transform('all_sources'),
        key: '',
      },
      {
        label: 'ROMA Connect',
        key: 'ROMA',
      },
      {
        label: this.i18n.transform('jiuwen_cloud_store'),
        key: 'kooGallery',
      },
    ];

    // 设置默认值
    if (!this.thirdValue) {
      this.thirdValue = this.thirdOptions[0];
    }
  }

  // 刷新官方预置数据
  refreshOfficialCardData() {
    this.officialSearchName = '';
    this.officialOnSearch();
  }


  // 官方预置
  getOfficialCardData() {
    this.officialLoading = true;
    const query = {};
    let isDisableSearch = false;
    if (window.innerHeight - OTHER_HEIGHT > MAX_HEIGHT) {
      this.officialPageSize.size = this.officialPageSize.options[1];
    } else {
      this.officialPageSize.size = this.officialPageSize.options[0];
    }
    if (this.selectedTagId) {
      query[mapKeys.category] = this.selectedTagId;
    }
    if (this.officialSearchName.length > 0) {
      query[mapKeys.language] = this.isZH() ? 'ZH' : 'EN';
      if (!this.validateUserInput(this.officialSearchName)) {
        isDisableSearch = true;
      }
      query[mapKeys.name] = this.officialSearchName;
    }
    if (isDisableSearch) {
      MessageComponent.showError(this.i18n.transform('support_char_types'), 3000);
      this.officialLoading = false;
      return;
    }
    const params = {
      offset: (this.officialCurrentPage - 1) * this.officialPageSize.size,
      limit: this.officialPageSize.size,
    };
    query[mapKeys.offset] = params.offset;
    query[mapKeys.limit] = params.limit;
    this.mcpAllService
      .getOfficialList(query)
      .then((res) => {
        if (res?.total) {
          this.officialCardData.push(...res?.mcps || []);
          this.officialCurrentPage++;
          this.hasMore = this.officialCurrentPage < Math.ceil(res?.total / this.officialPageSize.size) + 1;
        } else {
          this.officialCardData = [];
          this.hasMore = false;
        }
        this.officialTotal = res?.total;
      })
      .finally(() => {
        this.officialLoading = false;
      });
  }

  officialPageUpdate(event) {
    this.officialCurrentPage = event.currentPage;
    this.officialPageSize.size = event.size;
    this.getOfficialCardData();
  }

  officialOnSearch() {
    this.officialCurrentPage = 1;
    this.officialCardData.length = 0;
    this.getOfficialCardData();
  }

  // 第三方
  getSquareThirdCardData() {
    this.thirdLoading = true;
    if (window.innerHeight - OTHER_HEIGHT > MAX_HEIGHT) {
      this.thirdPageSize.size = this.thirdPageSize.options[1];
    } else {
      this.thirdPageSize.size = this.thirdPageSize.options[0];
    }
    const params = {
      offset: (this.thirdCurrentPage - 1) * this.thirdPageSize.size,
      limit: this.thirdPageSize.size,
    };
    const query: any = {};
    let isDisableSearch = false;
    if (this.thirdSearchName.length > 0) {
      query[mapKeys.language] = this.isZH() ? 'ZH' : 'EN';
      this.thirdSearchName.forEach((value) => {
        if (value) {
          if (!this.validateUserInput(value)) {
            isDisableSearch = true;
          }
        }
        query.name = value;
      });
    }
    if (isDisableSearch) {
      MessageComponent.showWarn(this.i18n.transform('support_char_types'), 3000);
      this.thirdLoading = false;
      return;
    }
    if (this.thirdValue?.key !== '') {
      query.resource = this.thirdValue?.key || '';
    }

    this.mcpAllService
      .getMcpSquareThird(params, query)
      .then((res) => {
        this.thirdTotal = res?.total || 0;
        if (res?.total) {
          this.thirdCardData.push(...res?.mcps || []);
          this.thirdCurrentPage++;
          this.hasMore = this.thirdCurrentPage < Math.ceil(res?.total / this.thirdPageSize.size) + 1;
        } else {
          this.thirdCardData = [];
          this.hasMore = false;
        }

      })
      .finally(() => {
        this.thirdLoading = false;
      });
  }

  thirdOnSearch() {
    this.thirdCurrentPage = 1;
    this.thirdCardData.length = 0;
    this.getSquareThirdCardData();
  }

  validateUserInput(userInput: string): boolean {
    const regex = /^[\u4e00-\u9fa5a-zA-Z0-9_ -]{1,64}$/;
    return regex.test(userInput);
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  protected readonly changeUrl = cdnAssetUrl;

  loadMore(): void {
    if (this.mcpAllService.tabPageType === 'third') {
      if (this.thirdLoading || !this.hasMore) {
        return;
      };
      this.thirdLoading = true;
      this.getSquareThirdCardData();
    } else {
      if (this.officialLoading || !this.hasMore) {
        return;
      };
      this.officialLoading = true;
      this.getOfficialCardData();
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

  public handleClickClearData() {
    if (this.mcpAllService.tabPageType === 'third') {
      this.thirdSearchName = [];
      this.thirdCurrentPage = 1;
      this.getSquareThirdCardData();
    } else {
      this.officialSearchName = '';
      this.officialCurrentPage = 1;
      this.getOfficialCardData();
    }
  }

}
