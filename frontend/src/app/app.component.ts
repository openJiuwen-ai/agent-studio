import { registerLocaleData } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import zh from '@angular/common/locales/zh';
import {
  ChangeDetectorRef,
  Component,
  Inject,
  OnInit, TemplateRef, ViewChild
} from '@angular/core';
import { Title } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { NzModalService } from 'ng-zorro-antd/modal';
import { POC_JS_SESSION_KEY } from '@constants/exp-tmpl-config.const';
import { ConsoleFrameworkService } from '@core/services';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { CommonService } from '@services/common.service';
import { ContextService } from '@services/context.service';
import { HttpService } from '@services/http.service';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { Subscription } from 'rxjs';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { PermissionService } from '@services/permission.service';
import { MasOperatorService } from '@services/mas-operator.service';
import { LinkInterceptorService } from '@services/LinkInterceptorService';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { StorageService } from '@shared/services/cfdata.service';
import { initHistoryInterceptor } from "../utils/utils";
import {
  clearSsoCookie,
  consumeSsoAuthFromUrl,
  hasRecentAuthParamAttempt,
} from '../utils/sso-auth.util';
import { PE_SESSION_KEY } from '@constants/exp-tmpl-config.const';

registerLocaleData(zh);

interface UserContext {
  projectId: string;
  userId: string;
}

@Component({
  selector: 'root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.less'],
  imports: [
    MODULES,
    ...COMMON_MODULES,
  ],
  providers: [
    HttpClient,
    {
      provide: angularI18next.I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM, I18nNamespace.AGENT],
    }
  ],
  standalone: true
})
export class AppComponent implements OnInit {
  @ViewChild('templateSafeTipContent', { static: true })
  public myTemplateRef: TemplateRef<any>;
  public safeTipContext = { contentName: '', contentUrl: '' };
  /** 订阅 */
  #subscriptions: Subscription[] = [];

  public pageInited = false;

  private workspaceList = [];

  public canUse: boolean = true;

  public permissionUse: boolean = true;

  public permissionMessage: string = '';

  public isUpdated: boolean = false;

  constructor(
    @Inject(angularI18next.I18NEXT_SERVICE)
    private readonly i18NextService: angularI18next.ITranslationService,
    private readonly title: Title,
    private readonly i18NextEagerPipe: angularI18next.I18NextEagerPipe,
    private readonly changeDetectorRef: ChangeDetectorRef,
    private readonly ctxServ: ContextService,
    private readonly http: HttpService,
    private readonly consoleFrameworkService: ConsoleFrameworkService,
    private appAgentRepoServ: AppAgentRepoService,
    private configServ: AgentConfigService,
    private readonly commonService: CommonService,
    private router: Router,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private permissionService: PermissionService,
    private masOperatorService: MasOperatorService,
    private linkInterceptorService: LinkInterceptorService,
    private modal: NzModalService,
    private modelManagementService: ModelManagementService,
  ) {
    this.#subscribe();
    this.#init();
    this.#closeSecAlert();
  }

  async ngOnInit(): Promise<void> {
    this.initLinkInterceptor();
    this.http.getPermissionError().subscribe((data) => {
      if (data?.error_code === 'Openjiuwen.02001084') {
        this.permissionUse = false;
        this.permissionMessage = data?.error_msg || this.i18NextEagerPipe.transform('app_component_2');
      }
    });
  }

  /** 初始化a标签和window.open的点击跳转事件 **/
  private initLinkInterceptor(): void {
    this.linkInterceptorService.init({
      allowExternal: false,
      allowSameOrigin: true,
      callback: (type, url, isBlank) => {
        this.safeTipContext = {
          contentName: this.i18NextEagerPipe.transform('leave-site'),
          contentUrl: url,
        };
        this.modal.confirm({
          nzTitle: this.i18NextEagerPipe.transform('app-tip-safe'),
          nzContent: this.myTemplateRef,
          nzClassName: 'modal-class-safe-wrapper',
          nzCancelText: this.i18NextEagerPipe.transform('cancel'),
          nzOkText: this.i18NextEagerPipe.transform('continue'),
          nzAutofocus: 'auto',
          nzOnOk: (): void => {
            this.linkInterceptorService.updateOptions(true);
            if (isBlank) {
              window.open(url, '_blank');
            } else {
              window.location.href = url;
            }
          },
        });
      }
    });
  }

