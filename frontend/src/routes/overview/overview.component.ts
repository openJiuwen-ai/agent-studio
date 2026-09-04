import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DestroyRef,
  inject,
  OnInit,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import {
  NzButtonModule,
} from 'ng-zorro-antd/button';
import {
  NzToolTipModule,
} from 'ng-zorro-antd/tooltip';
import {
  NzTypographyModule,
} from 'ng-zorro-antd/typography';
import {
  NzModalModule,
  NzModalService,
} from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { ExperienceCreationComponent } from '@routes/experience-creation/experience-creation.component';
import { AppExceedModalComponent } from '@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { CommonService } from '@services/common.service';
import { PermissionService } from '@services/permission.service';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { Subscription } from 'rxjs';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { CommonUtils } from '../../utils/common.util';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'overview',
  standalone: true,
  imports: [
    COMMON_MODULES,
    NzButtonModule,
    NzToolTipModule,
    NzTypographyModule,
    NzModalModule,
    MODULES,
    AppExceedModalComponent,
  ],
  templateUrl: './overview.component.html',
  styleUrls: ['./overview.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.MODEL_ACCESS,
        I18nNamespace.FEATURE_OVERVIEW,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.TOOL,
        I18nNamespace.PLATFORM_MANAGEMENT,
        I18nNamespace.GUIDE
      ],
    },
    NzModalService,
  ],
})
export class OverviewComponent implements OnInit {
  @ViewChild('nodeModal')
  readonly nodeModal?: TemplateRef<HTMLDivElement>;
  public changeUrl = cdnAssetUrl;

  public contentLoading: string = this.i18n.transform('loading_content');
  public tutorialTile: string = '';
  public isLoading: boolean = true;
  public currentPermissions: any;
  public appData = [];
  offset: number = 0;
  limit: number = 6;
  public lang: string = '';
  // 等于0的时候，不展示; 等于1的时候, 展示我的资源; 等于2的时候, 展示资产
  public isShowAssetCard: number = 0;
  public isShowTutorial: boolean = true;
  private permissionSubscription: Subscription;
  isShowMySpace: boolean = false;
  @ViewChild('callModal')
  readonly callModal?: TemplateRef<HTMLDivElement>;

  @ViewChild('exceedModal') exceedModal: AppExceedModalComponent;

  public isSending: boolean = false;
  orderValidityPeriod = false;
  is_due = false;
  count_down_status = null;
  overviewActive = 'create';

  showCreateAppRole = '';

  cardList = [
    {name: this.i18n.transform('overview_10'), key: 'create'},
    {name: this.i18n.transform('overview_12'), key: 'dep'},
  ];

  public workflowType = {
    ['chat']: this.i18n.transform('overview_52'),
    ['task']: this.i18n.transform('overview_53'),
  };
  public agentType = {
    ['agent']: this.i18n.transform('overview_28'),
    ['controller']: this.i18n.transform('overview_32'),
  };

  samestyleList = [];

  copyLoading = false;
  showtop = false;

  private destroyRef = inject(DestroyRef);

  private opsMenu: Record<string, boolean | string> = {
    showOpsMenu: false,
    obsRouter: '',
    evalRouter: ''
  };

  constructor(
    private cdr: ChangeDetectorRef,
    private router: Router,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private nzModal: NzModalService,
    private permissionService: PermissionService,
    public commonService: CommonService,
    private appLibraryRepoService: AppLibraryRepoService,
    private route: ActivatedRoute,
  ) {
    this.lang = CommonUtils.getLanguage();
    this.tutorialTile = this.i18n.transform('content_not_available_tip');
  }

