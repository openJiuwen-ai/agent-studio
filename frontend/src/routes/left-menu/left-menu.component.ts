import { CommonModule, NgForOf, NgIf } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, HostListener, Input, OnChanges, OnInit, SimpleChanges, ViewChild, ViewContainerRef } from '@angular/core';
import { cdnAssetUrl } from 'src/single-spa/assets-url';

import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { IMenuItem } from '@routes/home/home.model';
import { ConversationWorkspaceService } from '@routes/conversation-workspace/conversation-workspace.service';
import { ContextService } from '@services/context.service';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { filter, Subject, Subscription } from 'rxjs';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { FormsModule } from '@angular/forms';
import { CreateSpaceComponent } from '@routes/platform-management/space-team-management/create-space/create-space.component';
import { MODULES } from '@shared/modules';
import { PermissionService } from '@services/permission.service';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { ConsoleFrameworkService } from '@core/services';

import { MasOperatorService } from '@services/mas-operator.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';

import { AppExceedModalComponent } from '@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component';

import { CommonUtils } from '../../utils/common.util';
import { NzModalService } from 'ng-zorro-antd/modal';
import { StorageService } from '@shared/services/cfdata.service';

@Component({
  selector: 'left-menu',
  templateUrl: './left-menu.component.html',
  styleUrls: ['./left-menu.component.less'],
  standalone: true,
  imports: [NgIf, NgForOf, I18NextModule, FormsModule, CommonModule, MODULES, AppExceedModalComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.TOOL,
        I18nNamespace.COMMON,
        I18nNamespace.PROMPT_PLATFORM,
        I18nNamespace.PLATFORM_MANAGEMENT,
        I18nNamespace.AGENT,
        I18nNamespace.AGENT_CENTER,
      ],
    },
  ],
})
export class LeftMenuComponent implements OnInit, OnChanges {
  private destroy$ = new Subject<void>();

  @Input() items: IMenuItem[];
  @Input() marketItems: IMenuItem[];
  @ViewChild('select', { static: true }) SelectCom: any;
  @ViewChild('appExceedModal') appExceedModal: AppExceedModalComponent;
  @ViewChild('tipContentRef') tipContentRef!: ElementRef;
  @ViewChild('authorizationManageRef') authorizationManageRef!: ElementRef;
  @ViewChild('authorizationManageTip') authorizationManageTip!: ElementRef;
  @ViewChild('select', { read: ViewContainerRef }) selectViewContainerRef!: ViewContainerRef;

  private routerSub: Subscription;
  private permissionSubscription: Subscription;
  private subscribeBtnStatusSubscription: Subscription;
  public is_need_menu = true;
  public routeUrl = '';
  public routeParams = {}; // url上面的参数
  isMenuExpand = true;
  private cacheMenuData = {
    parent: [],
    children: [],
  };
  // 过滤后的项目列表
  filteredItems: any[] = [];
  // 是否触发过路由监听
  isRouteSub: boolean = false;

  roles_list = [];
  space_options: Array<any> = [];
  space_value: any = null;
  copyItems: IMenuItem[] = [];
  copy_space_options: Array<any> = [];
  space_name: string = '';
  space_icon: string = cdnAssetUrl('assets/images/menu/space-user.svg');
  isSwitchSpace: boolean = false;
  public currentPermissions: any;
  // 如果用户点击了从概览页跳转到创建应用页面
  public isRouteToApps: boolean = false;
  public isRotate: boolean = false;
  private tipInstance: any;
  public isHover: boolean = false;
  windowHeight: number = window.innerHeight;
  model_service_name = this.i18NextEagerPipe.transform('model_service');
  isMarket = false;

  @HostListener('window:resize', ['$event'])
  onWindowResize(event: Event) {
    this.windowHeight = window.innerHeight;
  }