  /**
   * 初始化
   */
  async #init() {
    // 判断是不是在同一个域名下
    if(this.judgeHostAndPathName()){
      StorageService.setSessionStorage('CUR_SPACE_OPTIONS', '{}')
    }
    this.#initTiny();
    this.#initFurion();

    this.initPocServiceType();

    // 尽早注册 hashchange：初始化期间（含 getHealth 网络往返）父平台变更
    // hash 换 token 的事件不再丢失
    window.onhashchange = () => {
      // 监听hashchange事件
      this.changeRouter();
      // iframe SSO：父平台在页面已加载后变更 hash 刷新/更换 Auth token 时即时消费。
      // 只要本次消费遇到 Auth（无论成败）都清理旧用户态（身份意图已表达）。
      // 清理只作用于持久层（Cookie/存储），运行中 SPA 的内存态（ContextService
      // 用户、路由、组件状态）无法就地重置——清后一律 reload 重新初始化，否则
      // 页面停留在"存储已登出、内存仍是旧用户"的不一致状态（workspace_id 取
      // 不到、请求被鉴权拒绝），直到下一次 hashchange 或手动刷新才恢复。
      // 失败重试预算由写入失败计数的 sessionStorage 持久化保护：reload 后
      // resetUserData 再次消费，再次失败即达上限剥除 Auth，此后不再触发消费
      // ——最多自动重试一次，不构成 reload 循环。
      const consumed = consumeSsoAuthFromUrl();
      if (consumed || hasRecentAuthParamAttempt()) {
        this.clearStaleUserState(!consumed);
        window.location.reload();
      }
    };

    await this.initLiteUserDate();

