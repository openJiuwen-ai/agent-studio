import { Component, ChangeDetectionStrategy, Input, Output, ChangeDetectorRef, EventEmitter } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { InlineSvgComponent } from '@shared/components/inline-svg.component';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import type { IPlugin } from '../app-plugin.interface';
import { pluginSchemaStr2Args, initializeReqItem } from '../utils';
import { PublishVersionModalComponent } from '@shared/components/publish-version-modal/publish-version-modal.component';
import { PluginDebugModalComponent } from '../components/plugin-debug-modal/plugin-debug-modal.component';
import { PluginReferenceComponent } from '../components/plugin-reference/plugin-reference.component';
import { NgIf } from '@angular/common';
import { AddPluginAuthComponent } from '@routes/plugin-market/add-plugin/add-plugin-auth.component';
import { PluginCredentialStatus } from '@enums/agent-center.enum';
import { PermissionService } from '@services/permission.service';
import { PrevRouteService } from '@services/prev-route.service';
import { ShareDetailBtnComponent } from '@routes/app-center/components/share-detail-btn/share-detail-btn.component';
import { SHARE_PAGE, SHARE_TOOL_TYPE } from '@routes/app-center/components/edit-share-modal/edit-share-modal.config';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import { ShareService } from '@routes/app-center/components/edit-share-modal/share.service';
import { CommonUtils } from 'src/utils/common.util';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService, NzDrawerModule } from 'ng-zorro-antd/drawer';
enum mapKeys {
  credential_status = 'credential_status',
  auth_required = 'auth_required',
}