  selectLanguage: any = {
    id: 'zh-cn',
    label: '简体中文',
  };
  from_page = '';
  lang = CommonUtils.getLanguage();
  public changeUrl = cdnAssetUrl;
  public isSelectedResourceManage: boolean = false;
  public isSelectedAuthorizationManage: boolean = false;
  public expandMenuData: any[] = []; // 收起左侧侧边栏的时候，展示的数据
  public handleClickOutMenu: any;

  windowMenu = 1279;
  private authorizationManageShow = false;

  private queryWorkSpace = '';
  searchSpaceLoading = false;

  isFocusSpaceSelectBox = false;

  constructor(
    private ctxServ: ContextService,
    private router: Router,
    private route: ActivatedRoute,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private nzModalService: NzModalService,
    private cdr: ChangeDetectorRef,
    private permissionService: PermissionService,
    public commonService: CommonService,
    private i18n: I18NextEagerPipe,
    private readonly http: HttpService,
    private readonly consoleFrameworkService: ConsoleFrameworkService,
    private readonly i18NextEagerPipe: angularI18next.I18NextEagerPipe,
    private masOperatorService: MasOperatorService,
    private appAgentRepoServ: AppAgentRepoService,
    private conversationWorkspaceService: ConversationWorkspaceService
  ) {
    // 箭头函数，保存this的指向
    this.handleClickOutMenu = event => {
      // 当屏幕尺寸小于1600px时，点击菜单外面收起菜单
      if (this.isMenuExpand && event.clientX > 256 && window.innerWidth <= this.windowMenu) {
        this.collapseMenu();
      }
    };
    window.addEventListener('click', this.handleClickOutMenu);
    if (window.innerWidth <= this.windowMenu) {
      this.collapseMenu();
    }
    this.get_space_member_roles();

    this.route.queryParams.subscribe(params => {
      this.from_page = params.from;
      this.queryWorkSpace = params.workspace_id;
    });
    if (this.router.url.indexOf('/develop-space') > -1) {
      this.from_page = 'develop-space';
    }
    this.setSelectedStatus();
    this.router.events.pipe(filter(event => event instanceof NavigationEnd)).subscribe((event: any) => {
      this.tipInstance?.hide(); // 隐藏tip提示
      CommonUtils.setCurUserLocalStorage('authorization_manage_tip', false);
    });
  }

  authorizationManageTipClick($event) {
    $event.stopPropagation();
    if (!this.tipInstance) {
      this.tipInstance = true;
    }
    this.authorizationManageShow = !this.authorizationManageShow;
  }
  closeAuthorizationManageTip() {
    this.authorizationManageShow = false;
    CommonUtils.setCurUserLocalStorage('authorization_manage_tip', true);
  }

  role_name(id: string): string {
    const lang = CommonUtils.getLanguage();
    const role = this.roles_list.filter(item => item.roleId === id);
    if (role.length) {
      if (lang === 'zh-cn') {
        return role[0].roleNameCn;
      } else {
        return CommonUtils.titleCase3(role[0].roleNameEn);
      }
    } else {
      return '';
    }
  }

  /**
   * 进入hover态
   */
  enterHover() {
    this.isHover = true;
    this.cdr.markForCheck();
  }
  /**
   * 离开hover态
   * 加与动画时间相等延时
   */
  leaveHover() {
    setTimeout(() => {
      this.isHover = false;
      this.cdr.markForCheck();
    }, 300);
  }
  // 点击收起时又会触发enter导致无法折叠，需要加与动画时间相等的锁
  mouseEnterLock = false;

  lockMouseEnter(time: number = 300) {
    this.mouseEnterLock = true;
    setTimeout(() => {
      this.mouseEnterLock = false;
    }, time);
  }

  handleMouseLeave($event) {
    const targetDom = $event?.toElement?.closest('body>ti-drop');
    if (targetDom) {
      // 判断是否为空间下拉框
      return;
    }
    if (this.isFocusSpaceSelectBox) {
      return;
    }
    if (window.innerWidth <= this.windowMenu) {
      this.collapseMenu();
    } else {
      if (this.isHover) {
        this.leaveHover();
        this.collapseMenu();
      }
    }
  }