    initHistoryInterceptor();
    this.changeRouter();
  }

  judgeHostAndPathName(){
    const host_path_url= StorageService.getSessionStorage('HOST_PATH_URL')
    const host_path_name = `${location.protocol}//${location.host}${location.pathname}`
    StorageService.setSessionStorage('HOST_PATH_URL',host_path_name);
    if(host_path_url){
      return host_path_url !== host_path_name
    }
    return  false

  }

  async init_space() {
    await this.spaceTeamManagementService
      .getWorkspace()
      .then((res) => {
        res.workspaceList.forEach(ws=>{
          if(ws.type === 'PERSON'){
            ws.name = this.i18NextEagerPipe.transform('personal_space')
          }
        })
        this.workspaceList = res.workspaceList;
        StorageService.setSessionStorage(
          'SPACE_OPTIONS',
          JSON.stringify(this.workspaceList),
        );
        const current_space_options = StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
        if (current_space_options && current_space_options !== '{}') {
          const current_space_options_obj = JSON.parse(current_space_options);
          // 判断是否是同一个账户登录，有可能是不同账户登录
          const wlist = this.workspaceList.filter(
            (witem) => witem.id === current_space_options_obj?.id,
          );
          if (!wlist.length) {
            StorageService.setSessionStorage('CUR_SPACE_OPTIONS', '{}');
            this.setWorkspaceDefault(true);
          } else {
            StorageService.setSessionStorage(
              'CUR_SPACE_OPTIONS',
              JSON.stringify(wlist[0]),
            );
          }
        } else {
          StorageService.setSessionStorage('CUR_SPACE_OPTIONS', '{}');
          this.setWorkspaceDefault(false);
        }
      })
      .finally(() => {});
  }

  setWorkspaceDefault(type = false) {
    // 设置空间wi默认账户
    const cur_space = this.workspaceList?.filter(
      (item) => item.type === 'PERSON',
    )[0];
    this.ctxServ.addUserIdToLocal(cur_space);
    StorageService.setSessionStorage(
      'CUR_SPACE_OPTIONS',
      JSON.stringify(cur_space),
    );
    if (type) {
      window.location.reload();
    }
  }

  initPocServiceType() {
    const POC_BASE_HREF = 'openjiuwen';
    const pathnames = window.location.pathname.split('/').filter(Boolean);

    if (
      pathnames.length &&
      pathnames[0] !== POC_BASE_HREF
    ) {
      this.http.setPocServicePrefix(pathnames[0]);
    }
  }

  initUserDate(userCtx?: UserContext) {
    this.ctxServ.refreshUserData().subscribe({
      next: async () => {
        this.modelManagementService.getMaaSModalSubscribe(true).then();
        await this.afterContextReady(userCtx);
        await this.init_space();
        this.permissionService.fetchPermissions().subscribe({
          next: (permissions) => {},
        });
        this.masOperatorService.fetchMasOperators().subscribe({
          next: (permissions) => {},
        });
      },
    });
  }

  async afterContextReady(userCtx?: UserContext) {
    await this.initConfigs();
    this.ctxServ.pocIsOpAccount =
      this.configServ.getConfigs().opsvc_project_id === userCtx?.projectId;

    this.pageInited = true;
  }

  async initLiteUserDate() {
    try {
      await this.resetUserData();
    } catch (e) {
      //临时处理，本地启动环境变量poc，进入本逻辑，待整理环境变量
    }
    const AGENT_SID = StorageService.getCookie('AGENT_SID');
    const [userId, projectId] = (AGENT_SID || '').split('|');

    StorageService.setLocalStorage(
      POC_JS_SESSION_KEY,
      JSON.stringify({
        userId,
        projectId,
      }),
    );

    this.initUserDate({ userId, projectId });
  }

  // SSO 换凭证时清理旧用户态：AGENT_SID Cookie 与本地/会话存储中的用户、
  // 会话与空间信息，确保按新凭证重新初始化（否则首个 getHealth 前的请求会读到
  // 旧 workspace/用户态，造成新凭证与旧状态不一致）。写入失败时
  // （clearAccessToken=true）连带清除旧 Access-Token Cookie——否则后续
  // getHealth 会携带旧凭证以旧身份重新登录，违背"失败降级为未登录"的意图；
  // 写入成功时保留（即新 token）。
  // Cookie 须显式 path=/ 删除：AGENT_SID 由后端（ServletUtils.buildAgentSidCookie）
  // 以 path=/ 下发、Access-Token 由本应用以 path=/ 写入；通用 delCookie 的
  // 删除串不带 path 属性（默认为当前文档路径），文根部署（/console、
  // /openjiuwen 等）下无法命中 path=/ 的同名 Cookie，删除会静默失败。
  // PE_SESSION_KEY 由 ContextService.refreshUserData 双写 localStorage 与
  // sessionStorage，两处都要清；SPACE_OPTIONS（init_space 写入的完整空间
  // 列表）与 CUR_SPACE_OPTIONS（当前空间）同为 sessionStorage 的旧空间态。
  clearStaleUserState(clearAccessToken: boolean): void {
    // AGENT_SID 当前由后端 ServletUtils.buildAgentSidCookie 以 path=/ 且不带
    // Domain 属性（host-only）下发，首条 host-only 删除串即可命中；追加
    // domain 变体防御后端/网关未来改以 Domain 属性下发（或历史上存在
    // domain 版 Cookie）时删除静默失败——写入已过期的 domain Cookie 无
    // 残留副作用，IP 部署下 domain 属性非法被浏览器忽略、同样无害
    document.cookie = 'AGENT_SID=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    document.cookie = `AGENT_SID=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=${location.hostname}`;
    if (clearAccessToken) {
      clearSsoCookie();
    }
    StorageService.delLocalStorage(PE_SESSION_KEY);
    StorageService.delSessionStorage(PE_SESSION_KEY);
    StorageService.delLocalStorage(POC_JS_SESSION_KEY);
    StorageService.delSessionStorage('SPACE_OPTIONS');
    StorageService.delSessionStorage('CUR_SPACE_OPTIONS');
  }

  //如果url参数带用户信息，取出调health接口setCookie，后清除url参数
  async resetUserData() {
    // iframe SSO 场景：解析 hash 中 Auth 参数写入 Access-Token Cookie（须早于 getHealth）。
    // 最近一次消费曾遇到 Auth（无论写入成败、甚至已达清理上限被剥除），父平台
    // 已表达身份意图——清理旧用户态，确保按新凭证而非旧状态初始化；写入失败
    // 时同样清理并连带清除旧 Access-Token：让应用可见地降级为未登录，而不是
    // 沿用旧用户身份。首次加载写入失败不自动 reload 重试：失败原因均为持续性
    // （浏览器拦截/非法字符/未确认/遮蔽），自动重试只会额外刷新且中断初始化；
    // 重试入口 = 手动 reload 或父平台重新挂载 iframe
    const consumed = consumeSsoAuthFromUrl();
    if (consumed || hasRecentAuthParamAttempt()) {
      this.clearStaleUserState(!consumed);
    }
    const url = new URL(window.location.href);
    const params = new URLSearchParams(url.search);

    const paramsUserId = params.get('x-user-id');
    const paramsProjectId = params.get('x-project-id');
    if (paramsUserId && paramsProjectId) {
      await this.appAgentRepoServ.getHealth(paramsUserId, paramsProjectId);
      this.clearParam();
    }
    const AGENT_SID = StorageService.getCookie('AGENT_SID');
    const [userId, projectId] = (AGENT_SID || '').split('|');
    //如果没有用户信息，调用health接口获取默认用户
    if (!userId || !projectId) {
      await this.appAgentRepoServ.getHealth();
    }
  }

  clearParam() {
    try {
      const url = new URL(window.location.href);
      const params = new URLSearchParams(url.search);

      params.delete('x-user-id');
      params.delete('x-project-id');

      const newQueryString = params.toString();
      const newUrl =
        url.pathname + (newQueryString ? '?' + newQueryString : '') + url.hash;

      window.history.pushState({}, '', window.location.origin + newUrl);
    } catch (e) {
      //不做处理
    }
  }

  public async initConfigs() {
    try {
      const data = await this.appAgentRepoServ.getConfigs();
      if (!Object.keys(data).includes('safety_barrier_display')) {
        data.safety_barrier_display = true;
      }
      this.configServ.setConfigs(data);
    } catch (e) {
      this.http.confirmFn();
    }
  }

  /**
   * 初始化 Tiny
   */
  // TODO 是不是要删除
  #initTiny() {}

  /**
   * 订阅
   */
  #subscribe() {
    this.#subscriptions = [
      ...this.#subscriptions,
      this.i18NextService.events.languageChanged.subscribe(() => {
        this.title.setTitle(
          this.i18NextEagerPipe.transform('jiuwen_devops_head_title', {
            ns: I18nNamespace.PROMPT_PLATFORM,
          }),
        );
        this.changeDetectorRef.markForCheck();
      }),
    ];
  }

  #closeSecAlert() {
    const SEC_KEY = 'securityCheckClose';
    const securityCheckCloseLocal = StorageService.getLocalStorage(SEC_KEY);
    const securityCheckCloseCookie = StorageService.getCookie(SEC_KEY);

    if (securityCheckCloseLocal !== 'true') {
      StorageService.setLocalStorage(SEC_KEY, 'true');
    }

    if (securityCheckCloseCookie !== 'true') {
      StorageService.setCookie(SEC_KEY, 'true');
    }
  }

  #initFurion(): void {
    return;
  }

  changeRouter() {

  }
}