@Component({
  selector: 'meta-plugin-header-new',
  standalone: true,
  imports: [COMMON_MODULES, MODULES, InlineSvgComponent, ShareDetailBtnComponent, NzDrawerModule],
  templateUrl: './plugin-header.component.html',
  styleUrl: './plugin-header.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginHeaderNewComponent {
  @Input() pluginInfo;
  @Input() isToolDetail: boolean = false;
  @Output() update = new EventEmitter<void>();
  @Output() visionSelectedChangeEvent = new EventEmitter();
  public successIcon = cdnAssetUrl('assets/images/flow-task/success.svg');
  public lang = CommonUtils.getLanguage();
  public noAuthIcon = cdnAssetUrl('assets/images/flow-task/un-auth.svg');

  historyVersionList = [];

  test_status: 'SUCCESS' | 'FAILED' | 'UNKNOWN';

  private destroy$ = new Subject<void>();

  public placeholderStr: string = this.i18n.transform('select_placeholder');

  public isPluginMarket = true;
  public currentPermissions: any;
  private permissionSubscription: Subscription;
  public isShare = false;
  public canEditShare = false;
  public visionsOptions = [];
  public visionSelected = '';
  pluginId = '';
  shareTag = '';
  pageType = SHARE_PAGE.plugin;
  toolType = SHARE_TOOL_TYPE.plugin;
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public shareInfo: any = {};
  private pageFromId: any;
  private pageFrom: any;
  constructor(
    private router: Router,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private appPluginRepoServ: AppPluginRepoService,
    private agentDataServe: AgentDataService,
    private permissionService: PermissionService,
    private activeRoute: ActivatedRoute,
    public commonService: CommonService,
    private readonly http: HttpService,
    private shareService: ShareService,
    private nzModal: NzModalService,
    private nzDrawerService: NzDrawerService
  ) {}

  ngOnInit() {
    this.activeRoute.queryParams.subscribe(params => {
      this.pageFromId = params.from_id;
      this.pageFrom = params.from;
    });
    this.pluginId = this.activeRoute.snapshot.queryParams.id || this.activeRoute.snapshot.queryParams.plugin_id;
    this.isShare = this.activeRoute.snapshot.queryParams.pageType === 'share';
    this.visionSelected = this.activeRoute.snapshot.queryParams.releaseVersion;
    if (this.isShare && !this.isToolDetail) {
      this.getShareDetail();
    }
    this.isPluginMarket = this.router.url.indexOf('plugin-market/detail') > -1;
    this?.agentDataServe
      .publishStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        if (status === 'succeeded') {
          this.pluginInfo = { ...this.pluginInfo };
          this.cdr?.markForCheck();
        }
      });
    // 订阅权限变化
    this.permissionSubscription = this.permissionService.permissions$.subscribe(permissions => {
      this.currentPermissions = permissions;
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  ngOnChanges(): void {
    this.test_status = this.pluginInfo.test_status;
  }

  public hasPermission(): boolean {
    return this.currentPermissions && this.currentPermissions.OPERATOR;
  }

  public getPluginName() {
    if (this.lang === 'zh-cn') {
      return `${this.pluginInfo?.plugin_chinese_name}(${this.pluginInfo?.plugin_display_name})`;
    } else {
      return this.pluginInfo?.plugin_display_name ?? '--';
    }
  }
  public openDebugModal() {
    let requestArgs = pluginSchemaStr2Args(this.pluginInfo?.input_schema);

    const {
      plugin_display_name,
      plugin_desc,
      visibility,
      plugin_chinese_name,
      request_info,
      is_input_list,
      auth_info,
      is_output_list,
      intf_type,
      input_schema,
    } = this.pluginInfo;
    let pluginBodyParams = {
      plugin_display_name,
      plugin_desc,
      visibility,
      plugin_chinese_name,
      request_info,
      auth_info,
      is_input_list,
      is_output_list,
      intf_type,
      icon: undefined,
      input_schema,
    };

    const modalRef: any = this.nzModal.create({
      nzContent: PluginDebugModalComponent,
      nzWidth: '1000px',
      nzFooter: null,
      nzClosable: true,
      nzMaskClosable: false,
    });
    const instance = modalRef.getContentComponent();
    instance.hideParseBtn = true;
    instance.requestArgs = requestArgs.map(item => initializeReqItem(item));
    instance.pluginBodyParams = this?.pluginInfo.tool_id ? { tool_id: this.pluginInfo.tool_id } : pluginBodyParams;

    instance.dismiss.subscribe(async () => {
      const result = instance?.instance?.debugResult;
      if (!result) {
        return;
      }

      if (result?.success) {
        this.test_status = 'SUCCESS';
      }

      if (result?.success === false) {
        this.test_status = 'FAILED';
      }

      const params = {
        data: { ...pluginBodyParams, test_status: this.test_status },
        id: this.pluginInfo?.plugin_id,
      };

      await this.appPluginRepoServ.updatePlugins(params);
      this.cdr.markForCheck();
    });
  }

  getPublishTip() {
    if (this.test_status === 'SUCCESS') {
      return '';
    } else if (this.test_status === 'FAILED') {
      return this.i18n.transform('plugin_debugging_failed_tip');
    } else if (this.pluginInfo.test_status === 'UNKNOWN') {
      return this.i18n.transform('plug_not_debug_tip');
    } else {
      return '';
    }
  }

  getReference() {
    const modalRef: any = this.nzDrawerService.create({
      nzContent: PluginReferenceComponent,
      nzWidth: 600,
      nzData: {
        tool_id: this.pluginInfo.plugin_id,
        type: 'system',
      },
    });
  }

  gotoPluginList() {
    let state: any = {
      formTab: this.isShare ? 'share' : '',
    };
    if (this.canEditShare) {
      state.myShare = true;
    }
    this.router.navigate(['/home/plugin-market'], { state });
  }

  onPageBack() {
    if (this.pageFrom === 'flow') {
      this.router.navigate(['/home/agent-center/app-flow/flow'], {
        queryParams: {
          id: this?.pageFromId,
        },
      });
    } else if (this.pageFrom === 'overview') {
      this.router.navigate(['/home/overview']);
    } else if (this.isToolDetail) {
      this.router.navigate(['/home/plugin-market/market-detail'], {
        queryParams: {
          id: this.pluginId,
          pageType: this.isShare ? 'share' : '',
          releaseVersion: this.visionSelected,
        },
      });
    } else {
      this.gotoPluginList();
    }
  }

  public handleClickAddAuthConfig(item, e) {
    e.stopPropagation();
    const modalRef: any = this.nzModal.create({
      nzContent: AddPluginAuthComponent,
      nzWidth: '700px',
    });
    const instance = modalRef.getContentComponent();
    instance.pluginInfo = item;
    instance.close.subscribe(() => {
      this.update.emit();
    });
  }

  public isShowAuthConfigBtn(plugin: IPlugin) {
    return !!(
      plugin[mapKeys.credential_status] === PluginCredentialStatus.AUTHENTICATED ||
      plugin[mapKeys.credential_status] === PluginCredentialStatus.UNAUTHENTICATED ||
      plugin[mapKeys.auth_required]
    );
  }

  public authConfigName(plugin: IPlugin) {
    if (plugin[mapKeys.credential_status] === PluginCredentialStatus.AUTHENTICATED) {
      return this.i18n.transform('pluginheadercomponent_1149');
    }
    return this.i18n.transform('configAuth');
  }

  visionSelectedChange(id: string) {
    this.visionSelected = id;
    // 重新请求详情
    this.visionSelectedChangeEvent.emit(this.visionSelected);
  }

  changeShearVersion(id: string) {
    this.visionSelected = id;
    this.getShareDetail();
    this.visionSelectedChangeEvent.emit(this.visionSelected);
  }

  async getShareDetail() {
    const res = await this.shareService.getShareDetail(this.pluginId, { release_version: this.visionSelected, resource_type: 'plugin' });
    this.canEditShare = res.resource_workspace_id === this.http.getWorkspaceId();
    this.visionsOptions = res.version_info_list;
    this.shareInfo = res;
    this.cdr.markForCheck();
  }
}