  handleMouseEnter() {
    if (this.mouseEnterLock) {
      return;
    }
    if (window.innerWidth <= this.windowMenu) {
      this.expandMenu();
    } else {
      if (!this.isMenuExpand) {
        this.enterHover();
      }
      this.expandMenu();
    }
  }

  /** 删除会话（软删除，带确认弹窗）：左菜单「任务空间」会话项悬停删除 */
  public deleteConversation(event: Event, item: any): void {
    event.stopPropagation();
    const id = item?.queryParams?.conversation_id;
    if (!id) {
      return;
    }
    this.nzModalService.confirm({
      nzTitle: '删除会话',
      nzContent: '确定要删除该会话吗？删除后不可恢复。',
      nzOkText: '删除',
      nzOkDanger: true,
      nzCancelText: '取消',
      nzOnOk: () =>
        this.conversationWorkspaceService.deleteSession(id).then(() => {
          if (this.conversationWorkspaceService.activeSession$.value?.conversation_id === id) {
            this.conversationWorkspaceService.newDraftSession();
          }
          return this.conversationWorkspaceService.refreshSessions();
        }),
    });
  }

  handleNodeClick(event: Event, item: any, index: number, childIndex: number, isRouter: boolean = true) {
    if (item.name !== '应用广场') {
      StorageService.delSessionStorage('application_square_type');
    }
    if (!item.collapseStatus && !this.isContainRouteUrl(item)) {
      StorageService.delSessionStorage('JIUWEN_SEARCH_PARAMS');
    }
    this.onClick(event);
    // 会话助手：新建/打开会话用查询参数驱动导航（不依赖 router，避免整组误高亮）
    if (item.id === 'conversation-new') {
      this.router.navigate(['home/conversation'], { queryParams: { new: Date.now() } });
      return;
    }
    if (item.queryParams?.conversation_id) {
      this.router.navigate(['home/conversation'], {
        queryParams: { conversation_id: item.queryParams.conversation_id },
      });
      return;
    }
    if (this.cacheMenuData.children.length && this.cacheMenuData.children[this.cacheMenuData.children.length - 1].name === item.name) {
      return;
    }
    this.cancelSelectChildMenu(item);
    if (!item.collapseStatus && (!item.children || !item.children.length) && !item.isSelected) {
      this.cacheMenuData.parent.length = 0;
      for (let index = 0; index < this.cacheMenuData.children.length; index++) {
        // 取消其他三级菜单的选择
        this.cacheMenuData.children[index].isSelected = false;
      }
      this.cacheMenuData.children.length = 0;
      if (isRouter) {
        this.router.navigate(['home/' + item.router[0]], {
          queryParams: event ? {} : this.routeParams,
        });
        this.routeUrl = item.router[0];
      }
      return;
    }
    if (!item.collapseStatus) {
      if (isRouter) {
        if (this.routeUrl && item.routerList && item.routerList.flat().indexOf(this.routeUrl) > -1) {
          return;
        } else {
          this.router.navigate(['home/' + item.router[0]], {
            queryParams: event ? {} : this.routeParams,
          });
          this.routeUrl = item.router[0];
        }
      }
      return;
    }
    if (item.collapseStatus === 1) {
      item.collapseStatus = 2;
    } else {
      item.collapseStatus = 1;
    }
    // 切换折叠展开状态后记录用户目录
    this.recordUserMenuState();
    if (!this.cacheMenuData.parent.some(data => data.name === item.name)) {
      this.cacheMenuData.parent.push(item);
    }
  }

