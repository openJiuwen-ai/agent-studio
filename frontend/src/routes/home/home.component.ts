import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit, ViewContainerRef } from '@angular/core';
import * as angularI18next from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { NzLayoutModule } from 'ng-zorro-antd/layout';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzProgressModule } from 'ng-zorro-antd/progress';
import { ContextService } from '@services/context.service';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { environment } from 'src/environment/environment';
import { IMenuItem, ViewModel } from './home.model';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { LeftMenuComponent } from '@routes/left-menu/left-menu.component';
import { ConversationWorkspaceService } from '@routes/conversation-workspace/conversation-workspace.service';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { HttpService } from '@services/http.service';
import { getSessionStorage, isDevelpor, setSessionStorage } from 'src/utils/utils';
import { isMobile } from '../../utils/commonFn';
import { MobileTipModalComponent } from '@routes/platform-management/resource-management/alert-model/mobile-tip-modal/mobile-tip-modal.component';
import { NzModalService } from 'ng-zorro-antd/modal';

@Component({
  selector: 'home',
  standalone: true,
  imports: [MODULES, LeftMenuComponent, NzLayoutModule, NzAlertModule, NzProgressModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
  changeDetection: ChangeDetectionStrategy.Default,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.REVIEW,
        I18nNamespace.PLATFORM_MANAGEMENT,
        I18nNamespace.COMMON,
        I18nNamespace.AGENT,
        I18nNamespace.NODE,
        I18nNamespace.AGENT_CORE,
        I18nNamespace.STATIC_APP_ORCHESTRATION,
        I18nNamespace.AGENT_CENTER,
      ],
    },
  ],
})
export class HomeComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  public vm: ViewModel;
  public home: ViewModel;
  is_platform_hide = true;
  private notification_model_subscribe;
  public notAdmin_create_error = false;

  constructor(
    private readonly i18NextEagerPipe: angularI18next.I18NextEagerPipe,
    private ctxServ: ContextService,
    private configServ: AgentConfigService,
    private conversationWorkspaceService: ConversationWorkspaceService,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private router: Router,
    private route: ActivatedRoute,
    private sidebarServ: SetSidebarVisibilityService,
    private cdr: ChangeDetectorRef,
    private http: HttpService,
    private i18n: I18NextEagerPipe,
    private modal: NzModalService,
    private viewContainerRef: ViewContainerRef
  ) {
    const isHideMobileModal = getSessionStorage('isHideMobileModal');
    if (isMobile() && !isHideMobileModal) {
      this.showMobileModal();
    } else {
      this.spaceTeamManagementService.data$.subscribe(data => {
        if (data) {
          const sapce = data.cur_space;
          const is_neeed_reload = data.is_neeed_reload ?? false;
          this.is_platform_hide = sapce.type === 'PERSON';
          // 有菜单列表时才会跳转到首页,没有菜单列表时 则不需要跳转到首页
          // 渲染菜单列表
          this.spanData = { ...data };
          this.render_menu_list(this.is_platform_hide);
          // 空间就绪后刷新会话列表（左菜单「任务空间」分组依赖）
          this.conversationWorkspaceService.refreshSessions();
          // 具体请查看this.spaceTeamManagementService.space$.subscribe 该方法
          if (is_neeed_reload) {
            this.router.navigate(['/home/overview']);
          }
        }
      });

      this.configServ.data$.subscribe(data => {
        if (data) {
          this.render_menu_list(this.is_platform_hide);
        }
      });

      this.route.queryParams.subscribe(params => {
        this.from_page = params.from;
      });

      this.http.getFristCreateError().subscribe(res => {
        this.notAdmin_create_error = res;
      });
    }
  }

  private routerEventsSubscription: Subscription;
  public computedClass = true;
  from_page = '';

  async ngOnInit() {
    // 初始化渲染菜单列表
    this.render_menu_list(this.is_platform_hide);

    this.filterRoutesByPermission(this.vm.leftmenu.items);

    // 会话列表/当前会话变化时重建「任务空间」分组
    this.conversationWorkspaceService.refreshSessions();
    this.conversationWorkspaceService.sessions$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.updateConversationMenu());
    this.conversationWorkspaceService.activeSession$
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => this.updateConversationMenu());

    this.sidebarServ.setSidebarsVisibilityByState('hideSidebar');

    this.ctxServ
      .isHideLeftMenuUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(value => {
        this.vm.leftmenu.config.collapsed = value;
        this.vm.leftmenu.config = { ...this.vm.leftmenu.config };
      });

    this.routerEventsSubscription = this.router.events.subscribe(event => {
      switch (true) {
        case event instanceof NavigationEnd: {
          let arr = ['/home/agent-observatory/statistic'];
          this.computedClass = !arr.includes(event.urlAfterRedirects);
          break;
        }
        default:
          break;
      }
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.routerEventsSubscription) {
      this.routerEventsSubscription.unsubscribe();
    }
    if (this.notification_model_subscribe) {
      this.notification_model_subscribe.unsubscribe();
    }
  }

  ngAfterViewInit(): void {}

  private showMobileModal() {
    const modal = this.modal.create<MobileTipModalComponent, any>({
      nzTitle: 'Modal Title',
      nzContent: MobileTipModalComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzOnOk: () => new Promise(resolve => setTimeout(resolve, 1000)),
      nzFooter: [
        {
          label: 'change component title from outside',
          onClick: () => {
            setSessionStorage('isHideMobileModal', true);
            (<any>window).location.reload(); // 如果使用navigate跳转，因为刷新的是当前页面，无法重新触发其他弹窗的展示
          },
        },
      ],
    });
  }

  private filterRoutesByPermission(menuItems: IMenuItem[]) {
    for (const item of menuItems) {
      if (item.children) {
        this.filterRoutesByPermission(item.children);

        if (item.children.every(child => child.hide)) {
          item.hide = true;
        }
      }
    }
  }

  spanData = {} as any;

  /** 构建「任务空间」分组的会话子项（定时任务 + 新建入口 + 会话列表） */
  private buildConversationItems(): IMenuItem[] {
    const activeId = this.conversationWorkspaceService.activeSession$.value?.conversation_id;
    const schedulerItem: IMenuItem = {
      id: 'scheduler',
      name: '自动化',
      label: '自动化',
      icon: cdnAssetUrl('assets/images/menu/home.svg'),
      iconSelected: cdnAssetUrl('assets/images/menu/home_selected.svg'),
      router: ['scheduler'],
      isSelected: false,
    };
    const newItem: IMenuItem = { id: 'conversation-new', name: '＋ 新建会话', label: '＋ 新建会话' };
    const sessionItems: IMenuItem[] = this.conversationWorkspaceService.sessions$.value.map((s) => ({
      name: s.title,
      label: s.title,
      queryParams: { conversation_id: s.conversation_id },
      isSelected: s.conversation_id === activeId,
    }));
    return [schedulerItem, newItem, ...sessionItems];
  }

  /** 会话列表/当前会话变化后，重建「任务空间」分组子项并触发 left-menu 重新渲染 */
  private updateConversationMenu(): void {
    const items = this.vm?.leftmenu?.items;
    if (!items) {
      return;
    }
    const group = items.find((i) => i.id === 'conversation-workspace');
    if (group?.children?.[0]) {
      group.children[0].children = this.buildConversationItems();
    }
    this.vm.leftmenu.items = [...items];
    this.cdr.markForCheck();
  }

  // 渲染菜单列表
  private render_menu_list(is_hide) {
    const { block_nodes } = this.configServ.getConfigs();
    const isHideSql = (block_nodes ?? []).some(type => type?.toLowerCase() === 'sql');
    const isHideDataQuery = (block_nodes ?? []).some(type => type?.toLowerCase() === 'dataquery');
    let isDevelporFlag = isDevelpor();
    const isHideOperationCenter =
      (isDevelporFlag && !this.configServ.getConfigs().agentops_evaluation_display) || !this.configServ.getConfigs().agentops_menu_display;
    const isHideDatasource = isHideSql && isHideDataQuery;
    let projectID: any = '';
    try {
      const curSpaceOptions = getSessionStorage('CUR_SPACE_OPTIONS');
      projectID = JSON.parse(curSpaceOptions || '{}').projectId;
    } catch (error) {
      projectID = '';
    }
    const cardWhitelist = (this.configServ.getConfigs()?.card_whitelist || '').split(',');
    const showCard = cardWhitelist.indexOf(projectID) < 0;
    this.vm = {
      leftmenu: {
        config: {
          reloadState: false,
          serviceName: this.i18NextEagerPipe.transform('agent_app_dev', {
            ns: I18nNamespace.PROMPT_PLATFORM,
          }),
        },
        items: [
          /** 首页-快速上手 */
          {
            name: '',
            label: '',
            router: ['dialog-home'],
            children: [
              {
                id: 'overview',
                name: this.i18NextEagerPipe.transform('survey'),
                label: this.i18NextEagerPipe.transform('survey'),
                icon: cdnAssetUrl('assets/images/menu/home.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/home_selected.svg'),
                router: ['overview'],
                isSelected: false,
              },
              /** 专家·技能 */
              {
                id: 'asset_center',
                name: this.i18NextEagerPipe.transform('asset_center'),
                label: this.i18NextEagerPipe.transform('asset_center'),
                isGroup: false,
                icon: cdnAssetUrl('assets/images/menu/public_planets.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/public_planets_selected.svg'),
                rightIcon: cdnAssetUrl('assets/images/menu/pycharm.svg'),
                isSelected: false,
                router: ['/app-library'],
              },
            ],
          },
          /** 开发中心 */
          {
            id: 'develop-center',
            name: this.i18NextEagerPipe.transform('develop-center'),
            label: this.i18NextEagerPipe.transform('develop-center'),
            isGroup: true,
            children: [
              {
                name: this.i18NextEagerPipe.transform('develop-center'),
                label: this.i18NextEagerPipe.transform('develop-center'),
                children: [
                  {
                    name: this.i18NextEagerPipe.transform('agent-management'),
                    label: this.i18NextEagerPipe.transform('agent-management'),
                    icon: cdnAssetUrl('assets/images/menu/agent-manage.svg'),
                    iconSelected: cdnAssetUrl('assets/images/menu/agent-manage_selected.svg'),
                    router: ['agent-center/single'],
                    routerList: [['agent-center/workflow'], ['agent-center/multi']],
                    isSelected: false,
                  },
                  {
                    name: this.i18NextEagerPipe.transform('component_library'),
                    label: this.i18NextEagerPipe.transform('component_library'),
                    icon: cdnAssetUrl('assets/images/menu/com_library.svg'),
                    iconSelected: cdnAssetUrl('assets/images/menu/com_library_selected.svg'),
                    router: ['agent-center/library-home'],
                    isSelected: false,
                  },
                  {
                    name: this.i18NextEagerPipe.transform('develop-config'),
                    label: this.i18NextEagerPipe.transform('develop-config'),
                    icon: cdnAssetUrl('assets/images/menu/develop-config.svg'),
                    iconSelected: cdnAssetUrl('assets/images/menu/develop-config_selected.svg'),
                    router: ['development-configuration'],
                    isSelected: false,
                  },
                ],
                collapseStatus: 1,
              },
            ],
          },
          /** 模型管理 */
          {
            id: 'model_center',
            name: this.i18NextEagerPipe.transform('model_center'),
            label: this.i18NextEagerPipe.transform('model_center'),
            isGroup: true,
            isHide: true,
            children: [
              {
                name: this.i18NextEagerPipe.transform('model_service'),
                label: this.i18NextEagerPipe.transform('model_service'),
                icon: cdnAssetUrl('assets/images/menu/service_deploy.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/service_deploy_selected.svg'),
                router: ['model/management'],
                isSelected: false,
              },
              {
                name: this.i18NextEagerPipe.transform('route_policy'),
                label: this.i18NextEagerPipe.transform('route_policy'),
                icon: cdnAssetUrl('assets/images/menu/my_flow.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/my_flow_selected.svg'),
                router: ['model/route-policy'],
                isSelected: false,
              },
              {
                name: this.i18NextEagerPipe.transform('model_test'),
                label: this.i18NextEagerPipe.transform('model_test'),
                icon: cdnAssetUrl('assets/images/menu/online_test_manage.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/online_test_manage_selected.svg'),
                router: ['model/online-test-manage'],
                isSelected: false,
              },
              {
                name: this.i18n.transform('my_credentials'),
                label: this.i18n.transform('my_credentials'),
                hide: !this.configServ.getConfigs()?.apikey_enable,
                icon: cdnAssetUrl('assets/images/menu/certification.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/certification_selected.svg'),
                router: ['model/certification'],
                isSelected: false,
              },
            ],
          },
          /** 运营中心 */
          {
            id: 'operation_center',
            name: this.i18NextEagerPipe.transform('operation_center'),
            label: this.i18NextEagerPipe.transform('operation_center'),
            isGroup: true,
            hide: isHideOperationCenter,
            children: [],
          },
          /** 平台管理 */
          {
            id: 'platform_management',
            name: this.i18NextEagerPipe.transform('platform_management'),
            label: this.i18NextEagerPipe.transform('platform_management'),
            isGroup: true,
            hide: ['hcs', 'hcso'].includes(environment.envType) ? is_hide : false,
            children: [
              {
                name: this.i18NextEagerPipe.transform('system-management'),
                label: this.i18NextEagerPipe.transform('system-management'),
                hide: ['site'].includes(environment.envType) ? false : is_hide,
                children: [
                  {
                    name: this.i18NextEagerPipe.transform('space_team_management'),
                    label: this.i18NextEagerPipe.transform('space_team_management'),
                    icon: cdnAssetUrl('assets/images/menu/mcp.svg'),
                    iconSelected: cdnAssetUrl('assets/images/menu/ic_public_teams.svg'),
                    router: ['platform-management/space-team-management'],
                    hide: is_hide,
                    isSelected: false,
                  },
                  {
                    name: this.i18NextEagerPipe.transform('environment_management'),
                    label: this.i18NextEagerPipe.transform('environment_management'),
                    icon: cdnAssetUrl('assets/images/menu/env_mgt.svg'),
                    iconSelected: cdnAssetUrl('assets/env-manager/env-memu-active.svg'),
                    router: ['platform-management/environment-management-home'],
                    isSelected: false,
                    hide: !['site'].includes(environment.envType),
                  },
                ],
                collapseStatus: 1,
              },
            ],
          },
          /** 配置管理  */
          {
            id: 'config_management',
            name: this.i18NextEagerPipe.transform('config_management'),
            label: this.i18NextEagerPipe.transform('config_management'),
            isHide: true,
            children: [
              {
                name: this.i18NextEagerPipe.transform('model_access_management'),
                label: this.i18NextEagerPipe.transform('model_access_management'),
                hide: environment.envType === 'hc' || environment.envType === 'hcs' || environment.envType === 'site',
                router: ['model/management'],
                isSelected: false,
              },
              {
                name: this.i18NextEagerPipe.transform('intent_package'),
                label: this.i18NextEagerPipe.transform('intent_package'),
                router: ['intent-package/management'],
                isSelected: false,
                routerList: [['intent-detail']],
              },
              {
                name: this.i18n.transform('data_source_management'),
                label: this.i18n.transform('data_source_management'),
                router: ['datasource/management'],
                isSelected: false,
                hide: isHideDatasource,
              },
            ],
          },
          /** 任务空间 */
          {
            id: 'conversation-workspace',
            name: '任务空间',
            label: '任务空间',
            isGroup: true,
            children: [
              {
                name: '任务空间',
                label: '任务空间',
                collapseStatus: 1,
                children: this.buildConversationItems(),
              },
            ],
          },
        ].filter(v => {
          // 通过hide这个字隐藏一些菜单
          return !(v?.hide || v?.isHide);
        }),
      },
    };
    this.vm.leftmenu.items.forEach(v => {
      if (v.children) {
        v.children = v.children.filter((ele: any) => {
          if (ele?.hide || ele?.isHide) return false;
          if (ele?.children && ele?.children.length > 0) {
            ele.children = ele.children.filter((e: any) => {
              return !(e?.hide || e?.isHide);
            });
          }
          return true;
        });
      }
    });
    this.home = {
      leftmenu: {
        config: {
          reloadState: false,
          serviceName: this.i18NextEagerPipe.transform('agent_app_dev', {
            ns: I18nNamespace.PROMPT_PLATFORM,
          }),
        },
        items: [
          /** 首页-快速上手 */
          {
            name: '',
            label: '',
            router: ['dialog-home'],
            children: [
              /** 专家·技能 */
              {
                id: 'app-library',
                name: this.i18NextEagerPipe.transform('app_square'),
                label: this.i18NextEagerPipe.transform('app_square'),
                icon: cdnAssetUrl('assets/images/menu/app-center.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/app-center-selected.svg'),
                isSelected: false,
                router: ['app-library'],
                routerList: [['/knowledge-bot'], ['/flow/knowledge-bot'], ['/flow/preload'], ['/scenario-bot/:appType/:appId']],
              },
              {
                name: this.i18NextEagerPipe.transform('mcp_square'),
                label: this.i18NextEagerPipe.transform('mcp_square'),
                icon: cdnAssetUrl('assets/images/menu/mcp-center.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/mcp-center-selected.svg'),
                isSelected: false,
                router: ['service-market'],
              },
              {
                name: this.i18NextEagerPipe.transform('skill_market'),
                label: this.i18NextEagerPipe.transform('skill_market'),
                icon: cdnAssetUrl('assets/images/menu/skill_market.svg'),
                iconSelected: cdnAssetUrl('assets/images/menu/skill_market_selected.svg'),
                isSelected: false,
                router: ['skill-market'],
              },
            ].filter((v: any) => {
              return !(v?.hide || v?.isHide);
            }),
          },
        ].filter((v: any) => {
          // 通过hide这个字隐藏一些菜单
          return !(v?.hide || v?.isHide);
        }),
      },
    };
    this.cdr.markForCheck();
  }
}
