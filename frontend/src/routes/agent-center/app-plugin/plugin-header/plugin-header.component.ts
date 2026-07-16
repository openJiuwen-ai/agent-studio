import { Component, ChangeDetectionStrategy, Input, Output, ChangeDetectorRef, EventEmitter } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { Subject, Subscription, takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { InlineSvgComponent } from '@shared/components/inline-svg.component';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import type { IPlugin } from '../app-plugin.interface';
import { pluginSchemaStr2Args, initializeReqItem, pluginSchemaStr2Path } from '../utils';
import { PublishVersionModalComponent } from '@shared/components/publish-version-modal/publish-version-modal.component';
import { PluginDebugModalComponent } from '../components/plugin-debug-modal/plugin-debug-modal.component';
import { PluginVersionComponent } from '../components/plugin-version/plugin-version.component';
import { PluginReferenceComponent } from '../components/plugin-reference/plugin-reference.component';
import { NgIf } from '@angular/common';
import { PermissionService } from '@services/permission.service';
import { PrevRouteService } from '@services/prev-route.service';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';

enum mapKeys {
  work_space_id = 'work_space_id',
}

@Component({
  selector: 'meta-plugin-header',
  standalone: true,
  imports: [COMMON_MODULES, MODULES, InlineSvgComponent, NgIf, NzIconModule, NzTagModule, NzToolTipModule, NzButtonModule, NzModalModule, NzDrawerModule],
  templateUrl: './plugin-header.component.html',
  styleUrl: './plugin-header.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.REVIEW],
    },
  ],
})
export class PluginHeaderComponent {
  @Input() pluginInfo;
  @Input() isToolDetail: boolean = false;
  @Input() previewVersionId = '';
  @Output() update = new EventEmitter<void>();
  // 是否来自agentBuilder
  @Input() isFromAgentBuilder: boolean = false;
  @Input() isFromDevelopSpace: boolean = false;

  @Input() showCrumb: boolean = true;

  public historyIcon = cdnAssetUrl('assets/agent-center/icons/release-history.svg');

  public referenceIcon = cdnAssetUrl('assets/agent-center/icons/public_link.svg');

  historyVersionList = [];

  test_status: 'SUCCESS' | 'FAILED' | 'UNKNOWN';

  private destroy$ = new Subject<void>();
  public currentPermissions: any;
  private permissionSubscription: Subscription;
  public isPluginMarket = true;
  pageFromId: any;
  pageFrom: any;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  workSpaceId = '';

  constructor(
    private router: Router,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private nzModal: NzModalService,
    private appPluginRepoServ: AppPluginRepoService,
    private agentDataServe: AgentDataService,
    private permissionService: PermissionService,
    private activeRoute: ActivatedRoute,
    private commonService: CommonService,
    private nzDrawerService: NzDrawerService
  ) {}

  ngOnInit() {
    this.activeRoute.queryParams.subscribe(params => {
      this.pageFromId = params.from_id;
      this.pageFrom = params.from;
      if (params[mapKeys.work_space_id]) {
        this.workSpaceId = params[mapKeys.work_space_id];
      }
    });
    this.isPluginMarket = this.router.url.indexOf('plugin-market/detail') > -1;
    this.agentDataServe
      .publishStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        if (status === 'succeeded') {
          this.pluginInfo.test_status === 'SUCCESS';
          this.pluginInfo = { ...this.pluginInfo };
          this.cdr.markForCheck();
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

  public openDebugModal() {
    let requestArgs = [...pluginSchemaStr2Args(this.pluginInfo?.input_schema), ...pluginSchemaStr2Path(this.pluginInfo?.input_schema)];
    const { tool_display_name, tool_desc, visibility, tool_chinese_name, request_info, auth_info, is_input_list, is_output_list, intf_type, input_schema } =
      this.pluginInfo;
    let pluginBodyParams = {
      tool_display_name,
      tool_desc,
      visibility,
      tool_chinese_name,
      request_info,
      auth_info,
      is_input_list,
      is_output_list,
      intf_type,
      input_schema,
      icon: undefined,
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
    instance.pluginBodyParams = this.pluginInfo.tool_id ? { tool_id: this.pluginInfo.tool_id } : pluginBodyParams;
    instance.afterClose.subscribe(async () => {
      const result = instance.debugResult;
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
        id: this.pluginInfo.tool_id,
      };
      delete params.data.auth_info;
      await this.appPluginRepoServ.updatePlugins(params);
      this.cdr.markForCheck();
    });
  }

  getPublishTip() {
    if (this.test_status === 'SUCCESS') {
      return '';
    }

    if (this.test_status === 'FAILED') {
      return this.i18n.transform('plugin_debugging_failed_tip');
    }

    if (this.pluginInfo.test_status === 'UNKNOWN') {
      return this.i18n.transform('plug_not_debug_tip');
    }

    return '';
  }

  getReference() {
    const drawerRef = this.nzDrawerService.create({
      nzContent: PluginReferenceComponent,
      nzWidth: 600,
      nzData: {
        tool_id: this.pluginInfo.plugin_id,
      },
    });
  }

  getHistory() {
    const drawerRef = this.nzDrawerService.create({
      nzContent: PluginVersionComponent,
      nzWidth: 600,
      nzData: {
        tool_id: this.pluginInfo.plugin_id,
        update: () => {
          this.update.emit();
        },
      },
    });
  }

  publishPlugin() {
    const modalRef: any = this.nzModal.create({
      nzContent: PublishVersionModalComponent,
      nzWidth: 600,
      nzFooter: null,
      nzClosable: true,
      nzMaskClosable: false,
    });
    const instance = modalRef.getContentComponent();
    instance.title = this.i18n.transform('submit_version');
    instance.app_id = this.pluginInfo.plugin_id;
    instance.app_type = 'tool';
    instance.publishSuccess.subscribe(() => {
      this.update.emit();
    });
  }
  gotoPluginList(queryParams?: Record<string, string>) {
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space']);
      return;
    }
    queryParams.tabId = 'plugin';
    this.router.navigate(['/home/agent-center/library-home'], { queryParams });
  }
  onPageBack() {
    const queryParams = this.activeRoute.snapshot.queryParams;
    let _queryParams: Record<string, string> = {};
    if (this.isFromAgentBuilder) {
      Object.keys(queryParams).forEach((key: string) => {
        if (key === 'from' || key === 'work_space_id') {
          _queryParams[key] = queryParams[key];
        }
      });
    }
    if (this.pageFrom === 'flow') {
      this.router.navigate(['/home/agent-center/app-flow/flow'], {
        queryParams: {
          id: this.pageFromId,
          ..._queryParams,
        },
      });
    } else if (this.pageFrom === 'overview') {
      this.router.navigate(['/home/overview']);
    } else if (this.isToolDetail) {
      // 需要保留从工作流或智能体跳转过来全部的query
      this.router.navigate(['/home/agent-center/custom-plugin/detail'], {
        queryParams: {
          id: this.pluginInfo?.plugin_id,
          ..._queryParams,
        },
      });
    } else {
      this.gotoPluginList(_queryParams);
    }
  }
}