  async onSpaceSelect(option: any) {
    console.log(this.space_value);
    this.isRotate = false;
    this.space_value = option.id;
    this.space_name = option.name;
    this.space_icon = option.icon;
    this.isSwitchSpace = true;
    this.ctxServ.addUserIdToLocal(option);
    StorageService.setSessionStorage('CUR_SPACE_OPTIONS', JSON.stringify(option));

    StorageService.setSessionStorage('agentOpsQueryAddtion', null);
    StorageService.setSessionStorage('agentOpsQueryAddtionOptions', null);
    let param = { ...option };
    const params = {
      is_neeed_reload: true,
      cur_space: param,
    };
    this.routeUrl = 'overview';
    this.spaceTeamManagementService.updateSpaceOptionsSelected(params);
    // 订阅权限变化
    // 初始过滤
    this.permissionService.fetchPermissions().subscribe({
      next: permissions => {},
    });
    this.masOperatorService.fetchMasOperators().subscribe({
      next: permissions => {},
    });
  }

  public hasPermission(): boolean {
    return this.currentPermissions && this.currentPermissions.OPERATOR;
  }

  private cancelSelectChildMenu(item: any) {
    if (Object.prototype.hasOwnProperty.call(item, 'isSelected')) {
      if (this.cacheMenuData.children.length <= 0) {
        this.cacheMenuData.children.push(item);
        item.isSelected = true;
      } else {
        this.cacheMenuData.children[0].isSelected = false;
        item.isSelected = true;
        this.cacheMenuData.children[0] = item;
      }
      // 需要折叠其他包含三级菜单
      if (this.cacheMenuData.parent.length > 1) {
        this.cacheMenuData.parent = [this.cacheMenuData.parent[this.cacheMenuData.parent.length - 1]];
      }
    }
  }

  async onBeforeOpen(selectComp: any) {
    // 得到空间列表
    await this.get_space();
  }

  async init_space() {
    // 初始化空间下拉列表
    let space_option = [];
    const get_space_options_str = StorageService.getSessionStorage('SPACE_OPTIONS');
    if (get_space_options_str) {
      space_option = JSON.parse(get_space_options_str);
      this.commonGetWorkSpaceCode(space_option);
    } else {
      await this.get_space();
    }
    this.handlerWorkSpace();
  }

  show_model_tip($event: any): void {
    $event.stopPropagation();
  }

  userInfo: any;

  get isAdmin() {
    return this.userInfo?.userRoles?.includes('te_admin') ?? false;
  }

  async ngOnInit(): Promise<void> {
    this.userInfo = StorageService.getLocalStorage('PROMPT_ENGINEERING_ME');
    const language = this.consoleFrameworkService?.dataService?.getLocale() as string;
    if (language === 'zh-cn') {
      this.selectLanguage = {
        id: 'zh-cn',
        label: '简体中文',
      };
    } else if (language === 'en-us') {
      this.selectLanguage = {
        id: 'en-us',
        label: 'English',
      };
    }

    await this.init_space();

    this.spaceTeamManagementService.space$.subscribe(async data => {
      // 该方法会在增加删除时触发
      if (data) {
        // 设置空间的默认值
        this.set_current_sapce();
      }
    });
    // 订阅权限变化
    this.permissionSubscription = this.permissionService.permissions$.subscribe(permissions => {
      this.filterItems(permissions);
      this.currentPermissions = permissions;
      this.initMenu();
    });
    // 初始过滤
    this.initIsMarket(window.location.hash);
    // 订阅路由变化事件
    this.routerSub = this.router.events
      .pipe(
        // 只关注NavigationEnd事件
        filter(event => event instanceof NavigationEnd)
      )
      .subscribe(async (event: any) => {
        this.initIsMarket(event?.url);
        // 这里处理路由变化后的逻辑
        this.isRouteSub = true;
        this.is_need_menu = !this.ctxServ.getIsHideLeftMenu();
        const urlStr = window.location.hash.slice(7);
        this.routeUrl = urlStr.split('?')[0];
        this.routeParams = this.getUrlParams(urlStr);
        this.setSelectedStatus();
        this.is_need_menu = !this.ctxServ.getIsHideLeftMenu();
        if (this.isRouteToApps) {
          this.setCopyMenuItem();
          this.isRouteToApps = false;
          return;
        }
        if (this.isSwitchSpace) {
          this.setCopyMenuItem();
        }
        this.initMenu();
        this.isSwitchSpace = false;
      });
    if (!this.isRouteSub) {
      const urlStr = window.location.hash.slice(7);
      this.routeUrl = urlStr.split('?')[0];
      this.routeParams = this.getUrlParams(urlStr);
      this.is_need_menu = !this.ctxServ.getIsHideLeftMenu();
      this.initMenu();
    }
  }