  getCardInfoList(i) {
    let cardinfoList = [];
    if (i === 'create') {
      cardinfoList = [
        {
          bg: 'rgba(242, 246, 255, 1)',
          icon: `url('${this.changeUrl('assets/images/overview/bg-1-2.png')}')`,
          title: this.i18n.transform('overview_15'),
          tip: this.i18n.transform('overview_16'),
          btns: [
            {
              name: this.i18n.transform('agentConfig_split4'),
              class: this.showCreateAppRole !== 'OPERATOR'
                  ? 'new-overview-learn-card-left-b-link'
                  : 'new-overview-learn-card-left-b-link-disable',
              clickFun: async () => {
                if (
                  this.showCreateAppRole !== 'OPERATOR'
                ) {
                  this.router.navigate(['/home/ai-assist-create-home'], {
                    queryParams: {
                      appType: 'agent',
                    },
                  });
                }
              },
            },
            {
              name: this.i18n.transform('overview_31'),
              class:
                this.showCreateAppRole !== 'OPERATOR'
                  ? 'new-overview-learn-card-left-b-link'
                  : 'new-overview-learn-card-left-b-link-disable',
              clickFun: async () => {
                if (
                  this.showCreateAppRole !== 'OPERATOR'
                ) {
                  this.showExperienceCreation('agent');
                }
              },
            },
          ],
        },
        {
          bg: '#F7F1FA',
          icon: `url('${this.changeUrl('assets/images/overview/bg-1-1.png')}')`,
          title: this.i18n.transform('overview_18'),
          tip: this.i18n.transform('overview_19'),
          btns: [
            {
              name: this.i18n.transform('agentConfig_split4'),
              class: this.showCreateAppRole !== 'OPERATOR'
                  ? 'new-overview-learn-card-left-b-link'
                  : 'new-overview-learn-card-left-b-link-disable',
              clickFun: async () => {
                if (
                  this.showCreateAppRole !== 'OPERATOR'
                ) {
                  this.router.navigate(['/home/ai-assist-create-home'], {
                    queryParams: {
                      appType: 'workflow',
                    },
                  });
                }
              },
            },
            {
              name: this.i18n.transform('overview_31'),
              class: 'new-overview-learn-card-left-b-link',
              clickFun: async () => {
                this.showExperienceCreation('workflow');
              },
            },
          ],
        },
      ];
    } else if (i === 'dep') {
      cardinfoList = [
        {
          bg: 'rgba(250, 247, 246, 1)',
          icon: `url('${this.changeUrl('assets/images/overview/bg-2-3.png')}')`,
          title: this.i18n.transform('overview_65'),
          tip: this.i18n.transform('overview_66'),
          btns: [
            {
              name: this.i18n.transform('overview_67'),
              class: 'new-overview-learn-card-left-b-link',
              clickFun: () => {
                this.router.navigate(['/home/agent-center/single']);
              },
            },
          ],
        },
        {
          bg: 'rgba(239, 244, 250, 1)',
          icon: `url('${this.changeUrl('assets/images/overview/bg-2-2.png')}')`,
          title: this.i18n.transform('overview_68'),
          tip: this.i18n.transform('overview_69'),
          btns: [
            {
              name: this.i18n.transform('overview_70'),
              class: 'new-overview-learn-card-left-b-link',
              clickFun: async () => {
                this.router.navigate(['/home/agent-center/library-home']);
              },
            },
          ],
        },
      ];
    } else if (i === 'op') {
      cardinfoList = [
        {
          bg: 'rgba(239, 244, 250, 1)',
          icon: `url('${this.changeUrl('assets/images/overview/bg-5-1.png')}')`,
          title: this.i18n.transform('overview_43'),
          tip: this.i18n.transform('overview_44'),
          show: this.opsMenu.obsRouter,
          btns: [
            {
              name: this.i18n.transform('overview_45'),
              class: 'new-overview-learn-card-left-b-link',
              clickFun: () => {
                this.router.navigate([`home/${this.opsMenu.obsRouter}`]);
              },
            },
          ],
        },
        {
          bg: 'rgba(250, 247, 246, 1)',
          icon: `url('${this.changeUrl('assets/images/overview/bg-5-3.png')}')`,
          title: this.i18n.transform('overview_49'),
          tip: this.i18n.transform('overview_50'),
          show: this.opsMenu.evalRouter,
          btns: [
            {
              name: this.i18n.transform('overview_51'),
              class: 'new-overview-learn-card-left-b-link',
              clickFun: () => {
                this.router.navigate([`home/${this.opsMenu.evalRouter}`]);
              },
            },
          ],
        },
      ].filter(c => Boolean(c.show));
    }
    return cardinfoList;
  }

