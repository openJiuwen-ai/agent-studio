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

    await this.initLiteUserDate();

    initHistoryInterceptor();
    this.changeRouter();

    window.onhashchange = () => {
      // 监听hashchange事件
      this.changeRouter();
    };
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

  //如果url参数带用户信息，取出调health接口setCookie，后清除url参数
  async resetUserData() {
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