  // 根据权限过滤项目
  private filterItems(permissions: any): void {
    // 复制原始项目列表
    if (this.isMarket) {
      if (!this.marketItems) {
        return;
      }
      this.filteredItems = [...this.marketItems];
    } else {
      if (!this.items) {
        return;
      }
      this.filteredItems = [...this.items];
    }
    if (permissions && permissions.OPERATOR) {
      this.filteredItems = this.filteredItems.filter(item => item.label !== this.i18NextEagerPipe.transform('develop-center'));
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    // 监听Input 数值的变化
    if (changes.items) {
      const currentPermissions = this.permissionService.getCurrentPermissions();
      this.filterItems(currentPermissions);
      this.initMenu();
    }
  }

  // 初始化菜单信息
  private setCopyMenuItem() {
    this.copyItems.length = 0;
    this.cacheMenuData.parent.length = 0;
    this.cacheMenuData.children.length = 0;
  }

  // 初始化菜单栏的折叠状态
  private initMenu() {
    this.setCopyMenuItem();
    const menuStateCache = this.loadUserMenuState();
    for (let index = 0; index < this.filteredItems.length; index++) {
      const item = JSON.parse(JSON.stringify(this.filteredItems[index]));
      this.copyItems.push(item);
      // 如果userMenuState不是空对象（即包含键），从其获取折叠状态
      if (menuStateCache && Object.keys(menuStateCache).length > 0) {
        if (item.isGroup && item.children && item.children.length > 0) {
          item.children[0].collapseStatus = menuStateCache[item.id] ?? 1;
        }
      } else {
        // 没有用户菜单缓存则使用默认配置
        if (
          this.routeUrl === 'overview' &&
          item.id === 'develop-center' &&
          (Object.keys(menuStateCache).length === 0 || menuStateCache[item.id] === undefined)
        ) {
          item.children[0].collapseStatus = 2;
        }
      }
    }
    for (let index = 0; index < this.copyItems.length; index++) {
      if (this.copyItems[index].children && this.copyItems[index].children.length > 0) {
        const childData = this.copyItems[index].children;
        let isFinish = false;
        for (let childIndex = 0; childIndex < childData.length; childIndex++) {
          if (isFinish) {
            break;
          }
          if (childData[childIndex].collapseStatus && childData[childIndex].children) {
            // 需要进一步去for循环迭代
            isFinish = this.handleSecondChildData(childData, childIndex, index);
            continue;
          }
          // 如果没有包含
          if (this.isContainRouteUrl(childData[childIndex])) {
            isFinish = true;
            break;
          }
        }
        if (isFinish) {
          break;
        }
      }
    }
    this.cdr.detectChanges();
  }

  private isContainRouteUrl(data: any): boolean {
    return (data.router && data.router.indexOf(this.routeUrl) > -1) || (data.routerList && data.routerList.flat().indexOf(this.routeUrl) > -1);
  }

  private handleSecondChildData(childData: any[], childIndex: number, index: number): boolean {
    const childChildren = childData[childIndex].children;
    let isFinish = false;
    for (let childChildIndex = 0; childChildIndex < childChildren.length; childChildIndex++) {
      if (this.isContainRouteUrl(childChildren[childChildIndex])) {
        childData[childIndex].collapseStatus = 2;
        this.cacheMenuData.parent.push(childData[childIndex]);
        this.handleNodeClick('' as any, childChildren[childChildIndex], index, childIndex, true);
        isFinish = true;
        break;
      }
    }
    return isFinish;
  }

  getClassName(menuItem: any): string {
    if ((menuItem.router && menuItem.router.indexOf(this.routeUrl) > -1) || (menuItem.routerList && menuItem.routerList.flat().indexOf(this.routeUrl) > -1)) {
      return 'is-selected';
    }
    return '';
  }

  getIcon(menuItem: any): string {
    if ((menuItem.router && menuItem.router.indexOf(this.routeUrl) > -1) || (menuItem.routerList && menuItem.routerList.flat().indexOf(this.routeUrl) > -1)) {
      return menuItem.iconSelected;
    }
    return menuItem.icon;
  }

  isContainSecondMenu(menuItem: any): boolean {
    return menuItem.children && menuItem.children.length > 0 && menuItem.collapseStatus === 2;
  }

  isLeafNode(menuItem: any): boolean {
    return !menuItem.children || (menuItem.children && menuItem.children.length === 0);
  }

  getMenuMaxHeight(menuItem: any): string {
    if (menuItem.children) {
      // 如果有子菜单
      if (menuItem.children.length > 0 && menuItem.collapseStatus === 2) {
        // 如果子菜单展开
        return '200px';
      } else {
        // 如果子菜单未展开
        return '26px';
      }
    } else {
      // 如果没有子菜单
      return '38px';
    }
  }

  getMenuHeight(menuItem: any): string {
    if (menuItem.children && menuItem.children.length > 0) {
      // 如果有子菜单
      return '26px';
    } else {
      // 如果没有子菜单
      return '38px';
    }
  }

  public onClick(event: Event) {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }
  }