  ngOnInit() {
    this.showtop = true;
    this.initOpsCard();
    this.route.queryParams.subscribe((params) => {
      if (params.active) {
        if (params.active === 'create') {
          this.overviewActive = 'create';
        } else if (params.active === 'dep') {
          this.overviewActive = 'dep';
        } else if (params.active === 'op') {
          this.overviewActive = 'op';
        }
      }
    });

    this.orderValidityPeriod = this.commonService.getOrderValidityPeriod();
    this.is_due = this.commonService.getDueStatus();
    this.count_down_status = this.commonService.getCountDownStatus();

    this.spaceTeamManagementService.data$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data) => {
      // [FIX] data$ 首次发射为 null（BehaviorSubject 初始值），此时 CUR_SPACE_OPTIONS 尚未被
      // left-menu 初始化，getWorkspaceId() 读不到 workspace_id → getAppData 带空 workspace_id
      // 请求 → 后端 400 "Workspace ID cannot be empty" → 错误分支触发模板 getCardInfoList
      // 变更检测死循环（overview 卡死）。仅当 workspace 就绪（data.cur_space.id 存在）才继续。
      if (!data || !data.cur_space?.id) {
        return;
      }
      this.isLoading = true;
      this.appData.length = 0;
      this.isShowAssetCard = 0;
      this.isShowMySpace = false;
      setTimeout(async () => {
        if (!this.router.url.includes('nonsupportRegion')) {
          const current_space_options = JSON.parse(
            StorageService.getSessionStorage('CUR_SPACE_OPTIONS') || '{}',
          );
          this.showCreateAppRole = current_space_options?.role;
          this.getAppData();
        }
        if (this.hasPermission()) {
          this.isShowAssetCard = 2;
        }
        this.getTutorialState();
        this.cdr.markForCheck();
      }, 500);
    });
    // 订阅权限变化
    this.permissionSubscription = this.permissionService.permissions$.subscribe(
      (permissions) => {
        this.currentPermissions = permissions;
      },
    );
  }

  private getAppData() {
    const params = {
      selected: true,
    };

    Promise.all([
      this.appLibraryRepoService.getTagList(),
      this.appLibraryRepoService.getAppCenterList(params, 0, 6, null),
    ])
      .then(([res1, res2]) => {
        this.samestyleList = (res2.app_list || []).map((item) => {
          return {
            resource_id: item.resource_id,
            icon: item.icon,
            title: item.name,
            desc: item.description,
            resource_type: item.resource_type,
            workflow_type: item.workflow_type,
            resource_type_new:
              item.resource_type === 'agent' ||
              item.resource_type === 'controller'
                ? item.resource_type
                : item.workflow_type,
            resource_type_name:
              item.resource_type === 'agent' ||
              item.resource_type === 'controller'
                ? this.agentType[item.resource_type]
                : this.workflowType[item.workflow_type],
            // [FIX] 修复 overview 首页卡死：t_app.tags 存中文标签名（如 "通用"/"效率"），而
            // t_tag.tag_id 是 UUID，res1.find 匹配不到 → showTags 含 undefined → 模板
            // {{ tags.name }} 抛 TypeError → Angular CD 死循环 → 页面卡死。
            // 过滤 find 未命中的 undefined，保证 showTags 不含空元素。
            showTags: ((item.tags || [])?.map((tag: string) =>
              (res1 || []).find((item: any) => item.tag_id === tag),
            ) || []).filter(Boolean),
            hot: '0',
          };
        });
      })
      .catch(() => {
        // 请求失败不阻塞页面（保持 loading 结束、卡片区隐藏）
        // [FIX] 补 .catch 避免 Promise.all 拒绝时 unhandled rejection 刷屏（overview 卡死修复的一部分）
      })
      .finally(() => {
        this.isLoading = false;
        this.isShowAssetCard = 1;
        this.cdr.markForCheck();
      });
  }

  get newOverivewHeight() {
    const dom = document.getElementsByClassName('new-overview');
    let rect = dom[0]?.getBoundingClientRect() || {top: 0};
    return `calc(100vh - ${rect.top || 0}px - 64px)`;
  }

  public getTutorialState() {
    if (localStorage.getItem('isShowTutorial') === null) {
      this.isShowTutorial = true;
    } else {
      this.isShowTutorial = localStorage.getItem('isShowTutorial') === 'true';
    }
  }

  public hasPermission(): boolean {
    return (
      this.currentPermissions &&
      Object.prototype.hasOwnProperty.call(this.currentPermissions, 'OPERATOR')
    );
  }

  ngOnDestroy() {
    // 组件销毁时取消订阅
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  setOverviewActive(val) {
    this.overviewActive = val;
  }

  public showAllApp() {
    this.router.navigate(['/home/app-library'], {
      queryParams: {
        from: 'overview',
      },
    });
  }

  public async toCardCopy(item: any) {
    if (this.showCreateAppRole !== 'OPERATOR') {

      this.copyLoading = true;
      const appId = item.resource_id || '';
      const type = item.resource_type === 'workflow' ? 'workflow' : 'agent';
      this.appLibraryRepoService
        .copyToWorkbench(appId, type)
        .then((res: any) => {
          if (res.resource_id) {
            MessageComponent.showSuccess(
              this.i18n.transform('common_tip_1'),
              3000,
            );

            if (item.resource_type === 'workflow') {
              this.router.navigate(['/home/agent-center/app-flow/flow'], {
                queryParams: {
                  id: res.resource_id,
                  from: 'overview',
                },
              });
            } else {
              this.router.navigate(['/home/agent-center/app-agent/detail'], {
                queryParams: {
                  agentId: res.resource_id,
                  from: 'overview',
                },
              });
            }
          }
        })
        .finally(() => {
          this.copyLoading = false;
        });
    }
  }

  public toCardDetail(item: any) {
    const appId = item.resource_id || '';
    const queryParams: any = {
      appId,
      from: 'overview',
    };
    if (item.resource_type === 'agent') {
      // 智能体
      this.router.navigate([`home/app-library/knowledge-bot`], {
        queryParams,
      });
    } else if (item.resource_type === 'workflow') {
      // 工作流 对话型 任务型
      if (item.workflow_type === 'chat') {
        this.router.navigate([`home/app-library/flow/knowledge-bot`], {
          queryParams,
        });
      } else {
        this.router.navigate(
          [`home/app-library/scenario-bot/scene/${appId}`],
          {
            queryParams,
          },
        );
      }
    } else if (item.resource_type === 'controller') {
      queryParams.isMultipleAgent = true;
      // 去多智能体
      this.router.navigate([`home/app-library/flow/knowledge-bot`], {
        queryParams,
      });
    }
  }

  showExperienceCreation(type): void {
    const getTitle = new Map([
      ['agent', '快速创建智能体'],
      ['workflow', '快速创建工作流'],
    ]);
    const modal = this.nzModal.create({
      nzTitle: getTitle.get(type),
      nzContent: ExperienceCreationComponent,
      nzFooter: null,
      nzData: {
        type: type,
        outputs: {},
        modalRef: null,
      },
      nzOnOk: (contentInstance) => {
        if (type === 'agent') {
          contentInstance.experienceCreateAgent();
        } else if (type === 'workflow') {
          contentInstance.experienceCreateFlow();
        }
      },
    });
    modal.afterOpen.subscribe(() => {
      const contentInstance = modal.getContentComponent();
      if (contentInstance) {
        contentInstance.modalRef = modal;
      }
    });
  }

  /**
   * 是否展示运营运维
   */
  private initOpsCard() {

  }
}