  /**
   * 阻止下拉面板收起
   * @param event
   */
  footerClick(event: MouseEvent) {
    event.preventDefault();
  }

  create_space_fn() {
    const modal = this.nzModalService.create<CreateSpaceComponent, any>({
      nzTitle: this.i18NextEagerPipe.transform('create_space'),
      nzContent: CreateSpaceComponent,
      nzWidth: 600,
      nzMaskClosable: false,
      nzFooter: null,
    });

    modal.afterClose.subscribe(() => {
      this.get_space();
    });
  }

  private commonGetWorkSpaceCode(workspaceList: any) {
    this.space_options.length = 0;
    this.space_options = workspaceList;
    this.space_options = this.space_options.filter((item: any) => item.name);
    this.copy_space_options = this.space_options;
  }

  async get_space() {
    await this.spaceTeamManagementService
      .getWorkspace()
      .then(res => {
        res.workspaceList.forEach(ws => {
          if (ws.type === 'PERSON' && this.lang === 'en-us') {
            ws.name = this.i18n.transform('personal_space');
          }
        });
        const workspaceList = res.workspaceList;

        this.commonGetWorkSpaceCode(workspaceList);
        // 存储最新的下拉选项
        StorageService.setSessionStorage('SPACE_OPTIONS', JSON.stringify(workspaceList));
      })
      .finally(() => {});
  }

  set_current_sapce() {
    const cur_space = this.space_options?.filter(item => item.type === 'PERSON')[0];
    this.space_value = cur_space?.id ?? '';
    this.space_name = cur_space?.name ?? '';
    this.space_icon = cur_space.icon;
    this.ctxServ.addUserIdToLocal(cur_space);
    StorageService.setSessionStorage('CUR_SPACE_OPTIONS', JSON.stringify(cur_space));
    const params = {
      is_neeed_reload: true, // 这个判断是否跳转至首页
      cur_space: cur_space,
    };
    this.spaceTeamManagementService.updateSpaceOptionsSelected(params);
  }

  async get_space_member_roles() {
    await this.spaceTeamManagementService.getSpaceMemberRoles().then((res: any) => {
      this.roles_list = res.roleList ?? [];
      StorageService.setSessionStorage('ROLES', JSON.stringify(this.roles_list));
    });
  }

  /**
   * 搜索工作空间
   * **/
  public searchMyWorkSpace(searchWord: string) {
    this.searchSpaceLoading = true;

    setTimeout(() => {
      this.searchSpaceLoading = false;
      if (searchWord === '' || searchWord === undefined || searchWord === null) {
        this.space_options = this.copy_space_options;
        return;
      }
      const tempArr = [];
      for (let index = 0; index < this.copy_space_options.length; index++) {
        if (this.copy_space_options[index].name && this.copy_space_options[index].name.indexOf(searchWord) > -1) {
          tempArr.push(this.copy_space_options[index]);
        }
      }
      this.space_options = tempArr;
    });
  }

  public async createApp() {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    this.isRouteToApps = true;
    this.router.navigate(['/home/agent-center/create']);
  }

  async isResourceExceed() {
    const res = await this.appAgentRepoServ.getResourceQuantity('agent');
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

  computeSideNavStyle() {
    return {
      height: `${this.windowHeight - 48}px`,
    };
  }

  handleClickSpaceSelectBox() {
    this.isRotate = true;
  }

  handleBlurSpaceSelectBox() {
    this.isRotate = false;
    this.isFocusSpaceSelectBox = false;
  }

  handleFocusSpaceSelectBox() {
    this.isFocusSpaceSelectBox = true;
  }

  protected readonly cdnAssetUrl = cdnAssetUrl;

  ngOnDestroy(): void {
    window.removeEventListener('click', this.handleClickOutMenu);
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
    if (this.subscribeBtnStatusSubscription) {
      this.subscribeBtnStatusSubscription.unsubscribe();
    }
  }

  changeLanguage(lang: string) {
    if (lang === 'zh-cn') {
      this.selectLanguage.label = '简体中文';
    } else if (lang === 'en-us') {
      this.selectLanguage.label = 'English';
    }
    this.selectLanguage.id = lang;
    window.localStorage.setItem('jiuwenlang', lang);
    window.location.reload();
  }

  getChildMenuStyle(menuItem: any) {
    if (menuItem.children && menuItem.children.length > 0) {
      return { color: 'rgb(89,89,89)', fontSize: '12px', fontWeight: 600 };
    }
    return { color: 'rgb(25,25,25)', fontSize: '14px' };
  }

  public routeToResourceManage() {
    this.router.navigate([`/home/platform-management/resource-management`]);
  }

  public routeToAuthorizationManage() {
    if (this.isSelectedAuthorizationManage) {
      return;
    }
    this.router.navigate([`/home/platform-management/authorization-management`]);
  }

  private setSelectedStatus() {
    let routeUrl = window.location.hash.slice(7);
    this.isSelectedResourceManage = routeUrl === 'platform-management/resource-management';
    this.isSelectedAuthorizationManage = routeUrl.startsWith('platform-management/authorization-management');
  }

  public collapseMenu() {
    this.isMenuExpand = false;
    this.lockMouseEnter();
    this.cdr.markForCheck();
    this.expandMenuData.length = 0;
    for (let index = 0; index < this.copyItems.length; index++) {
      if (!this.copyItems[index].children || this.copyItems[index].children.length <= 0) {
        continue;
      }
      for (let _index = 0; _index < this.copyItems[index].children.length; _index++) {
        if (!this.copyItems[index].children[_index].children) {
          this.expandMenuData.push(this.copyItems[index].children[_index]);
          continue;
        }
        for (let thirdIndex = 0; thirdIndex < this.copyItems[index].children[_index].children.length; thirdIndex++) {
          this.expandMenuData.push(this.copyItems[index].children[_index].children[thirdIndex]);
        }
      }
    }
  }

  public expandMenu() {
    this.isMenuExpand = true;
    this.cdr.markForCheck();
  }

  private recordUserMenuState() {
    const menuStateCache: any = {};
    this.copyItems.forEach(item => {
      // 记录用户菜单的展开状态
      if (item?.isGroup) {
        menuStateCache[item.id] = item?.children[0]?.collapseStatus ?? 1;
      }
    });

    const userMenuState: any = this.loadUserMenuState();

    userMenuState[this.ctxServ.user.userId] = menuStateCache;
    StorageService.setLocalStorage('USER_MENU_STATE', JSON.stringify(userMenuState));
  }
  private loadUserMenuState() {
    const userMenuStateStr = StorageService.getLocalStorage('USER_MENU_STATE');
    let userMenuState: any;
    try {
      userMenuState = JSON.parse(userMenuStateStr) ?? {};
    } catch (e) {
      return {};
    }
    return userMenuState[this.ctxServ.user.userId] ?? {};
  }
  goBack() {
    this.router.navigate([`/home/overview`]);
  }

  initIsMarket(url = '') {
    const currentPermissions = this.permissionService.getCurrentPermissions();
    const marketUrl = [
      '/app-library',
      '/service-market',
      '/plugin-market',
      'prompt/prompt-template',
      'knowledge-center/kb-plaza',
      '/model-square',
      '/skill-market',
    ];
    let hasMarketUrl = marketUrl.find(v => url.includes(v));
    if (hasMarketUrl) {
      this.isMarket = true;
      this.filterItems(currentPermissions);
    } else {
      this.isMarket = false;
      this.filterItems(currentPermissions);
    }
    this.cdr.detectChanges();
  }

  // 处理路由返回时带的参数
  public getUrlParams(url) {
    // 如果 url 中没有 ?，直接返回空对象
    if (url.indexOf('?') === -1) {
      return {};
    }
    // 截取第一个 ? 之后的字符串
    let queryString = url.substring(url.indexOf('?') + 1);
    let params = {};

    // 用 & 分割参数
    let pairs = queryString.split('&');

    // 遍历每个参数
    for (let i = 0; i < pairs.length; i++) {
      let pair = pairs[i].split('=');
      let key = decodeURIComponent(pair[0]);
      let value = decodeURIComponent(pair[1] || '');

      // 保存到对象中
      params[key] = value;
    }

    return params;
  }

  /**
   * 1. URL中有没有workspace_id，如果有，使用url中参数
   * 2. session中是否有缓存，如果有，使用缓存
   * 3. 使用个人空间
   * @returns
   */
  private handlerWorkSpace() {
    if (this.queryWorkSpace) {
      const curSpace = this.space_options?.find(item => item.id === this.queryWorkSpace);
      if (curSpace) {
        StorageService.setSessionStorage('CUR_SPACE_OPTIONS', JSON.stringify(curSpace));
        this.initWorkSapce(curSpace);
        return;
      }
    }
    const currentSpace = StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
    if (currentSpace && currentSpace !== '{}') {
      try {
        const spaceObj = JSON.parse(currentSpace);
        this.initWorkSapce(spaceObj);
        return;
      } catch (err) {}
    }
    // 设置空间为默认账户,再将默认账户更新到session中 进行兜底
    const firstSpace = this.space_options?.find(item => item.type === 'PERSON');
    this.space_value = firstSpace?.id ?? '';
    this.space_name = firstSpace?.name ?? '';
    StorageService.setSessionStorage('CUR_SPACE_OPTIONS', JSON.stringify(firstSpace));
  }

  private initWorkSapce(data) {
    this.space_value = data?.id ?? '';
    this.space_name = data.type === 'PERSON' ? this.i18n.transform('personal_space') : data.name;
    this.space_icon = data.icon;
    const params = {
      is_neeed_reload: false, // 无需跳转至overview页面
      cur_space: data,
    };
    this.spaceTeamManagementService.updateSpaceOptionsSelected(params);
  }
}
